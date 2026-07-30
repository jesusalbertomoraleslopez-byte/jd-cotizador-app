"""
Módulo de Autenticación, Control de Acceso y Roles de Usuario — J&D Automation Industries
Perfiles:
- Administrador: Acceso total (Captura, Consulta, Edición, Mantenimiento, Borrado de Datos)
- Operador: Acceso limitado (Captura y Consulta únicamente; Mantenimiento restringido)
"""

import streamlit as st

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

def render_login_sidebar():
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
    else:
        with st.sidebar.expander("🔑 Iniciar Sesión (Roles)", expanded=True):
            user_input = st.text_input("Usuario", "admin", key="login_user_in")
            pass_input = st.text_input("Contraseña", "123", type="password", key="login_pass_in")
            
            if st.button("🔓 Ingresar", type="primary", use_container_width=True, key="btn_login_submit"):
                u_clean = user_input.strip().lower()
                if u_clean in USERS_DB and USERS_DB[u_clean]["password"] == pass_input.strip():
                    st.session_state['authenticated'] = True
                    st.session_state['user_id'] = u_clean
                    st.session_state['user_name'] = USERS_DB[u_clean]["name"]
                    st.session_state['user_role'] = USERS_DB[u_clean]["role"]
                    st.session_state['user_role_label'] = USERS_DB[u_clean]["role_label"]
                    st.success(f"¡Bienvenido {USERS_DB[u_clean]['name']}!")
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")

def is_admin():
    init_auth_state()
    return st.session_state.get('user_role') == 'admin'

def check_admin_permission():
    if not is_admin():
        st.warning("🔒 ACCESO RESTRINGIDO — Este módulo o acción requiere perfil de ADMINISTRADOR.")
        st.info("Utiliza el panel lateral para iniciar sesión con la cuenta de Administrador.")
        return False
    return True
