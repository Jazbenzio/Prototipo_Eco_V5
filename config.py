"""Configuración central de Eco."""
import os
from dotenv import load_dotenv

load_dotenv()

NOMBRE = "Eco"
PALABRA_ACTIVACION = "eco"
API_KEY = os.getenv("GEMINI_API_KEY")
MODELO = "gemini-3.8-flash"
DB_PATH = "data/eco.db"
INTERVALO_CAPTURA_SEG = 30   # captura periódica de pantalla (si el usuario la activa)
DIAS_REPASO = [1, 3, 7, 14]  # repetición espaciada