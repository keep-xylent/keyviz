import sys
import os
import random
import colorsys
import time
from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QDialog, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QFontDatabase

class ConsentDialog(QDialog):
    """Interactive popup asking users to permit global keystroke capture before hooks attach."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("KeyViz - Security Consent")
        self.setFixedSize(460, 260)
        self.setWindowFlags(Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.CustomizeWindowHint)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Stylish look aligned with general dark mode theme
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
            }
            QLabel {
                color: #cdd6f4;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 8px 18px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
            QPushButton#acceptBtn {
                background-color: #f43f5e;
                color: #ffffff;
                border: 1px solid #f43f5e;
            }
            QPushButton#acceptBtn:hover {
                background-color: #e11d48;
            }
        """)
        
        title_label = QLabel("Permission Required")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #f43f5e;")
        layout.addWidget(title_label)
        
        desc_text = (
            "KeyViz requires permission to capture your keystrokes globally.\n\n"
            "• This allows the overlay dashboard to highlight pressed keys on your screen.\n"
            "• Keystrokes are processed locally and are NEVER recorded, stored, or sent online."
        )
        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(desc_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        deny_btn = QPushButton("Deny & Exit")
        deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deny_btn.clicked.connect(self.reject)
        
        accept_btn = QPushButton("Grant Permission")
        accept_btn.setObjectName("acceptBtn")
        accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        accept_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(deny_btn)
        btn_layout.addWidget(accept_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

class ZoomEffect:
    def __init__(self, rect, label, font, color):
        self.rect = rect
        self.label = label
        self.font = font
        self.color = color
        self.life = 1.0
        self.scale = 1.0
        self.speed = 0.05
        self.fade_speed = 0.04

    def update(self):
        self.scale += self.speed
        self.life -= self.fade_speed
        return self.life > 0

class KeyButton(QFrame):
    def __init__(self, sc_key, sc_list, display_name, width, height, is_knob=False, parent=None, color_mode="rgb"):
        super().__init__(parent)
        self.sc_key = sc_key
        self.sc_list = sc_list if isinstance(sc_list, list) else [sc_list]
        self.is_active = False
        self.is_knob = is_knob
        self.hue = 0.0
        self.color_mode = color_mode
        self.dragPos = QPoint()
        self.setFixedSize(width, height)
        
        self.label = QLabel(display_name, self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedSize(width, height)

        families = QFontDatabase.families()
        self.target_font = next((f for f in families if "Fira" in f and ("NF" in f or "Nerd" in f)), "Arial Black")
        
        font = QFont(self.target_font, 10)
        font.setBold(True)
        self.label.setFont(font)
        
        self.is_gaming = parent.mode == "gaming" if parent else False
        self.radius_val = f"{width//2}px" if is_knob else "4px"
        self.fixed_color = None
        if self.color_mode in ["white", "putih"]:
            self.fixed_color = "#FFFFFF"
        elif self.color_mode.startswith("#"):
            self.fixed_color = self.color_mode
            
        self.normal_style = f"background-color: #40000000; color: #FFFFFF; border: 0.5px solid #20FFFFFF; border-radius: {self.radius_val};"
        self.setStyleSheet(self.normal_style)

    def set_active(self, active):
        self.is_active = active
        if not active:
            self.setStyleSheet(self.normal_style)
            self.label.move(0, 0)
            self.label.setStyleSheet("color: #FFFFFF;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and getattr(self.parent(), 'setup_mode', None) == 'custom':
            self.dragPos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and getattr(self.parent(), 'setup_mode', None) == 'custom':
            new_pos = event.globalPosition().toPoint() - self.dragPos
            self.move(new_pos)
            if hasattr(self.parent(), 'update_button_pos'):
                self.parent().update_button_pos(self.sc_key, new_pos.x(), new_pos.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

class KeyboardOverlay(QWidget):
    def __init__(self, config_manager, input_handler, mode="normal", custom_keys=None, color_mode="default", setup_mode=None, force_pos=None, force_no_mouse=False):
        super().__init__()
        self.config_manager = config_manager
        self.input_handler = input_handler
        
        # Load the configuration data through the manager
        self.config_data = self.config_manager.load_config()
        
        self.mode = mode
        self.custom_keys = custom_keys
        self.color_mode = color_mode
        self.recorded_keys = set()
        self.custom_pos = {} 
        self.keys_map = {} 
        self.ripples = []
        self.buttons = []
        self.global_hue_offset = 0.0
        self.key_last_wave_time = {}
        self.dragPos = QPoint()
        
        # Load static packaged databases safely
        self.key_mapping = self.config_manager.load_packaged_json('key.json')
        self.layout_config = self.config_manager.load_packaged_json('layout.json')
        
        config_exists = os.path.exists(self.config_manager.get_config_path())
        legacy_exists = (os.path.exists(os.path.join(self.config_manager.CONFIG_DIR, 'settings.json')) or 
                         os.path.exists(os.path.join(self.config_manager.CONFIG_DIR, 'recorded_keys.json')))
        
        self.setup_mode = setup_mode
        if not self.setup_mode and not config_exists and not legacy_exists:
            self.setup_mode = 'all'
            
        self.is_in_setup = bool(self.setup_mode)
        
        if self.is_in_setup:
            self.is_locked = False
        else:
            self.is_locked = force_no_mouse

        self.initUI()
        self.load_overlay_config()
        
        if force_pos:
            try:
                x, y = map(int, force_pos.split(','))
                self.move(x, y)
            except Exception:
                pass

        self.apply_behavior()
        
        # Frame drawing animation timer (60 FPS approximate)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_anim)
        self.timer.start(16)

        # Wire up event signals from input_handler
        self.input_handler.signaller.press_sig.connect(self.handle_press)
        self.input_handler.signaller.release_sig.connect(self.handle_release)
        
        # Start input hooks shortly after window reveals
        QTimer.singleShot(500, self.start_keyboard_hook)

    def start_keyboard_hook(self):
        try:
            self.input_handler.start_hook()
        except Exception as e:
            print(f"[ERROR] Failed to establish keyboard hook: {e}")
            sys.exit(1)

    def apply_behavior(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        
        if self.is_locked and not self.is_in_setup:
            flags |= Qt.WindowType.WindowTransparentForInput
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        self.setWindowFlags(flags)
        
        for btn in self.buttons:
            btn.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked and not self.is_in_setup)
            btn.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked and not self.is_in_setup)
            
        self.show()
        self.update()

    def load_overlay_config(self):
        pos = self.config_data.get('pos')
        if pos:
            self.move(pos[0], pos[1])
        
        self.custom_pos = self.config_data.get('custom_pos', {})

        if not self.custom_keys:
            recorded = self.config_data.get('recorded_keys', {})
            keys_for_mode = recorded.get(self.mode, [])
            if keys_for_mode:
                self.recorded_keys = set(keys_for_mode)
                self.rebuild_ui()

    def save_overlay_config(self):
        self.config_data['pos'] = [self.x(), self.y()]
        self.config_data['mode'] = self.mode
        self.config_data['color'] = self.color_mode
        
        if not self.is_in_setup:
            self.config_data['no_mouse'] = self.is_locked
        
        if 'recorded_keys' not in self.config_data:
            self.config_data['recorded_keys'] = {}
        if self.recorded_keys:
            self.config_data['recorded_keys'][self.mode] = list(self.recorded_keys)
        
        self.config_data['custom_pos'] = self.custom_pos
        self.config_manager.save_config(self.config_data)

    def update_button_pos(self, sc_key, x, y):
        self.config_data = self.config_manager.update_button_pos(self.config_data, self.mode, sc_key, x, y)

    def initUI(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(1200, 500)
        self.rebuild_ui()

    def rebuild_ui(self):
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons = []
        self.keys_map = {}

        gaming_keys_default = ["w", "a", "s", "d", "space", "p"]
        target_keys = None

        if self.recorded_keys:
            target_keys = list(self.recorded_keys)
        elif self.custom_keys:
            target_keys = [k.strip().lower() for k in self.custom_keys.split(",")]
        elif self.mode in ["gaming", "custom"]:
            target_keys = gaming_keys_default

        for item in self.layout_config:
            sc_key = item['sc_key']
            if target_keys and sc_key.lower() not in target_keys:
                continue

            sc_val = self.key_mapping.get(sc_key)
            if sc_val is not None:
                pos_x, pos_y = item['x'], item['y']
                mode_customs = self.custom_pos.get(self.mode, {})
                if sc_key in mode_customs:
                    pos_x, pos_y = mode_customs[sc_key]

                btn = KeyButton(sc_key, sc_val, item['label'], item['w'], item['h'], item.get('is_knob', False), self, self.color_mode)
                btn.move(pos_x, pos_y)
                self.buttons.append(btn)
                
                codes = sc_val if isinstance(sc_val, list) else [sc_val]
                for code in codes:
                    if code not in self.keys_map:
                        self.keys_map[code] = []
                    self.keys_map[code].append(btn)

    def handle_press(self, sc, name):
        if sc in self.keys_map:
            for btn in self.keys_map[sc]:
                if ("right" in name or "alt gr" in name) and btn.x() < 500:
                    continue
                if "right" not in name and "alt gr" not in name and (sc in [29, 56, 42]) and btn.x() > 500:
                    continue
                btn.set_active(True)
                
                now = time.time()
                if now - self.key_last_wave_time.get(sc, 0) > 0.3:
                    self.key_last_wave_time[sc] = now
                    if btn.fixed_color:
                        wave_color = QColor(btn.fixed_color)
                    elif self.color_mode == "rgb":
                        hue = (self.global_hue_offset + btn.x() / 1200.0) % 1.0
                        rgb = colorsys.hls_to_rgb(hue, 0.5, 1.0)
                        wave_color = QColor(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
                    else:
                        wave_color = QColor(random.choice(['#f43f5e', '#38bdf8', '#fbbf24', '#a855f7']))
                    self.ripples.append(ZoomEffect(btn.geometry(), btn.label.text(), btn.label.font(), wave_color))

    def handle_release(self, sc, name):
        if sc in self.keys_map:
            for btn in self.keys_map[sc]:
                btn.set_active(False)

    def update_anim(self):
        self.global_hue_offset = (self.global_hue_offset + 0.01) % 1.0
        for sc in self.keys_map:
            for btn in self.keys_map[sc]:
                if btn.is_active:
                    rad = btn.radius_val
                    if btn.fixed_color:
                        btn.setStyleSheet(f"background-color: #80000000; color: #FFFFFF; border: 2.5px solid {btn.fixed_color}; border-radius: {rad};")
                    elif self.color_mode == "rgb":
                        hue = (self.global_hue_offset + btn.x() / 1200.0) % 1.0
                        rgb = colorsys.hls_to_rgb(hue, 0.5, 1.0)
                        r, g, b = [int(x * 255) for x in rgb]
                        border_px = "2.5px"
                        btn.setStyleSheet(f"background-color: #B0000000; color: #FFFFFF; border: {border_px} solid rgb({r},{g},{b}); border-radius: {rad};")
                    else:
                        btn.hue = (btn.hue + 0.03) % 1.0
                        rgb = colorsys.hls_to_rgb(btn.hue, 0.5, 1.0)
                        r, g, b = [int(x * 255) for x in rgb]
                        border_px = "2.5px"
                        btn.setStyleSheet(f"background-color: #B0000000; color: #FFFFFF; border: {border_px} solid rgb({r},{g},{b}); border-radius: {rad};")
                    btn.label.move(random.randint(-1, 1), random.randint(-1, 1))
        self.ripples = [r for r in self.ripples if r.update()]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.is_in_setup:
            painter.save()
            pen = QPen(QColor("#f43f5e"), 3, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(0, 0, self.width()-1, self.height()-1)
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            painter.setPen(QColor("#f43f5e"))
            msg = f" SETUP MODE ({'MOVE OVERLAY' if self.setup_mode == 'all' else 'MOVE KEYS'}) - Press ENTER to Confirm & Exit "
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, msg)
            painter.restore()

        for effect in self.ripples:
            painter.save()
            color = QColor(effect.color)
            color.setAlpha(int(effect.life * 255))
            center = effect.rect.center()
            painter.translate(center)
            painter.scale(effect.scale, effect.scale)
            painter.translate(-center)
            painter.setPen(QPen(color, 2))
            painter.drawRoundedRect(effect.rect, 2, 2)
            painter.setFont(effect.font)
            painter.drawText(effect.rect, Qt.AlignmentFlag.AlignCenter, effect.label)
            painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.setup_mode == 'all':
            self.dragPos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton and self.is_in_setup:
            self.is_in_setup = False
            self.is_locked = True
            self.save_overlay_config()
            self.apply_behavior()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.setup_mode == 'all':
            self.move(event.globalPosition().toPoint() - self.dragPos)
