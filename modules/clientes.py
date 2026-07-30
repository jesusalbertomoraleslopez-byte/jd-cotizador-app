"""
Módulo de Gestión de Clientes — J&D Automation Industries
Directorio corporativo J&D + Alta con botón para pegar imagen desde Portapapeles (Ctrl+V) + Contactos + Ingenieros J&D.
"""
import streamlit as st
import os
import base64
import uuid
from database.models import get_connection, init_db
from config import (BRAND_ORANGE, BRAND_CHARCOAL, BRAND_CHARCOAL_MED,
                    BRAND_WHITE, BRAND_BORDER_LIGHT, BRAND_GRAY_BG,
                    BRAND_SUCCESS, BRAND_DANGER)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "client_logos")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_clientes(filtro=""):
    conn = get_connection(); cur = conn.cursor()
    if filtro:
        cur.execute("""SELECT * FROM clientes WHERE activo=1 AND
                       (nombre LIKE ? OR acronimo LIKE ? OR ciudad LIKE ? OR rfc LIKE ?)
                       ORDER BY nombre""",
                    (f"%{filtro}%", f"%{filtro}%", f"%{filtro}%", f"%{filtro}%"))
    else:
        cur.execute("SELECT * FROM clientes WHERE activo=1 ORDER BY nombre")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows


def _get_contactos(cliente_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM clientes_contactos WHERE cliente_id=? ORDER BY es_principal DESC, nombre",
                (cliente_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows


def _badge(text, color=None):
    c = color or BRAND_ORANGE
    return (f"<span style='background:{c}1A;color:{c};font-size:11px;font-weight:800;"
            f"padding:3px 10px;border-radius:12px;border:1px solid {c}33;"
            f"font-family:Montserrat,sans-serif;'>{text}</span>")


# ─────────────────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def render_clientes_page():
    init_db()

    tab_lista, tab_nuevo, tab_ingenieros = st.tabs([
        "🏢 Directorio de Clientes",
        "➕ Alta de Nuevo Cliente",
        "👷 Ingenieros J&D & Folio",
    ])

    with tab_lista:
        _render_directorio()

    with tab_nuevo:
        _render_alta_cliente()

    with tab_ingenieros:
        _render_ingenieros()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: DIRECTORIO DE CLIENTES (TARJETAS CORPORATIVAS J&D)
# ─────────────────────────────────────────────────────────────────────────────

def _render_directorio():
    col_search, col_count = st.columns([4, 1])
    with col_search:
        filtro = st.text_input("🔍 Buscar cliente", placeholder="Escribe nombre, acrónimo, RFC o ciudad…",
                               key="search_client_dir", label_visibility="collapsed")
    clientes = _get_clientes(filtro)
    with col_count:
        st.markdown(f"<div style='padding-top:8px;text-align:right;font-size:13px;"
                    f"color:{BRAND_CHARCOAL_MED};font-weight:700;'>{len(clientes)} empresas</div>",
                    unsafe_allow_html=True)

    if not clientes:
        st.info("No se encontraron empresas clientes. Registra una en la pestaña **➕ Alta de Nuevo Cliente**.")
        return

    if "sel_client_detail" not in st.session_state:
        st.session_state.sel_client_detail = None

    for c in clientes:
        _render_cliente_card_clean(c)


def _render_cliente_card_clean(c):
    """Tarjeta corporativa limpia sin el expander defectuoso."""
    cid = c['id']
    acr = (c.get('acronimo') or '—').upper()
    nombre = c['nombre']
    ciudad = f"{c.get('ciudad','')}, {c.get('estado','')}".strip(" ,") or (c.get('estado') or '—')
    rfc = c.get('rfc') or '—'
    ind = c.get('industria') or 'General'
    contactos = _get_contactos(cid)
    n_contactos = len(contactos)
    logo = c.get('logo_path')

    is_open = (st.session_state.sel_client_detail == cid)

    # Contenedor de la tarjeta
    st.markdown(f"""
    <div style="
        background:{BRAND_WHITE};
        border:1px solid {BRAND_BORDER_LIGHT};
        border-left:6px solid {BRAND_ORANGE};
        border-radius:10px;
        padding:14px 20px;
        margin-top:12px;
        box-shadow:0 2px 5px rgba(0,0,0,0.03);
        font-family:'Montserrat',sans-serif;
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="background:{BRAND_CHARCOAL};color:#fff;border-radius:8px;
                            padding:8px 14px;text-align:center;min-width:65px;">
                    <span style="font-size:9px;font-weight:800;color:{BRAND_ORANGE};
                                 text-transform:uppercase;display:block;">CLAVE</span>
                    <span style="font-size:18px;font-weight:900;letter-spacing:1px;">{acr}</span>
                </div>
                <div>
                    <span style="font-size:16px;font-weight:800;color:{BRAND_CHARCOAL};">{nombre}</span>
                    <div style="display:flex;gap:12px;align-items:center;margin-top:3px;font-size:12px;color:{BRAND_CHARCOAL_MED};flex-wrap:wrap;">
                        <span>📍 {ciudad}</span>
                        <span>•</span>
                        <span>📄 RFC: <b>{rfc}</b></span>
                        <span>•</span>
                        <span>🏭 {ind}</span>
                    </div>
                </div>
            </div>
            <div style="display:flex;align-items:center;gap:16px;">
                <span style="background:{BRAND_GRAY_BG};color:{BRAND_CHARCOAL_MED};
                             font-size:11px;font-weight:700;padding:4px 10px;border-radius:12px;">
                    👤 {n_contactos} contacto{'s' if n_contactos!=1 else ''}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Botones de interacción por cliente
    c_btn1, c_btn2, c_btn3 = st.columns([2.5, 2.5, 2.5])

    btn_label = "🔼 Ocultar Detalle" if is_open else "🔽 Ver Detalle y Contactos"
    if c_btn1.button(btn_label, key=f"tog_c_{cid}", use_container_width=True):
        st.session_state.sel_client_detail = None if is_open else cid
        st.rerun()

    if c_btn2.button("✏️ Editar Empresa", key=f"btn_edit_emp_{cid}", use_container_width=True):
        st.session_state.sel_client_detail = cid
        st.session_state[f"show_edit_emp_{cid}"] = not st.session_state.get(f"show_edit_emp_{cid}", False)
        st.rerun()

    if c_btn3.button("➕ Agregar Contacto", key=f"btn_addcon_{cid}", use_container_width=True):
        st.session_state.sel_client_detail = cid
        st.session_state[f"show_form_con_{cid}"] = True
        st.rerun()

    # Si está abierto, mostrar desglose limpio
    if is_open:
        st.markdown(f"""
        <div style="background:#FAFAFA;border:1px solid {BRAND_BORDER_LIGHT};border-top:none;
                    border-radius:0 0 10px 10px;padding:18px 22px;margin-bottom:12px;
                    font-family:'Montserrat',sans-serif;">
        """, unsafe_allow_html=True)

        # Formulario de edición si se activó
        if st.session_state.get(f"show_edit_emp_{cid}", False):
            st.markdown(f"<p style='font-size:12px;font-weight:800;text-transform:uppercase;color:{BRAND_ORANGE};margin:0 0 10px 0;'>✏️ EDITAR DATOS DE {nombre.upper()}</p>", unsafe_allow_html=True)
            _form_editar_cliente(c)
            st.markdown(f"<hr style='border:1px dashed {BRAND_BORDER_LIGHT};margin:14px 0;'>", unsafe_allow_html=True)

        d1, d2, d3 = st.columns([3, 3, 2])
        with d1:
            st.markdown(f"**Dirección Fiscal:** {c.get('direccion_fiscal','—')}")
            st.markdown(f"**Ciudad / Estado:** {ciudad}")
            st.markdown(f"**País:** {c.get('pais','México')}")
        with d2:
            st.markdown(f"**Email Empresa:** {c.get('email','—')}")
            st.markdown(f"**Teléfono:** {c.get('telefono','—')}")
            if c.get('sitio_web'):
                st.markdown(f"**Sitio Web:** [{c['sitio_web']}]({c['sitio_web']})")
        with d3:
            if logo and os.path.exists(logo):
                st.image(logo, width=120, caption="Logo Cliente")
            if c.get('notas'):
                st.markdown(f"📝 _{c['notas']}_")

        # ── CONTACTOS ────────────────────────────────────────────────────────
        st.markdown(f"<hr style='border:1px solid {BRAND_BORDER_LIGHT};margin:14px 0 10px 0;'>",
                    unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                    f"color:{BRAND_ORANGE};margin:0 0 8px 0;'>👥 CONTACTOS DE LA EMPRESA</p>",
                    unsafe_allow_html=True)

        if contactos:
            cw = [2.5, 2, 2, 1.8, 1.6, 1.2, 0.5]
            ch = ["Nombre Completo", "Cargo", "Departamento", "Email", "Celular", "Iniciales", "✕"]
            cols_h = st.columns(cw)
            for col, lbl in zip(cols_h, ch):
                col.markdown(f"<p style='font-size:10px;font-weight:800;text-transform:uppercase;"
                             f"color:{BRAND_CHARCOAL_MED};margin:4px 0 2px 0;'>{lbl}</p>",
                             unsafe_allow_html=True)

            for con in contactos:
                star = "⭐ " if con.get('es_principal') else ""
                rc = st.columns(cw)
                rc[0].markdown(f"<p style='font-size:13px;font-weight:700;color:{BRAND_CHARCOAL};margin:3px 0;'>"
                               f"{star}{con['nombre']} {con.get('apellido','')}</p>", unsafe_allow_html=True)
                rc[1].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:3px 0;'>{con.get('cargo','—')}</p>", unsafe_allow_html=True)
                rc[2].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:3px 0;'>{con.get('departamento','—')}</p>", unsafe_allow_html=True)
                rc[3].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:3px 0;'>{con.get('email','—')}</p>", unsafe_allow_html=True)
                rc[4].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:3px 0;'>{con.get('celular','—')}</p>", unsafe_allow_html=True)
                rc[5].markdown(f"<p style='font-size:13px;font-weight:800;color:{BRAND_ORANGE};margin:3px 0;'>{con.get('iniciales','—')}</p>", unsafe_allow_html=True)
                if rc[6].button("✕", key=f"del_con_{con['id']}"):
                    conn = get_connection()
                    conn.execute("DELETE FROM clientes_contactos WHERE id=?", (con['id'],))
                    conn.commit(); conn.close(); st.rerun()
        else:
            st.markdown(f"<p style='color:{BRAND_CHARCOAL_MED};font-size:12px;font-style:italic;'>Aún no hay contactos registrados para esta empresa.</p>",
                        unsafe_allow_html=True)

        # Formulario nuevo contacto si está activo
        if st.session_state.get(f"show_form_con_{cid}", False):
            st.markdown(f"<hr style='border:1px dashed {BRAND_ORANGE}77;margin:12px 0;'>", unsafe_allow_html=True)
            st.markdown(f"**➕ Agregar nuevo contacto a {nombre}**")
            _form_nuevo_contacto(cid)

        # Eliminar / Desactivar cliente
        st.markdown(f"<hr style='border:1px solid {BRAND_BORDER_LIGHT};margin:12px 0 8px 0;'>", unsafe_allow_html=True)
        if st.button("🗑️ Desactivar Cliente", key=f"deact_{cid}"):
            conn = get_connection()
            conn.execute("UPDATE clientes SET activo=0 WHERE id=?", (cid,))
            conn.commit(); conn.close()
            st.session_state.sel_client_detail = None
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)



def _form_editar_cliente(c):
    cid = c['id']
    with st.form(f"form_edit_emp_{cid}"):
        e1, e2, e3 = st.columns([4, 1.8, 2.2])
        with e1: nom_e = st.text_input("Razón Social / Nombre *", value=c.get('nombre',''))
        with e2: acr_e = st.text_input("Acrónimo / Clave *", value=c.get('acronimo',''), max_chars=6)
        with e3: ind_e = st.selectbox("Industria", INDUSTRIAS, index=INDUSTRIAS.index(c['industria']) if c.get('industria') in INDUSTRIAS else 0)

        e4, e5, e6 = st.columns([2, 2, 2])
        with e4: rfc_e = st.text_input("RFC", value=c.get('rfc',''))
        with e5: web_e = st.text_input("Sitio Web", value=c.get('sitio_web',''))
        with e6: eml_e = st.text_input("Email Principal", value=c.get('email',''))

        e7, e8, e9 = st.columns([2, 2, 2])
        with e7: tel_e = st.text_input("Teléfono", value=c.get('telefono',''))
        with e8: dir_e = st.text_input("Dirección Fiscal", value=c.get('direccion_fiscal',''))
        with e9: ciu_e = st.text_input("Ciudad", value=c.get('ciudad',''))

        e10, e11 = st.columns([2, 4])
        with e10: est_e = st.text_input("Estado", value=c.get('estado',''))
        with e11: not_e = st.text_area("Notas / Observaciones", value=c.get('notas',''), height=50)

        if st.form_submit_button("💾 Guardar Cambios de la Empresa", type="primary"):
            if nom_e.strip() and acr_e.strip():
                conn = get_connection()
                conn.execute("""UPDATE clientes SET
                                nombre=?, acronimo=?, rfc=?, industria=?, sitio_web=?,
                                email=?, telefono=?, direccion_fiscal=?, ciudad=?,
                                estado=?, notas=? WHERE id=?""",
                             (nom_e.strip(), acr_e.strip().upper(), rfc_e, ind_e, web_e,
                              eml_e, tel_e, dir_e, ciu_e, est_e, not_e, cid))
                conn.commit(); conn.close()
                st.session_state[f"show_edit_emp_{cid}"] = False
                st.success("✅ Cambios guardados correctamente.")
                st.rerun()
            else:
                st.error("Nombre y Acrónimo son requeridos.")


def _form_nuevo_contacto(cliente_id):
    with st.form(f"form_con_{cliente_id}"):
        r1a, r1b, r1c = st.columns([2, 2, 1.5])
        with r1a: nom = st.text_input("Nombre *")
        with r1b: ape = st.text_input("Apellido")
        with r1c: ini = st.text_input("Iniciales", max_chars=5, help="Ej: DS, RG — para el folio de cotización")

        r2a, r2b, r2c = st.columns([2, 2, 2])
        with r2a: cargo = st.text_input("Cargo / Puesto")
        with r2b: depto = st.text_input("Departamento")
        with r2c: email = st.text_input("Email")

        r3a, r3b, r3c = st.columns([2, 2, 1])
        with r3a: tel_of = st.text_input("Teléfono Oficina")
        with r3b: cel    = st.text_input("Celular")
        with r3c: princ  = st.checkbox("Contacto Principal")

        notas_c = st.text_area("Notas del Contacto", height=60)

        if st.form_submit_button("💾 Guardar Contacto", type="primary"):
            if nom.strip():
                conn = get_connection()
                conn.execute("""INSERT INTO clientes_contactos
                                (cliente_id,nombre,apellido,cargo,departamento,
                                 email,telefono_oficina,celular,iniciales,es_principal,notas)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                             (cliente_id, nom.strip(), ape, cargo, depto,
                              email, tel_of, cel, ini.upper().strip(),
                              1 if princ else 0, notas_c))
                conn.commit(); conn.close()
                st.session_state[f"show_form_con_{cliente_id}"] = False
                st.success("Contacto guardado."); st.rerun()
            else:
                st.error("El nombre es requerido.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: ALTA DE NUEVO CLIENTE (CON SUBIDA / PEGAR IMAGEN PORTAPAPELES)
# ─────────────────────────────────────────────────────────────────────────────

INDUSTRIAS = [
    "Automatización Industrial", "Manufactura", "Automotriz", "Minería",
    "Alimentaria y Bebidas", "Petroquímica", "Farmacéutica", "Energía",
    "Construcción", "Logística y Transporte", "Gobierno / Público", "Otro"
]

def _render_alta_cliente():
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Registro de Nueva Empresa Cliente</h2>
        <p>Completa los datos de la empresa. Puedes cargar su imagen o <b>pegarla directamente desde el Portapapeles (Ctrl+V)</b>.</p>
    </div>""", unsafe_allow_html=True)

    # ── BOTÓN Y ÁREA JS PARA PEGAR IMAGEN DEL PORTAPAPELES ───────────────────
    st.markdown(f"""
    <div style="background:{BRAND_WHITE};border:2px dashed {BRAND_ORANGE};border-radius:10px;
                padding:16px 20px;margin-bottom:20px;font-family:'Montserrat',sans-serif;">
        <p style="font-size:12px;font-weight:800;color:{BRAND_ORANGE};text-transform:uppercase;margin:0 0 4px 0;">
            📋 PEGAR IMAGEN / LOGO DESDE EL PORTAPAPELES
        </p>
        <p style="font-size:11px;color:{BRAND_CHARCOAL_MED};margin:0 0 10px 0;">
            Copia cualquier imagen o logo (con Win + Shift + S o Ctrl+C) y luego haz clic en el área inferior y presiona <b>Ctrl + V</b>:
        </p>
        <div id="paste-zone" style="background:{BRAND_GRAY_BG};border:1px solid {BRAND_BORDER_LIGHT};
                                   border-radius:8px;padding:16px;text-align:center;cursor:pointer;">
            <span style="font-size:13px;font-weight:700;color:{BRAND_CHARCOAL};">
                📋 Haz clic aquí y presiona <kbd style='background:#fff;border:1px solid #ccc;padding:2px 6px;border-radius:4px;'>Ctrl + V</kbd> para Pegar Imagen
            </span>
            <div id="paste-preview" style="margin-top:10px;"></div>
        </div>
    </div>

    <script>
    const pasteZone = document.getElementById('paste-zone');
    if (pasteZone) {{
        pasteZone.addEventListener('paste', function(e) {{
            const items = e.clipboardData.items;
            for (let i = 0; i < items.length; i++) {{
                if (items[i].type.indexOf('image') !== -1) {{
                    const blob = items[i].getAsFile();
                    const reader = new FileReader();
                    reader.onload = function(event) {{
                        const img = document.createElement('img');
                        img.src = event.target.result;
                        img.style.maxHeight = '120px';
                        img.style.borderRadius = '6px';
                        img.style.border = '2px solid #FE8C29';
                        const preview = document.getElementById('paste-preview');
                        preview.innerHTML = '';
                        preview.appendChild(img);
                        
                        // Guardar en input de streamlit si está presente
                        const inputs = parent.document.querySelectorAll('input[type=text]');
                        for (let input of inputs) {{
                            if (input.placeholder && input.placeholder.includes('Base64')) {{
                                input.value = event.target.result;
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        }}
                    }};
                    reader.readAsDataURL(blob);
                }}
            }}
        }});
    }}
    </script>
    """, unsafe_allow_html=True)

    with st.form("form_nuevo_cliente", clear_on_submit=True):
        # ── DATOS PRINCIPALES DE LA EMPRESA ──────────────────────────────────
        st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                    f"color:{BRAND_ORANGE};margin:0 0 8px 0;'>📋 DATOS DE LA EMPRESA</p>",
                    unsafe_allow_html=True)

        c1, c2, c3 = st.columns([4, 1.8, 2.2])
        with c1:
            nombre = st.text_input("Razón Social / Nombre de la Empresa *",
                                   placeholder="Ej: YESO Y MOLDURAS SA de CV")
        with c2:
            acronimo = st.text_input("Acrónimo / Clave *",
                                     max_chars=6,
                                     placeholder="Ej: YES",
                                     help="Clave de 3 a 5 letras para el folio (Ej: YES, DXT, OHG)")
        with c3:
            industria = st.selectbox("Industria", INDUSTRIAS)

        c4, c5, c6 = st.columns([2, 2, 2])
        with c4: rfc      = st.text_input("RFC", placeholder="Ej: YMO841209XY3")
        with c5: sitio    = st.text_input("Sitio Web", placeholder="www.empresa.com")
        with c6: email    = st.text_input("Email Principal", placeholder="contacto@empresa.com")

        c7, c8 = st.columns([2, 2])
        with c7: telefono = st.text_input("Teléfono", placeholder="+52 (55) 1234-5678")
        with c8: tel2     = st.text_input("Teléfono 2 / WhatsApp")

        # ── LOGO E IMAGEN DE LA EMPRESA ───────────────────────────────────────
        st.markdown(f"<hr style='border:1px solid {BRAND_BORDER_LIGHT};margin:12px 0;'>",
                    unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                    f"color:{BRAND_ORANGE};margin:0 0 4px 0;'>🖼️ LOGO / IMAGEN DESDE ARCHIVO</p>",
                    unsafe_allow_html=True)

        logo_file = st.file_uploader("Subir archivo de logo o imagen (PNG, JPG, WEBP)",
                                     type=["png", "jpg", "jpeg", "webp", "bmp"],
                                     key="cl_logo_upload")

        st.divider()

        # ── DIRECCIÓN ─────────────────────────────────────────────────────────
        st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                    f"color:{BRAND_ORANGE};margin:0 0 8px 0;'>📍 DIRECCIÓN FISCAL / OBRA</p>",
                    unsafe_allow_html=True)
        dir_f = st.text_input("Dirección Fiscal", placeholder="Calle, Número, Colonia")
        cd1, cd2, cd3 = st.columns([2, 2, 2])
        with cd1: ciudad = st.text_input("Ciudad", placeholder="San Luis Potosí")
        with cd2: estado = st.text_input("Estado", placeholder="San Luis Potosí")
        with cd3: pais   = st.text_input("País", value="México")

        st.divider()

        # ── PRIMER CONTACTO ───────────────────────────────────────────────────
        st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                    f"color:{BRAND_ORANGE};margin:0 0 8px 0;'>👤 CONTACTO PRINCIPAL (OPCIONAL)</p>",
                    unsafe_allow_html=True)
        cp1, cp2, cp3, cp4 = st.columns([2, 2, 2, 1.5])
        with cp1: con_nom   = st.text_input("Nombre del Contacto")
        with cp2: con_ape   = st.text_input("Apellido")
        with cp3: con_cargo = st.text_input("Cargo / Puesto")
        with cp4: con_ini   = st.text_input("Iniciales", max_chars=5,
                                             help="Ej: RG — se usa para las iniciales del folio")
        cp5, cp6, cp7 = st.columns([2.5, 2, 2])
        with cp5: con_email = st.text_input("Email del Contacto")
        with cp6: con_tel   = st.text_input("Teléfono Oficina")
        with cp7: con_cel   = st.text_input("Celular")

        notas = st.text_area("Notas Generales del Cliente", height=60,
                              placeholder="Observaciones, condiciones especiales...")

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("💾 Registrar Cliente", type="primary")

    if submitted:
        if not nombre.strip():
            st.error("La Razón Social es requerida.")
        elif not acronimo.strip():
            st.error("El Acrónimo / Clave del cliente es requerido.")
        else:
            acr_clean = acronimo.strip().upper()

            # Guardar logo si se subió
            saved_logo_path = ""
            if logo_file is not None:
                fname = f"logo_{acr_clean}_{uuid.uuid4().hex[:6]}_{logo_file.name}"
                saved_logo_path = os.path.join(UPLOAD_DIR, fname)
                with open(saved_logo_path, "wb") as f:
                    f.write(logo_file.getbuffer())

            try:
                conn = get_connection()
                conn.execute("""INSERT INTO clientes
                                (nombre,acronimo,rfc,industria,sitio_web,
                                 direccion_fiscal,ciudad,estado,pais,
                                 email,telefono,notas,logo_path,activo)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
                             (nombre.strip(), acr_clean, rfc, industria, sitio,
                              dir_f, ciudad, estado, pais,
                              email, telefono, notas, saved_logo_path))
                conn.commit()

                cur = conn.cursor()
                cur.execute("SELECT id FROM clientes WHERE acronimo=? AND nombre=?",
                            (acr_clean, nombre.strip()))
                cliente_id = cur.fetchone()['id']

                if con_nom.strip():
                    conn.execute("""INSERT INTO clientes_contactos
                                    (cliente_id,nombre,apellido,cargo,email,
                                     telefono_oficina,celular,iniciales,es_principal)
                                    VALUES(?,?,?,?,?,?,?,?,1)""",
                                 (cliente_id, con_nom.strip(), con_ape,
                                  con_cargo, con_email, con_tel, con_cel,
                                  con_ini.upper().strip()))
                    conn.commit()
                conn.close()

                st.success(f"✅ Cliente **{nombre.strip()}** [{acr_clean}] registrado correctamente.")
                st.info("Puedes ver y gestionar sus contactos en la pestaña **🏢 Directorio de Clientes**.")
            except Exception as e:
                if "UNIQUE" in str(e):
                    st.error(f"Ya existe un cliente con ese nombre o acrónimo ({acr_clean}).")
                else:
                    st.error(f"Error al guardar: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3: INGENIEROS J&D Y ESTRUCTURA DE FOLIO
# ─────────────────────────────────────────────────────────────────────────────

def _render_ingenieros():
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Ingenieros y Personal J&D Automation</h2>
        <p>Las iniciales de cada ingeniero se integran en la clave oficial del folio de cotización.</p>
    </div>""", unsafe_allow_html=True)

    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM jd_ingenieros WHERE activo=1 ORDER BY iniciales")
    ings = [dict(r) for r in cur.fetchall()]; conn.close()

    if ings:
        iw = [1.2, 2.5, 2, 2.5, 2.5, 0.6]
        ih = ["Iniciales", "Nombre Completo", "Cargo", "Email", "", "✕"]
        hcols = st.columns(iw)
        for col, lbl in zip(hcols, ih):
            col.markdown(f"<p style='font-size:10px;font-weight:800;text-transform:uppercase;"
                         f"color:{BRAND_CHARCOAL_MED};margin:6px 0 2px 0;'>{lbl}</p>",
                         unsafe_allow_html=True)
        for ing in ings:
            rc = st.columns(iw)
            rc[0].markdown(f"<div style='background:{BRAND_ORANGE};color:#fff;font-size:15px;"
                           f"font-weight:900;border-radius:6px;text-align:center;padding:4px 0;"
                           f"font-family:Montserrat,sans-serif;'>{ing['iniciales']}</div>",
                           unsafe_allow_html=True)
            rc[1].markdown(f"<p style='font-size:13px;font-weight:700;color:{BRAND_CHARCOAL};"
                           f"margin:5px 0;'>{ing['nombre']} {ing.get('apellido','')}</p>",
                           unsafe_allow_html=True)
            rc[2].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:5px 0;'>{ing.get('cargo','—')}</p>",
                           unsafe_allow_html=True)
            rc[3].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:5px 0;'>{ing.get('email','—')}</p>",
                           unsafe_allow_html=True)
            rc[4].markdown("", unsafe_allow_html=True)
            if rc[5].button("✕", key=f"del_ing_{ing['id']}"):
                conn = get_connection()
                conn.execute("UPDATE jd_ingenieros SET activo=0 WHERE id=?", (ing['id'],))
                conn.commit(); conn.close(); st.rerun()

    st.divider()
    st.markdown("**Agregar Nuevo Ingeniero / Responsable**")
    with st.form("form_ing", clear_on_submit=True):
        fi1, fi2, fi3, fi4, fi5 = st.columns([1.5, 2, 2, 2, 2.5])
        with fi1: ini_i   = st.text_input("Iniciales *", max_chars=5, placeholder="DS")
        with fi2: nom_i   = st.text_input("Nombre *",    placeholder="David")
        with fi3: ape_i   = st.text_input("Apellido",    placeholder="de Santiago")
        with fi4: cargo_i = st.text_input("Cargo",      placeholder="Gerente de Proyectos")
        with fi5: email_i = st.text_input("Email",      placeholder="david@jdautomation.com")

        if st.form_submit_button("➕ Agregar Ingeniero", type="primary"):
            if ini_i.strip() and nom_i.strip():
                try:
                    conn = get_connection()
                    conn.execute("""INSERT INTO jd_ingenieros (iniciales,nombre,apellido,cargo,email)
                                    VALUES(?,?,?,?,?)""",
                                 (ini_i.strip().upper(), nom_i.strip(), ape_i, cargo_i, email_i))
                    conn.commit(); conn.close()
                    st.success(f"Ingeniero {ini_i.upper()} agregado."); st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Iniciales y nombre son requeridos.")

    # ── PREVIEW DEL NUEVO FORMATO DE FOLIO ─────────────────────────────────────
    st.divider()
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Estructura del Folio de Cotización J&D</h2>
        <p>Estructura oficial: <b>COT — CONSECUTIVO — CLIENTE — ING. RESPONSABLE — PROYECTO</b></p>
    </div>""", unsafe_allow_html=True)

    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM clientes WHERE activo=1 ORDER BY nombre")
    clientes_p = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT * FROM jd_ingenieros WHERE activo=1 ORDER BY iniciales")
    ings_p = [dict(r) for r in cur.fetchall()]
    conn.close()

    if clientes_p and ings_p:
        pc1, pc2, pc3 = st.columns([2.5, 2, 3])
        with pc1:
            cl_opts = {f"{c['nombre']} [{c.get('acronimo','CLI')}]": c for c in clientes_p}
            cl_sel  = st.selectbox("Cliente", list(cl_opts.keys()), key="prev_cl")
            cl_obj  = cl_opts[cl_sel]
        with pc2:
            ing_opts = {f"{i['iniciales']} — {i['nombre']} {i.get('apellido','')}": i['iniciales']
                        for i in ings_p}
            ing_sel  = st.selectbox("Ingeniero responsable", list(ing_opts.keys()), key="prev_ing")
            iniciales = ing_opts[ing_sel]
        with pc3:
            proy_prev = st.text_input("Nombre del Proyecto", value="CONTROL PID MOLINOS", key="prev_proy")

        acr = (cl_obj.get('acronimo') or 'CLI').upper()

        # NUEVO FORMATO SOLICITADO: COT-CONSECUTIVO-CLIENTE-ING-PROYECTO
        consec = 82
        folio_preview = f"COT-{consec:03d}-{acr}-{iniciales}-{proy_prev.upper().strip()}"

        st.markdown(f"""
        <div style="background:{BRAND_CHARCOAL};color:#fff;border-radius:10px;
                    padding:18px 24px;margin-top:12px;font-family:'Montserrat',sans-serif;
                    border-left:6px solid {BRAND_ORANGE};">
            <p style="font-size:10px;font-weight:800;text-transform:uppercase;
                      color:{BRAND_ORANGE};letter-spacing:1px;margin:0 0 6px 0;">
                NUEVO FORMATO DE FOLIO OFICIAL
            </p>
            <p style="font-size:26px;font-weight:900;letter-spacing:2px;margin:0 0 8px 0;">
                {folio_preview}
            </p>
            <div style="display:flex;gap:18px;margin-top:8px;font-size:11px;color:#CBD5E1;flex-wrap:wrap;">
                <span><b style="color:{BRAND_ORANGE};">COT</b> = Cotización</span>
                <span><b style="color:{BRAND_ORANGE};">{consec:03d}</b> = Consecutivo</span>
                <span><b style="color:{BRAND_ORANGE};">{acr}</b> = {cl_obj['nombre']}</span>
                <span><b style="color:{BRAND_ORANGE};">{iniciales}</b> = Ingeniero responsable</span>
                <span><b style="color:{BRAND_ORANGE};">{proy_prev.upper()}</b> = Nombre del proyecto</span>
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Registra al menos un cliente y un ingeniero para ver el preview del folio.")
