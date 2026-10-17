"""
Sistema de Gestión Avícola - Interfaz Web (Streamlit)
Versión optimizada: los cálculos que se repetían en varias pantallas
(total de huevos, promedio, gastos por categoría, líneas de PDF) ahora
viven en UNA sola función cada uno, en la sección de "AYUDANTES" de
más abajo. El resto del archivo los reutiliza en vez de recalcularlos.
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import date
from fpdf import FPDF

ARCHIVO = "datos.json"

st.set_page_config(page_title="Sistema Avícola", page_icon="🐔", layout="wide")

st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        border: 2px solid black;
        border-radius: 14px;
        padding: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# AYUDANTES (funciones reutilizables)
# Cada una de estas resume un cálculo que antes se repetía escrito a
# mano en 2 o 3 pantallas distintas. Ahora cada pantalla solo LLAMA a
# la función, en vez de repetir la fórmula.
# ============================================================

def seleccionar_por_indice(lista, etiqueta, texto_item, key):
    """Muestra un selectbox para elegir UN elemento de una lista por su
    posición (útil para listas sin código único, como recolecciones,
    compras o gastos). Devuelve (índice, elemento), o (None, None) si
    la lista está vacía."""
    if not lista:
        return None, None
    opciones = [f"{i}: {texto_item(item)}" for i, item in enumerate(lista)]
    seleccion = st.selectbox(etiqueta, opciones, key=key)
    idx = int(seleccion.split(":")[0])
    return idx, lista[idx]


def buenos_danados(datos):
    """Suma por separado los huevos buenos y dañados de UN gallinero."""
    buenos = sum(r["buenos"] for r in datos["recolecciones"])
    danados = sum(r["danados"] for r in datos["recolecciones"])
    return buenos, danados


def total_huevos(datos):
    """Total de huevos (buenos + dañados) de UN gallinero."""
    b, d = buenos_danados(datos)
    return b + d


def promedio_postura(datos):
    """Huevos por gallina de UN gallinero. Evita la división por cero
    si todavía no tiene aves registradas."""
    aves = datos["aves"]
    return total_huevos(datos) / aves if aves > 0 else 0


def totales_granja(gallineros):
    """Huevos buenos y dañados sumando TODOS los gallineros a la vez."""
    buenos = sum(r["buenos"] for g in gallineros.values() for r in g["recolecciones"])
    danados = sum(r["danados"] for g in gallineros.values() for r in g["recolecciones"])
    return buenos, danados


def gastos_por_categoria(alimento):
    """Devuelve {'Medicina': total, 'Empaque': total, 'Otro': total},
    sumando el campo 'valor' de cada gasto según su categoría. Los
    gastos viejos sin categoría guardada cuentan como 'Otro'."""
    totales = {"Medicina": 0, "Empaque": 0, "Otro": 0}
    for g in alimento["gastos_adicionales"]:
        categoria = g.get("categoria", "Otro")
        totales[categoria] = totales.get(categoria, 0) + g["valor"]
    return totales


def pdf_linea(pdf, texto, negrita=False, tamano=11, salto_despues=0):
    """Escribe una línea de texto en el PDF. Antes cada línea necesitaba
    2 instrucciones (set_font + cell); ahora es 1 sola llamada."""
    pdf.set_font("Helvetica", "B" if negrita else "", tamano)
    pdf.cell(0, 8 if negrita else 7, texto, ln=True)
    if salto_despues:
        pdf.ln(salto_despues)


# ============================================================
# PERSISTENCIA
# ============================================================

def alimento_vacio():
    return {
        "inventario_kg": 0.0,
        "precio_kg": 0.0,
        "compras": [],
        "consumos": [],
        "gastos_adicionales": [],
    }


def cargar_datos():
    if os.path.exists(ARCHIVO):
        try:
            with open(ARCHIVO, "r", encoding="utf-8") as f:
                contenido = json.load(f)
        except Exception:
            contenido = {}
    else:
        contenido = {}

    if "gallineros" in contenido or "alimento" in contenido:
        gallineros = contenido.get("gallineros", {})
        alimento = contenido.get("alimento", alimento_vacio())
    else:
        gallineros = contenido  # formato viejo: todo el archivo eran gallineros
        alimento = alimento_vacio()

    alimento.setdefault("gastos_adicionales", [])
    return gallineros, alimento


def guardar_datos():
    contenido = {
        "gallineros": st.session_state.gallineros,
        "alimento": st.session_state.alimento,
    }
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(contenido, f, indent=4, ensure_ascii=False)


if "datos_cargados" not in st.session_state:
    gallineros, alimento = cargar_datos()
    st.session_state.gallineros = gallineros
    st.session_state.alimento = alimento
    st.session_state.datos_cargados = True

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "pagina" not in st.session_state:
    st.session_state.pagina = "Dashboard"


# ============================================================
# GENERACIÓN DE PDFs (ahora usando pdf_linea para cada renglón)
# ============================================================

def pdf_a_bytes(pdf):
    return bytes(pdf.output())


def generar_pdf_resumen_general():
    gallineros = st.session_state.gallineros
    alimento = st.session_state.alimento

    pdf = FPDF()
    pdf.add_page()
    pdf_linea(pdf, "Resumen General - Sistema Avicola", negrita=True, tamano=16)
    pdf_linea(pdf, f"Fecha de generacion: {date.today()}", salto_despues=4)

    total_aves = sum(g["aves"] for g in gallineros.values())
    total_b, total_d = totales_granja(gallineros)

    pdf_linea(pdf, "Datos generales", negrita=True, tamano=12)
    pdf_linea(pdf, f"Gallineros activos: {len(gallineros)}")
    pdf_linea(pdf, f"Total de aves: {total_aves}")
    pdf_linea(pdf, f"Total de huevos recolectados: {total_b + total_d}")
    pdf_linea(pdf, f"Inventario de alimento: {alimento['inventario_kg']:.1f} kg", salto_despues=4)

    pdf_linea(pdf, "Gallineros", negrita=True, tamano=12)
    if gallineros:
        for codigo, datos in gallineros.items():
            pdf_linea(pdf, f"{codigo} - {datos['nombre']} | Aves: {datos['aves']} | Huevos: {total_huevos(datos)}", tamano=10)
    else:
        pdf_linea(pdf, "Sin gallineros registrados.", tamano=10)
    pdf.ln(4)

    gasto_alimento = sum(c["costo"] for c in alimento["compras"])
    gastos_cat = gastos_por_categoria(alimento)

    pdf_linea(pdf, "Presupuesto por categoria", negrita=True, tamano=12)
    pdf_linea(pdf, f"Alimento: ${gasto_alimento:,.0f}")
    pdf_linea(pdf, f"Medicinas: ${gastos_cat['Medicina']:,.0f}")
    pdf_linea(pdf, f"Empaques: ${gastos_cat['Empaque']:,.0f}")
    pdf_linea(pdf, f"Otros: ${gastos_cat['Otro']:,.0f}")
    pdf_linea(pdf, f"Total: ${gasto_alimento + sum(gastos_cat.values()):,.0f}")

    return pdf_a_bytes(pdf)


def generar_pdf_resumen_gallinero(codigo):
    alimento = st.session_state.alimento
    datos = st.session_state.gallineros[codigo]

    huevos = total_huevos(datos)
    promedio = promedio_postura(datos)
    kilos_consumidos = sum(c["kilos"] for c in alimento["consumos"] if c["codigo"] == codigo)
    costo_estimado = kilos_consumidos * alimento["precio_kg"]

    pdf = FPDF()
    pdf.add_page()
    pdf_linea(pdf, f"Resumen del Gallinero {codigo}", negrita=True, tamano=16)
    pdf_linea(pdf, f"Fecha de generacion: {date.today()}", salto_despues=4)

    pdf_linea(pdf, "Datos generales", negrita=True, tamano=12)
    pdf_linea(pdf, f"Nombre: {datos['nombre']}")
    pdf_linea(pdf, f"Aves: {datos['aves']}")
    pdf_linea(pdf, f"Huevos totales: {huevos}")
    pdf_linea(pdf, f"Promedio de postura por gallina: {promedio:.2f}")
    pdf_linea(pdf, f"Alimento consumido: {kilos_consumidos:.1f} kg")
    pdf_linea(pdf, f"Costo estimado en alimento: ${costo_estimado:,.0f}", salto_despues=4)

    pdf_linea(pdf, "Historico de recoleccion", negrita=True, tamano=12)
    if datos["recolecciones"]:
        for r in datos["recolecciones"]:
            pdf_linea(pdf, f"{r['fecha']} - Buenos: {r['buenos']} | Danados: {r['danados']}", tamano=10)
    else:
        pdf_linea(pdf, "Sin registros de recoleccion.", tamano=10)

    return pdf_a_bytes(pdf)


# ============================================================
# PANTALLA: Login
# ============================================================

def pantalla_login():
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("Accede")
        st.caption("Inicia sesión para continuar")
        correo = st.text_input("CORREO ELECTRÓNICO", placeholder="hola@sitioincreible.com")
        clave = st.text_input("CONTRASEÑA", type="password", placeholder="******")

        if st.button("Acceder", use_container_width=True, type="primary"):
            if correo.strip() == "" or clave.strip() == "":
                st.error("Completa ambos campos.")
            else:
                st.session_state.autenticado = True
                st.rerun()


# ============================================================
# PANTALLA: Dashboard Principal
# ============================================================

def pantalla_dashboard():
    st.title("Dashboard Principal")
    gallineros = st.session_state.gallineros
    alimento = st.session_state.alimento

    total_buenos, total_danados = totales_granja(gallineros)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gallineros Activos", len(gallineros))
    c2.metric("Total Aves", sum(g["aves"] for g in gallineros.values()))
    c3.metric("Huevos buenos", total_buenos)
    c4.metric("Alimento Disponible", f"{alimento['inventario_kg']:.1f} kg")

    st.write("")
    col_chart, col_side = st.columns([3, 1])

    with col_chart:
        st.subheader("Producción registrada")
        buenos_lista = [r["buenos"] for g in gallineros.values() for r in g["recolecciones"]]
        danados_lista = [r["danados"] for g in gallineros.values() for r in g["recolecciones"]]

        if buenos_lista:
            df = pd.DataFrame({"Buenos": buenos_lista, "Dañados": danados_lista})
            st.line_chart(df, color=["#000000", "#c0392b"])
        else:
            st.info("Todavía no hay recolecciones registradas.")

    with col_side:
        st.subheader("Alertas recientes")
        if not gallineros:
            st.warning("No hay gallineros registrados.")
        if alimento["inventario_kg"] < 10:
            st.warning("¡Atención! Stock de alimento bajo.")
        if gallineros and alimento["inventario_kg"] >= 10:
            st.success("Todo en orden.")

        st.subheader("Acciones rápidas")
        if st.button("Registrar Postura", use_container_width=True):
            st.session_state.pagina = "Registrar Postura"
            st.rerun()
        if st.button("Registrar Gallinero", use_container_width=True):
            st.session_state.pagina = "Gallineros"
            st.rerun()


# ============================================================
# PANTALLA: Gestión Gallineros
# RF01,02,03,05,06,23,36,41,42 + capacidad/ocupación, estado,
# tamaño, bitácora de movimientos y duplicar como plantilla.
# ============================================================

def pantalla_gallineros():
    st.title("Gestión Gallineros")
    gallineros = st.session_state.gallineros

    with st.expander("➕ Registrar nuevo gallinero", expanded=(len(gallineros) == 0)):
        codigo = st.text_input("Código", key="in_codigo")
        nombre = st.text_input("Nombre", key="in_nombre")
        aves = st.number_input("Cantidad de aves", min_value=0, step=1, key="in_aves")
        capacidad = st.number_input(
            "Capacidad máxima de aves", min_value=0, step=1, key="in_capacidad",
            help="Cuántas aves puede albergar este gallinero como máximo."
        )

        if st.button("Guardar gallinero"):
            if codigo.strip() == "":
                st.error("El código no puede estar vacío.")
            elif codigo in gallineros:
                st.error(f"Ya existe un gallinero con el código '{codigo}'.")
            else:
                gallineros[codigo] = {
                    "nombre": nombre,
                    "aves": int(aves),
                    "capacidad_maxima": int(capacidad),
                    "estado": "Activo",  # estado manual, el usuario lo cambia cuando quiera
                    "recolecciones": [],
                    "fecha_creacion": str(date.today()),
                    "movimientos": [{"fecha": str(date.today()), "tipo": "Alta inicial", "cantidad": int(aves)}],
                }
                guardar_datos()
                st.success(f"Gallinero '{nombre}' ({codigo}) registrado.")
                st.rerun()

    if gallineros:
        with st.expander("✏️ Modificar, dar de baja, duplicar o eliminar un gallinero"):
            codigo_sel = st.selectbox("Selecciona un gallinero", list(gallineros.keys()), key="editar_codigo")
            datos_sel = gallineros[codigo_sel]

            st.markdown(f"**Editando:** {datos_sel['nombre']} ({codigo_sel}) — {datos_sel['aves']} aves actuales")

            st.markdown("##### Modificar datos")
            nuevo_nombre = st.text_input("Nuevo nombre", value=datos_sel["nombre"], key="editar_nombre")
            nuevas_aves = st.number_input(
                "Nueva cantidad de aves", min_value=0, step=1, value=datos_sel["aves"], key="editar_aves"
            )
            nueva_capacidad = st.number_input(
                "Capacidad máxima de aves", min_value=0, step=1,
                value=datos_sel.get("capacidad_maxima", 0), key="editar_capacidad"
            )
            opciones_estado = ["Activo", "Inactivo", "Pausado"]
            estado_actual = datos_sel.get("estado", "Activo")
            nuevo_estado = st.selectbox(
                "Estado", opciones_estado,
                index=opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 0,
                key="editar_estado",
            )
            if st.button("Guardar cambios"):
                diferencia = int(nuevas_aves) - datos_sel["aves"]
                datos_sel["nombre"] = nuevo_nombre
                datos_sel["aves"] = int(nuevas_aves)
                datos_sel["capacidad_maxima"] = int(nueva_capacidad)
                datos_sel["estado"] = nuevo_estado
                if diferencia != 0:
                    datos_sel.setdefault("movimientos", []).append(
                        {"fecha": str(date.today()), "tipo": "Ajuste manual", "cantidad": diferencia}
                    )
                guardar_datos()
                st.success("Gallinero actualizado.")
                st.rerun()

            st.divider()
            st.markdown("##### Dar de baja aves (venta o muerte)")
            baja = st.number_input("Cantidad de aves a dar de baja", min_value=0, step=1, key="baja_aves")
            if st.button("Registrar baja"):
                if baja <= 0:
                    st.error("La cantidad debe ser mayor a 0.")
                elif baja > datos_sel["aves"]:
                    st.error("No puedes dar de baja más aves de las que hay disponibles.")
                else:
                    datos_sel["aves"] -= int(baja)
                    datos_sel.setdefault("movimientos", []).append(
                        {"fecha": str(date.today()), "tipo": "Baja", "cantidad": -int(baja)}
                    )
                    guardar_datos()
                    st.success(f"Se dieron de baja {int(baja)} aves.")
                    st.rerun()

            st.markdown("##### Historial de movimientos de aves")
            movimientos = datos_sel.get("movimientos", [])
            if movimientos:
                st.dataframe(movimientos, use_container_width=True, hide_index=True)
            else:
                st.caption("Sin movimientos registrados (gallinero creado antes de esta función).")

            st.divider()
            st.markdown("##### Duplicar como plantilla")
            st.caption("Crea un gallinero nuevo copiando nombre y capacidad (sin recolecciones ni historial).")
            nuevo_codigo_dup = st.text_input("Código para el nuevo gallinero", key="dup_codigo")
            if st.button("📑 Duplicar este gallinero"):
                if nuevo_codigo_dup.strip() == "":
                    st.error("Escribe un código para el nuevo gallinero.")
                elif nuevo_codigo_dup in gallineros:
                    st.error(f"Ya existe un gallinero con el código '{nuevo_codigo_dup}'.")
                else:
                    gallineros[nuevo_codigo_dup] = {
                        "nombre": f"{datos_sel['nombre']} (copia)",
                        "aves": 0,
                        "capacidad_maxima": datos_sel.get("capacidad_maxima", 0),
                        "recolecciones": [],
                        "fecha_creacion": str(date.today()),
                        "movimientos": [{"fecha": str(date.today()), "tipo": "Alta inicial", "cantidad": 0}],
                    }
                    guardar_datos()
                    st.success(f"Gallinero '{nuevo_codigo_dup}' creado como plantilla.")
                    st.rerun()

            st.divider()
            st.markdown("##### Eliminar gallinero")
            confirmar = st.checkbox("Confirmo que quiero eliminar este gallinero permanentemente", key="confirmar_eliminar")
            if st.button("🗑️ Eliminar gallinero", disabled=not confirmar):
                del gallineros[codigo_sel]
                guardar_datos()
                st.success("Gallinero eliminado.")
                st.rerun()

    st.subheader("Lista de gallineros activos")
    col_busqueda, col_orden = st.columns([2, 1])
    busqueda = col_busqueda.text_input("🔍 Buscar por nombre o código", key="busqueda_gallinero")
    orden = col_orden.selectbox(
        "Ordenar por",
        ["Código (A-Z)", "Código (Z-A)", "Nombre (A-Z)", "Nombre (Z-A)"],
        key="orden_gallineros",
    )

    if not gallineros:
        st.info("No hay gallineros registrados todavía.")
        return

    codigos_ordenados = list(gallineros.keys())
    if orden == "Código (A-Z)":
        codigos_ordenados.sort()
    elif orden == "Código (Z-A)":
        codigos_ordenados.sort(reverse=True)
    elif orden == "Nombre (A-Z)":
        codigos_ordenados.sort(key=lambda c: gallineros[c]["nombre"].lower())
    else:
        codigos_ordenados.sort(key=lambda c: gallineros[c]["nombre"].lower(), reverse=True)

    filas = []
    for codigo in codigos_ordenados:
        datos = gallineros[codigo]
        if busqueda and busqueda.lower() not in codigo.lower() and busqueda.lower() not in datos["nombre"].lower():
            continue

        buenos, danados = buenos_danados(datos)
        total = buenos + danados
        porcentaje = f"{(buenos / total * 100):.0f}%" if total > 0 else "—"
        ultima = datos["recolecciones"][-1]["fecha"] if datos["recolecciones"] else "—"

        capacidad = datos.get("capacidad_maxima", 0)
        if capacidad > 0:
            ocupacion = f"{(datos['aves'] / capacidad * 100):.0f}%"
            if datos["aves"] > capacidad:
                ocupacion += " ⚠️"
        else:
            ocupacion = "—"

        # Estado MANUAL: lo decide el usuario en "Modificar...", no se calcula solo.
        iconos_estado = {"Activo": "🟢 Activo", "Inactivo": "🔴 Inactivo", "Pausado": "🟡 Pausado"}
        estado = iconos_estado.get(datos.get("estado", "Activo"), "—")

        if datos["aves"] < 20:
            tamano = "Pequeño"
        elif datos["aves"] <= 50:
            tamano = "Mediano"
        else:
            tamano = "Grande"

        filas.append({
            "Código": codigo, "Nombre": datos["nombre"], "Aves": datos["aves"],
            "Tamaño": tamano, "Ocupación": ocupacion, "Estado": estado,
            "% Producción buena": porcentaje, "Últ. Recolección": ultima,
        })

    if filas:
        st.dataframe(filas, use_container_width=True, hide_index=True)
    else:
        st.info("No se encontró ningún gallinero con ese criterio de búsqueda.")


# ============================================================
# PANTALLA: Registro de Postura (RF07, RF28, RF29)
# ============================================================

def pantalla_postura():
    st.title("Registro de Postura")
    gallineros = st.session_state.gallineros

    if not gallineros:
        st.warning("Primero registra al menos un gallinero en la sección 'Gallineros'.")
        return

    codigo = st.selectbox("Gallinero", list(gallineros.keys()))
    fecha = st.date_input("Fecha")

    col1, col2 = st.columns(2)
    buenos = col1.number_input("Huevos buenos", min_value=0, step=1)
    danados = col2.number_input("Huevos dañados", min_value=0, step=1)

    if st.button("Guardar recolección", use_container_width=True, type="primary"):
        gallineros[codigo]["recolecciones"].append({"fecha": str(fecha), "buenos": int(buenos), "danados": int(danados)})
        guardar_datos()
        st.success("Recolección registrada correctamente.")

    with st.expander("✏️ Modificar o eliminar una recolección existente"):
        codigo_r = st.selectbox("Gallinero", list(gallineros.keys()), key="editar_postura_codigo")
        recolecciones = gallineros[codigo_r]["recolecciones"]

        idx_r, registro = seleccionar_por_indice(
            recolecciones, "Selecciona una recolección",
            lambda r: f"{r['fecha']} - Buenos: {r['buenos']} - Dañados: {r['danados']}", key="postura_sel",
        )

        if registro is None:
            st.info("Este gallinero no tiene recolecciones registradas.")
        else:
            nuevos_buenos = st.number_input("Huevos buenos", min_value=0, step=1, value=registro["buenos"], key="editar_buenos")
            nuevos_danados = st.number_input("Huevos dañados", min_value=0, step=1, value=registro["danados"], key="editar_danados")

            colA, colB = st.columns(2)
            if colA.button("Guardar cambios"):
                registro["buenos"] = int(nuevos_buenos)
                registro["danados"] = int(nuevos_danados)
                guardar_datos()
                st.success("Recolección actualizada.")
                st.rerun()
            if colB.button("🗑️ Eliminar esta recolección"):
                recolecciones.pop(idx_r)
                guardar_datos()
                st.success("Recolección eliminada.")
                st.rerun()


# ============================================================
# PANTALLA: Producción (RF10, RF11, RF38, RF43, RF44 + ranking/gráfica)
# ============================================================

def pantalla_produccion():
    st.title("Producción")
    gallineros = st.session_state.gallineros

    if not gallineros:
        st.info("No hay gallineros registrados todavía.")
        return

    if len(gallineros) > 1:
        huevos_por_gallinero = {codigo: total_huevos(g) for codigo, g in gallineros.items()}
        if any(huevos_por_gallinero.values()):
            mejor = max(huevos_por_gallinero, key=huevos_por_gallinero.get)
            peor = min(huevos_por_gallinero, key=huevos_por_gallinero.get)

            st.subheader("Ranking de producción")
            c1, c2 = st.columns(2)
            c1.metric("🏆 Mejor gallinero", f"{gallineros[mejor]['nombre']} ({mejor})", f"{huevos_por_gallinero[mejor]} huevos")
            c2.metric("⚠️ Menor producción", f"{gallineros[peor]['nombre']} ({peor})", f"{huevos_por_gallinero[peor]} huevos")

            st.subheader("Comparativo de producción entre gallineros")
            df_comp = pd.DataFrame({
                "Gallinero": [f"{c} - {gallineros[c]['nombre']}" for c in huevos_por_gallinero],
                "Huevos totales": list(huevos_por_gallinero.values()),
            }).set_index("Gallinero")
            st.bar_chart(df_comp)
        else:
            st.info("Todavía no hay recolecciones para comparar gallineros.")
        st.divider()

    codigo = st.selectbox("Selecciona un gallinero", list(gallineros.keys()), key="prod_codigo")
    datos = gallineros[codigo]
    huevos = total_huevos(datos)
    promedio = promedio_postura(datos)

    c1, c2, c3 = st.columns(3)
    c1.metric("Huevos totales de este gallinero", huevos)
    c2.metric("Promedio de postura por gallina", f"{promedio:.2f}")
    c3.metric("Porcentaje de producción", f"{promedio * 100:.0f}%")

    st.subheader("Promedio semanal de producción")
    semanas = set()
    for r in datos["recolecciones"]:
        try:
            f = date.fromisoformat(r["fecha"])
            semanas.add((f.isocalendar()[0], f.isocalendar()[1]))
        except ValueError:
            pass
    promedio_semanal = huevos / len(semanas) if semanas else 0
    st.metric("Huevos por semana (promedio)", f"{promedio_semanal:.1f}")
    st.caption(f"Calculado sobre {len(semanas)} semana(s) con registros.")

    st.subheader("Consultar por rango de fechas")
    col_desde, col_hasta = st.columns(2)
    desde = col_desde.date_input("Desde", key="rango_desde")
    hasta = col_hasta.date_input("Hasta", key="rango_hasta")
    en_rango = [r for r in datos["recolecciones"] if r["fecha"] and str(desde) <= r["fecha"] <= str(hasta)]

    if en_rango:
        st.metric(f"Huevos entre {desde} y {hasta}", sum(r["buenos"] + r["danados"] for r in en_rango))
        st.dataframe(en_rango, use_container_width=True, hide_index=True)
    else:
        st.info("No hay recolecciones registradas en ese rango de fechas.")

    st.subheader("Histórico de recolección completo")
    if datos["recolecciones"]:
        st.dataframe(datos["recolecciones"], use_container_width=True, hide_index=True)
    else:
        st.info("Todavía no hay recolecciones registradas para este gallinero.")


# ============================================================
# PANTALLA: Alimentación (RF12-17, RF24-27, RF33-34, RF46)
# ============================================================

def pantalla_alimentacion():
    st.title("Alimentación")
    alimento = st.session_state.alimento
    gallineros = st.session_state.gallineros

    c1, c2 = st.columns(2)
    c1.metric("Stock actual", f"{alimento['inventario_kg']:.1f} kg")
    c2.metric("Última compra", f"{(alimento['compras'][-1]['kilos'] if alimento['compras'] else 0):.1f} kg")

    if alimento["inventario_kg"] < 10:
        st.warning("⚠️ Atención: Stock bajo de alimento (menos de 10 kg).")

    with st.expander("💲 Precio del alimento"):
        st.metric("Precio actual por kg", f"${alimento['precio_kg']:,.2f}")
        nuevo_precio = st.number_input("Actualizar precio manualmente ($/kg)", min_value=0.0, step=100.0, key="nuevo_precio")
        if st.button("Actualizar precio"):
            if nuevo_precio <= 0:
                st.error("El precio debe ser mayor a 0.")
            else:
                alimento["precio_kg"] = nuevo_precio
                guardar_datos()
                st.success("Precio actualizado.")
                st.rerun()

    with st.expander("➕ Registrar compra de alimento"):
        kilos_compra = st.number_input("Kilos comprados", min_value=0.0, step=1.0, key="compra_kilos")
        costo_compra = st.number_input("Costo total ($)", min_value=0.0, step=1000.0, key="compra_costo")
        if st.button("Registrar compra"):
            if kilos_compra <= 0:
                st.error("Los kilos deben ser mayores a 0.")
            else:
                alimento["compras"].append({"fecha": str(date.today()), "kilos": kilos_compra, "costo": costo_compra})
                alimento["inventario_kg"] += kilos_compra
                alimento["precio_kg"] = costo_compra / kilos_compra
                guardar_datos()
                st.success("Compra registrada.")
                st.rerun()

    with st.expander("✏️ Modificar o eliminar una compra"):
        idx_c, compra = seleccionar_por_indice(
            alimento["compras"], "Selecciona una compra",
            lambda c: f"{c['fecha']} - {c['kilos']} kg - ${c['costo']:,.0f}", key="compra_sel",
        )
        if compra is None:
            st.info("No hay compras registradas.")
        else:
            nuevos_kilos = st.number_input("Kilos", min_value=0.0, step=1.0, value=float(compra["kilos"]), key="editar_compra_kilos")
            nuevo_costo = st.number_input("Costo total ($)", min_value=0.0, step=1000.0, value=float(compra["costo"]), key="editar_compra_costo")

            colA, colB = st.columns(2)
            if colA.button("Guardar cambios de la compra"):
                alimento["inventario_kg"] = max(0.0, alimento["inventario_kg"] - compra["kilos"] + nuevos_kilos)
                compra["kilos"] = nuevos_kilos
                compra["costo"] = nuevo_costo
                guardar_datos()
                st.success("Compra actualizada.")
                st.rerun()
            if colB.button("🗑️ Eliminar esta compra"):
                alimento["inventario_kg"] = max(0.0, alimento["inventario_kg"] - compra["kilos"])
                alimento["compras"].pop(idx_c)
                guardar_datos()
                st.success("Compra eliminada.")
                st.rerun()

    with st.expander("➖ Registrar consumo diario"):
        if not gallineros:
            st.info("Registra primero un gallinero en la sección 'Gallineros'.")
        else:
            codigo = st.selectbox("Gallinero", list(gallineros.keys()), key="consumo_gallinero")
            kilos_consumo = st.number_input("Kilos consumidos hoy", min_value=0.0, step=0.5, key="consumo_kilos")
            if st.button("Registrar consumo"):
                if kilos_consumo <= 0:
                    st.error("Los kilos deben ser mayores a 0.")
                elif kilos_consumo > alimento["inventario_kg"]:
                    st.error("No hay suficiente alimento en inventario para descontar esa cantidad.")
                else:
                    alimento["consumos"].append({"fecha": str(date.today()), "codigo": codigo, "kilos": kilos_consumo})
                    alimento["inventario_kg"] -= kilos_consumo
                    guardar_datos()
                    st.success("Consumo registrado.")
                    if alimento["inventario_kg"] < 10:
                        st.warning("Atención: Stock bajo de alimento.")
                    st.rerun()

    with st.expander("💊 Registrar gasto (medicina, empaque u otro)"):
        categoria = st.selectbox("Categoría", ["Medicina", "Empaque", "Otro"], key="gasto_categoria")
        concepto = st.text_input("Concepto", key="gasto_concepto")
        valor = st.number_input("Valor ($)", min_value=0.0, step=1000.0, key="gasto_valor")
        if st.button("Registrar gasto"):
            if concepto.strip() == "":
                st.error("El concepto no puede estar vacío.")
            elif valor <= 0:
                st.error("El valor debe ser mayor a 0.")
            else:
                alimento["gastos_adicionales"].append(
                    {"fecha": str(date.today()), "categoria": categoria, "concepto": concepto, "valor": valor}
                )
                guardar_datos()
                st.success("Gasto registrado.")
                st.rerun()

    # RF46: eliminar un gasto, reutilizando el mismo ayudante de siempre
    with st.expander("🗑️ Eliminar un gasto registrado"):
        idx_g, gasto_sel = seleccionar_por_indice(
            alimento["gastos_adicionales"], "Selecciona un gasto",
            lambda g: f"{g['fecha']} - {g.get('categoria', 'Otro')} - {g['concepto']} - ${g['valor']:,.0f}", key="gasto_sel",
        )
        if gasto_sel is None:
            st.info("No hay gastos registrados.")
        else:
            confirmar_gasto = st.checkbox("Confirmo que quiero eliminar este gasto", key="confirmar_gasto")
            if st.button("🗑️ Eliminar gasto", disabled=not confirmar_gasto):
                alimento["gastos_adicionales"].pop(idx_g)
                guardar_datos()
                st.success("Gasto eliminado.")
                st.rerun()

    st.subheader("Historial de compras")
    if alimento["compras"]:
        st.dataframe(alimento["compras"], use_container_width=True, hide_index=True)
    else:
        st.info("No hay compras registradas todavía.")

    st.subheader("Historial de gastos")
    if alimento["gastos_adicionales"]:
        st.dataframe(alimento["gastos_adicionales"], use_container_width=True, hide_index=True)
    else:
        st.info("No hay gastos registrados todavía.")


# ============================================================
# PANTALLA: Reportes (RF15, RF18, RF19, RF30, RF35, RF40+RF48)
# ============================================================

def pantalla_reportes():
    st.title("Reportes")
    gallineros = st.session_state.gallineros
    alimento = st.session_state.alimento

    st.subheader("Resumen general de la granja")
    total_b, total_d = totales_granja(gallineros)
    total_kg_consumidos = sum(c["kilos"] for c in alimento["consumos"])
    gasto_alimento = sum(c["costo"] for c in alimento["compras"])
    gastos_cat = gastos_por_categoria(alimento)

    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Producción total (huevos)", total_b + total_d)
    g2.metric("Alimento consumido", f"{total_kg_consumidos:.1f} kg")
    g3.metric("Gasto en alimento", f"${gasto_alimento:,.0f}")
    g4.metric("Gasto total", f"${gasto_alimento + sum(gastos_cat.values()):,.0f}")

    st.divider()

    st.subheader("Historial por fecha")
    fecha_hist = st.date_input("Selecciona una fecha", key="fecha_historial")
    recolecciones_dia = [
        {"Gallinero": codigo, **r}
        for codigo, g in gallineros.items() for r in g["recolecciones"] if r["fecha"] == str(fecha_hist)
    ]
    consumos_dia = [c for c in alimento["consumos"] if c["fecha"] == str(fecha_hist)]

    col_rec, col_cons = st.columns(2)
    with col_rec:
        st.markdown("**Recolecciones ese día**")
        if recolecciones_dia:
            st.dataframe(recolecciones_dia, use_container_width=True, hide_index=True)
        else:
            st.info("Sin recolecciones ese día.")
    with col_cons:
        st.markdown("**Consumos de alimento ese día**")
        if consumos_dia:
            st.dataframe(consumos_dia, use_container_width=True, hide_index=True)
        else:
            st.info("Sin consumos ese día.")

    st.divider()

    st.subheader("Costo diario de alimentación")
    fecha_costo = st.date_input("Selecciona una fecha", key="fecha_costo")
    kilos_dia = sum(c["kilos"] for c in alimento["consumos"] if c["fecha"] == str(fecha_costo))
    st.metric("Costo estimado ese día", f"${kilos_dia * alimento['precio_kg']:,.0f}")

    st.divider()

    st.subheader("Balance presupuestal por categoría")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Alimento", f"${gasto_alimento:,.0f}")
    r2.metric("Medicinas", f"${gastos_cat['Medicina']:,.0f}")
    r3.metric("Empaques", f"${gastos_cat['Empaque']:,.0f}")
    r4.metric("Otros", f"${gastos_cat['Otro']:,.0f}")

    st.divider()

    st.subheader("Rendimiento por gallinero")
    if not gallineros:
        st.info("No hay gallineros registrados.")
        return

    codigo = st.selectbox("Selecciona un gallinero", list(gallineros.keys()), key="reporte_gallinero")
    datos = gallineros[codigo]
    kilos_consumidos = sum(c["kilos"] for c in alimento["consumos"] if c["codigo"] == codigo)

    r1, r2, r3 = st.columns(3)
    r1.metric("Huevos totales", total_huevos(datos))
    r2.metric("Alimento consumido", f"{kilos_consumidos:.1f} kg")
    r3.metric("Costo estimado", f"${kilos_consumidos * alimento['precio_kg']:,.0f}")


# ============================================================
# PANTALLA: Exportar y Configuración
# ============================================================

def pantalla_exportar():
    st.title("Exportar y Configuración")
    gallineros = st.session_state.gallineros

    st.subheader("Exportar resumen general")
    st.download_button(
        "⬇️ Descargar PDF general", data=generar_pdf_resumen_general(),
        file_name="resumen_general.pdf", mime="application/pdf",
    )

    st.divider()

    st.subheader("Exportar resumen de un gallinero")
    if not gallineros:
        st.info("No hay gallineros registrados todavía.")
    else:
        codigo = st.selectbox("Selecciona un gallinero", list(gallineros.keys()), key="export_codigo")
        st.download_button(
            "⬇️ Descargar PDF del gallinero", data=generar_pdf_resumen_gallinero(codigo),
            file_name=f"resumen_{codigo}.pdf", mime="application/pdf",
        )

    st.divider()

    st.subheader("Zona de configuración")
    st.warning("Esta acción borra TODOS los datos (gallineros, recolecciones, alimento). No se puede deshacer.")
    confirmar_reset = st.checkbox("Confirmo que quiero borrar todos los datos", key="confirmar_reset")
    if st.button("🗑️ Reiniciar todos los datos", disabled=not confirmar_reset):
        st.session_state.gallineros = {}
        st.session_state.alimento = alimento_vacio()
        guardar_datos()
        st.success("Todos los datos se reiniciaron.")
        st.rerun()


# ============================================================
# NAVEGACIÓN PRINCIPAL
# ============================================================

def main():
    if not st.session_state.autenticado:
        pantalla_login()
        return

    with st.sidebar:
        st.markdown("## 🐔 Sistema Avícola")
        opciones = ["Dashboard", "Gallineros", "Producción", "Registrar Postura", "Alimentación", "Reportes", "Exportar"]
        opcion = st.radio("Menú", opciones, index=opciones.index(st.session_state.pagina))
        st.session_state.pagina = opcion

        st.divider()
        if st.button("Cerrar sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()

    pantallas = {
        "Dashboard": pantalla_dashboard,
        "Gallineros": pantalla_gallineros,
        "Producción": pantalla_produccion,
        "Registrar Postura": pantalla_postura,
        "Alimentación": pantalla_alimentacion,
        "Reportes": pantalla_reportes,
        "Exportar": pantalla_exportar,
    }
    pantallas[st.session_state.pagina]()


main()
