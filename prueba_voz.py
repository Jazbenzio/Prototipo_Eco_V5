import time
import numpy as np
import sounddevice as sd

print(sd.query_devices())
print("Entrada por defecto:", sd.default.device[0])
print("\nHabla 4 segundos...")
audio = sd.rec(4 * 16000, samplerate=16000, channels=1, dtype="float32")
sd.wait()
audio = audio.flatten()
print("Volumen máximo:", round(float(np.abs(audio).max()), 4))

print("\nCargando Whisper (la primera vez descarga el modelo)...")
t0 = time.time()
from faster_whisper import WhisperModel
modelo = WhisperModel("base", device="cpu", compute_type="int8")
print(f"Modelo listo en {time.time() - t0:.1f} s")

t0 = time.time()
segmentos, _ = modelo.transcribe(audio, language="es", vad_filter=False)
texto = " ".join(s.text.strip() for s in segmentos)
print(f"Transcrito en {time.time() - t0:.1f} s: {texto!r}")