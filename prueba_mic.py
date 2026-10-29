import sounddevice as sd
import numpy as np

print(sd.query_devices())
print("Dispositivo de entrada por defecto:", sd.default.device[0])
print("Habla durante 4 segundos...")
audio = sd.rec(4 * 16000, samplerate=16000, channels=1, dtype="float32")
sd.wait()
print("Volumen máximo:", float(np.abs(audio).max()))