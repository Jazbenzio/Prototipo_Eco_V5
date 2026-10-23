"""PERSONA 2 - CONTRATO: conexión con Gemini (texto + imagen)."""
import base64
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError
import config
from cerebro.modos import prompt_para

_cliente = genai.Client(api_key=config.API_KEY)

REINTENTOS = 3


def preguntar(texto: str, imagen_b64: str | None = None, modo: str = "estudio") -> str:
    partes = []
    if imagen_b64:
        partes.append(types.Part.from_bytes(
            data=base64.b64decode(imagen_b64), mime_type="image/png"))
    partes.append(texto)

    configuracion = types.GenerateContentConfig(
        system_instruction=prompt_para(modo),
        max_output_tokens=1000,
    )

    for intento in range(REINTENTOS):
        try:
            r = _cliente.models.generate_content(
                model=config.MODELO, contents=partes, config=configuracion)
            return r.text
        except ServerError:
            if intento == REINTENTOS - 1:
                raise
            time.sleep(2 * (intento + 1))  # espera 2 s, luego 4 s