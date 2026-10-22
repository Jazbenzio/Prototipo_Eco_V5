"""PERSONA 1 - Captura de cámara con OpenCV."""
import cv2


class Camara:
    def __init__(self, indice: int = 0):
        self.cap = cv2.VideoCapture(indice)

    def leer_frame(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def cerrar(self):
        self.cap.release()
