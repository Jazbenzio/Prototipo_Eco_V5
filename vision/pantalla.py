"""PERSONA 1 - Captura de pantalla con mss."""
import base64, io
import mss
from PIL import Image


def capturar_pantalla_b64() -> str:
    """Devuelve una captura de la pantalla en base64 (PNG)."""
    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[1])
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()
