"""PERSONA 3 - Ventana principal: chat, voz, pantalla y memoria de conversación."""
import html
import sys
import threading

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QCheckBox, QComboBox, QLabel, QMessageBox,
)

import config
from agente.agente import Agente
from cerebro.llm import preguntar, nueva_conversacion
from vision.pantalla import capturar_pantalla_b64, capturar_imagen
from voz.stt import Grabadora, transcribir, _get_modelo
from voz.tts import hablar, callar


class Trabajador(QThread):
    """Llama a Gemini en segundo plano para no congelar la ventana."""
    terminado = Signal(str)

    def __init__(self, texto, ver_pantalla, modo):
        super().__init__()
        self.texto = texto
        self.ver_pantalla = ver_pantalla
        self.modo = modo

    def run(self):
        try:
            imagen = capturar_pantalla_b64() if self.ver_pantalla else None
            self.terminado.emit(preguntar(self.texto, imagen, self.modo))
        except Exception as e:
            texto_error = str(e)
            if any(c in texto_error for c in ("503", "504", "UNAVAILABLE", "DEADLINE")):
                self.terminado.emit("Eco tuvo un problema: Gemini está tardando demasiado "
                                    "o saturado. Intenta de nuevo en un momento.")
            else:
                self.terminado.emit(f"Eco tuvo un problema: {e}")


class Transcriptor(QThread):
    """Convierte el audio grabado en texto, en segundo plano."""
    terminado = Signal(str)
    fallo = Signal(str)

    def __init__(self, audio):
        super().__init__()
        self.audio = audio

    def run(self):
        try:
            self.terminado.emit(transcribir(self.audio))
        except Exception as e:
            self.fallo.emit(str(e))


class AgenteWorker(QThread):
    """Ejecuta la tarea del agente en segundo plano."""
    progreso = Signal(str)
    pedir_confirmacion = Signal(str)
    terminado = Signal(str)

    def __init__(self, tarea, zona_prohibida):
        super().__init__()
        self.tarea = tarea
        self.zona_prohibida = zona_prohibida
        self._parar = False
        self._evento = threading.Event()
        self._respuesta = False

    def detener(self):
        self._parar = True
        self._evento.set()          # por si estaba esperando una confirmación

    def responder(self, permitido):
        self._respuesta = permitido
        self._evento.set()

    def _confirmar(self, texto):
        self._evento.clear()
        self._respuesta = False
        self.pedir_confirmacion.emit(texto)
        self._evento.wait()
        return self._respuesta and not self._parar

    def run(self):
        try:
            agente = Agente(self.tarea, self.progreso.emit, self._confirmar,
                            self.zona_prohibida, lambda: self._parar)
            self.terminado.emit(agente.ejecutar())
        except Exception as e:
            self.terminado.emit(f"El agente se detuvo por un error: {e}")


class VentanaPrincipal(QMainWindow):
    _zona = (0, 0, 0, 0)   # área que ocupa la ventana de Eco (el agente no hace clic ahí)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Eco")
        self.resize(1050, 650)
        self.trabajador = None
        self.transcriptor = None
        self.grabadora = Grabadora()
        self.grabando = False
        self.agente = None
        self._geom_previa = None

        # --- Controles superiores ---
        self.combo_modo = QComboBox()
        self.combo_modo.addItems(["Estudio", "Libre", "Agente"])
        self.check_pantalla = QCheckBox("👁 Eco ve mi pantalla en vivo")
        self.check_arriba = QCheckBox("📌 Siempre visible")
        self.check_voz = QCheckBox("Eco habla en voz alta")
        self.check_voz.setChecked(True)
        self.boton_nueva = QPushButton("🗑 Nueva conversación")
        self.boton_detener = QPushButton("⛔ Detener agente")
        self.boton_detener.setStyleSheet("background: #b00020; color: white; font-weight: bold;")
        self.boton_detener.hide()

        arriba = QHBoxLayout()
        arriba.addWidget(self.combo_modo)
        arriba.addWidget(self.check_pantalla)
        arriba.addWidget(self.check_voz)
        arriba.addWidget(self.check_arriba)
        arriba.addStretch()
        arriba.addWidget(self.boton_detener)
        arriba.addWidget(self.boton_nueva)

        # --- Chat ---
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)

        # --- Vista previa de lo que Eco ve (solo local, no se envía a ningún lado) ---
        self.vista = QLabel()
        self.vista.setFixedSize(320, 200)
        self.vista.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vista.setStyleSheet("border: 1px solid #555; background: #111;")
        self.etiqueta_vista = QLabel("Esto es lo que Eco puede ver")
        self.etiqueta_vista.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.columna_vista = QWidget()
        col = QVBoxLayout(self.columna_vista)
        col.setContentsMargins(0, 0, 0, 0)
        col.addWidget(self.etiqueta_vista)
        col.addWidget(self.vista)
        col.addStretch()
        self.columna_vista.hide()

        centro = QHBoxLayout()
        centro.addWidget(self.chat, 1)
        centro.addWidget(self.columna_vista)

        self.timer_vista = QTimer(self)
        self.timer_vista.timeout.connect(self.actualizar_vista)

        # --- Entrada ---
        self.entrada = QLineEdit()
        self.entrada.setPlaceholderText("Escríbele a Eco o usa el micrófono...")
        self.boton_mic = QPushButton("🎤 Hablar")
        self.boton = QPushButton("Enviar")

        abajo = QHBoxLayout()
        abajo.addWidget(self.entrada)
        abajo.addWidget(self.boton_mic)
        abajo.addWidget(self.boton)

        # --- Layout general ---
        layout = QVBoxLayout()
        layout.addLayout(arriba)
        layout.addLayout(centro, 1)
        layout.addLayout(abajo)
        contenedor = QWidget()
        contenedor.setLayout(layout)
        self.setCentralWidget(contenedor)

        # --- Conexiones ---
        self.boton.clicked.connect(self.enviar)
        self.entrada.returnPressed.connect(self.enviar)
        self.boton_mic.clicked.connect(self.alternar_microfono)
        self.boton_nueva.clicked.connect(self.nueva_conversacion_click)
        self.check_pantalla.toggled.connect(self.alternar_vista)
        self.check_arriba.toggled.connect(self.alternar_siempre_visible)
        self.boton_detener.clicked.connect(self.detener_agente)
        self.combo_modo.currentTextChanged.connect(self.cambio_modo)

        self.agregar("Eco", "Hola, soy Eco. ¿En qué te ayudo?")

        # Carga Whisper en segundo plano para que el primer mensaje de voz no espere
        threading.Thread(target=_get_modelo, daemon=True).start()

    # ---------- Agente (controla el PC) ----------
    def cambio_modo(self, modo):
        if modo == "Agente":
            self.entrada.setPlaceholderText("Dile a Eco qué hacer en tu computadora...")
        else:
            self.entrada.setPlaceholderText("Escríbele a Eco o usa el micrófono...")

    def iniciar_tarea(self, tarea):
        if self.agente is not None:
            self.agregar("Eco", "Ya estoy haciendo una tarea. Pulsa ⛔ Detener agente primero.")
            return
        pasos = getattr(config, "MAX_PASOS_AGENTE", 15)
        r = QMessageBox.question(
            self, "Eco va a controlar tu computadora",
            f"Tarea: {tarea}\n\n"
            f"Eco tomará el control del ratón y el teclado hasta terminar (máximo {pasos} pasos). "
            "Para detenerlo en cualquier momento: pulsa ⛔ Detener agente, o lleva el ratón "
            "a una esquina de la pantalla.\n\n¿Empezar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            self.agregar("Eco", "Tarea cancelada.")
            return

        self.agregar("Tú", tarea)
        self.agregar("Eco", "🤖 Empiezo en 3 segundos. Abre lo que necesites y no toques "
                            "el ratón ni el teclado.", estado=True)

        # la ventana de Eco se hace pequeña y se va a una esquina para no estorbar
        self._geom_previa = self.geometry()
        disponible = self.screen().availableGeometry()
        self.resize(430, 380)
        self.move(disponible.right() - 440, disponible.bottom() - 390)

        self.boton_detener.show()
        for w in (self.boton, self.boton_mic, self.entrada):
            w.setEnabled(False)

        self.agente = AgenteWorker(tarea, lambda: self._zona)
        self.agente.progreso.connect(self.agente_progreso)
        self.agente.pedir_confirmacion.connect(self.mostrar_confirmacion)
        self.agente.terminado.connect(self.tarea_terminada)
        self.agente.finished.connect(self._agente_finalizado)

        self._timer_inicio = QTimer(self)
        self._timer_inicio.setSingleShot(True)
        self._timer_inicio.timeout.connect(self.agente.start)
        self._timer_inicio.start(3000)

    def agente_progreso(self, texto):
        self.agregar("Eco", texto, estado=True)

    def mostrar_confirmacion(self, texto):
        self.raise_()
        self.activateWindow()
        r = QMessageBox.question(
            self, "Eco pide permiso", texto,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if self.agente is not None:
            self.agente.responder(r == QMessageBox.StandardButton.Yes)

    def detener_agente(self):
        if self.agente is not None:
            self.agente.detener()
            self.agregar("Eco", "⛔ Deteniendo...", estado=True)

    def tarea_terminada(self, resumen):
        self.agregar("Eco", resumen)
        if self.check_voz.isChecked():
            hablar(resumen)

    def _agente_finalizado(self):
        """Se llama cuando el hilo del agente ya terminó: se restaura la ventana."""
        if self.agente is not None:
            self.agente.wait(2000)
            self.agente = None
        self.boton_detener.hide()
        for w in (self.boton, self.boton_mic, self.entrada):
            w.setEnabled(True)
        if self._geom_previa is not None:
            self.setGeometry(self._geom_previa)
            self._geom_previa = None

    def _actualizar_zona(self):
        g = self.frameGeometry()
        r = self.devicePixelRatioF()
        self._zona = (int(g.left() * r), int(g.top() * r),
                      int(g.right() * r), int(g.bottom() * r))

    def moveEvent(self, evento):
        super().moveEvent(evento)
        self._actualizar_zona()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._actualizar_zona()

    # ---------- Pantalla en vivo ----------
    def alternar_vista(self, activo):
        if activo:
            self.columna_vista.show()
            self.actualizar_vista()
            self.timer_vista.start(getattr(config, "INTERVALO_VISTA_MS", 1500))
            self.agregar(
                "Eco",
                "👁 Ahora puedo ver tu pantalla. Solo envío una captura a Gemini cuando "
                "me haces una pregunta; la vista previa de la derecha es local.",
                estado=True)
        else:
            self.timer_vista.stop()
            self.columna_vista.hide()
            self.agregar("Eco", "Ya no veo tu pantalla.", estado=True)

    def actualizar_vista(self):
        try:
            img = capturar_imagen(ancho_max=640)
            img.thumbnail((320, 200))
            datos = img.tobytes("raw", "RGB")
            qimg = QImage(datos, img.width, img.height, img.width * 3,
                          QImage.Format.Format_RGB888).copy()
            self.vista.setPixmap(QPixmap.fromImage(qimg))
        except Exception as e:
            self.timer_vista.stop()
            self.vista.setText(f"Sin vista previa:\n{e}")

    def alternar_siempre_visible(self, activo):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, activo)
        self.show()                      # cambiar la bandera oculta la ventana
        self._excluir_de_captura()

    def _excluir_de_captura(self):
        """En Windows, hace que la ventana de Eco no salga en las capturas de pantalla,
        para que Eco vea lo que hay detrás y no a sí mismo."""
        if sys.platform != "win32" or not getattr(config, "EXCLUIR_VENTANA_DE_CAPTURA", True):
            return
        try:
            import ctypes
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            ctypes.windll.user32.SetWindowDisplayAffinity(
                int(self.winId()), WDA_EXCLUDEFROMCAPTURE)
        except Exception as e:
            print("[Eco] No pude ocultar la ventana de las capturas:", e)

    def showEvent(self, evento):
        super().showEvent(evento)
        self._excluir_de_captura()

    # ---------- Chat ----------
    def agregar(self, quien, texto, estado=False):
        """Agrega un mensaje al chat. estado=True lo muestra en cursiva (avisos)."""
        limpio = html.escape(texto).replace("\n", "<br>")
        if estado:
            limpio = f"<i>{limpio}</i>"
        self.chat.append(f"<b>{quien}:</b> {limpio}<br>")

    def nueva_conversacion_click(self):
        if self.trabajador is not None:   # espera a que Eco termine de responder
            return
        callar()
        nueva_conversacion()
        self.chat.clear()
        self.agregar("Eco", "Empecemos de nuevo. ¿En qué te ayudo?")

    # ---------- Micrófono ----------
    def alternar_microfono(self):
        if not self.grabando:
            callar()  # si Eco hablaba, se interrumpe
            try:
                self.grabadora.iniciar()
            except Exception as e:
                self.agregar("Eco", f"No pude abrir el micrófono: {e}")
                return
            self.grabando = True
            self.boton_mic.setText("⏹ Detener")
            self.agregar("Eco", "🔴 grabando... pulsa Detener cuando termines", estado=True)
        else:
            audio = self.grabadora.detener()
            self.grabando = False
            self.boton_mic.setText("🎤 Hablar")
            self.boton_mic.setEnabled(False)
            self.agregar("Eco", "transcribiendo...", estado=True)
            self.transcriptor = Transcriptor(audio)
            self.transcriptor.terminado.connect(self.texto_transcrito)
            self.transcriptor.fallo.connect(self.transcripcion_fallo)
            self.transcriptor.start()

    def texto_transcrito(self, texto):
        self.boton_mic.setEnabled(True)
        self.transcriptor = None
        if not texto:
            self.agregar("Eco", "No te escuché bien, ¿puedes repetirlo?")
            return
        self.enviar_texto(texto)

    def transcripcion_fallo(self, error):
        self.boton_mic.setEnabled(True)
        self.transcriptor = None
        self.agregar("Eco", f"Error al transcribir: {error}")

    # ---------- Envío al cerebro ----------
    def enviar(self):
        texto = self.entrada.text().strip()
        if texto:
            self.entrada.clear()
            self.enviar_texto(texto)

    def enviar_texto(self, texto):
        if self.combo_modo.currentText() == "Agente":
            self.iniciar_tarea(texto)
            return
        if self.trabajador is not None:
            self.agregar("Eco", "Espera un momento, sigo respondiendo tu pregunta anterior.")
            return
        self.agregar("Tú", texto)
        self.agregar("Eco", "pensando...", estado=True)
        self.boton.setEnabled(False)

        modo = "estudio" if self.combo_modo.currentText() == "Estudio" else "libre"
        self.trabajador = Trabajador(texto, self.check_pantalla.isChecked(), modo)
        self.trabajador.terminado.connect(self.mostrar_respuesta)
        self.trabajador.start()

    def mostrar_respuesta(self, respuesta):
        self.agregar("Eco", respuesta)
        self.boton.setEnabled(True)
        self.trabajador = None
        if self.check_voz.isChecked() and not respuesta.startswith("Eco tuvo un problema"):
            hablar(respuesta)

    # ---------- Cierre ----------
    def closeEvent(self, evento):
        self.timer_vista.stop()
        if self.agente is not None:
            if hasattr(self, "_timer_inicio"):
                self._timer_inicio.stop()
            self.agente.detener()
            self.agente.wait(5000)
        callar()
        if self.grabando:
            try:
                self.grabadora.detener()
            except Exception:
                pass
        for hilo in (self.transcriptor, self.trabajador):
            if hilo is not None:
                hilo.wait(3000)   # espera hasta 3 s a que termine
        super().closeEvent(evento)