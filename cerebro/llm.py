"""PERSONA 2 - CONTRATO: conexión con Claude (texto + imagen)."""
import anthropic
import config
from cerebro.modos import prompt_para

_cliente = anthropic.Anthropic(api_key=config.API_KEY)


def preguntar(texto: str, imagen_b64: str | None = None, modo: str = "estudio") -> str:
    contenido = []
    if imagen_b64:
        contenido.append({"type": "image", "source": {
            "type": "base64", "media_type": "image/png", "data": imagen_b64}})
    contenido.append({"type": "text", "text": texto})
    r = _cliente.messages.create(
        model=config.MODELO, max_tokens=1000,
        system=prompt_para(modo),
        messages=[{"role": "user", "content": contenido}],
    )
    return r.content[0].text
