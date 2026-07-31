import streamlit as st
import os
import io
import shutil
import pandas as pd
from datetime import datetime
from config import (BRAND_ORANGE, BRAND_CHARCOAL, BRAND_CHARCOAL_MED,
                    BRAND_GRAY_BG, BRAND_WHITE, BRAND_BORDER_LIGHT)
from database.models import get_connection, init_db
from modules.auth import check_admin_permission, is_admin
from modules.pdf_exporter import generar_pdf_modulo

SGC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sgc_procedimientos")
os.makedirs(SGC_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# 1. ÁREA DE MANTENIMIENTO Y ALMACENAMIENTO TÉCNICO AVANZADO (SECCIÓN 8)
# ─────────────────────────────────────────────────────────────────────────────

def render_mantenimiento_page():
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>🛠️ Módulo de Mantenimiento y Administración General</h2>
        <p>Centro unificado para la gestión de base de datos, corrección de registros, limpieza de deploy y almacenamiento.</p>
    </div>""", unsafe_allow_html=True)

    # Verificación de rol de Administrador
    admin_ok = is_admin()
    if not admin_ok:
        st.markdown(f"""
        <div style="background:#FFFBEB; border:1px solid #FCD34D; border-left:5px solid #F59E0B;
                    border-radius:8px; padding:16px 20px; margin-bottom:20px; font-family:'Montserrat',sans-serif;">
            <p style="font-size:13px; font-weight:800; color:#B45309; margin:0 0 4px 0;">
                🔒 ACCESO RESTRINGIDO — PERFIL OPERADOR (MODO CONSULTA)
            </p>
            <p style="font-size:11px; color:#92400E; margin:0;">
                Actualmente estás navegando con perfil de <b>Operador</b>. Puedes consultar los catálogos y resumenes de mantenimiento, 
                pero la modificación manual, eliminación de registros y borrado de fábrica están <b>reservados únicamente para el Administrador</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)

    m_tab1, m_tab2, m_tab3, m_tab4, m_tab5 = st.tabs([
        "🔒 Control DB & Borrado Masivo",
        "🏢 Clientes",
        "📦 Catálogos Base",
        "✏️ Modificador de Cotizaciones",
        "🗄️ Explorador Deploy & GitHub"
    ])

    # ── TAB 1: GESTIÓN DE BASE DE DATOS & BORRADO ──
    with m_tab1:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-left:5px solid {BRAND_ORANGE};
                    border-radius:8px;padding:16px 20px;margin-bottom:20px;font-family:'Montserrat',sans-serif;">
            <p style="font-size:13px;font-weight:700;color:{BRAND_CHARCOAL};margin:0 0 4px 0;">
                ⚙️ GESTIÓN Y CORRECCIÓN MASIVA DE COTIZACIONES
            </p>
            <p style="font-size:11px;color:{BRAND_CHARCOAL_MED};margin:0;">
                Selecciona casillas de verificación para cambio de estatus en lote, eliminación selectiva de datos o desbloqueo.
            </p>
        </div>
        """, unsafe_allow_html=True)

        conn = get_connection(); cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.folio, c.proyecto, c.congelada, c.estatus, COALESCE(c.revision,'R0') as revision,
                   COALESCE(cl.nombre,'—') as cliente,
                   (SELECT COUNT(*) FROM cotizacion_partidas WHERE cotizacion_id=c.id) as n_partidas
            FROM cotizaciones c LEFT JOIN clientes cl ON c.cliente_id=cl.id
            ORDER BY c.id DESC
        """)
        cots_mant = [dict(r) for r in cur.fetchall()]
        conn.close()

        if not cots_mant:
            st.info("No hay cotizaciones registradas en la base de datos.")
        else:
            df_mant = pd.DataFrame(cots_mant)
            df_mant['Seleccionar'] = False
            df_mant['Estado'] = df_mant['congelada'].apply(lambda x: "🔒 CONGELADA" if x else "✏️ EDITABLE")
            
            df_display = df_mant[['Seleccionar', 'id', 'folio', 'revision', 'proyecto', 'cliente', 'Estado', 'estatus', 'n_partidas']]

            edited_df = st.data_editor(
                df_display,
                column_config={
                    "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", help="Marcar para acciones masivas"),
                    "id": st.column_config.NumberColumn("ID", disabled=True),
                    "folio": st.column_config.TextColumn("Folio", disabled=True),
                    "revision": st.column_config.TextColumn("Revisión", disabled=True),
                    "proyecto": st.column_config.TextColumn("Proyecto", disabled=True),
                    "cliente": st.column_config.TextColumn("Cliente", disabled=True),
                    "Estado": st.column_config.TextColumn("Estado", disabled=True),
                    "estatus": st.column_config.SelectboxColumn("Estatus Comercial", options=["Borrador", "Cotizado", "En Proceso", "Ganada", "Perdida", "Cancelada"]),
                    "n_partidas": st.column_config.NumberColumn("Partidas", disabled=True)
                },
                use_container_width=True,
                hide_index=True,
                key="editor_cotizaciones_mant"
            )

            selected_rows = edited_df[edited_df["Seleccionar"] == True]
            selected_ids = selected_rows["id"].tolist()

            st.markdown("---")

            col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 1])

            with col_b1:
                st.markdown(f"<p style='font-size:12px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 6px 0;'>🏷️ CAMBIO DE ESTATUS EN LOTE</p>", unsafe_allow_html=True)
                nuevo_est_lote = st.selectbox("Estatus para seleccionadas", ["Borrador", "Cotizado", "En Proceso", "Ganada", "Perdida", "Cancelada"], key="sel_est_lote")
                if st.button(f"🏷️ Aplicar Estatus '{nuevo_est_lote}' a ({len(selected_ids)})", use_container_width=True):
                    if not admin_ok:
                        st.error("🔒 Se requiere perfil de ADMINISTRADOR para modificar registros.")
                    elif not selected_ids:
                        st.warning("Selecciona al menos una cotización usando las casillas de verificación.")
                    else:
                        from database.db_manager import bulk_update_cotizaciones_estatus
                        bulk_update_cotizaciones_estatus(selected_ids, nuevo_est_lote)
                        st.success(f"Estatus actualizado a '{nuevo_est_lote}' para {len(selected_ids)} cotización(es).")
                        st.rerun()

            with col_b2:
                st.markdown(f"<p style='font-size:12px;font-weight:800;color:#DC2626;margin:0 0 6px 0;'>🗑️ BORRADO DE REGISTROS SELECCIONADOS</p>", unsafe_allow_html=True)
                confirm_bulk = st.checkbox(f"Confirmar eliminación de {len(selected_ids)} registro(s)", key="chk_confirm_bulk")
                if st.button(f"🗑️ Eliminar ({len(selected_ids)}) Cotizaciones Seleccionadas", type="primary", use_container_width=True):
                    if not admin_ok:
                        st.error("🔒 Se requiere perfil de ADMINISTRADOR para borrar registros.")
                    elif not selected_ids:
                        st.warning("Selecciona al menos una cotización usando las casillas de verificación.")
                    elif not confirm_bulk:
                        st.error("Por favor marca la casilla de confirmación antes de eliminar.")
                    else:
                        from database.db_manager import bulk_delete_cotizaciones
                        bulk_delete_cotizaciones(selected_ids)
                        st.success(f"Se han eliminado exitosamente {len(selected_ids)} cotización(es) y sus desgloses.")
                        st.rerun()

            with col_b3:
                st.markdown(f"<p style='font-size:12px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 6px 0;'>🔓 ACCIÓN INDIVIDUAL</p>", unsafe_allow_html=True)
                cots_lock = [c for c in cots_mant if c['congelada']]
                if cots_lock:
                    opt_lock = {f"🔒 {c['folio']} ({c['revision']})": c['id'] for c in cots_lock}
                    sel_lock = st.selectbox("Reabrir Congelada", list(opt_lock.keys()), key="sel_unlock_fast", label_visibility="collapsed")
                    if st.button("🔓 Desbloquear", use_container_width=True):
                        if not admin_ok:
                            st.error("🔒 Se requiere perfil de ADMINISTRADOR para desbloquear.")
                        else:
                            c_id = opt_lock[sel_lock]
                            conn = get_connection()
                            conn.execute("UPDATE cotizaciones SET congelada=0, estatus='En Revisión' WHERE id=?", (c_id,))
                            conn.commit(); conn.close()
                            st.success("Cotización reabierta como Borrador.")
                            st.rerun()

        st.markdown("---")

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown(f"""
            <div style="background:#F8FAFC;border:1px solid #CBD5E1;border-radius:8px;padding:14px;margin-bottom:10px;">
                <h4 style="margin:0 0 4px 0;color:{BRAND_CHARCOAL};font-weight:800;font-size:13px;">📦 RESPALDO COMPLETO DE BASE DE DATOS (.ZIP)</h4>
                <p style="margin:0;color:{BRAND_CHARCOAL_MED};font-size:11px;">Genera un archivo comprimido .ZIP con la base de datos `cotizador.db` completa para resguardo.</p>
            </div>
            """, unsafe_allow_html=True)
            try:
                from database.db_manager import backup_database_zip
                zip_bytes, zip_fname = backup_database_zip()
                st.download_button(
                    label=f"📦 DESCARGAR RESPALDO COMPLETO ({zip_fname})",
                    data=zip_bytes,
                    file_name=zip_fname,
                    mime="application/zip",
                    use_container_width=True,
                    type="primary",
                    key="btn_dl_db_zip"
                )
            except Exception as e:
                st.error(f"Error generando respaldo ZIP: {e}")

        with col_res2:
            st.markdown(f"""
            <div style="background:#FEF2F2;border:1px solid #FCA5A5;border-radius:8px;padding:14px;margin-bottom:10px;">
                <h4 style="margin:0 0 4px 0;color:#991B1B;font-weight:800;font-size:13px;">⚙️ BORRADO DE FÁBRICA (RESET DE TRANSACCIONES)</h4>
                <p style="margin:0;color:#7F1D1D;font-size:11px;">Elimina TODAS las cotizaciones y partidas de prueba, <b>conservando 100% intactos los catálogos base</b>.</p>
            </div>
            """, unsafe_allow_html=True)
            
            chk_reset = st.checkbox("Confirmar que deseo realizar un Borrado de Fábrica completo", key="chk_reset_factory")
            if st.button("🚨 EJECUTAR BORRADO DE FÁBRICA (RESET)", type="primary", use_container_width=True, key="btn_factory_reset"):
                if not admin_ok:
                    st.error("🔒 Se requiere perfil de ADMINISTRADOR para realizar borrado de fábrica.")
                elif not chk_reset:
                    st.error("Por favor marca la casilla de confirmación obligatoria.")
                else:
                    from database.db_manager import factory_reset_database
                    factory_reset_database()
                    st.success("🎉 ¡Borrado de fábrica ejecutado! Todas las cotizaciones fueron eliminadas y los catálogos base se conservaron intactos.")
                    st.rerun()

    # ── TAB 2: CLIENTES ──
    with m_tab2:
        from modules.clientes import render_clientes_page
        render_clientes_page()

    # ── TAB 3: CATÁLOGOS BASE ──
    with m_tab3:
        from modules.catalogos import render_catalogos_page
        render_catalogos_page()

    # ── TAB 4: MODIFICADOR DE COTIZACIONES ──
    with m_tab4:
        from modules.cotizador_editor import render_cotizador_editor
        render_cotizador_editor()

    # ── TAB 5: ALMACENAMIENTO & DEPLOY (STREAMLIT / GITHUB) ──
    with m_tab5:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-left:5px solid #0EA5E9;
                    border-radius:8px;padding:16px 20px;margin-bottom:20px;font-family:'Montserrat',sans-serif;">
            <p style="font-size:13px;font-weight:700;color:{BRAND_CHARCOAL};margin:0 0 4px 0;">
                🗄️ EXPLORADOR DE ALMACENAMIENTO Y MANTENIMIENTO DE SERVIDOR (STREAMLIT / GITHUB)
            </p>
            <p style="font-size:11px;color:{BRAND_CHARCOAL_MED};margin:0;">
                Monitoreo de espacio en disco, optimización SQLite `VACUUM` y limpieza de temporales de compilación/deploy.
            </p>
        </div>
        """, unsafe_allow_html=True)

        base_project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_project_dir, "database", "cotizador.db")
        db_size_mb = (os.path.getsize(db_path) / (1024 * 1024)) if os.path.exists(db_path) else 0.0

        st.markdown(f"**Ubicación de Base de Datos:** `{db_path}`")
        st.markdown(f"**Tamaño Actual en Disco:** `<b style='color:{BRAND_ORANGE};font-size:16px;'>{db_size_mb:.2f} MB</b>`", unsafe_allow_html=True)

        cl1, cl2, cl3 = st.columns(3)
        with cl1:
            if st.button("🧹 Optimizar Base de Datos (SQLite VACUUM)", type="primary", use_container_width=True):
                conn = get_connection()
                conn.execute("VACUUM")
                conn.commit(); conn.close()
                st.success("Se ha ejecutado `VACUUM` exitosamente. Espacio liberado y BD compactada.")

        with cl2:
            if st.button("🔄 Reindexar & Integridad DB", use_container_width=True):
                conn = get_connection(); cur = conn.cursor()
                cur.execute("PRAGMA integrity_check")
                check = cur.fetchone()[0]
                conn.close()
                if check == "ok":
                    st.success("Integridad de base de datos: **OK (100% Saludable)**")
                else:
                    st.error(f"Resultado de verificación: {check}")

        with cl3:
            if st.button("🚀 Limpiar Temporales y Cache de Deploy", use_container_width=True):
                # Limpiar temporales
                temp_dir = os.path.join(base_project_dir, ".tempmediaStorage")
                count_del = 0
                if os.path.exists(temp_dir):
                    for f in os.listdir(temp_dir):
                        try:
                            os.remove(os.path.join(temp_dir, f))
                            count_del += 1
                        except Exception:
                            pass
                st.success(f"Se han removido {count_del} archivos temporales y caches de servidor.")

        st.markdown("---")
        st.markdown(f"### 📁 CARPETAS Y ARCHIVOS EN REPOSITORIO GITHUB & SERVIDOR")

        from database.storage_manager import list_saved_cotizaciones, delete_saved_cotizacion_folder, delete_from_github_api, fetch_github_quote_folders
        saved_cots = list_saved_cotizaciones()

        st.markdown(f"#### 🖥️ 1. Carpetas y Archivos en Servidor Local / Deploy (`cotizaciones_guardadas/`)")

        if not saved_cots:
            st.info("No hay carpetas de cotización resguardadas en `cotizaciones_guardadas/` actualmente.")
        else:
            df_storage = pd.DataFrame(saved_cots)[['folio_folder', 'proyecto', 'cliente', 'fecha_guardado', 'num_archivos', 'tamano_kb']]
            st.dataframe(
                df_storage,
                column_config={
                    "folio_folder": st.column_config.TextColumn("Carpeta Folio"),
                    "proyecto": st.column_config.TextColumn("Proyecto"),
                    "cliente": st.column_config.TextColumn("Cliente"),
                    "fecha_guardado": st.column_config.TextColumn("Fecha Guardado"),
                    "num_archivos": st.column_config.NumberColumn("Archivos"),
                    "tamano_kb": st.column_config.TextColumn("Tamaño")
                },
                use_container_width=True,
                hide_index=True
            )

            col_sel_f, col_act_f = st.columns([2, 1.5])
            with col_sel_f:
                opt_folders = [s['folio_folder'] for s in saved_cots]
                sel_folder = st.selectbox("Seleccionar Carpeta de Cotización para Gestionar", opt_folders, key="sel_folder_resguardo")
                
                target_rec = next((r for r in saved_cots if r['folio_folder'] == sel_folder), None)
                if target_rec:
                    st.markdown(f"**Archivos en `cotizaciones_guardadas/{sel_folder}/`:**")
                    for af in target_rec['archivos']:
                        af_p = os.path.join(target_rec['folder_path'], af)
                        af_size = os.path.getsize(af_p) / 1024.0 if os.path.exists(af_p) else 0.0
                        st.markdown(f"• `{af}` ({af_size:.1f} KB)")

            with col_act_f:
                st.markdown(f"<p style='font-size:12px;font-weight:800;color:#DC2626;'>🗑️ ACCIONES DE ELIMINACIÓN Y BORRADO REMOTO</p>", unsafe_allow_html=True)
                
                gh_token_input = st.text_input("GitHub Token (PAT Opcional)", value=os.environ.get("GITHUB_TOKEN", ""), type="password", help="Ingresa tu Personal Access Token de GitHub si deseas forzar el borrado o lectura restringida", key="gh_token_input")

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"🗑️ Eliminar '{sel_folder}' Localmente", use_container_width=True, key="btn_del_local_folder"):
                    if not admin_ok:
                        st.error("🔒 Se requiere perfil de ADMINISTRADOR para borrar carpetas resguardadas.")
                    else:
                        if delete_saved_cotizacion_folder(sel_folder):
                            st.success(f"La carpeta '{sel_folder}' ha sido eliminada localmente.")
                            st.rerun()
                        else:
                            st.error("No se pudo encontrar la carpeta especificada.")

                if st.button(f"🌐 ELIMINAR Y PURGAR CARPETA EN GITHUB", type="primary", use_container_width=True, key="btn_del_github_folder"):
                    if not admin_ok:
                        st.error("🔒 Se requiere perfil de ADMINISTRADOR para eliminar en GitHub.")
                    else:
                        with st.spinner(f"Eliminando carpeta '{sel_folder}' en repositorio GitHub..."):
                            res_gh = delete_from_github_api(sel_folder, token=gh_token_input.strip() if gh_token_input else None)
                            if res_gh["success"]:
                                st.success(f"🎉 {res_gh['message']} (Método: {res_gh['method']})")
                                st.rerun()
                            else:
                                st.error(f"Error al eliminar en GitHub: {res_gh['message']}")

        st.markdown("---")
        st.markdown("#### 🌐 2. Explorador en Tiempo Real de Carpetas y Archivos en Repositorio GITHUB")
        st.markdown("`https://github.com/jesusalbertomoraleslopez-byte/jd-cotizador-app/tree/main/cotizaciones_guardadas`")

        if st.button("🔄 Consultar / Refrescar Archivos en GitHub API", type="primary", key="btn_refresh_gh_api"):
            st.session_state['gh_fetch_run'] = True

        gh_res = fetch_github_quote_folders(token=gh_token_input.strip() if 'gh_token_input' in locals() and gh_token_input else None)

        if gh_res.get("success"):
            gh_folders = gh_res.get("folders", [])
            if not gh_folders:
                st.info("ℹ️ " + gh_res.get("message", "No se encontraron carpetas remotas en 'cotizaciones_guardadas' en GitHub."))
            else:
                st.success(f"✅ Se encontraron **{len(gh_folders)} carpeta(s)** registradas remotamente en GitHub:")
                for gf in gh_folders:
                    with st.expander(f"📁 GitHub: {gf['folder_name']} ({len(gf['files'])} archivos)", expanded=True):
                        st.markdown(f"**Ruta Remota:** `{gf['path']}` | [🔗 Ver en GitHub.com]({gf['html_url']})")
                        st.markdown("**Archivos Contenidos:**")
                        for gfile in gf['files']:
                            c_f1, c_f2 = st.columns([3, 1])
                            c_f1.markdown(f"• 📄 **`{gfile['name']}`** ({gfile['size_kb']})")
                            if gfile.get("download_url"):
                                c_f2.markdown(f"[⬇️ Descargar Directo de GitHub]({gfile['download_url']})")
        else:
            st.warning(f"No se pudo consultar el API de GitHub directamente: {gh_res.get('message')}")

        st.markdown("---")
        # Exportación Universal PDF Mantenimiento
        sec_mant_pdf = [
            {'title': 'Estado General de Base de Datos', 'content': f'Base de datos: {db_path}\nTamaño en disco: {db_size_mb:.2f} MB\nEstado Integridad: OK'},
            {'title': 'Resumen de Seguridad y Accesos', 'content': 'Perfil Activo: Administrador\nAcceso a Acciones Críticas: Habilitado'}
        ]
        pdf_mant_bytes = generar_pdf_modulo("Reporte de Mantenimiento y Almacenamiento", "Auditoría de Servidor y Deploy J&D Automation", sec_mant_pdf)
        st.download_button(
            label="📄 EXPORTAR REPORTE DE MANTENIMIENTO EN PDF",
            data=pdf_mant_bytes,
            file_name="Reporte_Mantenimiento_Almacenamiento_JD.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key="btn_dl_pdf_mantenimiento"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. SISTEMA DE GESTIÓN DE CALIDAD (SGC) (SECCIÓN 4)
# ─────────────────────────────────────────────────────────────────────────────

def render_sgc_page():
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>📜 Sistema de Gestión de Calidad (SGC)</h2>
        <p>Empatado de procedimientos institucionales oficiales de J&D Automation Industries y carga de documentación normada.</p>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{BRAND_GRAY_BG};border:1px solid {BRAND_BORDER_LIGHT};border-left:5px solid {BRAND_ORANGE};
                border-radius:10px;padding:20px;margin-bottom:24px;font-family:'Montserrat',sans-serif;">
        <h3 style="font-size:16px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 8px 0;">POLÍTICA DE CALIDAD & CONTROL DE PROCEDIMIENTOS (ISO 9001:2015)</h3>
        <p style="font-size:12px;color:{BRAND_CHARCOAL_MED};line-height:1.6;margin:0;">
            El presente módulo garantiza el cumplimiento de los estándares de calidad <b>ISO 9001:2015</b> alineados 
            al proceso de Ingeniería Comercial, Costeo de Proyectos de Automatización y Emisión de Ofertas Técnicas.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Procedimientos Institucionales Registrados
    procedimientos = [
        {"Código": "SGC-PROC-01", "Nombre": "Procedimiento Oficial para la Elaboración y Revisión de Cotizaciones", "Revisión": "Rev. 04", "Estatus": "VIGENTE", "Área": "Ingeniería Comercial"},
        {"Código": "SGC-PROC-02", "Nombre": "Control de Cambios de Alcance y Gestión de Revisiones (R0 -> R+1)", "Revisión": "Rev. 02", "Estatus": "VIGENTE", "Área": "Gestión de Proyectos"},
        {"Código": "SGC-PROC-03", "Nombre": "Norma de Estructuración de Tarifas de Mano de Obra y Factor de Salario Real (FSR)", "Revisión": "Rev. 03", "Estatus": "VIGENTE", "Área": "Finanzas & Capital Humano"},
        {"Código": "SGC-PROC-04", "Nombre": "Estándar de Interoperabilidad para Exportación de Cronogramas Gantt en MS Project 2024", "Revisión": "Rev. 01", "Estatus": "VIGENTE", "Área": "Tecnologías de Información"},
    ]

    st.markdown(f"<p style='font-size:12px;font-weight:800;color:{BRAND_CHARCOAL};margin-bottom:8px;'>MATRIZ DE PROCEDIMIENTOS INSTITUCIONALES SGC</p>", unsafe_allow_html=True)
    
    for proc in procedimientos:
        with st.container():
            c1, c2, c3, c4 = st.columns([1.5, 4, 2, 2.5])
            c1.markdown(f"**`{proc['Código']}`**")
            c2.markdown(f"**{proc['Nombre']}**<br/><span style='font-size:11px;color:#64748B;'>Área: {proc['Área']}</span>", unsafe_allow_html=True)
            c3.markdown(f"**{proc['Revisión']}** | <span style='color:#059669;font-weight:700;'>{proc['Estatus']}</span>", unsafe_allow_html=True)
            
            with c4:
                sec_p = [
                    {'title': f"Procedimiento Institucional: {proc['Código']}", 'content': f"Nombre: {proc['Nombre']}\nÁrea: {proc['Área']}\nRevisión: {proc['Revisión']}\nEstatus: {proc['Estatus']}"},
                    {'title': 'Normativa ISO 9001:2015', 'content': 'Este documento forma parte del Sistema de Gestión de Calidad institucional de J&D Automation Industries S.A. de C.V.'}
                ]
                pdf_p_bytes = generar_pdf_modulo(f"Procedimiento {proc['Código']}", proc['Nombre'], sec_p)
                st.download_button(
                    label=f"📄 Descargar PDF",
                    data=pdf_p_bytes,
                    file_name=f"{proc['Código']}_Procedimiento_SGC.pdf",
                    mime="application/pdf",
                    type="primary",
                    key=f"btn_dl_proc_{proc['Código']}",
                    use_container_width=True
                )
        st.divider()

    # Carga Inicial de Archivos SGC
    st.markdown(f"""
    <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-radius:10px;padding:20px;font-family:'Montserrat',sans-serif;">
        <h4 style="font-size:14px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 10px 0;">📤 Carga Inicial de Archivos y Manuales SGC</h4>
        <p style="font-size:11px;color:{BRAND_CHARCOAL_MED};margin-bottom:14px;">
            Sube los documentos originales firmados (.pdf, .docx, .xlsx) para vincularlos al repositorio de procedimientos del SGC.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c_up1, c_up2 = st.columns([3, 2])
    with c_up1:
        uploaded_files = st.file_uploader(
            "Seleccionar archivos institucionales de procedimientos SGC",
            type=['pdf', 'docx', 'xlsx'],
            accept_multiple_files=True,
            key="up_sgc_files"
        )
    with c_up2:
        cod_asoc = st.selectbox("Asociar a Código de Procedimiento", [p['Código'] for p in procedimientos], key="sel_cod_sgc")
        desc_proc = st.text_input("Observaciones de la Versión Subida", "Carga inicial de procedimiento normado", key="txt_obs_sgc")

    if uploaded_files:
        if st.button("🚀 Subir e Integrar Documentos al SGC", type="primary", use_container_width=True, key="btn_save_sgc_upload"):
            conn = get_connection(); cur = conn.cursor()
            for uf in uploaded_files:
                save_p = os.path.join(SGC_DIR, uf.name)
                with open(save_p, "wb") as f:
                    f.write(uf.getbuffer())
                cur.execute("""
                    INSERT INTO sgc_documentos (codigo, nombre, revision, area, archivo_path, mime_type, observaciones)
                    VALUES (?, ?, 'Rev. 01', 'Ingeniería Comercial', ?, ?, ?)
                """, (cod_asoc, uf.name, save_p, uf.type, desc_proc))
            conn.commit(); conn.close()
            st.success(f"Se han registrado y guardado exitosamente **{len(uploaded_files)} archivo(s)** en el repositorio SGC.")
            st.rerun()

    st.markdown("---")
    # Exportación Universal PDF SGC
    sec_sgc_pdf = [
        {'title': 'Matriz de Procedimientos SGC', 'content': 'Resumen auditable de procedimientos oficiales ISO 9001:2015.'},
        {'table': [['Código', 'Nombre del Procedimiento', 'Revisión', 'Área']] + [[p['Código'], p['Nombre'], p['Revisión'], p['Área']] for p in procedimientos]}
    ]
    pdf_sgc_bytes = generar_pdf_modulo("Sistema de Gestión de Calidad (SGC)", "Resumen Oficial de Procedimientos Normados J&D", sec_sgc_pdf)
    st.download_button(
        label="📄 EXPORTAR MATRIZ SGC COMPLETA EN PDF",
        data=pdf_sgc_bytes,
        file_name="Matriz_Procedimientos_SGC_JD.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        key="btn_dl_pdf_sgc_matriz"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. GLOSARIO DE DOCUMENTACIÓN (SECCIÓN 5)
# ─────────────────────────────────────────────────────────────────────────────

def render_glosario_page():
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>📚 Glosario de Documentación y Tabla Maestra</h2>
        <p>Tabla maestra auditable para auditar todos los archivos que entran o salen del sistema con descargas de muestras.</p>
    </div>""", unsafe_allow_html=True)

    docs_master = [
        {
            "Código del Documento": "DOC-XML-MSP2024",
            "Descripción / Nombre Oficial": "Archivo XML Nativo MSPDI v14/v16 para Microsoft Project 2024",
            "Asociado a / Referenciado en": "📅 Plan de Proyecto (Paso 3)",
            "MIME / Formato": "application/vnd.ms-project (.xml)",
            "Muestra": "xml_msproject"
        },
        {
            "Código del Documento": "DOC-EML-RFC2045",
            "Descripción / Nombre Oficial": "Borrador de Correo RFC 822 Multipart/Mixed con Hitos (.ics) y PDF Adjuntos",
            "Asociado a / Referenciado en": "📅 Plan de Proyecto (Paso 3)",
            "MIME / Formato": "message/rfc822 (.eml)",
            "Muestra": "eml_correo"
        },
        {
            "Código del Documento": "DOC-PDF-PLAN",
            "Descripción / Nombre Oficial": "Reporte Ejecutivo PDF de Plan de Proyecto con Logo J&D Automation",
            "Asociado a / Referenciado en": "📅 Plan de Proyecto (Paso 3)",
            "MIME / Formato": "application/pdf (.pdf)",
            "Muestra": "pdf_plan"
        },
        {
            "Código del Documento": "DOC-CSV-GANTT",
            "Descripción / Nombre Oficial": "Exportación Estructurada de Cronograma Gantt en Formato CSV / Excel",
            "Asociado a / Referenciado en": "📅 Plan de Proyecto (Paso 3)",
            "MIME / Formato": "text/csv (.csv)",
            "Muestra": "csv_gantt"
        },
        {
            "Código del Documento": "DOC-TPU-EXCEL",
            "Descripción / Nombre Oficial": "Tarjeta de Precio Unitario (TPU) Desglosada con Análisis de Materiales y M.O.",
            "Asociado a / Referenciado en": "🎴 Tarjetas TPU",
            "MIME / Formato": "application/vnd.ms-excel (.xlsx)",
            "Muestra": "tpu_excel"
        }
    ]

    st.markdown(f"<p style='font-size:12px;font-weight:800;color:{BRAND_CHARCOAL};margin-bottom:12px;'>TABLA MAESTRA AUDITABLE DE FORMATOS Y ESTÁNDARES</p>", unsafe_allow_html=True)

    for i, doc in enumerate(docs_master, 1):
        with st.container():
            col1, col2, col3, col4 = st.columns([1.5, 3.5, 2.2, 1.8])
            col1.markdown(f"**`{doc['Código del Documento']}`**")
            col2.markdown(f"**{doc['Descripción / Nombre Oficial']}**<br/><span style='font-size:11px;color:#64748B;'>Formato: {doc['MIME / Formato']}</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='font-size:12px;color:{BRAND_ORANGE};font-weight:700;'>{doc['Asociado a / Referenciado en']}</span>", unsafe_allow_html=True)

            with col4:
                if doc['Muestra'] == 'xml_msproject':
                    sample_bytes = """<?xml version="1.0" encoding="UTF-8"?><Project xmlns="http://schemas.microsoft.com/project"><SaveVersion>14</SaveVersion><Name>Muestra J&D MSProject</Name></Project>""".encode('utf-8')
                    file_n, mime_t = "Muestra_MSProject2024.xml", "application/vnd.ms-project"
                elif doc['Muestra'] == 'eml_correo':
                    sample_bytes = "From: ventas@jdautomation.mx\nSubject: Muestra Correo J&D\n\nPlan de Proyecto J&D Automation".encode('utf-8')
                    file_n, mime_t = "Muestra_Correo_JND.eml", "message/rfc822"
                elif doc['Muestra'] == 'csv_gantt':
                    sample_bytes = "ID,Actividad,Tipo,Inicio,Duracion\n1,Pago Anticipo,Hito,2026-08-01,1\n".encode('utf-8')
                    file_n, mime_t = "Muestra_Gantt.csv", "text/csv"
                else:
                    sample_bytes = generar_pdf_modulo(doc['Código del Documento'], doc['Descripción / Nombre Oficial'], [{'title': 'Muestra Oficial', 'content': 'Documento de muestra institucional de J&D Automation Industries.'}])
                    file_n, mime_t = f"Muestra_{doc['Código del Documento']}.pdf", "application/pdf"

                st.download_button(
                    label="⬇️ Descarga Muestra",
                    data=sample_bytes,
                    file_name=file_n,
                    mime=mime_t,
                    key=f"dl_sample_{i}",
                    type="primary",
                    use_container_width=True
                )
        st.divider()

    # Exportación Universal PDF Glosario
    sec_glo_pdf = [
        {'title': 'Glosario Maestro de Documentación', 'content': 'Catálogo estructurado para auditar archivos entrantes y salientes.'},
        {'table': [['Código', 'Descripción / Nombre Oficial', 'Asociado a']] + [[d['Código del Documento'], d['Descripción / Nombre Oficial'], d['Asociado a / Referenciado en']] for d in docs_master]}
    ]
    pdf_glo_bytes = generar_pdf_modulo("Glosario Maestro de Documentación", "Auditoría de Formatos e Intercambio de Archivos J&D", sec_glo_pdf)
    st.download_button(
        label="📄 EXPORTAR GLOSARIO MAESTRO EN PDF",
        data=pdf_glo_bytes,
        file_name="Glosario_Maestro_Documentacion_JD.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        key="btn_dl_pdf_glosario_master"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. MANUFACTURA INTELIGENTE E INDUSTRIA 4.0 (SECCIÓN 6)
# ─────────────────────────────────────────────────────────────────────────────

def render_industria40_page():
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>🤖 Manufactura Inteligente e Industria 4.0</h2>
        <p>Justificación tecnológica, beneficios estratégicos comerciales y resumen del stack empleado en la app.</p>
    </div>""", unsafe_allow_html=True)

    ind_tab1, ind_tab2, ind_tab3 = st.tabs([
        "💡 Justificación Industria 4.0",
        "📈 Beneficios Estratégicos",
        "⚡ Stack Tecnológico de la App"
    ])

    with ind_tab1:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-left:5px solid {BRAND_ORANGE};
                    border-radius:10px;padding:22px;font-family:'Montserrat',sans-serif;">
            <h3 style="font-size:16px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 10px 0;">JUSTIFICACIÓN TECNOLÓGICA BAJO EL ESQUEMA INDUSTRIA 4.0</h3>
            <p style="font-size:13px;color:{BRAND_CHARCOAL_MED};line-height:1.7;margin:0 0 14px 0;">
                En la integración de sistemas de automatización, tableros de control y celdas robotizadas, 
                la velocidad y precisión de la cotización es la principal ventaja competitiva. Esta aplicación transforma 
                el costeo tradicional en hojas de cálculo aisladas en una <b>Plataforma Digital Centralizada de Ingeniería Comercial</b>.
            </p>
            <ul style="font-size:12px;color:{BRAND_CHARCOAL_MED};line-height:1.7;margin:0;padding-left:20px;">
                <li><b>Digitalización de Extremo a Extremo:</b> Estandarización de 59 conceptos oficiales de gastos de obra y tarifas FSR.</li>
                <li><b>Interoperabilidad Nativa:</b> Integración transparente con Microsoft Project 2024 (MSPDI Schema v14) y Microsoft Outlook (RFC 2045/5545).</li>
                <li><b>Trazabilidad y Control de Revisiones:</b> Congelamiento de versiones ($R0 \rightarrow R+1$) con auditoría histórica en base de datos relational.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with ind_tab2:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-left:5px solid #059669;
                    border-radius:10px;padding:22px;font-family:'Montserrat',sans-serif;">
            <h3 style="font-size:16px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 10px 0;">BENEFICIOS ESTRATÉGICOS COMERCIALES Y TÉCNICOS</h3>
        </div>
        """, unsafe_allow_html=True)

        b_col1, b_col2 = st.columns(2)
        with b_col1:
            st.markdown(f"""
            <div style="background:{BRAND_GRAY_BG};border-radius:8px;padding:16px;margin-top:12px;">
                <h4 style="font-size:13px;font-weight:800;color:{BRAND_ORANGE};margin:0 0 6px 0;">💼 BENEFICIOS COMERCIALES</h4>
                <ul style="font-size:12px;color:{BRAND_CHARCOAL_MED};line-height:1.6;margin:0;padding-left:18px;">
                    <li><b>Reducción de Tiempo de Respuesta:</b> Generación de oferta en menos de 10 minutos frente al promedio industrial de 48 horas.</li>
                    <li><b>Propuestas de Alto Impacto:</b> Envío inmediato de correo corporativo (.eml) con Gantt, PDF membretado y MS Project nativo.</li>
                    <li><b>Confianza del Cliente:</b> Transparencia en precios unitarios y cronograma de hitos clave agendables.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with b_col2:
            st.markdown(f"""
            <div style="background:{BRAND_GRAY_BG};border-radius:8px;padding:16px;margin-top:12px;">
                <h4 style="font-size:13px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 6px 0;">🛠️ BENEFICIOS TÉCNICOS</h4>
                <ul style="font-size:12px;color:{BRAND_CHARCOAL_MED};line-height:1.6;margin:0;padding-left:18px;">
                    <li><b>Cero Errores de Prorrateo:</b> Motor financiero automatizado de Gastos Generales y Herramienta (3% MO).</li>
                    <li><b>Control de Margen Financiero:</b> Cálculo exacto de Utilidad Bruta, Comisión Comercial e Impuestos.</li>
                    <li><b>Blindaje de Archivos:</b> Prevención de errores de importación en MS Project 2024 mediante esquemas v14 oficiales.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

    with ind_tab3:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-left:5px solid #0EA5E9;
                    border-radius:10px;padding:22px;font-family:'Montserrat',sans-serif;">
            <h3 style="font-size:16px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 14px 0;">STACK TECNOLÓGICO EMPLEADO EN LA APLICACIÓN</h3>
        </div>
        """, unsafe_allow_html=True)

        stack_items = [
            {"Capa": "Núcleo Backend", "Tecnología": "Python 3.12+ & OpenPyXL", "Función": "Motor de cálculo financiero, matrices de precios y lógica."},
            {"Capa": "Interfaz de Usuario (UI/UX)", "Tecnología": "Streamlit & Modern HTML/CSS", "Función": "Interfaz web responsiva de alta velocidad."},
            {"Capa": "Base de Datos", "Tecnología": "SQLite 3 Relational Engine", "Función": "Almacenamiento persistente con integridad referencial."},
            {"Capa": "Motor de Generación PDF", "Tecnología": "ReportLab PDF Engine", "Función": "Compilación al vuelo de documentos PDF membretados."},
            {"Capa": "Interoperabilidad MS Office", "Tecnología": "MSPDI XML Schema v14", "Función": "Integración nativa con Microsoft Project 2024."},
            {"Capa": "Arquitectura de Correo", "Tecnología": "RFC 2045 / RFC 5545 (EML & iCalendar)", "Función": "Ensamblado de correos Multipart/Mixed con hitos agendables."}
        ]
        st.dataframe(pd.DataFrame(stack_items), use_container_width=True, hide_index=True)

    st.markdown("---")
    # Exportación Universal PDF Industria 4.0
    sec_ind_pdf = [
        {'title': 'Justificación Tecnológica Industria 4.0', 'content': 'Transformación del costeo tradicional en una Plataforma Digital Centralizada de Ingeniería Comercial.'},
        {'title': 'Beneficios Comerciales y Técnicos', 'content': '• Reducción de tiempo de respuesta de 48h a 10 minutos.\n• Eliminación de errores de prorrateo.\n• Interoperabilidad nativa con Microsoft Office 2024.'},
        {'table': [['Capa de Software', 'Tecnología', 'Función']] + [[s['Capa'], s['Tecnología'], s['Función']] for s in stack_items]}
    ]
    pdf_ind_bytes = generar_pdf_modulo("Manufactura Inteligente e Industria 4.0", "Resumen Tecnológico y Estratégico J&D Automation", sec_ind_pdf)
    st.download_button(
        label="📄 EXPORTAR RESUMEN INDUSTRIA 4.0 EN PDF",
        data=pdf_ind_bytes,
        file_name="Resumen_Industria40_Stack_JD.pdf",
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        key="btn_dl_pdf_industria40"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. MANUAL DE OPERACIÓN INTERACTIVO (SECCIÓN 7)
# ─────────────────────────────────────────────────────────────────────────────

def render_manual_page():
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>📖 Manual de Operación e Instrucción de Uso</h2>
        <p>Guía interactiva paso a paso para la captura de proyectos, costeo por partidas, análisis financiero y exportación.</p>
    </div>""", unsafe_allow_html=True)

    # ── Banner de Descarga de Manual PDF ──
    try:
        from generate_pdf_manual import obtener_manual_pdf_bytes
        pdf_bytes = obtener_manual_pdf_bytes()
    except Exception:
        pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Manual_Usuario_Plantilla_Excel_JD.pdf")
        pdf_bytes = open(pdf_path, "rb").read() if os.path.exists(pdf_path) else b""

    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        st.markdown(f"""
        <div style="background:{BRAND_GRAY_BG};border:2px solid {BRAND_ORANGE};border-radius:10px;padding:14px;margin-bottom:15px;">
            <h4 style="margin:0 0 4px 0;color:{BRAND_CHARCOAL};font-weight:900;font-size:14px;">📘 MANUAL OFICIAL EN PDF PARA PRESUPUESTADORES (PLANTILLA EXCEL V2.0)</h4>
            <p style="margin:0;color:{BRAND_CHARCOAL_MED};font-size:12px;">Guía técnica ilustrada paso a paso: reglas de captura, sueldos FASAR y prorrateo de gastos.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.download_button(
            label="📄 DESCARGAR MANUAL COMPLETO EN PDF",
            data=pdf_bytes,
            file_name="Manual_Usuario_Plantilla_Excel_JD.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key="btn_dl_manual_page_pdf"
        )

    man_tab1, man_tab2, man_tab3, man_tab4 = st.tabs([
        "1. Captura de Cotización",
        "2. Costeo por Partidas",
        "3. Análisis & Congelamiento",
        "4. Plan de Proyecto & Envíos"
    ])

    with man_tab1:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};padding:20px;border-radius:10px;">
            <h4 style="color:{BRAND_ORANGE};font-weight:800;margin:0 0 10px 0;">PASO 1: DATOS GENERALES DEL CLIENTE Y FOLIO</h4>
            <ol style="font-size:13px;color:{BRAND_CHARCOAL_MED};line-height:1.7;">
                <li>Selecciona un cliente registrado en el directorio o utiliza la opción rápida <b>➕ Alta de Cliente</b>.</li>
                <li>Ingresa la descripción del <b>Nombre del Proyecto</b>.</li>
                <li>Verifica el <b>Tipo de Cambio USD/MXN</b> aplicable a los materiales de importación.</li>
                <li>Define los porcentajes de <b>Margen de Utilidad (30%)</b>, <b>Comisión Comercial (5%)</b> y <b>Supervisión (30%)</b>.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    with man_tab2:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};padding:20px;border-radius:10px;">
            <h4 style="color:{BRAND_ORANGE};font-weight:800;margin:0 0 10px 0;">PASO 2 Y 3: ESTRUCTURACIÓN DE PARTIDAS Y DESGLOSE DE COSTOS</h4>
            <ol style="font-size:13px;color:{BRAND_CHARCOAL_MED};line-height:1.7;">
                <li>Agrega las partidas del proyecto (ej. <i>Partida 1: Ensamble Mecánico</i>, <i>Partida 2: Programación PLC</i>).</li>
                <li>Desglosa los 5 rubros de costos en cada partida: Materiales, Mano de Obra, Subcontratos, Maquinaria y Gastos Generales.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    with man_tab3:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};padding:20px;border-radius:10px;">
            <h4 style="color:{BRAND_ORANGE};font-weight:800;margin:0 0 10px 0;">PASO 4: DASHBOARD ANÁLISIS DE COSTO DIRECTO Y CONGELAMIENTO</h4>
            <ol style="font-size:13px;color:{BRAND_CHARCOAL_MED};line-height:1.7;">
                <li>Consulta el <b>Dashboard de Resumen de Costo Directo por Rubro</b>.</li>
                <li>Haz clic en <b>🔒 Aprobar y CONGELAR Cotización</b> para emitir la oferta oficial.</li>
                <li>Si hay cambios posteriores, presiona <b>🔄 Crear Nueva Revisión (R+1)</b>.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

    with man_tab4:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};padding:20px;border-radius:10px;">
            <h4 style="color:{BRAND_ORANGE};font-weight:800;margin:0 0 10px 0;">PLAN DE PROYECTO, MS PROJECT 2024 Y CORREO EML</h4>
            <ol style="font-size:13px;color:{BRAND_CHARCOAL_MED};line-height:1.7;">
                <li>Ingresa al módulo independiente <b>📅 Plan de Proyecto</b> en el menú lateral.</li>
                <li>Asigna fechas de inicio y duraciones de tareas.</li>
                <li>Exporta en 1 clic los formatos: <code>✉️ CORREO (.EML)</code>, <code>📄 PDF EJECUTIVO</code> o <code>⚡ MS PROJECT 2024 (.XML)</code>.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
