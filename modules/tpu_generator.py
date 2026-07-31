"""
Módulo de Tarjetas de Precios Unitarios (TPU) — J&D Automation Industries
Generación e inspección detallada de TPU por partida para propuestas técnicas y contratos.
Estructura ejecutiva fiel a los estándares oficiales de supervisión y precios unitarios con balanceador dinámico.
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
    Calcula matemáticamente todos los componentes de la Tarjeta de Precio Unitario (TPU)
    para una partida de proyecto garantizando el COINCIDENCIA 100% (MATCH)
    con el Precio de Venta de la tabla de costos principal de la cotización y leyendo
    ajustes personalizados desde la base de datos `cotizacion_tpu_custom`.
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

    # 2. MANO DE OBRA (Desglose Unitario con Costo H-H y Factor Personalizado)
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

        # Costo Hora-Hombre = (Sueldo * FASAR * SobreSueldo) / 48 hrs
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

    # 3. PORCENTAJES DE HERRAMIENTA Y SUPERVISIÓN SOBRE MANO DE OBRA
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

    # Subtotal Mano de Obra con Factores
    precio_unitario_mo_factor = costo_mo_unitario + monto_herramienta_unitario + monto_supervision_unitario

    # 4. SUBCONTRATOS, MAQUINARIA Y GASTOS (Asignados por unidad)
    total_sub = sum(float(s.get('importe_mxn', 0) or 0) for s in subcontratos) / cant_partida
    total_maq = sum(float(mq.get('total_mxn', 0) or 0) for mq in maquinaria) / cant_partida
    total_gas = gastos_partida / cant_partida

    # COSTO UNITARIO BASE
    costo_unitario_base = costo_mat_unitario + precio_unitario_mo_factor + total_sub + total_maq + total_gas

    # 5. GARANTIZAR MATCH CON EL PRECIO DE VENTA OFICIAL DE LA COTIZACIÓN
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

    # Revisar si existen porcentajes explícitos guardados en la BD
    if custom_tpu_dict.get('ind_campo_pct') is not None and custom_tpu_dict.get('ind_central_pct') is not None and custom_tpu_dict.get('utilidad_pct') is not None:
        ind_campo_pct = float(custom_tpu_dict['ind_campo_pct'])
        ind_central_pct = float(custom_tpu_dict['ind_central_pct'])
        utilidad_pct = float(custom_tpu_dict['utilidad_pct'])

        monto_ind_campo = costo_unitario_base * (ind_campo_pct / 100.0)
        monto_ind_central = costo_unitario_base * (ind_central_pct / 100.0)
        monto_utilidad = costo_unitario_base * (utilidad_pct / 100.0)
    else:
        monto_ind_campo = diferencia_indirectos * 0.20
        monto_ind_central = diferencia_indirectos * 0.40
        monto_utilidad = diferencia_indirectos * 0.40

        ind_campo_pct = (monto_ind_campo / costo_unitario_base * 100.0) if costo_unitario_base > 0 else 7.0
        ind_central_pct = (monto_ind_central / costo_unitario_base * 100.0) if costo_unitario_base > 0 else 14.0
        utilidad_pct = (monto_utilidad / costo_unitario_base * 100.0) if costo_unitario_base > 0 else 14.0

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

    return f"""<div style="background:#FFFFFF; border:1px solid #CBD5E1; border-radius:10px; padding:24px; font-family:'Montserrat', sans-serif; color:#0F172A; max-width:850px; margin:0 auto; box-shadow:0 6px 18px rgba(0,0,0,0.06);">
        <div style="border-bottom:2px solid #FE8C29; padding-bottom:12px; margin-bottom:16px;">
            <p style="margin:0; font-size:14px; font-weight:800; color:#FE8C29;">Partida {tpu_data['numero_partida']:04d}: {tpu_data['nombre_partida']}</p>
            <p style="margin:4px 0 0 0; font-size:12.5px; font-weight:700; color:#334155;">
                <b>Unidad:</b> {tpu_data['unidad']} &nbsp;|&nbsp; <b>Horas:</b> {tpu_data['horas_hh_unitarias']:.5f} hrs &nbsp;|&nbsp; <b>Alcance:</b> {tpu_data['descripcion']}
            </p>
        </div>

        <div style="margin-bottom:16px;">
            <table style="width:100%; border-collapse:collapse; font-size:12.5px;">
                <thead>
                    <tr style="background:#1E293B; color:#FFFFFF; text-align:left;">
                        <th style="padding:6px 8px;">Material</th>
                        <th style="padding:6px 8px; text-align:center;">Unidad</th>
                        <th style="padding:6px 8px; text-align:right;">Cantidad</th>
                        <th style="padding:6px 8px; text-align:right;">Costo</th>
                        <th style="padding:6px 8px; text-align:right;">Importe</th>
                    </tr>
                </thead>
                <tbody>
                    {mat_html_rows if mat_html_rows else '<tr><td colspan="5" style="padding:6px 8px; color:#94A3B8; font-style:italic;">Sin materiales directos asignados</td></tr>'}
                    <tr style="border-top:1px solid #CBD5E1; font-weight:800;">
                        <td colspan="4" style="padding:6px 8px; text-align:right;">Total</td>
                        <td style="padding:6px 8px; text-align:right; color:#0F172A;">${tpu_data['costo_mat_unitario']:,.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div style="margin-bottom:16px;">
            <table style="width:100%; border-collapse:collapse; font-size:12.5px;">
                <thead>
                    <tr style="background:#1E293B; color:#FFFFFF; text-align:left;">
                        <th style="padding:6px 8px;">Mano de Obra</th>
                        <th style="padding:6px 8px; text-align:center;">Cantidad</th>
                        <th style="padding:6px 8px; text-align:right;">Horas</th>
                        <th style="padding:6px 8px; text-align:right;">Costo HH</th>
                        <th style="padding:6px 8px; text-align:right;">Importe</th>
                    </tr>
                </thead>
                <tbody>
                    {mo_html_rows if mo_html_rows else '<tr><td colspan="5" style="padding:6px 8px; color:#94A3B8; font-style:italic;">Sin mano de obra directa asignada</td></tr>'}
                    <tr style="border-top:1px solid #CBD5E1; font-weight:800;">
                        <td colspan="4" style="padding:4px 8px; text-align:right;">Total</td>
                        <td style="padding:4px 8px; text-align:right; color:#0F172A;">${tpu_data['costo_mo_unitario']:,.2f}</td>
                    </tr>
                </tbody>
            </table>
            
            <table style="float:right; width:340px; border-collapse:collapse; font-size:12.5px; margin-top:8px;">
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Herramienta {tpu_data['hta_pct']:.2f}%</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_herramienta']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Supervisión {tpu_data['sup_pct']:.2f}%</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_supervision']:,.2f}</td>
                </tr>
                <tr style="border-top:1.5px solid #434E62; font-weight:800;">
                    <td style="padding:4px 8px; font-size:12px; text-transform:uppercase;">PRECIO UNITARIO</td>
                    <td style="padding:4px 8px; text-align:right; font-size:13.5px; color:#0F172A;">${tpu_data['precio_unitario_mo_factor']:,.2f}</td>
                </tr>
            </table>
            <div style="clear:both;"></div>
        </div>

        <div style="margin-top:16px; border-top:2px solid #E2E8F0; padding-top:12px;">
            <table style="float:right; width:420px; border-collapse:collapse; font-size:13px;">
                <tr>
                    <td style="padding:3px 8px; font-weight:800; color:#334155;">COSTO UNITARIO BASE</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:800; color:#334155;">${tpu_data['costo_unitario_base']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Indirecto de campo ({tpu_data['ind_campo_pct']:.2f}%)</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_ind_campo']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Indirecto Central ({tpu_data['ind_central_pct']:.2f}%)</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_ind_central']:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding:3px 8px; font-weight:600;">Utilidad ({tpu_data['utilidad_pct']:.2f}%)</td>
                    <td style="padding:3px 8px; text-align:right; font-weight:700;">${tpu_data['monto_utilidad']:,.2f}</td>
                </tr>
                <tr style="background:#10B981; color:#FFFFFF; font-weight:900; font-size:15px;">
                    <td style="padding:8px 12px; border-radius:4px 0 0 4px;">PRECIO UNITARIO FINAL</td>
                    <td style="padding:8px 12px; text-align:right; border-radius:0 4px 4px 0;">${tpu_data['precio_unitario_final']:,.2f}</td>
                </tr>
            </table>
            <div style="clear:both;"></div>
            <p style="margin:12px 0 0 0; text-align:right; font-size:11.5px; font-weight:700; color:#334155; font-style:italic;">
                {tpu_data['monto_letras']}
            </p>
        </div>
    </div>"""


def generate_tpu_pdf_oficial(cot_info, partidas):
    """
    Genera un PDF membretado oficial con la hoja membretada J&D (hoja_membretada.png)
    y colores institucionales, garantizando el MATCH del 100% con la tabla de cotización.
    """
    try:
        buffer = io.BytesIO()

        # Canvas con Hoja Membretada Oficial J&D
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

        # Encabezado Principal
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

            # Resumen Final TPU con MATCH exacto al PDF de la cotización
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
    Renderiza la interfaz interactiva de Tarjetas de Precios Unitarios (TPU) con balanceador dinámico.
    """
    st.markdown(f"""
    <div style="background:{BRAND_WHITE}; border:1px solid {BRAND_BORDER_LIGHT}; border-left:5px solid {BRAND_ORANGE};
                border-radius:8px; padding:16px 20px; margin-bottom:18px;">
        <h3 style="margin:0; color:{BRAND_CHARCOAL}; font-size:18px; font-weight:800;">🎴 DESGLOSE DE TARJETAS DE PRECIOS UNITARIOS (TPU)</h3>
        <p style="margin:4px 0 0 0; color:{BRAND_CHARCOAL_MED}; font-size:12px;">
            Inspección ejecutiva, balanceador dinámico de rendimientos e indirectos y resguardo oficial de Tarjetas TPU.
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

    # Botón de Descarga Oficial de TPU en PDF dentro del Módulo 6
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

    p_label = st.selectbox("🎯 Seleccionar Partida para Generar Tarjeta TPU", list(partida_opts.keys()))
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

        # ── INTERFAZ DEL BALANCEADOR DE TPU ──
        with st.expander("🎛️ Ajustar Porcentajes y Rendimientos TPU (Balanceador Dinámico)", expanded=True):
            st.markdown("""
            <p style="font-size:12.5px; color:#475569; margin-bottom:12px;">
                Modifica los porcentajes de <b>Herramienta</b>, <b>Supervisión</b> o <b>Factor H-H</b>. El <b>PRECIO UNITARIO FINAL</b> permanecerá <b>100% FIJO Y BLOQUEADO</b> ajustando automáticamente el rubro compensador seleccionado.
            </p>
            """, unsafe_allow_html=True)

            col_b1, col_b2, col_b3 = st.columns([1, 1, 1])
            with col_b1:
                input_sup = st.number_input("👷 Supervisión % (sobre MO)", value=float(tpu_data['sup_pct']), min_value=0.0, max_value=120.0, step=1.0, key=f"sup_{selected_p_id}")
                input_hta = st.number_input("🛠️ Herramienta % (sobre MO)", value=float(tpu_data['hta_pct']), min_value=0.0, max_value=30.0, step=0.5, key=f"hta_{selected_p_id}")

            with col_b2:
                input_hh_factor = st.number_input("⏱️ Multiplicador H-H (Rendimiento)", value=float(tpu_data['custom_tpu_dict'].get('horas_hh_factor', 1.0) or 1.0), min_value=0.2, max_value=5.0, step=0.05, key=f"hh_{selected_p_id}")
                target_comp = st.selectbox("⚖️ Rubro que absorbe el ajuste (Compensador)", [
                    "🏕️ Indirecto de Campo",
                    "🏢 Indirecto Central",
                    "💰 Utilidad",
                    "⚖️ Distribuir equitativamente (33% c/u)"
                ], key=f"target_{selected_p_id}")

            with col_b3:
                st.markdown("<p style='font-size:12px; font-weight:800; color:#334155;'>📌 PRECIO UNITARIO TARGET (BLOQUEADO):</p>", unsafe_allow_html=True)
                st.metric("PRECIO FINAL COTIZADO", f"${tpu_data['precio_unitario_target']:,.2f}")

            # Recálculo simulado en vivo
            temp_mo_unitario = tpu_data['costo_mo_unitario'] * input_hh_factor
            temp_hta_monto = temp_mo_unitario * (input_hta / 100.0)
            temp_sup_monto = temp_mo_unitario * (input_sup / 100.0)
            temp_mo_factor = temp_mo_unitario + temp_hta_monto + temp_sup_monto

            temp_costo_base = tpu_data['costo_mat_unitario'] + temp_mo_factor
            temp_dif = max(0.0, tpu_data['precio_unitario_target'] - temp_costo_base)

            if "Campo" in target_comp:
                sim_campo_monto = temp_dif
                sim_central_monto = 0.0
                sim_utilidad_monto = 0.0
            elif "Central" in target_comp:
                sim_campo_monto = 0.0
                sim_central_monto = temp_dif
                sim_utilidad_monto = 0.0
            elif "Utilidad" in target_comp:
                sim_campo_monto = 0.0
                sim_central_monto = 0.0
                sim_utilidad_monto = temp_dif
            else:
                sim_campo_monto = temp_dif * 0.20
                sim_central_monto = temp_dif * 0.40
                sim_utilidad_monto = temp_dif * 0.40

            sim_campo_pct = (sim_campo_monto / temp_costo_base * 100.0) if temp_costo_base > 0 else 0.0
            sim_central_pct = (sim_central_monto / temp_costo_base * 100.0) if temp_costo_base > 0 else 0.0
            sim_utilidad_pct = (sim_utilidad_monto / temp_costo_base * 100.0) if temp_costo_base > 0 else 0.0

            st.markdown("---")
            if st.button("💾 Guardar Ajuste Personalizado de TPU", type="primary", key=f"btn_save_tpu_{selected_p_id}"):
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
                    cot_id, selected_p_id,
                    input_hta, input_sup,
                    sim_campo_pct, sim_central_pct, sim_utilidad_pct,
                    input_hh_factor
                ))
                conn.commit()
                conn.close()

                try:
                    from database.storage_manager import auto_sync_database_and_storage_to_github
                    auto_sync_database_and_storage_to_github("Guardar ajuste personalizado TPU partida #" + str(p_info['numero_partida']))
                except Exception:
                    pass

                st.success("Ajuste personalizado guardado exitosamente en la Base de Datos.")
                st.rerun()

        st.markdown(render_tpu_card_html(tpu_data), unsafe_allow_html=True)
