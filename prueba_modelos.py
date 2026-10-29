import time
from google import genai
import config

cliente = genai.Client(api_key=config.API_KEY)
for m in ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
          "gemini-3.5-flash", "gemini-3.8-flash"]:
    try:
        t0 = time.time()
        r = cliente.models.generate_content(
            model=m, contents="¿Qué es una ecuación? Responde en 2 frases.")
        print(f"{m}: {time.time() - t0:.1f} s -> {r.text[:60]!r}")
    except Exception as e:
        print(f"{m}: ERROR {str(e)[:80]}")