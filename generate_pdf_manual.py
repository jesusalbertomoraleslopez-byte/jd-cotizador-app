import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# ─── PALETA CORPORATIVA J&D AUTOMATION ───
COLOR_PRIMARY = colors.HexColor("#FE8C29")      # Orange J&D
COLOR_SECONDARY = colors.HexColor("#434E62")    # Charcoal Dark
COLOR_DARK_TEXT = colors.HexColor("#1E293B")    # Slate 800
COLOR_MUTED = colors.HexColor("#64748B")        # Slate 500
COLOR_LIGHT_BG = colors.HexColor("#F8FAFC")     # Slate 50
COLOR_CALLOUT_BG = colors.HexColor("#FFF7ED")   # Orange Light BG
COLOR_CALLOUT_BORDER = colors.HexColor("#F97316") # Orange Border
COLOR_TABLE_HEADER = colors.HexColor("#434E62") # Charcoal Table Header
COLOR_ALT_ROW = colors.HexColor("#F1F5F9")      # Light Row Alternating

class JDManualCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def _startPage(self):
        super()._startPage()
        # Fondo Membretado Oficial J&D (Se dibuja AL INICIO de la página, por debajo de todo el texto)
        base_dir = os.path.dirname(os.path.abspath(__file__))
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
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages):
        self.saveState()
        # Omite número de página en la Portada (Página 1)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.white)
            # Dibuja la numeración limpiamente sobre la barra naranja inferior de la hoja membretada
            self.drawRightString(575, 20, f"Página {self._pageNumber} de {total_pages}")
        self.restoreState()


def crear_manual_pdf(filename="Manual_Usuario_Plantilla_Excel_JD.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=115,  # Evita empalme con el logotipo superior de la hoja membretada
        bottomMargin=80   # Evita empalme con la barra naranja inferior
    )

    styles = getSampleStyleSheet()
    
    # ── ESTILOS PERSONALIZADOS ──
    style_cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=COLOR_SECONDARY,
        alignment=0, # Left
        spaceAfter=12
    )
    
    style_cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=COLOR_PRIMARY,
        alignment=0,
        spaceAfter=20
    )
    
    style_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=COLOR_SECONDARY,
        spaceBefore=16,
        spaceAfter=10,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=COLOR_PRIMARY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=COLOR_DARK_TEXT,
        spaceAfter=8
    )

    style_bullet = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=COLOR_DARK_TEXT,
        leftIndent=15,
        spaceAfter=4
    )

    style_callout = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=COLOR_DARK_TEXT
    )

    style_tbl_hdr = ParagraphStyle(
        'TblHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white,
        alignment=1 # Center
    )

    style_tbl_cell = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=COLOR_DARK_TEXT
    )

    style_tbl_cell_bold = ParagraphStyle(
        'TblCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=COLOR_SECONDARY
    )

    story = []

    # ─────────────────────────────────────────────────────────────────────────
    # PÁGINA 1: PORTADA EJECUTIVA DEDICADA
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10))

    # Logo Corporativo J&D en la Portada
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "assets", "logo_corporativo.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(base_dir, "assets", "logo_naranja.png")

    if os.path.exists(logo_path):
        try:
            img_logo = Image(logo_path, width=170, height=52)
            story.append(img_logo)
            story.append(Spacer(1, 15))
        except Exception:
            pass

    story.append(Paragraph("MANUAL DE USUARIO Y GUÍA DE CAPTURA<br/>PLANTILLA EXCEL DE COTIZACIÓN V2.0", style_cover_title))
    story.append(Paragraph("Estandarización paso a paso para Presupuestadores y Gestión Comercial de Ventas", style_cover_subtitle))
    
    story.append(HRFlowable(width="100%", thickness=2.5, color=COLOR_PRIMARY, spaceBefore=0, spaceAfter=18))
    
    # Cuadro resumen ejecutivo en la portada
    info_data = [
        [Paragraph("<b>Documento:</b>", style_tbl_cell_bold), Paragraph("Manual de Operación y Llenado de Plantilla Excel", style_tbl_cell)],
        [Paragraph("<b>Versión Sistema:</b>", style_tbl_cell_bold), Paragraph("v2.0 (Edición Robustecida con BD Dinámica)", style_tbl_cell)],
        [Paragraph("<b>Dirigido a:</b>", style_tbl_cell_bold), Paragraph("Ingenieros Presupuestadores, Auxiliares de Cotizaciones y Agentes de Ventas", style_tbl_cell)],
        [Paragraph("<b>Estructura Libro:</b>", style_tbl_cell_bold), Paragraph("9 Hojas (PROY, WBS, MAT, MO, GAS, SUB, MAQ, RESUMEN DE COSTO, BD)", style_tbl_cell)],
        [Paragraph("<b>Fecha Actualización:</b>", style_tbl_cell_bold), Paragraph("Julio 2026", style_tbl_cell)]
    ]
    t_info = Table(info_data, colWidths=[120, 402])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, COLOR_SECONDARY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 16))

    # Banner explicativo en la portada
    callout_general = [
        [Paragraph("📌 <b>¿POR QUÉ USAR LA PLANTILLA OFICIAL?</b><br/>"
                   "Esta plantilla elimina por completo la captura manual repetitiva de sueldos, factores FASAR y catálogos de gastos. "
                   "Garantiza que todos los presupuestos de J&D sigan la misma estructura homologada, asegurando que al cargarse en la Web App "
                   "la cotización oficial se genere de forma <b>automática, limpia y sin errores de cálculo</b>.", style_callout)]
    ]
    t_callout = Table(callout_general, colWidths=[522])
    t_callout.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CALLOUT_BG),
        ('BOX', (0,0), (-1,-1), 1.5, COLOR_CALLOUT_BORDER),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_callout)
    story.append(Spacer(1, 25))

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 1: EL FLUJO DE TRABAJO EN 2 ROLES
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("1. Flujo de Trabajo Operativo en 2 Roles", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_SECONDARY, spaceBefore=2, spaceAfter=10))
    story.append(Paragraph("El proceso de cotización en J&D Automation opera mediante una sinergia perfecta entre el <b>Presupuestador Técnico</b> y el <b>Agente de Ventas</b>:", style_body))

    flujo_data = [
        [Paragraph("PASO", style_tbl_hdr), Paragraph("ROL RESPONSIBLE", style_tbl_hdr), Paragraph("ACTIVIDAD Y ENTREGABLE", style_tbl_hdr)],
        [
            Paragraph("<b>Paso 1</b>", style_tbl_cell_bold),
            Paragraph("<b>Presupuestador Técnico</b><br/>(Ingeniero de Costos)", style_tbl_cell),
            Paragraph("1. Descarga la <b>Plantilla Oficial (.xlsx)</b> desde la App.<br/>"
                      "2. Llena los materiales, mano de obra, subcontratos, maquinaria y gastos generales localmente en su computadora.<br/>"
                      "3. Entrega el archivo <b>.xlsx terminado</b> al Vendedor.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Paso 2</b>", style_tbl_cell_bold),
            Paragraph("<b>Vendedor / Comercial</b><br/>(Gestor de Ventas)", style_tbl_cell),
            Paragraph("1. Entra al menú <b>'2. Importador Excel'</b> en la Web App.<br/>"
                      "2. Sube el archivo Excel completado por el presupuestador.<br/>"
                      "3. Selecciona los parámetros comerciales (Margen %, Comisión %, Términos de Pago).<br/>"
                      "4. La App asigna el <b>Folio Oficial J&D</b> y genera el paquete de entregables (PDF, TPU y Excel).", style_tbl_cell)
        ]
    ]
    t_flujo = Table(flujo_data, colWidths=[55, 145, 340])
    t_flujo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_TABLE_HEADER),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 1, COLOR_SECONDARY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_ALT_ROW]),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_flujo)
    story.append(Spacer(1, 15))

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 2: CÓDIGO DE COLORES Y REGLAS DE ORO
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("2. Reglas de Oro de Captura (Código de Colores)", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_SECONDARY, spaceBefore=2, spaceAfter=10))
    story.append(Paragraph("Para evitar borrar fórmulas automáticas o corromper el archivo, siga estrictamente el código de colores incorporado en la plantilla:", style_body))

    reglas_data = [
        [Paragraph("COLOR DE CELDA", style_tbl_hdr), Paragraph("TIPO DE DATO", style_tbl_hdr), Paragraph("INSTRUCCIÓN DE MANEJO", style_tbl_hdr)],
        [
            Paragraph("<b>Celda Blanca</b>", style_tbl_cell_bold),
            Paragraph("<b>Captura Manual</b>", style_tbl_cell),
            Paragraph("Espacios donde el usuario debe escribir información técnica (descripciones, cantidades, precios unitarios de materiales).", style_tbl_cell)
        ],
        [
            Paragraph("<b>Celda con Flecha (▼)</b>", style_tbl_cell_bold),
            Paragraph("<b>Lista Desplegable</b>", style_tbl_cell),
            Paragraph("Hacer clic en la flechita para seleccionar conceptos del catálogo oficial de J&D (Puestos de MO, Gastos, Subcontratos, Clientes).", style_tbl_cell)
        ],
        [
            Paragraph("<b>Celda Celeste / Naranja</b>", style_tbl_cell_bold),
            Paragraph("<b>Fórmula Automática</b>", style_tbl_cell),
            Paragraph("<b>¡PROHIBIDO EDITAR O BORRAR!</b> Contiene fórmulas (`VLOOKUP`, `SUMIF`, multiplicación). Se calculan automáticamente.", style_tbl_cell)
        ]
    ]
    t_reglas = Table(reglas_data, colWidths=[120, 120, 300])
    t_reglas.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_TABLE_HEADER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, COLOR_SECONDARY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_ALT_ROW]),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(t_reglas)
    story.append(Spacer(1, 15))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 3: ESTRUCTURA DE HOJAS Y GUÍA PASO A PASO
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("3. Guía Detallada Paso a Paso por Hoja", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_SECONDARY, spaceBefore=2, spaceAfter=12))

    # --- HOJA PROY ---
    story.append(Paragraph("Hoja 1: PROY — Datos Generales del Proyecto", style_h2))
    story.append(Paragraph("En esta hoja se registran los datos de identificación del cliente y del proyecto. <b>No requiere ingresar folio de cotización</b> (el folio se genera en automático al subir el archivo a la App).", style_body))
    story.append(Paragraph("• <b>Cliente (Celda B4):</b> Seleccione el cliente desde el menú desplegable (▼). Si el cliente no existe, contáctese con Administración para agregarlo.", style_bullet))
    story.append(Paragraph("• <b>Nombre del Proyecto (Celda B5):</b> Escriba la descripción o título técnico completo del proyecto.", style_bullet))
    story.append(Paragraph("• <b>Ingeniero Responsable (Celda B6):</b> Escriba sus iniciales o nombre completo como presupuestador.", style_bullet))
    story.append(Paragraph("• <b>Tipo de Cambio USD (Celda B7):</b> Ingrese el tipo de cambio pactado (ej. 18.00). Sirve para convertir partidas cotizadas en dólares.", style_bullet))
    story.append(Spacer(1, 10))

    # --- HOJA WBS ---
    story.append(Paragraph("Hoja 2: WBS — Estructura de Partidas del Proyecto", style_h2))
    story.append(Paragraph("La WBS (Work Breakdown Structure) define las secciones o módulos en los que se divide el proyecto técnico.", style_body))
    story.append(Paragraph("• <b>Columna A (N° Partida):</b> Ingrese el número entero consecutivo de la partida (1, 2, 3, 4...).", style_bullet))
    story.append(Paragraph("• <b>Columna B (Descripción WBS):</b> Ingrese el nombre claro del entregable (ej. <i>'Gabinete de Control Principal PLC'</i>, <i>'Programación e Integración de Robots'</i>, <i>'Instalación Eléctrica en Planta'</i>).", style_bullet))
    story.append(Paragraph("• <b>Columna C (Alcance / Especificaciones):</b> Descripción breve del alcance de esta partida.", style_bullet))
    story.append(Spacer(1, 10))

    # --- HOJA MAT ---
    story.append(Paragraph("Hoja 3: MAT — Detalle de Materiales e Insumos", style_h2))
    story.append(Paragraph("Registra todos los componentes físicos, equipos, cables, sensores y consumibles requeridos.", style_body))
    story.append(Paragraph("• <b>Columna A (Partida N°):</b> Escriba el número de partida al que pertenece el material (1, 2, 3...).", style_bullet))
    story.append(Paragraph("• <b>Columna B (Partida WBS - Auto):</b> <font color='#1565C0'><b>¡AUTOMÁTICA!</b></font> Despliega automáticamente el nombre de la partida WBS gracias a la fórmula `VLOOKUP`. No escribir aquí.", style_bullet))
    story.append(Paragraph("• <b>Columna C (Concepto de Material):</b> Descripción comercial del material.", style_bullet))
    story.append(Paragraph("• <b>Columna D (Especificación / Modelo):</b> Marca, catálogo o número de parte.", style_bullet))
    story.append(Paragraph("• <b>Columna E (Cantidad) y F (Unidad):</b> Cantidad requerida y unidad (PZA, MTR, LOTE, KG, etc.).", style_bullet))
    story.append(Paragraph("• <b>Columna G (P.U. Base) y H (Moneda):</b> Precio unitario de lista sin IVA y moneda (MXN o USD).", style_bullet))
    story.append(Paragraph("• <b>Columna I (Importe Total MXN):</b> <font color='#1565C0'><b>¡AUTOMÁTICA!</b></font> Calcula el total convirtiendo a MXN según el tipo de cambio si es USD.", style_bullet))
    story.append(Spacer(1, 10))

    # --- HOJA MO ---
    story.append(Paragraph("Hoja 4: MO — Detalle de Mano de Obra Especializada", style_h2))
    story.append(Paragraph("Registra el personal técnico y cuadrillas de campo requeridas para cada partida.", style_body))
    
    callout_mo = [
        [Paragraph("⚡ <b>¡CÁLCULO AUTOMÁTICO DE SUELDO Y FASAR EN MO!</b><br/>"
                   "Al seleccionar el Puesto en la <b>Columna C</b> desde la lista desplegable (▼), la plantilla busca automáticamente "
                   "el <b>Sueldo Base Semanal</b> y el <b>Factor FASAR</b> directamente de la base de datos de J&D. "
                   "El costo por hora y el importe total se calculan en automático.", style_callout)]
    ]
    t_mo_box = Table(callout_mo, colWidths=[540])
    t_mo_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CALLOUT_BG),
        ('BOX', (0,0), (-1,-1), 1.5, COLOR_CALLOUT_BORDER),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_mo_box)
    story.append(Spacer(1, 6))

    story.append(Paragraph("• <b>Columna A (Partida N°):</b> Número de la partida WBS.", style_bullet))
    story.append(Paragraph("• <b>Columna B (Partida WBS - Auto):</b> <font color='#1565C0'><b>AUTOMÁTICA</b></font>.", style_bullet))
    story.append(Paragraph("• <b>Columna C (Puesto / Categoría):</b> <font color='#D35400'><b>SELECCIONAR DE MENÚ DESPLEGABLE (▼)</b></font> (ej. <i>'Programador PLC / Robot'</i>, <i>'Diseñador de Controles'</i>, <i>'Técnico Electromecánico'</i>).", style_bullet))
    story.append(Paragraph("• <b>Columna D (N° Personas):</b> Cantidad de especialistas asignados.", style_bullet))
    story.append(Paragraph("• <b>Columna E (Horas/Día) y F (Días Trabajo):</b> Horas por jornada (ej. 8 u 10) y días de duración.", style_bullet))
    story.append(Paragraph("• <b>Columnas G a J:</b> <font color='#1565C0'><b>AUTOMÁTICAS</b></font> (Sueldo Base, FASAR, Costo/Hora y Total MO).", style_bullet))
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # --- HOJA GAS ---
    story.append(Paragraph("Hoja 5: GAS — Gastos Generales de Obra (Globales)", style_h2))
    story.append(Paragraph("Los gastos generales representan los costos logísticos del proyecto (viáticos, hospedajes, pasajes, fletes, herramienta menor).", style_body))

    callout_gas = [
        [Paragraph("🟠 <b>CONCEPTO CLAVE: PRORRATEO AUTOMÁTICO DE GASTOS GENERALES</b><br/>"
                   "En la nueva plantilla, <b>los gastos NO se asignan a ninguna partida en particular</b>. Se capturan como una lista global del proyecto "
                   "y en la hoja <b>RESUMEN DE COSTO</b> el sistema los distribuye automáticamente entre todas las partidas según su porcentaje de costo directo.", style_callout)]
    ]
    t_gas_box = Table(callout_gas, colWidths=[540])
    t_gas_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_CALLOUT_BG),
        ('BOX', (0,0), (-1,-1), 1.5, COLOR_CALLOUT_BORDER),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_gas_box)
    story.append(Spacer(1, 6))

    story.append(Paragraph("• <b>Columna A (Concepto de Gasto):</b> <font color='#D35400'><b>SELECCIONAR DE MENÚ DESPLEGABLE (▼)</b></font> (disponibles los 59 conceptos oficiales de J&D).", style_bullet))
    story.append(Paragraph("• <b>Columna B (Cantidad), C (Unidad) y D (Tiempo):</b> Definir volumen, unidad (VJE, NOCH, DÍA) y duración.", style_bullet))
    story.append(Paragraph("• <b>Columna E (Costo Unitario):</b> Ingrese el costo estimado por unidad.", style_bullet))
    story.append(Paragraph("• <b>Columna F (Importe Total):</b> <font color='#1565C0'><b>AUTOMÁTICA</b></font>. Suma el total del gasto.", style_bullet))
    story.append(Spacer(1, 10))

    # --- HOJA SUB ---
    story.append(Paragraph("Hoja 6: SUB — Subcontratos Especializados", style_h2))
    story.append(Paragraph("Servicios contratados a terceros por partida (maquinados, instalaciones mecánicas, ensayos, etc.).", style_body))
    story.append(Paragraph("• <b>Columna A (Partida N°) y B (Partida WBS - Auto):</b> Asignación a partida.", style_bullet))
    story.append(Paragraph("• <b>Columna C (Concepto Subcontrato):</b> <font color='#D35400'><b>SELECCIONAR DE MENÚ DESPLEGABLE (▼)</b></font>.", style_bullet))
    story.append(Paragraph("• <b>Columna D (Proveedor) a H (Moneda):</b> Captura manual de proveedor habitual, cantidad, PU y moneda.", style_bullet))
    story.append(Paragraph("• <b>Columna I (Importe Total MXN):</b> <font color='#1565C0'><b>AUTOMÁTICA</b></font>.", style_bullet))
    story.append(Spacer(1, 10))

    # --- HOJA MAQ ---
    story.append(Paragraph("Hoja 7: MAQ — Maquinaria y Equipo Menor de Obra", style_h2))
    story.append(Paragraph("Renta o asignación de grúas, elevadores de tijera, plantas de soldar y camionetas por partida.", style_body))
    story.append(Paragraph("• <b>Columna A (Partida N°) y B (Partida WBS - Auto):</b> Asignación a partida.", style_bullet))
    story.append(Paragraph("• <b>Columna C (Concepto Maquinaria):</b> <font color='#D35400'><b>SELECCIONAR DE MENÚ DESPLEGABLE (▼)</b></font>.", style_bullet))
    story.append(Paragraph("• <b>Columna D (Modelo/Capacidad) a H (Moneda):</b> Especificaciones técnicas, tiempo, costo unitario y moneda.", style_bullet))
    story.append(Paragraph("• <b>Columna I (Importe Total MXN):</b> <font color='#1565C0'><b>AUTOMÁTICA</b></font>.", style_bullet))
    story.append(Spacer(1, 10))

    # --- HOJA RESUMEN DE COSTO ---
    story.append(Paragraph("Hoja 8: RESUMEN DE COSTO — Concentrado Final", style_h2))
    story.append(Paragraph("Esta hoja es <b>100% AUTOMÁTICA</b>. Reúne los totales de Materiales, Mano de Obra, Subcontratos y Maquinaria por partida, realiza el cálculo del costo directo base y efectúa el prorrateo proporcional de los Gastos Generales.", style_body))

    resumen_cols_data = [
        [Paragraph("COLUMNA RESUMEN", style_tbl_hdr), Paragraph("CÁLCULO AUTOMÁTICO EJECUTADO POR LA PLANTILLA", style_tbl_hdr)],
        [Paragraph("<b>Materiales / MO / SUB / MAQ</b>", style_tbl_cell_bold), Paragraph("Fórmulas `=SUMIF()` que suman automáticamente los totales asignados a esa partida.", style_tbl_cell)],
        [Paragraph("<b>Costo Directo Base</b>", style_tbl_cell_bold), Paragraph("Fórmula `=SUM(MAT+MO+SUB+MAQ)` (Costo directo sin incluir gastos generales).", style_tbl_cell)],
        [Paragraph("<b>% sobre Total</b>", style_tbl_cell_bold), Paragraph("Porcentaje de participación de esa partida sobre el costo directo total del proyecto.", style_tbl_cell)],
        [Paragraph("<b>GAS Prorrateado</b>", style_tbl_cell_bold), Paragraph("Fórmula `=TOTAL_GAS * %_Partida`. Asigna la parte proporcional de los Gastos Generales.", style_tbl_cell)],
        [Paragraph("<b>TOTAL CON GASTOS</b>", style_tbl_cell_bold), Paragraph("Suma final del costo directo de la partida incluyendo su prorrateo de gastos.", style_tbl_cell)]
    ]
    t_res_cols = Table(resumen_cols_data, colWidths=[150, 390])
    t_res_cols.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_TABLE_HEADER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, COLOR_SECONDARY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_ALT_ROW]),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_res_cols)
    story.append(Spacer(1, 10))

    # --- HOJA BD ---
    story.append(Paragraph("Hoja 9: BD — Base de Datos de Catálogos (AL FINAL)", style_h2))
    story.append(Paragraph("Ubicada al final del libro, contiene las listas maestras de puestos, sueldos, factores FASAR, gastos y subcontratos. <b>NUNCA BORRAR NI MODIFICAR ESTA HOJA</b> para no romper los desplegables del libro.", style_body))
    story.append(Spacer(1, 15))

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 4: PREGUNTAS FRECUENTES Y ERRORES COMUNES
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("4. Preguntas Frecuentes y Errores Comunes", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_SECONDARY, spaceBefore=2, spaceAfter=10))

    faq_data = [
        [Paragraph("SÍNTOMA / DUDA", style_tbl_hdr), Paragraph("CAUSA Y SOLUCIÓN RECOMENDADA", style_tbl_hdr)],
        [
            Paragraph("<b>Aparece `#N/A` o `#¡VALOR!` en la hoja MO</b>", style_tbl_cell_bold),
            Paragraph("<b>Causa:</b> Escribió manualmente el puesto en lugar de seleccionarlo del menú desplegable (▼).<br/>"
                      "<b>Solución:</b> Borre la celda y elija la categoría exacta desde la flechita del menú desplegable.", style_tbl_cell)
        ],
        [
            Paragraph("<b>La celda 'Partida WBS (Auto)' queda en blanco</b>", style_tbl_cell_bold),
            Paragraph("<b>Causa:</b> Ingresó un número de partida que no existe en la hoja `WBS`.<br/>"
                      "<b>Solución:</b> Verifique que la partida esté dada de alta primero en la hoja `WBS`.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Se borró una fórmula por accidente</b>", style_tbl_cell_bold),
            Paragraph("<b>Solución:</b> Presione `Ctrl + Z` de inmediato para deshacer el cambio, o descargue una copia limpia de la plantilla oficial desde la Web App.", style_tbl_cell)
        ],
        [
            Paragraph("<b>¿Cómo sé dónde capturar los viáticos de obra?</b>", style_tbl_cell_bold),
            Paragraph("<b>Respuesta:</b> Vaya a la hoja `GAS` (Gastos Generales), elija el concepto (ej. <i>'Hospedaje de Cuadrillas'</i> o <i>'Pasajes y Fletes'</i>) y capture cantidad y costo. Se prorrateará automáticamente en el Resumen.", style_tbl_cell)
        ]
    ]
    t_faq = Table(faq_data, colWidths=[180, 360])
    t_faq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_TABLE_HEADER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 1, COLOR_SECONDARY),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_ALT_ROW]),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(t_faq)

    doc.build(story, canvasmaker=JDManualCanvas)

def obtener_manual_pdf_bytes():
    import io
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=46
    )
    # Re-run build on buffer
    crear_manual_pdf(filename=buffer)
    buffer.seek(0)
    return buffer.getvalue()

if __name__ == "__main__":
    crear_manual_pdf("Manual_Usuario_Plantilla_Excel_JD.pdf")

