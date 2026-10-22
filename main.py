"""Punto de entrada: une visión, voz/cerebro y UI/memoria."""
import sys
from PySide6.QtWidgets import QApplication
from ui.ventana_principal import VentanaPrincipal


def main():
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
