import sys, os, json, threading, math, random, re
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from main import main as start_voice
from modules.controller import execute_system_command
from modules.ai_brain import generate_response, generate_webhook_json, generate_macro_json
from modules.tts import speak

STYLE = """
QMainWindow { background-color: #0b0b14; }
QTabWidget::pane { border: 1px solid #252538; background: #12121e; border-radius: 8px; }
QTabBar::tab { background: #151525; color: #a6adc8; padding: 12px 30px; border-radius: 6px; margin-right: 5px; font-weight: bold; }
QTabBar::tab:selected { background: #252538; color: #00e5ff; }

QLabel { color: #e0e0e0; font-family: 'Segoe UI'; font-size: 13px; }
QLabel#title { color: #00e5ff; font-size: 20px; font-weight: bold; margin-bottom: 5px; }
QLabel#subtitle { color: #b052ff; font-size: 16px; font-weight: bold; }
QLabel#desc { color: #8888a0; font-size: 12px; margin-bottom: 5px; }

QLineEdit, QTextEdit, QTextBrowser, QComboBox, QSpinBox, QDoubleSpinBox { 
    background: rgba(20, 20, 30, 220); 
    border: 1px solid #3b3b54; 
    color: #ffffff; 
    padding: 10px; 
    border-radius: 8px; 
    font-size: 14px; 
}
QLineEdit:focus, QTextEdit:focus, QTextBrowser:focus, QComboBox:focus, QSpinBox:focus { 
    border: 1px solid #00e5ff; 
    background: rgba(30, 30, 45, 250); 
}

QPushButton { background: #1a1a2e; border: 1px solid #252538; color: #00e5ff; font-weight: bold; border-radius: 8px; padding: 10px 20px; font-size: 13px; }
QPushButton:hover { background: #252538; border: 1px solid #00e5ff; }
QPushButton#primary { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00e5ff, stop:1 #b052ff); color: #000000; border: none; }
QPushButton#primary:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #33ebff, stop:1 #c27aff); }
QPushButton#danger { background: #1a1a2e; border: 1px solid #8d1f2b; color: #ff4d4d; }
QPushButton#danger:hover { background: #8d1f2b; color: white; }
QPushButton#tool { padding: 5px; min-width: 30px; }
QPushButton#gear { font-size: 24px; padding: 5px; border: none; background: transparent; color: #00e5ff;}
QPushButton#gear:hover { color: #b052ff; }

QListWidget#HorizCats { background: transparent; border: none; outline: none; }
QListWidget#HorizCats::item { background: #151525; color: #a6adc8; padding: 10px 20px; border-radius: 8px; margin-right: 10px; border: 1px solid #252538; text-align: center; }
QListWidget#HorizCats::item:selected { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1a2e, stop:1 #151525); color: #00e5ff; border: 1px solid #00e5ff; font-weight: bold; }
QListWidget#VertMacros { background: transparent; border: 1px solid #252538; border-radius: 8px; outline: none; }
QListWidget#VertMacros::item { padding: 15px; border-bottom: 1px solid #1a1a2e; color: #ffffff;}
QListWidget#VertMacros::item:selected { background: #252538; color: #b052ff; font-weight: bold; border-left: 4px solid #b052ff; }

QScrollBar:horizontal { background: transparent; height: 10px; margin: 0px; }
QScrollBar::handle:horizontal { background: #3b3b54; border-radius: 5px; min-width: 20px; }
QScrollBar::handle:horizontal:hover { background: #00e5ff; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0px; }
QScrollBar::handle:vertical { background: #3b3b54; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #00e5ff; }

QMenu { background-color: #151525; border: 1px solid #3b3b54; border-radius: 6px; color: #ffffff; font-size: 14px; }
QMenu::item { padding: 10px 30px; }
QMenu::item:selected { background-color: #252538; color: #00e5ff; }
"""

class WaveformBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = "idle"
        self.phase = 0.0; self.amplitude = 10.0; self.target_amplitude = 10.0; self.speed = 0.02
        self.timer = QTimer(self); self.timer.timeout.connect(self.animate); self.timer.start(16)

    def animate(self):
        if self.status == "idle": 
            self.target_amplitude = 15.0; self.speed = 0.02
        elif self.status == "listening": 
            self.target_amplitude = 60.0; self.speed = 0.04
        elif self.status == "processing": 
            self.target_amplitude = 40.0; self.speed = 0.15 
        elif self.status == "speaking": 
            pulse = math.sin(self.phase * 3.0) * math.cos(self.phase * 7.0) + math.sin(self.phase * 13.0) * 0.5
            self.target_amplitude = 60.0 + (pulse * 50.0); self.speed = 0.08
            
        self.amplitude += (self.target_amplitude - self.amplitude) * 0.1
        self.phase += self.speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0b0b14"))
        width = self.width(); height = self.height(); mid_y = height / 2

        layers = [
            {"color": QColor(176, 82, 255, 80), "freq_mult": 0.8, "amp_mult": 1.2, "phase_mult": 1.5, "thickness": 2},
            {"color": QColor(0, 229, 255, 120), "freq_mult": 1.0, "amp_mult": 0.8, "phase_mult": 1.0, "thickness": 3},
            {"color": QColor(255, 255, 255, 200), "freq_mult": 1.2, "amp_mult": 0.5, "phase_mult": 2.0, "thickness": 1}
        ]
        for layer in layers:
            path = QPainterPath(); path.moveTo(0, mid_y)
            freq = 0.005 * layer["freq_mult"]; amp = self.amplitude * layer["amp_mult"]; offset = self.phase * layer["phase_mult"]
            for x in range(0, width, 5):
                edge_damping = math.sin(math.pi * (x / width)) 
                y = mid_y + math.sin(x * freq + offset) * (amp * edge_damping)
                path.lineTo(x, y)
            painter.setPen(QPen(layer["color"], layer["thickness"])); painter.drawPath(path)

class HorizontalListWidget(QListWidget):
    def wheelEvent(self, event):
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - event.angleDelta().y())

class HotkeyInput(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True); self.setPlaceholderText("Клікніть і натисніть клавіші...")
        self.setStyleSheet("background: rgba(42, 42, 64, 250); color: #00e5ff; font-weight: bold;")
    def keyPressEvent(self, event):
        mods = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier: mods.append("ctrl")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: mods.append("shift")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier: mods.append("alt")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier: mods.append("win")
        key = event.key()
        if key not in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            key_name = QKeySequence(key).toString().lower()
            if key_name:
                mods.append(key_name); self.setText("+".join(mods))

class ActionRow(QFrame):
    def __init__(self, act_type="Функція", act_val="", parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: #12121e; border: 1px solid #252538; border-radius: 8px; }")
        self.l = QHBoxLayout(self); self.l.setContentsMargins(10, 10, 10, 10); self.l.setSpacing(10)
        self.cb_type = QComboBox(); self.cb_type.setFixedWidth(130)
        self.cb_type.addItems(["Функція", "Медіа", "Гучність", "Клавіша", "Затримка", "Система", "Посилання", "Файл"])
        self.cb_type.setCurrentText(act_type); self.cb_type.currentTextChanged.connect(self.build_val_widget)
        self.l.addWidget(self.cb_type)
        self.val_layout = QHBoxLayout(); self.val_layout.setContentsMargins(0,0,0,0)
        self.l.addLayout(self.val_layout, stretch=1)
        self.val_widget = None; self.extra_widget = None
        btn_del = QPushButton("❌"); btn_del.setObjectName("danger"); btn_del.setFixedSize(40, 40)
        btn_del.clicked.connect(self.deleteLater); self.l.addWidget(btn_del)
        self.current_val = act_val; self.build_val_widget(act_type)

    def build_val_widget(self, text):
        if self.val_widget: self.val_widget.deleteLater(); self.val_widget = None
        if self.extra_widget: self.extra_widget.deleteLater(); self.extra_widget = None

        if text == "Функція":
            self.val_widget = QComboBox()
            opts = {"🌤 Прогноз погоди": "погода", "🕒 Поточний час": "час", "🎉 Яке сьогодні свято": "свято", "🔍 Веб-пошук (Google)": "пошук"}
            for k, v in opts.items(): self.val_widget.addItem(k, v)
            idx = self.val_widget.findData(str(self.current_val)); 
            if idx >= 0: self.val_widget.setCurrentIndex(idx)
        elif text == "Медіа":
            self.val_widget = QComboBox()
            opts = {"▶/⏸ Старт / Пауза": "playpause", "⏭ Наступний трек": "nexttrack", "⏮ Попередній трек": "prevtrack", "🔇 Вимкнути звук": "volumemute"}
            for k, v in opts.items(): self.val_widget.addItem(k, v)
            idx = self.val_widget.findData(str(self.current_val)); 
            if idx >= 0: self.val_widget.setCurrentIndex(idx)
        elif text == "Гучність":
            # --- ОНОВЛЕНО ТУТ: Додано Встановити (%) ---
            self.val_widget = QComboBox(); self.val_widget.addItems(["🔊 Збільшити", "🎯 Встановити (%)", "🔉 Зменшити"])
            self.extra_widget = QSpinBox(); self.extra_widget.setRange(0, 100); self.extra_widget.setSuffix(" %"); self.extra_widget.setFixedWidth(100)
            
            val_str = str(self.current_val)
            if "up" in val_str: self.val_widget.setCurrentText("🔊 Збільшити")
            elif "down" in val_str: self.val_widget.setCurrentText("🔉 Зменшити")
            elif "set" in val_str: self.val_widget.setCurrentText("🎯 Встановити (%)")
            
            if ":" in val_str:
                try: self.extra_widget.setValue(int(val_str.split(":")[1]))
                except: self.extra_widget.setValue(50)
            else: self.extra_widget.setValue(20)
        elif text == "Система":
            self.val_widget = QComboBox()
            opts = {"💤 Сплячий режим ПК": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0", "📁 Відкрити Провідник": "start explorer", "🔌 Вимкнути ПК": "shutdown /s /t 0"}
            for k, v in opts.items(): self.val_widget.addItem(k, v)
            idx = self.val_widget.findData(str(self.current_val))
            if idx >= 0: self.val_widget.setCurrentIndex(idx)
        elif text == "Затримка":
            self.val_widget = QDoubleSpinBox(); self.val_widget.setRange(0.1, 30.0); self.val_widget.setSuffix(" сек"); self.val_widget.setSingleStep(0.5)
            try: self.val_widget.setValue(float(self.current_val))
            except: self.val_widget.setValue(1.0)
        elif text == "Клавіша":
            self.val_widget = HotkeyInput(); self.val_widget.setText(str(self.current_val))
        elif text == "Посилання":
            self.val_widget = QLineEdit(str(self.current_val)); self.val_widget.setPlaceholderText("https://...")
        elif text == "Файл":
            self.val_widget = QLineEdit(str(self.current_val)); self.val_widget.setPlaceholderText("Шлях до файлу")
            self.extra_widget = QPushButton("📂"); self.extra_widget.setFixedSize(40, 40)
            self.extra_widget.clicked.connect(lambda: self.val_widget.setText(QFileDialog.getOpenFileName(self, "Файл")[0] or self.val_widget.text()))

        self.val_layout.addWidget(self.val_widget)
        if self.extra_widget: self.val_layout.addWidget(self.extra_widget)

    def get_data(self):
        t = self.cb_type.currentText()
        if t == "Гучність":
            txt = self.val_widget.currentText()
            if "Збільшити" in txt: cmd = "volumeup"
            elif "Зменшити" in txt: cmd = "volumedown"
            else: cmd = "volumeset" # Встановити
            v = f"{cmd}:{self.extra_widget.value()}"
        elif isinstance(self.val_widget, QComboBox): v = self.val_widget.currentData()
        elif isinstance(self.val_widget, QDoubleSpinBox): v = str(self.val_widget.value())
        else: v = self.val_widget.text().strip()
        return {"type": t, "value": v}

class FloatingCore(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(120, 120); self.status = "idle"; self.angle = 0; self.speed = 2
        self.timer = QTimer(self); self.timer.timeout.connect(self.animate); self.timer.start(30)
        
    def animate(self): 
        self.angle = (self.angle + self.speed) % 360; self.update()
        
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor("#00e5ff") if self.status == "idle" else QColor("#b052ff")
        if self.status == "mic_off": c = QColor("#ff4d4d")
        r = 35 + math.sin(self.angle * 0.05) * 6
        p.setPen(QPen(c, 2)); p.drawEllipse(int(60-r), int(60-r), int(r*2), int(r*2))
        p.setBrush(QColor("#12121e")); p.drawEllipse(int(60-r+4), int(60-r+4), int((r-4)*2), int((r-4)*2))
        p.setPen(c); p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold)); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "AVE")
        
    def mousePressEvent(self, e): self.dragPos = e.globalPosition().toPoint()
    def mouseMoveEvent(self, e): self.move(self.pos() + e.globalPosition().toPoint() - self.dragPos); self.dragPos = e.globalPosition().toPoint()
    def mouseDoubleClickEvent(self, e): self.hide(); self.parent.show()


class AveMainWindow(QMainWindow):
    update_signal = pyqtSignal(str, str)
    webhook_signal = pyqtSignal(dict)
    macro_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AVE // COMMAND CENTER")
        self.resize(1150, 800); self.setStyleSheet(STYLE)
        self.mini = FloatingCore(self)
        self.app_state = {'mic_active': True}
        self.macros_data_cache = {}; self.webhooks_cache = []
        self.current_cat_name = ""; self.current_macro_name = ""
        
        self.init_tray()
        self.init_ui()
        self.update_signal.connect(self.update_gui)
        self.webhook_signal.connect(self.on_webhook_generated)
        self.macro_signal.connect(self.on_macro_generated)
        
        threading.Thread(target=start_voice, args=(self.update_signal.emit, self.app_state), daemon=True).start()

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("favicon.ico") if os.path.exists("favicon.ico") else QIcon())
        tray_menu = QMenu(); show_action = tray_menu.addAction("Розгорнути AVE")
        show_action.triggered.connect(self.showNormal); quit_action = tray_menu.addAction("Вихід")
        quit_action.triggered.connect(sys.exit)
        self.tray_icon.setContextMenu(tray_menu); self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick: self.showNormal()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized(): self.hide(); event.ignore()

    def init_ui(self):
        self.main_stack = QStackedWidget()
        self.setCentralWidget(self.main_stack)

        # --- СТОРІНКА 0: ДАШБОРД ---
        self.dash_bg = WaveformBackground()
        
        dash_lay = QVBoxLayout(self.dash_bg)
        dash_lay.setContentsMargins(50, 50, 50, 50)
        
        header = QHBoxLayout()
        self.lbl_status = QLabel("СИСТЕМА: ОНЛАЙН"); self.lbl_status.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #00e5ff; background: transparent;")
        header.addWidget(self.lbl_status); header.addStretch()
        
        self.btn_mic = QPushButton("🎙 Мікрофон: УВІМКНЕНО"); self.btn_mic.clicked.connect(self.toggle_mic)
        self.btn_mic.setStyleSheet("background: rgba(26, 26, 46, 200); color: #a6e3a1; font-weight: bold;")
        btn_mini = QPushButton("МІНІ-РЕЖИМ"); btn_mini.clicked.connect(lambda: (self.hide(), self.mini.show()))
        btn_set = QPushButton("⚙"); btn_set.setObjectName("gear"); btn_set.clicked.connect(lambda: self.main_stack.setCurrentIndex(1))
        
        header.addWidget(self.btn_mic); header.addWidget(btn_mini); header.addWidget(btn_set)
        dash_lay.addLayout(header)

        self.log = QTextBrowser()
        self.log.setOpenExternalLinks(True)
        self.log.setStyleSheet("background: rgba(10, 10, 15, 150); border: 1px solid rgba(0, 229, 255, 50); color: #ffffff; padding: 15px; border-radius: 12px;")
        dash_lay.addWidget(self.log)

        inp_lay = QHBoxLayout(); self.query_input = QLineEdit(); self.query_input.setPlaceholderText("Введіть команду або запит для Аве...")
        self.query_input.returnPressed.connect(self.send_text)
        btn_send = QPushButton("ВІДПРАВИТИ"); btn_send.setObjectName("primary"); btn_send.clicked.connect(self.send_text)
        inp_lay.addWidget(self.query_input); inp_lay.addWidget(btn_send); dash_lay.addLayout(inp_lay)

        self.main_stack.addWidget(self.dash_bg)

        # --- СТОРІНКА 1: НАЛАШТУВАННЯ ---
        sett_wrap = QWidget(); sw_lay = QVBoxLayout(sett_wrap); sw_lay.setContentsMargins(20, 20, 20, 20)
        set_head = QHBoxLayout(); btn_back = QPushButton("🡄 НАЗАД ДО ДАШБОРДУ"); btn_back.clicked.connect(lambda: self.main_stack.setCurrentIndex(0))
        set_head.addWidget(btn_back); set_head.addStretch(); sw_lay.addLayout(set_head)
        
        self.sub_tabs = QTabWidget()
        
        # --- ТАБ 1: АВТОМАТИЗАЦІЯ ---
        tab_cmd = QWidget(); cmd_lay = QVBoxLayout(tab_cmd); cmd_lay.setContentsMargins(15, 15, 15, 15)
        cat_top_lay = QHBoxLayout(); cat_top_lay.addWidget(self.mk_lbl("Категорії:", "title"))
        btn_add_cat = QPushButton("+ Створити"); btn_add_cat.setObjectName("tool"); btn_add_cat.clicked.connect(self.add_category_dialog)
        cat_top_lay.addWidget(btn_add_cat); cat_top_lay.addStretch(); cmd_lay.addLayout(cat_top_lay)

        self.list_cats = HorizontalListWidget(); self.list_cats.setObjectName("HorizCats")
        self.list_cats.setFlow(QListView.Flow.LeftToRight); self.list_cats.setWrapping(False); self.list_cats.setFixedHeight(75) 
        self.list_cats.itemSelectionChanged.connect(self.on_category_select)
        self.list_cats.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_cats.customContextMenuRequested.connect(self.show_cat_context_menu)
        cmd_lay.addWidget(self.list_cats)

        split = QSplitter(Qt.Orientation.Horizontal)
        mac_panel = QWidget(); mac_lay = QVBoxLayout(mac_panel); mac_lay.setContentsMargins(0,10,0,0)
        mac_lay.addWidget(self.mk_lbl("Макроси (Команди):", "subtitle"))
        self.list_macros = QListWidget(); self.list_macros.setObjectName("VertMacros")
        self.list_macros.itemSelectionChanged.connect(self.on_macro_select)
        self.list_macros.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_macros.customContextMenuRequested.connect(self.show_mac_context_menu)
        mac_lay.addWidget(self.list_macros)
        
        btn_add_mac = QPushButton("+ Створити вручну"); btn_add_mac.clicked.connect(self.create_macro)
        mac_lay.addWidget(btn_add_mac)
        btn_ai_mac = QPushButton("✨ Згенерувати Макрос через ШІ"); btn_ai_mac.setObjectName("primary"); btn_ai_mac.clicked.connect(self.create_ai_macro)
        mac_lay.addWidget(btn_ai_mac)
        split.addWidget(mac_panel)

        self.editor_scroll = QScrollArea(); self.editor_scroll.setWidgetResizable(True); self.editor_scroll.setStyleSheet("border: none;")
        self.editor_w = QWidget(); self.ed_lay = QVBoxLayout(self.editor_w); self.ed_lay.setContentsMargins(20, 10, 10, 10)
        self.lbl_mac_title = self.mk_lbl("Оберіть макрос для редагування", "subtitle"); self.ed_lay.addWidget(self.lbl_mac_title)
        
        self.form_content = QWidget(); fc_lay = QVBoxLayout(self.form_content); fc_lay.setContentsMargins(0,0,0,0)
        fc_lay.addWidget(self.mk_lbl("Слова-тригери (через кому):", "desc")); self.inp_triggers = QLineEdit(); fc_lay.addWidget(self.inp_triggers)
        fc_lay.addSpacing(10); fc_lay.addWidget(self.mk_lbl("Ланцюжок дій (зверху вниз):", "desc"))
        self.actions_container = QWidget(); self.actions_lay = QVBoxLayout(self.actions_container); self.actions_lay.setContentsMargins(0,0,0,0)
        fc_lay.addWidget(self.actions_container)
        btn_add_act = QPushButton("+ ДОДАТИ КРОК ДО ЛАНЦЮЖКА"); btn_add_act.clicked.connect(lambda: self.add_action_row("Затримка", "1.0"))
        fc_lay.addWidget(btn_add_act)
        fc_lay.addSpacing(10); fc_lay.addWidget(self.mk_lbl("Кастомна відповідь Аве (опціонально):", "desc"))
        self.inp_response = QTextEdit(); self.inp_response.setMaximumHeight(80); fc_lay.addWidget(self.inp_response)
        
        btn_save_mac = QPushButton("✓ ПРИЙНЯТИ ЗМІНИ МАКРОСУ"); btn_save_mac.setObjectName("primary"); btn_save_mac.clicked.connect(self.save_macro_to_cache)
        fc_lay.addWidget(btn_save_mac)
        
        self.ed_lay.addWidget(self.form_content); self.ed_lay.addStretch(); self.form_content.hide()
        self.editor_scroll.setWidget(self.editor_w); split.addWidget(self.editor_scroll)
        split.setSizes([250, 750]); cmd_lay.addWidget(split)
        self.sub_tabs.addTab(tab_cmd, "АВТОМАТИЗАЦІЯ")

        # --- ТАБ 2: ШІ ТА ЛОКАЛІЗАЦІЯ ---
        tab_dev = QWidget(); dev_lay = QVBoxLayout(tab_dev); dev_lay.setContentsMargins(30, 30, 30, 30); dev_lay.setSpacing(20)
        
        g1 = QGridLayout(); g1.setVerticalSpacing(15); g1.setHorizontalSpacing(20)
        g1.addWidget(self.mk_lbl("Локалізація та Голос", "subtitle"), 0, 0, 1, 2)
        g1.addWidget(QLabel("Мова інтерфейсу:"), 1, 0); self.cb_ui_lang = QComboBox(); self.cb_ui_lang.addItems(["Українська", "English"]); g1.addWidget(self.cb_ui_lang, 1, 1)
        g1.addWidget(QLabel("Мова розпізнавання:"), 2, 0); self.cb_stt_lang = QComboBox(); self.cb_stt_lang.addItems(["uk-UA", "en-US"]); g1.addWidget(self.cb_stt_lang, 2, 1)
        g1.addWidget(QLabel("Голос Аве:"), 3, 0); self.cb_voice = QComboBox(); self.cb_voice.addItems(["PolinaNeural (Жіночий)", "OstapNeural (Чоловічий)"]); g1.addWidget(self.cb_voice, 3, 1)
        dev_lay.addLayout(g1); dev_lay.addSpacing(20)
        
        g2 = QGridLayout(); g2.setVerticalSpacing(15); g2.setHorizontalSpacing(20)
        g2.addWidget(self.mk_lbl("Мережеві ключі (API Keys & Telegram)", "subtitle"), 0, 0, 1, 2)
        g2.addWidget(QLabel("Активний ШІ:"), 1, 0); self.cb_ai_provider = QComboBox(); self.cb_ai_provider.addItems(["Gemini", "ChatGPT", "OpenRouter"]); g2.addWidget(self.cb_ai_provider, 1, 1)
        g2.addWidget(QLabel("Gemini Key:"), 2, 0); self.inp_gemini = QLineEdit(); g2.addWidget(self.inp_gemini, 2, 1)
        g2.addWidget(QLabel("OpenAI Key:"), 3, 0); self.inp_openai = QLineEdit(); g2.addWidget(self.inp_openai, 3, 1)
        g2.addWidget(QLabel("OpenRouter Key:"), 4, 0); self.inp_openrouter = QLineEdit(); g2.addWidget(self.inp_openrouter, 4, 1)
        g2.addWidget(QLabel("OpenWeatherMap Key:"), 5, 0); self.inp_owm = QLineEdit(); g2.addWidget(self.inp_owm, 5, 1)
        
        # ПОЛЯ ДЛЯ TELEGRAM БОТА
        g2.addWidget(QLabel("Telegram Bot Token:"), 6, 0)
        self.inp_tg_token = QLineEdit()
        self.inp_tg_token.setPlaceholderText("Отримати у @BotFather")
        g2.addWidget(self.inp_tg_token, 6, 1)

        g2.addWidget(QLabel("Telegram Chat ID:"), 7, 0)
        self.inp_tg_chat = QLineEdit()
        self.inp_tg_chat.setPlaceholderText("Обов'язково для безпеки")
        g2.addWidget(self.inp_tg_chat, 7, 1)

        # КНОПКИ АВТОЗАВАНТАЖЕННЯ
        btn_auto_on = QPushButton("✅ Додати в Автозавантаження Windows")
        btn_auto_on.clicked.connect(lambda: self.toggle_autostart(True))
        g2.addWidget(btn_auto_on, 8, 0)
        
        btn_auto_off = QPushButton("❌ Видалити з Автозавантаження")
        btn_auto_off.setObjectName("danger")
        btn_auto_off.clicked.connect(lambda: self.toggle_autostart(False))
        g2.addWidget(btn_auto_off, 8, 1)
        
        dev_lay.addLayout(g2); dev_lay.addStretch()
        self.sub_tabs.addTab(tab_dev, "ШІ ТА ЛОКАЛІЗАЦІЯ")

        # --- ТАБ 3: ВЕБХУКИ ---
        tab_hooks = QWidget(); hooks_lay = QVBoxLayout(tab_hooks); hooks_lay.setContentsMargins(30, 30, 30, 30)
        hooks_lay.addWidget(self.mk_lbl("Активні фонові перевірки:", "subtitle"))
        self.list_hooks = QListWidget(); self.list_hooks.setObjectName("VertMacros"); hooks_lay.addWidget(self.list_hooks)
        btn_ai_hook = QPushButton("✨ Згенерувати Вебхук через ШІ"); btn_ai_hook.setObjectName("primary")
        btn_ai_hook.clicked.connect(self.create_ai_webhook); hooks_lay.addWidget(btn_ai_hook)
        btn_del_hook = QPushButton("❌ Видалити обраний"); btn_del_hook.setObjectName("danger")
        btn_del_hook.clicked.connect(self.delete_webhook); hooks_lay.addWidget(btn_del_hook)
        self.sub_tabs.addTab(tab_hooks, "ВЕБХУКИ")

        sw_lay.addWidget(self.sub_tabs)
        btn_save_all = QPushButton("💾 ЗБЕРЕГТИ ВСІ НАЛАШТУВАННЯ НА ДИСК"); btn_save_all.setObjectName("primary"); btn_save_all.setMinimumHeight(50)
        btn_save_all.clicked.connect(self.save_cfg); sw_lay.addWidget(btn_save_all)
        
        self.main_stack.addWidget(sett_wrap)
        self.load_cfg()

    def mk_lbl(self, txt, obj_name): l = QLabel(txt); l.setObjectName(obj_name); return l

    def toggle_mic(self):
        self.app_state['mic_active'] = not self.app_state['mic_active']
        if self.app_state['mic_active']:
            self.btn_mic.setText("🎙 Мікрофон: УВІМКНЕНО")
            self.btn_mic.setStyleSheet("background: rgba(26, 26, 46, 200); color: #a6e3a1; font-weight: bold;")
        else:
            self.btn_mic.setText("🔇 Мікрофон: ВИМКНЕНО")
            self.btn_mic.setStyleSheet("background: rgba(141, 31, 43, 200); color: white; font-weight: bold;")

    # ================= ЛОГІКА АВТОМАТИЗАЦІЇ ЧЕРЕЗ ШІ =================
    def create_ai_macro(self):
        text, ok = QInputDialog.getText(self, "ШІ-Конструктор Макросів", "Опишіть команду для ПК.\nНаприклад: 'Створи команду щоб відкрити Discord і Telegram'")
        if ok and text:
            self.lbl_status.setText("СИСТЕМА: ШІ ПИШЕ МАКРОС...")
            self.lbl_status.setStyleSheet("color: #b052ff; background: transparent;")
            threading.Thread(target=self._ai_macro_thread, args=(text,), daemon=True).start()

    def _ai_macro_thread(self, prompt):
        result_dict = generate_macro_json(prompt)
        self.macro_signal.emit(result_dict if result_dict else {})

    @pyqtSlot(dict)
    def on_macro_generated(self, macro_data):
        self.lbl_status.setText("СИСТЕМА: ОНЛАЙН")
        self.lbl_status.setStyleSheet("color: #00e5ff; background: transparent;")
        
        if macro_data and "name" in macro_data:
            if not self.current_cat_name:
                self.current_cat_name = "Згенеровані ШІ"
                if self.current_cat_name not in self.macros_data_cache:
                    self.macros_data_cache[self.current_cat_name] = {}
                    item = QListWidgetItem(self.current_cat_name); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.list_cats.addItem(item)
                    self.list_cats.setCurrentItem(item)

            m_name = macro_data["name"]
            if m_name in self.macros_data_cache[self.current_cat_name]:
                m_name += f"_{random.randint(1, 99)}"
                
            self.macros_data_cache[self.current_cat_name][m_name] = {
                "triggers": macro_data.get("triggers", ""),
                "actions": macro_data.get("actions", []),
                "response": macro_data.get("response", "Виконано.")
            }
            self.on_category_select()
            items = self.list_macros.findItems(m_name, Qt.MatchFlag.MatchExactly)
            if items: self.list_macros.setCurrentItem(items[0])
            
            self.save_cfg()
            QMessageBox.information(self, "Успіх", f"Макрос '{m_name}' успішно створено!")
        else:
            QMessageBox.warning(self, "Помилка", "ШІ не зміг згенерувати команду. Спробуйте описати інакше.")

    # ================= ЛОГІКА ВЕБХУКІВ ЧЕРЕЗ ШІ =================
    def create_ai_webhook(self):
        text, ok = QInputDialog.getText(self, "ШІ-Конструктор Вебхуків", "Опишіть завдання для Аве.\nНаприклад: 'Перевіряй курс Ethereum кожні 15 хвилин'")
        if ok and text:
            self.lbl_status.setText("СИСТЕМА: ШІ ГЕНЕРУЄ КОД...")
            self.lbl_status.setStyleSheet("color: #b052ff; background: transparent;")
            threading.Thread(target=self._ai_webhook_thread, args=(text,), daemon=True).start()

    def _ai_webhook_thread(self, prompt):
        result_dict = generate_webhook_json(prompt)
        self.webhook_signal.emit(result_dict if result_dict else {})

    @pyqtSlot(dict)
    def on_webhook_generated(self, webhook_data):
        self.lbl_status.setText("СИСТЕМА: ОНЛАЙН")
        self.lbl_status.setStyleSheet("color: #00e5ff; background: transparent;")
        
        if webhook_data and "name" in webhook_data:
            self.webhooks_cache.append(webhook_data)
            self.refresh_hooks_list()
            self.save_cfg() 
            QMessageBox.information(self, "Успіх", f"Вебхук '{webhook_data['name']}' успішно згенеровано та додано!")
        else:
            QMessageBox.warning(self, "Помилка", "ШІ не зміг згенерувати валідний код. Спробуйте описати завдання інакше.")

    def refresh_hooks_list(self):
        self.list_hooks.clear()
        for idx, hook in enumerate(self.webhooks_cache):
            name = hook.get("name", "Unknown")
            interval = hook.get("interval_minutes", "?")
            item = QListWidgetItem(f"{name} (Кожні {interval} хв)")
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.list_hooks.addItem(item)

    def delete_webhook(self):
        itm = self.list_hooks.currentItem()
        if not itm: return
        idx = itm.data(Qt.ItemDataRole.UserRole)
        del self.webhooks_cache[idx]
        self.refresh_hooks_list(); self.save_cfg()

    # ================= МЕНЮ ТА ІНШЕ =================
    def show_cat_context_menu(self, pos):
        item = self.list_cats.itemAt(pos)
        if not item: return
        menu = QMenu(self); ren_act = menu.addAction("✎ Змінити назву"); del_act = menu.addAction("❌ Видалити")
        action = menu.exec(self.list_cats.mapToGlobal(pos))
        if action == ren_act: self.rename_category_dialog(item)
        elif action == del_act: self.delete_category_item(item)

    def show_mac_context_menu(self, pos):
        item = self.list_macros.itemAt(pos)
        if not item: return
        menu = QMenu(self); ren_act = menu.addAction("✎ Змінити назву"); del_act = menu.addAction("❌ Видалити")
        action = menu.exec(self.list_macros.mapToGlobal(pos))
        if action == ren_act: self.rename_macro_dialog(item)
        elif action == del_act: self.delete_macro_item(item)

    def add_category_dialog(self):
        text, ok = QInputDialog.getText(self, "Нова категорія", "Назва:")
        if ok and text and text not in self.macros_data_cache:
            self.macros_data_cache[text] = {}
            item = QListWidgetItem(text); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_cats.addItem(item); self.list_cats.setCurrentItem(item)

    def rename_category_dialog(self, item):
        old_name = item.text()
        text, ok = QInputDialog.getText(self, "Змінити назву", "Нова назва:", text=old_name)
        if ok and text and text != old_name and text not in self.macros_data_cache:
            self.macros_data_cache[text] = self.macros_data_cache.pop(old_name)
            item.setText(text); self.on_category_select()

    def delete_category_item(self, item):
        cat = item.text()
        if cat in self.macros_data_cache: del self.macros_data_cache[cat]
        self.list_cats.takeItem(self.list_cats.row(item))
        self.list_macros.blockSignals(True); self.list_macros.clear(); self.list_macros.blockSignals(False); self.form_content.hide()

    def on_category_select(self):
        itm = self.list_cats.currentItem(); 
        if not itm: return
        self.list_macros.blockSignals(True)
        self.current_cat_name = itm.text(); self.list_macros.clear()
        for m_name, m_data in self.macros_data_cache.get(self.current_cat_name, {}).items():
            item = QListWidgetItem(m_name); item.setData(Qt.ItemDataRole.UserRole, m_name)
            self.list_macros.addItem(item)
        self.list_macros.blockSignals(False); self.form_content.hide(); self.lbl_mac_title.setText("Оберіть макрос для редагування")
        self.current_macro_name = ""

    def create_macro(self):
        if not getattr(self, 'current_cat_name', None): return QMessageBox.warning(self, "Помилка", "Оберіть категорію зверху!")
        new_name = f"Новий_Макрос_{len(self.macros_data_cache[self.current_cat_name]) + 1}"
        self.macros_data_cache[self.current_cat_name][new_name] = {"triggers": "тригер", "actions": [{"type":"Затримка", "value":"1.0"}], "response": ""}
        self.on_category_select(); self.list_macros.setCurrentRow(self.list_macros.count()-1)

    def rename_macro_dialog(self, item):
        old_name = item.data(Qt.ItemDataRole.UserRole)
        text, ok = QInputDialog.getText(self, "Змінити назву", "Нова назва макросу:", text=old_name)
        if ok and text and text != old_name:
            cat_name = self.current_cat_name
            self.macros_data_cache[cat_name][text] = self.macros_data_cache[cat_name].pop(old_name)
            item.setText(text); item.setData(Qt.ItemDataRole.UserRole, text)
            self.list_macros.setCurrentItem(item); self.on_macro_select()

    def delete_macro_item(self, item):
        m_name = item.data(Qt.ItemDataRole.UserRole)
        if m_name in self.macros_data_cache[self.current_cat_name]: del self.macros_data_cache[self.current_cat_name][m_name]
        self.on_category_select(); self.form_content.hide()

    def on_macro_select(self):
        itm = self.list_macros.currentItem()
        if not itm: return
        m_name = itm.data(Qt.ItemDataRole.UserRole)
        if self.current_cat_name not in self.macros_data_cache or m_name not in self.macros_data_cache[self.current_cat_name]: return
            
        self.current_macro_name = m_name
        data = self.macros_data_cache[self.current_cat_name][self.current_macro_name]
        
        self.lbl_mac_title.setText(f"⚙ Редагування: {self.current_macro_name}")
        self.inp_triggers.setText(data.get("triggers", ""))
        self.inp_response.setText(data.get("response", ""))
        
        while self.actions_lay.count():
            child = self.actions_lay.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        for act in data.get("actions", []): self.add_action_row(act.get("type", ""), act.get("value", ""))
        self.form_content.show()

    def add_action_row(self, a_type, a_val):
        self.actions_lay.addWidget(ActionRow(a_type, a_val))

    def save_macro_to_cache(self):
        if not self.current_macro_name: return
        actions = []
        for i in range(self.actions_lay.count()):
            row = self.actions_lay.itemAt(i).widget()
            if row: actions.append(row.get_data())
            
        trigs = self.inp_triggers.text().strip()
        self.macros_data_cache[self.current_cat_name][self.current_macro_name] = {"triggers": trigs, "actions": actions, "response": self.inp_response.toPlainText().strip()}

    def build_default_config(self):
        return {
            "Медіа (Плеєр)": {
                "Плей_Пауза": {"triggers": "стоп, пауза, грай", "actions": [{"type": "Медіа", "value": "playpause"}], "response": "Зробила."},
                "Наступний": {"triggers": "наступне, далі", "actions": [{"type": "Медіа", "value": "nexttrack"}], "response": "Вмикаю наступний."},
                "Голосніше": {"triggers": "голосніше, гучніше", "actions": [{"type": "Гучність", "value": "volumeup:5"}], "response": ""},
                "Тихіше": {"triggers": "тихіше", "actions": [{"type": "Гучність", "value": "volumedown:5"}], "response": ""}
            },
            "Система ПК": {
                "Провідник": {"triggers": "мій комп'ютер, провідник", "actions": [{"type": "Система", "value": "start explorer"}], "response": "Відкриваю."},
                "Сон": {"triggers": "сплячий режим", "actions": [{"type": "Система", "value": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"}], "response": "На добраніч."}
            },
            "Асистент": {
                "Погода": {"triggers": "погода", "actions": [{"type": "Функція", "value": "погода"}], "response": ""},
                "Час": {"triggers": "час, година", "actions": [{"type": "Функція", "value": "час"}], "response": ""},
                "Свято": {"triggers": "свято, свята", "actions": [{"type": "Функція", "value": "свято"}], "response": ""},
                "Пошук": {"triggers": "пошук, знайди", "actions": [{"type": "Функція", "value": "пошук"}], "response": ""}
            }
        }

    def load_cfg(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f: c = json.load(f)
        except: 
            c = {"commands": self.build_default_config(), "owm_key": "2178b761793c0d9bb0b87cf04cfbb683"}
            with open('config.json', 'w', encoding='utf-8') as f: json.dump(c, f, ensure_ascii=False, indent=4)

        self.cb_ui_lang.setCurrentText(c.get('ui_language', 'Українська'))
        self.cb_stt_lang.setCurrentText(c.get('stt_language', 'uk-UA'))
        self.cb_voice.setCurrentIndex(1 if "Ostap" in c.get('voice', '') else 0)
        self.cb_ai_provider.setCurrentText(c.get('ai_provider', 'Gemini'))
        self.inp_gemini.setText(c.get('gemini_key', ''))
        self.inp_openai.setText(c.get('openai_key', ''))
        self.inp_openrouter.setText(c.get('openrouter_key', ''))
        self.inp_owm.setText(c.get('owm_key', ''))
        self.inp_tg_token.setText(c.get('telegram_token', ''))
        self.inp_tg_chat.setText(c.get('telegram_chat_id', ''))

        self.list_cats.clear()
        self.macros_data_cache = c.get('commands', {})
        if not self.macros_data_cache: self.macros_data_cache = self.build_default_config() 
        for cat_name in self.macros_data_cache.keys():
            item = QListWidgetItem(cat_name); item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_cats.addItem(item)
        if self.list_cats.count() > 0: self.list_cats.setCurrentRow(0)

        self.webhooks_cache = c.get("webhooks", [])
        self.refresh_hooks_list()

    def save_cfg(self):
        cfg = {
            "ai_provider": self.cb_ai_provider.currentText(),
            "gemini_key": self.inp_gemini.text().strip(), "openai_key": self.inp_openai.text().strip(),
            "openrouter_key": self.inp_openrouter.text().strip(), "owm_key": self.inp_owm.text().strip(),
            "telegram_token": self.inp_tg_token.text().strip(),
            "telegram_chat_id": self.inp_tg_chat.text().strip(),
            "voice": "uk-UA-OstapNeural" if self.cb_voice.currentIndex() == 1 else "uk-UA-PolinaNeural",
            "ui_language": self.cb_ui_lang.currentText(), "stt_language": self.cb_stt_lang.currentText(),
            "commands": self.macros_data_cache,
            "webhooks": self.webhooks_cache
        }
        with open('config.json', 'w', encoding='utf-8') as f: json.dump(cfg, f, ensure_ascii=False, indent=4)
        from dotenv import set_key
        set_key(".env", "GEMINI_API_KEY", cfg["gemini_key"]); set_key(".env", "OWM_API_KEY", cfg["owm_key"])
        self.log.append("✅ Конфігурацію збережено!")

    def toggle_autostart(self, enable):
        startup_path = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "AVE_AutoStart.bat")
        if enable:
            try:
                with open(startup_path, "w", encoding="utf-8") as f:
                    f.write(f'@echo off\ncd /d "{os.getcwd()}"\nstart "" /B pythonw gui_main.py\n')
                QMessageBox.information(self, "Автозавантаження", "AVE успішно додано в автозавантаження Windows!")
            except Exception as e:
                QMessageBox.warning(self, "Помилка", f"Не вдалося додати: {e}")
        else:
            if os.path.exists(startup_path):
                os.remove(startup_path)
                QMessageBox.information(self, "Автозавантаження", "AVE видалено з автозавантаження.")
            else:
                QMessageBox.information(self, "Автозавантаження", "AVE і так не була в автозавантаженні.")

    def process_text_query(self, text):
        self.update_signal.emit("processing", "")
        is_system_cmd, sys_response = execute_system_command(text)
        final_response = sys_response if is_system_cmd else generate_response(text)
        self.update_signal.emit("speaking", final_response)
        speak(re.sub(r'<[^>]+>', ' ', final_response).strip())
        self.update_signal.emit("idle", "")

    def send_text(self):
        txt = self.query_input.text().strip()
        if txt: 
            self.append_chat(f"⌨️ Ви (Текст): {txt}", "#a6adc8")
            self.query_input.clear()
            threading.Thread(target=self.process_text_query, args=(txt,), daemon=True).start()

    def append_chat(self, text, color="#ffffff", size="18px"):
        html = f"<div align='center' style='font-size: {size}; color: {color}; margin-bottom: 10px; line-height: 1.4;'>{text}</div>"
        self.log.append(html)
        sb = self.log.verticalScrollBar(); sb.setValue(sb.maximum())

    @pyqtSlot(str, str)
    def update_gui(self, status, msg):
        if status == "user_input":
            self.append_chat(f"🎙 Ви (Голос): {msg}", "#a6e3a1")
            return
            
        self.mini.status = status
        self.dash_bg.status = status
        
        labels = {"idle": "ОНЛАЙН", "listening": "СЛУХАЄ...", "processing": "АНАЛІЗУЄ...", "speaking": "ВІДПОВІДАЄ...", "mic_off": "МІКРОФОН ВИМКНЕНО"}
        
        if status in labels:
            self.lbl_status.setText(f"СИСТЕМА: {labels[status]}")
            color = "#00e5ff" if status == "idle" else ("#ff4d4d" if status == "mic_off" else "#b052ff")
            self.lbl_status.setStyleSheet(f"color: {color}; background: transparent;")
            
            if status == "idle": self.mini.speed = 2
            elif status == "listening": self.mini.speed = 5
            elif status == "processing": self.mini.speed = 12
            elif status == "speaking": self.mini.speed = 5
        
        if msg and status not in ["idle", "processing", "listening", "user_input", "mic_off"]: 
            self.append_chat(f"🤖 <b>AVE:</b> {msg}", "#00e5ff", "20px")
            
        if msg and status == "idle": 
            self.append_chat(f"🤖 <b>AVE:</b> {msg}", "#00e5ff", "20px")

if __name__ == "__main__":
    import ctypes
    try:
        myappid = 'ave.command.center.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception: pass

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app_icon = QIcon("favicon.ico") if os.path.exists("favicon.ico") else QIcon()
    app.setWindowIcon(app_icon)
    
    window = AveMainWindow()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())