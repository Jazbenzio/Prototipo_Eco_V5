"""PERSONA 2 - Voz a texto con faster-whisper (local)."""
import threading
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import config

FS = 16000
_modelo = None
_lock = threading.Lock()


def _get_modelo():
    global _modelo
    with _lock:
        if _modelo is None:
            print("[Eco] Cargando Whisper (la primera vez descarga el modelo)...")
            _modelo = WhisperModel("base", device="cpu", compute_type="int8")
            print("[Eco] Whisper listo")
    return _modelo


class Grabadora:
    """Graba del micrófono entre iniciar() y detener()."""

    def __init__(self):
        self.frames = []
        self.stream = None

    def _callback(self, indata, frames, time, status):
        self.frames.append(indata.copy())

    def iniciar(self):
        self.frames = []
        dispositivo = getattr(config, "MIC_DISPOSITIVO", None)
        print(f"[Eco] Grabando con el dispositivo: {dispositivo}")
        self.stream = sd.InputStream(
            samplerate=FS, channels=1, dtype="float32",
            device=dispositivo, callback=self._callback)
        self.stream.start()

    def detener(self):
        self.stream.stop()
        self.stream.close()
        if not self.frames:
            print("[Eco] No llegó audio del micrófono")
            return np.zeros(0, dtype="float32")
        audio = np.concatenate(self.frames).flatten()
        print(f"[Eco] Audio: {len(audio) / FS:.1f} s, volumen máx {np.abs(audio).max():.3f}")
        return audio


def transcribir(audio) -> str:
    if audio.size < FS * 0.5:   # menos de medio segundo
        return ""
    pico = float(np.abs(audio).max())
    if pico < 0.005:
        print("[Eco] El micrófono grabó silencio")
        return ""
    if pico < 0.3:              # si quedó muy bajito, se sube el volumen
        audio = audio / pico * 0.5
    segmentos, _ = _get_modelo().transcribe(
        audio, language="es", vad_filter=False, beam_size=1)
    texto = " ".join(s.text.strip() for s in segmentos).strip()
    print(f"[Eco] Whisper entendió: {texto!r}")
    return texto