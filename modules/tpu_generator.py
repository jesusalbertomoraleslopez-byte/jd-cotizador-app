import streamlit as st
import pandas as pd
from database.models import get_connection

def render_tpu_generator():
    st.title("🎴 Tarjetas de Precios Unitarios (TPU)")
    st.caption("Generación e inspección detallada de TPU por partida para propuestas técnicas y contratos.")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.folio, c.proyecto, c.revision, c.margen_porcentaje, c.comision_porcentaje
        FROM cotizaciones c
        ORDER BY c.id DESC
    """)
    cotizaciones = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not cotizaciones:
        st.warning("No hay cotizaciones guardadas. Crea una nueva cotización o importa un archivo Excel para ver sus Tarjetas de Precios Unitarios.")

        # Cargar ejemplo de TPU demostrativo
        st.subheader("📌 Vista Previa Demostrativa de TPU (Partida 1)")
        st.info("Ejemplo: TABLERO DE CONTROL PARA SEÑALES DE CORRIENTE MOLINO Y SOPLADOR")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **Empresa:** J&D Automation  
            **Proyecto:** MIGRACIÓN Y CONTROL PID MOLINOS  
            **Cliente:** YESA  
            **Unidad:** LOTE  
            """)
        with col2:
            st.markdown("""
            **Folio:** COT-YES-082-RG  
            **Revisión:** R0  
            **Costo Directo Unitario:** $75,553.00 MXN  
            **Precio Unitario Cobrado (TPU):** $113,330.00 MXN  
            """)

        st.divider()
        st.write("#### 1. Materiales e Insumos Integrados")
        df_mat_demo = pd.DataFrame([
            {"Concepto": "MODULO DE ENTRADAS ANALOGAS", "Cant": 3, "Unidad": "LOTE", "P.U. MXN": 8000.0, "Importe": 24000.0},
            {"Concepto": "BASE", "Cant": 3, "Unidad": "PZA", "P.U. MXN": 2475.0, "Importe": 7425.0},
            {"Concepto": "TERMINAL", "Cant": 3, "Unidad": "PZA", "P.U. MXN": 1155.0, "Importe": 3465.0},
            {"Concepto": "MODULO ETHERNET", "Cant": 1, "Unidad": "PZA", "P.U. MXN": 8600.0, "Importe": 8600.0},
            {"Concepto": "GABINETE", "Cant": 1, "Unidad": "PZA", "P.U. MXN": 1980.0, "Importe": 1980.0},
            {"Concepto": "MISCELANEOS DE MONTAJE", "Cant": 1, "Unidad": "LOTE", "P.U. MXN": 4950.0, "Importe": 4950.0},
            {"Concepto": "FUENTE ALIMENTACION", "Cant": 1, "Unidad": "PZA", "P.U. MXN": 3300.0, "Importe": 3300.0},
            {"Concepto": "SWITCH ETHERNET", "Cant": 1, "Unidad": "PZA", "P.U. MXN": 3300.0, "Importe": 3300.0},
        ])
        st.dataframe(df_mat_demo.style.format({'P.U. MXN': '${:,.2f}', 'Importe': '${:,.2f}'}), use_container_width=True)

        st.write("#### 2. Mano de Obra Operativa Integrada")
        df_mo_demo = pd.DataFrame([
            {"Puesto": "Tablerista", "Personal": 1, "Semanas": 2.0, "Sueldo Base Semanal": 4500.0, "FASAR": 1.45, "Costo Semanal Real": 6525.0, "Importe": 13050.0},
        ])
        st.dataframe(df_mo_demo.style.format({'Sueldo Base Semanal': '${:,.2f}', 'Costo Semanal Real': '${:,.2f}', 'Importe': '${:,.2f}'}), use_container_width=True)

        st.write("#### 3. Desglose Final de Precio Unitario (TPU)")
        tpu_summary = pd.DataFrame([
            {"Elemento": "Materiales (A)", "Importe": 57020.0},
            {"Elemento": "Mano de Obra (B)", "Importe": 13050.0},
            {"Elemento": "Supervisión (C - 30% MO)", "Importe": 3915.0},
            {"Elemento": "Herramienta Menor (F - 3% MO)", "Importe": 839.34},
            {"Elemento": "Gastos / Viáticos Asignados (G)", "Importe": 728.67},
            {"Elemento": "TOTAL COSTO DIRECTO", "Importe": 75553.01},
            {"Elemento": "Margen de Utilidad Asignado (30%)", "Importe": 32379.86},
            {"Elemento": "Comisión Asignada (5%)", "Importe": 5397.13},
            {"Elemento": "PRECIO UNITARIO FINAL COBRADO (TPU)", "Importe": 113330.00},
        ])
        st.dataframe(tpu_summary.style.format({'Importe': '${:,.2f}'}), use_container_width=True)

    else:
        cot_options = {f"{c['folio']} - {c['proyecto']} ({c['revision']})": c['id'] for c in cotizaciones}
        selected_label = st.selectbox("Seleccionar Cotización", list(cot_options.keys()))
        cot_id = cot_options[selected_label]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cotizacion_partidas WHERE cotizacion_id = ? ORDER BY numero_partida", (cot_id,))
        partidas = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if partidas:
            partida_opts = {f"Partida {p['numero_partida']}: {p['descripcion']}": p['id'] for p in partidas}
            p_label = st.selectbox("Seleccionar Partida para Generar TPU", list(partida_opts.keys()))
            p_id = partida_opts[p_label]

            p_info = next(p for p in partidas if p['id'] == p_id)

            st.success(f"Visualizando TPU para Partida #{p_info['numero_partida']}: {p_info['descripcion']}")
            st.metric("Costo Directo Partida", f"${p_info['costo_directo_total']:,.2f}")
