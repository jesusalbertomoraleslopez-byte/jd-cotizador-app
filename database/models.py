import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "cotizador.db")

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Catálogo de Materiales e Insumos Base
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_materiales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT,
        descripcion TEXT NOT NULL UNIQUE,
        unidad TEXT DEFAULT 'PZA',
        precio_unitario_usd REAL DEFAULT 0.0,
        precio_unitario_mxn REAL DEFAULT 0.0,
        categoria TEXT DEFAULT 'General',
        proveedor TEXT,
        activo INTEGER DEFAULT 1,
        fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Catálogo de Mano de Obra Base
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_mano_obra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT NOT NULL UNIQUE,
        sueldo_base_semanal REAL NOT NULL,
        fasar REAL DEFAULT 1.45,
        sobre_sueldo REAL DEFAULT 1.0,
        bonos REAL DEFAULT 0.0,
        viaticos_semanal REAL DEFAULT 0.0,
        activo INTEGER DEFAULT 1
    );
    """)

    # 2b. Catálogo de Gastos Generales Base
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_gastos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clave TEXT,
        concepto TEXT NOT NULL UNIQUE,
        unidad TEXT DEFAULT 'VJE',
        costo_unitario_default REAL DEFAULT 0.0,
        categoria TEXT DEFAULT 'Generales',
        uso_descripcion TEXT,
        activo INTEGER DEFAULT 1
    );
    """)
    for col, typedef in [('clave', 'TEXT'), ('uso_descripcion', 'TEXT')]:
        try:
            cursor.execute(f"ALTER TABLE catalogo_gastos ADD COLUMN {col} {typedef}")
            conn.commit()
        except Exception:
            pass


    # 2c. Catálogo de Subcontratos Base
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_subcontratos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        concepto TEXT NOT NULL UNIQUE,
        unidad TEXT DEFAULT 'SERV',
        costo_referencia REAL DEFAULT 0.0,
        proveedor_habitual TEXT,
        categoria TEXT DEFAULT 'Especializados',
        activo INTEGER DEFAULT 1
    );
    """)


    # 3. Clientes (empresa)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        acronimo TEXT,
        rfc TEXT,
        industria TEXT,
        sitio_web TEXT,
        direccion_fiscal TEXT,
        ciudad TEXT,
        estado TEXT,
        pais TEXT DEFAULT 'México',
        contacto TEXT,
        email TEXT,
        telefono TEXT,
        notas TEXT,
        activo INTEGER DEFAULT 1
    );
    """)
    # Agregar columnas nuevas si la tabla ya existía (migración segura con commit inmediato)
    for col, typedef in [
        ('acronimo', 'TEXT'), ('industria', 'TEXT'), ('sitio_web', 'TEXT'),
        ('direccion_fiscal', 'TEXT'), ('ciudad', 'TEXT'), ('estado', 'TEXT'),
        ('pais', "TEXT DEFAULT 'México'"), ('notas', 'TEXT'), ('activo', 'INTEGER DEFAULT 1'),
        ('contacto', 'TEXT'), ('rfc', 'TEXT'), ('logo_path', 'TEXT'),
    ]:
        try:
            cursor.execute(f"ALTER TABLE clientes ADD COLUMN {col} {typedef}")
            conn.commit()
        except Exception:
            pass


    # 3b. Contactos por cliente (múltiples usuarios/contactos por empresa)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes_contactos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        apellido TEXT,
        cargo TEXT,
        departamento TEXT,
        email TEXT,
        telefono_oficina TEXT,
        celular TEXT,
        iniciales TEXT,
        es_principal INTEGER DEFAULT 0,
        notas TEXT,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    );
    """)

    # 3c. Ingenieros J&D (para las iniciales del folio)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jd_ingenieros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        apellido TEXT,
        iniciales TEXT NOT NULL UNIQUE,
        cargo TEXT,
        email TEXT,
        activo INTEGER DEFAULT 1
    );
    """)
    # Semilla de ingenieros base
    for ing in [
        ('David', 'de Santiago', 'DS', 'Gerente de Proyectos', ''),
        ('Rodrigo', 'González', 'RG', 'Ingeniero de Control', ''),
        ('Jesús', 'Morales', 'JM', 'Ingeniero Eléctrico', ''),
        ('Alberto', 'López', 'AL', 'Director General', ''),
    ]:
        cursor.execute("""
            INSERT OR IGNORE INTO jd_ingenieros (nombre, apellido, iniciales, cargo, email)
            VALUES (?,?,?,?,?)
        """, ing)

    # 4. Encabezado de Cotizaciones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        folio TEXT NOT NULL UNIQUE,
        cliente_id INTEGER,
        proyecto TEXT NOT NULL,
        revision TEXT DEFAULT 'R0',
        fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
        tipo_cambio_usd REAL DEFAULT 18.00,
        margen_porcentaje REAL DEFAULT 0.30,
        comision_porcentaje REAL DEFAULT 0.05,
        supervision_porcentaje REAL DEFAULT 0.30,
        herramienta_porcentaje REAL DEFAULT 0.03,
        gastos_indirectos REAL DEFAULT 0.0,
        maquinaria_total REAL DEFAULT 0.0,
        estatus TEXT DEFAULT 'Borrador',
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
    );
    """)

    for col, typedef in [
        ('nombre_contacto', "TEXT"),
        ('correo_contacto', "TEXT"),
        ('telefono_contacto', "TEXT"),
        ('congelada', "INTEGER DEFAULT 0"),
        ('pdf_path', "TEXT"),
        ('excel_path', "TEXT"),
        ('condiciones_pago', "TEXT DEFAULT 'CREDITO'"),
        ('tiempo_entrega', "TEXT DEFAULT '2 SEMANAS'"),
        ('vigencia_cotizacion', "TEXT DEFAULT '15 días'"),
        ('moneda_cotizacion', "TEXT DEFAULT 'MXN pesos mexicanos'"),
        ('hitos_pago_json', "TEXT"),
        ('historial_modificaciones', "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE cotizaciones ADD COLUMN {col} {typedef}")
            conn.commit()
        except Exception:
            pass

    # Tabla para Respuestas Técnicas / Especificaciones con Foto por Cotización
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizacion_respuestas_tecnicas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL,
        partida_num INTEGER DEFAULT 1,
        componente TEXT NOT NULL,
        especificacion_tecnica TEXT NOT NULL,
        imagen_path TEXT,
        FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE
    );
    """)

    # 5. Partidas de Cotización

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizacion_partidas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL,
        numero_partida INTEGER NOT NULL,
        descripcion TEXT NOT NULL,
        costo_mat REAL DEFAULT 0.0,
        costo_mo REAL DEFAULT 0.0,
        costo_sup REAL DEFAULT 0.0,
        costo_sub REAL DEFAULT 0.0,
        costo_maq REAL DEFAULT 0.0,
        costo_hta REAL DEFAULT 0.0,
        costo_gastos REAL DEFAULT 0.0,
        costo_directo_total REAL DEFAULT 0.0,
        precio_venta_partida REAL DEFAULT 0.0,
        FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE
    );
    """)

    # 6. DETALLE: Materiales por Partida (Pestaña Material)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizacion_materiales_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL,
        partida_id INTEGER NOT NULL,
        codigo TEXT,
        descripcion TEXT NOT NULL,
        cantidad REAL DEFAULT 1.0,
        unidad TEXT DEFAULT 'PZA',
        precio_unitario_usd REAL DEFAULT 0.0,
        precio_unitario_mxn REAL DEFAULT 0.0,
        importe_mxn REAL DEFAULT 0.0,
        FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE,
        FOREIGN KEY (partida_id) REFERENCES cotizacion_partidas(id) ON DELETE CASCADE
    );
    """)

    # 7. DETALLE: Mano de Obra por Partida (Pestaña M. O.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizacion_mo_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL,
        partida_id INTEGER NOT NULL,
        categoria_nombre TEXT NOT NULL,
        cantidad_personal INTEGER DEFAULT 1,
        sueldo_base_semanal REAL DEFAULT 0.0,
        fasar REAL DEFAULT 1.45,
        sobre_sueldo REAL DEFAULT 1.0,
        bonos REAL DEFAULT 0.0,
        viaticos_semanal REAL DEFAULT 0.0,
        semanas REAL DEFAULT 1.0,
        horas_hombre REAL DEFAULT 0.0,
        importe_total REAL DEFAULT 0.0,
        FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE,
        FOREIGN KEY (partida_id) REFERENCES cotizacion_partidas(id) ON DELETE CASCADE
    );
    """)

    # 8. DETALLE: Subcontratos por Partida (Pestaña Subcontratos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizacion_subcontratos_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL,
        partida_id INTEGER NOT NULL,
        descripcion TEXT NOT NULL,
        cantidad REAL DEFAULT 1.0,
        unidad TEXT DEFAULT 'SERV',
        pu_mxn REAL DEFAULT 0.0,
        importe_mxn REAL DEFAULT 0.0,
        subcontratista TEXT,
        FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE,
        FOREIGN KEY (partida_id) REFERENCES cotizacion_partidas(id) ON DELETE CASCADE
    );
    """)

    # 9. DETALLE: Maquinaria por Partida (Pestaña Maquinaria)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizacion_maquinaria_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL,
        partida_id INTEGER NOT NULL,
        clave TEXT,
        nombre TEXT NOT NULL,
        cantidad REAL DEFAULT 1.0,
        unidad TEXT DEFAULT 'DIA',
        costo_unitario REAL DEFAULT 0.0,
        total_mxn REAL DEFAULT 0.0,
        FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE,
        FOREIGN KEY (partida_id) REFERENCES cotizacion_partidas(id) ON DELETE CASCADE
    );
    """)

    # 10. DETALLE: Gastos Generales del Proyecto (Pestaña Gastos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizacion_gastos_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL,
        nombre TEXT NOT NULL,
        cantidad REAL DEFAULT 1.0,
        unidad TEXT DEFAULT 'LTS',
        tiempo_valor REAL DEFAULT 1.0,
        tiempo_unidad TEXT DEFAULT 'DIAS',
        costo_unitario REAL DEFAULT 0.0,
        importe_total REAL DEFAULT 0.0,
        FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE
    );
    """)

    # 11. GANTT — Cronograma de actividades por cotización
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cotizacion_gantt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cotizacion_id INTEGER NOT NULL,
        partida_id INTEGER,
        actividad TEXT NOT NULL,
        tipo TEXT DEFAULT 'Actividad',
        responsable TEXT,
        fecha_inicio DATE,
        dias_duracion INTEGER DEFAULT 1,
        orden INTEGER DEFAULT 0,
        predecesora_id INTEGER,
        FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE,
        FOREIGN KEY (partida_id) REFERENCES cotizacion_partidas(id) ON DELETE SET NULL,
        FOREIGN KEY (predecesora_id) REFERENCES cotizacion_gantt(id) ON DELETE SET NULL
    );
    """)

    conn.commit()

    # ── Migración segura: columnas de versión/congelamiento en cotizaciones ──
    for col, typedef in [
        ('fecha_aprobacion', 'DATETIME'),
        ('aprobado_por',     'TEXT'),
        ('congelada',        'INTEGER DEFAULT 0'),
        ('notas_version',    'TEXT'),
        ('ingeniero_id',     'TEXT'),
        ('nombre_contacto',  'TEXT'),
    ]:
        try:
            cursor.execute(f"ALTER TABLE cotizaciones ADD COLUMN {col} {typedef}")
            conn.commit()
        except Exception:
            pass

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos estructurada correctamente.")

