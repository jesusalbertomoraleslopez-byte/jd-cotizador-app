"""
Módulo de Plan de Proyecto — Sección de Planeación Inicial (Gantt & MS Project Export)
J&D Automation Industries

Diseñado como borrador inicial de planeación para cotizaciones y ofertas comerciales.
Genera diagramas de Gantt interactivos y exportación oficial a Microsoft Project (.xml / .csv) y cliente.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, date, timedelta
import io

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os

from database.models import get_connection, init_db
from database.db_manager import sync_cotizacion_totals
from config import (
    BRAND_ORANGE, BRAND_CHARCOAL, BRAND_CHARCOAL_MED,
    BRAND_WHITE, BRAND_BORDER_LIGHT, BRAND_GRAY_BG,
    BRAND_SUCCESS, BRAND_DANGER, get_brand_asset_path
)



# ─────────────────────────────────────────────────────────────────────────────
# MS PROJECT XML & CSV EXPORT GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def _generate_msproject_xml(proyecto_nombre, folio, fecha_inicio_base, tasks):
    """
    Genera un archivo XML de Intercambio de Datos de Microsoft Project (MSPDI v14/v16)
    Optimizado nativamente para Microsoft Project 2024 / 365.
    Se abre directamente al hacer doble clic sin asistentes de mapeo.
    """
    import uuid
    now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    start_dt = datetime.combine(fecha_inicio_base, datetime.min.time().replace(hour=8))

    # Calcular fecha fin global aproximada
    total_days = max(sum(int(t.get('dias_duracion') or 1) for t in tasks), 5)
    finish_dt = start_dt + timedelta(days=total_days)

    root = ET.Element("Project", xmlns="http://schemas.microsoft.com/project")

    # Identificadores nativos de versión de MS Project 2010/2016/2021/2024
    ET.SubElement(root, "SaveVersion").text = "14"  # MSPDI Version 14 (Nativo Project 2010 - 2024)
    ET.SubElement(root, "GUID").text = f"{{{str(uuid.uuid4()).upper()}}}"
    ET.SubElement(root, "Name").text = folio
    ET.SubElement(root, "Title").text = f"{folio} - {proyecto_nombre}"
    ET.SubElement(root, "Subject").text = "Plan de Proyecto Comercial"
    ET.SubElement(root, "Category").text = "Cotizaciones"
    ET.SubElement(root, "Company").text = "J&D Automation Industries"
    ET.SubElement(root, "CreationDate").text = now_iso
    ET.SubElement(root, "LastSaved").text = now_iso

    # Parámetros Globales de Agendamiento
    ET.SubElement(root, "ScheduleFromStart").text = "1"
    ET.SubElement(root, "StartDate").text = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
    ET.SubElement(root, "FinishDate").text = finish_dt.strftime("%Y-%m-%dT%H:%M:%S")
    ET.SubElement(root, "FYStartDate").text = "1"
    ET.SubElement(root, "CriticalSlackLimit").text = "0"
    ET.SubElement(root, "CurrencyDigits").text = "2"
    ET.SubElement(root, "CurrencySymbol").text = "$"
    ET.SubElement(root, "CurrencyCode").text = "MXN"

    # Parámetros del Calendario Base (Standard 8h/día, 40h/semana)
    ET.SubElement(root, "CalendarUID").text = "1"
    ET.SubElement(root, "DefaultStartTime").text = "08:00:00"
    ET.SubElement(root, "DefaultFinishTime").text = "17:00:00"
    ET.SubElement(root, "MinutesPerDay").text = "480"
    ET.SubElement(root, "HoursPerWeek").text = "40"
    ET.SubElement(root, "DaysPerMonth").text = "20"
    ET.SubElement(root, "DefaultTaskType").text = "0"  # Fixed Units
    ET.SubElement(root, "DefaultFixedCostAccrual").text = "3"
    ET.SubElement(root, "DefaultStandardRate").text = "0"
    ET.SubElement(root, "DefaultOvertimeRate").text = "0"

    # Definición de Calendario Estándar
    cals_elem = ET.SubElement(root, "Calendars")
    cal_elem = ET.SubElement(cals_elem, "Calendar")
    ET.SubElement(cal_elem, "UID").text = "1"
    ET.SubElement(cal_elem, "Name").text = "Estándar"
    ET.SubElement(cal_elem, "IsBaseCalendar").text = "1"
    ET.SubElement(cal_elem, "IsBaselineCalendar").text = "0"

    # Colección de Tareas
    tasks_elem = ET.SubElement(root, "Tasks")

    # Tarea 0 (Root Project Task en MS Project 2024)
    t0 = ET.SubElement(tasks_elem, "Task")
    ET.SubElement(t0, "UID").text = "0"
    ET.SubElement(t0, "ID").text = "0"
    ET.SubElement(t0, "Name").text = f"{folio} - {proyecto_nombre}"
    ET.SubElement(t0, "Type").text = "0"
    ET.SubElement(t0, "CreateDate").text = now_iso
    ET.SubElement(t0, "Start").text = start_dt.strftime("%Y-%m-%dT08:00:00")
    ET.SubElement(t0, "Finish").text = finish_dt.strftime("%Y-%m-%dT17:00:00")
    ET.SubElement(t0, "Duration").text = f"PT{total_days*8}H0M0S"
    ET.SubElement(t0, "DurationFormat").text = "7"
    ET.SubElement(t0, "Work").text = f"PT{total_days*8}H0M0S"
    ET.SubElement(t0, "Summary").text = "1"
    ET.SubElement(t0, "OutlineLevel").text = "0"

    # Mapeo de UIDs de Tareas
    uid_map = {}
    for idx, t in enumerate(tasks, 1):
        uid_map[t['id']] = idx

    for idx, t in enumerate(tasks, 1):
        task_node = ET.SubElement(tasks_elem, "Task")
        ET.SubElement(task_node, "UID").text = str(idx)
        ET.SubElement(task_node, "ID").text = str(idx)
        ET.SubElement(task_node, "Name").text = t['actividad']
        ET.SubElement(task_node, "Type").text = "0"
        ET.SubElement(task_node, "CreateDate").text = now_iso

        # Fechas
        t_start = t['fecha_inicio_dt']
        dias = max(int(t['dias_duracion'] or 1), 1)
        t_finish = t_start + timedelta(days=dias)

        ET.SubElement(task_node, "Start").text = t_start.strftime("%Y-%m-%dT08:00:00")
        ET.SubElement(task_node, "Finish").text = t_finish.strftime("%Y-%m-%dT17:00:00")

        # Duración en formato ISO 8601 PT{horas}H0M0S exigido por MS Project 2024
        horas = dias * 8
        ET.SubElement(task_node, "Duration").text = f"PT{horas}H0M0S"
        ET.SubElement(task_node, "DurationFormat").text = "7"  # 7 = Días
        ET.SubElement(task_node, "Work").text = f"PT{horas}H0M0S"

        # Atributos de Jerarquía Nativos MS Project 2024
        ET.SubElement(task_node, "OutlineLevel").text = "1"
        ET.SubElement(task_node, "OutlineNumber").text = str(idx)
        ET.SubElement(task_node, "WBS").text = f"1.{idx}"
        ET.SubElement(task_node, "Priority").text = "500"
        ET.SubElement(task_node, "Manual").text = "0"  # Auto-agendado automático
        ET.SubElement(task_node, "ConstraintType").text = "0"  # Tan pronto como sea posible (As Soon As Possible)

        if t.get('responsable'):
            ET.SubElement(task_node, "Contact").text = t['responsable']

        if t.get('tipo') == 'Hito':
            ET.SubElement(task_node, "Milestone").text = "1"
            ET.SubElement(task_node, "Duration").text = "PT0H0M0S"
        else:
            ET.SubElement(task_node, "Milestone").text = "0"

        # Enlace de Predecesora
        pred_id = t.get('predecesora_id')
        if pred_id and pred_id in uid_map:
            pred_link = ET.SubElement(task_node, "PredecessorLink")
            ET.SubElement(pred_link, "PredecessorUID").text = str(uid_map[pred_id])
            ET.SubElement(pred_link, "Type").text = "1"  # 1 = FS (Fin a Comienzo)
            ET.SubElement(pred_link, "CrossProject").text = "0"

    xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    return xml_str



def _generate_msproject_csv(proyecto_nombre, folio, fecha_inicio_base, tasks):
    """
    Genera un archivo CSV estructurado estándar listo para importar en MS Project o Excel.
    """
    rows = []
    uid_map = {t['id']: i for i, t in enumerate(tasks, 1)}

    for i, t in enumerate(tasks, 1):
        dias = max(int(t['dias_duracion'] or 1), 1)
        t_start = t['fecha_inicio_dt']
        t_finish = t_start + timedelta(days=dias)

        pred_str = ""
        if t.get('predecesora_id') and t['predecesora_id'] in uid_map:
            pred_str = str(uid_map[t['predecesora_id']])

        rows.append({
            "ID": i,
            "WBS": f"1.{i}",
            "Task_Name": t['actividad'],
            "Duration_Days": dias,
            "Start_Date": t_start.strftime("%Y-%m-%d"),
            "Finish_Date": t_finish.strftime("%Y-%m-%d"),
            "Predecessors": pred_str,
            "Resource_Names": t.get('responsable', ''),
            "Task_Type": t.get('tipo', 'Actividad'),
            "Partida": t.get('partida_desc', '')
        })

    df = pd.DataFrame(rows)
    return df.to_csv(index=False, encoding='utf-8-sig')


class JDLandscapeCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []
        # Dibujar fondo para la primera página inmediatamente en el constructor
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        membretada_path = os.path.join(base_dir, "assets", "hoja_membretada.png")
        if os.path.exists(membretada_path):
            try:
                self.saveState()
                self.drawImage(membretada_path, 0, 0, width=792, height=612)
                self.restoreState()
            except Exception:
                pass

    def _startPage(self):
        super()._startPage()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        membretada_path = os.path.join(base_dir, "assets", "hoja_membretada.png")
        if os.path.exists(membretada_path):
            try:
                self.saveState()
                self.drawImage(membretada_path, 0, 0, width=792, height=612)
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

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor('#434E62'))
        self.drawRightString(756, 18, f"Página {self._pageNumber} de {total_pages}")
        self.restoreState()


def _generate_plan_pdf(cot_info, fecha_inicio_base, tasks):

    """
    Genera un documento PDF corporativo ejecutivo con el Plan de Proyecto,
    Logo de J&D Automation Industries, tabla detallada de tiempos y entregables.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    font_bold, font_regular = "Helvetica-Bold", "Helvetica"
    try:
        from modules.cierre_entrega import _get_jd_fonts
        font_bold, font_regular = _get_jd_fonts()
    except Exception:
        pass

    style_title = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName=font_bold, fontSize=15, leading=18, textColor=colors.HexColor('#434E62')
    )
    style_sub = ParagraphStyle(
        'DocSub', parent=styles['Normal'],
        fontName=font_bold, fontSize=10, leading=13, textColor=colors.HexColor('#FE8C29')
    )
    style_body = ParagraphStyle(
        'DocBody', parent=styles['Normal'],
        fontName=font_regular, fontSize=9, leading=12, textColor=colors.HexColor('#334155')
    )
    style_body_bold = ParagraphStyle(
        'DocBodyBold', parent=styles['Normal'],
        fontName=font_bold, fontSize=9, leading=12, textColor=colors.HexColor('#434E62')
    )

    elements = []

    # Logo Corporativo de J&D
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, "assets", "logo_corporativo.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(base_dir, "assets", "logo_naranja.png")

    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=130, height=42)
            header_data = [[
                img,
                Paragraph("<b>J&D AUTOMATION INDUSTRIES</b><br/><font color='#FE8C29' size=9><b>PLAN DE PROYECTO & CRONOGRAMA PRELIMINAR DE TIEMPOS</b></font>", style_title)
            ]]
        except Exception:
            header_data = [[
                Paragraph("<b>J&D AUTOMATION INDUSTRIES</b>", style_title),
                Paragraph("<font color='#FE8C29' size=9><b>PLAN DE PROYECTO & CRONOGRAMA PRELIMINAR DE TIEMPOS</b></font>", style_sub)
            ]]
    else:
        header_data = [[
            Paragraph("<b>J&D AUTOMATION INDUSTRIES</b>", style_title),
            Paragraph("<font color='#FE8C29' size=9><b>PLAN DE PROYECTO & CRONOGRAMA PRELIMINAR DE TIEMPOS</b></font>", style_sub)
        ]]

    t_header = Table(header_data, colWidths=[150, 570])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 10))

    # Metadatos del Proyecto
    fol = cot_info.get('folio', 'COT-000')
    proy = cot_info.get('proyecto', 'PROYECTO')
    cli = cot_info.get('cliente', 'CLIENTE')
    ing = cot_info.get('ingeniero_id', 'DS')
    finicio_str = fecha_inicio_base.strftime("%Y-%m-%d")

    meta_data = [
        [Paragraph(f"<b>FOLIO:</b> {fol}", style_body), Paragraph(f"<b>CLIENTE:</b> {cli}", style_body)],
        [Paragraph(f"<b>PROYECTO:</b> {proy}", style_body), Paragraph(f"<b>ING. RESPONSABLE:</b> {ing}", style_body)],
        [Paragraph(f"<b>FECHA DE INICIO ESTIMADA:</b> {finicio_str}", style_body), Paragraph(f"<b>ESTATUS:</b> BORRADOR COMERCIAL DE TIEMPOS", style_body)]
    ]
    t_meta = Table(meta_data, colWidths=[360, 360])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 12))

    # Tabla de Tareas y Tiempos
    t_rows = [[
        Paragraph("<b>#</b>", style_body_bold),
        Paragraph("<b>ACTIVIDAD / ENTREGABLE</b>", style_body_bold),
        Paragraph("<b>TIPO</b>", style_body_bold),
        Paragraph("<b>INICIO</b>", style_body_bold),
        Paragraph("<b>DURACIÓN</b>", style_body_bold),
        Paragraph("<b>FIN ESTIMADO</b>", style_body_bold),
        Paragraph("<b>RESPONSABLE</b>", style_body_bold)
    ]]

    for i, t in enumerate(tasks, 1):
        dias = max(int(t.get('dias_duracion') or 1), 1)
        t_start = t['fecha_inicio_dt']
        t_finish = t_start + timedelta(days=dias)
        t_rows.append([
            Paragraph(str(i), style_body),
            Paragraph(t['actividad'], style_body),
            Paragraph(t.get('tipo', 'Actividad'), style_body),
            Paragraph(t_start.strftime("%Y-%m-%d"), style_body),
            Paragraph(f"{dias} días", style_body),
            Paragraph(t_finish.strftime("%Y-%m-%d"), style_body),
            Paragraph(str(t.get('responsable') or '—'), style_body)
        ])

    t_tasks = Table(t_rows, colWidths=[25, 265, 80, 80, 70, 80, 120])
    t_tasks.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#434E62')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F1F5F9')]),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_tasks)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("<font color='#64748B' size=8>Documento generado automáticamente por el Sistema de Cotizaciones J&D Automation Industries.</font>", style_body))

    doc.build(elements, canvasmaker=JDLandscapeCanvas)
    buffer.seek(0)
    return buffer.getvalue()




def _generate_ics_content(task, folio, proyecto):
    """
    Genera un archivo iCalendar (.ics - RFC 5545) en memoria para agendar un Hito.
    Utiliza formato UTC con 'Z' al final (YYYYMMDDTHHMMSSZ) para garantizar
    compatibilidad universal en Outlook, Google Calendar y Apple Calendar sin desfase horario.
    """
    import re
    task_name = task.get('actividad', 'Hito J&D')
    clean_name = re.sub(r'[^\w\s-]', '', task_name).strip().replace(' ', '_')
    filename = f"Hito_{clean_name[:25]}.ics"

    t_start = task['fecha_inicio_dt']
    dias = max(int(task.get('dias_duracion') or 1), 1)
    t_end = t_start + timedelta(days=dias)

    now_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dtstart_utc = t_start.strftime("%Y%m%dT080000Z")
    dtend_utc   = t_end.strftime("%Y%m%dT170000Z")
    task_uid    = f"hito-{task['id']}-{t_start.strftime('%Y%m%d')}@jdautomation.com.mx"

    ics_body = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//J&D Automation Industries//Cotizador v1.0//ES\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{task_uid}\r\n"
        f"DTSTAMP:{now_utc}\r\n"
        f"DTSTART:{dtstart_utc}\r\n"
        f"DTEND:{dtend_utc}\r\n"
        f"SUMMARY:Hito J&D: {task_name} ({folio})\r\n"
        f"DESCRIPTION:Hito oficial de entregable/pago para el proyecto {proyecto} ({folio}). Responsable: {task.get('responsable','—')}.\r\n"
        "LOCATION:Instalaciones Cliente / J&D Automation Industries\r\n"
        "STATUS:CONFIRMED\r\n"
        "PRIORITY:1\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    return filename, ics_body


def _generate_plan_eml(cot_info, fecha_inicio_base, tasks, pdf_bytes, xml_bytes):
    """
    Genera un archivo .eml (RFC 2045 Multipart/Mixed) listo para enviar por correo electrónico.
    Filtra dinámicamente las tareas de tipo 'Hito' y adjunta individualmente sus archivos .ics de calendario,
    además del reporte PDF oficial con el logo corporativo y el archivo de MS Project 2024.
    """
    msg = MIMEMultipart('mixed')
    folio = cot_info.get('folio', 'COT-000')
    proyecto = cot_info.get('proyecto', 'PROYECTO')
    cliente = cot_info.get('cliente', 'CLIENTE')
    contacto = cot_info.get('nombre_contacto', '')

    msg['Subject'] = f"J&D - Hitos de Planeación del Proyecto — {folio}"
    msg['From'] = "ventas@jdautomation.com.mx"
    if contacto:
        msg['To'] = f"{contacto} <contacto@cliente.com>"

    # 1. FILTRADO DE DATOS: Identificar tareas marcadas como Hito
    hitos_list = [t for t in tasks if t.get('tipo') == 'Hito']

    table_rows_html = ""
    for i, t in enumerate(tasks, 1):
        dias = max(int(t.get('dias_duracion') or 1), 1)
        t_start = t['fecha_inicio_dt']
        t_finish = t_start + timedelta(days=dias)
        is_hito = t.get('tipo') == 'Hito'
        badge_hito = "<b style='color:#DC2626;'>🚩 HITO DE PROYECTO</b>" if is_hito else t.get('tipo', 'Actividad')

        table_rows_html += f"""
        <tr style="background-color: {'#FFF7ED' if is_hito else ('#FFFFFF' if i%2!=0 else '#F8FAFC')};">
            <td style="padding: 8px; border: 1px solid #E2E8F0; font-weight: bold; text-align: center;">{i}</td>
            <td style="padding: 8px; border: 1px solid #E2E8F0; color: #434E62; font-weight: 600;">{t['actividad']}</td>
            <td style="padding: 8px; border: 1px solid #E2E8F0;">{badge_hito}</td>
            <td style="padding: 8px; border: 1px solid #E2E8F0;">{t_start.strftime('%Y-%m-%d')}</td>
            <td style="padding: 8px; border: 1px solid #E2E8F0;">{dias} días</td>
            <td style="padding: 8px; border: 1px solid #E2E8F0;">{t_finish.strftime('%Y-%m-%d')}</td>
            <td style="padding: 8px; border: 1px solid #E2E8F0; color: #64748B;">{t.get('responsable', '—')}</td>
        </tr>
        """

    hitos_html_list = ""
    if hitos_list:
        hitos_html_list = "<ul>" + "".join([f"<li><b>{h['actividad']}</b> — Fecha: {h['fecha_inicio_dt'].strftime('%Y-%m-%d')} (Adjunto <code>Hito_{h['id']}.ics</code>)</li>" for h in hitos_list]) + "</ul>"
    else:
        hitos_html_list = "<p style='font-size:12px;color:#64748B;'><i>No hay hitos específicos filtrados. Se incluyen los adjuntos generales del proyecto.</i></p>"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #334155; margin: 0; padding: 0; background-color: #F1F5F9; }}
            .container {{ max-width: 720px; margin: 20px auto; background: #FFFFFF; border-radius: 12px; overflow: hidden; border: 1px solid #E2E8F0; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
            .header {{ background-color: #434E62; padding: 24px; text-align: left; border-bottom: 5px solid #FE8C29; }}
            .header h1 {{ color: #FFFFFF; margin: 0; font-size: 22px; font-weight: 800; }}
            .header p {{ color: #FE8C29; margin: 4px 0 0 0; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }}
            .content {{ padding: 28px; }}
            .meta-box {{ background-color: #F8FAFC; border-left: 4px solid #FE8C29; padding: 14px 18px; margin: 18px 0; border-radius: 4px; }}
            .meta-box td {{ padding: 4px 10px; font-size: 13px; }}
            .table-gantt {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 12px; }}
            .table-gantt th {{ background-color: #434E62; color: #FFFFFF; padding: 10px; text-align: left; font-size: 11px; text-transform: uppercase; }}
            .footer {{ background-color: #F8FAFC; padding: 16px 28px; font-size: 11px; color: #94A3B8; text-align: center; border-top: 1px solid #E2E8F0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>J&D AUTOMATION INDUSTRIES</h1>
                <p>Plan de Proyecto & Cronograma de Tiempos</p>
            </div>
            <div class="content">
                <p style="font-size: 15px; color: #434E62;"><b>Estimado(a) {contacto or 'Cliente'},</b></p>
                <p style="font-size: 13px; line-height: 1.5; color: #475569;">
                    Le enviamos la propuesta oficial de <b>Plan de Proyecto y Cronograma de Ejecución</b> para <b>{proyecto}</b>.
                </p>

                <div class="meta-box">
                    <table>
                        <tr><td><b>Folio de Cotización:</b></td><td style="color:#FE8C29; font-weight:bold;">{folio}</td></tr>
                        <tr><td><b>Cliente:</b></td><td>{cliente}</td></tr>
                        <tr><td><b>Proyecto:</b></td><td>{proyecto}</td></tr>
                        <tr><td><b>Fecha Estimada de Inicio:</b></td><td>{fecha_inicio_base.strftime('%Y-%m-%d')}</td></tr>
                    </table>
                </div>

                <h3 style="color: #434E62; font-size: 14px; margin-top: 22px;">🚩 Hitos Clave del Proyecto (Agendables automáticamente en tu Calendario)</h3>
                {hitos_html_list}

                <h3 style="color: #434E62; font-size: 14px; margin-top: 22px;">📋 Desglose General de Actividades y Tiempos</h3>
                <table class="table-gantt">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Actividad / Entregable</th>
                            <th>Tipo</th>
                            <th>Inicio</th>
                            <th>Duración</th>
                            <th>Fin</th>
                            <th>Responsable</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>

                <p style="font-size: 12px; color: #64748B; margin-top: 24px; background: #FFF7ED; padding: 12px; border-radius: 6px; border: 1px solid #FFEDD5;">
                    📎 <b>Archivos Adjuntos Incluidos en este Mensaje:</b><br>
                    • <b>Archivos de Hitos (.ics)</b>: Haz doble clic sobre cada hito para agregarlo directamente a tu Outlook o Google Calendar.<br>
                    • <b>{folio}_Plan_de_Proyecto.pdf</b>: Documento PDF oficial impreso con el logo corporativo J&D.<br>
                    • <b>{folio}_MSProject2024.xml</b>: Archivo nativo para abrir en Microsoft Project 2024.
                </p>
            </div>
            <div class="footer">
                J&D Automation Industries S.A. de C.V. &bull; Área de Cotizaciones e Ingeniería Comercial
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    # 2. ADJUNTAR ARCHIVOS .ICS INDEPENDIENTES PARA CADA HITO (ESTRATEGIA B)
    for hito in hitos_list:
        fname_ics, body_ics = _generate_ics_content(hito, folio, proyecto)
        part_ics = MIMEApplication(body_ics.encode('utf-8'), _subtype="calendar; method=PUBLISH")
        part_ics.add_header("Content-Type", "text/calendar", name=fname_ics, method="PUBLISH")
        part_ics.add_header("Content-Disposition", "attachment", filename=fname_ics)
        msg.attach(part_ics)

    # 3. ADJUNTAR PDF EJECUTIVO CON LOGO
    part_pdf = MIMEApplication(pdf_bytes, Name=f"{folio}_Plan_de_Proyecto.pdf")
    part_pdf.add_header("Content-Disposition", "attachment", filename=f"{folio}_Plan_de_Proyecto.pdf")
    msg.attach(part_pdf)

    # 4. ADJUNTAR MS PROJECT 2024 XML
    xml_data = xml_bytes.encode('utf-8') if isinstance(xml_bytes, str) else xml_bytes
    part_xml = MIMEApplication(xml_data, Name=f"{folio}_MSProject2024.xml")
    part_xml.add_header("Content-Disposition", "attachment", filename=f"{folio}_MSProject2024.xml")
    msg.attach(part_xml)

    return msg.as_bytes()




# ─────────────────────────────────────────────────────────────────────────────
# MÓDULO RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def render_plan_proyecto():
    init_db()

    # Cargar cotizaciones disponibles
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.folio, c.proyecto, c.congelada, COALESCE(c.revision,'R0') as revision, COALESCE(cl.nombre,'—') as cliente
        FROM cotizaciones c LEFT JOIN clientes cl ON c.cliente_id = cl.id
        ORDER BY c.id DESC
    """)
    cots = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not cots:
        st.warning("⚠️ No hay cotizaciones registradas para generar el Plan de Proyecto.")
        return

    cot_labels = {f"{'🔒 ' if c['congelada'] else '✏️ '}{c['folio']} ({c['revision']}) — {c['cliente']} | {c['proyecto'][:40]}": c['id'] for c in cots}
    sel_label = st.selectbox("📌 Selecciona la Cotización para la Planeación Inicial", list(cot_labels.keys()), key="plan_cot_sel")
    cot_id = cot_labels[sel_label]


    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT * FROM cotizaciones WHERE id=?", (cot_id,))
    cot_info = dict(cur.fetchone())
    cur.execute("SELECT * FROM cotizacion_partidas WHERE cotizacion_id=? ORDER BY numero_partida", (cot_id,))
    partidas = [dict(r) for r in cur.fetchall()]
    conn.close()

    st.markdown(f"""
    <div style="background:{BRAND_CHARCOAL};color:#fff;border-radius:10px;padding:14px 22px;
                border-left:6px solid {BRAND_ORANGE};margin:10px 0 16px 0;
                font-family:'Montserrat',sans-serif;">
        <span style="font-size:10px;font-weight:800;text-transform:uppercase;color:{BRAND_ORANGE};letter-spacing:1px;">
            PLANEACIÓN INICIAL DEL PROYECTO
        </span><br>
        <span style="font-size:22px;font-weight:900;">{cot_info['folio']}</span>
        <span style="font-size:13px;color:#CBD5E1;margin-left:12px;">{cot_info['proyecto']}</span>
    </div>
    """, unsafe_allow_html=True)

    # Pestañas del flujo UX en 3 Pasos
    tab1, tab2, tab3 = st.tabs([
        "1. Parámetros Iniciales",
        "2. Editor de Gantt (Borrador Rápido)",
        "3. Exportar MS Project & Cliente"
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 1: PARÁMETROS DEL PROYECTO
    # ─────────────────────────────────────────────────────────────────────────
    with tab1:
        st.markdown(f"""
        <div class="jd-section-header">
            <h2>Paso 1 — Parámetros de Inicio del Proyecto</h2>
            <p>Establece la fecha tentativa de inicio y genera las tareas base automáticas a partir de las partidas de la cotización.</p>
        </div>""", unsafe_allow_html=True)

        cp1, cp2, cp3 = st.columns([2, 2, 2.5])
        with cp1:
            fecha_inicio_base = st.date_input("Fecha Global de Inicio Estimada", value=date.today(), key="plan_f_ini")
        with cp2:
            jornada = st.selectbox("Jornada de Trabajo", ["Días Hábiles (Lunes a Viernes)", "Días Naturales (Lunes a Domingo)"], key="plan_jornada")
        with cp3:
            st.write(" ")
            st.write(" ")
            if st.button("⚡ Autogenerar Tareas desde Partidas", type="primary", use_container_width=True):
                if partidas:
                    conn = get_connection()
                    for idx, p in enumerate(partidas, 1):
                        act_nom = f"Ejecución de Partida {p['numero_partida']}: {p['descripcion']}"
                        conn.execute("""INSERT INTO cotizacion_gantt
                                        (cotizacion_id,partida_id,actividad,tipo,responsable,fecha_inicio,dias_duracion,orden)
                                        VALUES(?,?,?,?,?,?,?,?)""",
                                     (cot_id, p['id'], act_nom, 'Actividad',
                                      cot_info.get('ingeniero_id','DS'), str(fecha_inicio_base), 5, idx))
                    conn.commit(); conn.close()
                    st.success("✅ Tareas base autogeneradas para cada partida.")
                    st.rerun()
                else:
                    st.warning("La cotización no tiene partidas registradas.")

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 2: EDITOR DE GANTT (BORRADOR RÁPIDO)
    # ─────────────────────────────────────────────────────────────────────────
    with tab2:
        st.markdown(f"""
        <div class="jd-section-header">
            <h2>Paso 2 — Editor Rápido del Diagrama de Gantt</h2>
            <p>Agrega o modifica actividades, duraciones y predecesoras. Los datos se actualizan en tiempo real.</p>
        </div>""", unsafe_allow_html=True)

        # Cargar tareas existentes
        conn = get_connection(); cur = conn.cursor()
        cur.execute("""SELECT g.*, p.numero_partida, p.descripcion as partida_desc
                       FROM cotizacion_gantt g
                       LEFT JOIN cotizacion_partidas p ON g.partida_id=p.id
                       WHERE g.cotizacion_id=? ORDER BY g.orden, g.id""", (cot_id,))
        gantt_raw = [dict(r) for r in cur.fetchall()]; conn.close()

        # Formulario rápido para nueva tarea
        with st.expander("➕ Agregar Nueva Tarea / Hito al Plan", expanded=not bool(gantt_raw)):
            part_opts = {f"P{p['numero_partida']} — {p['descripcion'][:35]}": p['id'] for p in partidas}
            part_opts["— Tarea General del Proyecto —"] = None
            
            # Opciones de predecesora
            pred_opts = {"— Ninguna —": None}
            for idx_p, t_p in enumerate(gantt_raw, 1):
                pred_opts[f"Tarea {idx_p}: {t_p['actividad'][:30]}..."] = t_p['id']

            with st.form("form_plan_add_task", clear_on_submit=True):
                r1a, r1b = st.columns([4, 2])
                with r1a: nom_task = st.text_input("Nombre de la Tarea / Entregable *", placeholder="Ej: Levantamiento topográfico y firma de sitio")
                with r1b: part_task = st.selectbox("Partida Asociada", list(part_opts.keys()))

                r2a, r2b, r2c, r2d, r2e = st.columns([1.5, 1.2, 1.5, 1.5, 1.5])
                with r2a: f_ini_task = st.date_input("Fecha Inicio", value=fecha_inicio_base)
                with r2b: dur_task   = st.number_input("Duración (Días)", value=5, min_value=1, step=1)
                with r2c: tipo_task  = st.selectbox("Tipo de Tarea", ["Actividad", "Entregable", "Hito", "Reunión"])
                with r2d: resp_task  = st.text_input("Responsable / Rol", value=cot_info.get('ingeniero_id','DS'))
                with r2e: pred_task  = st.selectbox("Predecesora", list(pred_opts.keys()))

                if st.form_submit_button("➕ Agregar Tarea", type="primary"):
                    if nom_task.strip():
                        conn = get_connection()
                        conn.execute("""INSERT INTO cotizacion_gantt
                                        (cotizacion_id,partida_id,actividad,tipo,responsable,
                                         fecha_inicio,dias_duracion,orden,predecesora_id)
                                        VALUES(?,?,?,?,?,?,?,?,?)""",
                                     (cot_id, part_opts[part_task], nom_task.strip(), tipo_task,
                                      resp_task, str(f_ini_task), dur_task, len(gantt_raw)+1, pred_opts[pred_task]))
                        conn.commit(); conn.close()
                        st.success("Tarea agregada."); st.rerun()
                    else:
                        st.error("El nombre de la tarea es obligatorio.")

        # Construir y procesar tareas para la vista de Gantt
        tasks_processed = []
        for row in gantt_raw:
            try: fi = datetime.strptime(str(row['fecha_inicio']), "%Y-%m-%d").date()
            except: fi = fecha_inicio_base
            dt_start = datetime.combine(fi, datetime.min.time().replace(hour=8))
            tasks_processed.append({
                "id": row['id'],
                "actividad": row['actividad'],
                "tipo": row.get('tipo', 'Actividad'),
                "responsable": row.get('responsable', '—'),
                "fecha_inicio_dt": dt_start,
                "fecha_inicio_str": fi.strftime("%Y-%m-%d"),
                "dias_duracion": int(row['dias_duracion'] or 1),
                "partida_id": row.get('partida_id'),
                "partida_desc": row.get('partida_desc', 'General'),
                "predecesora_id": row.get('predecesora_id')
            })

        if tasks_processed:
            st.markdown("<br>", unsafe_allow_html=True)

            # Render de la Gráfica de Gantt Plotly
            gantt_plot_data = []
            for t in tasks_processed:
                ff = t['fecha_inicio_dt'] + timedelta(days=t['dias_duracion'])
                gantt_plot_data.append({
                    "Tarea": t['actividad'],
                    "Inicio": t['fecha_inicio_dt'],
                    "Fin": ff,
                    "Tipo": t['tipo'],
                    "Responsable": t['responsable'],
                    "Partida": t['partida_desc']
                })

            df_gantt = pd.DataFrame(gantt_plot_data)
            tipo_colors = {"Actividad": BRAND_ORANGE, "Entregable": "#059669", "Hito": "#DC2626", "Reunión": "#0EA5E9"}
            fig_g = px.timeline(df_gantt, x_start="Inicio", x_end="Fin", y="Tarea", color="Tipo",
                                color_discrete_map=tipo_colors, hover_data=["Partida", "Responsable"])
            fig_g.update_yaxes(categoryorder="array", categoryarray=df_gantt["Tarea"].unique())
            fig_g.update_yaxes(autorange="reversed")
            fig_g.update_layout(height=max(280, 50 + len(gantt_plot_data)*35),
                                margin=dict(t=10, b=20, l=10, r=10),
                                font_family="Montserrat",
                                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')

            st.plotly_chart(fig_g, use_container_width=True)

            # Tabla de Tareas con botón para borrar e información de predecesoras
            st.divider()
            st.markdown("**Tabla Detallada de Tareas**")
            cw = [0.5, 3.2, 1.2, 1.2, 1.2, 1.5, 1.5, 0.5]
            ch = ["#", "Tarea / Entregable", "Tipo", "Inicio", "Duración", "Predecesora", "Responsable", "✕"]
            cols_h = st.columns(cw)
            for col, lbl in zip(cols_h, ch):
                col.markdown(f"<p style='font-size:10px;font-weight:800;text-transform:uppercase;color:{BRAND_CHARCOAL_MED};margin:2px 0;'>{lbl}</p>", unsafe_allow_html=True)

            for i, t in enumerate(tasks_processed, 1):
                rc = st.columns(cw)
                rc[0].markdown(f"<p style='font-size:12px;font-weight:700;color:{BRAND_CHARCOAL_MED};margin:3px 0;'>{i}</p>", unsafe_allow_html=True)
                rc[1].markdown(f"<p style='font-size:13px;font-weight:700;color:{BRAND_CHARCOAL};margin:3px 0;'>{t['actividad']}</p>", unsafe_allow_html=True)
                rc[2].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:3px 0;'>{t['tipo']}</p>", unsafe_allow_html=True)
                rc[3].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:3px 0;'>{t['fecha_inicio_str']}</p>", unsafe_allow_html=True)
                rc[4].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:3px 0;'>{t['dias_duracion']} días</p>", unsafe_allow_html=True)
                
                # Encontrar el índice de la predecesora para mostrarlo de forma comprensible
                pred_label = "—"
                if t.get('predecesora_id'):
                    for idx_p, tp in enumerate(tasks_processed, 1):
                        if tp['id'] == t['predecesora_id']:
                            pred_label = f"Tarea {idx_p}"
                            break
                            
                rc[5].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL};margin:3px 0;'>{pred_label}</p>", unsafe_allow_html=True)
                rc[6].markdown(f"<p style='font-size:12px;color:{BRAND_CHARCOAL_MED};margin:3px 0;'>{t['responsable']}</p>", unsafe_allow_html=True)
                if rc[7].button("✕", key=f"del_ptask_{t['id']}"):
                    conn = get_connection()
                    conn.execute("DELETE FROM cotizacion_gantt WHERE id=?", (t['id'],))
                    conn.commit(); conn.close(); st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # PASO 3: EXPORTACIÓN A MS PROJECT & CLIENTE
    # ─────────────────────────────────────────────────────────────────────────
    with tab3:
        st.markdown(f"""
        <div class="jd-section-header">
            <h2>Paso 3 — Exportación e Integración Externa</h2>
            <p>Descarga el Plan de Proyecto en archivos compatibles con <b>Microsoft Project (.xml / .csv)</b> o en reporte ejecutable.</p>
        </div>""", unsafe_allow_html=True)

        if not tasks_processed:
            st.info("Primero debes agregar o generar tareas en el **Paso 2** para habilitar las descargas.")
            return

        # Generar XML de MS Project, PDF y EML
        xml_content = _generate_msproject_xml(cot_info['proyecto'], cot_info['folio'], fecha_inicio_base, tasks_processed)
        csv_content = _generate_msproject_csv(cot_info['proyecto'], cot_info['folio'], fecha_inicio_base, tasks_processed)
        pdf_content = _generate_plan_pdf(cot_info, fecha_inicio_base, tasks_processed)
        eml_content = _generate_plan_eml(cot_info, fecha_inicio_base, tasks_processed, pdf_content, xml_content)

        # ── SECCIÓN 1: ENVÍO POR CORREO ELECTRÓNICO (.EML) Y REPORTE PDF ──
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-left:6px solid {BRAND_ORANGE};
                    border-radius:10px;padding:18px 22px;margin-bottom:20px;font-family:'Montserrat',sans-serif;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <span style="font-size:22px;">✉️</span>
                <span style="font-size:16px;font-weight:800;color:{BRAND_CHARCOAL};">ENVÍO POR CORREO Y REPORTE EJECUTIVO PDF</span>
            </div>
            <p style="font-size:12px;color:{BRAND_CHARCOAL_MED};margin:0;line-height:1.5;">
                Descarga el borrador del correo <b>.EML</b> (abre directamente en Outlook / Mail). Contiene el texto corporativo 
                con el logo de <b>J&D Automation Industries</b>, la tabla de tiempos y trae <b>adjuntos automáticamente</b> 
                el reporte <b>PDF oficial</b> y el archivo <b>.XML de MS Project 2024</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)

        e_col1, e_col2 = st.columns(2)
        with e_col1:
            st.download_button(
                label="✉️ GENERAR Y DESCARGAR CORREO (.EML CON ADJUNTOS)",
                data=eml_content,
                file_name=f"{cot_info['folio']}_CorreoPlanProyecto.eml",
                mime="message/rfc822",
                type="primary",
                use_container_width=True
            )

        with e_col2:
            st.download_button(
                label="📄 DESCARGAR PDF EJECUTIVO CON LOGO J&D (.pdf)",
                data=pdf_content,
                file_name=f"{cot_info['folio']}_PlanDeProyecto.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        st.divider()

        # ── SECCIÓN 2: MICROSOFT PROJECT 2024 ──
        st.markdown(f"""
        <div style="background:{BRAND_GRAY_BG};border:2px solid {BRAND_ORANGE};border-radius:12px;
                    padding:22px;margin:10px 0 20px 0;font-family:'Montserrat',sans-serif;box-shadow:0 4px 12px rgba(254,140,41,0.12);">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
                <span style="font-size:24px;">📊</span>
                <span style="font-size:18px;font-weight:900;color:{BRAND_CHARCOAL};">INTEGRACIÓN NATIVA MS PROJECT 2024</span>
            </div>
            <p style="font-size:13px;color:{BRAND_CHARCOAL_MED};margin:0 0 16px 0;line-height:1.5;">
                Genera el archivo nativo <b>MSPDI v14/v16 (.xml)</b> con esquema <code>http://schemas.microsoft.com/project</code>. 
                Al hacer <b>doble clic</b> sobre el archivo descargado, <b>Microsoft Project 2024 lo abre automáticamente</b> sin mostrar asistentes.
            </p>
        </div>
        """, unsafe_allow_html=True)

        ex1, ex2 = st.columns([1.2, 1])
        with ex1:
            st.download_button(
                label="⚡ GENERAR ARCHIVO NATIVO MS PROJECT 2024 (.xml)",
                data=xml_content,
                file_name=f"{cot_info['folio']}_MSProject2024.xml",
                mime="application/vnd.ms-project",
                type="primary",
                use_container_width=True
            )

        with ex2:
            st.download_button(
                label="📄 DESCARGAR FORMATO CSV EXCEL / PROJECT (.csv)",
                data=csv_content,
                file_name=f"{cot_info['folio']}_Gantt.csv",
                mime="text/csv",
                use_container_width=True
            )

        # Vista de Gantt Interactiva con los datos reales del programa
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📊 Cronograma Real del Proyecto en este Programa")
        st.markdown(
            "Esta es la representación visual en tiempo real de tus tareas y duraciones cargadas en la cotización. "
            "Al descargar el archivo **.xml** e importarlo en **Microsoft Project**, verás exactamente esta estructura:"
        )

        total_tasks = len(tasks_processed)
        if total_tasks > 0:
            min_date = min(t['fecha_inicio_dt'].date() for t in tasks_processed)
            max_date = max((t['fecha_inicio_dt'].date() + timedelta(days=t['dias_duracion'])) for t in tasks_processed)
            project_days = (max_date - min_date).days
            if project_days == 0:
                project_days = 1

            html_gantt = f"<div style=\"font-family:'Montserrat',sans-serif; background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:16px; box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);\">"
            html_gantt += f"<div style=\"display:flex; border-bottom:2px solid #CBD5E1; padding-bottom:8px; font-weight:800; font-size:11px; color:#434E62;\">"
            html_gantt += f"<div style=\"width:35%; text-align:left;\">ACTIVIDAD / ENTREGABLE</div>"
            html_gantt += f"<div style=\"width:15%; text-align:center;\">DURACIÓN</div>"
            html_gantt += f"<div style=\"width:50%; text-align:center; position:relative;\">CRONOGRAMA (DEL {min_date.strftime('%d/%m/%Y')} AL {max_date.strftime('%d/%m/%Y')})</div>"
            html_gantt += "</div>"

            for t in tasks_processed:
                task_start = t['fecha_inicio_dt'].date()
                task_dur = t['dias_duracion']
                offset_days = (task_start - min_date).days
                
                left_pct = (offset_days / project_days) * 100
                width_pct = (task_dur / project_days) * 100
                
                color_map = {"Actividad": BRAND_ORANGE, "Entregable": "#10B981", "Hito": "#EF4444", "Reunión": "#3B82F6"}
                bar_color = color_map.get(t['tipo'], "#434E62")
                
                html_gantt += f"<div style=\"display:flex; align-items:center; border-bottom:1px solid #F1F5F9; padding:8px 0; font-size:12px;\">"
                html_gantt += f"<div style=\"width:35%; font-weight:700; color:#2C3442; padding-right:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;\">{t['actividad']}</div>"
                html_gantt += f"<div style=\"width:15%; text-align:center; color:#64748B; font-weight:600;\">{task_dur} días</div>"
                html_gantt += f"<div style=\"width:50%; position:relative; height:18px; background:#F1F5F9; border-radius:4px;\">"
                html_gantt += f"<div style=\"position:absolute; left:{left_pct}%; width:{width_pct}%; height:100%; background:{bar_color}; border-radius:4px; opacity:0.9; display:flex; align-items:center; justify-content:center;\">"
                html_gantt += f"<span style=\"font-size:8px; color:#FFFFFF; font-weight:bold; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; padding:0 3px;\">{t['responsable']}</span>"
                html_gantt += "</div></div></div>"
                
            html_gantt += "</div>"
            st.markdown(html_gantt, unsafe_allow_html=True)



