"""PERSONA 1 - Captura de pantalla con mss."""
import base64
import io

import mss
from PIL import Image

import config


def capturar_imagen(ancho_max: int | None = None) -> Image.Image:
    """Captura el monitor elegido en config.MONITOR y lo reduce a ancho_max px."""
    ancho_max = ancho_max or getattr(config, "ANCHO_CAPTURA", 1600)
    with mss.mss() as sct:
        monitores = sct.monitors
        indice = getattr(config, "MONITOR", 1)
        if indice >= len(monitores):
            indice = 1
        raw = sct.grab(monitores[indice])
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    if img.width > ancho_max:
        alto = int(img.height * ancho_max / img.width)
        img = img.resize((ancho_max, alto), Image.Resampling.LANCZOS)
    return img


def imagen_a_b64(img: Image.Image, calidad: int = 75) -> str:
    """Convierte una imagen a JPEG en base64 (lo que se envía a Gemini)."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=calidad)
    return base64.b64encode(buf.getvalue()).decode()


def capturar_pantalla_b64(ancho_max: int | None = None) -> str:
    """Captura la pantalla ahora mismo y la devuelve en base64."""
    return imagen_a_b64(capturar_imagen(ancho_max))