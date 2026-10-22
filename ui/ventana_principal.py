"""PERSONA 3 - Ventana principal."""
from PySide6.QtWidgets import QMainWindow, QLabel


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eco")
        self.resize(900, 600)
        self.setCentralWidget(QLabel("Hola, soy Eco"))
