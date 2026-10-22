"""Configuración central de Eco."""
import os
from dotenv import load_dotenv

load_dotenv()

NOMBRE = "Eco"
PALABRA_ACTIVACION = "eco"
API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODELO = "claude-sonnet-5-5"
DB_PATH = "data/eco.db"
INTERVALO_CAPTURA_SEG = 30   # captura periódica de pantalla (si el usuario la activa)
DIAS_REPASO = [1, 3, 7, 14]  # repetición espaciada
