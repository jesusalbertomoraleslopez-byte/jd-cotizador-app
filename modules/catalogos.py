"""
Módulo de Catálogos Base — J&D Automation Industries
Administración de 4 catálogos clave: Mano de Obra, Materiales, Gastos Generales y Subcontratos.
"""
import streamlit as st
import pandas as pd
from database.db_manager import (
    get_catalogo_mano_obra,
    get_catalogo_materiales,
    add_material,
    update_mano_obra,
    get_catalogo_gastos,
    add_gasto_base,
    delete_gasto_base,
    get_catalogo_subcontratos,
    add_subcontrato_base,
    delete_subcontrato_base
)
from config import BRAND_ORANGE, BRAND_CHARCOAL, BRAND_CHARCOAL_MED, BRAND_WHITE, BRAND_BORDER_LIGHT

def render_catalogos_page():
    tab_mo, tab_mat, tab_gas, tab_sub = st.tabs([
        "👷 Mano de Obra (Tarifas)",
        "🔩 Materiales e Insumos",
        "✈️ Gastos Generales",
        "🤝 Subcontratos Base"
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 1: MANO DE OBRA
    # ─────────────────────────────────────────────────────────────────────────
    with tab_mo:
        st.subheader("Listado de Personal Operativo y Tarifas J&D")
        st.info("💡 Las tarifas base semanales se ajustan mediante el FASAR (Factor de Salario Real = 1.45) para calcular el costo semanal real y el costo diario.")

        mo_data = get_catalogo_mano_obra()
        if mo_data:
            df_mo = pd.DataFrame(mo_data)
            df_show = df_mo[['id', 'categoria', 'sueldo_base_semanal', 'fasar', 'costo_semanal', 'costo_diario_real']].copy()
            df_show.columns = ['ID', 'Categoría / Puesto', 'Sueldo Base Semanal (MXN)', 'FASAR', 'Costo Semanal Real (MXN)', 'Costo Diario Real (MXN)']

            st.dataframe(
                df_show.style.format({
                    'Sueldo Base Semanal (MXN)': '${:,.2f}',
                    'FASAR': '{:.2f}',
                    'Costo Semanal Real (MXN)': '${:,.2f}',
                    'Costo Diario Real (MXN)': '${:,.2f}'
                }),
                use_container_width=True,
                height=380
            )

            st.divider()
            st.subheader("✏️ Editar Tarifa de Mano de Obra")
            col_sel, col_val, col_btn = st.columns([2, 2, 1])
            with col_sel:
                role_selected = st.selectbox("Seleccionar Categoría", options=df_mo['categoria'].tolist(), key="cat_mo_sel")

            selected_row = df_mo[df_mo['categoria'] == role_selected].iloc[0]

            with col_val:
                new_salary = st.number_input("Nuevo Sueldo Base Semanal (MXN)", value=float(selected_row['sueldo_base_semanal']), step=100.0, key="cat_mo_salary")
                new_fasar  = st.number_input("FASAR", value=float(selected_row['fasar']), step=0.05, key="cat_mo_fasar")

            with col_btn:
                st.write(" ")
                st.write(" ")
                if st.button("💾 Guardar Cambios", key="save_mo_btn", type="primary"):
                    update_mano_obra(int(selected_row['id']), new_salary, fasar=new_fasar)
                    st.success(f"Tarifa actualizada para {role_selected}")
                    st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 2: MATERIALES E INSUMOS
    # ─────────────────────────────────────────────────────────────────────────
    with tab_mat:
        st.subheader("Catálogo Base de Insumos y Precios Unitarios")
        col_search, col_space = st.columns([3, 1])
        with col_search:
            search_query = st.text_input("🔍 Buscar material por descripción...", value="", key="mat_search_input")

        materials = get_catalogo_materiales(filtro=search_query)
        if materials:
            df_mat = pd.DataFrame(materials)
            df_mat_show = df_mat[['codigo', 'descripcion', 'unidad', 'precio_unitario_mxn', 'precio_unitario_usd', 'categoria']].copy()
            df_mat_show.columns = ['Código', 'Descripción', 'Unidad', 'Precio Unitario (MXN)', 'Precio Unitario (USD)', 'Categoría']

            st.dataframe(
                df_mat_show.style.format({
                    'Precio Unitario (MXN)': '${:,.2f}',
                    'Precio Unitario (USD)': '${:,.2f}'
                }),
                use_container_width=True,
                height=420
            )
            st.caption(f"Mostrando {len(materials)} materiales registrados.")
        else:
            st.warning("No se encontraron materiales con ese criterio de búsqueda.")

        st.divider()
        st.subheader("➕ Agregar Nuevo Insumo al Catálogo Base")
        with st.form("form_nuevo_material", clear_on_submit=True):
            c1, c2, c3 = st.columns([1.2, 3, 1.5])
            with c1:
                codigo = st.text_input("Código / N° Parte")
                unidad = st.selectbox("Unidad", ["PZA", "MTS", "LOTE", "SERVICIOS", "JGO", "KG", "KIT", "TRAMO"])
            with c2:
                descripcion = st.text_input("Descripción del Insumo *")
                categoria   = st.text_input("Categoría", value="General")
            with c3:
                pu_mxn = st.number_input("Precio Unitario (MXN)", value=0.0, step=10.0)
                pu_usd = st.number_input("Precio Unitario (USD)", value=0.0, step=1.0)

            if st.form_submit_button("💾 Guardar Insumo", type="primary"):
                if descripcion.strip():
                    add_material(codigo, descripcion.strip(), unidad, pu_usd, pu_mxn, categoria)
                    st.success(f"Material '{descripcion}' agregado correctamente.")
                    st.rerun()
                else:
                    st.error("La descripción es obligatoria.")

    # ─────────────────────────────────────────────────────────────────────────
    # TAB 3: GASTOS GENERALES BASE
    # ─────────────────────────────────────────────────────────────────────────
    with tab_gas:
        st.subheader("Cuentas de Costo y Gastos Generales (Catálogo Oficial J&D)")
        st.caption("Catálogo completo de conceptos de costo a nivel general de obras y proyectos.")

        col_sg, col_count_g = st.columns([3, 1])
        with col_sg:
            search_g = st.text_input("🔍 Buscar por Clave, Concepto o Categoría...", key="gas_search_input")

        gastos_list = get_catalogo_gastos(filtro=search_g)
        with col_count_g:
            st.markdown(f"<div style='padding-top:10px;text-align:right;font-size:13px;color:{BRAND_CHARCOAL_MED};font-weight:700;'>{len(gastos_list)} conceptos</div>", unsafe_allow_html=True)

        if gastos_list:
            df_g = pd.DataFrame(gastos_list)
            # Asegurar columnas
            for col_n in ['clave', 'uso_descripcion']:
                if col_n not in df_g.columns: df_g[col_n] = '—'

            df_g_show = df_g[['clave', 'concepto', 'uso_descripcion', 'unidad', 'costo_unitario_default', 'categoria']].copy()
            df_g_show.columns = ['Clave', 'Descripción del Concepto', 'Descripción de Su Uso', 'Unidad Default', 'Costo Unit. Default (MXN)', 'Categoría']

            st.dataframe(
                df_g_show.style.format({'Costo Unit. Default (MXN)': '${:,.2f}'}),
                use_container_width=True,
                height=480
            )

            # Botón para eliminar un concepto
            st.divider()
            col_del_sel, col_del_btn = st.columns([3, 1])
            with col_del_sel:
                gasto_del_name = st.selectbox("Eliminar Concepto del Catálogo", [f"{g.get('clave','')} — {g['concepto']}" for g in gastos_list], key="g_del_sel")
            with col_del_btn:
                st.write(" ")
                st.write(" ")
                if st.button("🗑️ Eliminar Concepto", key="btn_del_g_base"):
                    sel_clave = gasto_del_name.split(" — ")[0]
                    g_obj = next((g for g in gastos_list if g.get('clave') == sel_clave or f"{g.get('clave','')} — {g['concepto']}" == gasto_del_name), None)
                    if g_obj:
                        delete_gasto_base(g_obj['id'])
                        st.success("Concepto eliminado del catálogo.")
                        st.rerun()
        else:
            st.info("No se encontraron conceptos de gastos.")

        st.divider()
        st.subheader("➕ Agregar Nuevo Concepto al Catálogo de Gastos Base")
        with st.form("form_nuevo_gasto_base", clear_on_submit=True):
            g1, g2, g3 = st.columns([1.5, 3.5, 1.5])
            with g1: g_clav = st.text_input("Clave *", placeholder="Ej: GAST-100 / CBE-120")
            with g2: g_conc = st.text_input("Concepto / Descripción *", placeholder="Ej: Servicios de Mantenimiento Especializado")
            with g3: g_uni  = st.selectbox("Unidad", ["VJE", "NOCH", "DIA", "LOTE", "SERV", "MES", "PZA", "HRS"])

            g4, g5, g6 = st.columns([2, 2, 4])
            with g4: g_cost = st.number_input("Costo Unitario Default (MXN)", value=0.0, step=50.0)
            with g5: g_cat  = st.text_input("Categoría", value="Generales")
            with g6: g_uso  = st.text_input("Descripción de Su Uso", placeholder="Uso previsto en obra / proyecto")

            if st.form_submit_button("💾 Guardar Concepto de Gasto", type="primary"):
                if g_conc.strip():
                    add_gasto_base(g_conc.strip(), g_uni, g_cost, g_cat, clave=g_clav, uso=g_uso)
                    st.success(f"Gasto '{g_conc.strip()}' [{g_clav}] agregado correctamente.")
                    st.rerun()
                else:
                    st.error("La descripción del concepto es obligatoria.")


    # ─────────────────────────────────────────────────────────────────────────
    # TAB 4: SUBCONTRATOS BASE
    # ─────────────────────────────────────────────────────────────────────────
    with tab_sub:
        st.subheader("Catálogo Base de Subcontratos y Servicios Externos")
        st.caption("Catálogo de servicios subcontratados con proveedores habituales y tarifas de referencia.")

        col_ss, _ = st.columns([3, 1])
        with col_ss:
            search_s = st.text_input("🔍 Buscar subcontrato base...", key="sub_search_input")

        subs_list = get_catalogo_subcontratos(filtro=search_s)
        if subs_list:
            df_sub = pd.DataFrame(subs_list)
            df_sub_show = df_sub[['concepto', 'unidad', 'costo_referencia', 'proveedor_habitual', 'categoria']].copy()
            df_sub_show.columns = ['Servicio / Subcontrato', 'Unidad', 'Costo Referencia (MXN)', 'Proveedor Habitual', 'Categoría']

            st.dataframe(
                df_sub_show.style.format({'Costo Referencia (MXN)': '${:,.2f}'}),
                use_container_width=True,
                height=350
            )

            st.divider()
            col_delsub_sel, col_delsub_btn = st.columns([3, 1])
            with col_delsub_sel:
                sub_del_name = st.selectbox("Eliminar Subcontrato Base", [s['concepto'] for s in subs_list], key="s_del_sel")
            with col_delsub_btn:
                st.write(" ")
                st.write(" ")
                if st.button("🗑️ Eliminar", key="btn_del_s_base"):
                    s_obj = next((s for s in subs_list if s['concepto'] == sub_del_name), None)
                    if s_obj:
                        delete_subcontrato_base(s_obj['id'])
                        st.success("Subcontrato eliminado de la base.")
                        st.rerun()
        else:
            st.info("No hay subcontratos registrados en la base.")

        st.divider()
        st.subheader("➕ Agregar Nuevo Subcontrato al Catálogo Base")
        with st.form("form_nuevo_sub_base", clear_on_submit=True):
            s1, s2, s3, s4, s5 = st.columns([3, 1.2, 1.8, 2.5, 1.5])
            with s1: s_conc = st.text_input("Servicio / Subcontrato *", placeholder="Ej: Arrendamiento de Grúa Telescópica 25t")
            with s2: s_uni  = st.selectbox("Unidad", ["SERV", "HORAS", "SEMANAS", "PZA", "ARREND", "CONTRATO", "DIAS", "LOTE", "FLETE"])
            with s3: s_cost = st.number_input("Costo Referencia (MXN)", value=0.0, step=100.0)
            with s4: s_prov = st.text_input("Proveedor Habitual", placeholder="Nombre del proveedor habitual")
            with s5: s_cat  = st.text_input("Categoría", value="Especializados")

            if st.form_submit_button("💾 Guardar Subcontrato Base", type="primary"):
                if s_conc.strip():
                    add_subcontrato_base(s_conc.strip(), s_uni, s_cost, s_prov, s_cat)
                    st.success(f"Subcontrato '{s_conc.strip()}' agregado al catálogo base.")
                    st.rerun()
                else:
                    st.error("El concepto del subcontrato es obligatorio.")
