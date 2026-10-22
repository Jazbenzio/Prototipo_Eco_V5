"""PERSONA 2 - Selección de modo."""
from cerebro.prompts import PROMPT_ESTUDIO, PROMPT_LIBRE


def prompt_para(modo: str) -> str:
    return PROMPT_ESTUDIO if modo == "estudio" else PROMPT_LIBRE
