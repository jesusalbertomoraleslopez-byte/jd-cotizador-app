"""
Wizard de Cotización — J&D Automation Industries
Flujo guiado de 5 pasos: Proyecto → Partidas → Costos → Revisión → Gantt
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

from database.models import get_connection, init_db
from database.db_manager import (
    get_catalogo_materiales, get_catalogo_mano_obra, sync_cotizacion_totals
)
from config import (
    BRAND_ORANGE, BRAND_CHARCOAL, BRAND_CHARCOAL_MED,
    BRAND_WHITE, BRAND_BORDER_LIGHT, BRAND_GRAY_BG
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DEL WIZARD
# ─────────────────────────────────────────────────────────────────────────────
STEPS = [
    ("1", "📋 Proyecto",   "Cliente · Folio · Parámetros"),
    ("2", "📑 Partidas",   "Conceptos de obra"),
    ("3", "💰 Costos",     "Mat · M.O · Sub · Maq · Gastos"),
    ("4", "📊 Revisión",   "ANÁLISIS · Aprobar · Congelar"),
    ("5", "📅 Cronograma", "Gantt del proyecto"),
]

# ─────────────────────────────────────────────────────────────────────────────
# STEPPER VISUAL
# ─────────────────────────────────────────────────────────────────────────────
def _render_stepper(current_step: int):
    n = len(STEPS)
    html_steps = ""
    for i, (num, label, sub) in enumerate(STEPS):
        idx = i + 1
        if idx < current_step:
            circle_bg = BRAND_ORANGE
            circle_color = "#fff"
            text_color = BRAND_ORANGE
            icon = "✓"
        elif idx == current_step:
            circle_bg = BRAND_ORANGE
            circle_color = "#fff"
            text_color = BRAND_CHARCOAL
            icon = num
        else:
            circle_bg = "#E2E8F0"
            circle_color = BRAND_CHARCOAL_MED
            text_color = BRAND_CHARCOAL_MED
            icon = num

        line = ""
        if i < n - 1:
            line_color = BRAND_ORANGE if idx < current_step else "#E2E8F0"
            line = f'<div style="flex:1;height:2px;background:{line_color};margin:0 4px;align-self:center;min-width:15px;"></div>'

        step_item = (
            f'<div style="display:flex;flex-direction:column;align-items:center;min-width:90px;">'
            f'<div style="width:34px;height:34px;border-radius:50%;background:{circle_bg};color:{circle_color};display:flex;align-items:center;justify-content:center;font-weight:900;font-size:14px;font-family:\'Montserrat\',sans-serif;border:2px solid {circle_bg};">{icon}</div>'
            f'<p style="font-size:11px;font-weight:800;color:{text_color};margin:4px 0 0 0;text-align:center;font-family:\'Montserrat\',sans-serif;">{label}</p>'
            f'<p style="font-size:9px;color:{BRAND_CHARCOAL_MED};margin:1px 0 0 0;text-align:center;font-family:\'Montserrat\',sans-serif;">{sub}</p>'
            f'</div>{line}'
        )
        html_steps += step_item

    container = (
        f'<div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};'
        f'border-radius:12px;padding:16px 24px;margin-bottom:20px;'
        f'display:flex;align-items:flex-start;justify-content:space-between;overflow-x:auto;">'
        f'{html_steps}'
        f'</div>'
    )
    st.markdown(container, unsafe_allow_html=True)



def _nav_buttons(step, max_step=5, can_next=True):
    """Botones de navegación Anterior / Siguiente."""
    c1, c2, c3 = st.columns([1, 6, 1])
    with c1:
        if step > 1:
            if st.button("← Anterior", key=f"prev_{step}", use_container_width=True):
                st.session_state.wiz_step = step - 1
                st.rerun()
    with c3:
        if step < max_step and can_next:
            if st.button("Siguiente →", key=f"next_{step}", use_container_width=True, type="primary"):
                st.session_state.wiz_step = step + 1
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL DEL WIZARD
# ─────────────────────────────────────────────────────────────────────────────
def render_wizard_cotizador():
    init_db()

    # ── Estado de sesión ──────────────────────────────────────────────────────
    if "wiz_step"   not in st.session_state: st.session_state.wiz_step   = 1
    if "wiz_cot_id" not in st.session_state: st.session_state.wiz_cot_id = None

    step   = st.session_state.wiz_step
    cot_id = st.session_state.wiz_cot_id

    # ── Selector de cotización existente (siempre visible en sidebar) ─────────
    _sidebar_cot_selector()
    cot_id = st.session_state.wiz_cot_id  # puede cambiar tras selector

    # ── Stepper ───────────────────────────────────────────────────────────────
    _render_stepper(step)

    # ── Verificar si la cotización está congelada ─────────────────────────────
    congelada = False
    if cot_id:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT congelada FROM cotizaciones WHERE id=?", (cot_id,))
        row = cur.fetchone(); conn.close()
        congelada = bool(row and row['congelada'])

    if congelada and step in (1, 2, 3):
        st.warning("🔒 Esta cotización está **congelada / aprobada**. Solo puede consultarse. "
                   "Para editar, ve al Paso 4 y crea una nueva revisión.")

    # ── Ruteo de pasos ────────────────────────────────────────────────────────
    if step == 1:
        _step1_proyecto(cot_id, congelada)
    elif step == 2:
        if not cot_id:
            st.error("Primero completa el Paso 1 para crear o seleccionar una cotización.")
        else:
            _step2_partidas(cot_id, congelada)
    elif step == 3:
        if not cot_id:
            st.error("Primero completa el Paso 1.")
        else:
            _step3_costos(cot_id, congelada)
    elif step == 4:
        if not cot_id:
            st.error("Primero completa el Paso 1.")
        else:
            _step4_revision(cot_id)
    elif step == 5:
        if not cot_id:
            st.error("Primero completa el Paso 1.")
        else:
            _step5_gantt(cot_id, congelada)


def _sidebar_cot_selector():
    """Selector compacto en sidebar para cambiar de cotización."""
    with st.sidebar:
        st.markdown(f"<hr style='border:1px solid #5A6478;margin:12px 0;'>",
                    unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:10px;font-weight:800;text-transform:uppercase;"
                    f"color:#8C96A6;letter-spacing:.5px;'>Cotización activa</p>",
                    unsafe_allow_html=True)
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""SELECT c.id, c.folio, c.estatus, c.congelada,
                              COALESCE(cl.acronimo,'—') as acr
                       FROM cotizaciones c
                       LEFT JOIN clientes cl ON c.cliente_id=cl.id
                       ORDER BY c.id DESC LIMIT 30""")
        cots = [dict(r) for r in cur.fetchall()]; conn.close()

        if not cots:
            st.caption("Sin cotizaciones creadas.")
            return

        opts = {f"{'🔒 ' if c['congelada'] else ''}{c['folio']}": c['id'] for c in cots}
        # Determinar índice actual
        curr = st.session_state.get('wiz_cot_id')
        idx = list(opts.values()).index(curr) if curr in opts.values() else 0

        sel = st.selectbox("", list(opts.keys()), index=idx,
                           label_visibility="collapsed", key="sb_cot_sel")
        if opts[sel] != st.session_state.wiz_cot_id:
            st.session_state.wiz_cot_id = opts[sel]
            st.session_state.wiz_step   = 1
            st.rerun()

        if st.button("➕ Nueva Cotización", use_container_width=True, key="btn_new_cot"):
            st.session_state.wiz_cot_id = None
            st.session_state.wiz_step   = 1
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: DATOS DEL PROYECTO
# ─────────────────────────────────────────────────────────────────────────────
def _step1_proyecto(cot_id, congelada):
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 1 — Datos del Proyecto</h2>
        <p>Selecciona el cliente, el ingeniero responsable y define el nombre del proyecto.</p>
    </div>""", unsafe_allow_html=True)

    # Cargar catálogos
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, nombre, COALESCE(acronimo,'SIN') as acronimo FROM clientes WHERE activo=1 ORDER BY nombre")
    clientes = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT iniciales, nombre, apellido FROM jd_ingenieros WHERE activo=1 ORDER BY iniciales")
    ings = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Cargar datos actuales si hay cotización
    cot_info = {}
    if cot_id:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM cotizaciones WHERE id=?", (cot_id,))
        row = cur.fetchone()
        if row: cot_info = dict(row)
        conn.close()

    if not clientes:
        st.warning("⚠️ No hay clientes registrados. Ve a **🏢 Clientes** para dar de alta al menos uno.")
        _nav_buttons(1, can_next=False)
        return

    if not ings:
        st.warning("⚠️ No hay ingenieros J&D registrados. Ve a **🏢 Clientes → Ingenieros J&D**.")
        _nav_buttons(1, can_next=False)
        return

    # ── SELECCIÓN CLIENTE / CONTACTO ─────────────────────────────────────────
    st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                f"color:{BRAND_ORANGE};margin:0 0 8px 0;'>1. CLIENTE</p>",
                unsafe_allow_html=True)

    cl_opts = {f"{c['nombre']}": c for c in clientes}
    curr_cl_name = ""
    if cot_info.get('cliente_id'):
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT nombre FROM clientes WHERE id=?", (cot_info['cliente_id'],))
        r = cur.fetchone(); conn.close()
        if r: curr_cl_name = r['nombre']
    curr_cl_idx = list(cl_opts.keys()).index(curr_cl_name) if curr_cl_name in cl_opts else 0

    cc1, cc2 = st.columns([4, 2])
    with cc1:
        cl_sel = st.selectbox("Empresa Cliente *", list(cl_opts.keys()),
                              index=curr_cl_idx, key="s1_cl",
                              disabled=congelada)
        cl_obj  = cl_opts[cl_sel]
        acr_cl  = cl_obj['acronimo'].upper()

    # Contactos de ese cliente
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT id, nombre, apellido, cargo, iniciales
                   FROM clientes_contactos WHERE cliente_id=? ORDER BY es_principal DESC, nombre""",
                (cl_obj['id'],))
    contactos = [dict(r) for r in cur.fetchall()]; conn.close()

    with cc2:
        con_opts = {f"{c['nombre']} {c.get('apellido','')} — {c.get('cargo','')}"[:50]: c
                    for c in contactos}
        con_opts_list = ["— Sin contacto específico —"] + list(con_opts.keys())
        curr_con = cot_info.get('nombre_contacto','')
        curr_con_idx = 0
        for i, k in enumerate(con_opts_list):
            if curr_con and curr_con in k:
                curr_con_idx = i; break
        con_sel = st.selectbox("Contacto del Cliente", con_opts_list,
                               index=curr_con_idx, key="s1_con",
                               disabled=congelada)

    # ── INGENIERO / PROYECTO ──────────────────────────────────────────────────
    st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                f"color:{BRAND_ORANGE};margin:12px 0 8px 0;'>2. INGENIERO Y PROYECTO</p>",
                unsafe_allow_html=True)

    ing_opts = {f"{i['iniciales']} — {i['nombre']} {i.get('apellido','')}": i['iniciales']
                for i in ings}
    curr_ing = cot_info.get('ingeniero_id', list(ing_opts.values())[0] if ing_opts else '')
    curr_ing_idx = list(ing_opts.values()).index(curr_ing) if curr_ing in ing_opts.values() else 0

    pi1, pi2, pi3 = st.columns([2, 4, 1.5])
    with pi1:
        ing_sel  = st.selectbox("Ingeniero Responsable *", list(ing_opts.keys()),
                                index=curr_ing_idx, key="s1_ing",
                                disabled=congelada)
        iniciales = ing_opts[ing_sel]
    with pi2:
        proyecto = st.text_input("Nombre del Proyecto *",
                                  value=cot_info.get('proyecto',''),
                                  placeholder="Ej: CONTROL PID MOLINOS",
                                  key="s1_proy", disabled=congelada)
    with pi3:
        revision_opts = ["R0","R1","R2","R3","R4","R5","R6","R7","R8","R9"]
        curr_rev = cot_info.get('revision','R0')
        curr_rev_idx = revision_opts.index(curr_rev) if curr_rev in revision_opts else 0
        revision = st.selectbox("Revisión", revision_opts,
                                index=curr_rev_idx, key="s1_rev",
                                disabled=congelada)

    # ── FOLIO GENERADO ────────────────────────────────────────────────────────
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM cotizaciones WHERE id != ?", (cot_id or -1,))
    consec = (cur.fetchone()[0] or 0) + 1
    folio_actual = cot_info.get('folio','')
    parts = folio_actual.split('-')
    if len(parts) >= 2:
        for p in parts[1:]:
            if p.isdigit():
                try: consec = int(p); break
                except: pass
    conn.close()

    proy_clean = proyecto.strip().upper() if proyecto.strip() else "PROYECTO"
    folio_gen  = f"COT-{consec:03d}-{acr_cl}-{iniciales}-{proy_clean}_Cotizacion_Oficial"

    st.markdown(f"""
    <div style="background:{BRAND_CHARCOAL};border-radius:10px;padding:14px 22px;
                border-left:6px solid {BRAND_ORANGE};margin:12px 0;
                font-family:'Montserrat',sans-serif;">
        <span style="font-size:10px;font-weight:800;text-transform:uppercase;
                     color:{BRAND_ORANGE};letter-spacing:1.2px;">FOLIO GENERADO AUTOMÁTICAMENTE</span><br>
        <span style="font-size:24px;font-weight:900;color:#fff;letter-spacing:1.5px;">{folio_gen}</span>
        <div style="display:flex;gap:16px;margin-top:6px;font-size:10px;color:#94A3B8;flex-wrap:wrap;">
            <span><b style="color:{BRAND_ORANGE};">COT</b> = Cotización</span>
            <span><b style="color:{BRAND_ORANGE};">{consec:03d}</b> = Consecutivo</span>
            <span><b style="color:{BRAND_ORANGE};">{acr_cl}</b> = {cl_sel}</span>
            <span><b style="color:{BRAND_ORANGE};">{iniciales}</b> = Ing. responsable</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # ── PARÁMETROS FINANCIEROS ────────────────────────────────────────────────
    st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                f"color:{BRAND_ORANGE};margin:12px 0 8px 0;'>3. PARÁMETROS FINANCIEROS</p>",
                unsafe_allow_html=True)

    pf1, pf2, pf3, pf4 = st.columns(4)
    with pf1: tc  = st.number_input("Tipo de Cambio (MXN/USD)", value=float(cot_info.get('tipo_cambio_usd', 18.0)), step=0.10, disabled=congelada)
    with pf2: mg  = st.number_input("Margen de Utilidad (%)",   value=round(float(cot_info.get('margen_porcentaje', 0.30))*100, 1), step=1.0, disabled=congelada)
    with pf3: cm  = st.number_input("Comisión (%)",             value=round(float(cot_info.get('comision_porcentaje', 0.05))*100, 1), step=1.0, disabled=congelada)
    with pf4: sv  = st.number_input("Supervisión (%)",          value=round(float(cot_info.get('supervision_porcentaje', 0.30))*100, 1), step=1.0, disabled=congelada)

    # ── NOTAS DE VERSIÓN ──────────────────────────────────────────────────────
    notas_v = st.text_area("Notas de esta Versión / Revisión",
                            value=cot_info.get('notas_version',''),
                            height=60, key="s1_notas",
                            placeholder="Ej: Ajuste de precios de materiales / Cambio de alcance en Partida 3",
                            disabled=congelada)

    # ── GUARDAR ───────────────────────────────────────────────────────────────
    if not congelada:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Guardar y Continuar al Paso 2 →", type="primary", key="s1_save"):
            if not proyecto.strip():
                st.error("El nombre del proyecto es requerido.")
                return

            nom_contacto = ""
            if con_sel != "— Sin contacto específico —" and con_sel in con_opts:
                con_obj = con_opts[con_sel]
                nom_contacto = f"{con_obj['nombre']} {con_obj.get('apellido','')}"

            conn = get_connection()
            if cot_id:
                conn.execute("""UPDATE cotizaciones SET
                                folio=?, proyecto=?, revision=?, cliente_id=?,
                                tipo_cambio_usd=?, margen_porcentaje=?,
                                comision_porcentaje=?, supervision_porcentaje=?,
                                ingeniero_id=?, nombre_contacto=?, notas_version=?
                                WHERE id=?""",
                             (folio_gen, proyecto.strip(), revision, cl_obj['id'],
                              tc, mg/100, cm/100, sv/100,
                              iniciales, nom_contacto, notas_v, cot_id))
                conn.commit(); conn.close()
                st.success(f"✅ Cotización actualizada: **{folio_gen}**")
            else:
                conn.execute("""INSERT INTO cotizaciones
                                (folio, proyecto, revision, cliente_id,
                                 tipo_cambio_usd, margen_porcentaje,
                                 comision_porcentaje, supervision_porcentaje,
                                 ingeniero_id, nombre_contacto, notas_version, estatus)
                                VALUES(?,?,?,?,?,?,?,?,?,?,?,'Borrador')""",
                             (folio_gen, proyecto.strip(), revision, cl_obj['id'],
                              tc, mg/100, cm/100, sv/100,
                              iniciales, nom_contacto, notas_v))
                conn.commit()
                cur = conn.cursor()
                cur.execute("SELECT id FROM cotizaciones WHERE folio=?", (folio_gen,))
                new_id = cur.fetchone()['id']
                conn.close()
                st.session_state.wiz_cot_id = new_id
                st.success(f"✅ Cotización creada: **{folio_gen}**")

            st.session_state.wiz_step = 2
            st.rerun()
    else:
        _nav_buttons(1)


# ─────────────────────────────────────────────────────────────────────────────
# PASO 2: PARTIDAS
# ─────────────────────────────────────────────────────────────────────────────
def _step2_partidas(cot_id, congelada):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT folio, proyecto FROM cotizaciones WHERE id=?", (cot_id,))
    cot = dict(cur.fetchone())
    cur.execute("SELECT * FROM cotizacion_partidas WHERE cotizacion_id=? ORDER BY numero_partida", (cot_id,))
    partidas = [dict(r) for r in cur.fetchall()]
    conn.close()

    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 2 — Partidas del Proyecto</h2>
        <p>Define las partidas (conceptos de obra) de <b>{cot['folio']}</b></p>
    </div>""", unsafe_allow_html=True)

    # ── LISTA DE PARTIDAS ─────────────────────────────────────────────────────
    if partidas:
        for p in partidas:
            ca, cb, cc, cd = st.columns([0.4, 0.8, 6.5, 0.6])
            ca.markdown(f"<div style='background:{BRAND_ORANGE};color:#fff;border-radius:6px;"
                        f"text-align:center;padding:7px 0;font-weight:900;font-size:14px;"
                        f"font-family:Montserrat,sans-serif;'>{p['numero_partida']}</div>",
                        unsafe_allow_html=True)
            cb.markdown(f"<p style='font-size:10px;color:{BRAND_CHARCOAL_MED};margin:8px 0 0 0;'>Partida</p>",
                        unsafe_allow_html=True)
            cc.markdown(f"<p style='font-size:14px;font-weight:700;color:{BRAND_CHARCOAL};margin:6px 0;'>"
                        f"{p['descripcion']}</p>", unsafe_allow_html=True)
            if not congelada and cd.button("✕", key=f"del_p2_{p['id']}"):
                conn = get_connection()
                conn.execute("DELETE FROM cotizacion_partidas WHERE id=?", (p['id'],))
                conn.commit(); conn.close()
                sync_cotizacion_totals(cot_id); st.rerun()
            st.markdown(f"<hr style='border:none;border-top:1px solid {BRAND_BORDER_LIGHT};margin:4px 0;'>",
                        unsafe_allow_html=True)
    else:
        st.info("Aún no hay partidas. Agrega la primera abajo.")

    # ── FORMULARIO NUEVA PARTIDA ──────────────────────────────────────────────
    if not congelada:
        st.markdown(f"""
        <div style="background:#F8F9FB;border:1px dashed {BRAND_ORANGE}77;border-radius:10px;
                    padding:14px 18px;margin-top:16px;">
        """, unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                    f"color:{BRAND_ORANGE};margin:0 0 10px 0;'>➕ AGREGAR PARTIDA</p>",
                    unsafe_allow_html=True)
        with st.form("form_p2", clear_on_submit=True):
            fc1, fc2, fc3 = st.columns([0.7, 5, 1.5])
            with fc1: num_p  = st.number_input("N°", value=len(partidas)+1, min_value=1, step=1)
            with fc2: desc_p = st.text_input("Descripción de la Partida *",
                                              placeholder="Ej: TABLERO DE CONTROL PARA SEÑALES DE CORRIENTE MOLINOS 1,2 Y 3")
            with fc3:
                unidad_p = st.selectbox("Unidad", ["LOTE","PZA","KIT","SERV","JGO","SISTEMA"])
            if st.form_submit_button("Guardar Partida", type="primary"):
                if desc_p.strip():
                    conn = get_connection()
                    conn.execute("INSERT INTO cotizacion_partidas (cotizacion_id,numero_partida,descripcion) VALUES(?,?,?)",
                                 (cot_id, num_p, desc_p.strip()))
                    conn.commit(); conn.close()
                    st.rerun()
                else:
                    st.error("La descripción es requerida.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── NAVEGACIÓN ────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _nav_buttons(2, can_next=len(partidas) > 0)
    if not partidas:
        st.warning("Agrega al menos una partida para continuar al Paso 3.")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3: COSTOS (sub-tabs)
# ─────────────────────────────────────────────────────────────────────────────
def _step3_costos(cot_id, congelada):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT folio, tipo_cambio_usd FROM cotizaciones WHERE id=?", (cot_id,))
    cot = dict(cur.fetchone())
    cur.execute("SELECT * FROM cotizacion_partidas WHERE cotizacion_id=? ORDER BY numero_partida", (cot_id,))
    partidas = [dict(r) for r in cur.fetchall()]
    conn.close()
    tc = float(cot['tipo_cambio_usd'])

    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 3 — Costos por Partida</h2>
        <p>Captura los costos de <b>{cot['folio']}</b> · Tipo de cambio: ${tc:,.2f} MXN/USD</p>
    </div>""", unsafe_allow_html=True)

    if not partidas:
        st.error("Sin partidas. Regresa al Paso 2.")
        _nav_buttons(3)
        return

    tabs = st.tabs(["🔩 Materiales", "👷 Mano de Obra", "🤝 Subcontratos", "🚜 Maquinaria", "✈️ Gastos"])

    with tabs[0]: _costos_materiales(cot_id, partidas, tc, congelada)
    with tabs[1]: _costos_mano_obra(cot_id, partidas, congelada)
    with tabs[2]: _costos_subcontratos(cot_id, partidas, congelada)
    with tabs[3]: _costos_maquinaria(cot_id, partidas, congelada)
    with tabs[4]: _costos_gastos(cot_id, congelada)

    st.markdown("<br>", unsafe_allow_html=True)
    _nav_buttons(3)


# ─── Helper render de partida ──────────────────────────────────────────────
def _ph(num, nombre, subtotal=None):
    badge = f"<span style='float:right;font-size:16px;font-weight:800;color:{BRAND_ORANGE};'>${subtotal:,.2f} MXN</span>" if subtotal is not None else ""
    st.markdown(f"""
    <div style="background:{BRAND_CHARCOAL};color:#fff;padding:10px 20px;
                border-radius:8px 8px 0 0;border-left:6px solid {BRAND_ORANGE};
                margin-top:24px;overflow:hidden;font-family:'Montserrat',sans-serif;">
        <span style="font-size:10px;font-weight:800;text-transform:uppercase;
                     letter-spacing:1.5px;color:{BRAND_ORANGE};">PARTIDA {num}</span>
        {badge}<br>
        <span style="font-size:13px;font-weight:700;">{nombre}</span>
    </div>""", unsafe_allow_html=True)


def _sub_bar(label, total):
    st.markdown(f"""
    <div style="background:linear-gradient(90deg,{BRAND_CHARCOAL},#3a4455);
                color:#fff;padding:9px 20px;display:flex;justify-content:space-between;
                font-family:'Montserrat',sans-serif;">
        <span style="font-size:11px;font-weight:700;text-transform:uppercase;">{label}</span>
        <span style="font-size:16px;font-weight:800;color:{BRAND_ORANGE};">${total:,.2f}</span>
    </div>""", unsafe_allow_html=True)


def _gran_total(label, total):
    st.markdown(f"""
    <div style="background:{BRAND_ORANGE};color:#fff;padding:13px 22px;border-radius:8px;
                margin-top:20px;display:flex;justify-content:space-between;
                font-family:'Montserrat',sans-serif;">
        <span style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;">{label}</span>
        <span style="font-size:21px;font-weight:900;">${total:,.2f} MXN</span>
    </div>""", unsafe_allow_html=True)


def _add_wrap_open():
    st.markdown(f"""<div style="background:#F8F9FB;border:1px solid {BRAND_BORDER_LIGHT};
                    border-top:2px dashed {BRAND_ORANGE}44;border-radius:0 0 8px 8px;
                    padding:10px 16px 14px;">""", unsafe_allow_html=True)


def _add_wrap_close():
    st.markdown("</div>", unsafe_allow_html=True)


def _lbl(text):
    st.markdown(f"<p style='font-size:10px;font-weight:800;text-transform:uppercase;"
                f"color:{BRAND_CHARCOAL_MED};letter-spacing:.5px;margin:0 0 2px 0;'>{text}</p>",
                unsafe_allow_html=True)


def _hdrs(cols, labels):
    for col, lbl in zip(cols, labels):
        col.markdown(f"<p style='font-size:10px;font-weight:800;text-transform:uppercase;"
                     f"color:{BRAND_CHARCOAL_MED};margin:6px 0 2px 0;'>{lbl}</p>",
                     unsafe_allow_html=True)


def _cell(col, text, bold=False, color=None):
    c = color or BRAND_CHARCOAL
    w = "font-weight:700;" if bold else ""
    col.markdown(f"<p style='font-size:13px;color:{c};{w}margin:3px 0;'>{text}</p>",
                 unsafe_allow_html=True)


def _empty():
    st.markdown(f"<div style='background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};"
                f"border-top:none;padding:10px 18px;color:{BRAND_CHARCOAL_MED};font-size:12px;"
                f"font-style:italic;'>Sin registros.</div>", unsafe_allow_html=True)


# ── MATERIALES ──────────────────────────────────────────────────────────────
def _costos_materiales(cot_id, partidas, tc, congelada):
    cat = get_catalogo_materiales()
    cat_names = ["— catálogo —"] + [m['descripcion'] for m in cat]
    LW = [.35, 4.8, 1.0, 1.1, 1.4, 1.5, 1.8, .5]
    LH = ["#","Descripción","Cant.","Unidad","P.U. USD","P.U. MXN","Importe MXN",""]

    # Resumen
    tots = []
    for p in partidas:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(importe_mxn),0) FROM cotizacion_materiales_detalle WHERE partida_id=?", (p['id'],))
        tots.append(cur.fetchone()[0]); conn.close()
    df = pd.DataFrame({"N°":[p['numero_partida'] for p in partidas],"Partida":[p['descripcion'] for p in partidas],"Mat. MXN":tots})
    st.dataframe(df.style.format({"Mat. MXN":"${:,.2f}"}), use_container_width=True, hide_index=True)
    _gran_total("TOTAL MATERIALES", sum(tots))

    st.markdown("<br>", unsafe_allow_html=True)
    for p in partidas:
        pid, num, nom = p['id'], p['numero_partida'], p['descripcion']
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM cotizacion_materiales_detalle WHERE partida_id=? ORDER BY id", (pid,))
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        sub = sum(r['importe_mxn'] for r in rows)
        _ph(num, nom, sub)
        if rows:
            cols_h = st.columns(LW); _hdrs(cols_h, LH)
            for i, row in enumerate(rows, 1):
                rc = st.columns(LW)
                _cell(rc[0], str(i))
                _cell(rc[1], row['descripcion'])
                _cell(rc[2], f"{row['cantidad']:,.2f}")
                _cell(rc[3], row['unidad'])
                _cell(rc[4], f"${row['precio_unitario_usd']:,.2f}")
                _cell(rc[5], f"${row['precio_unitario_mxn']:,.2f}")
                _cell(rc[6], f"${row['importe_mxn']:,.2f}", bold=True)
                if not congelada and rc[7].button("✕", key=f"dm_{row['id']}"):
                    conn = get_connection()
                    conn.execute("DELETE FROM cotizacion_materiales_detalle WHERE id=?", (row['id'],))
                    conn.commit(); conn.close()
                    sync_cotizacion_totals(cot_id); st.rerun()
        else: _empty()
        _sub_bar(f"SUBTOTAL — PARTIDA {num}", sub)

        if not congelada:
            _add_wrap_open()
            ca, cb = st.columns([4, 2])
            with ca: desc_in = st.text_input("Descripción", key=f"dm_d_{pid}", placeholder="Nombre del insumo", label_visibility="collapsed")
            with cb: cat_sel = st.selectbox("Catálogo", cat_names, key=f"dm_c_{pid}", label_visibility="collapsed")
            matched = next((m for m in cat if m['descripcion'] == cat_sel), None) if cat_sel != "— catálogo —" else None
            if matched and not desc_in: desc_in = matched['descripcion']
            f1,f2,f3,f4,f5,f6 = st.columns([1,.9,1.2,1.2,1.5,2])
            with f1: _lbl("Cant."); cant = st.number_input("c",value=1.0,min_value=.01,step=1.,key=f"dm_q_{pid}",label_visibility="collapsed")
            with f2: _lbl("Unidad"); unit = st.selectbox("u",["PZA","MTS","LOTE","JGO","KG","KIT","M","TRAMO"],key=f"dm_u_{pid}",label_visibility="collapsed")
            with f3: _lbl("P.U. USD"); pusd = st.number_input("us",min_value=0.,step=1.,value=float(matched['precio_unitario_usd']) if matched else 0.,key=f"dm_us_{pid}",label_visibility="collapsed")
            with f4: _lbl("P.U. MXN"); pmxn = st.number_input("mx",min_value=0.,step=10.,value=float(matched['precio_unitario_mxn']) if matched else (pusd*tc if pusd else 0.),key=f"dm_mx_{pid}",label_visibility="collapsed")
            with f5: st.markdown(f"<div style='padding-top:20px;text-align:right;'><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>IMPORTE</span><br><b style='font-size:15px;color:{BRAND_ORANGE};'>${cant*pmxn:,.2f}</b></div>", unsafe_allow_html=True)
            with f6:
                st.markdown("<div style='margin-top:18px;'>", unsafe_allow_html=True)
                if st.button(f"➕ Agregar a P{num}", key=f"dm_add_{pid}", type="primary", use_container_width=True):
                    if desc_in.strip():
                        conn = get_connection()
                        conn.execute("INSERT INTO cotizacion_materiales_detalle (cotizacion_id,partida_id,descripcion,cantidad,unidad,precio_unitario_usd,precio_unitario_mxn,importe_mxn) VALUES(?,?,?,?,?,?,?,?)",
                                     (cot_id,pid,desc_in.strip(),cant,unit,pusd,pmxn,cant*pmxn))
                        conn.commit(); conn.close()
                        sync_cotizacion_totals(cot_id); st.rerun()
                    else: st.error("Descripción requerida.")
                st.markdown("</div>", unsafe_allow_html=True)
            _add_wrap_close()


# ── MANO DE OBRA ────────────────────────────────────────────────────────────
def _costos_mano_obra(cot_id, partidas, congelada):
    mo_roles = get_catalogo_mano_obra()
    role_names = [r['categoria'] for r in mo_roles]
    LW = [2.5,.7,1.2,.7,1.,1.1,1.6,.5]; LH = ["Categoría","Personal","Sueldo Sem.","FASAR","Semanas","H-H","Importe",""]

    tots = []
    for p in partidas:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(importe_total),0) FROM cotizacion_mo_detalle WHERE partida_id=?", (p['id'],))
        tots.append(cur.fetchone()[0]); conn.close()
    df = pd.DataFrame({"N°":[p['numero_partida'] for p in partidas],"Partida":[p['descripcion'] for p in partidas],"M.O. MXN":tots,"Sup.30%":[v*.30 for v in tots]})
    st.dataframe(df.style.format({"M.O. MXN":"${:,.2f}","Sup.30%":"${:,.2f}"}), use_container_width=True, hide_index=True)
    _gran_total("TOTAL MANO DE OBRA", sum(tots))

    st.markdown("<br>", unsafe_allow_html=True)
    for p in partidas:
        pid, num, nom = p['id'], p['numero_partida'], p['descripcion']
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM cotizacion_mo_detalle WHERE partida_id=? ORDER BY id", (pid,))
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        sub = sum(r['importe_total'] for r in rows)
        _ph(num, nom, sub)
        if rows:
            cols_h = st.columns(LW); _hdrs(cols_h, LH)
            for row in rows:
                rc = st.columns(LW)
                _cell(rc[0], row['categoria_nombre'], bold=True)
                _cell(rc[1], str(row['cantidad_personal']))
                _cell(rc[2], f"${row['sueldo_base_semanal']:,.2f}")
                _cell(rc[3], f"{row['fasar']:.2f}")
                _cell(rc[4], f"{row['semanas']:.1f}")
                _cell(rc[5], f"{row['horas_hombre']:,.0f}")
                _cell(rc[6], f"${row['importe_total']:,.2f}", bold=True)
                if not congelada and rc[7].button("✕", key=f"dmo_{row['id']}"):
                    conn = get_connection()
                    conn.execute("DELETE FROM cotizacion_mo_detalle WHERE id=?", (row['id'],))
                    conn.commit(); conn.close()
                    sync_cotizacion_totals(cot_id); st.rerun()
        else: _empty()
        _sub_bar(f"SUBTOTAL M.O. — PARTIDA {num}", sub)

        if not congelada:
            _add_wrap_open()
            role_sel = st.selectbox("Categoría", role_names, key=f"mo_r_{pid}", label_visibility="collapsed")
            si = next((r for r in mo_roles if r['categoria'] == role_sel), mo_roles[0])
            c1,c2,c3,c4,c5 = st.columns([2,1,1.2,.8,.8])
            with c1: _lbl("Sueldo Base Sem."); sueldo = st.number_input("s",value=float(si['sueldo_base_semanal']),step=100.,key=f"mo_s_{pid}",label_visibility="collapsed")
            with c2: _lbl("Personal"); cant_p = st.number_input("p",value=1,min_value=1,step=1,key=f"mo_p_{pid}",label_visibility="collapsed")
            with c3: _lbl("Semanas"); sem_p = st.number_input("sem",value=1.0,min_value=.5,step=.5,key=f"mo_sem_{pid}",label_visibility="collapsed")
            with c4: _lbl("FASAR"); fasar = st.number_input("f",value=float(si['fasar']),step=.05,key=f"mo_f_{pid}",label_visibility="collapsed")
            with c5: _lbl("Sobre Sueldo"); sobre = st.number_input("o",value=float(si['sobre_sueldo']),step=.1,key=f"mo_o_{pid}",label_visibility="collapsed")
            costo_sem = sueldo*fasar*sobre; imp_mo = cant_p*costo_sem*sem_p; hh = cant_p*sem_p*48.
            st.markdown(f"<div style='display:flex;gap:24px;padding:4px 0;font-family:Montserrat,sans-serif;'><span><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>COSTO SEM.</span><br><b>${costo_sem:,.2f}</b></span><span><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>H-H</span><br><b>{hh:,.0f} hrs</b></span><span><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>IMPORTE M.O.</span><br><b style='font-size:15px;color:{BRAND_ORANGE};'>${imp_mo:,.2f}</b></span></div>", unsafe_allow_html=True)
            if st.button(f"➕ Asignar a P{num}", key=f"mo_add_{pid}", type="primary"):
                conn = get_connection()
                conn.execute("INSERT INTO cotizacion_mo_detalle (cotizacion_id,partida_id,categoria_nombre,cantidad_personal,sueldo_base_semanal,fasar,sobre_sueldo,semanas,horas_hombre,importe_total) VALUES(?,?,?,?,?,?,?,?,?,?)",
                             (cot_id,pid,role_sel,cant_p,sueldo,fasar,sobre,sem_p,hh,imp_mo))
                conn.commit(); conn.close()
                sync_cotizacion_totals(cot_id); st.rerun()
            _add_wrap_close()


# ── SUBCONTRATOS ────────────────────────────────────────────────────────────
def _costos_subcontratos(cot_id, partidas, congelada):
    tots = []
    for p in partidas:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(importe_mxn),0) FROM cotizacion_subcontratos_detalle WHERE partida_id=?", (p['id'],))
        tots.append(cur.fetchone()[0]); conn.close()
    df = pd.DataFrame({"N°":[p['numero_partida'] for p in partidas],"Partida":[p['descripcion'] for p in partidas],"Subcontratos MXN":tots})
    st.dataframe(df.style.format({"Subcontratos MXN":"${:,.2f}"}), use_container_width=True, hide_index=True)
    _gran_total("TOTAL SUBCONTRATOS", sum(tots))
    st.markdown("<br>", unsafe_allow_html=True)
    LW=[3.5,.9,1.2,1.5,1.9,2.5,.5]; LH=["Descripción","Cant.","Unidad","P.U. MXN","Importe MXN","Subcontratista",""]
    for p in partidas:
        pid, num, nom = p['id'], p['numero_partida'], p['descripcion']
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM cotizacion_subcontratos_detalle WHERE partida_id=? ORDER BY id", (pid,))
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        sub = sum(r['importe_mxn'] for r in rows)
        _ph(num, nom, sub)
        if rows:
            cols_h = st.columns(LW); _hdrs(cols_h, LH)
            for row in rows:
                rc = st.columns(LW)
                _cell(rc[0], row['descripcion'], bold=True); _cell(rc[1], f"{row['cantidad']:,.2f}"); _cell(rc[2], row['unidad'])
                _cell(rc[3], f"${row['pu_mxn']:,.2f}"); _cell(rc[4], f"${row['importe_mxn']:,.2f}", bold=True)
                _cell(rc[5], row.get('subcontratista','—'), color=BRAND_CHARCOAL_MED)
                if not congelada and rc[6].button("✕", key=f"ds_{row['id']}"):
                    conn = get_connection(); conn.execute("DELETE FROM cotizacion_subcontratos_detalle WHERE id=?", (row['id'],)); conn.commit(); conn.close(); sync_cotizacion_totals(cot_id); st.rerun()
        else: _empty()
        _sub_bar(f"SUBTOTAL SUB — PARTIDA {num}", sub)
        if not congelada:
            _add_wrap_open()
            fa,fb,fc,fd,fe = st.columns([3.2,.9,1.8,1.4,2.5])
            with fa: _lbl("Descripción *"); ds = st.text_input("d", key=f"sub_d_{pid}", placeholder="Ej: Servicio de Montacargas", label_visibility="collapsed")
            with fb: _lbl("Cant."); cq = st.number_input("c",value=1.,min_value=.01,step=1.,key=f"sub_q_{pid}",label_visibility="collapsed")
            with fc:
                _lbl("Unidad")
                UNIDADES_SUB = [
                    "SERV (Servicio)", "HORAS (Hrs)", "SEMANAS (Sem)", "PZA (Pieza)",
                    "ARREND (Arrendamiento)", "CONTRATO", "DIAS", "LOTE", "JGO", "FLETE",
                    "✍️ Otra unidad libre..."
                ]
                unit_sel = st.selectbox("Unidad", UNIDADES_SUB, key=f"sub_usel_{pid}", label_visibility="collapsed")
                if unit_sel == "✍️ Otra unidad libre...":
                    cu = st.text_input("Unidad Libre", value="SERV", key=f"sub_ucust_{pid}")
                else:
                    cu = unit_sel.split(" ")[0]
            with fd: _lbl("P.U. MXN"); pu = st.number_input("p",value=0.,step=100.,key=f"sub_p_{pid}",label_visibility="collapsed")
            with fe: _lbl("Empresa Subcontratista"); ns = st.text_input("n",key=f"sub_n_{pid}",placeholder="Nombre del proveedor",label_visibility="collapsed")
            if st.button(f"➕ Agregar a P{num}", key=f"sub_add_{pid}", type="primary"):
                if ds.strip():
                    conn = get_connection(); conn.execute("INSERT INTO cotizacion_subcontratos_detalle (cotizacion_id,partida_id,descripcion,cantidad,unidad,pu_mxn,importe_mxn,subcontratista) VALUES(?,?,?,?,?,?,?,?)", (cot_id,pid,ds.strip(),cq,cu.strip(),pu,cq*pu,ns)); conn.commit(); conn.close(); sync_cotizacion_totals(cot_id); st.rerun()
                else: st.error("Descripción requerida.")
            _add_wrap_close()



# ── MAQUINARIA ──────────────────────────────────────────────────────────────
def _costos_maquinaria(cot_id, partidas, congelada):
    tots = []
    for p in partidas:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(total_mxn),0) FROM cotizacion_maquinaria_detalle WHERE partida_id=?", (p['id'],))
        tots.append(cur.fetchone()[0]); conn.close()
    df = pd.DataFrame({"N°":[p['numero_partida'] for p in partidas],"Partida":[p['descripcion'] for p in partidas],"Maquinaria MXN":tots})
    st.dataframe(df.style.format({"Maquinaria MXN":"${:,.2f}"}), use_container_width=True, hide_index=True)
    _gran_total("TOTAL MAQUINARIA", sum(tots))
    st.markdown("<br>", unsafe_allow_html=True)
    LW=[1.,3.5,.9,1.2,1.8,1.8,.5]; LH=["Clave","Equipo","Cant.","Unidad","Costo Unit.","Total MXN",""]
    for p in partidas:
        pid, num, nom = p['id'], p['numero_partida'], p['descripcion']
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM cotizacion_maquinaria_detalle WHERE partida_id=? ORDER BY id", (pid,))
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        sub = sum(r['total_mxn'] for r in rows)
        _ph(num, nom, sub)
        if rows:
            cols_h = st.columns(LW); _hdrs(cols_h, LH)
            for row in rows:
                rc = st.columns(LW)
                _cell(rc[0], row.get('clave',''), color=BRAND_CHARCOAL_MED); _cell(rc[1], row['nombre'], bold=True)
                _cell(rc[2], f"{row['cantidad']:,.2f}"); _cell(rc[3], row['unidad'])
                _cell(rc[4], f"${row['costo_unitario']:,.2f}"); _cell(rc[5], f"${row['total_mxn']:,.2f}", bold=True)
                if not congelada and rc[6].button("✕", key=f"dq_{row['id']}"):
                    conn = get_connection(); conn.execute("DELETE FROM cotizacion_maquinaria_detalle WHERE id=?", (row['id'],)); conn.commit(); conn.close(); sync_cotizacion_totals(cot_id); st.rerun()
        else: _empty()
        _sub_bar(f"SUBTOTAL MAQ — PARTIDA {num}", sub)
        if not congelada:
            _add_wrap_open()
            fa,fb,fc,fd,fe = st.columns([1.,3.5,.9,1.2,1.8])
            with fa: _lbl("Clave"); ck = st.text_input("k",key=f"mq_k_{pid}",label_visibility="collapsed")
            with fb: _lbl("Nombre del Equipo *"); cn = st.text_input("n",key=f"mq_n_{pid}",placeholder="Ej: Grúa telescópica 25 ton",label_visibility="collapsed")
            with fc: _lbl("Cant."); cq = st.number_input("c",value=1.,min_value=.01,step=1.,key=f"mq_q_{pid}",label_visibility="collapsed")
            with fd: _lbl("Unidad"); cu = st.text_input("u",value="DIA",key=f"mq_u_{pid}",label_visibility="collapsed")
            with fe: _lbl("Costo Unitario MXN"); cc2 = st.number_input("p",value=0.,step=100.,key=f"mq_p_{pid}",label_visibility="collapsed")
            if st.button(f"➕ Agregar a P{num}", key=f"mq_add_{pid}", type="primary"):
                if cn.strip():
                    conn = get_connection(); conn.execute("INSERT INTO cotizacion_maquinaria_detalle (cotizacion_id,partida_id,clave,nombre,cantidad,unidad,costo_unitario,total_mxn) VALUES(?,?,?,?,?,?,?,?)", (cot_id,pid,ck,cn.strip(),cq,cu,cc2,cq*cc2)); conn.commit(); conn.close(); sync_cotizacion_totals(cot_id); st.rerun()
                else: st.error("Nombre requerido.")
            _add_wrap_close()


# ── GASTOS GENERALES ────────────────────────────────────────────────────────
def _costos_gastos(cot_id, congelada):
    st.markdown(f"""
    <div style="background:{BRAND_CHARCOAL};color:#fff;padding:10px 20px;border-radius:8px;
                border-left:6px solid {BRAND_ORANGE};margin-bottom:4px;
                font-family:'Montserrat',sans-serif;">
        <span style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;
                     color:{BRAND_ORANGE};">PROYECTO COMPLETO — Gastos Generales de Obra</span><br>
        <span style="font-size:11px;color:#CBD5E1;">
            Se prorratean proporcionalmente entre partidas en el ANÁLISIS final.</span>
    </div>""", unsafe_allow_html=True)
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM cotizacion_gastos_detalle WHERE cotizacion_id=? ORDER BY id", (cot_id,))
    rows = [dict(r) for r in cur.fetchall()]; conn.close()
    total_g = sum(r['importe_total'] for r in rows)
    LW=[3.5,.9,1.2,1.1,1.8,1.8,.5]; LH=["Nombre / Concepto","Cant.","Unidad","Tiempo","Costo Unit.","Importe Total",""]
    if rows:
        cols_h = st.columns(LW); _hdrs(cols_h, LH)
        for row in rows:
            rc = st.columns(LW)
            _cell(rc[0], row['nombre'], bold=True); _cell(rc[1], f"{row['cantidad']:,.1f}")
            _cell(rc[2], row['unidad']); _cell(rc[3], f"{row['tiempo_valor']:,.1f}")
            _cell(rc[4], f"${row['costo_unitario']:,.2f}"); _cell(rc[5], f"${row['importe_total']:,.2f}", bold=True)
            if not congelada and rc[6].button("✕", key=f"dg_{row['id']}"):
                conn = get_connection(); conn.execute("DELETE FROM cotizacion_gastos_detalle WHERE id=?", (row['id'],)); conn.commit(); conn.close(); sync_cotizacion_totals(cot_id); st.rerun()
    else: _empty()
    _sub_bar("SUBTOTAL GASTOS GENERALES", total_g)
    if not congelada:
        _add_wrap_open()
        fa,fb,fc,fd,fe = st.columns([3.5,.9,1.2,1.1,1.8])
        with fa: _lbl("Nombre del Gasto *"); ng = st.text_input("g",key="g_n",placeholder="Ej: Viáticos / Combustible",label_visibility="collapsed")
        with fb: _lbl("Cant."); gq = st.number_input("gc",value=1.,min_value=.01,step=1.,key="g_q",label_visibility="collapsed")
        with fc: _lbl("Unidad"); gu = st.text_input("gu",value="VJE",key="g_u",label_visibility="collapsed")
        with fd: _lbl("Tiempo"); gt = st.number_input("gt",value=1.,min_value=0.,step=1.,key="g_t",label_visibility="collapsed")
        with fe: _lbl("Costo Unit. MXN"); gp = st.number_input("gp",value=0.,step=50.,key="g_p",label_visibility="collapsed")
        imp_g = gq*gt*gp
        if imp_g > 0: st.markdown(f"<span style='font-size:12px;color:{BRAND_CHARCOAL_MED};'>Importe: <b style='color:{BRAND_ORANGE};'>${imp_g:,.2f}</b></span>", unsafe_allow_html=True)
        if st.button("➕ Agregar Gasto General", key="g_add", type="primary"):
            if ng.strip():
                conn = get_connection(); conn.execute("INSERT INTO cotizacion_gastos_detalle (cotizacion_id,nombre,cantidad,unidad,tiempo_valor,costo_unitario,importe_total) VALUES(?,?,?,?,?,?,?)", (cot_id,ng.strip(),gq,gu,gt,gp,imp_g)); conn.commit(); conn.close(); sync_cotizacion_totals(cot_id); st.rerun()
            else: st.error("Nombre requerido.")
        _add_wrap_close()


# ─────────────────────────────────────────────────────────────────────────────
# PASO 4: REVISIÓN, ANÁLISIS Y CONGELAMIENTO
# ─────────────────────────────────────────────────────────────────────────────
def _step4_revision(cot_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM cotizaciones WHERE id=?", (cot_id,))
    cot = dict(cur.fetchone())
    cur.execute("""SELECT p.*,
                      COALESCE((SELECT SUM(importe_mxn) FROM cotizacion_materiales_detalle WHERE partida_id=p.id),0) as mat,
                      COALESCE((SELECT SUM(importe_total) FROM cotizacion_mo_detalle WHERE partida_id=p.id),0) as mo,
                      COALESCE((SELECT SUM(importe_mxn) FROM cotizacion_subcontratos_detalle WHERE partida_id=p.id),0) as sub,
                      COALESCE((SELECT SUM(total_mxn) FROM cotizacion_maquinaria_detalle WHERE partida_id=p.id),0) as maq
                   FROM cotizacion_partidas p WHERE p.cotizacion_id=? ORDER BY p.numero_partida""",
               (cot_id,))
    partidas = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT COALESCE(SUM(importe_total),0) FROM cotizacion_gastos_detalle WHERE cotizacion_id=?", (cot_id,))
    total_gastos = cur.fetchone()[0]
    conn.close()

    congelada = bool(cot.get('congelada'))
    mg = float(cot['margen_porcentaje']); cm = float(cot['comision_porcentaje'])
    sv = float(cot.get('supervision_porcentaje', 0.30))
    hta_pct = float(cot.get('herramienta_porcentaje', 0.03))

    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 4 — Revisión y Aprobación</h2>
        <p>ANÁLISIS financiero de <b>{cot['folio']}</b> · Revisión {cot['revision']}</p>
    </div>""", unsafe_allow_html=True)

    # ── ESTADO ────────────────────────────────────────────────────────────────
    est = cot.get('estatus','Borrador')
    estado_color = {
        'Borrador': '#64748B', 'En Revisión': '#D97706',
        'Aprobada': '#059669', 'Congelada': BRAND_ORANGE
    }.get(est, BRAND_CHARCOAL_MED)

    st.markdown(f"""
    <div style="display:flex;gap:16px;align-items:center;margin-bottom:16px;">
        <div style="background:{estado_color}22;border:2px solid {estado_color};border-radius:8px;
                    padding:8px 20px;font-family:'Montserrat',sans-serif;">
            <span style="font-size:10px;font-weight:700;color:{estado_color};text-transform:uppercase;">Estado</span><br>
            <span style="font-size:18px;font-weight:900;color:{estado_color};">{'🔒 ' if congelada else ''}{est}</span>
        </div>
        <div style="font-family:'Montserrat',sans-serif;">
            <span style="font-size:12px;color:{BRAND_CHARCOAL_MED};">Aprobada por:</span>
            <b style="color:{BRAND_CHARCOAL};"> {cot.get('aprobado_por','—')}</b><br>
            <span style="font-size:12px;color:{BRAND_CHARCOAL_MED};">Fecha:</span>
            <b style="color:{BRAND_CHARCOAL};"> {cot.get('fecha_aprobacion','—')}</b>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── ANÁLISIS POR PARTIDA ──────────────────────────────────────────────────
    analisis_rows = []
    total_cd = 0.
    n_parts = max(len(partidas), 1)

    for p in partidas:
        mat = p['mat']; mo = p['mo']; sub = p['sub']; maq = p['maq']
        sup  = mo * sv
        hta  = (mat + mo) * hta_pct
        gas_part = total_gastos / n_parts
        cd   = mat + mo + sup + hta + sub + maq + gas_part
        total_cd += cd
        pv   = cd / (1 - mg - cm) if (1 - mg - cm) > 0 else cd
        analisis_rows.append({
            "N°": p['numero_partida'], "Partida": p['descripcion'][:40],
            "Materiales": mat, "M.O.": mo, "Supervisión": sup,
            "Herramienta": hta, "Subcontratos": sub, "Maquinaria": maq,
            "Gastos (part.)": gas_part, "Costo Directo": cd,
            "Precio Venta": pv, "Margen $": pv - cd
        })

    df_an = pd.DataFrame(analisis_rows)
    money_cols = [c for c in df_an.columns if c not in ("N°", "Partida")]
    st.dataframe(df_an.style.format({c: "${:,.2f}" for c in money_cols}),
                 use_container_width=True, hide_index=True, height=min(300, 40 + len(partidas)*38))

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_pv   = sum(r['Precio Venta'] for r in analisis_rows)
    total_mg   = sum(r['Margen $']     for r in analisis_rows)
    total_mat  = sum(r['Materiales']   for r in analisis_rows)
    total_mo   = sum(r['M.O.']         for r in analisis_rows)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    def _kpi(col, label, val, fmt="${:,.2f}", color=BRAND_ORANGE):
        col.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};
                    border-top:4px solid {color};border-radius:8px;padding:14px 16px;
                    font-family:'Montserrat',sans-serif;">
            <p style="font-size:10px;font-weight:700;text-transform:uppercase;
                      color:{BRAND_CHARCOAL_MED};margin:0;">{label}</p>
            <p style="font-size:22px;font-weight:900;color:{BRAND_CHARCOAL};margin:4px 0 0 0;">{fmt.format(val)}</p>
        </div>""", unsafe_allow_html=True)

    _kpi(kpi1, "Precio de Venta Total",   total_pv)
    _kpi(kpi2, "Utilidad Bruta",          total_mg,  color="#059669")
    _kpi(kpi3, "Margen Real",             (total_mg/total_pv*100) if total_pv else 0, fmt="{:,.1f}%", color="#0EA5E9")
    _kpi(kpi4, "Costo Directo Total",     total_cd,  color=BRAND_CHARCOAL)

    # ── GRÁFICA ────────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    df_pie = pd.DataFrame({"Concepto": ["Materiales","M.O.","Supervisión","Subcontratos","Maquinaria","Gastos","Margen"],
                            "Monto":    [total_mat, total_mo,
                                         sum(r['Supervisión'] for r in analisis_rows),
                                         sum(r['Subcontratos'] for r in analisis_rows),
                                         sum(r['Maquinaria'] for r in analisis_rows),
                                         total_gastos, total_mg]})
    df_pie = df_pie[df_pie['Monto'] > 0]
    if not df_pie.empty:
        fig = px.pie(df_pie, names='Concepto', values='Monto',
                     color_discrete_sequence=[BRAND_ORANGE,'#434E62','#64748B','#94A3B8','#CBD5E1','#E2E8F0','#059669'],
                     hole=.45)
        fig.update_layout(margin=dict(t=20,b=20,l=0,r=0), height=280,
                          font_family="Montserrat",
                          legend=dict(orientation="v", font_size=11))
        fig.update_traces(textfont_family="Montserrat")
        c_pie, c_bar = st.columns([2, 3])
        with c_pie: st.plotly_chart(fig, use_container_width=True)
        with c_bar:
            fig2 = px.bar(pd.DataFrame({"Partida": [f"P{r['N°']}" for r in analisis_rows],
                                         "C.Directo": [r['Costo Directo'] for r in analisis_rows],
                                         "P.Venta":   [r['Precio Venta'] for r in analisis_rows]}),
                          x="Partida", y=["C.Directo","P.Venta"], barmode="group",
                          color_discrete_map={"C.Directo": BRAND_CHARCOAL, "P.Venta": BRAND_ORANGE})
            fig2.update_layout(margin=dict(t=20,b=20,l=0,r=0), height=280,
                               font_family="Montserrat", legend_title="",
                               plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── ACCIONES DE VERSIÓN / CONGELAMIENTO ───────────────────────────────────
    st.markdown(f"""<p style="font-size:11px;font-weight:800;text-transform:uppercase;
                    color:{BRAND_ORANGE};margin:0 0 10px 0;">CONTROL DE VERSIÓN Y APROBACIÓN</p>""",
                unsafe_allow_html=True)

    if not congelada:
        ca, cb = st.columns([3, 2])
        with ca:
            aprobado_por = st.text_input("Aprobada / Autorizada por",
                                          value=cot.get('aprobado_por',''),
                                          placeholder="Nombre del responsable de aprobación")
            nuevo_estatus = st.selectbox("Cambiar Estado a",
                                          ["Borrador","En Revisión","Aprobada"],
                                          index=["Borrador","En Revisión","Aprobada"].index(est) if est in ["Borrador","En Revisión","Aprobada"] else 0)
        with cb:
            st.markdown(f"""
            <div style="background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;
                        padding:12px 16px;font-family:'Montserrat',sans-serif;">
                <p style="font-size:11px;font-weight:700;color:#92400E;margin:0 0 6px 0;">
                    ⚠️ CONGELAR COTIZACIÓN</p>
                <p style="font-size:11px;color:#78350F;margin:0;">
                    Al congelar, la cotización queda en modo lectura.
                    Podrás crear una nueva revisión (R1, R2…) sin perder la versión aprobada.</p>
            </div>""", unsafe_allow_html=True)

        bc1, bc2 = st.columns([2, 2])
        with bc1:
            if st.button("💾 Guardar Estado", type="primary", use_container_width=True):
                conn = get_connection()
                conn.execute("UPDATE cotizaciones SET estatus=?, aprobado_por=? WHERE id=?",
                             (nuevo_estatus, aprobado_por, cot_id))
                conn.commit(); conn.close()
                st.success(f"Estado actualizado a **{nuevo_estatus}**."); st.rerun()
        with bc2:
            if st.button("🔒 Aprobar y CONGELAR Cotización", use_container_width=True):
                conn = get_connection()
                conn.execute("""UPDATE cotizaciones SET
                                estatus='Aprobada', congelada=1,
                                aprobado_por=?, fecha_aprobacion=CURRENT_TIMESTAMP
                                WHERE id=?""", (aprobado_por or "J&D Automation", cot_id))
                conn.commit(); conn.close()
                st.success("🔒 Cotización CONGELADA y aprobada."); st.rerun()
    else:
        st.success(f"🔒 Esta cotización está congelada y aprobada por: **{cot.get('aprobado_por','—')}**")
        if st.button("🔄 Crear Nueva Revisión (R+1)", type="primary"):
            import re
            rev = cot.get('revision','R0')
            num_r = int(re.sub(r'\D','',rev) or '0') + 1
            new_rev = f"R{num_r}"
            parts = cot['folio'].split('-')
            # Reemplazar revisión en el folio si aplica, o simplemente actualizar
            conn = get_connection()
            conn.execute("""UPDATE cotizaciones SET
                            revision=?, congelada=0, estatus='Borrador',
                            fecha_aprobacion=NULL, aprobado_por=NULL
                            WHERE id=?""", (new_rev, cot_id))
            conn.commit(); conn.close()
            st.success(f"Nueva revisión **{new_rev}** creada. La cotización está desbloqueada."); st.rerun()

    _nav_buttons(4, max_step=5)


# ─────────────────────────────────────────────────────────────────────────────
# PASO 5: GANTT
# ─────────────────────────────────────────────────────────────────────────────
def _step5_gantt(cot_id, congelada):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT folio FROM cotizaciones WHERE id=?", (cot_id,))
    cot = dict(cur.fetchone())
    cur.execute("SELECT * FROM cotizacion_partidas WHERE cotizacion_id=? ORDER BY numero_partida", (cot_id,))
    partidas = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT g.*, p.numero_partida, p.descripcion as partida_desc FROM cotizacion_gantt g LEFT JOIN cotizacion_partidas p ON g.partida_id=p.id WHERE g.cotizacion_id=? ORDER BY g.orden, g.id", (cot_id,))
    gantt_rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 5 — Cronograma del Proyecto (Gantt)</h2>
        <p>Tiempos aproximados de ejecución de <b>{cot['folio']}</b></p>
    </div>""", unsafe_allow_html=True)

    # ── FORMULARIO NUEVA ACTIVIDAD ─────────────────────────────────────────────
    if not congelada:
        part_opts = {f"P{p['numero_partida']} — {p['descripcion'][:40]}": p['id'] for p in partidas}
        part_opts["— Actividad general del proyecto —"] = None

        st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;color:{BRAND_ORANGE};margin:0 0 8px 0;'>AGREGAR ACTIVIDAD</p>", unsafe_allow_html=True)
        with st.form("form_gantt", clear_on_submit=True):
            gc1, gc2 = st.columns([3, 2])
            with gc1: act_name = st.text_input("Nombre de la Actividad *", placeholder="Ej: Fabricación de tablero eléctrico")
            with gc2:
                part_sel = st.selectbox("Partida asociada", list(part_opts.keys()))
                part_id_g = part_opts[part_sel]
            gc3, gc4, gc5, gc6 = st.columns([1.5, 1.5, 1.2, 2])
            with gc3:
                fecha_ini = st.date_input("Fecha de Inicio", value=date.today())
            with gc4:
                dias_dur = st.number_input("Duración (días)", value=5, min_value=1, step=1)
            with gc5:
                tipo_act = st.selectbox("Tipo", ["Actividad","Entregable","Hito","Reunión"])
            with gc6:
                resp_g = st.text_input("Responsable", placeholder="Ej: RG — Rodrigo González")
            if st.form_submit_button("➕ Agregar al Cronograma", type="primary"):
                if act_name.strip():
                    conn = get_connection()
                    conn.execute("""INSERT INTO cotizacion_gantt
                                    (cotizacion_id,partida_id,actividad,tipo,responsable,
                                     fecha_inicio,dias_duracion,orden)
                                    VALUES(?,?,?,?,?,?,?,?)""",
                                 (cot_id, part_id_g, act_name.strip(), tipo_act,
                                  resp_g, str(fecha_ini), dias_dur, len(gantt_rows)+1))
                    conn.commit(); conn.close(); st.rerun()
                else: st.error("El nombre de la actividad es requerido.")

    # ── TABLA DE ACTIVIDADES ──────────────────────────────────────────────────
    if gantt_rows:
        # Construir datos para Plotly Gantt
        gantt_data = []
        for row in gantt_rows:
            try:
                fi = datetime.strptime(str(row['fecha_inicio']), "%Y-%m-%d").date()
            except:
                fi = date.today()
            ff = fi + timedelta(days=int(row['dias_duracion'] or 1))
            pn = f"P{row['numero_partida']}" if row.get('numero_partida') else "General"
            gantt_data.append({
                "Actividad": row['actividad'],
                "Partida":   pn,
                "Inicio":    datetime.combine(fi, datetime.min.time()),
                "Fin":       datetime.combine(ff, datetime.min.time()),
                "Tipo":      row.get('tipo','Actividad'),
                "Responsable": row.get('responsable','—'),
            })

        df_g = pd.DataFrame(gantt_data)
        tipo_colors = {
            "Actividad":  BRAND_ORANGE,
            "Entregable": "#059669",
            "Hito":       "#DC2626",
            "Reunión":    "#0EA5E9",
        }
        fig_g = px.timeline(df_g, x_start="Inicio", x_end="Fin",
                            y="Actividad", color="Tipo",
                            color_discrete_map=tipo_colors,
                            hover_data=["Partida","Responsable","Tipo"])
        fig_g.update_yaxes(autorange="reversed")
        fig_g.update_layout(
            height=max(250, 55 + len(gantt_data) * 35),
            margin=dict(t=10, b=30, l=10, r=10),
            font_family="Montserrat", legend_title="",
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor='#E2E8F0'),
        )
        st.plotly_chart(fig_g, use_container_width=True)

        # Lista con botón eliminar
        st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;color:{BRAND_CHARCOAL_MED};margin:12px 0 4px 0;'>ACTIVIDADES REGISTRADAS</p>", unsafe_allow_html=True)
        for row in gantt_rows:
            rc = st.columns([.5, 3.5, 1.5, 1, 1.5, 1.8, .5])
            rc[0].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:4px 0;'>{row.get('numero_partida','—')}</p>", unsafe_allow_html=True)
            rc[1].markdown(f"<p style='font-size:13px;font-weight:700;color:{BRAND_CHARCOAL};margin:4px 0;'>{row['actividad']}</p>", unsafe_allow_html=True)
            rc[2].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:4px 0;'>{row.get('tipo','')}</p>", unsafe_allow_html=True)
            rc[3].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:4px 0;'>{row['fecha_inicio']}</p>", unsafe_allow_html=True)
            rc[4].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:4px 0;'>{row['dias_duracion']} días</p>", unsafe_allow_html=True)
            rc[5].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:4px 0;'>{row.get('responsable','—')}</p>", unsafe_allow_html=True)
            if not congelada and rc[6].button("✕", key=f"dg_{row['id']}"):
                conn = get_connection()
                conn.execute("DELETE FROM cotizacion_gantt WHERE id=?", (row['id'],))
                conn.commit(); conn.close(); st.rerun()
    else:
        st.info("Aún no hay actividades en el cronograma. Agrégalas arriba.")
        fig_empty = px.timeline(pd.DataFrame({"Actividad":["Agrega actividades"],"Inicio":[datetime.today()],"Fin":[datetime.today()+timedelta(days=7)],"Tipo":["Ejemplo"]}), x_start="Inicio",x_end="Fin",y="Actividad",color="Tipo",color_discrete_map={"Ejemplo":BRAND_ORANGE+"44"})
        fig_empty.update_layout(height=120, margin=dict(t=5,b=20,l=10,r=10), font_family="Montserrat", showlegend=False, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_empty, use_container_width=True)

    _nav_buttons(5)
