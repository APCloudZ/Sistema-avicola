"""
Lanzador de escritorio para el Sistema Avícola.

Instalar antes de usar (una sola vez):
    pip install pywebview

Ejecutar con:
    python desktop_launcher.py

"""

import subprocess
import time
import webview


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
