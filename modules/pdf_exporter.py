"""
Generador Universal de Reportes PDF — J&D Automation Industries
Crea documentos PDF membretados con logo J&D para cualquier módulo o vista del sistema.
"""

import os
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

COLOR_PRIMARY = colors.HexColor("#FE8C29")      # Orange J&D
COLOR_SECONDARY = colors.HexColor("#434E62")    # Charcoal
COLOR_DARK_TEXT = colors.HexColor("#1E293B")
COLOR_MUTED = colors.HexColor("#64748B")
COLOR_LIGHT_BG = colors.HexColor("#F8FAFC")
COLOR_BORDER = colors.HexColor("#CBD5E1")

class JDBrandCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def _startPage(self):
        super()._startPage()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        membretada_path = os.path.join(base_dir, "assets", "hoja_membretada.png")
        if os.path.exists(membretada_path):
            try:
                self.saveState()
                self.drawImage(membretada_path, 0, 0, width=612, height=792)
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
            if self._pageNumber > 1:
                self.saveState()
                self.setFont("Helvetica-Bold", 8)
                self.setFillColor(colors.white)
                self.drawRightString(575, 20, f"Página {self._pageNumber} de {total_pages}")
                self.restoreState()
            super().showPage()
        super().save()


def generar_pdf_modulo(titulo_modulo, subtitulo, secciones, filename="Reporte_Oficial_JD.pdf"):
    """
    secciones: lista de diccionarios [{'title': '...', 'content': '...', 'items': [...]}]
    Retorna bytes del archivo PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=115,
        bottomMargin=80
    )

    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=COLOR_SECONDARY
    )
    style_subtitle = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=COLOR_PRIMARY
    )
    style_sec_title = ParagraphStyle(
        'SecTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=COLOR_SECONDARY,
        spaceBefore=10,
        spaceAfter=4
    )
    style_body = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=COLOR_DARK_TEXT,
        spaceAfter=6
    )

    story = []

    # Encabezado del Documento
    story.append(Paragraph(titulo_modulo.upper(), style_title))
    story.append(Paragraph(subtitulo, style_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY, spaceBefore=6, spaceAfter=15))

    for sec in secciones:
        if sec.get('title'):
            story.append(Paragraph(sec['title'].upper(), style_sec_title))
        if sec.get('content'):
            story.append(Paragraph(sec['content'], style_body))
        
        if sec.get('items'):
            for item in sec['items']:
                story.append(Paragraph(f"• <b>{item.get('label', '')}:</b> {item.get('val', '')}", style_body))
        
        if sec.get('table'):
            t_data = sec['table']
            # Formatear celdas con Paragraph
            formatted_data = []
            for row in t_data:
                formatted_row = [Paragraph(str(c), style_body) for c in row]
                formatted_data.append(formatted_row)
            
            t = Table(formatted_data, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECONDARY),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))

        story.append(Spacer(1, 6))

    doc.build(story, canvasmaker=JDBrandCanvas)
    buffer.seek(0)
    return buffer.getvalue()
