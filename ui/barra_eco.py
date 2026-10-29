"""PERSONA 3 - Barra flotante de Eco: siempre visible en la esquina de la pantalla."""
import html
import sys
import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QFont, QGuiApplication, QIcon, QPainter, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox,
    QPushButton, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget,
)

import config
from cerebro.llm import nueva_conversacion
from ui.ventana_principal import Trabajador, Transcriptor, AgenteWorker
from voz.stt import Grabadora, _get_modelo
from voz.tts import hablar, callar

ANCHO = 460
ALTO_BARRA = 60       # barra sola
ALTO_PANEL = 330      # alto extra cuando se abre el chat
MARGEN = 14           # distancia a la esquina de la pantalla
SEGUNDOS_AUTOCIERRE = 20

COLORES = {"listo": "#3b82f6", "grabando": "#dc2626", "pensando": "#f59e0b", "agente": "#8b5cf6"}
LETRAS = {"listo": "E", "grabando": "●", "pensando": "…", "agente": "A"}

# Los estilos se limitan al marco "caja" para no afectar a los cuadros de diálogo.
ESTILO = """
#caja { background: rgba(28, 28, 34, 245); border: 1px solid #4a4a55; border-radius: 22px; }
#caja QTextEdit { background: transparent; color: #eeeeee; border: none; font-size: 13px; }
#caja QLineEdit { background: #2b2b33; color: #ffffff; border: 1px solid #444450;
                  border-radius: 17px; padding: 4px 12px; font-size: 13px; }
#caja QLineEdit:focus { border: 1px solid #3b82f6; }
#caja QPushButton { background: #2b2b33; color: white; border: none; border-radius: 16px;
                    min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px;
                    font-size: 15px; }
#caja QPushButton:hover { background: #3a3a46; }
#caja QPushButton:checked { background: #2563eb; }
#caja QPushButton:disabled { color: #777777; }
#caja QPushButton::menu-indicator { image: none; width: 0px; }
#caja #mic:checked { background: #dc2626; }
#caja #stop { background: #b00020; }
#caja #avatar { background: #3b82f6; color: white; border-radius: 20px;
                font-size: 17px; font-weight: bold; }
"""


def _icono() -> QIcon:
    """Icono de Eco dibujado por código (círculo azul con una E)."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#3b82f6"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(2, 2, 60, 60)
    p.setPen(QColor("white"))
    fuente = QFont()
    fuente.setBold(True)
    fuente.setPixelSize(38)
    p.setFont(fuente)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "E")
    p.end()
    return QIcon(pm)


class BarraEco(QWidget):
    _zona = (0, 0, 0, 0)   # área que ocupa la barra (el agente no hace clic ahí)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Eco")
        self.setWindowIcon(_icono())
        self.setStyleSheet(ESTILO)

        self.modo = "Estudio"
        self.trabajador = None
        self.transcriptor = None
        self.agente = None
        self.grabadora = Grabadora()
        self.grabando = False
        self._abierto = False
        self._arrastre = None
        self._press_en_avatar = False

        # --- Piezas de la barra ---
        self.avatar = QLabel("E")
        self.avatar.setObjectName("avatar")
        self.avatar.setFixedSize(40, 40)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setCursor(Qt.CursorShape.PointingHandCursor)

        self.entrada = QLineEdit()
        self.entrada.setMinimumHeight(34)

        self.boton_ojo = self._boton("👁", "Dejar que Eco vea mi pantalla", checkable=True)
        self.boton_mic = self._boton("🎤", "Hablar con Eco (clic para empezar y otra vez para terminar)",
                                     checkable=True, nombre="mic")
        self.boton_stop = self._boton("⛔", "Detener la tarea de Eco", nombre="stop")
        self.boton_stop.hide()
        self.boton_abrir = self._boton("▴", "Abrir o cerrar el chat")
        self.boton_menu = self._boton("⋯", "Más opciones")

        # --- Panel de chat (oculto hasta que haga falta) ---
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.panel = QWidget()
        lp = QVBoxLayout(self.panel)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.addWidget(self.chat)
        self.panel.hide()

        # --- Distribución ---
        caja = QFrame()
        caja.setObjectName("caja")
        v = QVBoxLayout(caja)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)
        v.addWidget(self.panel, 1)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        fila.addWidget(self.avatar)
        fila.addWidget(self.entrada, 1)
        for b in (self.boton_ojo, self.boton_mic, self.boton_stop,
                  self.boton_abrir, self.boton_menu):
            fila.addWidget(b)
        v.addLayout(fila)
        externo = QVBoxLayout(self)
        externo.setContentsMargins(0, 0, 0, 0)
        externo.addWidget(caja)

        self._crear_menu()
        self._crear_bandeja()

        # --- Conexiones ---
        self.entrada.returnPressed.connect(self.enviar)
        self.boton_mic.clicked.connect(self.alternar_microfono)
        self.boton_ojo.toggled.connect(self.alternar_ojo)
        self.boton_abrir.clicked.connect(self.alternar_panel)
        self.boton_stop.clicked.connect(self.detener_agente)

        self._timer_cerrar = QTimer(self)
        self._timer_cerrar.setSingleShot(True)
        self._timer_cerrar.timeout.connect(self._autocerrar)

        self.setFixedSize(ANCHO, ALTO_BARRA)
        self._colocar_esquina()
        self._estado("listo")
        self._placeholder()
        self._tooltip_avatar()
        self.agregar("Eco", "Hola, soy Eco. ¿En qué te ayudo?", abrir=False)

        # Carga Whisper en segundo plano para que el primer mensaje de voz no espere
        threading.Thread(target=_get_modelo, daemon=True).start()

    # ---------- Construcción ----------
    def _boton(self, texto, tip, checkable=False, nombre=""):
        b = QPushButton(texto)
        b.setToolTip(tip)
        b.setCheckable(checkable)
        if nombre:
            b.setObjectName(nombre)
        return b

    def _crear_menu(self):
        menu = QMenu(self)
        sub = menu.addMenu("Modo")
        self._grupo_modo = QActionGroup(self)
        self._grupo_modo.setExclusive(True)
        for nombre in ("Estudio", "Libre", "Agente"):
            a = QAction(nombre, self)
            a.setCheckable(True)
            a.setChecked(nombre == self.modo)
            a.triggered.connect(lambda _=False, n=nombre: self.cambiar_modo(n))
            self._grupo_modo.addAction(a)
            sub.addAction(a)
        self.accion_voz = QAction("Eco habla en voz alta", self)
        self.accion_voz.setCheckable(True)
        self.accion_voz.setChecked(True)
        menu.addAction(self.accion_voz)
        menu.addAction("🗑 Nueva conversación", self.nueva_conversacion_click)
        menu.addSeparator()
        menu.addAction("Ocultar (sigue en la bandeja)", self.hide)
        menu.addAction("Salir de Eco", self.salir)
        self.boton_menu.setMenu(menu)
        self._menu = menu

    def _crear_bandeja(self):
        self.bandeja = QSystemTrayIcon(_icono(), self)
        self.bandeja.setToolTip("Eco")
        menu = QMenu()
        menu.addAction("Mostrar / ocultar", self._alternar_visible)
        menu.addAction("Salir de Eco", self.salir)
        self.bandeja.setContextMenu(menu)
        self._menu_bandeja = menu
        self.bandeja.activated.connect(self._clic_bandeja)
        self.bandeja.show()

    # ---------- Posición, tamaño y ventana ----------
    def _colocar_esquina(self):
        disp = QGuiApplication.primaryScreen().availableGeometry()
        self.move(disp.right() - self.width() - MARGEN, disp.bottom() - self.height() - MARGEN)

    def _redimensionar(self, abierto):
        """Abre o cierra el chat manteniendo fija la esquina inferior derecha."""
        esquina = self.geometry().bottomRight()
        alto = ALTO_BARRA + (ALTO_PANEL if abierto else 0)
        self.panel.setVisible(abierto)
        self.setFixedSize(ANCHO, alto)
        x = esquina.x() - ANCHO + 1
        y = esquina.y() - alto + 1
        disp = self.screen().availableGeometry() if self.screen() else None
        if disp is not None:
            y = max(disp.top(), y)
            x = max(disp.left(), x)
        self.move(x, y)

    def _abrir_panel(self):
        if not self._abierto:
            self._abierto = True
            self._redimensionar(True)
            self.boton_abrir.setText("▾")
        self._timer_cerrar.start(SEGUNDOS_AUTOCIERRE * 1000)

    def _cerrar_panel(self):
        if self._abierto:
            self._abierto = False
            self._redimensionar(False)
            self.boton_abrir.setText("▴")

    def alternar_panel(self):
        if self._abierto:
            self._cerrar_panel()
        else:
            self._abrir_panel()

    def _ocupado(self):
        return bool(self.trabajador or self.transcriptor or self.agente or self.grabando)

    def _autocerrar(self):
        if not self._abierto:
            return
        if self._ocupado() or self.underMouse():
            self._timer_cerrar.start(10000)   # lo vuelve a intentar más tarde
        else:
            self._cerrar_panel()

    def _alternar_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _clic_bandeja(self, motivo):
        if motivo == QSystemTrayIcon.ActivationReason.Trigger:
            self._alternar_visible()

    # ---------- Que Eco no se vea a sí mismo en las capturas ----------
    def _excluir_de_captura(self):
        if sys.platform != "win32" or not getattr(config, "EXCLUIR_VENTANA_DE_CAPTURA", True):
            return
        try:
            import ctypes
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            ctypes.windll.user32.SetWindowDisplayAffinity(
                int(self.winId()), WDA_EXCLUDEFROMCAPTURE)
        except Exception as e:
            print("[Eco] No pude ocultar la barra de las capturas:", e)

    def _actualizar_zona(self):
        g = self.frameGeometry()
        r = self.devicePixelRatioF()
        self._zona = (int(g.left() * r), int(g.top() * r),
                      int(g.right() * r), int(g.bottom() * r))

    def showEvent(self, evento):
        super().showEvent(evento)
        self._excluir_de_captura()
        self._actualizar_zona()
        self.entrada.setFocus()

    def moveEvent(self, evento):
        super().moveEvent(evento)
        self._actualizar_zona()

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._actualizar_zona()

    def closeEvent(self, evento):
        evento.ignore()   # cerrar solo oculta; se sale desde el menú "Salir de Eco"
        self.hide()

    def keyPressEvent(self, evento):
        if evento.key() == Qt.Key.Key_Escape:
            self._cerrar_panel()
        else:
            super().keyPressEvent(evento)

    # ---------- Arrastrar la barra / clic en el avatar ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._arrastre = [e.globalPosition().toPoint(), self.frameGeometry().topLeft(), False]
            self._press_en_avatar = self.childAt(e.position().toPoint()) is self.avatar
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._arrastre and (e.buttons() & Qt.MouseButton.LeftButton):
            inicio, esquina, movido = self._arrastre
            delta = e.globalPosition().toPoint() - inicio
            if movido or delta.manhattanLength() > 4:
                self._arrastre[2] = True
                self.move(esquina + delta)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._arrastre:
            movido = self._arrastre[2]
            self._arrastre = None
            if not movido and self._press_en_avatar:
                self.alternar_panel()
        super().mouseReleaseEvent(e)

    # ---------- Estado visual ----------
    def _estado(self, nombre):
        self.avatar.setText(LETRAS[nombre])
        self.avatar.setStyleSheet(f"background: {COLORES[nombre]};")

    def _placeholder(self):
        if self.modo == "Agente":
            self.entrada.setPlaceholderText("Dile a Eco qué hacer en tu computadora...")
        else:
            self.entrada.setPlaceholderText(f"Pregúntale a Eco ({self.modo.lower()})...")

    def _tooltip_avatar(self):
        self.avatar.setToolTip(f"Eco · modo {self.modo}\nClic: abrir o cerrar el chat · Arrastra para mover")

    def cambiar_modo(self, modo):
        self.modo = modo
        self._placeholder()
        self._tooltip_avatar()
        self.agregar("Eco", f"Modo {modo} activado.", estado=True, abrir=False)

    def alternar_ojo(self, activo):
        if activo:
            self.agregar("Eco", "👁 Ahora puedo ver tu pantalla cuando me preguntes. "
                                "Solo envío una captura al hacer una pregunta.", estado=True)
        else:
            self.agregar("Eco", "Ya no veo tu pantalla.", estado=True, abrir=False)

    # ---------- Chat ----------
    def agregar(self, quien, texto, estado=False, abrir=True):
        limpio = html.escape(texto).replace("\n", "<br>")
        if estado:
            limpio = f"<i>{limpio}</i>"
        self.chat.append(f"<b>{quien}:</b> {limpio}<br>")
        if abrir:
            self._abrir_panel()

    def nueva_conversacion_click(self):
        if self.trabajador is not None:
            return
        callar()
        nueva_conversacion()
        self.chat.clear()
        self.agregar("Eco", "Empecemos de nuevo. ¿En qué te ayudo?", abrir=False)

    def _al_terminar(self, nombre):
        """Libera un hilo cuando ya terminó de verdad (evita avisos de QThread)."""
        hilo = getattr(self, nombre)
        if hilo is not None:
            hilo.wait(2000)
            setattr(self, nombre, None)

    # ---------- Micrófono ----------
    def alternar_microfono(self):
        if not self.grabando:
            callar()   # si Eco hablaba, se interrumpe
            try:
                self.grabadora.iniciar()
            except Exception as e:
                self.boton_mic.setChecked(False)
                self.agregar("Eco", f"No pude abrir el micrófono: {e}")
                return
            self.grabando = True
            self._estado("grabando")
            self.entrada.setPlaceholderText("🔴 Te escucho... pulsa 🎤 otra vez para terminar")
        else:
            audio = self.grabadora.detener()
            self.grabando = False
            self.boton_mic.setChecked(False)
            self.boton_mic.setEnabled(False)
            self._estado("pensando")
            self._placeholder()
            self.transcriptor = Transcriptor(audio)
            self.transcriptor.terminado.connect(self.texto_transcrito)
            self.transcriptor.fallo.connect(self.transcripcion_fallo)
            self.transcriptor.finished.connect(lambda: self._al_terminar("transcriptor"))
            self.transcriptor.start()

    def texto_transcrito(self, texto):
        self.boton_mic.setEnabled(True)
        if not texto:
            self._estado("listo")
            self.agregar("Eco", "No te escuché bien, ¿puedes repetirlo?")
            return
        self.enviar_texto(texto)

    def transcripcion_fallo(self, error):
        self.boton_mic.setEnabled(True)
        self._estado("listo")
        self.agregar("Eco", f"Error al transcribir: {error}")

    # ---------- Envío al cerebro ----------
    def enviar(self):
        texto = self.entrada.text().strip()
        if texto:
            self.entrada.clear()
            self.enviar_texto(texto)

    def enviar_texto(self, texto):
        if self.modo == "Agente":
            self.iniciar_tarea(texto)
            return
        if self.trabajador is not None:
            self.agregar("Eco", "Espera un momento, sigo respondiendo tu pregunta anterior.")
            return
        self.agregar("Tú", texto)
        self.agregar("Eco", "pensando...", estado=True)
        self._estado("pensando")
        modo_llm = "estudio" if self.modo == "Estudio" else "libre"
        self.trabajador = Trabajador(texto, self.boton_ojo.isChecked(), modo_llm)
        self.trabajador.terminado.connect(self.mostrar_respuesta)
        self.trabajador.finished.connect(lambda: self._al_terminar("trabajador"))
        self.trabajador.start()

    def mostrar_respuesta(self, respuesta):
        self.agregar("Eco", respuesta)
        self._estado("listo")
        if self.accion_voz.isChecked() and not respuesta.startswith("Eco tuvo un problema"):
            hablar(respuesta)

    # ---------- Agente (controla el PC) ----------
    def iniciar_tarea(self, tarea):
        if self.agente is not None:
            self.agregar("Eco", "Ya estoy haciendo una tarea. Pulsa ⛔ para detenerla.")
            return
        pasos = getattr(config, "MAX_PASOS_AGENTE", 15)
        r = QMessageBox.question(
            self, "Eco va a controlar tu computadora",
            f"Tarea: {tarea}\n\n"
            f"Eco tomará el control del ratón y el teclado hasta terminar (máximo {pasos} pasos). "
            "Para detenerlo en cualquier momento: pulsa ⛔ en la barra, o lleva el ratón "
            "a una esquina de la pantalla.\n\n¿Empezar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            self.agregar("Eco", "Tarea cancelada.")
            return

        self.agregar("Tú", tarea, abrir=False)
        self.agregar("Eco", "🤖 Empiezo en 3 segundos. Abre lo que necesites y no toques "
                            "el ratón ni el teclado.", estado=True, abrir=False)
        self._cerrar_panel()          # la barra queda pequeña para no estorbar
        self._estado("agente")
        self.boton_stop.show()
        for w in (self.entrada, self.boton_mic, self.boton_ojo):
            w.setEnabled(False)
        self.entrada.setPlaceholderText("🤖 Empezando en 3 segundos...")

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
        self.entrada.setPlaceholderText("🤖 " + texto[:70])
        self.agregar("Eco", texto, estado=True, abrir=False)

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
            self.entrada.setPlaceholderText("⛔ Deteniendo...")

    def tarea_terminada(self, resumen):
        self.agregar("Eco", resumen)
        if self.accion_voz.isChecked():
            hablar(resumen)

    def _agente_finalizado(self):
        """Se llama cuando el hilo del agente ya terminó: la barra vuelve a la normalidad."""
        if self.agente is not None:
            self.agente.wait(2000)
            self.agente = None
        self.boton_stop.hide()
        for w in (self.entrada, self.boton_mic, self.boton_ojo):
            w.setEnabled(True)
        self._estado("listo")
        self._placeholder()

    def detener_agente_y_salir(self):
        if self.agente is not None:
            if hasattr(self, "_timer_inicio"):
                self._timer_inicio.stop()
            self.agente.detener()
            self.agente.wait(5000)

    # ---------- Salir ----------
    def salir(self):
        self._timer_cerrar.stop()
        if self.grabando:
            try:
                self.grabadora.detener()
            except Exception:
                pass
        self.detener_agente_y_salir()
        callar()
        for hilo in (self.transcriptor, self.trabajador):
            if hilo is not None:
                hilo.wait(3000)
        self.bandeja.hide()
        QApplication.quit()
