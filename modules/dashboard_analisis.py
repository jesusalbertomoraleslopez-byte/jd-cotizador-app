import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.models import get_connection
from config import (BRAND_ORANGE, BRAND_CHARCOAL, BRAND_CHARCOAL_MED, BRAND_WHITE,
                    BRAND_BORDER_LIGHT, BRAND_GRAY_BG, BRAND_SUCCESS, BRAND_DANGER,
                    DEFAULT_MARGEN, DEFAULT_COMISION)

# Paleta de colores J&D para gráficos (Orange primero, luego grises/azules institucionales)
JD_CHART_COLORS = ["#FE8C29", "#434E62", "#8C96A6", "#CBD5E1", "#10B981", "#3B82F6", "#EF4444"]

def jd_metric_card(label, value, subtext="", highlight=False):
    color = BRAND_ORANGE if highlight else BRAND_CHARCOAL
    return f"""
    <div class="jd-metric-card">
        <div class="jd-metric-label">{label}</div>
        <div class="jd-metric-value" style="color:{color};">{value}</div>
        <div class="jd-metric-subtext">{subtext}</div>
    </div>
    """

def render_dashboard_analisis():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.folio, c.proyecto, cl.nombre as cliente, COALESCE(c.revision,'R0') as revision,
               c.tipo_cambio_usd, c.margen_porcentaje, c.comision_porcentaje, c.gastos_indirectos,
               COALESCE(c.estatus, 'Cotizado') as estatus, COALESCE(c.congelada, 0) as congelada
        FROM cotizaciones c
        LEFT JOIN clientes cl ON c.cliente_id = cl.id
        ORDER BY c.id DESC
    """)
    cotizaciones = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # ── DOS VISTAS PRINCIPALES: EMBUDO CRM Y ANÁLISIS DETALLADO ──
    dash_tab1, dash_tab2 = st.tabs([
        "🎯 Embudo de Ventas & Oportunidades (CRM Odoo Style)",
        "📊 Análisis Financiero Detallado por Cotización"
    ])

    # ─────────────────────────────────────────────────────────────────────────
    # PESTAÑA 1: VISTA CRM / EMBUDO KANBAN ODOO STYLE
    # ─────────────────────────────────────────────────────────────────────────
    with dash_tab1:
        st.markdown(f"""
        <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-left:5px solid {BRAND_ORANGE};
                    border-radius:8px;padding:14px 18px;margin-bottom:18px;font-family:'Montserrat',sans-serif;">
            <p style="font-size:13px;font-weight:800;color:{BRAND_CHARCOAL};margin:0 0 2px 0;">
                🎯 PIPELINE DE VENTAS & GESTIÓN DE OPORTUNIDADES COMERCIALES
            </p>
            <p style="font-size:11px;color:{BRAND_CHARCOAL_MED};margin:0;">
                Visualiza y gestiona el flujo de proyectos por etapa (En Proceso, Cotizados, Ganadas y Perdidas) con estética de CRM.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if not cotizaciones:
            st.info("No hay presupuestos registrados en el pipeline de ventas.")
        else:
            # Agrupar por estatus
            cots_en_proceso = [c for c in cotizaciones if c['estatus'].lower() in ['borrador', 'en proceso', 'en revisión']]
            cots_cotizadas  = [c for c in cotizaciones if c['estatus'].lower() in ['cotizado', 'emitido', 'enviado']]
            cots_ganadas    = [c for c in cotizaciones if c['estatus'].lower() in ['ganada', 'aprobada', 'aceptada']]
            cots_perdidas   = [c for c in cotizaciones if c['estatus'].lower() in ['perdida', 'cancelada', 'rechazada']]

            # Métricas de Embudo CRM
            crm_c1, crm_c2, crm_c3, crm_c4 = st.columns(4)
            with crm_c1:
                st.markdown(jd_metric_card("🟡 En Proceso", f"{len(cots_en_proceso)} Proyectos", "Presupuestación Interna"), unsafe_allow_html=True)
            with crm_c2:
                st.markdown(jd_metric_card("🔵 Cotizados / Oferta", f"{len(cots_cotizadas)} Proyectos", "En Seguimiento Cliente", highlight=True), unsafe_allow_html=True)
            with crm_c3:
                st.markdown(jd_metric_card("🟢 Ganadas / Cierre", f"{len(cots_ganadas)} Proyectos", "Proyectos Adjudicados"), unsafe_allow_html=True)
            with crm_c4:
                st.markdown(jd_metric_card("🔴 Perdidas / Cancel", f"{len(cots_perdidas)} Proyectos", "Descartadas / Vencidas"), unsafe_allow_html=True)

            st.markdown("---")

            # ── VISTA KANBAN DE 4 COLUMNAS ──
            k_col1, k_col2, k_col3, k_col4 = st.columns(4)

            def render_kanban_card(c):
                rev_tag = c.get('revision','R0')
                state_icon = "🔒" if c['congelada'] else "✏️"
                return f"""
                <div style="background:{BRAND_WHITE};border:1px solid {BRAND_BORDER_LIGHT};border-top:3px solid {BRAND_ORANGE};
                            border-radius:8px;padding:10px 12px;margin-bottom:10px;font-family:'Montserrat',sans-serif;
                            box-shadow:0 1px 3px rgba(0,0,0,0.06);">
                    <div style="font-size:10px;font-weight:800;color:{BRAND_ORANGE};">{state_icon} {c['folio']} ({rev_tag})</div>
                    <div style="font-size:12px;font-weight:800;color:{BRAND_CHARCOAL};margin:2px 0;">{c['cliente']}</div>
                    <div style="font-size:11px;color:{BRAND_CHARCOAL_MED};line-height:1.2;margin-bottom:6px;">{c['proyecto'][:35]}...</div>
                    <div style="display:flex;justify-content:space-between;font-size:10px;color:#64748B;">
                        <span>Margen: <b>{c['margen_porcentaje']*100:.0f}%</b></span>
                        <span style="color:#10B981;font-weight:800;">{c['estatus'].upper()}</span>
                    </div>
                </div>
                """

            with k_col1:
                st.markdown(f"<p style='font-size:12px;font-weight:900;color:#D97706;margin:0 0 8px 0;'>🟡 EN PROCESO ({len(cots_en_proceso)})</p>", unsafe_allow_html=True)
                for c in cots_en_proceso:
                    st.markdown(render_kanban_card(c), unsafe_allow_html=True)

            with k_col2:
                st.markdown(f"<p style='font-size:12px;font-weight:900;color:#2563EB;margin:0 0 8px 0;'>🔵 COTIZADOS ({len(cots_cotizadas)})</p>", unsafe_allow_html=True)
                for c in cots_cotizadas:
                    st.markdown(render_kanban_card(c), unsafe_allow_html=True)

            with k_col3:
                st.markdown(f"<p style='font-size:12px;font-weight:900;color:#059669;margin:0 0 8px 0;'>🟢 GANADAS ({len(cots_ganadas)})</p>", unsafe_allow_html=True)
                for c in cots_ganadas:
                    st.markdown(render_kanban_card(c), unsafe_allow_html=True)

            with k_col4:
                st.markdown(f"<p style='font-size:12px;font-weight:900;color:#DC2626;margin:0 0 8px 0;'>🔴 PERDIDAS ({len(cots_perdidas)})</p>", unsafe_allow_html=True)
                for c in cots_perdidas:
                    st.markdown(render_kanban_card(c), unsafe_allow_html=True)

            st.markdown("---")

            # ── INTERACTIVIDAD CRM DETALLADA POR ETAPA ──
            st.markdown(f"<h3 style='font-size:15px;font-weight:900;color:{BRAND_CHARCOAL};margin-bottom:10px;'>📋 DESGLOSE DETALLADO DE SEGUIMIENTO COMERCIAL CRM</h3>", unsafe_allow_html=True)
            
            sel_crm_stage = st.selectbox(
                "Filtrar Oportunidades por Etapa Comercial",
                ["🔵 COTIZADOS (Ofertas en seguimiento)", "🟡 EN PROCESO (En presupuestación)", "🟢 GANADAS (Aprobadas)", "🔴 PERDIDAS (Descartadas)"],
                index=0
            )

            stage_filter = "cotizado" if "COTIZADOS" in sel_crm_stage else ("borrador" if "PROCESO" in sel_crm_stage else ("ganada" if "GANADAS" in sel_crm_stage else "perdida"))
            
            if stage_filter == "cotizado":
                cots_stage = cots_cotizadas
            elif stage_filter == "borrador":
                cots_stage = cots_en_proceso
            elif stage_filter == "ganada":
                cots_stage = cots_ganadas
            else:
                cots_stage = cots_perdidas

            if not cots_stage:
                st.info(f"No hay oportunidades registradas en la categoría **{sel_crm_stage}**.")
            else:
                for c in cots_stage:
                    with st.expander(f"💼 {c['folio']} ({c['revision']}) — {c['cliente']} | {c['proyecto']}", expanded=True):
                        crm_o1, crm_o2, crm_o3 = st.columns([2, 2, 1.5])
                        with crm_o1:
                            st.markdown(f"""
                            <b>Cliente:</b> {c['cliente']}<br/>
                            <b>Proyecto:</b> {c['proyecto']}<br/>
                            <b>Revisión Activa:</b> {c['revision']} ({'🔒 Congelada' if c['congelada'] else '✏️ Editable'})
                            """, unsafe_allow_html=True)
                        with crm_o2:
                            st.markdown(f"""
                            <b>Margen Aplicado:</b> {c['margen_porcentaje']*100:.0f}%<br/>
                            <b>Comisión Comercial:</b> {c['comision_porcentaje']*100:.0f}%<br/>
                            <b>Estatus Actual:</b> <b style="color:{BRAND_ORANGE};">{c['estatus']}</b>
                            """, unsafe_allow_html=True)
                        with crm_o3:
                            st.markdown("<p style='font-size:11px;font-weight:800;margin-bottom:4px;'>Acción Rápida CRM:</p>", unsafe_allow_html=True)
                            col_act_a, col_act_b = st.columns(2)
                            if col_act_a.button("🟢 Ganada", key=f"btn_win_{c['id']}", use_container_width=True):
                                conn = get_connection(); conn.execute("UPDATE cotizaciones SET estatus='Ganada' WHERE id=?", (c['id'],)); conn.commit(); conn.close()
                                st.success("¡Cotización marcada como GANADA!")
                                st.rerun()
                            if col_act_b.button("🔴 Perdida", key=f"btn_lost_{c['id']}", use_container_width=True):
                                conn = get_connection(); conn.execute("UPDATE cotizaciones SET estatus='Perdida' WHERE id=?", (c['id'],)); conn.commit(); conn.close()
                                st.warning("Cotización marcada como PERDIDA.")
                                st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # PESTAÑA 2: ANÁLISIS FINANCIERO DETALLADO DE COTIZACIÓN
    # ─────────────────────────────────────────────────────────────────────────
    # ─────────────────────────────────────────────────────────────────────────
    # PESTAÑA 2: ANÁLISIS FINANCIERO DETALLADO DE COTIZACIÓN
    # ─────────────────────────────────────────────────────────────────────────
    with dash_tab2:
        if not cotizaciones:
            st.info("ℹ️ No hay cotizaciones registradas actualmente en el sistema. Sube una cotización desde '2. Importador Excel' para analizar sus costos.")
        else:
            # Selector con HISTORIAL COMPLETO DE REVISIONES (R0, R1, R2...)
            import re
            cot_labels = {
                f"{'🔒 ' if c['congelada'] else '✏️ '}{re.sub(r'\\s*\\(R\\d+\\)$', '', c['folio']).strip()} ({c.get('revision','R0')}) — {c.get('cliente','—')} | {(c.get('proyecto') or '')[:40]}": c['id']
                for c in cotizaciones
            }
            selected_label = st.selectbox("📂 Seleccionar Cotización e Historial de Versión para Análisis", list(cot_labels.keys()), key="sel_analisis_ver")
            cot_id = cot_labels[selected_label]

            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT c.*, cl.nombre as cliente FROM cotizaciones c LEFT JOIN clientes cl ON c.cliente_id = cl.id WHERE c.id = ?", (cot_id,))
            cot_info = dict(cursor.fetchone())
            cursor.execute("SELECT * FROM cotizacion_partidas WHERE cotizacion_id = ? ORDER BY numero_partida", (cot_id,))
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()

            tipo_cambio     = cot_info['tipo_cambio_usd']
            margen_pct      = cot_info['margen_porcentaje']
            comision_pct    = cot_info['comision_porcentaje']
            proyecto_nombre = cot_info['proyecto']
            cliente_nombre  = cot_info.get('cliente') or 'J&D'
            folio           = cot_info['folio']
            revision        = cot_info['revision']
            gastos_totales  = cot_info['gastos_indirectos'] or 0.0

            partidas_data = [{"num":p['numero_partida'],"concepto":p['descripcion'],"mat":p['costo_mat'],
                              "mo":p['costo_mo'],"sup":p['costo_sup'],"sub":p['costo_sub'],"maq":p['costo_maq']} for p in rows]

            # ── CÁLCULOS FINANCIEROS ──
            total_mat  = sum(p['mat'] for p in partidas_data)
            total_mo   = sum(p['mo']  for p in partidas_data)
            total_sup  = sum(p['sup'] for p in partidas_data)
            total_sub  = sum(p['sub'] for p in partidas_data)
            total_maq  = sum(p['maq'] for p in partidas_data)
            total_hta  = total_mo * 0.03
            total_g    = gastos_totales
            cd_total   = total_mat + total_mo + total_sup + total_sub + total_maq + total_hta + total_g

            pv_antes_com = cd_total / (1 - margen_pct) if margen_pct < 1 else cd_total
            margen_monto = pv_antes_com - cd_total
            pv_final     = pv_antes_com / (1 - comision_pct) if comision_pct < 1 else pv_antes_com
            comision_monto = pv_final - pv_antes_com
            precio_usd   = pv_final / tipo_cambio if tipo_cambio > 0 else 0

            # ── CABECERA DEL PROYECTO ──
            st.markdown(f"""
            <div class="jd-section-header">
                <h2>{folio}</h2>
                <p>{proyecto_nombre} &nbsp;|&nbsp; Cliente: <strong>{cliente_nombre}</strong> &nbsp;|&nbsp; Revisión: <strong>{revision}</strong> &nbsp;|&nbsp; TC: <strong>${tipo_cambio:,.2f} MXN/USD</strong></p>
            </div>
            """, unsafe_allow_html=True)

            # ── KPI CARDS ──
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(jd_metric_card(
                    "Subtotal Costo Directo",
                    f"${cd_total:,.2f}",
                    "100% Base de Costo"
                ), unsafe_allow_html=True)
            with k2:
                st.markdown(jd_metric_card(
                    f"Margen de Utilidad ({margen_pct*100:.1f}%)",
                    f"${margen_monto:,.2f}",
                    f"P.V. s/ Comisión: ${pv_antes_com:,.2f}",
                    highlight=True
                ), unsafe_allow_html=True)
            with k3:
                st.markdown(jd_metric_card(
                    "Precio de Venta Final (MXN)",
                    f"${pv_final:,.2f}",
                    f"Comisión ({comision_pct*100:.1f}%): ${comision_monto:,.2f}"
                ), unsafe_allow_html=True)
            with k4:
                st.markdown(jd_metric_card(
                    f"Precio de Venta (USD @ ${tipo_cambio:,.2f})",
                    f"${precio_usd:,.2f} USD",
                    "Precio final en Dólares",
                    highlight=True
                ), unsafe_allow_html=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── DESGLOSE DE COSTO DIRECTO Y GRÁFICO ──
            col_tbl, col_chart = st.columns([3, 2])

            rubros = [
                {"Clave":"A","Rubro":"Materiales","Costo (MXN)":total_mat,"%":total_mat/cd_total if cd_total else 0},
                {"Clave":"B","Rubro":"Mano de Obra","Costo (MXN)":total_mo,"%":total_mo/cd_total if cd_total else 0},
                {"Clave":"C","Rubro":"Supervisión (30% MO)","Costo (MXN)":total_sup,"%":total_sup/cd_total if cd_total else 0},
                {"Clave":"D","Rubro":"Subcontratos","Costo (MXN)":total_sub,"%":total_sub/cd_total if cd_total else 0},
                {"Clave":"E","Rubro":"Maquinaria","Costo (MXN)":total_maq,"%":total_maq/cd_total if cd_total else 0},
                {"Clave":"F","Rubro":"Herramienta (3% MO)","Costo (MXN)":total_hta,"%":total_hta/cd_total if cd_total else 0},
                {"Clave":"G","Rubro":"Gastos Generales","Costo (MXN)":total_g,"%":total_g/cd_total if cd_total else 0},
            ]
            df_rubros = pd.DataFrame(rubros)

            with col_tbl:
                st.markdown("""<div class="jd-section-header"><h2>Resumen de Costo Directo por Rubro</h2></div>""", unsafe_allow_html=True)
                st.dataframe(
                    df_rubros.style.format({'Costo (MXN)': '${:,.2f}', '%': '{:.2%}'})
                                  .set_properties(**{'font-family': 'Montserrat, sans-serif', 'font-size': '13px'}),
                    use_container_width=True, height=300
                )

            with col_chart:
                st.markdown("""<div class="jd-section-header"><h2>Distribución del Costo Directo</h2></div>""", unsafe_allow_html=True)
                df_donut = df_rubros[df_rubros['Costo (MXN)'] > 0]
                fig = px.pie(
                    df_donut, values='Costo (MXN)', names='Rubro', hole=0.45,
                    color_discrete_sequence=JD_CHART_COLORS
                )
                fig.update_layout(
                    margin=dict(t=5, b=5, l=5, r=5),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Montserrat, sans-serif', color=BRAND_CHARCOAL),
                    legend=dict(font=dict(size=11, family='Montserrat, sans-serif')),
                    showlegend=True
                )
                fig.update_traces(textfont=dict(family='Montserrat, sans-serif', size=11))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("<hr>", unsafe_allow_html=True)

            # ── TABLA MAESTRA DE ANÁLISIS POR PARTIDAS ──
            st.markdown("""<div class="jd-section-header"><h2>Tabla Maestra de Análisis por Partidas</h2><p>Ponderación de herramienta y gastos por partida — Costo Directo Total — Precio de Venta</p></div>""", unsafe_allow_html=True)

            sum_cost1 = sum(p['mat'] + p['mo'] + p['sup'] for p in partidas_data)
            rows_analisis = []
            for p in partidas_data:
                cost1 = p['mat'] + p['mo'] + p['sup']
                pct = cost1 / sum_cost1 if sum_cost1 > 0 else 0.0
                hta_p   = total_hta * pct
                gasto_p = total_g  * pct
                cd_p    = cost1 + p['sub'] + p['maq'] + hta_p + gasto_p
                pct_cd  = cd_p / cd_total if cd_total > 0 else 0.0
                pv_p    = cd_p / ((1 - margen_pct) * (1 - comision_pct)) if (1-margen_pct)*(1-comision_pct) > 0 else cd_p
                rows_analisis.append({
                    "#": p['num'], "Concepto": p['concepto'][:60]+"..." if len(p['concepto'])>60 else p['concepto'],
                    "MAT": p['mat'], "MO": p['mo'], "SUP": p['sup'], "COST-1": cost1,
                    "% COST-1": pct, "SUB": p['sub'], "MAQ": p['maq'],
                    "HTA": hta_p, "GASTOS": gasto_p, "COSTO TOTAL CD": cd_p,
                    "% TOTAL": pct_cd, "PRECIO VENTA (MXN)": pv_p
                })

            df_analisis = pd.DataFrame(rows_analisis)
            money_cols = ['MAT','MO','SUP','COST-1','SUB','MAQ','HTA','GASTOS','COSTO TOTAL CD','PRECIO VENTA (MXN)']
            pct_cols   = ['% COST-1','% TOTAL']
            fmt = {c: '${:,.2f}' for c in money_cols}
            fmt.update({c: '{:.1%}' for c in pct_cols})

            st.dataframe(df_analisis.style.format(fmt), use_container_width=True, height=300)

            # ── GRÁFICO DE BARRAS DE PRECIO DE VENTA POR PARTIDA ──
            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("""<div class="jd-section-header"><h2>Comparativa: Costo Directo vs Precio de Venta por Partida</h2></div>""", unsafe_allow_html=True)
            
            fig_bar = go.Figure()
            conceptos = [r['Concepto'] for r in rows_analisis]
            fig_bar.add_trace(go.Bar(name='Costo Directo', x=conceptos, y=[r['COSTO TOTAL CD'] for r in rows_analisis],
                                     marker_color=BRAND_CHARCOAL_MED, text=[f"${v:,.0f}" for v in [r['COSTO TOTAL CD'] for r in rows_analisis]],
                                     textposition='outside'))
            fig_bar.add_trace(go.Bar(name='Precio de Venta', x=conceptos, y=[r['PRECIO VENTA (MXN)'] for r in rows_analisis],
                                     marker_color=BRAND_ORANGE, text=[f"${v:,.0f}" for v in [r['PRECIO VENTA (MXN)'] for r in rows_analisis]],
                                     textposition='outside'))
            fig_bar.update_layout(
                barmode='group',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Montserrat, sans-serif', color=BRAND_CHARCOAL),
                xaxis=dict(tickfont=dict(size=10), gridcolor='#E2E8F0'),
                yaxis=dict(tickprefix="$", gridcolor='#E2E8F0'),
                margin=dict(t=20, b=20, l=10, r=10),
                height=350
            )
            st.plotly_chart(fig_bar, use_container_width=True)

