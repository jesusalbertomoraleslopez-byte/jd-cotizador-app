"""
Módulo de Autenticación, Control de Acceso y Portal de Inicio de Sesión — J&D Automation Industries
Perfiles:
- Administrador (admin / 123): Acceso total (Captura, Consulta, Edición, Mantenimiento, Borrado de Datos)
- Operador (operador / 123): Acceso limitado (Captura y Consulta únicamente; Mantenimiento restringido)
"""

import streamlit as st
import os

USERS_DB = {
    "admin": {
        "password": "123",
        "name": "Ing. David Alaniz",
        "role": "admin",
        "role_label": "👑 Administrador General"
    },
    "operador": {
        "password": "123",
        "name": "Operador de Presupuestos",
        "role": "operador",
        "role_label": "👤 Operador de Captura"
    }
}

def init_auth_state():
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'user_name' not in st.session_state:
        st.session_state['user_name'] = ""
    if 'user_role' not in st.session_state:
        st.session_state['user_role'] = "operador"
    if 'user_role_label' not in st.session_state:
        st.session_state['user_role_label'] = "👤 Operador"

def render_login_screen():
    """
    Despliega la pantalla centrada de inicio de sesión antes de dar acceso a la app.
    """
    init_auth_state()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, "assets", "logo_naranja.png")

    # Centrar la tarjeta de inicio de sesión usando columnas de Streamlit
    col_left, col_center, col_right = st.columns([1, 2.2, 1])

    with col_center:
        st.markdown(f"""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-top:6px solid #FE8C29;
                    border-radius:12px; padding:28px 24px 16px 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.08);
                    text-align:center; font-family:'Montserrat', sans-serif; margin-top: 2rem;">
        """, unsafe_allow_html=True)

        if os.path.exists(logo_path):
            st.image(logo_path, width=220)
        else:
            st.markdown("<h2 style='color:#FE8C29; margin:0;'>⚡ J&D AUTOMATION INDUSTRIES</h2>", unsafe_allow_html=True)

        st.markdown("""
            <h3 style="color:#434E62; font-size:17px; font-weight:800; margin:14px 0 4px 0;">SISTEMA DE COTIZACIONES &amp; PRECIOS UNITARIOS</h3>
            <p style="color:#8C96A6; font-size:11.5px; font-weight:600; margin:0 0 16px 0;">Acceso Restringido — Ingrese sus credenciales de usuario</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_portal_form", clear_on_submit=False):
            u_in = st.text_input("👤 Usuario", value="", placeholder="Ingresa tu usuario (ej. admin u operador)")
            p_in = st.text_input("🔑 Contraseña", value="", type="password", placeholder="••••••••")
            
            submitted = st.form_submit_button("🔐 INICIAR SESIÓN", type="primary", use_container_width=True)
            if submitted:
                u_clean = u_in.strip().lower()
                p_clean = p_in.strip()
                if u_clean in USERS_DB and USERS_DB[u_clean]["password"] == p_clean:
                    st.session_state['authenticated'] = True
                    st.session_state['user_id'] = u_clean
                    st.session_state['user_name'] = USERS_DB[u_clean]["name"]
                    st.session_state['user_role'] = USERS_DB[u_clean]["role"]
                    st.session_state['user_role_label'] = USERS_DB[u_clean]["role_label"]
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos. Verifique sus datos.")

        st.markdown("""
        <p style="text-align:center; font-size:10px; color:#94A3B8; margin-top:20px; font-family:'Montserrat',sans-serif;">
            J&D Automation Industries S.A. de C.V. &bull; Torreón, Coahuila, México.
        </p>
        """, unsafe_allow_html=True)


def render_login_sidebar():
    """
    Muestra la insignia del usuario conectado en la barra lateral con botón para cerrar sesión.
    """
    init_auth_state()
    
    st.sidebar.markdown("""
    <div style="border-top: 1px solid #5A6478; margin: 15px 0 10px 0;"></div>
    """, unsafe_allow_html=True)
    
    if st.session_state['authenticated']:
        st.sidebar.markdown(f"""
        <div style="background:#2A3447; border:1px solid #3B475D; border-radius:8px; padding:10px; margin-bottom:10px;">
            <p style="margin:0; font-size:11px; color:#FE8C29; font-weight:800;">{st.session_state['user_role_label']}</p>
            <p style="margin:2px 0 0 0; font-size:12px; color:#FFFFFF; font-weight:700;">{st.session_state['user_name']}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, key="btn_logout_side"):
            st.session_state['authenticated'] = False
            st.session_state['user_id'] = None
            st.session_state['user_name'] = ""
            st.session_state['user_role'] = "operador"
            st.session_state['user_role_label'] = "👤 Operador"
            st.rerun()


def is_admin():
    init_auth_state()
    return st.session_state.get('user_role') == 'admin'


def check_admin_permission():
    if not is_admin():
        st.warning("🔒 ACCESO RESTRINGIDO — Este módulo o acción requiere perfil de ADMINISTRADOR.")
        st.info("Inicia sesión con la cuenta de Administrador para desbloquear este módulo.")
        return False
    return True
