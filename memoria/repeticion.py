"""PERSONA 3 - Repetición espaciada."""
from datetime import date, timedelta
import config


def proxima_fecha(nivel: int) -> str:
    dias = config.DIAS_REPASO[min(nivel, len(config.DIAS_REPASO) - 1)]
    return (date.today() + timedelta(days=dias)).isoformat()
