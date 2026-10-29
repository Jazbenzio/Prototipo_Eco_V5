import sounddevice as sd
import numpy as np

print("Habla sin parar durante toda la prueba...")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] < 1:
        continue
    try:
        a = sd.rec(int(2 * 16000), samplerate=16000, channels=1,
                   dtype="float32", device=i)
        sd.wait()
        print(f"[{i}] {d['name'][:45]:45} volumen máx: {float(np.abs(a).max()):.3f}")
    except Exception as e:
        print(f"[{i}] {d['name'][:45]:45} error: {str(e)[:40]}")