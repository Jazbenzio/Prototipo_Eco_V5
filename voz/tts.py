"""PERSONA 2 - Texto a voz con pyttsx3 (voces de Windows)."""
import threading
import pyttsx3

_lock = threading.Lock()
_engine = None


def _limpiar(texto: str) -> str:
    return texto.replace("*", "").replace("#", "").replace("`", "")


def _hablar(texto: str):
    global _engine
    with _lock:
        engine = pyttsx3.init()
        _engine = engine
        for v in engine.getProperty("voices"):
            nombre = v.name.lower()
            if "spanish" in nombre or "español" in nombre or "sabina" in nombre:
                engine.setProperty("voice", v.id)
                break
        engine.setProperty("rate", 175)
        engine.say(_limpiar(texto))
        engine.runAndWait()
        _engine = None


def hablar(texto: str) -> None:
    """Habla en segundo plano para no congelar la ventana."""
    threading.Thread(target=_hablar, args=(texto,), daemon=True).start()


def callar() -> None:
    """Interrumpe la voz."""
    try:
        if _engine is not None:
            _engine.stop()
    except Exception:
        pass