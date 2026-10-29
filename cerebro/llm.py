"""PERSONA 2 - CONTRATO: conexión con Gemini (texto + imagen) con memoria de conversación."""
import base64
import time
from google import genai
from google.genai import types
from google.genai.errors import ClientError
import config
from cerebro.modos import prompt_para

# timeout en milisegundos: si un modelo no responde en 15 s, se pasa al siguiente
_cliente = genai.Client(
    api_key=config.API_KEY,
    http_options=types.HttpOptions(timeout=15000),
)

# Memoria de la conversación actual (se borra al cerrar la app)
_historial: list[types.Content] = []
MAX_MENSAJES = 40   # máximo de mensajes recordados (20 preguntas y 20 respuestas)


def nueva_conversacion() -> None:
    """Borra la memoria de la conversación."""
    _historial.clear()


def _guardar(texto_usuario: str, respuesta: str) -> None:
    _historial.append(types.Content(
        role="user", parts=[types.Part.from_text(text=texto_usuario)]))
    _historial.append(types.Content(
        role="model", parts=[types.Part.from_text(text=respuesta)]))
    del _historial[:-MAX_MENSAJES]   # conserva solo los más recientes


def preguntar(texto: str, imagen_b64: str | None = None, modo: str = "estudio") -> str:
    partes = []
    if imagen_b64:
        partes.append(types.Part.from_bytes(
            data=base64.b64decode(imagen_b64), mime_type="image/jpeg"))
    partes.append(types.Part.from_text(text=texto))
    mensaje_actual = types.Content(role="user", parts=partes)
    contenido = _historial + [mensaje_actual]

    configuracion = types.GenerateContentConfig(
        system_instruction=prompt_para(modo),
        max_output_tokens=2048,
    )

    modelos = [config.MODELO] + getattr(config, "MODELOS_RESPALDO", [])
    ultimo_error = None
    for modelo in modelos:
        try:
            t0 = time.time()
            r = _cliente.models.generate_content(
                model=modelo, contents=contenido, config=configuracion)
            print(f"[Eco] {modelo} respondió en {time.time() - t0:.1f} s "
                  f"(memoria: {len(_historial)} mensajes)")
            if r.text:
                nota = " [el usuario compartió su pantalla]" if imagen_b64 else ""
                _guardar(texto + nota, r.text)
                return r.text
            ultimo_error = RuntimeError("Gemini devolvió una respuesta vacía")
        except ClientError as e:
            if e.code in (404, 429):   # modelo inexistente o límite de uso: probar otro
                print(f"[Eco] {modelo} no disponible ({e.code})")
                ultimo_error = e
                continue
            raise
        except Exception as e:         # 503, 504, timeout...
            print(f"[Eco] {modelo} falló: {str(e)[:100]}")
            ultimo_error = e
    raise ultimo_error