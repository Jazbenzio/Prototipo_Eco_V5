"""Configuración central de Eco."""
import os
from dotenv import load_dotenv

load_dotenv()

NOMBRE = "Eco"
PALABRA_ACTIVACION = "eco"
API_KEY = os.getenv("GEMINI_API_KEY")
MODELO = "gemini-3.5-flash-lite"
MODELOS_RESPALDO = ["gemini-3.1-flash-lite", "gemini-3.5-flash"]
MODELO_AGENTE = "gemini-3.5-flash"
DB_PATH = "data/eco.db"
INTERVALO_CAPTURA_SEG = 30   # captura periódica de pantalla (si el usuario la activa)
DIAS_REPASO = [1, 3, 7, 14]  # repetición espaciada
_mic = os.getenv("MIC_DISPOSITIVO")
MIC_DISPOSITIVO = int(_mic) if _mic else None
ANCHO_CAPTURA = 1024                # más alto = lee mejor el texto pequeño, pero tarda más
MONITOR = 1                       # 1 = pantalla principal, 2 = la segunda, etc.
INTERVALO_VISTA_MS = 3000        # cada cuánto se actualiza la miniatura
EXCLUIR_VENTANA_DE_CAPTURA = True # pon False si vas a grabar la pantalla con Eco visible
MAX_PASOS_AGENTE = 15
PAUSA_ENTRE_PASOS = 0.5
ANCHO_AGENTE = 1024