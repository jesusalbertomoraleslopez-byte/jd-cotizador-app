"""
Módulo de Tarjetas de Precios Unitarios (TPU) — J&D Automation Industries
Generación e inspección detallada de TPU por partida con pantalla interactiva de ajuste en línea.
Implementa la regla de selección de 2 casillas (1 para SUBIR y 1 para BAJAR) en una sola pantalla unificada.
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

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def _get_jd_fonts():
    bold_font = "Helvetica-Bold"
    regular_font = "Helvetica"
    try:
        brand_dir = r"C:\Users\albertol\JD_Automation_Brand_Assets\Imagen Corporativa J&D\JD_ENTREGABLES\JD_TIPOGRAFIAS\nexa"
        heavy_path = os.path.join(brand_dir, "Nexa-Heavy.ttf")
        light_path = os.path.join(brand_dir, "Nexa-ExtraLight.ttf")

        if os.path.exists(heavy_path):
            if "Nexa-Heavy" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('Nexa-Heavy', heavy_path))
            bold_font = "Nexa-Heavy"

        if os.path.exists(light_path):
            if "Nexa-Light" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('Nexa-Light', light_path))
            regular_font = "Nexa-Light"
    except Exception:
        pass
    return bold_font, regular_font


def calcular_tpu_partida(p, cot_info, materiales, mo, subcontratos, maquinaria, gastos_partida=0.0):
    """
    Calcula todos los componentes de la Tarjeta TPU garantizando MATCH 100% con la cotización.
    """
    cant_partida = float(p.get('cantidad', 1.0) or 1.0)
    if cant_partida <= 0:
        cant_partida = 1.0

    # Cargar valores personalizados de la BD si existen para esta partida
    custom_tpu_dict = {}
    try:
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT * FROM cotizacion_tpu_custom WHERE partida_id=?", (p['id'],))
        r = cur.fetchone()
        if r:
            custom_tpu_dict = dict(r)
        conn.close()
    except Exception:
        pass

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
    hh_factor = float(custom_tpu_dict.get('horas_hh_factor', 1.0) or 1.0)
    mo_rows = []
    total_mo_partida = 0.0
    total_hh_partida = 0.0

    for o in mo:
        pers = int(o.get('cantidad_personal', 1) or 1)
        sueldo = float(o.get('sueldo_base_semanal', 0) or 0)
        fasar = float(o.get('fasar', 1.45) or 1.45)
        sobre = float(o.get('sobre_sueldo', 1.0) or 1.0)
        semanas = float(o.get('semanas', 1.0) or 1.0)

        costo_hh = (sueldo * fasar * sobre) / 48.0 if sueldo > 0 else 0.0
        horas_totales = pers * semanas * 48.0 * hh_factor
        horas_unitarias = horas_totales / cant_partida
        total_hh_partida += horas_totales

        imp_mo = pers * (sueldo * fasar * sobre) * semanas * hh_factor
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
    if custom_tpu_dict.get('herramienta_pct') is not None:
        hta_pct = float(custom_tpu_dict['herramienta_pct']) / 100.0 if float(custom_tpu_dict['herramienta_pct']) > 1.0 else float(custom_tpu_dict['herramienta_pct'])
    else:
        hta_pct = float(cot_info.get('herramienta_porcentaje', 0.03) or 0.03)
        if hta_pct > 1.0: hta_pct = hta_pct / 100.0

    if custom_tpu_dict.get('supervision_pct') is not None:
        sup_pct = float(custom_tpu_dict['supervision_pct']) / 100.0 if float(custom_tpu_dict['supervision_pct']) > 1.0 else float(custom_tpu_dict['supervision_pct'])
    else:
        sup_pct = float(cot_info.get('supervision_porcentaje', 0.30) or 0.30)
        if sup_pct > 1.0: sup_pct = sup_pct / 100.0

    monto_herramienta_unitario = costo_mo_unitario * hta_pct
    monto_supervision_unitario = costo_mo_unitario * sup_pct

    precio_unitario_mo_factor = costo_mo_unitario + monto_herramienta_unitario + monto_supervision_unitario

    # 4. SUBCONTRATOS, MAQUINARIA Y GASTOS
    total_sub = sum(float(s.get('importe_mxn', 0) or 0) for s in subcontratos) / cant_partida
    total_maq = sum(float(mq.get('total_mxn', 0) or 0) for mq in maquinaria) / cant_partida
    total_gas = gastos_partida / cant_partida

    costo_unitario_base = costo_mat_unitario + precio_unitario_mo_factor + total_sub + total_maq + total_gas

    # 5. PRECIO TARGET Y BALANCE DE INDIRECTOS
    pv_registrado = float(p.get('precio_venta', 0) or 0)
    if pv_registrado > 0:
        precio_unitario_target = pv_registrado / cant_partida
    else:
        cd_tot = float(p.get('costo_directo_total', 0) or 0)
        mg_global = float(cot_info.get('margen_porcentaje', 0.35) or 0.35)
        m_factor = (1.0 - mg_global) if mg_global < 1.0 else 0.65
        precio_unitario_target = (cd_tot / m_factor) / cant_partida if cd_tot > 0 else (costo_unitario_base / 0.65)

    if precio_unitario_target < costo_unitario_base:
        precio_unitario_target = costo_unitario_base

    diferencia_indirectos = precio_unitario_target - costo_unitario_base

    if custom_tpu_dict.get('ind_campo_pct') is not None and custom_tpu_dict.get('ind_central_pct') is not None and custom_tpu_dict.get('utilidad_pct') is not None:
        ind_campo_pct = float(custom_tpu_dict['ind_campo_pct'])
        ind_central_pct = float(custom_tpu_dict['ind_central_pct'])
        utilidad_pct = float(custom_tpu_dict['utilidad_pct'])

        monto_ind_campo = costo_unitario_base * (ind_campo_pct / 100.0)
        monto_ind_central = costo_unitario_base * (ind_central_pct / 100.0)
        monto_utilidad = costo_unitario_base * (utilidad_pct / 100.0)
    else:
        # Estándar J&D: Indirecto de Campo ~ 5.00%, Indirecto Central ~ 12.00%, Utilidad absorbe el saldo
        monto_ind_campo = costo_unitario_base * 0.0500
        monto_ind_central = costo_unitario_base * 0.1200
        monto_utilidad = max(0.0, diferencia_indirectos - monto_ind_campo - monto_ind_central)

        ind_campo_pct = 5.00
        ind_central_pct = 12.00
        utilidad_pct = (monto_utilidad / costo_unitario_base * 100.0) if costo_unitario_base > 0 else 8.00

    precio_unitario_final = costo_unitario_base + monto_ind_campo + monto_ind_central + monto_utilidad

    moneda = cot_info.get('moneda_cotizacion', 'MXN')
    monto_letras = numero_a_letras_mxn(precio_unitario_final, moneda)

    return {
        "partida_id": p['id'],
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
        "precio_unitario_mo_factor": precio_unitario_mo_factor,
        "costo_unitario_base": costo_unitario_base,
        "ind_campo_pct": ind_campo_pct,
        "monto_ind_campo": monto_ind_campo,
        "ind_central_pct": ind_central_pct,
        "monto_ind_central": monto_ind_central,
        "utilidad_pct": utilidad_pct,
        "monto_utilidad": monto_utilidad,
        "precio_unitario_final": precio_unitario_final,
        "precio_unitario_target": precio_unitario_target,
        "monto_letras": monto_letras,
        "custom_tpu_dict": custom_tpu_dict
    }


def generate_tpu_pdf_oficial(cot_info, partidas):
    """
    Genera un PDF membretado oficial con la hoja membretada J&D (hoja_membretada.png)
    y colores institucionales, garantizando el MATCH del 100% con la tabla de cotización.
    """
    try:
        buffer = io.BytesIO()

        class TPUJDFooterCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.pages = []
                bg_path = get_brand_asset_path("hoja_membretada.png")
                if os.path.exists(bg_path):
                    try:
                        self.saveState()
                        self.drawImage(bg_path, 0, 0, width=612, height=792)
                        self.restoreState()
                    except Exception:
                        pass

            def _startPage(self):
                super()._startPage()
                bg_path = get_brand_asset_path("hoja_membretada.png")
                if os.path.exists(bg_path):
                    try:
                        self.saveState()
                        self.drawImage(bg_path, 0, 0, width=612, height=792)
                        self.restoreState()
                    except Exception:
                        pass

            def showPage(self):
                self.pages.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                num_pages = len(self.pages)
                for page in self.pages:
                    self.__dict__.update(page)
                    self.draw_page_decorations(num_pages)
                    super().showPage()
                super().save()

            def draw_page_decorations(self, page_count):
                self.saveState()
                bold_f, reg_f = _get_jd_fonts()
                self.setFont(reg_f, 8)
                self.setFillColor(colors.HexColor('#64748B'))
                self.drawString(36, 30, f"Propuesta Técnica y Comercial: {cot_info.get('proyecto','—')} | Ref: {cot_info.get('folio','—')}")
                self.drawRightString(612 - 36, 30, f"Página {self._pageNumber} de {page_count}")
                self.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=54,
            bottomMargin=54
        )
        bold_f, reg_f = _get_jd_fonts()

        phead_style = ParagraphStyle('PHead', fontName=bold_f, fontSize=10, leading=13, textColor=colors.HexColor('#FE8C29'))
        normal_style = ParagraphStyle('TPUNormal', fontName=reg_f, fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'))
        header_style = ParagraphStyle('TPUHeader', fontName=bold_f, fontSize=8.5, leading=10, textColor=colors.white, alignment=1)

        story = []

        story.append(Paragraph("<b>DESGLOSE OFICIAL DE TARJETAS DE PRECIOS UNITARIOS (TPU)</b>", ParagraphStyle('Title', fontName=bold_f, fontSize=13, leading=16, textColor=colors.HexColor('#FE8C29'))))
        story.append(Paragraph(f"Proyecto: <b>{cot_info.get('proyecto','—')}</b> &bull; Folio: <b>{cot_info.get('folio','—')}</b> &bull; Revisión: <b>{cot_info.get('revision','R0')}</b>", normal_style))
        story.append(Spacer(1, 14))

        idx = 0
        for p in partidas:
            idx += 1
            if idx > 1:
                story.append(Spacer(1, 14))

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

            tpu = calcular_tpu_partida(p, cot_info, mats, mo, sub, maq)

            story.append(Paragraph(f"<b>Partida {tpu['numero_partida']:04d}:</b> {tpu['nombre_partida']}", phead_style))
            story.append(Paragraph(f"Unidad: {tpu['unidad']} | Horas: {tpu['horas_hh_unitarias']:.5f} hrs | Alcance: {tpu['descripcion']}", normal_style))
            story.append(Spacer(1, 4))

            # Tabla Materiales
            mat_table_data = [[Paragraph("<b>Material</b>", header_style), Paragraph("<b>Unidad</b>", header_style), Paragraph("<b>Cantidad</b>", header_style), Paragraph("<b>Costo</b>", header_style), Paragraph("<b>Importe</b>", header_style)]]
            for m in tpu['mat_rows']:
                mat_table_data.append([
                    Paragraph(m['material'], normal_style),
                    Paragraph(m['unidad'], normal_style),
                    Paragraph(f"{m['cantidad']:.3f}", normal_style),
                    Paragraph(f"${m['costo']:,.2f}", normal_style),
                    Paragraph(f"${m['importe']:,.2f}", normal_style)
                ])
            mat_table_data.append([Paragraph("<b>Total</b>", ParagraphStyle('R', fontName=bold_f, fontSize=8.5, alignment=2)), "", "", "", Paragraph(f"<b>${tpu['costo_mat_unitario']:,.2f}</b>", ParagraphStyle('R2', fontName=bold_f, fontSize=8.5, alignment=2))])

            t_mat = Table(mat_table_data, colWidths=[240, 50, 60, 80, 80])
            t_mat.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('ALIGN', (2,1), (-1,-1), 'RIGHT'),
            ]))
            story.append(t_mat)
            story.append(Spacer(1, 6))

            # Tabla Mano de Obra + Factores
            mo_table_data = [[Paragraph("<b>Mano de Obra</b>", header_style), Paragraph("<b>Cantidad</b>", header_style), Paragraph("<b>Horas</b>", header_style), Paragraph("<b>Costo HH</b>", header_style), Paragraph("<b>Importe</b>", header_style)]]
            for o in tpu['mo_rows']:
                mo_table_data.append([
                    Paragraph(o['puesto'], normal_style),
                    Paragraph(str(o['cantidad']), normal_style),
                    Paragraph(f"{o['horas']:.3f}", normal_style),
                    Paragraph(f"${o['costo_hh']:,.2f}", normal_style),
                    Paragraph(f"${o['importe']:,.2f}", normal_style)
                ])
            mo_table_data.append([Paragraph("<b>Total</b>", ParagraphStyle('R', fontName=bold_f, fontSize=8.5, alignment=2)), "", "", "", Paragraph(f"<b>${tpu['costo_mo_unitario']:,.2f}</b>", ParagraphStyle('R2', fontName=bold_f, fontSize=8.5, alignment=2))])
            mo_table_data.append([Paragraph(f"Herramienta {tpu['hta_pct']:.2f}%", normal_style), "", "", "", Paragraph(f"${tpu['monto_herramienta']:,.2f}", ParagraphStyle('R', fontName=reg_f, fontSize=8.5, alignment=2))])
            mo_table_data.append([Paragraph(f"Supervisión {tpu['sup_pct']:.2f}%", normal_style), "", "", "", Paragraph(f"${tpu['monto_supervision']:,.2f}", ParagraphStyle('R', fontName=reg_f, fontSize=8.5, alignment=2))])
            mo_table_data.append([Paragraph("<b>PRECIO UNITARIO</b>", ParagraphStyle('B', fontName=bold_f, fontSize=8.5)), "", "", "", Paragraph(f"<b>${tpu['precio_unitario_mo_factor']:,.2f}</b>", ParagraphStyle('BR', fontName=bold_f, fontSize=8.5, alignment=2))])

            t_mo = Table(mo_table_data, colWidths=[240, 50, 60, 80, 80])
            t_mo.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ]))
            story.append(t_mo)
            story.append(Spacer(1, 6))

            # Resumen Final TPU
            tot_table_data = [
                [Paragraph("<b>COSTO UNITARIO BASE</b>", ParagraphStyle('B', fontName=bold_f, fontSize=8.5)), Paragraph(f"<b>${tpu['costo_unitario_base']:,.2f}</b>", ParagraphStyle('BR', fontName=bold_f, fontSize=8.5, alignment=2))],
                [Paragraph(f"Indirecto de Campo ({tpu['ind_campo_pct']:.2f}%)", normal_style), Paragraph(f"${tpu['monto_ind_campo']:,.2f}", ParagraphStyle('R', fontName=reg_f, fontSize=8.5, alignment=2))],
                [Paragraph(f"Indirecto Central ({tpu['ind_central_pct']:.2f}%)", normal_style), Paragraph(f"${tpu['monto_ind_central']:,.2f}", ParagraphStyle('R', fontName=reg_f, fontSize=8.5, alignment=2))],
                [Paragraph(f"Utilidad ({tpu['utilidad_pct']:.2f}%)", normal_style), Paragraph(f"${tpu['monto_utilidad']:,.2f}", ParagraphStyle('R', fontName=reg_f, fontSize=8.5, alignment=2))],
                [Paragraph("<b>PRECIO UNITARIO FINAL</b>", ParagraphStyle('W', fontName=bold_f, fontSize=9.5, textColor=colors.white)), Paragraph(f"<b>${tpu['precio_unitario_final']:,.2f}</b>", ParagraphStyle('WR', fontName=bold_f, fontSize=9.5, textColor=colors.white, alignment=2))]
            ]
            t_tot = Table(tot_table_data, colWidths=[330, 180])
            t_tot.setStyle(TableStyle([
                ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#10B981')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ]))
            story.append(t_tot)
            story.append(Spacer(1, 2))
            story.append(Paragraph(f"<i>{tpu['monto_letras']}</i>", ParagraphStyle('Lit', fontName=reg_f, fontSize=8, alignment=2, textColor=colors.HexColor('#475569'))))
            story.append(Spacer(1, 14))

        doc.build(story, canvasmaker=TPUJDFooterCanvas)
        return buffer.getvalue()
    except Exception:
        return b""


def render_tpu_generator():
    """
    Renderiza la interfaz interactiva oficial de Tarjetas de Precios Unitarios (TPU)
    idéntica a la pantalla solicitada por el usuario con controles [-] [+] y regla de 2 casillas (1 SUBIR, 1 BAJAR).
    """
    st.markdown(f"""
    <div style="background:{BRAND_WHITE}; border:1px solid {BRAND_BORDER_LIGHT}; border-left:5px solid {BRAND_ORANGE};
                border-radius:8px; padding:16px 20px; margin-bottom:18px;">
        <h3 style="margin:0; color:{BRAND_CHARCOAL}; font-size:18px; font-weight:800;">🎴 PANTALLA UNIFICADA DE AJUSTE Y BALANCE TPU</h3>
        <p style="margin:4px 0 0 0; color:{BRAND_CHARCOAL_MED}; font-size:12px;">
            Selecciona la casilla <b>☑️ SUBE</b> (Driver que aumenta) y la casilla <b>☑️ BAJA</b> (Rubro que absorbe el cambio). El PRECIO UNITARIO FINAL permanece 100% FIJO.
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
    selected_label = st.selectbox("📌 Seleccionar Cotización Activa para Ajustar TPU", list(cot_options.keys()))
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

    clean_f = re.sub(r'[^a-zA-Z0-9_-]', '_', cot_info.get('folio', 'COT-001')).strip('_')
    tpu_pdf_bytes = generate_tpu_pdf_oficial(cot_info, partidas)

    st.markdown(f"""
    <div style="background:{BRAND_GRAY_BG}; border:2px solid {BRAND_ORANGE}; border-radius:10px; padding:16px 20px; margin:16px 0;">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <span style="font-size:22px;">🎴</span>
            <span style="font-size:16px; font-weight:900; color:{BRAND_CHARCOAL};">EXPORTACIÓN OFICIAL DE TARJETAS DE PRECIOS UNITARIOS</span>
        </div>
        <p style="font-size:12px; color:{BRAND_CHARCOAL_MED}; margin:0 0 12px 0;">
            Descarga el reporte completo en formato PDF membretado con la Hoja Membretada Oficial J&D y el MATCH 100% de precios de la cotización <b>{cot_info.get('folio')}</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if tpu_pdf_bytes:
        st.download_button(
            label="⬇️ 🎴 DESCARGAR DOCUMENTO DE TARJETAS TPU (.PDF)",
            data=tpu_pdf_bytes,
            file_name=f"{clean_f}_Tarjetas_Precios_Unitarios.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key="btn_download_tpu_pdf_mod6"
        )

    st.divider()

    partida_opts = {f"Partida {p['numero_partida']:04d}: {p['descripcion'][:50]}": p['id'] for p in partidas}
    partida_opts["🌟 TODAS LAS PARTIDAS (REPORTE CONSOLIDADO DE TPU)"] = "ALL"

    p_label = st.selectbox("🎯 Seleccionar Partida para Generar y Ajustar Tarjeta TPU", list(partida_opts.keys()))
    selected_p_id = partida_opts[p_label]

    if selected_p_id == "ALL":
        st.markdown(f"### 📋 Reporte Consolidado de Tarjetas TPU ({len(partidas)} Partidas)")
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
            render_unified_tpu_card_screen(tpu_data, cot_info, p, is_read_only=True)
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
        render_unified_tpu_card_screen(tpu_data, cot_info, p_info, is_read_only=False)


def render_unified_tpu_card_screen(tpu_data, cot_info, p_info, is_read_only=False):
    """
    Renderiza la Pantalla Única de Ajuste TPU idéntica a la imagen de prototipo del usuario.
    Regla: Permite seleccionar 2 casillas globales (1 para SUBIR y 1 para BAJAR).
    """
    pid = tpu_data['partida_id']

    # Inicializar estado en session_state
    if f"sup_{pid}" not in st.session_state:
        st.session_state[f"sup_{pid}"] = float(tpu_data['sup_pct'])
    if f"hta_{pid}" not in st.session_state:
        st.session_state[f"hta_{pid}"] = float(tpu_data['hta_pct'])
    if f"hh_{pid}" not in st.session_state:
        st.session_state[f"hh_{pid}"] = float(tpu_data['custom_tpu_dict'].get('horas_hh_factor', 1.0) or 1.0)

    if f"sube_driver_{pid}" not in st.session_state:
        st.session_state[f"sube_driver_{pid}"] = "supervision" # 'supervision', 'herramienta', 'mo_hh'
    if f"baja_driver_{pid}" not in st.session_state:
        st.session_state[f"baja_driver_{pid}"] = "ind_campo" # 'ind_campo', 'ind_central', 'utilidad'

    sup_val = st.session_state[f"sup_{pid}"]
    hta_val = st.session_state[f"hta_{pid}"]
    hh_val = st.session_state[f"hh_{pid}"]
    sube_sel = st.session_state[f"sube_driver_{pid}"]
    baja_sel = st.session_state[f"baja_driver_{pid}"]

    target_price = tpu_data['precio_unitario_target']

    # Recálculos en vivo
    c_mo_u = tpu_data['costo_mo_unitario'] * hh_val
    m_hta_u = c_mo_u * (hta_val / 100.0)
    m_sup_u = c_mo_u * (sup_val / 100.0)
    pu_mo_fac = c_mo_u + m_hta_u + m_sup_u

    costo_base = tpu_data['costo_mat_unitario'] + pu_mo_fac
    dif_ind = max(0.0, target_price - costo_base)

    if baja_sel == "ind_campo":
        m_ind_central = costo_base * 0.1200
        m_utilidad = max(0.0, dif_ind * 0.35)
        m_ind_campo = max(0.0, dif_ind - m_ind_central - m_utilidad)
    elif baja_sel == "ind_central":
        m_ind_campo = costo_base * 0.0500
        m_utilidad = max(0.0, dif_ind * 0.35)
        m_ind_central = max(0.0, dif_ind - m_ind_campo - m_utilidad)
    else: # 'utilidad' (Default compensator)
        m_ind_campo = costo_base * 0.0500
        m_ind_central = costo_base * 0.1200
        m_utilidad = max(0.0, dif_ind - m_ind_campo - m_ind_central)

    p_ind_campo = (m_ind_campo / costo_base * 100.0) if costo_base > 0 else 0.0
    p_ind_central = (m_ind_central / costo_base * 100.0) if costo_base > 0 else 0.0
    p_utilidad = (m_utilidad / costo_base * 100.0) if costo_base > 0 else 0.0

    precio_final_sim = costo_base + m_ind_campo + m_ind_central + m_utilidad
    letras_sim = numero_a_letras_mxn(precio_final_sim, cot_info.get('moneda_cotizacion','MXN'))

    # ── TARJETA TPU UNIFICADA CON CONTROLES INLINE Y REGLA DE 2 CASILLAS ──
    st.markdown(f"""
    <div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:10px; padding:20px;
                font-family:'Montserrat', sans-serif; color:#0F172A; max-width:920px; margin:0 auto; box-shadow:0 6px 18px rgba(0,0,0,0.06);">
        
        <div style="border-bottom:2px solid #FE8C29; padding-bottom:8px; margin-bottom:12px;">
            <p style="margin:0; font-size:14px; font-weight:800; color:#FE8C29;">Partida {tpu_data['numero_partida']:04d}: {tpu_data['nombre_partida']}</p>
            <p style="margin:2px 0 0 0; font-size:12px; font-weight:700; color:#334155;">
                <b>Unidad:</b> {tpu_data['unidad']} &nbsp;|&nbsp; <b>Horas:</b> {tpu_data['horas_hh_unitarias'] * hh_val:.5f} hrs &nbsp;|&nbsp; <b>Alcance:</b> {tpu_data['descripcion']}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. TABLA MATERIALES
    st.markdown("##### 📦 Material")
    mat_data = []
    for m in tpu_data['mat_rows']:
        mat_data.append({
            "Material": m['material'],
            "Unidad": m['unidad'],
            "Cantidad": f"{m['cantidad']:.3f}",
            "Costo": f"${m['costo']:,.2f}",
            "Importe": f"${m['importe']:,.2f}"
        })
    if mat_data:
        st.table(pd.DataFrame(mat_data))
    else:
        st.caption("Sin materiales directos asignados.")
    st.markdown(f"<p style='text-align:right; font-weight:800; margin-top:-10px;'>Total Material: <b>${tpu_data['costo_mat_unitario']:,.2f}</b></p>", unsafe_allow_html=True)

    # 2. SELECCIÓN DE REGLA DE CASILLAS (1 SUBIR, 1 BAJAR)
    if not is_read_only:
        st.markdown("<div style='background:#FFF7ED; border:1px solid #FFEDD5; border-radius:6px; padding:8px 12px; margin:10px 0;'><b>⚡ Regla de Ajuste de Casillas:</b> Selecciona 1 casilla para <b>SUBIR (🟢)</b> y 1 casilla para <b>BAJAR (🔴)</b>.</div>", unsafe_allow_html=True)
        r_c1, r_c2 = st.columns(2)
        with r_c1:
            sel_sube = st.radio("🟢 Casilla seleccionada para SUBIR:", [
                "Supervisión %",
                "Herramienta %",
                "Rendimiento H-H"
            ], index=0 if sube_sel == "supervision" else (1 if sube_sel == "herramienta" else 2), key=f"rad_sube_{pid}")
            if "Supervisión" in sel_sube: st.session_state[f"sube_driver_{pid}"] = "supervision"
            elif "Herramienta" in sel_sube: st.session_state[f"sube_driver_{pid}"] = "herramienta"
            else: st.session_state[f"sube_driver_{pid}"] = "mo_hh"

        with r_c2:
            sel_baja = st.radio("🔴 Casilla seleccionada para BAJAR (Absorbe la diferencia):", [
                "Indirecto de Campo",
                "Indirecto Central",
                "Utilidad"
            ], index=0 if baja_sel == "ind_campo" else (1 if baja_sel == "ind_central" else 2), key=f"rad_baja_{pid}")
            if "Campo" in sel_baja: st.session_state[f"baja_driver_{pid}"] = "ind_campo"
            elif "Central" in sel_baja: st.session_state[f"baja_driver_{pid}"] = "ind_central"
            else: st.session_state[f"baja_driver_{pid}"] = "utilidad"

    # 3. TABLA MANO DE OBRA Y CONTROLES INLINE
    st.markdown("##### 👷 Mano de Obra")
    for o in tpu_data['mo_rows']:
        cm1, cm2, cm3, cm4, cm5 = st.columns([3, 1, 3, 1.5, 1.5])
        with cm1: st.markdown(f"**{o['puesto']}**")
        with cm2: st.markdown(f"Cant: **{o['cantidad']}**")
        with cm3:
            if not is_read_only and sube_sel == "mo_hh":
                b1, b2, b3 = st.columns([1, 1, 2])
                with b1:
                    if st.button("➖", key=f"dec_hh_{pid}_{o['puesto']}"):
                        st.session_state[f"hh_{pid}"] = max(0.2, round(st.session_state[f"hh_{pid}"] - 0.05, 2))
                        st.rerun()
                with b2:
                    if st.button("➕", key=f"inc_hh_{pid}_{o['puesto']}"):
                        st.session_state[f"hh_{pid}"] = round(st.session_state[f"hh_{pid}"] + 0.05, 2)
                        st.rerun()
                with b3: st.caption(f"Horas: **{o['horas'] * hh_val:.3f}**")
            else:
                st.markdown(f"Horas: **{o['horas'] * hh_val:.3f}**")
        with cm4: st.markdown(f"Costo HH: **${o['costo_hh']:,.2f}**")
        with cm5: st.markdown(f"Importe: **${o['importe'] * hh_val:,.2f}**")

    st.markdown(f"<p style='text-align:right; font-weight:800;'>Total Mano de Obra: <b>${c_mo_u:,.2f}</b></p>", unsafe_allow_html=True)
    st.divider()

    # 4. HERRAMIENTA Y SUPERVISIÓN
    ch1, ch2, ch3, ch4 = st.columns([2, 3, 2, 2])
    with ch1:
        prefix = "🟢 " if sube_sel == "herramienta" else ""
        st.markdown(f"**{prefix}Herramienta**")
    with ch2:
        if not is_read_only and sube_sel == "herramienta":
            hb1, hb2, hb3 = st.columns([1, 1, 2])
            with hb1:
                if st.button("➖", key=f"dec_hta_{pid}"):
                    st.session_state[f"hta_{pid}"] = max(0.0, round(st.session_state[f"hta_{pid}"] - 0.5, 1))
                    st.rerun()
            with hb2:
                if st.button("➕", key=f"inc_hta_{pid}"):
                    st.session_state[f"hta_{pid}"] = round(st.session_state[f"hta_{pid}"] + 0.5, 1)
                    st.rerun()
            with hb3: st.markdown(f"**{hta_val:.2f}%**")
        else:
            st.markdown(f"**{hta_val:.2f}%**")
    with ch3: st.caption("Factor MO")
    with ch4: st.markdown(f"<p style='text-align:right; font-weight:700;'>${m_hta_u:,.2f}</p>", unsafe_allow_html=True)

    cs1, cs2, cs3, cs4 = st.columns([2, 3, 2, 2])
    with cs1:
        prefix = "🟢 " if sube_sel == "supervision" else ""
        st.markdown(f"**{prefix}Supervisión**")
    with cs2:
        if not is_read_only and sube_sel == "supervision":
            sb1, sb2, sb3 = st.columns([1, 1, 2])
            with sb1:
                if st.button("➖", key=f"dec_sup_{pid}"):
                    st.session_state[f"sup_{pid}"] = max(0.0, round(st.session_state[f"sup_{pid}"] - 1.0, 1))
                    st.rerun()
            with sb2:
                if st.button("➕", key=f"inc_sup_{pid}"):
                    st.session_state[f"sup_{pid}"] = round(st.session_state[f"sup_{pid}"] + 1.0, 1)
                    st.rerun()
            with sb3: st.markdown(f"**{sup_val:.2f}%**")
        else:
            st.markdown(f"**{sup_val:.2f}%**")
    with cs3: st.caption("Factor MO")
    with cs4: st.markdown(f"<p style='text-align:right; font-weight:700;'>${m_sup_u:,.2f}</p>", unsafe_allow_html=True)

    st.markdown(f"<p style='text-align:right; font-weight:800; color:#0F172A; font-size:14px;'>PRECIO UNITARIO MO + FACTORES: <b>${pu_mo_fac:,.2f}</b></p>", unsafe_allow_html=True)
    st.divider()

    # 5. COSTO BASE, INDIRECTOS Y UTILIDAD
    st.markdown(f"<p style='font-size:14px; font-weight:800; color:#334155;'>COSTO UNITARIO BASE: <b>${costo_base:,.2f}</b></p>", unsafe_allow_html=True)

    ci1, ci2, ci3 = st.columns([3, 2, 2])
    with ci1:
        tag = "🔴 (BAJA)" if baja_sel == "ind_campo" else ""
        st.markdown(f"Indirecto de campo ({p_ind_campo:.2f}%) {tag}")
    with ci2: st.caption("Compensador Target" if baja_sel == "ind_campo" else "Fijo")
    with ci3: st.markdown(f"<p style='text-align:right; font-weight:700;'>${m_ind_campo:,.2f}</p>", unsafe_allow_html=True)

    ci1, ci2, ci3 = st.columns([3, 2, 2])
    with ci1:
        tag = "🔴 (BAJA)" if baja_sel == "ind_central" else ""
        st.markdown(f"Indirecto Central ({p_ind_central:.2f}%) {tag}")
    with ci2: st.caption("Compensador Target" if baja_sel == "ind_central" else "Fijo")
    with ci3: st.markdown(f"<p style='text-align:right; font-weight:700;'>${m_ind_central:,.2f}</p>", unsafe_allow_html=True)

    ci1, ci2, ci3 = st.columns([3, 2, 2])
    with ci1:
        tag = "🔴 (BAJA)" if baja_sel == "utilidad" else ""
        st.markdown(f"Utilidad ({p_utilidad:.2f}%) {tag}")
    with ci2: st.caption("Compensador Target" if baja_sel == "utilidad" else "Fijo")
    with ci3: st.markdown(f"<p style='text-align:right; font-weight:700;'>${m_utilidad:,.2f}</p>", unsafe_allow_html=True)

    # PRECIO UNITARIO FINAL - VERDE RESALTADO
    st.markdown(f"""
    <div style="background:#10B981; color:#FFFFFF; padding:12px 16px; border-radius:6px; margin-top:14px;
                display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:15px; font-weight:900;">PRECIO UNITARIO FINAL (COINCIDENCIA 100% FIJA)</span>
        <span style="font-size:18px; font-weight:900;">${precio_final_sim:,.2f}</span>
    </div>
    <p style="text-align:right; font-size:11.5px; font-weight:700; color:#334155; font-style:italic; margin-top:6px;">
        {letras_sim}
    </p>
    """, unsafe_allow_html=True)

    if not is_read_only:
        st.markdown("---")
        if st.button("💾 GUARDAR AJUSTE TPU EN BASE DE DATOS Y RE-GENERAR PDF", type="primary", key=f"btn_save_unified_{pid}"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO cotizacion_tpu_custom
                (cotizacion_id, partida_id, herramienta_pct, supervision_pct, ind_campo_pct, ind_central_pct, utilidad_pct, horas_hh_factor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(partida_id) DO UPDATE SET
                    herramienta_pct = excluded.herramienta_pct,
                    supervision_pct = excluded.supervision_pct,
                    ind_campo_pct = excluded.ind_campo_pct,
                    ind_central_pct = excluded.ind_central_pct,
                    utilidad_pct = excluded.utilidad_pct,
                    horas_hh_factor = excluded.horas_hh_factor,
                    fecha_actualizacion = CURRENT_TIMESTAMP
            """, (
                cot_info['id'], pid,
                hta_val, sup_val,
                p_ind_campo, p_ind_central, p_utilidad,
                hh_val
            ))
            conn.commit()
            conn.close()

            try:
                from database.storage_manager import auto_sync_database_and_storage_to_github
                auto_sync_database_and_storage_to_github("Guardar ajuste unificado TPU partida #" + str(p_info['numero_partida']))
            except Exception:
                pass

            st.success("Ajuste unificado guardado exitosamente en la Base de Datos y sincronizado.")
            st.rerun()
