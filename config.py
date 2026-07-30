# Configuración Global y Sistema de Diseño OFICIAL para J&D Automation Industries

APP_TITLE = "J&D Automation Industries - Cotizaciones & TPU"
COMPANY_NAME = "J&D Automation Industries"

# ─────────────────────────────────────────────────────────────────
# PALETA OFICIAL J&D AUTOMATION INDUSTRIES
# Auditada de la aplicación de Administración (jd_automation_app)
# ─────────────────────────────────────────────────────────────────
BRAND_ORANGE      = "#FE8C29"   # UT Orange - Botones, acentos, tabs activos, métricas
BRAND_ORANGE_DARK = "#e0771b"   # Orange Hover
BRAND_CHARCOAL    = "#434E62"   # Sidebar, títulos, texto principal
BRAND_CHARCOAL_MED = "#8C96A6"  # Texto secundario / labels
BRAND_CHARCOAL_LIGHT = "#CBD5E1"  # Bordes suaves
BRAND_GRAY_BG     = "#EDEDED"   # Fondo general de la app
BRAND_WHITE       = "#FFFFFF"   # Tarjetas, paneles blancos
BRAND_LIGHT_BG    = "#FAFAFA"   # Encabezados de expanders
BRAND_HOVER_BG    = "#FFF8F3"   # Hover en expanders
BRAND_BORDER_LIGHT = "#E2E8F0"  # Bordes de tarjetas
BRAND_SUCCESS     = "#10B981"   # Verde éxito
BRAND_DANGER      = "#EF4444"   # Rojo error

DEFAULT_TIPO_CAMBIO = 18.00
DEFAULT_MARGEN = 0.30
DEFAULT_COMISION = 0.05
DEFAULT_SUPERVISION = 0.30
DEFAULT_HERRAMIENTA = 0.03

# ─────────────────────────────────────────────────────────────────
# CSS CORPORATIVO OFICIAL J&D AUTOMATION (idéntico al app admin)
# ─────────────────────────────────────────────────────────────────
CUSTOM_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;900&display=swap');

    /* ─── OCULTAR FRANJA BLANCA SUPERIOR, MENÚ DE 3 PUNTOS, BOTÓN FORK Y FOOTER ─── */
    header[data-testid="stHeader"],
    div[data-testid="stHeader"],
    .stAppHeader,
    [data-testid="stAppHeader"],
    #MainMenu,
    footer,
    header,
    div[data-testid="stStatusWidget"],
    .stToolbar,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stActionButtonIcon"] {{
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        padding: 0px !important;
        margin: 0px !important;
    }}

    /* Reducir espacio superior vacante de la página principal */
    .block-container, [data-testid="stMainBlockContainer"] {{
        padding-top: 1rem !important;
    }}

    /* ─── TIPOGRAFÍA CORPORATIVA MONTSERRAT ─── */
    html, body, .stWidget, .stMarkdown, p, li, label, input, button, span, div {{
        font-family: 'Montserrat', 'Inter', sans-serif !important;
    }}

    /* ─── PRESERVAR FUENTES DE ICONOS DE STREAMLIT (EXPANDERS Y OTROS) ─── */
    [data-testid="stExpanderToggleIcon"],
    [data-testid="stExpanderIcon"],
    [data-testid="stIcon"],
    summary [data-testid="stIcon"],
    i, .material-symbols-outlined, .material-icons {{
        font-family: 'Material Symbols Outlined', 'Material Icons', sans-serif !important;
    }}

    /* ─── FONDO PRINCIPAL GRIS CORPORATIVO ─── */
    .stApp {{
        background-color: {BRAND_GRAY_BG} !important;
    }}

    /* ─── TÍTULOS Y ENCABEZADOS EN CHARCOAL ─── */
    h1, h2, h3, h4, h5, h6 {{
        color: {BRAND_CHARCOAL} !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
    }}

    /* ─── SIDEBAR CHARCOAL CORPORATIVO Y PILLS DE NAVEGACIÓN ─── */
    section[data-testid="stSidebar"] {{
        background-color: {BRAND_CHARCOAL} !important;
        border-right: 1px solid #333F53 !important;
    }}
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {{
        color: {BRAND_WHITE} !important;
        font-family: 'Montserrat', sans-serif !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
        color: {BRAND_WHITE} !important;
        font-weight: 700 !important;
    }}
    /* Radio buttons del sidebar en formato Pills */
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label {{
        color: {BRAND_WHITE} !important;
        font-size: 12.5px !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        padding: 6px 10px !important;
        margin-bottom: 2px !important;
        transition: all 0.2s ease !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover {{
        background-color: rgba(254, 140, 41, 0.18) !important;
        color: {BRAND_ORANGE} !important;
    }}

    /* ─── BOTONES PRIMARIOS EN ORANGE J&D ─── */
    div.stButton > button:first-child,
    div.stFormSubmitButton > button:first-child {{
        background-color: {BRAND_ORANGE} !important;
        color: {BRAND_WHITE} !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 10px 24px !important;
        box-shadow: 0 3px 8px rgba(254, 140, 41, 0.35) !important;
        transition: transform 0.15s, background-color 0.2s, box-shadow 0.2s !important;
    }}
    div.stButton > button:first-child:hover,
    div.stFormSubmitButton > button:first-child:hover {{
        background-color: {BRAND_ORANGE_DARK} !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 5px 12px rgba(254, 140, 41, 0.45) !important;
    }}

    /* ─── BOTONES DE DESCARGA E INFOS EN AZUL INTENSO CORPORATIVO ─── */
    .stDownloadButton > button,
    button[kind="primaryDownload"] {{
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 800 !important;
        font-size: 12.5px !important;
        border: 1px solid #1D4ED8 !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
        transition: all 0.2s ease !important;
    }}
    .stDownloadButton > button:hover,
    button[kind="primaryDownload"]:hover {{
        background: linear-gradient(135deg, #1D4ED8 0%, #1E40AF 100%) !important;
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5) !important;
        transform: translateY(-1px) !important;
        color: #FFFFFF !important;
    }}
    div.stButton > button:first-child:active,
    div.stFormSubmitButton > button:first-child:active {{
        transform: scale(0.98) !important;
    }}

    /* ─── PESTAÑAS (TABS) EN ORANGE ─── */
    button[data-baseweb="tab"] {{
        font-size: 13.5px !important;
        font-weight: 700 !important;
        color: {BRAND_CHARCOAL} !important;
        font-family: 'Montserrat', sans-serif !important;
        padding: 10px 18px !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {BRAND_ORANGE} !important;
        border-bottom-color: {BRAND_ORANGE} !important;
        border-bottom-width: 3px !important;
    }}

    /* ─── MÉTRICAS EJECUTIVAS ─── */
    div[data-testid="stMetric"] {{
        background-color: {BRAND_WHITE} !important;
        border: 1px solid {BRAND_BORDER_LIGHT} !important;
        border-left: 5px solid {BRAND_ORANGE} !important;
        padding: 16px !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 10px rgba(67, 78, 98, 0.06) !important;
    }}
    div[data-testid="stMetricValue"] > div {{
        color: {BRAND_CHARCOAL} !important;
        font-weight: 800 !important;
        font-family: 'Montserrat', sans-serif !important;
    }}
    div[data-testid="stMetricLabel"] > div {{
        color: {BRAND_CHARCOAL_MED} !important;
        font-size: 11.5px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.8px !important;
        font-weight: 700 !important;
    }}

    /* ─── TARJETAS INFORMATIVAS PERSONALIZADAS J&D ─── */
    .jd-metric-card {{
        background-color: {BRAND_WHITE};
        border: 1px solid {BRAND_BORDER_LIGHT};
        border-left: 5px solid {BRAND_ORANGE};
        border-radius: 8px;
        padding: 18px 20px;
        box-shadow: 0 4px 10px rgba(67, 78, 98, 0.06);
        margin-bottom: 15px;
    }}
    .jd-metric-label {{
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: {BRAND_CHARCOAL_MED};
        margin-bottom: 4px;
        font-weight: 700;
    }}
    .jd-metric-value {{
        font-size: 1.75rem;
        font-weight: 800;
        color: {BRAND_CHARCOAL};
        font-family: 'Montserrat', sans-serif;
    }}
    .jd-metric-orange {{
        color: {BRAND_ORANGE} !important;
    }}
    .jd-metric-subtext {{
        font-size: 0.78rem;
        color: {BRAND_CHARCOAL_MED};
        margin-top: 4px;
        font-weight: 600;
    }}

    /* ─── HEADER CORPORATIVO CON LÍNEA ORANGE ─── */
    .jd-section-header {{
        border-left: 4px solid {BRAND_ORANGE};
        padding-left: 14px;
        margin-bottom: 18px;
    }}
    .jd-section-header h2, .jd-section-header h3 {{
        margin: 0;
        color: {BRAND_CHARCOAL} !important;
        font-size: 20px !important;
        font-weight: 800 !important;
    }}
    .jd-section-header p {{
        margin: 3px 0 0 0;
        color: {BRAND_CHARCOAL_MED};
        font-size: 12.5px;
        font-weight: 500;
    }}

    /* ─── EXPANDERS CORPORATIVOS ─── */
    [data-testid="stExpander"] {{
        background-color: {BRAND_WHITE} !important;
        border: 1px solid {BRAND_BORDER_LIGHT} !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03) !important;
        margin-bottom: 12px !important;
    }}
    [data-testid="stExpander"] summary {{
        background-color: {BRAND_LIGHT_BG} !important;
        color: {BRAND_CHARCOAL} !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        font-size: 13.5px !important;
        padding: 12px 16px !important;
        border-radius: 8px !important;
    }}
    [data-testid="stExpander"] summary:hover {{
        background-color: {BRAND_HOVER_BG} !important;
        color: {BRAND_ORANGE} !important;
    }}

    /* ─── SELECTBOX Y DROPDOWNS ─── */
    [data-baseweb="select"] > div {{
        background-color: {BRAND_WHITE} !important;
        border: 1px solid {BRAND_CHARCOAL_LIGHT} !important;
        border-radius: 6px !important;
        color: {BRAND_CHARCOAL} !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }}
    [data-baseweb="select"] > div:hover {{
        border-color: {BRAND_ORANGE} !important;
    }}

    /* ─── ALERTAS E INFO BOXES ─── */
    div[data-testid="stAlert"] {{
        border-radius: 8px !important;
        font-family: 'Montserrat', sans-serif !important;
    }}

    /* ─── FILE UPLOADER CORPORATIVO ─── */
    section[data-testid="stFileUploaderDropzone"],
    div[data-testid="stFileUploaderDropzone"] {{
        background-color: {BRAND_WHITE} !important;
        border: 2px dashed {BRAND_ORANGE} !important;
        border-radius: 10px !important;
        padding: 14px !important;
    }}
    section[data-testid="stFileUploaderDropzone"]:hover,
    div[data-testid="stFileUploaderDropzone"]:hover {{
        border-color: {BRAND_ORANGE_DARK} !important;
        background-color: {BRAND_HOVER_BG} !important;
    }}

    /* ─── DATAFRAMES / TABLAS ─── */
    .stDataFrame thead th {{
        background-color: {BRAND_CHARCOAL} !important;
        color: {BRAND_WHITE} !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
    }}

    /* ─── INPUTS / FORMS ─── */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {{
        border-radius: 6px !important;
        border: 1px solid {BRAND_CHARCOAL_LIGHT} !important;
        font-family: 'Montserrat', sans-serif !important;
        font-size: 13px !important;
    }}
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {{
        border-color: {BRAND_ORANGE} !important;
        box-shadow: 0 0 0 2px rgba(254,140,41,0.15) !important;
    }}

    /* ─── DIVIDERS CON COLOR ─── */
    hr {{
        border: 1px solid {BRAND_BORDER_LIGHT} !important;
    }}
</style>
"""

# ─────────────────────────────────────────────────────────────────
# CARPETA CENTRALIZADA DE IMAGEN CORPORATIVA Y MARCA J&D
# ─────────────────────────────────────────────────────────────────
import os

GLOBAL_BRAND_ASSETS_DIR = r"C:\Users\albertol\JD_Automation_Brand_Assets"

def get_brand_asset_path(filename: str) -> str:
    """
    Busca el archivo de imagen corporativa en la carpeta centralizada compartida
    C:\\Users\\albertol\\JD_Automation_Brand_Assets (y sus subcarpetas Logos, Membretes, etc.),
    y si no lo encuentra, recae en la carpeta local 'assets/' del proyecto.
    """
    if not filename:
        return ""
    
    # 1. Buscar en raíz de la carpeta centralizada
    central_path = os.path.join(GLOBAL_BRAND_ASSETS_DIR, filename)
    if os.path.exists(central_path):
        return central_path
        
    # 2. Buscar en subcarpetas de la centralizada
    for sub in ["Logos", "Membretes", "Certificaciones", "Firmas"]:
        sub_path = os.path.join(GLOBAL_BRAND_ASSETS_DIR, sub, filename)
        if os.path.exists(sub_path):
            return sub_path
            
    # 3. Buscar en assets local del proyecto
    local_base = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(local_base, "assets", filename)
    if os.path.exists(local_path):
        return local_path
        
    return central_path
