"""
Módulo de Registro de Carpetas Persistentes y Gestión Git / GitHub — J&D Automation Industries
Guarda la información completa de cada cotización en un directorio resguardado (`cotizaciones_guardadas/{folio}/`):
- Cotización PDF membretada
- Archivo Excel presupuestario
- Correo .EML completo
- Paquete .ZIP entregable
- Archivo de metadata JSON (info_cotizacion.json)

Incluye utilidades para exploración y borrado seguro local y remoto en GitHub vía API REST o Git CLI.
"""

import os
import json
import io
import shutil
import re
import requests
from datetime import datetime
import subprocess

STORAGE_BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cotizaciones_guardadas")
os.makedirs(STORAGE_BASE_DIR, exist_ok=True)

GITHUB_REPO_OWNER = "jesusalbertomoraleslopez-byte"
GITHUB_REPO_NAME = "jd-cotizador-app"

def sanitize_folio(folio_str):
    if not folio_str:
        return "COT_2026_001"
    clean_f = str(folio_str).replace('_Cotizacion_Oficial', '').strip()
    f_parts = clean_f.split('-')
    folio_corto = "-".join(f_parts[:3]) if len(f_parts) >= 3 else clean_f
    return re.sub(r'[^a-zA-Z0-9_-]', '_', folio_corto).strip('_')

def save_cotizacion_to_folder(cot_info, pdf_bytes=None, excel_bytes=None, eml_bytes=None, zip_bytes=None):
    """
    Crea o actualiza la carpeta persistente para la cotización especificada y guarda todos los entregables.
    """
    folio_clean = sanitize_folio(cot_info.get('folio', 'COT-001'))
    folder_path = os.path.join(STORAGE_BASE_DIR, folio_clean)
    os.makedirs(folder_path, exist_ok=True)

    saved_files = []

    # 1. Guardar PDF Membretado
    if pdf_bytes:
        pdf_fname = f"{folio_clean}_Propuesta_Tecnico_Comercial.pdf"
        pdf_path = os.path.join(folder_path, pdf_fname)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        saved_files.append(pdf_fname)

    # 2. Guardar Excel Presupuestario
    if excel_bytes:
        excel_fname = f"{folio_clean}_Presupuesto_Financiero.xlsx"
        excel_path = os.path.join(folder_path, excel_fname)
        with open(excel_path, "wb") as f:
            f.write(excel_bytes)
        saved_files.append(excel_fname)

    # 3. Guardar Correo .EML
    if eml_bytes:
        eml_fname = f"{folio_clean}_Correo_Notificacion.eml"
        eml_path = os.path.join(folder_path, eml_fname)
        with open(eml_path, "wb") as f:
            f.write(eml_bytes)
        saved_files.append(eml_fname)

    # 4. Guardar Paquete .ZIP
    if zip_bytes:
        zip_fname = f"{folio_clean}_Paquete_Entregable.zip"
        zip_path = os.path.join(folder_path, zip_fname)
        with open(zip_path, "wb") as f:
            f.write(zip_bytes)
        saved_files.append(zip_fname)

    # 5. Guardar Ficha JSON de Metadata
    metadata = {
        "folio": cot_info.get('folio'),
        "folio_clean": folio_clean,
        "proyecto": cot_info.get('proyecto'),
        "cliente": cot_info.get('cliente'),
        "fecha_guardado": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "archivos": saved_files
    }
    json_path = os.path.join(folder_path, "info_cotizacion.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    try:
        auto_sync_database_and_storage_to_github(f"Auto-sync quote {folio_clean} and database")
    except Exception:
        pass

    return folder_path, saved_files


def list_saved_cotizaciones():
    """
    Retorna la lista de carpetas de cotizaciones resguardadas con sus detalles.
    """
    if not os.path.exists(STORAGE_BASE_DIR):
        return []

    records = []
    for item in os.listdir(STORAGE_BASE_DIR):
        item_path = os.path.join(STORAGE_BASE_DIR, item)
        if os.path.isdir(item_path):
            json_path = os.path.join(item_path, "info_cotizacion.json")
            meta = {}
            if os.path.exists(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass

            files_list = [f for f in os.listdir(item_path) if not f.startswith('.')]
            total_size_kb = sum(os.path.getsize(os.path.join(item_path, f)) for f in files_list) / 1024.0

            records.append({
                "folio_folder": item,
                "proyecto": meta.get("proyecto", item),
                "cliente": meta.get("cliente", "—"),
                "fecha_guardado": meta.get("fecha_guardado", "—"),
                "num_archivos": len(files_list),
                "tamano_kb": f"{total_size_kb:.1f} KB",
                "folder_path": item_path,
                "archivos": files_list
            })
    return records


def delete_saved_cotizacion_folder(folio_folder):
    """
    Elimina localmente la carpeta de la cotización resguardada.
    """
    folder_path = os.path.join(STORAGE_BASE_DIR, folio_folder)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        return True
    return False


def delete_from_github_api(folio_folder, token=None):
    """
    Elimina la carpeta de la cotización en el repositorio de GitHub usando la API REST v3 o comandos Git.
    """
    results = {"success": False, "message": "", "method": "Git CLI / GitHub API"}
    
    # Intento 1: Usar Git CLI local si el directorio es una copia de trabajo git
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_rel = os.path.join("cotizaciones_guardadas", folio_folder)
    target_abs = os.path.join(repo_root, target_rel)

    # Borrado local primero
    if os.path.exists(target_abs):
        try:
            shutil.rmtree(target_abs)
        except Exception:
            pass

    # Intentar git rm y push
    try:
        cmd_rm = subprocess.run(["git", "rm", "-r", "--ignore-unmatch", target_rel], cwd=repo_root, capture_output=True, text=True)
        cmd_commit = subprocess.run(["git", "commit", "-m", f"Delete saved quote folder {folio_folder} from storage"], cwd=repo_root, capture_output=True, text=True)
        cmd_push = subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, capture_output=True, text=True)

        if cmd_push.returncode == 0 or "Everything up-to-date" in cmd_push.stdout or "Everything up-to-date" in cmd_push.stderr:
            return {
                "success": True,
                "message": f"Se ha eliminado localmente y sincronizado el borrado en GitHub para '{folio_folder}'.",
                "method": "Git CLI Native Push"
            }
    except Exception as e:
        pass

    # Intento 2: Usar API REST de GitHub si se proporciona Token
    if token:
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/cotizaciones_guardadas/{folio_folder}"
        
        # Obtener lista de archivos en esa carpeta de GitHub
        resp = requests.get(api_url, headers=headers)
        if resp.status_code == 200:
            files_items = resp.json()
            deleted_count = 0
            for file_item in files_items:
                if file_item.get("type") == "file":
                    del_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/{file_item['path']}"
                    payload = {
                        "message": f"Delete {file_item['name']} from {folio_folder}",
                        "sha": file_item["sha"],
                        "branch": "main"
                    }
                    del_resp = requests.delete(del_url, headers=headers, json=payload)
                    if del_resp.status_code == 200:
                        deleted_count += 1
            return {
                "success": True,
                "message": f"Se han eliminado {deleted_count} archivo(s) de GitHub en la carpeta '{folio_folder}'.",
                "method": "GitHub REST API v3"
            }
        elif resp.status_code == 404:
            return {
                "success": True,
                "message": f"La carpeta '{folio_folder}' no existía en el remoto de GitHub (o ya fue eliminada).",
                "method": "GitHub REST API v3"
            }
        else:
            return {
                "success": False,
                "message": f"Error de autenticación o respuesta de GitHub: {resp.status_code} - {resp.text}",
                "method": "GitHub REST API v3"
            }

    return {
        "success": True,
        "message": f"Se eliminó la carpeta '{folio_folder}' del sistema de archivos.",
        "method": "Local Filesystem Clean"
    }


def fetch_github_quote_folders(token=None):
    """
    Consulta la API REST de GitHub para obtener en tiempo real todas las carpetas y archivos resguardados en GitHub.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/cotizaciones_guardadas"
    headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "JD-Cotizador-App"}
    if token:
        headers["Authorization"] = f"token {token}"
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            items = res.json()
            folders = []
            for it in items:
                if it.get("type") == "dir":
                    sub_url = it.get("url")
                    sub_res = requests.get(sub_url, headers=headers, timeout=10)
                    sub_files = []
                    if sub_res.status_code == 200:
                        for s_it in sub_res.json():
                            sub_files.append({
                                "name": s_it.get("name"),
                                "size_kb": f"{s_it.get('size', 0)/1024.0:.1f} KB",
                                "download_url": s_it.get("download_url"),
                                "html_url": s_it.get("html_url"),
                                "path": s_it.get("path"),
                                "sha": s_it.get("sha")
                            })
                    folders.append({
                        "folder_name": it.get("name"),
                        "path": it.get("path"),
                        "html_url": it.get("html_url"),
                        "files": sub_files
                    })
            return {"success": True, "folders": folders}
        elif res.status_code == 404:
            return {"success": True, "folders": [], "message": "La carpeta 'cotizaciones_guardadas' aún no se ha subido a GitHub."}
        else:
            return {"success": False, "message": f"Respuesta de GitHub HTTP {res.status_code}: {res.text}"}
    except Exception as e:
        return {"success": False, "message": f"Error conectando con la API de GitHub: {str(e)}"}


def auto_sync_database_and_storage_to_github(commit_message="Auto-sync cotizador.db and quote files"):
    """
    Sincroniza y hace commit/push automático a GitHub de la base de datos SQLite (cotizador.db)
    y el directorio cotizaciones_guardadas/ para garantizar que persistan 100% tras un reboot en Streamlit Cloud.
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_rel = os.path.join("database", "cotizador.db")
    storage_rel = "cotizaciones_guardadas"
    
    try:
        subprocess.run(["git", "add", "-f", db_rel, storage_rel], cwd=repo_root, capture_output=True, text=True)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=repo_root, capture_output=True, text=True)
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, capture_output=True, text=True)
        
        if push_res.returncode == 0 or "Everything up-to-date" in push_res.stdout or "Everything up-to-date" in push_res.stderr:
            return {"success": True, "method": "Git CLI Native Auto-Push"}
    except Exception:
        pass

    return {"success": False, "message": "Proceso local completado."}
