"""Acciones sobre el ratón y el teclado (pyautogui).

Las coordenadas que recibe el agente van de 0 a 1000 sobre la imagen que Gemini vio
(0,0 = esquina superior izquierda). Aquí se convierten a píxeles reales de la pantalla.
"""
import time

import mss
import pyautogui
import pyperclip

import config

# Mover el ratón a una esquina de la pantalla detiene al agente de inmediato.
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# Combinaciones que el agente nunca puede pulsar.
TECLAS_BLOQUEADAS = {
    "alt+f4", "ctrl+alt+delete", "ctrl+alt+del", "ctrl+shift+esc", "win+r", "win+x",
}

ALIAS = {
    "control": "ctrl", "escape": "esc", "windows": "win", "return": "enter",
    "suprimir": "delete", "supr": "delete", "retroceso": "backspace",
    "espacio": "space", "mayus": "shift", "flecha_abajo": "down", "flecha_arriba": "up",
}


def geometria_monitor() -> dict:
    """Posición y tamaño (en píxeles reales) del monitor que Eco está mirando."""
    with mss.mss() as sct:
        monitores = sct.monitors
        i = getattr(config, "MONITOR", 1)
        if i >= len(monitores):
            i = 1
        return dict(monitores[i])


def a_pantalla(x: float, y: float) -> tuple[int, int]:
    """Convierte coordenadas 0-1000 a píxeles reales (sin tocar las esquinas)."""
    g = geometria_monitor()
    x = max(3.0, min(997.0, float(x)))
    y = max(3.0, min(997.0, float(y)))
    return g["left"] + int(x / 1000 * g["width"]), g["top"] + int(y / 1000 * g["height"])


def click(x: float, y: float, veces: int = 1, boton: str = "left") -> None:
    px, py = a_pantalla(x, y)
    pyautogui.moveTo(px, py, duration=0.3)
    pyautogui.click(clicks=veces, interval=0.1, button=boton)


def escribir(texto: str, enter: bool = False) -> None:
    """Escribe pegando desde el portapapeles (así funcionan acentos y la ñ).
    Después restaura lo que había en el portapapeles."""
    texto = texto[:1000]
    anterior = None
    try:
        anterior = pyperclip.paste()
    except Exception:
        pass
    pyperclip.copy(texto)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.4)
    if enter:
        pyautogui.press("enter")
    if anterior is not None:
        time.sleep(0.3)
        try:
            pyperclip.copy(anterior)
        except Exception:
            pass


def tecla(combo: str) -> None:
    """Pulsa una tecla o combinación, por ejemplo 'enter' o 'ctrl+l'."""
    teclas = [ALIAS.get(t, t) for t in combo.lower().replace(" ", "").split("+") if t]
    if not teclas:
        raise ValueError("No indicaste ninguna tecla")
    if "+".join(teclas) in TECLAS_BLOQUEADAS:
        raise PermissionError(f"La combinación {combo} está bloqueada por seguridad")
    for t in teclas:
        if t not in pyautogui.KEYBOARD_KEYS:
            raise ValueError(f"Tecla desconocida: {t}")
    if len(teclas) == 1:
        pyautogui.press(teclas[0])
    else:
        pyautogui.hotkey(*teclas)


def scroll(cantidad: float, x: float | None = None, y: float | None = None) -> None:
    """Desplaza la rueda: positivo sube, negativo baja (1 = una muesca)."""
    if x is not None and y is not None:
        px, py = a_pantalla(x, y)
        pyautogui.moveTo(px, py, duration=0.2)
    pyautogui.scroll(int(float(cantidad) * 120))