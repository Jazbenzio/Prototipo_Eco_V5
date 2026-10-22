"""PERSONA 1 - CONTRATO con el resto del equipo."""
from vision.pantalla import capturar_pantalla_b64
from vision.atencion import detectar_estado


def obtener_contexto_visual() -> dict:
    """Devuelve {'imagen': str base64, 'estado': 'atento'|'distraido'|'cansado'}."""
    return {"imagen": capturar_pantalla_b64(), "estado": "atento"}
