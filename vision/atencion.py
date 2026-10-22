"""PERSONA 1 - Estado del usuario con MediaPipe (todo local, no se guarda video)."""


def detectar_estado(frame) -> str:
    """Devuelve 'atento', 'distraido' o 'cansado'.
    TODO: face mesh -> parpadeo, orientación de cabeza, mirada."""
    return "atento"
