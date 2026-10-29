"""Punto de entrada: abre la barra flotante de Eco."""
import sys

from PySide6.QtWidgets import QApplication

from ui.barra_eco import BarraEco


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # Eco sigue en la bandeja aunque se oculte la barra
    barra = BarraEco()
    barra.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()