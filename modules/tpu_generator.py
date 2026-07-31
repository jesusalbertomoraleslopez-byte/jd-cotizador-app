"""
Módulo de Tarjetas de Precios Unitarios (TPU) — J&D Automation Industries
Generación e inspección detallada de TPU por partida para propuestas técnicas y contratos.
Estructura ejecutiva fiel a los estándares oficiales de supervisión y precios unitarios.
"""

import streamlit as st
import pandas as pd
import io
import os
import re
from datetime import datetime
from database.models import get_connection
from utils.number_to_letters import numero_a_letras_mxn
from config import (BRAND_ORANGE, BRAND_CHARCOAL, BRAND_CHARCOAL_MED, BRAND_WHITE,
                    BRAND_BORDER_LIGHT, BRAND_GRAY_BG, get_brand_asset_path)


def calcular_tpu_partida(p, cot_info, materiales, mo, subcontratos, maquinaria, gastos_partida=0.0):
    """
    Calcula matemáticamente todos los componentes de la Tarjeta de Precio Unitario (TPU)
    para una partida de proyecto conforme al formato institucional J&D.
    """
    cant_partida = float(p.get('cantidad', 1.0) or 1.0)
    if cant_partida <= 0:
        cant_partida = 1.0

    # 1. MATERIALES (Desglose Unitario)
    mat_rows = []
    total_mat_partida = 0.0
    for m in materiales:
        m_cant = float(m.get('cantidad', 1) or 1)
        m_pu = float(m.get('precio_unitario_mxn', 0) or 0)
        m_imp = m_cant * m_pu
        total_mat_partida += m_imp
        mat_rows.append({
            "material": m.get('descripcion', 'Material'),
            "unidad": m.get('unidad', 'pza').lower(),
            "cantidad": m_cant / cant_partida,
            "costo": m_pu,
            "importe": m_imp / cant_partida
        })

    costo_mat_unitario = total_mat_partida / cant_partida

    # 2. MANO DE OBRA (Desglose Unitario con Costo H-H)
    mo_rows = []
    total_mo_partida = 0.0
    total_hh_partida = 0.0

    for o in mo:
        pers = int(o.get('cantidad_personal', 1) or 1)
        sueldo = float(o.get('sueldo_base_semanal', 0) or 0)
        fasar = float(o.get('fasar', 1.45) or 1.45)
        sobre = float(o.get('sobre_sueldo', 1.0) or 1.0)
        semanas = float(o.get('semanas', 1.0) or 1.0)

        # Costo Hora-Hombre = (Sueldo * FASAR * SobreSueldo) / 48 hrs
        costo_hh = (sueldo * fasar * sobre) / 48.0 if sueldo > 0 else 0.0
        horas_totales = pers * semanas * 48.0
        horas_unitarias = horas_totales / cant_partida
        total_hh_partida += horas_totales

        imp_mo = pers * (sueldo * fasar * sobre) * semanas
        total_mo_partida += imp_mo

        mo_rows.append({
            "puesto": o.get('categoria_nombre', 'Mano de Obra'),
            "cantidad": pers,
            "horas": horas_unitarias,
            "costo_hh": costo_hh,
            "importe": imp_mo / cant_partida
        })

    costo_mo_unitario = total_mo_partida / cant_partida
    horas_hh_unitarias = total_hh_partida / cant_partida

    # 3. PORCENTAJES DE HERRAMIENTA Y SUPERVISIÓN
    hta_pct = float(cot_info.get('herramienta_porcentaje', 0.06) or 0.06)
    if hta_pct > 1.0:
        hta_pct = hta_pct / 100.0

    sup_pct = float(cot_info.get('supervision_porcentaje', 0.62) or 0.62)
    if sup_pct > 1.0:
        sup_pct = sup_pct / 100.0

    # Herramienta = (Material + MO) * hta_pct o MO * hta_pct
    monto_herramienta_unitario = (costo_mo_unitario + costo_mat_unitario) * hta_pct
    monto_supervision_unitario = costo_mo_unitario * sup_pct

    costo_directo_parcial = costo_mat_unitario + costo_mo_unitario + monto_herramienta_unitario + monto_supervision_unitario

    # 4. SUBCONTRATOS, MAQUINARIA Y GASTOS (Asignados por unidad)
    total_sub = sum(float(s.get('importe_mxn', 0) or 0) for s in subcontratos) / cant_partida
    total_maq = sum(float(mq.get('total_mxn', 0) or 0) for mq in maquinaria) / cant_partida
    total_gas = gastos_partida / cant_partida

    costo_unitario_base = costo_directo_parcial + total_sub + total_maq + total_gas

    # 5. INDIRECTOS Y UTILIDAD
    ind_campo_pct = 0.0388  # 3.88% Indirecto de Campo
    ind_central_pct = 0.1200 # 12.00% Indirecto Central
    utilidad_pct = 0.0800    # 8.00% Utilidad

    # Permite tomar los porcentajes comerciales globales si están definidos
    mg_global = float(cot_info.get('margen_porcentaje', 0.30) or 0.30)
    if mg_global > 0:
        utilidad_pct = mg_global * 0.40
        ind_central_pct = mg_global * 0.40
        ind_campo_pct = mg_global * 0.20

    monto_ind_campo = costo_unitario_base * ind_campo_pct
    monto_ind_central = costo_unitario_base * ind_central_pct
    monto_utilidad = costo_unitario_base * utilidad_pct

    precio_unitario_final = costo_unitario_base + monto_ind_campo + monto_ind_central + monto_utilidad

    moneda = cot_info.get('moneda_cotizacion', 'MXN')
    monto_letras = numero_a_letras_mxn(precio_unitario_final, moneda)

    return {
        "numero_partida": p.get('numero_partida', 1),
        "nombre_partida": p.get('descripcion', 'Partida'),
        "unidad": p.get('unidad', 'pza').lower(),
        "horas_hh_unitarias": horas_hh_unitarias,
        "descripcion": p.get('descripcion', ''),
        "mat_rows": mat_rows,
        "costo_mat_unitario": costo_mat_unitario,
        "mo_rows": mo_rows,
        "costo_mo_unitario": costo_mo_unitario,
        "hta_pct": hta_pct * 100.0,
        "monto_herramienta": monto_herramienta_unitario,
        "sup_pct": sup_pct * 100.0,
        "monto_supervision": monto_supervision_unitario,
        "precio_unitario_cd": costo_directo_parcial,
        "costo_unitario_base": costo_unitario_base,
        "ind_campo_pct": ind_campo_pct * 100.0,
        "monto_ind_campo": monto_ind_campo,
        "ind_central_pct": ind_central_pct * 100.0,
        "monto_ind_central": monto_ind_central,
        "utilidad_pct": utilidad_pct * 100.0,
        "monto_utilidad": monto_utilidad,
        "precio_unitario_final": precio_unitario_final,
        "monto_letras": monto_letras
    }


def render_tpu_card_html(tpu_data):
    """
    Renderiza el HTML ejecutivo idéntico a las imágenes de referencia para la TPU.
    """
    mat_html_rows = ""
    for m in tpu_data['mat_rows']:
        mat_html_rows += f"""
        <tr>
            <td style="padding:4px 8px; font-weight:600;">{m['material']}</td>
            <td style="padding:4px 8px; text-align:center;">{m['unidad']}</td>
            <td style="padding:4px 8px; text-align:right;">{m['cantidad']:.3f}</td>
            <td style="padding:4px 8px; text-align:right;">${m['costo']:,.2f}</td>
            <td style="padding:4px 8px; text-align:right; font-weight:700;">${m['importe']:,.2f}</td>
        </tr>
        """

    mo_html_rows = ""
    for o in tpu_data['mo_rows']:
        mo_html_rows += f"""
        <tr>
            <td style="padding:4px 8px; font-weight:600;">{o['puesto']}</td>
            <td style="padding:4px 8px; text-align:center;">{o['cantidad']}</td>
            <td style="padding:4px 8px; text-align:right;">{o['horas']:.3f}</td>
            <td style="padding:4px 8px; text-align:right;">${o['costo_hh']:,.2f}</td>
            <td style="padding:4px 8px; text-align:right; font-weight:700;">${o['importe']:,.2f}</td>
        </tr>
        """

    return f"""
    <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:10px; padding:24px;
                font-family:'Montserrat', sans-serif; color:#0F172A; max-width:850px; margin:0 auto; box-shadow:0 6px 18px rgba(0,0,0,0.06);">
        
        <!-- ENCABEZADO DE TARJETA TPU -->
        <div style="border-bottom:2px solid #FE8C29; padding-bottom:12px; margin-bottom:16px;">
            <p style="margin:0; font-size:14px; font-weight:800; color:#434E62;"><b>Partida:</b> {tpu_data['numero_partida']:04d}</p>
            <h3 style="margin:4px 0; font-size:17px; font-weight:900; color:#FE8C29;"><b>Nombre:</b> {tpu_data['nombre_partida']}</h3>
            <p style="margin:2px 0; font-size:13px; font-weight:700;"><b>Unidad:</b> {tpu_data['unidad']} &nbsp;&bull;&nbsp; <b>Horas H-H:</b> {tpu_data['horas_hh_unitarias']:.5f}</p>
            <p style="margin:4px 0 0 0; font-size:12px; color:#475569; font-style:italic;"><b>Descripción:</b> {tpu_data['descripcion']}</p>
        </div>

        <!-- SECCIÓN 1: MATERIALES -->
        <div style="margin-bottom:16px;">
            <table style="width:100%; border-collapse:collapse; font-size:12.5px;">
                <thead>
                    <tr style="border-bottom:1.5px solid #434E62; text-align:left;">
                        <th style="padding:4px 8px; color:#434E62;">Material</th>
                        <th style="padding:4px 8px; text-align:center; color:#434E62;">Unidad</th>
                        <th style="padding:4px 8px; text-align:right; color:#434E62;">Cantidad</th>
                        <th style="padding:4px 8px; text-align:right; color:#434E62;">Costo</th>
                        <th style="padding:4px 8px; text-align:right; color:#434E62;">Importe</th>
                    </tr>
                </thead>
                <tbody>
                    {mat_html_rows if mat_html_rows else '<tr><td colspan="5" style="padding:6px 8px; color:#94A3B8; font-style:italic;">Sin materiales directos asignados</td></tr>'}
                    <tr style="border-top:1px solid #CBD5E1; font-weight:800;">
                        <td colspan="4" style="padding:6px 8px; text-align:right;">Total Materiales:</td>
                        <td style="padding:6px 8px; text-align:right; color:#0F172A;">${tpu_data['costo_mat_unitario']:,.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- SECCIÓN 2: MANO DE OBRA -->
        <div style="margin-bottom:16px;">
            <table style="width:100%; border-collapse:collapse; font-size:12.5px;">
                <thead>
                    <tr style="border-bottom:1.5px solid #434E62; text-align:left;">
                        <th style="padding:4px 8px; color:#434E62;">Mano de Obra</th>
                        <th style="padding:4px 8px; text-align:center; color:#434E62;">Cantidad</th>
                        <th style="padding:4px 8px; text-align:right; color:#434E62;">Horas</th>
                        <th style="padding:4px 8px; text-align:right; color:#434E62;">Costo HH</th>
                        <th style="padding:4px 8px; text-align:right; color:#434E62;">Importe</th>
                    </tr>
                </thead>
                <tbody>
                    {mo_html_rows if mo_html_rows else '<tr><td colspan="5" style="padding:6px 8px; color:#94A3B8; font-style:italic;">Sin mano de obra directa asignada</td></tr>'}
                    <tr style="border-top:1px solid #CBD5E1; font-weight:800;">
                        <td colspan="4" style="padding:6px 8px; text-align:right;">Total Mano de Obra:</td>
                        <td style="padding:6px 8px; text-align:right; color:#0F172A;">${tpu_data['costo_mo_unitario']:,.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- SECCIÓN 3: HERRAMIENTA, SUPERVISIÓN Y COSTO DIRECTO -->
        <div style="margin-bottom:18px; text-align:right; font-size:13px;">
            <table style="float:right; width:340px; border-collapse:collapse;">
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Herramienta</td>
                    <td style="padding:3px 8px; text-align:right; color:#475569;">{tpu_data['hta_pct']:.2f}%</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_herramienta']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Supervisión</td>
                    <td style="padding:3px 8px; text-align:right; color:#475569;">{tpu_data['sup_pct']:.2f}%</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_supervision']:,.2f}</td>
                </tr>
                <tr style="border-top:1.5px solid #FE8C29; font-weight:800;">
                    <td colspan="2" style="padding:4px 8px; font-size:12px; text-transform:uppercase;">PRECIO UNITARIO C.D.</td>
                    <td style="padding:4px 8px; text-align:right; font-size:14px; color:#FE8C29;">${tpu_data['precio_unitario_cd']:,.2f}</td>
                </tr>
            </table>
            <div style="clear:both;"></div>
        </div>

        <!-- SECCIÓN 4: COSTO BASE, INDIRECTOS Y UTILIDAD FINAL -->
        <div style="margin-top:16px; border-top:2px solid #E2E8F0; padding-top:12px;">
            <table style="float:right; width:380px; border-collapse:collapse; font-size:13px;">
                <tr>
                    <td colspan="2" style="padding:3px 8px; font-weight:800; color:#334155;">COSTO UNITARIO BASE</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:800; color:#334155;">${tpu_data['costo_unitario_base']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Indirecto de campo</td>
                    <td style="padding:3px 8px; text-align:right; color:#475569;">{tpu_data['ind_campo_pct']:.2f}%</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_ind_campo']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Indirecto Central</td>
                    <td style="padding:3px 8px; text-align:right; color:#475569;">{tpu_data['ind_central_pct']:.2f}%</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_ind_central']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Utilidad</td>
                    <td style="padding:3px 8px; text-align:right; color:#475569;">{tpu_data['utilidad_pct']:.2f}%</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_utilidad']:,.2f}</td>
                </tr>
                <tr style="background:#10B981; color:#FFFFFF; font-weight:900; font-size:15px;">
                    <td colspan="2" style="padding:8px 12px; border-radius:4px 0 0 4px;">PRECIO UNITARIO</td>
                    <td style="padding:8px 12px; text-align:right; border-radius:0 4px 4px 0;">${tpu_data['precio_unitario_final']:,.2f}</td>
                </tr>
            </table>
            <div style="clear:both;"></div>
            <p style="margin:12px 0 0 0; text-align:right; font-size:11.5px; font-weight:700; color:#334155; font-style:italic;">
                {tpu_data['monto_letras']}
            </p>
        </div>

    </div>
    """


def render_tpu_generator():
    """
    Renderiza la interfaz interactiva de Tarjetas de Precios Unitarios (TPU).
    """
    st.markdown(f"""
    <div style="background:{BRAND_WHITE}; border:1px solid {BRAND_BORDER_LIGHT}; border-left:5px solid {BRAND_ORANGE};
                border-radius:8px; padding:16px 20px; margin-bottom:18px;">
        <h3 style="margin:0; color:{BRAND_CHARCOAL}; font-size:18px; font-weight:800;">🎴 DESGLOSE DE TARJETAS DE PRECIOS UNITARIOS (TPU)</h3>
        <p style="margin:4px 0 0 0; color:{BRAND_CHARCOAL_MED}; font-size:12px;">
            Inspección ejecutiva de costo directo, rendimientos H-H, indirectos de campo/central y precio unitario final por partida.
        </p>
    </div>
    """, unsafe_allow_html=True)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.folio, c.proyecto, c.revision, c.margen_porcentaje, c.comision_porcentaje, cl.nombre as cliente
        FROM cotizaciones c LEFT JOIN clientes cl ON c.cliente_id = cl.id
        ORDER BY c.id DESC
    """)
    cotizaciones = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not cotizaciones:
        st.warning("⚠️ No hay cotizaciones registradas. Crea una cotización en el Modificador o Importador Excel para generar sus TPU.")
        return

    cot_options = {f"{c['folio']} - {c['proyecto']} ({c.get('cliente','—')})": c['id'] for c in cotizaciones}
    selected_label = st.selectbox("📌 Seleccionar Cotización Activa para Inspeccionar TPU", list(cot_options.keys()))
    cot_id = cot_options[selected_label]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cotizaciones WHERE id=?", (cot_id,))
    cot_info = dict(cursor.fetchone())

    cursor.execute("SELECT * FROM cotizacion_partidas WHERE cotizacion_id = ? ORDER BY numero_partida", (cot_id,))
    partidas = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not partidas:
        st.info("La cotización seleccionada no tiene partidas registradas aún.")
        return

    partida_opts = {f"Partida {p['numero_partida']:04d}: {p['descripcion'][:50]}": p['id'] for p in partidas}
    partida_opts["🌟 TODAS LAS PARTIDAS (REPORTE CONSOLIDADO DE TPU)"] = "ALL"

    p_label = st.selectbox("🎯 Seleccionar Partida para Generar Tarjeta TPU", list(partida_opts.keys()))
    selected_p_id = partida_opts[p_label]

    if selected_p_id == "ALL":
        st.markdown(f"### 📋 Reporte Consolidado de Tarjetas TPU ({len(partidas)} Partidas)")
        tpu_list = []
        for p in partidas:
            p_id = p['id']
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT * FROM cotizacion_materiales_detalle WHERE partida_id=?", (p_id,))
            mats = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT * FROM cotizacion_mo_detalle WHERE partida_id=?", (p_id,))
            mo = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT * FROM cotizacion_subcontratos_detalle WHERE partida_id=?", (p_id,))
            sub = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT * FROM cotizacion_maquinaria_detalle WHERE partida_id=?", (p_id,))
            maq = [dict(r) for r in cur.fetchall()]
            conn.close()

            tpu_data = calcular_tpu_partida(p, cot_info, mats, mo, sub, maq)
            tpu_list.append(tpu_data)
            st.markdown(render_tpu_card_html(tpu_data), unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    else:
        p_info = next(p for p in partidas if p['id'] == selected_p_id)

        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM cotizacion_materiales_detalle WHERE partida_id=?", (selected_p_id,))
        mats = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM cotizacion_mo_detalle WHERE partida_id=?", (selected_p_id,))
        mo = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM cotizacion_subcontratos_detalle WHERE partida_id=?", (selected_p_id,))
        sub = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT * FROM cotizacion_maquinaria_detalle WHERE partida_id=?", (selected_p_id,))
        maq = [dict(r) for r in cur.fetchall()]
        conn.close()

        tpu_data = calcular_tpu_partida(p_info, cot_info, mats, mo, sub, maq)
        st.markdown(render_tpu_card_html(tpu_data), unsafe_allow_html=True)
