"""
Lanzador de escritorio para el Sistema Avícola.

En vez de abrir la app en una pestaña del navegador, esto abre una
ventana nativa (como cualquier programa de escritorio) que muestra
por dentro la misma app de Streamlit.

Instalar antes de usar (una sola vez):
    pip install pywebview

Ejecutar con:
    python desktop_launcher.py

(Ya NO uses 'streamlit run app_streamlit.py' directamente si quieres
la ventana de escritorio — usa este archivo en su lugar.)
"""

import subprocess
import time
import webview

# Por seguridad, pywebview NO permite descargar archivos dentro de su
# ventana a menos que se lo activemos explícitamente. Sin esta línea,
# el botón "Descargar PDF" de Streamlit no hace absolutamente nada.
webview.settings['ALLOW_DOWNLOADS'] = True

URL = "http://localhost:8501"


def iniciar_streamlit():
    """Arranca streamlit como un proceso aparte, en segundo plano."""
    return subprocess.Popen(
        [
            "python", "-m", "streamlit", "run", "app_streamlit.py",
            "--server.headless", "true",
            "--server.port", "8501",
        ]
    )


def main():
    proceso = iniciar_streamlit()

    # Le damos unos segundos a Streamlit para que termine de arrancar
    # antes de intentar abrir la ventana, si no, la ventana cargaría
    # antes de que el servidor esté listo.
    time.sleep(3)

    try:
        # Esto abre la ventana de escritorio apuntando a la app local.
        webview.create_window("Sistema Avícola", URL, width=1200, height=800)
        webview.start()
    finally:
        # Cuando el usuario cierra la ventana, apagamos también el
        # servidor de Streamlit para no dejarlo corriendo de fondo.
        proceso.terminate()


if __name__ == "__main__":
    main()
