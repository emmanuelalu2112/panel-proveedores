from streamlit.runtime.scriptrunner import RerunException, get_script_run_ctx
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Usuarios y Login ---
usuarios = {
    "a01_user": ["claveA01", "PROVEEDOR A01"],
    "a02_user": ["claveA02", "PROVEEDOR A02"],
    "a03_user": ["claveA03", "PROVEEDOR A03"]
}

st.title("Panel de Proveedores")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""
if "proveedor" not in st.session_state:
    st.session_state.proveedor = ""

if not st.session_state.logged_in:
    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")

    if st.button("Ingresar"):
        if usuario in usuarios and clave == usuarios[usuario][0]:
            st.session_state.logged_in = True
            st.session_state.usuario = usuario
            st.session_state.proveedor = usuarios[usuario][1]
            st.success(f"Bienvenido {st.session_state.proveedor}")
            raise RerunException(get_script_run_ctx())
        else:
            st.error("Usuario o contraseña incorrectos")

else:
    proveedor = st.session_state.proveedor
    st.success(f"Bienvenido {proveedor}")

    # --- Leer datos del Google Sheet ---
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="Hoja_1")

    df["FECHA ENTREGA"] = pd.to_datetime(df["FECHA ENTREGA"], dayfirst=True, errors='coerce')
    df["__row_index"] = df.index

    # --- Filtrar por proveedor actual ---
    df_proveedor = df[df["NOMBRE PROVEEDOR"] == proveedor].copy()

    columnas_editables = ["FECHA ENTREGA", "CANTIDAD ENTREGADA"]

    # --- Tabs para agregar/modificar/métricas ---
    tab1, tab2, tab3 = st.tabs(["➕ Agregar entrega", "✏️ Modificar entrega", "📊 Métricas y Análisis"])

    # === TAB 1: AGREGAR ===
    with tab1:
        df_agregar = df_proveedor[df_proveedor["FECHA ENTREGA"].isna() & df_proveedor["CANTIDAD ENTREGADA"].isna()]
        st.subheader("Cargar nuevas entregas")

        if df_agregar.empty:
            st.info("No hay entregas pendientes para completar.")
        else:
            df_editado = st.data_editor(
                df_agregar,
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "FECHA ENTREGA": st.column_config.DateColumn("Fecha de Entrega"),
                    "CANTIDAD ENTREGADA": st.column_config.NumberColumn("Cantidad Entregada", min_value=0, step=1)
                },
                disabled=[col for col in df_agregar.columns if col not in columnas_editables],
                key="editor_agregar"
            )

            if st.button("Guardar nuevas entregas"):
                df_actualizado = df.copy()
                for _, fila in df_editado.iterrows():
                    idx = fila["__row_index"]
                    df_actualizado.loc[idx, "FECHA ENTREGA"] = fila["FECHA ENTREGA"]
                    df_actualizado.loc[idx, "CANTIDAD ENTREGADA"] = fila["CANTIDAD ENTREGADA"]

                df_actualizado.drop(columns="__row_index", inplace=True)
                conn.update(worksheet="Hoja_1", data=df_actualizado)
                st.success("Nuevas entregas guardadas correctamente.")

    # === TAB 2: MODIFICAR ===
    with tab2:
        df_modificar = df_proveedor[df_proveedor["FECHA ENTREGA"].notna() | df_proveedor["CANTIDAD ENTREGADA"].notna()]
        st.subheader("Modificar entregas registradas")

        if df_modificar.empty:
            st.info("No hay entregas cargadas aún.")
        else:
            df_editado = st.data_editor(
                df_modificar,
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "FECHA ENTREGA": st.column_config.DateColumn("Fecha de Entrega"),
                    "CANTIDAD ENTREGADA": st.column_config.NumberColumn("Cantidad Entregada", min_value=0, step=1)
                },
                disabled=[col for col in df_modificar.columns if col not in columnas_editables],
                key="editor_modificar"
            )

            if st.button("Guardar modificaciones"):
                df_actualizado = df.copy()
                for _, fila in df_editado.iterrows():
                    idx = fila["__row_index"]
                    df_actualizado.loc[idx, "FECHA ENTREGA"] = fila["FECHA ENTREGA"]
                    df_actualizado.loc[idx, "CANTIDAD ENTREGADA"] = fila["CANTIDAD ENTREGADA"]

                df_actualizado.drop(columns="__row_index", inplace=True)
                conn.update(worksheet="Hoja_1", data=df_actualizado)
                st.success("Modificaciones guardadas correctamente.")

    # === TAB 3: MÉTRICAS Y ANÁLISIS ===
    with tab3:
        st.subheader("📊 Análisis de Desempeño")

        # Datos con entregas completadas
        df_entregado = df_proveedor[
            df_proveedor["FECHA ENTREGA"].notna() &
            df_proveedor["CANTIDAD ENTREGADA"].notna()
        ].copy()

        if df_entregado.empty:
            st.info("No hay datos de entregas para mostrar métricas.")
        else:
            # === MÉTRICAS PRINCIPALES ===
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_entregas = len(df_entregado)
                st.metric("Total Entregas", total_entregas)

            with col2:
                cantidad_total = df_entregado["CANTIDAD ENTREGADA"].sum()
                st.metric("Cantidad Total", f"{cantidad_total:,.0f}")

            with col3:
                promedio_cantidad = df_entregado["CANTIDAD ENTREGADA"].mean()
                st.metric("Promedio por Entrega", f"{promedio_cantidad:.1f}")

            with col4:
                # Entregas pendientes
                pendientes = len(df_proveedor) - len(df_entregado)
                st.metric("Entregas Pendientes", pendientes)

            st.markdown("---")

            # === GRÁFICOS ===

            # Preparar datos para gráficos
            df_chart = df_entregado.copy()
            df_chart["Mes"] = df_chart["FECHA ENTREGA"].dt.to_period("M").astype(str)
            df_chart["Semana"] = df_chart["FECHA ENTREGA"].dt.isocalendar().week
            df_chart["Año-Semana"] = df_chart["FECHA ENTREGA"].dt.strftime("%Y-S%U")

            # === GRÁFICO 1: EVOLUCIÓN TEMPORAL ===
            st.subheader("📈 Evolución de Entregas en el Tiempo")

            # Selector de período
            periodo = st.selectbox("Seleccionar período:", ["Diario", "Semanal", "Mensual"])

            if periodo == "Diario":
                fig_timeline = px.line(
                    df_chart.sort_values("FECHA ENTREGA"),
                    x="FECHA ENTREGA",
                    y="CANTIDAD ENTREGADA",
                    title="Cantidad Entregada por Día",
                    markers=True
                )
            elif periodo == "Semanal":
                df_semanal = df_chart.groupby("Año-Semana")["CANTIDAD ENTREGADA"].sum().reset_index()
                fig_timeline = px.bar(
                    df_semanal,
                    x="Año-Semana",
                    y="CANTIDAD ENTREGADA",
                    title="Cantidad Entregada por Semana"
                )
            else:  # Mensual
                df_mensual = df_chart.groupby("Mes")["CANTIDAD ENTREGADA"].sum().reset_index()
                fig_timeline = px.bar(
                    df_mensual,
                    x="Mes",
                    y="CANTIDAD ENTREGADA",
                    title="Cantidad Entregada por Mes"
                )

            fig_timeline.update_layout(height=400)
            st.plotly_chart(fig_timeline, use_container_width=True)

            # === GRÁFICO 2: DISTRIBUCIÓN DE CANTIDADES ===
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📊 Distribución de Cantidades")
                fig_hist = px.histogram(
                    df_chart,
                    x="CANTIDAD ENTREGADA",
                    nbins=10,
                    title="Frecuencia por Cantidad Entregada"
                )
                fig_hist.update_layout(height=350)
                st.plotly_chart(fig_hist, use_container_width=True)

            with col2:
                st.subheader("🥧 Top Productos/Servicios")
                if "PRODUCTO" in df_chart.columns:
                    top_productos = df_chart.groupby("PRODUCTO")["CANTIDAD ENTREGADA"].sum().sort_values(ascending=False).head(5)
                    fig_pie = px.pie(
                        values=top_productos.values,
                        names=top_productos.index,
                        title="Top 5 Productos por Cantidad"
                    )
                    fig_pie.update_layout(height=350)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No hay columna 'PRODUCTO' para analizar")

            # === TABLA RESUMEN ===
            st.subheader("📋 Resumen por Período")

            if len(df_chart) > 0:
                # Resumen mensual
                resumen_mensual = df_chart.groupby("Mes").agg({
                    "CANTIDAD ENTREGADA": ["sum", "mean", "count"],
                    "FECHA ENTREGA": ["min", "max"]
                }).round(2)

                # Aplanar columnas
                resumen_mensual.columns = ["Total", "Promedio", "N° Entregas", "Primera Entrega", "Última Entrega"]
                resumen_mensual = resumen_mensual.reset_index()

                st.dataframe(resumen_mensual, use_container_width=True)

            # === ANÁLISIS DE TENDENCIAS ===
            if len(df_chart) >= 3:  # Necesitamos al menos 3 puntos
                st.subheader("📊 Análisis de Tendencia")

                # Calcular tendencia simple (últimas 3 entregas vs primeras 3)
                df_ordenado = df_chart.sort_values("FECHA ENTREGA")
                primeras_3 = df_ordenado.head(3)["CANTIDAD ENTREGADA"].mean()
                ultimas_3 = df_ordenado.tail(3)["CANTIDAD ENTREGADA"].mean()

                cambio_pct = ((ultimas_3 - primeras_3) / primeras_3 * 100) if primeras_3 > 0 else 0

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Promedio Inicial",
                        f"{primeras_3:.1f}",
                        help="Promedio de las primeras 3 entregas"
                    )

                with col2:
                    st.metric(
                        "Promedio Reciente",
                        f"{ultimas_3:.1f}",
                        delta=f"{cambio_pct:+.1f}%",
                        help="Promedio de las últimas 3 entregas"
                    )

                with col3:
                    # Estado de la tendencia
                    if cambio_pct > 10:
                        estado = "📈 Creciente"
                        color = "normal"
                    elif cambio_pct < -10:
                        estado = "📉 Decreciente"
                        color = "inverse"
                    else:
                        estado = "➡️ Estable"
                        color = "off"

                    st.metric("Tendencia", estado)

    # --- Botón para cerrar sesión ---
    st.markdown("---")
    if st.button("Cerrar sesión 🔒"):
        st.session_state.logged_in = False
        st.session_state.usuario = ""
        st.session_state.proveedor = ""
        st.success("Sesión cerrada.")
        raise RerunException(get_script_run_ctx())
