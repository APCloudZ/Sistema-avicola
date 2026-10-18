# Sistema de Gestión Avícola

Aplicación de escritorio para administrar una granja avícola: gallineros, registro de postura, producción, alimentación, gastos y reportes en PDF.

Está hecha en **Python** con **Streamlit** y se abre en una ventana de escritorio gracias a **pywebview**

## Funcionalidades

- **Dashboard:** resumen de gallineros, aves, huevos y alimento, con gráfica de producción y alertas.
- **Gallineros:** registrar, modificar, dar de baja aves, duplicar como plantilla y eliminar. Incluye búsqueda, orden e historial de movimientos.
- **Producción:** ranking entre gallineros, promedio de postura, promedio semanal y consulta por rango de fechas.
- **Registrar Postura:** recolección diaria de huevos buenos y dañados, con edición y eliminación.
- **Alimentación:** inventario, precio por kg, compras, consumo diario y gastos (medicina, empaque y otros).
- **Reportes:** indicadores generales, historial por fecha, costo diario y balance por categoría.
- **Exportar:** resúmenes en PDF (general y por gallinero) y reinicio de datos.

## Requisitos

- Python 3.10 o superior.
- Las librerías de `requirements.txt`.

## Instalación

```bash
pip install -r requirements.txt
```

## Cómo ejecutar

Como aplicación de escritorio (ventana propia):

```bash
python desktop_launcher.py
```

O en el navegador:

```bash
python -m streamlit run app_streamlit.py
```

## Estructura del proyecto

| Archivo | Para qué sirve |
| --- | --- |
| `app_streamlit.py` | Todas las pantallas, la lógica y los estilos visuales (función `cargar_estilos()`). |
| `desktop_launcher.py` | Arranca Streamlit y abre la ventana de escritorio (1200x800). |
| `.streamlit/config.toml` | Tema visual: colores, tipografía y barra lateral. |
| `datos.json` | Datos guardados (gallineros y alimento). Se crea solo si no existe. |
| `requirements.txt` | Librerías necesarias. |

## Notas

- Los datos se guardan automáticamente en `datos.json` en la misma carpeta.
- La tipografía Inter se descarga de Google Fonts; sin internet se usa una letra del sistema.
