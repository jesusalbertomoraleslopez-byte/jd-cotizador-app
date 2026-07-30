"""
Creador y Editor de Cotizaciones — J&D Automation Industries
Estructura guiada en 5 Pasos:
1. Cliente, Usuario/Contacto, Ing. Responsable, Nombre del Proyecto → Folio (COT-082-YES-RG-CONTROL PID MOLINOS)
2. Alta de Partidas
3. Detalle de Costos (Materiales, M.O. con FASAR/HH, Subcontratos, Maquinaria, Gastos)
4. Dashboard ANÁLISIS, Márgenes, Estatus y Congelamiento de Versión
5. Cronograma Gantt
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta

from database.models import get_connection, init_db
from database.db_manager import (
    get_catalogo_materiales,
    get_catalogo_mano_obra,
    get_catalogo_gastos,
    get_catalogo_subcontratos,
    sync_cotizacion_totals
)
from config import (
    BRAND_ORANGE, BRAND_CHARCOAL, BRAND_CHARCOAL_MED,
    BRAND_WHITE, BRAND_BORDER_LIGHT, BRAND_GRAY_BG
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE RENDER Y FORMATO
# ─────────────────────────────────────────────────────────────────────────────

def _partida_header(num, nombre, subtotal=None):
    badge = f"<span style='float:right;font-size:24px;font-weight:900;color:{BRAND_ORANGE};'>${subtotal:,.2f} MXN</span>" if subtotal is not None else ""
    st.markdown(f"""
    <div style="
        background:{BRAND_CHARCOAL};
        color:#FFFFFF;
        padding:14px 22px;
        border-radius:10px 10px 0 0;
        border-left:8px solid {BRAND_ORANGE};
        margin-top:28px;
        overflow:hidden;
        font-family:'Montserrat',sans-serif;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    ">
        <span style="font-size:13px;font-weight:900;text-transform:uppercase;
                     letter-spacing:2px;color:{BRAND_ORANGE};">PARTIDA {num}</span>
        {badge}
        <br>
        <span style="font-size:24px;font-weight:900;letter-spacing:0.5px;line-height:1.3;">{nombre}</span>
    </div>
    """, unsafe_allow_html=True)


def _col_header_row(labels_widths):
    cols = st.columns([w for _, w in labels_widths])
    for col, (lbl, _) in zip(cols, labels_widths):
        col.markdown(f"<p style='font-size:10px;font-weight:800;text-transform:uppercase;"
                     f"color:{BRAND_CHARCOAL_MED};margin:8px 0 2px 0;letter-spacing:.5px;'>{lbl}</p>",
                     unsafe_allow_html=True)


def _empty_partition_row():
    st.markdown(f"""
    <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};
                border-top:none;padding:12px 20px;font-family:'Montserrat',sans-serif;
                color:{BRAND_CHARCOAL_MED};font-size:12px;font-style:italic;">
        ─── Sin registros en esta partida aún. ───
    </div>""", unsafe_allow_html=True)


def _subtotal_bar(label, total):
    st.markdown(f"""
    <div style="
        background:linear-gradient(90deg,{BRAND_CHARCOAL},#3a4455);
        color:#fff;padding:9px 20px;
        display:flex;justify-content:space-between;align-items:center;
        font-family:'Montserrat',sans-serif;
    ">
        <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;">{label}</span>
        <span style="font-size:16px;font-weight:800;color:{BRAND_ORANGE};">${total:,.2f} MXN</span>
    </div>""", unsafe_allow_html=True)


def _grand_total_bar(label, total):
    st.markdown(f"""
    <div style="
        background:{BRAND_ORANGE};color:#fff;
        padding:13px 22px;border-radius:8px;margin-top:20px;
        display:flex;justify-content:space-between;align-items:center;
        font-family:'Montserrat',sans-serif;
    ">
        <span style="font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:1px;">{label}</span>
        <span style="font-size:21px;font-weight:900;">${total:,.2f} MXN</span>
    </div>""", unsafe_allow_html=True)


def _add_form_wrapper_open():
    st.markdown(f"""
    <div style="
        background:#F8F9FB;
        border:1px solid {BRAND_BORDER_LIGHT};
        border-top:2px dashed {BRAND_ORANGE}44;
        border-radius:0 0 8px 8px;
        padding:10px 16px 14px 16px;
        margin-bottom:4px;
    ">""", unsafe_allow_html=True)


def _add_form_wrapper_close():
    st.markdown("</div>", unsafe_allow_html=True)


def _section_label(text):
    st.markdown(f"<p style='font-size:10px;font-weight:800;text-transform:uppercase;"
                f"color:{BRAND_CHARCOAL_MED};letter-spacing:.8px;margin:0 0 2px 0;'>{text}</p>",
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MÓDULO PRINCIPAL DEL CREADOR
# ─────────────────────────────────────────────────────────────────────────────

def render_cotizador_editor():
    init_db()

    # ── Selector de Cotización Activa o Crear Nueva ──────────────────────────
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.folio, c.proyecto, c.congelada, COALESCE(c.revision, 'R0') as revision, COALESCE(cl.nombre,'—') as cliente
        FROM cotizaciones c LEFT JOIN clientes cl ON c.cliente_id = cl.id
        ORDER BY c.id DESC
    """)
    cots = [dict(r) for r in cursor.fetchall()]
    conn.close()

    col_sel, col_new = st.columns([4, 1.2])

    if not cots:
        st.info("No hay cotizaciones registradas. Crea una nueva usando el botón a la derecha.")
        cot_id = None
    else:
        import re
        cot_labels = {
            f"{'🔒 ' if c['congelada'] else '✏️ '}{re.sub(r'\\s*\\(R\\d+\\)$', '', c['folio']).strip()} ({c.get('revision','R0')}) — {(c.get('proyecto') or '')[:38]} ({c.get('cliente','—')})": c['id']
            for c in cots
        }
        sel_label = col_sel.selectbox("📌 Cotización Activa a Editar / Construir", list(cot_labels.keys()))
        cot_id = cot_labels[sel_label]


    if col_new.button("➕ Nueva Cotización", type="primary", use_container_width=True):
        # Crear cotización borrador inicial
        conn = get_connection()
        conn.execute("INSERT INTO cotizaciones (folio, proyecto, estatus) VALUES (?, ?, 'Borrador')",
                     ("COT-001-NUEVA-PROYECTO", "NUEVO PROYECTO"))
        conn.commit()
        cur = conn.cursor()
        cur.execute("SELECT id FROM cotizaciones ORDER BY id DESC LIMIT 1")
        new_id = cur.fetchone()['id']
        conn.close()
        st.success("Nueva cotización iniciada. Completa el Paso 1.")
        st.rerun()

    if not cot_id:
        return

    # Cargar datos de la cotización activa
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM cotizaciones WHERE id=?", (cot_id,))
    cot_info = dict(cursor.fetchone())
    cursor.execute("SELECT * FROM cotizacion_partidas WHERE cotizacion_id=? ORDER BY numero_partida", (cot_id,))
    partidas = [dict(r) for r in cursor.fetchall()]
    conn.close()

    tc = float(cot_info.get('tipo_cambio_usd', 18.0))
    congelada = bool(cot_info.get('congelada', 0))

    if congelada:
        st.warning("🔒 Esta cotización está **Aprobada y Congelada**. Está en modo lectura. "
                   "Para editar, ve al **Paso 4** y presiona 'Crear Nueva Revisión'.")

    # ── PESTAÑAS / PASOS PRINCIPALES DE LA COTIZACIÓN ──────────────
    tabs = st.tabs([
        "📋 Paso 1: Cliente & Folio",
        "📑 Paso 2: Partidas del Proyecto",
        "💰 Paso 3: Detalle de Costos por Partida",
        "📊 Paso 4: ANÁLISIS, Márgenes & Versión",
    ])

    with tabs[0]:
        _paso1_cliente_folio(cot_id, cot_info, congelada)

    with tabs[1]:
        _paso2_partidas(cot_id, cot_info, partidas, congelada)

    with tabs[2]:
        _paso3_costos_partidas(cot_id, partidas, tc, congelada)

    with tabs[3]:
        _paso4_analisis_version(cot_id, cot_info, partidas)



# ─────────────────────────────────────────────────────────────────────────────
# PASO 1: CLIENTE, USUARIO, INGENIERO, PROYECTO Y FOLIO
# ─────────────────────────────────────────────────────────────────────────────

def _paso1_cliente_folio(cot_id, cot_info, congelada):
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 1 — Cliente, Usuario, Proyecto & Folio Oficial</h2>
        <p>Selecciona el cliente, el contacto, el ingeniero responsable y define el proyecto.</p>
    </div>""", unsafe_allow_html=True)

    # Cargar catálogos de clientes e ingenieros
    conn = get_connection(); cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, COALESCE(acronimo,'CLI') as acronimo FROM clientes WHERE activo=1 ORDER BY nombre")
    clientes_db = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT iniciales, nombre, apellido FROM jd_ingenieros WHERE activo=1 ORDER BY iniciales")
    ings_db = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not clientes_db:
        st.warning("⚠️ No hay clientes registrados. Ve al menú **🏢 Clientes** para dar de alta al menos uno.")
        return

    if not ings_db:
        st.warning("⚠️ No hay ingenieros J&D registrados. Ve al menú **🏢 Clientes → Ingenieros J&D**.")
        return

    # 1. Selección Cliente
    cl_opts = {f"{c['nombre']} [{c['acronimo']}]": c for c in clientes_db}
    curr_cl_name = ""
    if cot_info.get('cliente_id'):
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT nombre FROM clientes WHERE id=?", (cot_info['cliente_id'],))
        r = cur.fetchone(); conn.close()
        if r: curr_cl_name = r['nombre']
    curr_cl_idx = 0
    for i, k in enumerate(cl_opts.keys()):
        if curr_cl_name and curr_cl_name in k:
            curr_cl_idx = i; break

    c1, c2 = st.columns([4, 2])
    with c1:
        cl_sel = st.selectbox("Empresa Cliente *", list(cl_opts.keys()), index=curr_cl_idx, key="p1_cl", disabled=congelada)
        cl_obj = cl_opts[cl_sel]
        acr_cl = cl_obj['acronimo'].upper()

    # Contactos del cliente
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT id, nombre, apellido, cargo, iniciales
                   FROM clientes_contactos WHERE cliente_id=? ORDER BY es_principal DESC, nombre""",
                (cl_obj['id'],))
    contactos = [dict(r) for r in cur.fetchall()]; conn.close()

    con_opts = {f"{c['nombre']} {c.get('apellido','')} — {c.get('cargo','')}"[:50]: c for c in contactos}
    con_opts_list = ["— Sin contacto específico —"] + list(con_opts.keys())
    curr_con = cot_info.get('nombre_contacto','')
    curr_con_idx = 0
    for i, k in enumerate(con_opts_list):
        if curr_con and curr_con in k:
            curr_con_idx = i; break

    with c2:
        con_sel = st.selectbox("Contacto del Cliente (Usuario)", con_opts_list, index=curr_con_idx, key="p1_con", disabled=congelada)

    # 2. Ingeniero Responsable y Proyecto
    ing_opts = {f"{i['iniciales']} — {i['nombre']} {i.get('apellido','')}": i['iniciales'] for i in ings_db}
    curr_ing = cot_info.get('ingeniero_id', list(ing_opts.values())[0] if ing_opts else '')
    curr_ing_idx = list(ing_opts.values()).index(curr_ing) if curr_ing in ing_opts.values() else 0

    p1, p2, p3 = st.columns([2, 4, 1.5])
    with p1:
        ing_sel = st.selectbox("Ingeniero Responsable *", list(ing_opts.keys()), index=curr_ing_idx, key="p1_ing", disabled=congelada)
        iniciales = ing_opts[ing_sel]
    with p2:
        proyecto = st.text_input("Nombre del Proyecto (para el folio) *", value=cot_info.get('proyecto',''), placeholder="Ej: CONTROL PID MOLINOS", key="p1_proy", disabled=congelada)
    with p3:
        revision_opts = ["R0","R1","R2","R3","R4","R5","R6","R7","R8","R9"]
        curr_rev = cot_info.get('revision','R0')
        curr_rev_idx = revision_opts.index(curr_rev) if curr_rev in revision_opts else 0
        revision = st.selectbox("Revisión", revision_opts, index=curr_rev_idx, key="p1_rev", disabled=congelada)

    # 3. Cálculo de Consecutivo y Folio Oficial: COT-CONSECUTIVO-CLIENTE-ING-PROYECTO
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM cotizaciones WHERE id != ?", (cot_id,))
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
    folio_gen  = f"COT-{consec:03d}-{acr_cl}-{iniciales}-{proy_clean}"

    st.markdown(f"""
    <div style="background:{BRAND_CHARCOAL};color:#fff;padding:14px 22px;border-radius:10px;
                border-left:6px solid {BRAND_ORANGE};margin:14px 0 18px 0;
                font-family:'Montserrat',sans-serif;">
        <span style="font-size:10px;font-weight:800;text-transform:uppercase;
                     color:{BRAND_ORANGE};letter-spacing:1.5px;">ESTRUCTURA DE FOLIO GENERADO AUTOMÁTICAMENTE</span><br>
        <span style="font-size:26px;font-weight:900;letter-spacing:1.5px;">{folio_gen}</span>
        <div style="display:flex;gap:18px;margin-top:8px;font-size:11px;color:#CBD5E1;flex-wrap:wrap;">
            <span><b style="color:{BRAND_ORANGE};">COT</b> = Cotización</span>
            <span><b style="color:{BRAND_ORANGE};">{consec:03d}</b> = Consecutivo</span>
            <span><b style="color:{BRAND_ORANGE};">{acr_cl}</b> = {cl_sel}</span>
            <span><b style="color:{BRAND_ORANGE};">{iniciales}</b> = Ingeniero responsable</span>
            <span><b style="color:{BRAND_ORANGE};">{proy_clean}</b> = Proyecto</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 4. Parámetros Financieros
    st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                f"color:{BRAND_ORANGE};margin:10px 0 8px 0;'>Parámetros Financieros Globales</p>",
                unsafe_allow_html=True)

    with st.form("form_p1_fin"):
        fa, fb, fc, fd = st.columns([2, 1.5, 1.5, 1.5])
        with fa: tc = st.number_input("Tipo de Cambio (MXN/USD)", value=float(cot_info.get('tipo_cambio_usd', 18.0)), step=0.10, disabled=congelada)
        with fb: mg = st.number_input("Margen Utilidad (%)", value=round(float(cot_info.get('margen_porcentaje', 0.30))*100, 1), step=1.0, disabled=congelada)
        with fc: cm = st.number_input("Comisión (%)", value=round(float(cot_info.get('comision_porcentaje', 0.05))*100, 1), step=1.0, disabled=congelada)
        with fd: sv = st.number_input("Supervisión (%)", value=round(float(cot_info.get('supervision_porcentaje', 0.30))*100, 1), step=1.0, disabled=congelada)

        submitted_p1 = st.form_submit_button(
            "💾 Guardar Datos del Proyecto y Folio" if not congelada else "🔒 Cotización Congelada (Modo Lectura)",
            type="primary" if not congelada else "secondary",
            disabled=congelada
        )

        if submitted_p1 and not congelada:
            if not proyecto.strip():
                st.error("El nombre del proyecto es requerido.")
            else:
                nom_contacto = ""
                if con_sel != "— Sin contacto específico —" and con_sel in con_opts:
                    cobj = con_opts[con_sel]
                    nom_contacto = f"{cobj['nombre']} {cobj.get('apellido','')}"

                conn = get_connection()
                conn.execute("""UPDATE cotizaciones SET
                                folio=?, proyecto=?, revision=?, cliente_id=?,
                                tipo_cambio_usd=?, margen_porcentaje=?,
                                comision_porcentaje=?, supervision_porcentaje=?,
                                ingeniero_id=?, nombre_contacto=?
                                WHERE id=?""",
                             (folio_gen, proyecto.strip(), revision, cl_obj['id'],
                              tc, mg/100, cm/100, sv/100,
                              iniciales, nom_contacto, cot_id))
                conn.commit(); conn.close()
                st.success(f"✅ Cotización guardada con Folio: **{folio_gen}**")
                st.rerun()



# ─────────────────────────────────────────────────────────────────────────────
# PASO 2: PARTIDAS DEL PROYECTO
# ─────────────────────────────────────────────────────────────────────────────

def _paso2_partidas(cot_id, cot_info, partidas, congelada):
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 2 — Conceptos y Partidas del Proyecto</h2>
        <p>Da de alta las partidas de obra para <b>{cot_info['folio']}</b></p>
    </div>""", unsafe_allow_html=True)

    if partidas:
        for p in partidas:
            ca, cb, cc = st.columns([0.5, 7, 0.6])
            ca.markdown(f"<div style='background:{BRAND_ORANGE};color:#fff;border-radius:4px;text-align:center;"
                        f"padding:5px 0;font-weight:800;'>{p['numero_partida']}</div>", unsafe_allow_html=True)
            cb.markdown(f"<p style='font-size:13px;color:{BRAND_CHARCOAL};font-weight:600;margin:5px 0;'>{p['descripcion']}</p>",
                        unsafe_allow_html=True)
            if not congelada and cc.button("✕", key=f"del_p_{p['id']}"):
                conn = get_connection()
                conn.execute("DELETE FROM cotizacion_partidas WHERE id=?", (p['id'],))
                conn.commit(); conn.close()
                sync_cotizacion_totals(cot_id); st.rerun()

    else:
        st.info("Aún no hay partidas registradas. Agrega la primera partida del proyecto abajo.")

    if not congelada:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("➕ Agregar Nueva Partida", expanded=not bool(partidas)):
            with st.form("form_new_p"):
                nc, dc = st.columns([1, 5])
                num_p  = nc.number_input("N° Partida", value=len(partidas)+1, min_value=1, step=1)
                desc_p = dc.text_input("Descripción de la Partida *", placeholder="Ej: TABLERO DE CONTROL DE CORRIENTE MOLINOS 1,2 Y 3")
                if st.form_submit_button("Guardar Partida", type="primary"):
                    if desc_p.strip():
                        conn = get_connection()
                        conn.execute("INSERT INTO cotizacion_partidas (cotizacion_id,numero_partida,descripcion) VALUES(?,?,?)",
                                     (cot_id, num_p, desc_p.strip()))
                        conn.commit(); conn.close(); st.rerun()
                    else:
                        st.error("La descripción es requerida.")


# ─────────────────────────────────────────────────────────────────────────────
# PASO 3: DETALLE DE COSTOS POR PARTIDA (SUB-PESTAÑAS)
# ─────────────────────────────────────────────────────────────────────────────

def _paso3_costos_partidas(cot_id, partidas, tc, congelada):
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 3 — Detalle de Costos por Partida</h2>
        <p>Muestra primero la tabla resumen superior y al hacer scroll el desglose y formulario rápido de captura.</p>
    </div>""", unsafe_allow_html=True)

    if not partidas:
        st.warning("Primero debes dar de alta al menos una partida en el **Paso 2**.")
        return

    sub_tabs = st.tabs([
        "🔩 Materiales",
        "👷 Mano de Obra",
        "🤝 Subcontratos",
        "🚜 Maquinaria",
        "✈️ Gastos Generales",
    ])

    with sub_tabs[0]: _render_materiales(cot_id, partidas, tc, congelada)
    with sub_tabs[1]: _render_mano_obra(cot_id, partidas, congelada)
    with sub_tabs[2]: _render_subcontratos(cot_id, partidas, congelada)
    with sub_tabs[3]: _render_maquinaria(cot_id, partidas, congelada)
    with sub_tabs[4]: _render_gastos(cot_id, congelada)


def _registrar_log_modificacion(cot_id, log_text):
    if not log_text.strip():
        return
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT historial_modificaciones FROM cotizaciones WHERE id=?", (cot_id,))
    row = cur.fetchone()
    prev_log = (row[0] if row and row[0] else "") or ""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_entry = f"[{timestamp}] Modificación Técnica por Supervisión:\n{log_text.strip()}\n"
    
    updated_log = f"{new_entry}\n{prev_log}".strip()
    
    cur.execute("UPDATE cotizaciones SET historial_modificaciones=? WHERE id=?", (updated_log, cot_id))
    conn.commit(); conn.close()


# ── Sub-sección 1: Materiales ────────────────────────────────────────────────
def _render_materiales(cot_id, partidas, tc, congelada):
    cat_mats  = get_catalogo_materiales()
    cat_names = ["— catálogo —"] + [m['descripcion'] for m in cat_mats]

    totales = []; gran_total = 0.0
    for p in partidas:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(importe_mxn),0) FROM cotizacion_materiales_detalle WHERE partida_id=?", (p['id'],))
        sub = cur.fetchone()[0]; conn.close()
        totales.append(sub); gran_total += sub

    df_res = pd.DataFrame({"N°": [p['numero_partida'] for p in partidas],
                           "Partida": [p['descripcion'] for p in partidas],
                           "Materiales MXN": totales})
    st.dataframe(df_res.style.format({"Materiales MXN": "${:,.2f}"}), use_container_width=True, hide_index=True)
    _grand_total_bar("TOTAL MATERIALES — TODAS LAS PARTIDAS", gran_total)

    # BANNER MODO EDICIÓN SUPERVISOR (AZUL CLARO)
    st.markdown(f"""
    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-left:5px solid #0284C7;border-radius:8px;padding:12px 18px;margin:16px 0 10px 0;font-family:'Montserrat',sans-serif;">
        <div style="font-size:13px;font-weight:800;color:#0369A1;">✏️ MODO EDICIÓN DIRECTA EN TABLA POR SUPERVISOR (MATERIALES)</div>
        <div style="font-size:11px;color:#0C4A6E;">
            Modifica las celdas destacadas en <b>Azul Claro</b> (<b>Descripción</b>, <b>Cantidad</b>, <b>Unidad</b> y <b>P.U. MXN</b>). Haz clic en <b>💾 Guardar Cambios & Auditar</b> para actualizar en base de datos y generar el registro de auditoría.
        </div>
    </div>
    """, unsafe_allow_html=True)

    for p in partidas:
        pid, num, nombre = p['id'], p['numero_partida'], p['descripcion']
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT id, descripcion, cantidad, unidad, precio_unitario_usd, precio_unitario_mxn, importe_mxn FROM cotizacion_materiales_detalle WHERE partida_id=? ORDER BY id", (pid,))
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        subtotal = sum(r['importe_mxn'] for r in rows)

        _partida_header(num, nombre, subtotal)
        st.markdown("<div style='margin-left:24px;padding-left:16px;border-left:4px solid #CBD5E1;margin-bottom:24px;'>", unsafe_allow_html=True)
        
        if rows:
            df_m = pd.DataFrame(rows)
            df_display = df_m.rename(columns={
                "id": "id",
                "descripcion": "Descripción del Insumo ✏️",
                "cantidad": "Cantidad ✏️",
                "unidad": "Unidad ✏️",
                "precio_unitario_usd": "P.U. USD",
                "precio_unitario_mxn": "P.U. MXN ✏️",
                "importe_mxn": "Importe Total MXN"
            })

            edited_df_m = st.data_editor(
                df_display,
                key=f"editor_m_{pid}",
                disabled=["id", "P.U. USD", "Importe Total MXN"] if not congelada else True,
                column_config={
                    "id": None,
                    "Descripción del Insumo ✏️": st.column_config.TextColumn("Descripción ✏️ (Editable)", required=True),
                    "Cantidad ✏️": st.column_config.NumberColumn("Cantidad ✏️ (Editable)", min_value=0.01, step=1.0, format="%.2f"),
                    "Unidad ✏️": st.column_config.SelectboxColumn("Unidad ✏️", options=["PZA","MTS","LOTE","JGO","TRAMO","KG","KIT","M"]),
                    "P.U. USD": st.column_config.NumberColumn("P.U. USD", format="$%.2f"),
                    "P.U. MXN ✏️": st.column_config.NumberColumn("P.U. MXN ✏️ (Editable)", min_value=0.0, step=10.0, format="$%.2f"),
                    "Importe Total MXN": st.column_config.NumberColumn("Importe Total MXN", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

            col_btn1, col_btn2 = st.columns([1, 2.5])
            with col_btn2:
                if not congelada and st.button(f"💾 Guardar Cambios en Partida {num} & Auditar", key=f"btn_save_m_{pid}", type="primary", use_container_width=True):
                    conn = get_connection(); cur = conn.cursor()
                    log_entries = []
                    for idx_row, orig in enumerate(rows):
                        ed_row = edited_df_m.iloc[idx_row]
                        r_id = int(orig["id"])
                        new_cant = float(ed_row["Cantidad ✏️"])
                        new_desc = str(ed_row["Descripción del Insumo ✏️"]).strip()
                        new_unit = str(ed_row["Unidad ✏️"]).strip()
                        new_pu_mxn = float(ed_row["P.U. MXN ✏️"])
                        new_imp = new_cant * new_pu_mxn

                        changes = []
                        if abs(orig["cantidad"] - new_cant) > 1e-4:
                            diff_c = new_cant - orig["cantidad"]
                            changes.append(f"Cantidad: {orig['cantidad']:.2f} -> {new_cant:.2f} (Dif: {diff_c:+.2f})")
                        if orig["descripcion"] != new_desc:
                            changes.append(f"Descripción: '{orig['descripcion']}' -> '{new_desc}'")
                        if orig["unidad"] != new_unit:
                            changes.append(f"Unidad: {orig['unidad']} -> {new_unit}")
                        if abs(orig["precio_unitario_mxn"] - new_pu_mxn) > 1e-4:
                            diff_p = new_pu_mxn - orig["precio_unitario_mxn"]
                            changes.append(f"P.U. MXN: ${orig['precio_unitario_mxn']:,.2f} -> ${new_pu_mxn:,.2f} (Dif: ${diff_p:+,.2f})")

                        if changes:
                            log_entries.append(f"• Partida {num} [Materiales]: Insumo '{new_desc}' | " + " | ".join(changes) + f" | Nuevo Importe: ${new_imp:,.2f} MXN")
                            cur.execute("""
                                UPDATE cotizacion_materiales_detalle
                                SET descripcion=?, cantidad=?, unidad=?, precio_unitario_mxn=?, importe_mxn=?
                                WHERE id=?
                            """, (new_desc, new_cant, new_unit, new_pu_mxn, new_imp, r_id))

                    conn.commit(); conn.close()

                    if log_entries:
                        _registrar_log_modificacion(cot_id, "\n".join(log_entries))
                        sync_cotizacion_totals(cot_id)
                        st.success(f"🎉 ¡{len(log_entries)} modificación(es) guardadas en Partida {num} y registradas en la bitácora!")
                        st.rerun()
                    else:
                        st.info("No se detectaron cambios en las filas de la tabla.")

        else:
            _empty_partition_row()

        _subtotal_bar(f"SUBTOTAL MATERIALES — PARTIDA {num}", subtotal)

        if not congelada:
            _add_form_wrapper_open()
            fc1, fc2 = st.columns([4, 2])
            with fc1: desc_in = st.text_input("Descripción", key=f"desc_m_{pid}", placeholder="Nombre del insumo o selecciona del catálogo →", label_visibility="collapsed")
            with fc2: cat_sel  = st.selectbox("Catálogo", cat_names, key=f"cat_m_{pid}", label_visibility="collapsed")

            matched = next((m for m in cat_mats if m['descripcion'] == cat_sel), None) if cat_sel != "— catálogo —" else None
            if matched and not desc_in: desc_in = matched['descripcion']

            fn1, fn2, fn3, fn4, fn5, fn6 = st.columns([1.0, 1.2, 1.5, 1.5, 1.8, 2.0])
            with fn1: _section_label("Cantidad"); cant_in = st.number_input("Cant", value=1.0, min_value=0.01, step=1.0, key=f"cant_m_{pid}", label_visibility="collapsed")
            with fn2: _section_label("Unidad");   unit_in = st.selectbox("Unidad", ["PZA","MTS","LOTE","JGO","TRAMO","KG","KIT","M"], key=f"unit_m_{pid}", label_visibility="collapsed")
            with fn3: _section_label("P.U. (USD)"); pu_usd = st.number_input("USD", min_value=0.0, step=1.0, value=float(matched['precio_unitario_usd']) if matched else 0.0, key=f"usd_m_{pid}", label_visibility="collapsed")
            with fn4: _section_label("P.U. (MXN)"); def_mxn = float(matched['precio_unitario_mxn']) if matched else (pu_usd * tc if pu_usd > 0 else 0.0); pu_mxn = st.number_input("MXN", min_value=0.0, step=10.0, value=def_mxn, key=f"mxn_m_{pid}", label_visibility="collapsed")
            with fn5:
                imp_prev = cant_in * pu_mxn
                st.markdown(f"<div style='margin-top:22px;text-align:right;'><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>IMPORTE</span><br><span style='font-size:16px;font-weight:800;color:{BRAND_ORANGE};'>${imp_prev:,.2f}</span></div>", unsafe_allow_html=True)
            with fn6:
                st.markdown("<div style='margin-top:20px;'>", unsafe_allow_html=True)
                if st.button(f"➕ Agregar a Partida {num}", key=f"add_m_{pid}", type="primary", use_container_width=True):
                    final = desc_in.strip()
                    if final:
                        conn = get_connection()
                        conn.execute("""INSERT INTO cotizacion_materiales_detalle
                                        (cotizacion_id,partida_id,descripcion,cantidad,unidad,precio_unitario_usd,precio_unitario_mxn,importe_mxn)
                                        VALUES(?,?,?,?,?,?,?,?)""",
                                     (cot_id, pid, final, cant_in, unit_in, pu_usd, pu_mxn, imp_prev))
                        conn.commit(); conn.close()
                        sync_cotizacion_totals(cot_id); st.rerun()
                    else: st.error("Ingresa una descripción.")
                st.markdown("</div>", unsafe_allow_html=True)
            _add_form_wrapper_close()
        st.markdown("</div>", unsafe_allow_html=True)


# ── Sub-sección 2: Mano de Obra ──────────────────────────────────────────────
def _render_mano_obra(cot_id, partidas, congelada):
    mo_roles   = get_catalogo_mano_obra()
    role_names = [r['categoria'] for r in mo_roles]

    totales = []; gran_total = 0.0
    for p in partidas:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(importe_total),0) FROM cotizacion_mo_detalle WHERE partida_id=?", (p['id'],))
        sub = cur.fetchone()[0]; conn.close()
        totales.append(sub); gran_total += sub

    df_mo = pd.DataFrame({"N°": [p['numero_partida'] for p in partidas],
                          "Partida": [p['descripcion'] for p in partidas],
                          "M.O. MXN": totales,
                          "Supervisión (30%)": [v*0.30 for v in totales]})
    st.dataframe(df_mo.style.format({"M.O. MXN":"${:,.2f}","Supervisión (30%)":"${:,.2f}"}), use_container_width=True, hide_index=True)
    _grand_total_bar("TOTAL MANO DE OBRA — TODAS LAS PARTIDAS", gran_total)

    st.markdown("<br>", unsafe_allow_html=True)
    LW  = [2.5, 0.7, 1.2, 0.7, 1.0, 1.1, 1.6, 0.5]
    LHR = ["Categoría","Personal","Sueldo Base Sem.","FASAR","Semanas","H-H","Importe Total",""]

    # BANNER MODO EDICIÓN SUPERVISOR (AZUL CLARO)
    st.markdown(f"""
    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-left:5px solid #0284C7;border-radius:8px;padding:12px 18px;margin:16px 0 10px 0;font-family:'Montserrat',sans-serif;">
        <div style="font-size:13px;font-weight:800;color:#0369A1;">✏️ MODO EDICIÓN DIRECTA EN TABLA POR SUPERVISOR (MANO DE OBRA)</div>
        <div style="font-size:11px;color:#0C4A6E;">
            Modifica las celdas destacadas en <b>Azul Claro</b> (<b>Personal</b>, <b>Sueldo Base Sem.</b>, <b>FASAR</b> y <b>Semanas</b>). Haz clic en <b>💾 Guardar Cambios & Auditar</b> para recalcular H-H e Importes.
        </div>
    </div>
    """, unsafe_allow_html=True)

    for p in partidas:
        pid, num, nombre = p['id'], p['numero_partida'], p['descripcion']
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT id, categoria_nombre, cantidad_personal, sueldo_base_semanal, fasar, sobre_sueldo, semanas, horas_hombre, importe_total FROM cotizacion_mo_detalle WHERE partida_id=? ORDER BY id", (pid,))
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        subtotal = sum(r['importe_total'] for r in rows)

        _partida_header(num, nombre, subtotal)
        st.markdown("<div style='margin-left:24px;padding-left:16px;border-left:4px solid #CBD5E1;margin-bottom:24px;'>", unsafe_allow_html=True)
        
        if rows:
            df_m = pd.DataFrame(rows)
            df_display = df_m.rename(columns={
                "id": "id",
                "categoria_nombre": "Categoría ✏️",
                "cantidad_personal": "Personal ✏️",
                "sueldo_base_semanal": "Sueldo Base Sem. ✏️",
                "fasar": "FASAR ✏️",
                "sobre_sueldo": "Sobre Sueldo ✏️",
                "semanas": "Semanas ✏️",
                "horas_hombre": "H-H Total",
                "importe_total": "Importe Total MXN"
            })

            edited_df_mo = st.data_editor(
                df_display,
                key=f"editor_mo_{pid}",
                disabled=["id", "H-H Total", "Importe Total MXN"] if not congelada else True,
                column_config={
                    "id": None,
                    "Categoría ✏️": st.column_config.TextColumn("Categoría ✏️", required=True),
                    "Personal ✏️": st.column_config.NumberColumn("Personal ✏️", min_value=1, step=1),
                    "Sueldo Base Sem. ✏️": st.column_config.NumberColumn("Sueldo Base Sem. ✏️", min_value=0.0, step=100.0, format="$%.2f"),
                    "FASAR ✏️": st.column_config.NumberColumn("FASAR ✏️", min_value=1.0, step=0.05, format="%.2f"),
                    "Sobre Sueldo ✏️": st.column_config.NumberColumn("Sobre Sueldo ✏️", min_value=1.0, step=0.1, format="%.2f"),
                    "Semanas ✏️": st.column_config.NumberColumn("Semanas ✏️", min_value=0.5, step=0.5, format="%.1f"),
                    "H-H Total": st.column_config.NumberColumn("H-H Total", format="%.0f hrs"),
                    "Importe Total MXN": st.column_config.NumberColumn("Importe Total MXN", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

            col_btn1, col_btn2 = st.columns([1, 2.5])
            with col_btn2:
                if not congelada and st.button(f"💾 Guardar Cambios M.O. en Partida {num} & Auditar", key=f"btn_save_mo_{pid}", type="primary", use_container_width=True):
                    conn = get_connection(); cur = conn.cursor()
                    log_entries = []
                    for idx_row, orig in enumerate(rows):
                        ed_row = edited_df_mo.iloc[idx_row]
                        r_id = int(orig["id"])
                        new_cat = str(ed_row["Categoría ✏️"]).strip()
                        new_pers = int(ed_row["Personal ✏️"])
                        new_sueldo = float(ed_row["Sueldo Base Sem. ✏️"])
                        new_fasar = float(ed_row["FASAR ✏️"])
                        new_sobre = float(ed_row["Sobre Sueldo ✏️"])
                        new_sem = float(ed_row["Semanas ✏️"])

                        costo_sem = new_sueldo * new_fasar * new_sobre
                        new_imp = new_pers * costo_sem * new_sem
                        new_hh = new_pers * new_sem * 48.0

                        changes = []
                        if orig["categoria_nombre"] != new_cat:
                            changes.append(f"Categoría: '{orig['categoria_nombre']}' -> '{new_cat}'")
                        if orig["cantidad_personal"] != new_pers:
                            changes.append(f"Personal: {orig['cantidad_personal']} -> {new_pers}")
                        if abs(orig["sueldo_base_semanal"] - new_sueldo) > 1e-4:
                            changes.append(f"Sueldo Base: ${orig['sueldo_base_semanal']:,.2f} -> ${new_sueldo:,.2f}")
                        if abs(orig["semanas"] - new_sem) > 1e-4:
                            changes.append(f"Semanas: {orig['semanas']:.1f} -> {new_sem:.1f}")

                        if changes:
                            log_entries.append(f"• Partida {num} [Mano de Obra]: Puesto '{new_cat}' | " + " | ".join(changes) + f" | Nuevo Importe Total: ${new_imp:,.2f} MXN")
                            cur.execute("""
                                UPDATE cotizacion_mo_detalle
                                SET categoria_nombre=?, cantidad_personal=?, sueldo_base_semanal=?, fasar=?, sobre_sueldo=?, semanas=?, horas_hombre=?, importe_total=?
                                WHERE id=?
                            """, (new_cat, new_pers, new_sueldo, new_fasar, new_sobre, new_sem, new_hh, new_imp, r_id))

                    conn.commit(); conn.close()

                    if log_entries:
                        _registrar_log_modificacion(cot_id, "\n".join(log_entries))
                        sync_cotizacion_totals(cot_id)
                        st.success(f"🎉 ¡{len(log_entries)} modificación(es) guardadas en Mano de Obra (Partida {num})!")
                        st.rerun()
                    else:
                        st.info("No se detectaron cambios en la Mano de Obra.")
        else:
            _empty_partition_row()

        _subtotal_bar(f"SUBTOTAL M.O. — PARTIDA {num}", subtotal)

        if not congelada:
            _add_form_wrapper_open()
            role_sel = st.selectbox("Categoría", role_names, key=f"role_{pid}", label_visibility="collapsed")
            sel_info = next((r for r in mo_roles if r['categoria'] == role_sel), mo_roles[0])

            fc1, fc2, fc3, fc4, fc5 = st.columns([2, 1, 1.2, 0.8, 0.8])
            with fc1: _section_label("Sueldo Base Semanal"); sueldo = st.number_input("Sueldo", value=float(sel_info['sueldo_base_semanal']), step=100.0, key=f"sueldo_{pid}", label_visibility="collapsed")
            with fc2: _section_label("Personal");           cant_p = st.number_input("Personal", value=1, min_value=1, step=1, key=f"cant_p_{pid}", label_visibility="collapsed")
            with fc3: _section_label("Semanas");            sem_p  = st.number_input("Semanas", value=1.0, min_value=0.5, step=0.5, key=f"sem_p_{pid}", label_visibility="collapsed")
            with fc4: _section_label("FASAR");              fasar  = st.number_input("FASAR", value=float(sel_info['fasar']), step=0.05, key=f"fasar_{pid}", label_visibility="collapsed")
            with fc5: _section_label("Sobre Sueldo");       sobre  = st.number_input("Sobre", value=float(sel_info['sobre_sueldo']), step=0.1, key=f"sobre_{pid}", label_visibility="collapsed")

            costo_sem = sueldo * fasar * sobre
            imp_mo    = cant_p * costo_sem * sem_p
            hh        = cant_p * sem_p * 48.0

            st.markdown(f"<div style='display:flex;gap:28px;padding:6px 0 4px 0;font-family:Montserrat,sans-serif;'><span><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>COSTO SEM.</span><br><b style='color:{BRAND_CHARCOAL};'>${costo_sem:,.2f}</b></span><span><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>H-H</span><br><b style='color:{BRAND_CHARCOAL};'>{hh:,.0f} hrs</b></span><span><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>IMPORTE MO</span><br><b style='font-size:16px;color:{BRAND_ORANGE};'>${imp_mo:,.2f} MXN</b></span></div>", unsafe_allow_html=True)
            if st.button(f"➕ Asignar Personal a Partida {num}", key=f"add_mo_{pid}", type="primary"):
                conn = get_connection()
                conn.execute("""INSERT INTO cotizacion_mo_detalle
                                (cotizacion_id,partida_id,categoria_nombre,cantidad_personal,
                                 sueldo_base_semanal,fasar,sobre_sueldo,semanas,horas_hombre,importe_total)
                                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                             (cot_id, pid, role_sel, cant_p, sueldo, fasar, sobre, sem_p, hh, imp_mo))
                conn.commit(); conn.close()
                sync_cotizacion_totals(cot_id); st.rerun()
            _add_form_wrapper_close()
        st.markdown("</div>", unsafe_allow_html=True)


# ── Sub-sección 3: Subcontratos ──────────────────────────────────────────────
def _render_subcontratos(cot_id, partidas, congelada):
    totales = []; gran_total = 0.0
    for p in partidas:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(importe_mxn),0) FROM cotizacion_subcontratos_detalle WHERE partida_id=?", (p['id'],))
        sub = cur.fetchone()[0]; conn.close()
        totales.append(sub); gran_total += sub

    df_s = pd.DataFrame({"N°": [p['numero_partida'] for p in partidas], "Partida": [p['descripcion'] for p in partidas], "Subcontratos MXN": totales})
    st.dataframe(df_s.style.format({"Subcontratos MXN": "${:,.2f}"}), use_container_width=True, hide_index=True)
    _grand_total_bar("TOTAL SUBCONTRATOS", gran_total)

    # BANNER MODO EDICIÓN SUPERVISOR (AZUL CLARO)
    st.markdown(f"""
    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-left:5px solid #0284C7;border-radius:8px;padding:12px 18px;margin:16px 0 10px 0;font-family:'Montserrat',sans-serif;">
        <div style="font-size:13px;font-weight:800;color:#0369A1;">✏️ MODO EDICIÓN DIRECTA EN TABLA POR SUPERVISOR (SUBCONTRATOS)</div>
        <div style="font-size:11px;color:#0C4A6E;">
            Modifica las celdas destacadas en <b>Azul Claro</b> (<b>Servicio</b>, <b>Cantidad</b>, <b>Unidad</b>, <b>P.U. MXN</b> y <b>Subcontratista</b>). Haz clic en <b>💾 Guardar Cambios & Auditar</b>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    for p in partidas:
        pid, num, nombre = p['id'], p['numero_partida'], p['descripcion']
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT id, descripcion, cantidad, unidad, pu_mxn, importe_mxn, subcontratista FROM cotizacion_subcontratos_detalle WHERE partida_id=? ORDER BY id", (pid,))
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        subtotal = sum(r['importe_mxn'] for r in rows)

        _partida_header(num, nombre, subtotal)
        st.markdown("<div style='margin-left:24px;padding-left:16px;border-left:4px solid #CBD5E1;margin-bottom:24px;'>", unsafe_allow_html=True)
        
        if rows:
            df_m = pd.DataFrame(rows)
            df_display = df_m.rename(columns={
                "id": "id",
                "descripcion": "Descripción del Servicio ✏️",
                "cantidad": "Cantidad ✏️",
                "unidad": "Unidad ✏️",
                "pu_mxn": "P.U. MXN ✏️",
                "importe_mxn": "Importe Total MXN",
                "subcontratista": "Subcontratista ✏️"
            })

            edited_df_sub = st.data_editor(
                df_display,
                key=f"editor_sub_{pid}",
                disabled=["id", "Importe Total MXN"] if not congelada else True,
                column_config={
                    "id": None,
                    "Descripción del Servicio ✏️": st.column_config.TextColumn("Descripción ✏️", required=True),
                    "Cantidad ✏️": st.column_config.NumberColumn("Cantidad ✏️", min_value=0.01, step=1.0, format="%.2f"),
                    "Unidad ✏️": st.column_config.TextColumn("Unidad ✏️"),
                    "P.U. MXN ✏️": st.column_config.NumberColumn("P.U. MXN ✏️", min_value=0.0, step=10.0, format="$%.2f"),
                    "Importe Total MXN": st.column_config.NumberColumn("Importe Total MXN", format="$%.2f"),
                    "Subcontratista ✏️": st.column_config.TextColumn("Subcontratista ✏️")
                },
                use_container_width=True,
                hide_index=True
            )

            col_btn1, col_btn2 = st.columns([1, 2.5])
            with col_btn2:
                if not congelada and st.button(f"💾 Guardar Cambios Subcontratos en Partida {num} & Auditar", key=f"btn_save_sub_{pid}", type="primary", use_container_width=True):
                    conn = get_connection(); cur = conn.cursor()
                    log_entries = []
                    for idx_row, orig in enumerate(rows):
                        ed_row = edited_df_sub.iloc[idx_row]
                        r_id = int(orig["id"])
                        new_desc = str(ed_row["Descripción del Servicio ✏️"]).strip()
                        new_cant = float(ed_row["Cantidad ✏️"])
                        new_unit = str(ed_row["Unidad ✏️"]).strip()
                        new_pu = float(ed_row["P.U. MXN ✏️"])
                        new_subc = str(ed_row.get("Subcontratista ✏️", "") or "").strip()
                        new_imp = new_cant * new_pu

                        changes = []
                        if orig["descripcion"] != new_desc:
                            changes.append(f"Servicio: '{orig['descripcion']}' -> '{new_desc}'")
                        if abs(orig["cantidad"] - new_cant) > 1e-4:
                            changes.append(f"Cantidad: {orig['cantidad']:.2f} -> {new_cant:.2f}")
                        if abs(orig["pu_mxn"] - new_pu) > 1e-4:
                            changes.append(f"P.U. MXN: ${orig['pu_mxn']:,.2f} -> ${new_pu:,.2f}")

                        if changes:
                            log_entries.append(f"• Partida {num} [Subcontratos]: Servicio '{new_desc}' | " + " | ".join(changes) + f" | Nuevo Importe: ${new_imp:,.2f} MXN")
                            cur.execute("""
                                UPDATE cotizacion_subcontratos_detalle
                                SET descripcion=?, cantidad=?, unidad=?, pu_mxn=?, importe_mxn=?, subcontratista=?
                                WHERE id=?
                            """, (new_desc, new_cant, new_unit, new_pu, new_imp, new_subc, r_id))

                    conn.commit(); conn.close()

                    if log_entries:
                        _registrar_log_modificacion(cot_id, "\n".join(log_entries))
                        sync_cotizacion_totals(cot_id)
                        st.success(f"🎉 ¡{len(log_entries)} modificación(es) guardadas en Subcontratos (Partida {num})!")
                        st.rerun()
                    else:
                        st.info("No se detectaron cambios en Subcontratos.")
        else:
            _empty_partition_row()

        _subtotal_bar(f"SUBTOTAL SUBCONTRATOS — PARTIDA {num}", subtotal)

        if not congelada:
            cat_subs   = get_catalogo_subcontratos()
            cat_s_names= ["— Seleccionar del Catálogo Base de Subcontratos —"] + [s['concepto'] for s in cat_subs]

            _add_form_wrapper_open()
            fs_cat, fs_txt = st.columns([3.5, 3.5])
            with fs_cat:
                _section_label("Catálogo Base de Subcontratos")
                sub_sel = st.selectbox("Catálogo Subcontratos", cat_s_names, key=f"sub_cat_{pid}", label_visibility="collapsed")
                matched_s = next((s for s in cat_subs if s['concepto'] == sub_sel), None) if sub_sel != "— Seleccionar del Catálogo Base de Subcontratos —" else None

            with fs_txt:
                _section_label("Descripción del Servicio *")
                default_desc_s = matched_s['concepto'] if matched_s else ""
                desc_s = st.text_input("Servicio", value=default_desc_s, key=f"desc_s_{pid}", placeholder="O escribe una descripción libre…", label_visibility="collapsed")

            fa, fb, fc, fd = st.columns([1.0, 1.2, 1.8, 2.0])
            with fa:
                _section_label("Cant.")
                cant_s = st.number_input("Cant", value=1.0, min_value=0.01, step=1.0, key=f"cant_s_{pid}", label_visibility="collapsed")
            with fb:
                _section_label("Unidad")
                default_unit_s = matched_s['unidad'] if matched_s else "SERV"
                unit_s = st.text_input("Unidad", value=default_unit_s, key=f"unit_s_{pid}", label_visibility="collapsed")
            with fc:
                _section_label("P.U. MXN")
                default_pu_s = float(matched_s['precio_unitario_default']) if matched_s else 0.0
                pu_s = st.number_input("P.U. MXN", value=default_pu_s, step=50.0, key=f"pu_s_{pid}", label_visibility="collapsed")
            with fd:
                _section_label("Subcontratista / Proveedor")
                nom_s = st.text_input("Subcontratista", key=f"nom_s_{pid}", placeholder="Ej: Electrificaciones del Norte S.A.", label_visibility="collapsed")

            imp_prev_s = cant_s * pu_s
            st.markdown(f"<div style='margin-top:4px;text-align:right;'><span style='font-size:10px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>IMPORTE</span> <b style='font-size:15px;color:{BRAND_ORANGE};'>${imp_prev_s:,.2f} MXN</b></div>", unsafe_allow_html=True)

            if st.button(f"➕ Agregar Servicio a Partida {num}", key=f"add_sub_{pid}", type="primary"):
                final_desc_s = desc_s.strip()
                if final_desc_s:
                    conn = get_connection()
                    conn.execute("""INSERT INTO cotizacion_subcontratos_detalle
                                    (cotizacion_id,partida_id,descripcion,cantidad,unidad,pu_mxn,importe_mxn,subcontratista)
                                    VALUES(?,?,?,?,?,?,?,?)""",
                                 (cot_id, pid, final_desc_s, cant_s, unit_s, pu_s, imp_prev_s, nom_s))
                    conn.commit(); conn.close()
                    sync_cotizacion_totals(cot_id); st.rerun()
                else:
                    st.error("La descripción es requerida.")
            _add_form_wrapper_close()
        st.markdown("</div>", unsafe_allow_html=True)




# ── Sub-sección 4: Maquinaria ────────────────────────────────────────────────
def _render_maquinaria(cot_id, partidas, congelada):
    totales = []; gran_total = 0.0
    for p in partidas:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT COALESCE(SUM(total_mxn),0) FROM cotizacion_maquinaria_detalle WHERE partida_id=?", (p['id'],))
        sub = cur.fetchone()[0]; conn.close()
        totales.append(sub); gran_total += sub

    df_q = pd.DataFrame({"N°": [p['numero_partida'] for p in partidas], "Partida": [p['descripcion'] for p in partidas], "Maquinaria MXN": totales})
    st.dataframe(df_q.style.format({"Maquinaria MXN": "${:,.2f}"}), use_container_width=True, hide_index=True)
    _grand_total_bar("TOTAL MAQUINARIA", gran_total)

    # BANNER MODO EDICIÓN SUPERVISOR (AZUL CLARO)
    st.markdown(f"""
    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-left:5px solid #0284C7;border-radius:8px;padding:12px 18px;margin:16px 0 10px 0;font-family:'Montserrat',sans-serif;">
        <div style="font-size:13px;font-weight:800;color:#0369A1;">✏️ MODO EDICIÓN DIRECTA EN TABLA POR SUPERVISOR (MAQUINARIA & EQUIPO)</div>
        <div style="font-size:11px;color:#0C4A6E;">
            Modifica las celdas destacadas en <b>Azul Claro</b> (<b>Clave</b>, <b>Equipo</b>, <b>Cantidad</b>, <b>Unidad</b> y <b>Costo Unit.</b>). Haz clic en <b>💾 Guardar Cambios & Auditar</b>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    for p in partidas:
        pid, num, nombre = p['id'], p['numero_partida'], p['descripcion']
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT id, clave, nombre, cantidad, unidad, costo_unitario, total_mxn FROM cotizacion_maquinaria_detalle WHERE partida_id=? ORDER BY id", (pid,))
        rows = [dict(r) for r in cur.fetchall()]; conn.close()
        subtotal = sum(r['total_mxn'] for r in rows)

        _partida_header(num, nombre, subtotal)
        st.markdown("<div style='margin-left:24px;padding-left:16px;border-left:4px solid #CBD5E1;margin-bottom:24px;'>", unsafe_allow_html=True)
        
        if rows:
            df_m = pd.DataFrame(rows)
            df_display = df_m.rename(columns={
                "id": "id",
                "clave": "Clave ✏️",
                "nombre": "Equipo / Maquinaria ✏️",
                "cantidad": "Cantidad ✏️",
                "unidad": "Unidad ✏️",
                "costo_unitario": "Costo Unit. MXN ✏️",
                "total_mxn": "Importe Total MXN"
            })

            edited_df_mq = st.data_editor(
                df_display,
                key=f"editor_mq_{pid}",
                disabled=["id", "Importe Total MXN"] if not congelada else True,
                column_config={
                    "id": None,
                    "Clave ✏️": st.column_config.TextColumn("Clave ✏️"),
                    "Equipo / Maquinaria ✏️": st.column_config.TextColumn("Equipo / Maquinaria ✏️", required=True),
                    "Cantidad ✏️": st.column_config.NumberColumn("Cantidad ✏️", min_value=0.01, step=1.0, format="%.2f"),
                    "Unidad ✏️": st.column_config.TextColumn("Unidad ✏️"),
                    "Costo Unit. MXN ✏️": st.column_config.NumberColumn("Costo Unit. MXN ✏️", min_value=0.0, step=10.0, format="$%.2f"),
                    "Importe Total MXN": st.column_config.NumberColumn("Importe Total MXN", format="$%.2f")
                },
                use_container_width=True,
                hide_index=True
            )

            col_btn1, col_btn2 = st.columns([1, 2.5])
            with col_btn2:
                if not congelada and st.button(f"💾 Guardar Cambios Maquinaria en Partida {num} & Auditar", key=f"btn_save_mq_{pid}", type="primary", use_container_width=True):
                    conn = get_connection(); cur = conn.cursor()
                    log_entries = []
                    for idx_row, orig in enumerate(rows):
                        ed_row = edited_df_mq.iloc[idx_row]
                        r_id = int(orig["id"])
                        new_cla = str(ed_row.get("Clave ✏️", "") or "").strip()
                        new_nom = str(ed_row["Equipo / Maquinaria ✏️"]).strip()
                        new_cant = float(ed_row["Cantidad ✏️"])
                        new_unit = str(ed_row["Unidad ✏️"]).strip()
                        new_cu = float(ed_row["Costo Unit. MXN ✏️"])
                        new_imp = new_cant * new_cu

                        changes = []
                        if orig["nombre"] != new_nom:
                            changes.append(f"Equipo: '{orig['nombre']}' -> '{new_nom}'")
                        if abs(orig["cantidad"] - new_cant) > 1e-4:
                            changes.append(f"Cantidad: {orig['cantidad']:.2f} -> {new_cant:.2f}")
                        if abs(orig["costo_unitario"] - new_cu) > 1e-4:
                            changes.append(f"Costo Unit.: ${orig['costo_unitario']:,.2f} -> ${new_cu:,.2f}")

                        if changes:
                            log_entries.append(f"• Partida {num} [Maquinaria]: Equipo '{new_nom}' | " + " | ".join(changes) + f" | Nuevo Importe: ${new_imp:,.2f} MXN")
                            cur.execute("""
                                UPDATE cotizacion_maquinaria_detalle
                                SET clave=?, nombre=?, cantidad=?, unidad=?, costo_unitario=?, total_mxn=?
                                WHERE id=?
                            """, (new_cla, new_nom, new_cant, new_unit, new_cu, new_imp, r_id))

                    conn.commit(); conn.close()

                    if log_entries:
                        _registrar_log_modificacion(cot_id, "\n".join(log_entries))
                        sync_cotizacion_totals(cot_id)
                        st.success(f"🎉 ¡{len(log_entries)} modificación(es) guardadas en Maquinaria (Partida {num})!")
                        st.rerun()
                    else:
                        st.info("No se detectaron cambios en Maquinaria.")
        else:
            _empty_partition_row()

        _subtotal_bar(f"SUBTOTAL MAQUINARIA — PARTIDA {num}", subtotal)

        if not congelada:
            _add_form_wrapper_open()
            fa, fb, fc, fd, fe = st.columns([1.0, 3.5, 0.9, 1.2, 1.8])
            with fa: _section_label("Clave");         cla_m = st.text_input("Clave", key=f"cla_mq_{pid}", label_visibility="collapsed")
            with fb: _section_label("Equipo *");      nom_m = st.text_input("Equipo", key=f"nom_mq_{pid}", placeholder="Ej: Grúa telescópica 25t", label_visibility="collapsed")
            with fc: _section_label("Cant.");         cnt_m = st.number_input("Cant", value=1.0, min_value=0.01, step=1.0, key=f"cnt_mq_{pid}", label_visibility="collapsed")
            with fd: _section_label("Unidad");       unt_m = st.text_input("Unidad", value="DIA", key=f"unt_mq_{pid}", label_visibility="collapsed")
            with fe: _section_label("Costo Unit. MXN"); cu_m = st.number_input("Costo", value=0.0, step=100.0, key=f"cu_mq_{pid}", label_visibility="collapsed")

            if st.button(f"➕ Agregar Equipo a Partida {num}", key=f"add_mq_{pid}", type="primary"):
                if nom_m.strip():
                    conn = get_connection()
                    conn.execute("""INSERT INTO cotizacion_maquinaria_detalle
                                    (cotizacion_id,partida_id,clave,nombre,cantidad,unidad,costo_unitario,total_mxn)
                                    VALUES(?,?,?,?,?,?,?,?)""",
                                 (cot_id, pid, cla_m, nom_m.strip(), cnt_m, unt_m, cu_m, cnt_m*cu_m))
                    conn.commit(); conn.close()
                    sync_cotizacion_totals(cot_id); st.rerun()
                else: st.error("El nombre del equipo es requerido.")
            _add_form_wrapper_close()
        st.markdown("</div>", unsafe_allow_html=True)


# ── Sub-sección 5: Gastos Generales ──────────────────────────────────────────
def _render_gastos(cot_id, congelada):
    st.markdown(f"""
    <div style="background:{BRAND_CHARCOAL};color:#fff;padding:10px 18px;border-radius:8px;
                border-left:6px solid {BRAND_ORANGE};margin-bottom:12px;
                font-family:'Montserrat',sans-serif;">
        <span style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1.5px;
                     color:{BRAND_ORANGE};">PROYECTO COMPLETO</span><br>
        <span style="font-size:13px;font-weight:700;">Gastos Generales de Obra</span>
        <span style="font-size:11px;color:#CBD5E1;margin-left:10px;">
            — Se prorratean automáticamente entre todas las partidas en el ANÁLISIS
        </span>
    </div>""", unsafe_allow_html=True)

    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id, nombre, cantidad, unidad, tiempo_valor, costo_unitario, importe_total FROM cotizacion_gastos_detalle WHERE cotizacion_id=? ORDER BY id", (cot_id,))
    rows = [dict(r) for r in cur.fetchall()]; conn.close()
    total_g = sum(r['importe_total'] for r in rows)

    # BANNER MODO EDICIÓN SUPERVISOR (AZUL CLARO)
    st.markdown(f"""
    <div style="background:#F0F9FF;border:1px solid #BAE6FD;border-left:5px solid #0284C7;border-radius:8px;padding:12px 18px;margin:16px 0 10px 0;font-family:'Montserrat',sans-serif;">
        <div style="font-size:13px;font-weight:800;color:#0369A1;">✏️ MODO EDICIÓN DIRECTA EN TABLA POR SUPERVISOR (GASTOS GENERALES)</div>
        <div style="font-size:11px;color:#0C4A6E;">
            Modifica las celdas destacadas en <b>Azul Claro</b> (<b>Concepto</b>, <b>Cantidad</b>, <b>Unidad</b>, <b>Tiempo</b> y <b>Costo Unit.</b>). Haz clic en <b>💾 Guardar Cambios & Auditar</b>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if rows:
        df_m = pd.DataFrame(rows)
        df_display = df_m.rename(columns={
            "id": "id",
            "nombre": "Nombre / Concepto de Gasto ✏️",
            "cantidad": "Cantidad ✏️",
            "unidad": "Unidad ✏️",
            "tiempo_valor": "Tiempo ✏️",
            "costo_unitario": "Costo Unit. MXN ✏️",
            "importe_total": "Importe Total MXN"
        })

        edited_df_g = st.data_editor(
            df_display,
            key=f"editor_g_{cot_id}",
            disabled=["id", "Importe Total MXN"] if not congelada else True,
            column_config={
                "id": None,
                "Nombre / Concepto de Gasto ✏️": st.column_config.TextColumn("Nombre / Concepto ✏️", required=True),
                "Cantidad ✏️": st.column_config.NumberColumn("Cantidad ✏️", min_value=0.01, step=1.0, format="%.2f"),
                "Unidad ✏️": st.column_config.TextColumn("Unidad ✏️"),
                "Tiempo ✏️": st.column_config.NumberColumn("Tiempo ✏️", min_value=0.0, step=1.0, format="%.1f"),
                "Costo Unit. MXN ✏️": st.column_config.NumberColumn("Costo Unit. MXN ✏️", min_value=0.0, step=10.0, format="$%.2f"),
                "Importe Total MXN": st.column_config.NumberColumn("Importe Total MXN", format="$%.2f")
            },
            use_container_width=True,
            hide_index=True
        )

        col_btn1, col_btn2 = st.columns([1, 2.5])
        with col_btn2:
            if not congelada and st.button("💾 Guardar Cambios en Gastos Generales & Auditar", key=f"btn_save_g_{cot_id}", type="primary", use_container_width=True):
                conn = get_connection(); cur = conn.cursor()
                log_entries = []
                for idx_row, orig in enumerate(rows):
                    ed_row = edited_df_g.iloc[idx_row]
                    r_id = int(orig["id"])
                    new_nom = str(ed_row["Nombre / Concepto de Gasto ✏️"]).strip()
                    new_cant = float(ed_row["Cantidad ✏️"])
                    new_unit = str(ed_row["Unidad ✏️"]).strip()
                    new_tiem = float(ed_row["Tiempo ✏️"])
                    new_cu = float(ed_row["Costo Unit. MXN ✏️"])
                    new_imp = new_cant * (new_tiem if new_tiem > 0 else 1.0) * new_cu

                    changes = []
                    if orig["nombre"] != new_nom:
                        changes.append(f"Gasto: '{orig['nombre']}' -> '{new_nom}'")
                    if abs(orig["cantidad"] - new_cant) > 1e-4:
                        changes.append(f"Cantidad: {orig['cantidad']:.2f} -> {new_cant:.2f}")
                    if abs(orig["costo_unitario"] - new_cu) > 1e-4:
                        changes.append(f"Costo Unit.: ${orig['costo_unitario']:,.2f} -> ${new_cu:,.2f}")

                    if changes:
                        log_entries.append(f"• [Gastos Generales]: Concepto '{new_nom}' | " + " | ".join(changes) + f" | Nuevo Importe Total: ${new_imp:,.2f} MXN")
                        cur.execute("""
                            UPDATE cotizacion_gastos_detalle
                            SET nombre=?, cantidad=?, unidad=?, tiempo_valor=?, costo_unitario=?, importe_total=?
                            WHERE id=?
                        """, (new_nom, new_cant, new_unit, new_tiem, new_cu, new_imp, r_id))

                conn.commit(); conn.close()

                if log_entries:
                    _registrar_log_modificacion(cot_id, "\n".join(log_entries))
                    sync_cotizacion_totals(cot_id)
                    st.success(f"🎉 ¡{len(log_entries)} modificación(es) guardadas en Gastos Generales!")
                    st.rerun()
                else:
                    st.info("No se detectaron cambios en Gastos Generales.")
    else:
        _empty_partition_row()

    _subtotal_bar("SUBTOTAL GASTOS GENERALES DEL PROYECTO", total_g)

    if not congelada:
        st.markdown("<br>", unsafe_allow_html=True)
        cat_gastos  = get_catalogo_gastos()
        cat_g_names = ["— Seleccionar del Catálogo Base de Gastos —"] + [f"{g.get('clave','')} — {g['concepto']}" for g in cat_gastos]

        _add_form_wrapper_open()
        fg_cat, fg_txt = st.columns([3.5, 3.5])
        with fg_cat:
            _section_label("Catálogo Base de Gastos (59 conceptos)")
            g_sel = st.selectbox("Catálogo Gastos", cat_g_names, key="g_cat_sel", label_visibility="collapsed")
            matched_g = next((g for g in cat_gastos if f"{g.get('clave','')} — {g['concepto']}" == g_sel), None) if g_sel != "— Seleccionar del Catálogo Base de Gastos —" else None

        with fg_txt:
            _section_label("Nombre / Concepto de Gasto *")
            default_nom = matched_g['concepto'] if matched_g else ""
            nom_g = st.text_input("Gasto", value=default_nom, key="nom_g", placeholder="O escribe un concepto libre aquí…", label_visibility="collapsed")

        fa, fb, fc, fd = st.columns([1.0, 1.5, 1.2, 2.0])
        with fa:
            _section_label("Cant.")
            cant_g = st.number_input("Cant", value=1.0, min_value=0.01, step=1.0, key="cant_g", label_visibility="collapsed")
        with fb:
            _section_label("Unidad")
            default_uni = matched_g['unidad'] if matched_g else "VJE"
            unit_g = st.text_input("Unidad", value=default_uni, key="unit_g", label_visibility="collapsed")
        with fc:
            _section_label("Tiempo")
            tiem_g = st.number_input("Tiempo", value=1.0, min_value=0.0, step=1.0, key="tiem_g", label_visibility="collapsed")
        with fd:
            _section_label("Costo Unit. MXN")
            default_pu = float(matched_g['costo_unitario_default']) if matched_g else 0.0
            pu_g = st.number_input("PU", value=default_pu, step=50.0, key="pu_g", label_visibility="collapsed")

        imp_g = cant_g * tiem_g * pu_g
        if imp_g > 0:
            st.markdown(f"<div style='margin-top:6px;'><span style='font-size:12px;color:{BRAND_CHARCOAL_MED};'>Importe Total Gasto: <b style='color:{BRAND_ORANGE};font-size:15px;'>${imp_g:,.2f} MXN</b></span></div>", unsafe_allow_html=True)

        if st.button("➕ Agregar Gasto General al Proyecto", key="add_g", type="primary"):
            final_nom = nom_g.strip() or (matched_g['concepto'] if matched_g else "")
            if final_nom:
                conn = get_connection()
                conn.execute("""INSERT INTO cotizacion_gastos_detalle
                                (cotizacion_id,nombre,cantidad,unidad,tiempo_valor,costo_unitario,importe_total)
                                VALUES(?,?,?,?,?,?,?)""",
                             (cot_id, final_nom, cant_g, unit_g, tiem_g, pu_g, imp_g))
                conn.commit(); conn.close()
                sync_cotizacion_totals(cot_id); st.rerun()
            else:
                st.error("El nombre o concepto del gasto es requerido.")
        _add_form_wrapper_close()



# ─────────────────────────────────────────────────────────────────────────────
# PASO 4: DASHBOARD ANÁLISIS, MÁRGENES Y CONGELAMIENTO DE VERSIÓN
# ─────────────────────────────────────────────────────────────────────────────

def _paso4_analisis_version(cot_id, cot_info, partidas):
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 4 — ANÁLISIS, Márgenes & Control de Versión</h2>
        <p>Resumen financiero ponderado por partida de <b>{cot_info['folio']}</b> · Revisión {cot_info.get('revision','R0')}</p>
    </div>""", unsafe_allow_html=True)

    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT p.*,
                      COALESCE((SELECT SUM(importe_mxn) FROM cotizacion_materiales_detalle WHERE partida_id=p.id),0) as mat,
                      COALESCE((SELECT SUM(importe_total) FROM cotizacion_mo_detalle WHERE partida_id=p.id),0) as mo,
                      COALESCE((SELECT SUM(importe_mxn) FROM cotizacion_subcontratos_detalle WHERE partida_id=p.id),0) as sub,
                      COALESCE((SELECT SUM(total_mxn) FROM cotizacion_maquinaria_detalle WHERE partida_id=p.id),0) as maq
                   FROM cotizacion_partidas p WHERE p.cotizacion_id=? ORDER BY p.numero_partida""", (cot_id,))
    partidas_an = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT COALESCE(SUM(importe_total),0) FROM cotizacion_gastos_detalle WHERE cotizacion_id=?", (cot_id,))
    total_gastos = cur.fetchone()[0]
    conn.close()

    congelada = bool(cot_info.get('congelada'))
    mg = float(cot_info.get('margen_porcentaje', 0.30))
    cm = float(cot_info.get('comision_porcentaje', 0.05))
    sv = float(cot_info.get('supervision_porcentaje', 0.30))
    hta_pct = float(cot_info.get('herramienta_porcentaje', 0.03))

    # ── CONSTRUIR TABLA DE ANÁLISIS PONDERADA ──

    analisis_rows = []
    total_cd = 0.0
    n_parts = max(len(partidas_an), 1)

    for p in partidas_an:
        mat = p['mat']; mo = p['mo']; sub = p['sub']; maq = p['maq']
        sup  = mo * sv
        hta  = (mat + mo) * hta_pct
        gas_part = total_gastos / n_parts
        cd   = mat + mo + sup + hta + sub + maq + gas_part
        total_cd += cd
        pv   = cd / (1 - mg - cm) if (1 - mg - cm) > 0 else cd
        analisis_rows.append({
            "N°": p['numero_partida'], "Partida": p['descripcion'][:45],
            "Materiales": mat, "M.O.": mo, "Supervisión": sup,
            "Herramienta": hta, "Subcontratos": sub, "Maquinaria": maq,
            "Gastos": gas_part, "Costo Directo": cd,
            "Precio Venta": pv, "Margen $": pv - cd
        })

    # ── DASHBOARD: RESUMEN Y DISTRIBUCIÓN DEL COSTO DIRECTO (SOLICITADO) ──
    total_mat = sum(p['mat'] for p in partidas_an)
    total_mo  = sum(p['mo'] for p in partidas_an)
    total_sup = total_mo * sv
    total_sub = sum(p['sub'] for p in partidas_an)
    total_maq = sum(p['maq'] for p in partidas_an)
    total_hta = (total_mat + total_mo) * hta_pct
    total_cd_calc = total_mat + total_mo + total_sup + total_sub + total_maq + total_hta + total_gastos

    rubro_rows = [
        {"Clave": "A", "Rubro": "Materiales", "Costo (MXN)": total_mat},
        {"Clave": "B", "Rubro": "Mano de Obra", "Costo (MXN)": total_mo},
        {"Clave": "C", "Rubro": f"Supervisión ({int(sv*100)}% MO)", "Costo (MXN)": total_sup},
        {"Clave": "D", "Rubro": "Subcontratos", "Costo (MXN)": total_sub},
        {"Clave": "E", "Rubro": "Maquinaria", "Costo (MXN)": total_maq},
        {"Clave": "F", "Rubro": f"Herramienta ({int(hta_pct*100)}% MO)", "Costo (MXN)": total_hta},
        {"Clave": "G", "Rubro": "Gastos Generales", "Costo (MXN)": total_gastos},
    ]
    for r in rubro_rows:
        r['%'] = f"{(r['Costo (MXN)'] / total_cd_calc * 100):.2f}%" if total_cd_calc > 0 else "0.00%"

    # Fila de TOTAL COSTO DIRECTO
    rubro_rows_df = list(rubro_rows) + [{
        "Clave": "TOTAL",
        "Rubro": "TOTAL COSTO DIRECTO",
        "Costo (MXN)": total_cd_calc,
        "%": "100.00%"
    }]

    df_rubros = pd.DataFrame(rubro_rows_df)

    def _highlight_total(row):
        if str(row['Clave']).strip() == 'TOTAL':
            return ['background-color: #FE8C29; color: #FFFFFF; font-weight: 900; font-size: 15px;'] * len(row)
        return [''] * len(row)

    d_col1, d_col2 = st.columns([1.2, 1.0])
    with d_col1:
        st.markdown(f"""
        <div style="border-left:4px solid {BRAND_ORANGE};padding-left:12px;margin:8px 0 14px 0;">
            <h3 style="font-size:16px;font-weight:800;color:{BRAND_CHARCOAL};margin:0;">Resumen de Costo Directo por Rubro</h3>
        </div>
        """, unsafe_allow_html=True)
        st.dataframe(
            df_rubros.style.format({'Costo (MXN)': '${:,.2f}'}).apply(_highlight_total, axis=1),
            use_container_width=True,
            hide_index=True
        )


    with d_col2:
        st.markdown(f"""
        <div style="border-left:4px solid {BRAND_ORANGE};padding-left:12px;margin:8px 0 14px 0;">
            <h3 style="font-size:16px;font-weight:800;color:{BRAND_CHARCOAL};margin:0;">Distribución del Costo Directo</h3>
        </div>
        """, unsafe_allow_html=True)

        df_pie = pd.DataFrame([r for r in rubro_rows if r['Costo (MXN)'] >= 0])
        color_map = {
            "Materiales": BRAND_ORANGE,
            "Mano de Obra": BRAND_CHARCOAL,
            f"Supervisión ({int(sv*100)}% MO)": "#CBD5E1",
            "Subcontratos": "#059669",
            "Maquinaria": "#E2E8F0",
            f"Herramienta ({int(hta_pct*100)}% MO)": "#0EA5E9",
            "Gastos Generales": "#8C96A6"
        }
        fig_donut = px.pie(
            df_pie,
            values='Costo (MXN)',
            names='Rubro',
            hole=0.55,
            color='Rubro',
            color_discrete_map=color_map
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent')
        fig_donut.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            height=290,
            font_family="Montserrat",
            showlegend=True,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_donut, use_container_width=True)


    st.divider()
    st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                f"color:{BRAND_ORANGE};margin:0 0 8px 0;'>ANÁLISIS PONDERADO POR PARTIDA Y MÁRGENES FINANCIEROS</p>",
                unsafe_allow_html=True)


    if analisis_rows:
        df_an = pd.DataFrame(analisis_rows)
        m_cols = [c for c in df_an.columns if c not in ("N°","Partida")]
        st.dataframe(df_an.style.format({c: "${:,.2f}" for c in m_cols}), use_container_width=True, hide_index=True)

        # KPIs
        total_pv  = sum(r['Precio Venta'] for r in analisis_rows)
        total_mg  = sum(r['Margen $']     for r in analisis_rows)
        total_mat = sum(r['Materiales']   for r in analisis_rows)
        total_mo  = sum(r['M.O.']         for r in analisis_rows)

        k1, k2, k3, k4 = st.columns(4)
        def _kpi(col, label, val, fmt="${:,.2f}", color=BRAND_ORANGE):
            col.markdown(f"""
            <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};
                        border-top:4px solid {color};border-radius:8px;padding:12px 14px;
                        font-family:'Montserrat',sans-serif;">
                <p style="font-size:10px;font-weight:700;text-transform:uppercase;color:{BRAND_CHARCOAL_MED};margin:0;">{label}</p>
                <p style="font-size:20px;font-weight:900;color:{BRAND_CHARCOAL};margin:3px 0 0 0;">{fmt.format(val)}</p>
            </div>""", unsafe_allow_html=True)

        _kpi(k1, "Precio Venta Total", total_pv)
        _kpi(k2, "Utilidad Bruta",     total_mg, color="#059669")
        _kpi(k3, "Margen Real %",      (total_mg/total_pv*100) if total_pv else 0, fmt="{:,.1f}%", color="#0EA5E9")
        _kpi(k4, "Costo Directo Total",total_cd, color=BRAND_CHARCOAL)


    st.divider()

    # Control de Estado y Congelada
    st.markdown(f"<p style='font-size:11px;font-weight:800;text-transform:uppercase;"
                f"color:{BRAND_ORANGE};margin:0 0 8px 0;'>ESTADO Y CONGELAMIENTO DE COTIZACIÓN</p>",
                unsafe_allow_html=True)

    if not congelada:
        c_est1, c_est2 = st.columns([3, 2])
        with c_est1:
            aprob_por = st.text_input("Aprobada / Autorizada por", value=cot_info.get('aprobado_por','') or 'Alberto López / J&D')
            est_opts  = ["Borrador", "En Revisión", "Aprobada"]
            curr_est  = cot_info.get('estatus','Borrador')
            curr_idx  = est_opts.index(curr_est) if curr_est in est_opts else 0
            n_estatus = st.selectbox("Cambiar Estado a", est_opts, index=curr_idx)

        with c_est2:
            st.markdown(f"""
            <div style="background:#FEF3C7;border:1px solid #F59E0B;border-radius:8px;
                        padding:10px 14px;font-family:'Montserrat',sans-serif;">
                <p style="font-size:11px;font-weight:700;color:#92400E;margin:0 0 4px 0;">🔒 APROBAR Y CONGELAR</p>
                <p style="font-size:10px;color:#78350F;margin:0;">Bloquea la edición para emitir la oferta oficial. Podrás generar una nueva revisión (R1, R2) en cualquier momento.</p>
            </div>""", unsafe_allow_html=True)

        b1, b2 = st.columns([2, 2])
        with b1:
            if st.button("💾 Guardar Estado", type="primary", use_container_width=True):
                conn = get_connection()
                conn.execute("UPDATE cotizaciones SET estatus=?, aprobado_por=? WHERE id=?", (n_estatus, aprob_por, cot_id))
                conn.commit(); conn.close()
                st.success(f"Estado actualizado a **{n_estatus}**."); st.rerun()
        with b2:
            if st.button("🔒 Aprobar y CONGELAR Cotización", use_container_width=True):
                conn = get_connection()
                conn.execute("""UPDATE cotizaciones SET estatus='Aprobada', congelada=1,
                                aprobado_por=?, fecha_aprobacion=CURRENT_TIMESTAMP
                                WHERE id=?""", (aprob_por or "J&D Automation", cot_id))
                conn.commit(); conn.close()
                st.success("🔒 Cotización APROBADA y CONGELADA."); st.rerun()
    else:
        st.success(f"🔒 Esta cotización está **Aprobada y Congelada** (Revisión **{cot_info.get('revision','R0')}** por **{cot_info.get('aprobado_por','—')}**).")
        if st.button("🔄 Crear Nueva Revisión (R+1) y Desbloquear", type="primary"):
            from database.db_manager import duplicar_cotizacion_nueva_revision
            new_id, new_rev = duplicar_cotizacion_nueva_revision(cot_id)
            st.success(f"✅ Se creó la revisión **{new_rev}** como nueva cotización editable. La versión **{cot_info.get('revision','R0')}** se conserva intacta 🔒.")
    st.markdown("---")
    st.markdown(f"""
    <div style="background:#1E293B;border-radius:10px;padding:16px 20px;margin:20px 0 12px 0;font-family:'Montserrat',sans-serif;">
        <div style="color:{BRAND_ORANGE};font-weight:900;font-size:14px;letter-spacing:0.5px;">
            📜 BITÁCORA HISTÓRICA DE AUDITORÍA & CONTROL DE CAMBIOS (SUPERVISIÓN)
        </div>
        <div style="color:#CBD5E1;font-size:11px;margin-top:4px;">
            Historial de auditoría imborrable de todos los ajustes de cantidades, precios y sueldos realizados por la supervisión para la versión activa.
        </div>
    </div>
    """, unsafe_allow_html=True)

    historial_str = cot_info.get("historial_modificaciones", "") or "— No hay modificaciones registradas por la supervisión aún. —"

    st.text_area(
        "Registro de Cambios Realizados por Supervisión (Guardado en Revisión R0/R1/R2)",
        value=historial_str,
        height=220,
        disabled=True,
        key=f"ta_historial_mod_{cot_id}"
    )




# ─────────────────────────────────────────────────────────────────────────────
# PASO 5: CRONOGRAMA GANTT
# ─────────────────────────────────────────────────────────────────────────────

def _paso5_gantt(cot_id, partidas, congelada):
    st.markdown(f"""
    <div class="jd-section-header">
        <h2>Paso 5 — Cronograma del Proyecto (Gantt)</h2>
        <p>Tiempos aproximados de ejecución por actividad y partida.</p>
    </div>""", unsafe_allow_html=True)

    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT g.*, p.numero_partida, p.descripcion as partida_desc
                   FROM cotizacion_gantt g
                   LEFT JOIN cotizacion_partidas p ON g.partida_id=p.id
                   WHERE g.cotizacion_id=? ORDER BY g.orden, g.id""", (cot_id,))
    gantt_rows = [dict(r) for r in cur.fetchall()]; conn.close()

    if not congelada:
        part_opts = {f"P{p['numero_partida']} — {p['descripcion'][:40]}": p['id'] for p in partidas}
        part_opts["— Actividad general del proyecto —"] = None

        with st.form("form_gantt_editor", clear_on_submit=True):
            gc1, gc2 = st.columns([3, 2])
            with gc1: act_name = st.text_input("Actividad *", placeholder="Ej: Fabricación e integración de gabinete")
            with gc2: part_sel = st.selectbox("Partida asociada", list(part_opts.keys()))
            part_id_g = part_opts[part_sel]

            gc3, gc4, gc5, gc6 = st.columns([1.5, 1.5, 1.2, 2])
            with gc3: fecha_ini = st.date_input("Fecha Inicio", value=date.today())
            with gc4: dias_dur  = st.number_input("Duración (días)", value=5, min_value=1, step=1)
            with gc5: tipo_act  = st.selectbox("Tipo", ["Actividad","Entregable","Hito","Reunión"])
            with gc6: resp_g    = st.text_input("Responsable", placeholder="Ej: RG — Rodrigo González")

            if st.form_submit_button("➕ Agregar Actividad al Cronograma", type="primary"):
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

    if gantt_rows:
        gantt_data = []
        for row in gantt_rows:
            try: fi = datetime.strptime(str(row['fecha_inicio']), "%Y-%m-%d").date()
            except: fi = date.today()
            ff = fi + timedelta(days=int(row['dias_duracion'] or 1))
            pn = f"P{row['numero_partida']}" if row.get('numero_partida') else "General"
            gantt_data.append({
                "Actividad": row['actividad'], "Partida": pn,
                "Inicio": datetime.combine(fi, datetime.min.time()),
                "Fin": datetime.combine(ff, datetime.min.time()),
                "Tipo": row.get('tipo','Actividad'), "Responsable": row.get('responsable','—')
            })

        df_g = pd.DataFrame(gantt_data)
        tipo_colors = {"Actividad": BRAND_ORANGE, "Entregable": "#059669", "Hito": "#DC2626", "Reunión": "#0EA5E9"}
        fig_g = px.timeline(df_g, x_start="Inicio", x_end="Fin", y="Actividad", color="Tipo", color_discrete_map=tipo_colors, hover_data=["Partida","Responsable"])
        fig_g.update_yaxes(autorange="reversed")
        fig_g.update_layout(height=max(250, 55 + len(gantt_data)*35), margin=dict(t=10,b=30,l=10,r=10), font_family="Montserrat", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_g, use_container_width=True)

        for row in gantt_rows:
            rc = st.columns([.5, 3.5, 1.5, 1, 1.5, 1.8, .5])
            rc[0].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:4px 0;'>{row.get('numero_partida','—')}</p>", unsafe_allow_html=True)
            rc[1].markdown(f"<p style='font-size:13px;font-weight:700;color:{BRAND_CHARCOAL};margin:4px 0;'>{row['actividad']}</p>", unsafe_allow_html=True)
            rc[2].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:4px 0;'>{row.get('tipo','')}</p>", unsafe_allow_html=True)
            rc[3].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:4px 0;'>{row['fecha_inicio']}</p>", unsafe_allow_html=True)
            rc[4].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:4px 0;'>{row['dias_duracion']} días</p>", unsafe_allow_html=True)
            rc[5].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:4px 0;'>{row.get('responsable','—')}</p>", unsafe_allow_html=True)
            if not congelada and rc[6].button("✕", key=f"del_gantt_{row['id']}"):
                conn = get_connection()
                conn.execute("DELETE FROM cotizacion_gantt WHERE id=?", (row['id'],))
                conn.commit(); conn.close(); st.rerun()
    else:
        st.info("Aún no hay actividades en el cronograma. Agrégalas arriba.")
