import streamlit as st
import os
import base64
from config import CUSTOM_CSS, APP_TITLE, COMPANY_NAME, BRAND_ORANGE, BRAND_CHARCOAL
from database.models import init_db
from database.db_manager import seed_initial_catalogs
from modules.dashboard_analisis import render_dashboard_analisis
from modules.catalogos import render_catalogos_page
from modules.cotizador_editor import render_cotizador_editor
from modules.wizard_cotizador import render_wizard_cotizador
from modules.tpu_generator import render_tpu_generator
from modules.excel_importer import render_excel_importer
from modules.clientes import render_clientes_page

# ─── ASSETS PATHS ───
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
FAVICON_PATH = os.path.join(ASSETS_DIR, "favicon_512.png")
LOGO_WHITE   = os.path.join(ASSETS_DIR, "logo_blanco.png")
LOGO_CORP    = os.path.join(ASSETS_DIR, "logo_corporativo.png")
LOGO_ORANGE  = os.path.join(ASSETS_DIR, "logo_naranja.png")

# ─── PAGE CONFIG ───
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── FAVICON DINÁMICO ───
if os.path.exists(FAVICON_PATH):
    with open(FAVICON_PATH, "rb") as f:
        fav_b64 = base64.b64encode(f.read()).decode("utf-8")
    st.markdown(f"""
    <head>
        <link rel="icon" type="image/png" href="data:image/png;base64,{fav_b64}">
        <link rel="shortcut icon" type="image/png" href="data:image/png;base64,{fav_b64}">
        <link rel="apple-touch-icon" href="data:image/png;base64,{fav_b64}">
    </head>
    """, unsafe_allow_html=True)

# ─── INYECTAR CSS CORPORATIVO OFICIAL ───
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ─── INICIALIZAR BASE DE DATOS Y DATOS SEMILLA ───
try:
    init_db()
    seed_initial_catalogs()
except Exception as _e:
    pass

# ─── SIDEBAR CORPORATIVO J&D ───
with st.sidebar:
    if os.path.exists(LOGO_ORANGE):
        st.image(LOGO_ORANGE, width=180)
    else:
        st.markdown(f"## ⚡ **{COMPANY_NAME}**")

    st.markdown(f"""
    <div style="border-top: 2px solid {BRAND_ORANGE}; margin: 10px 0 16px 0;"></div>
    <p style="color: #CBD5E1; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin: 0 0 12px 0;">
        SISTEMA DE COTIZACIONES
    </p>
    """, unsafe_allow_html=True)

    menu_option = st.radio(
        "Navegación",
        [
            "1. Dashboard ANÁLISIS",
            "2. Importador Excel",
            "3. Modificador de Cotizaciones",
            "4. Plan de Proyecto",
            "5. Cierre y Entregable",
            "6. Tarjetas TPU",
            "7. Mantenimiento del Sistema",
            "8. SGC (Gestión de Calidad)",
            "9. Glosario de Documentos (PDF)",
            "10. Industria 4.0",
            "11. Manual de Operación (PDF)"
        ],
        label_visibility="collapsed"
    )

    st.markdown(f"""
    <div style="border-top: 1px solid #5A6478; margin: 20px 0 12px 0;"></div>
    <p style="color: #8C96A6; font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin: 0;">
        J&D Automation Industries<br>
        <span style="color: {BRAND_ORANGE}; font-size: 10px;">Cotizaciones & Precios Unitarios v1.0</span>
    </p>
    """, unsafe_allow_html=True)




# ─── RENDER_HEADER CORPORATIVO ───
def render_header(title, subtitle=""):
    logo_path = LOGO_CORP if os.path.exists(LOGO_CORP) else None
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        if logo_path:
            st.image(logo_path, width=140)
    with col_title:
        st.markdown(f"""
        <div style="border-left: 4px solid {BRAND_ORANGE}; padding-left: 18px; margin-top: 8px;">
            <h2 style="margin: 0; color: {BRAND_CHARCOAL}; font-family: 'Montserrat', sans-serif; font-size: 22px; font-weight: 800;">{title}</h2>
            <p style="margin: 4px 0 0 0; color: #8C96A6; font-family: 'Montserrat', sans-serif; font-size: 12px; font-weight: 500;">{subtitle}</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<hr style='border: 1px solid #E2E8F0; margin: 12px 0 20px 0;'>", unsafe_allow_html=True)

# ─── ENRUTAMIENTO POR MÓDULO ───
if "Dashboard" in menu_option:
    render_header("Dashboard ANÁLISIS de Cotización",
                  "Resumen financiero ejecutivo: costos, márgenes, comisión y partidas ponderadas")
    render_dashboard_analisis()

elif "Importador" in menu_option:
    render_header("Importador de Cotizaciones Excel",
                  "Carga automática de archivos .xlsx con hoja ANALISIS, Material, M.O., Subcontratos, Maquinaria y Gastos")
    render_excel_importer()

elif "Modificador" in menu_option:
    render_header("Modificador Técnico de Cotizaciones (Supervisor)",
                  "Ajuste directo de cantidades, sueldos y precios en tablas interactivas con bitácora de auditoría de cambios")
    render_cotizador_editor()

elif "Plan de Proyecto" in menu_option:
    render_header("Sección de Planeación Inicial (Plan de Proyecto)",
                  "Borrador rápido de diagrama de Gantt y exportación oficial a Microsoft Project (.xml / .csv)")
    from modules.plan_proyecto import render_plan_proyecto
    render_plan_proyecto()

elif "Cierre" in menu_option:
    render_header("Módulo de Cierre y Entrega de Cotización",
                  "Previsualización, supervisión y descarga en 1 clic del paquete completo de entregables (PDF, Excel y Correo .EML)")
    from modules.cierre_entrega import render_cierre_entrega
    render_cierre_entrega()

elif "TPU" in menu_option:
    render_header("Tarjetas de Precios Unitarios (TPU)",
                  "Desglose ejecutivo del costo unitario y precio de venta por concepto")
    render_tpu_generator()

elif "Mantenimiento" in menu_option:
    render_header("Módulo de Mantenimiento y Administración General",
                  "Centro unificado para la gestión de base de datos, clientes, catálogos base y modificación de cotizaciones")
    from modules.mantenimiento_sgc import render_mantenimiento_page
    render_mantenimiento_page()


elif "SGC" in menu_option:
    render_header("Sistema de Gestión de Calidad (SGC)",
                  "Procedimientos institucionales normados y carga de documentación ISO 9001:2015")
    from modules.mantenimiento_sgc import render_sgc_page
    render_sgc_page()

elif "Glosario" in menu_option:
    render_header("Glosario y Auditoría Master de Documentación",
                  "Tabla maestra auditable de formatos generados e intercambiados por el sistema con descargas de muestras")
    from modules.mantenimiento_sgc import render_glosario_page
    render_glosario_page()

elif "Industria" in menu_option:
    render_header("Manufactura Inteligente e Industria 4.0",
                  "Justificación tecnológica, beneficios estratégicos comerciales y resumen del stack")
    from modules.mantenimiento_sgc import render_industria40_page
    render_industria40_page()

elif "Manual" in menu_option:
    render_header("Manual de Operación e Instrucción de Uso",
                  "Guía de usuario interactiva paso a paso para la captura y operación del sistema")
    from modules.mantenimiento_sgc import render_manual_page
    render_manual_page()





