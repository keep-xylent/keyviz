import os
import sys
import json
import time
import math
import keyboard
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QCheckBox, QColorDialog,
    QDialog, QLineEdit, QSystemTrayIcon, QMenu, QFrame, QApplication, QStyle,
    QComboBox, QInputDialog, QMessageBox, QFileDialog, QSlider, QScrollArea,
    QStackedWidget
)
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QAction, QPainter, QPen, QBrush,
    QFontDatabase, QFontInfo
)
from keyviz.main import get_theme_color, KeyboardOverlay

# Base directory for static files (inside keyviz package directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Determine CONFIG_DIR for dynamic config files
if "site-packages" in BASE_DIR or "dist-packages" in BASE_DIR:
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".keyviz")
    os.makedirs(CONFIG_DIR, exist_ok=True)
else:
    CONFIG_DIR = os.path.dirname(BASE_DIR)


class WindowButton(QPushButton):
    """
    Consistent vector-drawn window caption button (Minimize & Close).
    Eliminates font alignment inconsistencies and provides native-like feel.
    """
    def __init__(self, btn_type="close", parent=None):
        super().__init__(parent)
        self.btn_type = btn_type  # "min" or "close"
        self.setFixedSize(28, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_hovered = False

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())
        rect = QRectF(0, 0, w, h)

        if self.is_hovered:
            if self.btn_type == "close":
                painter.fillRect(rect, QColor("#e81123"))
                pen_color = QColor(255, 255, 255)
            else:
                painter.fillRect(rect, QColor(38, 41, 50))
                pen_color = QColor(255, 255, 255)
        else:
            pen_color = QColor(120, 125, 136)

        pen = QPen(pen_color, 1.2)
        painter.setPen(pen)

        cx, cy = w / 2.0, h / 2.0
        if self.btn_type == "min":
            painter.drawLine(QPointF(cx - 5.0, cy), QPointF(cx + 5.0, cy))
        elif self.btn_type == "close":
            s = 3.5
            painter.drawLine(QPointF(cx - s, cy - s), QPointF(cx + s, cy + s))
            painter.drawLine(QPointF(cx - s, cy + s), QPointF(cx + s, cy - s))


class DynamicStackedWidget(QStackedWidget):
    """
    QStackedWidget subclass that reports the sizeHint and minimumSizeHint
    of the currently active page, allowing the window to dynamically
    shrink or expand to hug active content with zero dead space.
    """
    def sizeHint(self):
        cur = self.currentWidget()
        if cur:
            return cur.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        cur = self.currentWidget()
        if cur:
            return cur.minimumSizeHint()
        return super().minimumSizeHint()


class KeyboardPreviewWidget(QWidget):
    """
    Compact wireframe keyboard preview.
    Displays layout and highlights keys when typed, without neon effects.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(125)
        self.setMinimumWidth(320)
        self.layout_config = []
        self.key_mapping = {}
        self.active_keys_filter = None
        self.active_pressed_keys = set()
        self.color_mode = "white"
        self.global_offset = 0.0
        
        self.load_data()
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.on_anim_tick)
        self.anim_timer.start(40)

    def load_data(self):
        try:
            with open(os.path.join(BASE_DIR, 'key.json'), 'r', encoding='utf-8') as f:
                self.key_mapping = json.load(f)
            with open(os.path.join(BASE_DIR, 'layout.json'), 'r', encoding='utf-8') as f:
                self.layout_config = json.load(f)
        except Exception as e:
            print(f"[Preview] Error loading layout: {e}")

    def on_anim_tick(self):
        self.global_offset = (self.global_offset + 0.01) % 1.0
        if self.color_mode in ["rgb", "rainbow", "spectrum"] or self.active_pressed_keys:
            self.update()

    def set_config(self, mode, color_mode, active_preset=None, presets=None):
        self.color_mode = color_mode
        if mode == 'gaming':
            self.active_keys_filter = set(["w", "a", "s", "d", "space", "l_shift", "l_ctrl", "r", "e", "q", "f", "1", "2", "3", "4", "tab"])
        elif mode == 'custom' and presets and active_preset in presets:
            self.active_keys_filter = set(k.lower() for k in presets[active_preset])
        else:
            self.active_keys_filter = None
        self.update()

    def handle_press(self, sc):
        matched = False
        for k, v in self.key_mapping.items():
            codes = v if isinstance(v, list) else [v]
            if sc in codes:
                self.active_pressed_keys.add(k.lower())
                matched = True
        if matched:
            self.update()

    def handle_release(self, sc):
        matched = False
        for k, v in self.key_mapping.items():
            codes = v if isinstance(v, list) else [v]
            if sc in codes:
                self.active_pressed_keys.discard(k.lower())
                matched = True
        if matched:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())

        bg_rect = QRectF(0, 0, w, h)
        painter.setPen(QPen(QColor(32, 34, 42), 1.0))
        painter.setBrush(QColor(14, 15, 18))
        painter.drawRoundedRect(bg_rect, 6.0, 6.0)

        if not self.layout_config:
            return

        max_base_x = 1060.0
        max_base_y = 405.0
        scale_x = (w - 16.0) / max_base_x
        scale_y = (h - 16.0) / max_base_y
        scale = min(scale_x, scale_y)
        
        total_w = max_base_x * scale
        total_h = max_base_y * scale
        start_x = (w - total_w) / 2.0
        start_y = (h - total_h) / 2.0

        for item in self.layout_config:
            sc_key = item['sc_key'].lower()
            is_enabled = (self.active_keys_filter is None) or (sc_key in self.active_keys_filter)
            
            kx = start_x + (item['x'] * scale)
            ky = start_y + (item['y'] * scale)
            kw = max(3.0, item['w'] * scale)
            kh = max(3.0, item['h'] * scale)
            krect = QRectF(kx, ky, kw, kh)
            is_pressed = sc_key in self.active_pressed_keys
            is_knob = item.get('is_knob', False)

            if is_knob:
                r = min(kw, kh) / 2.0
                cx, cy = kx + kw / 2.0, ky + kh / 2.0
                if is_pressed:
                    col = get_theme_color(self.color_mode, (item['x'] / max_base_x), self.global_offset)
                    painter.setPen(QPen(col, 1.5))
                    painter.setBrush(QColor(28, 30, 36))
                    painter.drawEllipse(QPointF(cx, cy), r, r)
                else:
                    painter.setPen(QPen(QColor(50, 53, 62) if is_enabled else QColor(26, 28, 34), 0.7))
                    painter.setBrush(QColor(20, 21, 26) if is_enabled else QColor(12, 13, 16))
                    painter.drawEllipse(QPointF(cx, cy), r, r)
                continue

            round_r = max(1.5, 2.5 * scale)

            if is_pressed:
                col = get_theme_color(self.color_mode, (item['x'] / max_base_x), self.global_offset)
                painter.setPen(QPen(col, 1.5))
                painter.setBrush(QColor(32, 35, 44))
                painter.drawRoundedRect(krect, round_r, round_r)
            elif is_enabled:
                painter.setPen(QPen(QColor(48, 52, 62), 0.7))
                painter.setBrush(QColor(20, 22, 27))
                painter.drawRoundedRect(krect, round_r, round_r)
            else:
                painter.setPen(QPen(QColor(24, 26, 32), 0.5))
                painter.setBrush(QColor(12, 13, 16))
                painter.drawRoundedRect(krect, round_r, round_r)


class KeyRecorderDialog(QDialog):
    """Subdued compact dialog for recording custom keys with clean badges."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Custom Keys")
        self.setFixedSize(420, 260)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.recorded_keys = []
        self.key_mapping = {}
        self.load_key_mapping()
        self.init_ui()
        keyboard.hook(self.on_key_event)
        
    def load_key_mapping(self):
        try:
            with open(os.path.join(BASE_DIR, 'key.json'), 'r', encoding='utf-8') as f:
                self.key_mapping = json.load(f)
        except Exception as e:
            print(f"Failed to load key mapping in recorder: {e}")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        card = QFrame(self)
        card.setObjectName("dialogCard")
        card.setStyleSheet("""
            QFrame#dialogCard {
                background-color: #141519;
                border: 1px solid #282a33;
                border-radius: 10px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)
        
        title = QLabel("Record Custom Keys", card)
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #f0f1f4;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)
        
        subtitle = QLabel("Press any key to record. Click Save & Apply when done.", card)
        subtitle.setStyleSheet("font-size: 11px; color: #7f8492;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(subtitle)
        
        self.display_box = QLabel(card)
        self.display_box.setWordWrap(True)
        self.display_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_box.setStyleSheet("""
            background-color: #0d0e11;
            border: 1px solid #20222a;
            border-radius: 6px;
            padding: 8px;
            color: #d1d5db;
            font-size: 12px;
            min-height: 50px;
        """)
        self.display_box.setText("Press keys to start recording...")
        card_layout.addWidget(self.display_box)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        self.clear_btn = QPushButton("Reset", card)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #1c1d24;
                color: #d1d5db;
                border: 1px solid #2c2e39;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #262832; color: white; }
        """)
        self.clear_btn.clicked.connect(self.clear_keys)
        
        self.cancel_btn = QPushButton("Cancel", card)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #7f8492;
                border: 1px solid #242630;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #1a1b22; color: white; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save & Apply", card)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: 1px solid #3b82f6;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.save_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        card_layout.addLayout(btn_layout)
        
        main_layout.addWidget(card)

    def on_key_event(self, e):
        if e.event_type == 'down':
            matched_key = None
            for key_name, codes in self.key_mapping.items():
                codes_list = codes if isinstance(codes, list) else [codes]
                if e.scan_code in codes_list:
                    matched_key = key_name
                    break
            
            if matched_key and matched_key not in self.recorded_keys:
                self.recorded_keys.append(matched_key)
                self.update_display()

    def update_display(self):
        if not self.recorded_keys:
            self.display_box.setText("Press keys to start recording...")
            return
            
        badges = []
        for k in self.recorded_keys:
            badges.append(f"<span style='background-color: #1a1c23; color: #f0f1f4; border: 1px solid #30333f; border-radius: 3px; padding: 2px 5px; font-weight: 600;'>{k.upper()}</span>")
        self.display_box.setText(" ".join(badges))

    def clear_keys(self):
        self.recorded_keys = []
        self.update_display()

    def closeEvent(self, event):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        event.accept()


class AddPresetDialog(QDialog):
    """Subdued compact dialog for creating a layout preset."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Preset")
        self.setFixedSize(360, 175)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.preset_name = ""
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        
        card = QFrame(self)
        card.setObjectName("dialogCard")
        card.setStyleSheet("""
            QFrame#dialogCard {
                background-color: #141519;
                border: 1px solid #282a33;
                border-radius: 10px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)
        
        title = QLabel("Create New Preset", card)
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #f0f1f4;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)
        
        name_label = QLabel("Preset Name:", card)
        name_label.setStyleSheet("color: #7f8492; font-size: 11px; font-weight: 600;")
        card_layout.addWidget(name_label)
        
        self.name_input = QLineEdit(card)
        self.name_input.setPlaceholderText("e.g. Work or Gaming")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background-color: #0d0e11;
                border: 1px solid #242630;
                border-radius: 5px;
                padding: 6px 8px;
                color: #ffffff;
                font-size: 11px;
            }
            QLineEdit:focus { border: 1px solid #4b5563; }
        """)
        card_layout.addWidget(self.name_input)
        card_layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        self.cancel_btn = QPushButton("Cancel", card)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #7f8492;
                border: 1px solid #242630;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #1a1b22; color: white; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.add_btn = QPushButton("Create", card)
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: 1px solid #3b82f6;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.add_btn.clicked.connect(self.validate_and_accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.add_btn)
        card_layout.addLayout(btn_layout)
        main_layout.addWidget(card)
        
    def validate_and_accept(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a preset name.")
            return
        self.preset_name = name
        self.accept()


class SettingsMenu(QWidget):
    """
    Compact, refined, slate-dark Control Panel.
    Clean typography, consistent vector-drawn window controls, zero emojis, zero neon.
    """
    def __init__(self):
        super().__init__()
        self.drag_position = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.icon_path = os.path.join(BASE_DIR, 'icon.png')
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))
            
        self.overlay_instance = None
        self.config_file = os.path.join(CONFIG_DIR, 'config.json')
        self.config = self.load_config()
        self.init_presets()
        
        self.total_keystrokes = 0
        self.recent_keystroke_timestamps = []
        self.peak_kps = 0
        
        # Apply crisp, modern system typography
        app = QApplication.instance()
        if app:
            app_font = QFont("Segoe UI Variable Text", 9)
            if not QFontInfo(app_font).exactMatch():
                app_font = QFont("Segoe UI", 9)
            app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            app.setFont(app_font)

        self.init_ui()
        self.setup_tray()
        self.setup_menu_hook()

    def setup_menu_hook(self):
        def on_menu_key(e):
            if e.event_type == 'down':
                now = time.time()
                self.total_keystrokes += 1
                self.recent_keystroke_timestamps.append(now)
                self.recent_keystroke_timestamps = [t for t in self.recent_keystroke_timestamps if now - t <= 1.0]
                cur_kps = len(self.recent_keystroke_timestamps)
                if cur_kps > self.peak_kps:
                    self.peak_kps = cur_kps
                if hasattr(self, 'preview_widget'):
                    self.preview_widget.handle_press(e.scan_code)
                if hasattr(self, 'kps_label'):
                    self.kps_label.setText(f"{cur_kps} KPS  •  {self.total_keystrokes} Total")
            elif e.event_type == 'up':
                if hasattr(self, 'preview_widget'):
                    self.preview_widget.handle_release(e.scan_code)

        try:
            self.menu_hook_ref = keyboard.hook(on_menu_key)
        except Exception:
            pass

    def init_presets(self):
        if 'presets' not in self.config:
            self.config['presets'] = {}
            
        legacy_custom = self.config.get('recorded_keys', {}).get('custom', [])
        if legacy_custom and "Default Preset" not in self.config['presets']:
            self.config['presets']["Default Preset"] = legacy_custom
            if 'custom' in self.config.get('recorded_keys', {}):
                del self.config['recorded_keys']['custom']
                
        if not self.config['presets']:
            self.config['presets']["Default"] = [
                "esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
                "del", "knob", "space", "w", "a", "s", "d", "tab", "l_shift", "l_ctrl"
            ]
            
        if "75% Exploded + Knob" in self.config['presets']:
            self.config['presets']["Default"] = self.config['presets'].pop("75% Exploded + Knob")
            if self.config.get('active_preset') == "75% Exploded + Knob":
                self.config['active_preset'] = "Default"
            self.save_config()
            
        if 'active_preset' not in self.config or self.config['active_preset'] not in self.config['presets']:
            self.config['active_preset'] = list(self.config['presets'].keys())[0]

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load config: {e}")
        
        return {
            "pos": [100, 100],
            "recorded_keys": {
                "gaming": ["w", "a", "s", "d", "space", "l_shift", "l_ctrl", "r", "e", "q", "f"]
            },
            "mode": "normal",
            "color": "white",
            "scale": 1.0,
            "opacity": 1.0,
            "compact_mode": False,
            "ripple_effect": True,
            "tactile_anim": True,
            "no_mouse": False,
            "custom_pos": {}
        }

    def save_config(self):
        try:
            if hasattr(self, 'mode_gaming') and self.mode_gaming is not None:
                self.config['mode'] = self.get_selected_mode()
            if hasattr(self, 'color_white') and self.color_white is not None:
                self.config['color'] = self.get_selected_color()
            if hasattr(self, 'click_through_cb') and self.click_through_cb is not None:
                self.config['no_mouse'] = self.click_through_cb.isChecked()
            if hasattr(self, 'compact_cb') and self.compact_cb is not None:
                self.config['compact_mode'] = self.compact_cb.isChecked()
            if hasattr(self, 'scale_slider') and self.scale_slider is not None:
                self.config['scale'] = self.scale_slider.value() / 100.0
            if hasattr(self, 'opacity_slider') and self.opacity_slider is not None:
                self.config['opacity'] = self.opacity_slider.value() / 100.0
            if hasattr(self, 'ripple_cb') and self.ripple_cb is not None:
                self.config['ripple_effect'] = self.ripple_cb.isChecked()
            if hasattr(self, 'tactile_cb') and self.tactile_cb is not None:
                self.config['tactile_anim'] = self.tactile_cb.isChecked()

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def init_ui(self):
        self.setWindowTitle("KeyViz Control Panel")
        self.setFixedWidth(430)
        self.setStyleSheet(self.get_stylesheet())
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        
        # Main Container Card
        card = QFrame(self)
        card.setObjectName("mainCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(8)

        # --- Consistent Title Bar ---
        self.title_bar = QFrame(card)
        self.title_bar.setObjectName("titleBar")
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(2, 0, 0, 0)
        title_bar_layout.setSpacing(8)
        
        app_icon_label = QLabel(self.title_bar)
        if os.path.exists(self.icon_path):
            pix = QIcon(self.icon_path).pixmap(16, 16)
            app_icon_label.setPixmap(pix)
        else:
            app_icon_label.setText("KV")
            app_icon_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #9ca3af;")
        title_bar_layout.addWidget(app_icon_label)

        title_text = QLabel("KeyViz", self.title_bar)
        title_text.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6;")
        title_bar_layout.addWidget(title_text)

        ver_badge = QLabel("0.2.1", self.title_bar)
        ver_badge.setStyleSheet("""
            background-color: #1a1c22;
            color: #888d9a;
            border: 1px solid #2a2d37;
            border-radius: 3px;
            padding: 1px 5px;
            font-size: 9px;
            font-weight: 600;
        """)
        title_bar_layout.addWidget(ver_badge)
        title_bar_layout.addStretch()

        # Consistent vector-drawn window buttons
        self.min_btn = WindowButton("min", self.title_bar)
        self.min_btn.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(self.min_btn)

        self.close_btn = WindowButton("close", self.title_bar)
        self.close_btn.clicked.connect(self.close)
        title_bar_layout.addWidget(self.close_btn)
        
        card_layout.addWidget(self.title_bar)

        # --- Compact Segmented Navigation Bar ---
        nav_container = QFrame(card)
        nav_container.setObjectName("navContainer")
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(2, 2, 2, 2)
        nav_layout.setSpacing(3)
        
        self.nav_group = QButtonGroup(self)
        self.nav_btns = []
        
        tabs_meta = [
            ("Dashboard", 0),
            ("Appearance", 1),
            ("Presets", 2),
            ("Settings", 3)
        ]
        
        for title, idx in tabs_meta:
            btn = QPushButton(title, nav_container)
            btn.setCheckable(True)
            btn.setObjectName("navPillBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, i=idx: self.switch_tab(i))
            self.nav_group.addButton(btn, idx)
            self.nav_btns.append(btn)
            nav_layout.addWidget(btn)
            
        card_layout.addWidget(nav_container)

        # --- Dynamic Stacked Widget (auto-hugs active tab content) ---
        self.stacked_widget = DynamicStackedWidget(card)
        self.stacked_widget.addWidget(self.build_dashboard_tab())
        self.stacked_widget.addWidget(self.build_appearance_tab())
        self.stacked_widget.addWidget(self.build_presets_tab())
        self.stacked_widget.addWidget(self.build_preferences_tab())
        
        card_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(card)

        # Initialize button state and fit window directly to Dashboard content
        self.update_toggle_button_ui(False)
        self.adjust_to_content()

    def switch_tab(self, index):
        self.stacked_widget.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
        self.adjust_to_content()

    def adjust_to_content(self):
        """Dynamically resize window height to hug the active tab's content with zero dead space."""
        self.stacked_widget.updateGeometry()
        self.layout().activate()
        self.adjustSize()

    def showEvent(self, event):
        super().showEvent(event)
        self.adjust_to_content()

    def wrap_in_scroll(self, content_widget):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(content_widget)
        return scroll

    # =========================================================================
    # TAB 1: DASHBOARD (COMPACT)
    # =========================================================================
    def build_dashboard_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(8)

        # 1. Compact Status & Action Toolbar Row
        status_card = QFrame(container)
        status_card.setObjectName("innerCard")
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(10, 8, 10, 8)
        status_layout.setSpacing(10)

        # Left status text
        status_info_layout = QVBoxLayout()
        status_info_layout.setSpacing(1)

        top_status_row = QHBoxLayout()
        top_status_row.setSpacing(6)
        self.status_dot = QFrame(status_card)
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setStyleSheet("border-radius: 4px; background-color: #64748b;")
        top_status_row.addWidget(self.status_dot)

        self.status_text = QLabel("Overlay Stopped", status_card)
        self.status_text.setStyleSheet("font-size: 12px; font-weight: 700; color: #f3f4f6;")
        top_status_row.addWidget(self.status_text)
        top_status_row.addStretch()
        status_info_layout.addLayout(top_status_row)

        self.kps_label = QLabel("0 KPS  •  0 Total", status_card)
        self.kps_label.setStyleSheet("font-size: 10px; color: #7f8492;")
        status_info_layout.addWidget(self.kps_label)

        status_layout.addLayout(status_info_layout)
        status_layout.addStretch()

        # Right Action Button
        self.toggle_btn = QPushButton("Start Overlay", status_card)
        self.toggle_btn.setObjectName("toggleButton")
        self.toggle_btn.setFixedSize(105, 30)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_overlay)
        status_layout.addWidget(self.toggle_btn)

        layout.addWidget(status_card)

        # 2. Compact Layout Profile Card
        mode_card = QFrame(container)
        mode_card.setObjectName("innerCard")
        mode_layout = QVBoxLayout(mode_card)
        mode_layout.setContentsMargins(10, 7, 10, 7)
        mode_layout.setSpacing(5)

        mode_header = QLabel("Layout Profile", mode_card)
        mode_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8;")
        mode_layout.addWidget(mode_header)

        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(6)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.mode_normal = QPushButton("Full Layout", mode_card)
        self.mode_gaming = QPushButton("Gaming (WASD)", mode_card)
        self.mode_custom = QPushButton("Custom Preset", mode_card)

        for btn in [self.mode_normal, self.mode_gaming, self.mode_custom]:
            btn.setCheckable(True)
            btn.setObjectName("profilePillBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.mode_group.addButton(btn)
            pills_layout.addWidget(btn)

        saved_mode = self.config.get('mode', 'normal')
        if saved_mode == 'gaming':
            self.mode_gaming.setChecked(True)
        elif saved_mode == 'custom':
            self.mode_custom.setChecked(True)
        else:
            self.mode_normal.setChecked(True)

        self.mode_normal.clicked.connect(self.on_settings_changed)
        self.mode_gaming.clicked.connect(self.on_settings_changed)
        self.mode_custom.clicked.connect(self.on_settings_changed)

        pills_layout.addStretch()
        mode_layout.addLayout(pills_layout)
        layout.addWidget(mode_card)

        # 3. Compact Wireframe Live Preview Card
        preview_card = QFrame(container)
        preview_card.setObjectName("innerCard")
        prev_layout = QVBoxLayout(preview_card)
        prev_layout.setContentsMargins(10, 7, 10, 7)
        prev_layout.setSpacing(5)

        prev_title_layout = QHBoxLayout()
        prev_title = QLabel("Live Preview", preview_card)
        prev_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8;")
        prev_title_layout.addWidget(prev_title)
        prev_title_layout.addStretch()

        prev_hint = QLabel("Type to test", preview_card)
        prev_hint.setStyleSheet("font-size: 10px; color: #71717a; font-weight: 500;")
        prev_title_layout.addWidget(prev_hint)
        prev_layout.addLayout(prev_title_layout)

        self.preview_widget = KeyboardPreviewWidget(preview_card)
        self.preview_widget.set_config(
            self.get_selected_mode(),
            self.config.get('color', 'white'),
            self.config.get('active_preset'),
            self.config.get('presets', {})
        )
        prev_layout.addWidget(self.preview_widget)
        layout.addWidget(preview_card)

        layout.addStretch()
        return self.wrap_in_scroll(container)

    # =========================================================================
    # TAB 2: APPEARANCE (COMPACT)
    # =========================================================================
    def build_appearance_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(8)

        # 1. Color Palette Card
        theme_card = QFrame(container)
        theme_card.setObjectName("innerCard")
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(10, 8, 10, 8)
        theme_layout.setSpacing(8)

        theme_header = QLabel("Key Highlight Color", theme_card)
        theme_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #9ca3af;")
        theme_layout.addWidget(theme_header)

        self.color_group = QButtonGroup(self)
        self.color_white = QRadioButton("White (Mono)", theme_card)
        self.color_slate = QRadioButton("Cool Slate", theme_card)
        self.color_blue = QRadioButton("Nordic Blue", theme_card)
        self.color_green = QRadioButton("Sage Green", theme_card)
        self.color_amber = QRadioButton("Warm Amber", theme_card)
        self.color_rose = QRadioButton("Subtle Rose", theme_card)
        self.color_spectrum = QRadioButton("Spectrum Wave", theme_card)
        self.color_custom = QRadioButton("Custom Hex", theme_card)

        radio_list = [
            self.color_white, self.color_slate, self.color_blue,
            self.color_green, self.color_amber, self.color_rose,
            self.color_spectrum, self.color_custom
        ]

        for btn in radio_list:
            self.color_group.addButton(btn)
            btn.toggled.connect(self.on_settings_changed)

        row1 = QHBoxLayout()
        row1.addWidget(self.color_white)
        row1.addWidget(self.color_slate)
        row1.addWidget(self.color_blue)
        theme_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(self.color_green)
        row2.addWidget(self.color_amber)
        row2.addWidget(self.color_rose)
        theme_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(self.color_spectrum)
        row3.addWidget(self.color_custom)
        theme_layout.addLayout(row3)

        hex_row = QHBoxLayout()
        self.hex_input = QLineEdit(theme_card)
        self.hex_input.setPlaceholderText("#FFFFFF")
        self.hex_input.setFixedSize(80, 24)
        self.hex_input.textChanged.connect(self.on_hex_text_changed)
        hex_row.addWidget(self.hex_input)

        self.color_preview = QFrame(theme_card)
        self.color_preview.setFixedSize(18, 18)
        self.color_preview.setStyleSheet("border-radius: 9px; background-color: #ffffff; border: 1px solid #4b5563;")
        hex_row.addWidget(self.color_preview)

        self.pick_color_btn = QPushButton("Pick", theme_card)
        self.pick_color_btn.setFixedSize(55, 24)
        self.pick_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pick_color_btn.clicked.connect(self.open_color_dialog)
        hex_row.addWidget(self.pick_color_btn)
        hex_row.addStretch()

        theme_layout.addLayout(hex_row)
        layout.addWidget(theme_card)

        saved_color = self.config.get('color', 'white').lower()
        if saved_color in ['white', 'monochrome', 'putih', 'clean']:
            self.color_white.setChecked(True)
        elif saved_color in ['slate', 'gray', 'default']:
            self.color_slate.setChecked(True)
        elif saved_color in ['blue', 'nordic', 'tokyo']:
            self.color_blue.setChecked(True)
        elif saved_color in ['green', 'sage', 'matrix']:
            self.color_green.setChecked(True)
        elif saved_color in ['amber', 'warm', 'sunset']:
            self.color_amber.setChecked(True)
        elif saved_color in ['rose', 'subtle', 'cyberpunk']:
            self.color_rose.setChecked(True)
        elif saved_color in ['rgb', 'rainbow', 'spectrum']:
            self.color_spectrum.setChecked(True)
        elif saved_color.startswith('#'):
            self.color_custom.setChecked(True)
            self.hex_input.setText(saved_color)
            self.color_preview.setStyleSheet(f"border-radius: 9px; background-color: {saved_color}; border: 1px solid #4b5563;")
        else:
            self.color_white.setChecked(True)

        # 2. Scaling & Sizing Card
        size_card = QFrame(container)
        size_card.setObjectName("innerCard")
        size_layout = QVBoxLayout(size_card)
        size_layout.setContentsMargins(10, 8, 10, 8)
        size_layout.setSpacing(6)

        size_header = QLabel("Overlay Scale & Opacity", size_card)
        size_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #9ca3af;")
        size_layout.addWidget(size_header)

        # Scale Slider
        scale_label_layout = QHBoxLayout()
        scale_title = QLabel("Scale:", size_card)
        scale_title.setStyleSheet("color: #858997; font-size: 11px;")
        scale_label_layout.addWidget(scale_title)
        scale_label_layout.addStretch()

        saved_scale = int(round(self.config.get('scale', 1.0) * 100))
        self.scale_badge = QLabel(f"{saved_scale}%", size_card)
        self.scale_badge.setStyleSheet("color: #f3f4f6; font-weight: 600; font-size: 11px;")
        scale_label_layout.addWidget(self.scale_badge)
        size_layout.addLayout(scale_label_layout)

        self.scale_slider = QSlider(Qt.Orientation.Horizontal, size_card)
        self.scale_slider.setRange(50, 150)
        self.scale_slider.setValue(saved_scale)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        size_layout.addWidget(self.scale_slider)

        # Opacity Slider
        op_label_layout = QHBoxLayout()
        op_title = QLabel("Transparency:", size_card)
        op_title.setStyleSheet("color: #858997; font-size: 11px;")
        op_label_layout.addWidget(op_title)
        op_label_layout.addStretch()

        saved_opacity = int(round(self.config.get('opacity', 1.0) * 100))
        self.opacity_badge = QLabel(f"{saved_opacity}%", size_card)
        self.opacity_badge.setStyleSheet("color: #f3f4f6; font-weight: 600; font-size: 11px;")
        op_label_layout.addWidget(self.opacity_badge)
        size_layout.addLayout(op_label_layout)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal, size_card)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(saved_opacity)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        size_layout.addWidget(self.opacity_slider)

        layout.addWidget(size_card)

        # 3. Effects Card
        fx_card = QFrame(container)
        fx_card.setObjectName("innerCard")
        fx_layout = QVBoxLayout(fx_card)
        fx_layout.setContentsMargins(10, 8, 10, 8)
        fx_layout.setSpacing(6)

        fx_header = QLabel("Effects", fx_card)
        fx_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #9ca3af;")
        fx_layout.addWidget(fx_header)

        self.ripple_cb = QCheckBox("Enable ripple effect on keypress", fx_card)
        self.ripple_cb.setChecked(self.config.get('ripple_effect', True))
        self.ripple_cb.toggled.connect(self.on_settings_changed)
        fx_layout.addWidget(self.ripple_cb)

        self.tactile_cb = QCheckBox("Enable key depression animation", fx_card)
        self.tactile_cb.setChecked(self.config.get('tactile_anim', True))
        self.tactile_cb.toggled.connect(self.on_settings_changed)
        fx_layout.addWidget(self.tactile_cb)

        layout.addWidget(fx_card)
        layout.addStretch()
        return self.wrap_in_scroll(container)

    def on_scale_changed(self, val):
        self.scale_badge.setText(f"{val}%")
        self.on_settings_changed()

    def on_opacity_changed(self, val):
        self.opacity_badge.setText(f"{val}%")
        self.on_settings_changed()

    # =========================================================================
    # TAB 3: PRESETS (COMPACT)
    # =========================================================================
    def build_presets_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(8)

        card = QFrame(container)
        card.setObjectName("innerCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(8)

        header = QLabel("Presets Management", card)
        header.setStyleSheet("font-size: 11px; font-weight: 700; color: #9ca3af;")
        card_layout.addWidget(header)

        row1 = QHBoxLayout()
        self.presets_combo = QComboBox(card)
        self.presets_combo.addItems(list(self.config['presets'].keys()))
        self.presets_combo.setCurrentText(self.config['active_preset'])
        self.presets_combo.currentTextChanged.connect(self.on_preset_changed)
        row1.addWidget(self.presets_combo)

        self.add_preset_btn = QPushButton("New Preset", card)
        self.add_preset_btn.setFixedHeight(26)
        self.add_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_preset_btn.clicked.connect(self.add_new_preset)
        row1.addWidget(self.add_preset_btn)
        card_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(6)

        self.record_preset_btn = QPushButton("Record Keys", card)
        self.record_preset_btn.setFixedHeight(26)
        self.record_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_preset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: 1px solid #3b82f6;
                border-radius: 5px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #1d4ed8; }
        """)
        self.record_preset_btn.clicked.connect(self.record_current_preset)
        row2.addWidget(self.record_preset_btn)

        self.rename_preset_btn = QPushButton("Rename", card)
        self.rename_preset_btn.setFixedHeight(26)
        self.rename_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rename_preset_btn.clicked.connect(self.rename_current_preset)
        row2.addWidget(self.rename_preset_btn)

        self.delete_preset_btn = QPushButton("Delete", card)
        self.delete_preset_btn.setFixedHeight(26)
        self.delete_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_preset_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1c22;
                color: #ef4444;
                border: 1px solid #3b2228;
                border-radius: 5px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #ef4444; color: white; }
        """)
        self.delete_preset_btn.clicked.connect(self.delete_current_preset)
        row2.addWidget(self.delete_preset_btn)
        card_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.setSpacing(6)

        self.import_preset_btn = QPushButton("Import JSON", card)
        self.import_preset_btn.setFixedHeight(26)
        self.import_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_preset_btn.clicked.connect(self.import_preset)
        row3.addWidget(self.import_preset_btn)

        self.export_preset_btn = QPushButton("Export JSON", card)
        self.export_preset_btn.setFixedHeight(26)
        self.export_preset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_preset_btn.clicked.connect(self.export_preset)
        row3.addWidget(self.export_preset_btn)
        card_layout.addLayout(row3)

        self.presets_status_label = QLabel(card)
        self.presets_status_label.setStyleSheet("color: #7f8492; font-size: 10px; padding-top: 2px;")
        active_preset = self.config['active_preset']
        num_keys = len(self.config['presets'].get(active_preset, []))
        self.presets_status_label.setText(f"{num_keys} keys registered in '{active_preset}'")
        card_layout.addWidget(self.presets_status_label)

        layout.addWidget(card)
        layout.addStretch()
        return self.wrap_in_scroll(container)

    # =========================================================================
    # TAB 4: SETTINGS / PREFERENCES (COMPACT)
    # =========================================================================
    def build_preferences_tab(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(8)

        # 1. Behavior Card
        behave_card = QFrame(container)
        behave_card.setObjectName("innerCard")
        b_layout = QVBoxLayout(behave_card)
        b_layout.setContentsMargins(10, 8, 10, 8)
        b_layout.setSpacing(6)

        b_header = QLabel("Interaction", behave_card)
        b_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #9ca3af;")
        b_layout.addWidget(b_header)

        self.click_through_cb = QCheckBox("Enable Click-Through Mode (clicks pass through overlay)", behave_card)
        self.click_through_cb.setChecked(self.config.get('no_mouse', False))
        self.click_through_cb.toggled.connect(self.on_settings_changed)
        b_layout.addWidget(self.click_through_cb)

        self.compact_cb = QCheckBox("Compact Window Mode (auto-fit canvas tightly to active keys)", behave_card)
        self.compact_cb.setChecked(self.config.get('compact_mode', False))
        self.compact_cb.toggled.connect(self.on_settings_changed)
        b_layout.addWidget(self.compact_cb)

        layout.addWidget(behave_card)

        # 2. Positioning Tools
        pos_card = QFrame(container)
        pos_card.setObjectName("innerCard")
        p_layout = QVBoxLayout(pos_card)
        p_layout.setContentsMargins(10, 8, 10, 8)
        p_layout.setSpacing(6)

        p_header = QLabel("Positioning Tools", pos_card)
        p_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #9ca3af;")
        p_layout.addWidget(p_header)

        p_desc = QLabel("Drag to reposition the overlay window or individual keycaps.", pos_card)
        p_desc.setStyleSheet("color: #7f8492; font-size: 10px;")
        p_layout.addWidget(p_desc)

        pos_btn_layout = QHBoxLayout()
        pos_btn_layout.setSpacing(6)

        self.pos_overlay_btn = QPushButton("Move Overlay", pos_card)
        self.pos_overlay_btn.setFixedHeight(26)
        self.pos_overlay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pos_overlay_btn.clicked.connect(self.position_overlay)
        pos_btn_layout.addWidget(self.pos_overlay_btn)

        self.pos_keys_btn = QPushButton("Rearrange Keys", pos_card)
        self.pos_keys_btn.setFixedHeight(26)
        self.pos_keys_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pos_keys_btn.clicked.connect(self.position_keys)
        pos_btn_layout.addWidget(self.pos_keys_btn)

        p_layout.addLayout(pos_btn_layout)
        layout.addWidget(pos_card)

        # 3. Reset Card
        maint_card = QFrame(container)
        maint_card.setObjectName("innerCard")
        m_layout = QVBoxLayout(maint_card)
        m_layout.setContentsMargins(10, 8, 10, 8)
        m_layout.setSpacing(6)

        m_header = QLabel("Reset", maint_card)
        m_header.setStyleSheet("font-size: 11px; font-weight: 700; color: #9ca3af;")
        m_layout.addWidget(m_header)

        reset_btn = QPushButton("Reset Settings to Defaults", maint_card)
        reset_btn.setFixedHeight(26)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1c22;
                color: #ef4444;
                border: 1px solid #3b2026;
                border-radius: 5px;
                padding: 5px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #ef4444; color: white; }
        """)
        reset_btn.clicked.connect(self.confirm_reset)
        m_layout.addWidget(reset_btn)

        layout.addWidget(maint_card)
        layout.addStretch()
        return self.wrap_in_scroll(container)

    # =========================================================================
    # LOGIC & EVENT HANDLERS
    # =========================================================================
    def get_selected_mode(self):
        if self.mode_gaming.isChecked():
            return "gaming"
        elif self.mode_custom.isChecked():
            return "custom"
        return "normal"

    def get_selected_color(self):
        if self.color_slate.isChecked():
            return "slate"
        elif self.color_blue.isChecked():
            return "blue"
        elif self.color_green.isChecked():
            return "green"
        elif self.color_amber.isChecked():
            return "amber"
        elif self.color_rose.isChecked():
            return "rose"
        elif self.color_spectrum.isChecked():
            return "spectrum"
        elif self.color_custom.isChecked():
            txt = self.hex_input.text().strip()
            return txt if txt else "#ffffff"
        return "white"

    def open_color_dialog(self):
        current_hex = self.hex_input.text().strip() or "#ffffff"
        color = QColorDialog.getColor(QColor(current_hex), self, "Select Color")
        if color.isValid():
            hex_name = color.name().upper()
            self.hex_input.setText(hex_name)
            self.color_preview.setStyleSheet(f"border-radius: 9px; background-color: {hex_name}; border: 1px solid #4b5563;")
            self.color_custom.setChecked(True)
            self.on_settings_changed()

    def on_hex_text_changed(self, text):
        text = text.strip()
        if len(text) == 7 and text.startswith("#"):
            self.color_preview.setStyleSheet(f"border-radius: 9px; background-color: {text}; border: 1px solid #4b5563;")
            if self.color_custom.isChecked():
                self.on_settings_changed()

    def toggle_overlay(self):
        if self.overlay_instance is None:
            self.start_overlay()
        else:
            self.stop_overlay()

    def start_overlay(self, setup_mode=None):
        self.save_config()
        
        custom_keys_str = None
        if self.config['mode'] == 'custom':
            active_preset = self.config.get('active_preset')
            if active_preset and active_preset in self.config.get('presets', {}):
                recorded_list = self.config['presets'][active_preset]
            else:
                recorded_list = self.config.get('recorded_keys', {}).get('gaming', [])
            custom_keys_str = ",".join(recorded_list)

        self.overlay_instance = KeyboardOverlay(
            mode=self.config['mode'],
            custom_keys=custom_keys_str,
            color_mode=self.config['color'],
            setup_mode=setup_mode,
            force_no_mouse=self.config['no_mouse'],
            scale=self.config.get('scale', 1.0),
            opacity=self.config.get('opacity', 1.0),
            compact_mode=self.config.get('compact_mode', False)
        )
        self.overlay_instance.tactile_anim = self.config.get('tactile_anim', True)
        self.overlay_instance.ripple_effect = self.config.get('ripple_effect', True)
        self.overlay_instance.launched_from_menu = True

        if setup_mode:
            self.hide()
            def handle_overlay_close():
                self.show()
                self.stop_overlay()
                self.config = self.load_config()
            self.overlay_instance.closed_signal.connect(handle_overlay_close)

        self.update_toggle_button_ui(True)
        self.pos_overlay_btn.setEnabled(False)
        self.pos_keys_btn.setEnabled(False)
        self.update_tray_menu()

    def update_toggle_button_ui(self, is_active):
        """Update status indicator, text, and button style consistently."""
        if not hasattr(self, 'toggle_btn') or not hasattr(self, 'status_dot'):
            return
        if is_active:
            self.status_dot.setStyleSheet("border-radius: 4px; background-color: #22c55e;")
            self.status_text.setText("Overlay Active")
            self.toggle_btn.setText("Stop Overlay")
            self.toggle_btn.setStyleSheet("""
                QPushButton#toggleButton {
                    background-color: #1e293b;
                    color: #e2e8f0;
                    border: 1px solid #334155;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 5px 12px;
                    border-radius: 5px;
                }
                QPushButton#toggleButton:hover {
                    background-color: #334155;
                    color: #ffffff;
                }
            """)
        else:
            self.status_dot.setStyleSheet("border-radius: 4px; background-color: #64748b;")
            self.status_text.setText("Overlay Stopped")
            self.toggle_btn.setText("Start Overlay")
            self.toggle_btn.setStyleSheet("""
                QPushButton#toggleButton {
                    background-color: #2563eb;
                    color: #ffffff;
                    border: 1px solid #3b82f6;
                    font-size: 11px;
                    font-weight: 600;
                    padding: 5px 12px;
                    border-radius: 5px;
                }
                QPushButton#toggleButton:hover {
                    background-color: #1d4ed8;
                }
                QPushButton#toggleButton:pressed {
                    background-color: #1e40af;
                }
            """)

    def stop_overlay(self):
        if self.overlay_instance is not None:
            overlay = self.overlay_instance
            self.overlay_instance = None
            try:
                overlay.closed_signal.disconnect()
            except Exception:
                pass
            try:
                overlay.close()
            except Exception:
                pass

        self.update_toggle_button_ui(False)
        self.pos_overlay_btn.setEnabled(True)
        self.pos_keys_btn.setEnabled(True)
        self.update_tray_menu()

    def on_settings_changed(self):
        self.save_config()
        
        if hasattr(self, 'preview_widget'):
            self.preview_widget.set_config(
                self.config['mode'],
                self.config['color'],
                self.config.get('active_preset'),
                self.config.get('presets', {})
            )

        if self.overlay_instance is not None:
            self.overlay_instance.mode = self.config['mode']
            self.overlay_instance.color_mode = self.config['color']
            self.overlay_instance.is_locked = self.config['no_mouse']
            self.overlay_instance.scale = self.config.get('scale', 1.0)
            self.overlay_instance.opacity = self.config.get('opacity', 1.0)
            self.overlay_instance.compact_mode = self.config.get('compact_mode', False)
            self.overlay_instance.ripple_effect = self.config.get('ripple_effect', True)
            self.overlay_instance.tactile_anim = self.config.get('tactile_anim', True)

            custom_keys_str = None
            if self.config['mode'] == 'custom':
                active_preset = self.config.get('active_preset')
                if active_preset and active_preset in self.config.get('presets', {}):
                    recorded_list = self.config['presets'][active_preset]
                else:
                    recorded_list = self.config.get('recorded_keys', {}).get('gaming', [])
                custom_keys_str = ",".join(recorded_list)

            self.overlay_instance.custom_keys = custom_keys_str
            self.overlay_instance.rebuild_ui()
            self.overlay_instance.apply_behavior()

    def position_overlay(self):
        self.stop_overlay()
        self.start_overlay(setup_mode='all')

    def position_keys(self):
        self.stop_overlay()
        self.start_overlay(setup_mode='custom')

    def on_preset_changed(self, text):
        if not text:
            return
        self.config['active_preset'] = text
        num_keys = len(self.config['presets'].get(text, []))
        self.presets_status_label.setText(f"{num_keys} keys in '{text}'")
        
        if not self.mode_custom.isChecked():
            self.mode_custom.setChecked(True)
        else:
            self.on_settings_changed()

    def add_new_preset(self):
        dlg = AddPresetDialog(self)
        if dlg.exec():
            name = dlg.preset_name
            if name in self.config['presets']:
                QMessageBox.warning(self, "Duplicate Name", f"A preset named '{name}' exists.")
                return
                
            self.config['presets'][name] = []
            self.save_config()
            
            self.presets_combo.blockSignals(True)
            self.presets_combo.clear()
            self.presets_combo.addItems(list(self.config['presets'].keys()))
            self.presets_combo.setCurrentText(name)
            self.presets_combo.blockSignals(False)
            
            self.config['active_preset'] = name
            self.presets_status_label.setText(f"0 keys in '{name}'")
            self.record_current_preset()

    def record_current_preset(self):
        active_preset = self.presets_combo.currentText()
        if not active_preset:
            return
        
        self.stop_overlay()
        dlg = KeyRecorderDialog(self)
        dlg.recorded_keys = list(self.config['presets'].get(active_preset, []))
        dlg.update_display()
        
        if dlg.exec():
            self.config['presets'][active_preset] = dlg.recorded_keys
            self.save_config()
            num_keys = len(dlg.recorded_keys)
            self.presets_status_label.setText(f"{num_keys} keys in '{active_preset}'")
            self.mode_custom.setChecked(True)
            self.on_settings_changed()

    def rename_current_preset(self):
        active_preset = self.presets_combo.currentText()
        if not active_preset:
            return
        
        new_name, ok = QInputDialog.getText(
            self, "Rename Preset", f"Enter new name for '{active_preset}':", text=active_preset
        )
        if ok and new_name.strip() and new_name.strip() != active_preset:
            new_name = new_name.strip()
            if new_name in self.config['presets']:
                QMessageBox.warning(self, "Duplicate Name", f"A preset named '{new_name}' exists.")
                return
            
            self.config['presets'][new_name] = self.config['presets'].pop(active_preset)
            self.config['active_preset'] = new_name
            self.save_config()
            
            self.presets_combo.blockSignals(True)
            self.presets_combo.clear()
            self.presets_combo.addItems(list(self.config['presets'].keys()))
            self.presets_combo.setCurrentText(new_name)
            self.presets_combo.blockSignals(False)
            
            self.presets_status_label.setText(f"{len(self.config['presets'][new_name])} keys in '{new_name}'")
            self.on_settings_changed()

    def delete_current_preset(self):
        active_preset = self.presets_combo.currentText()
        if not active_preset:
            return
            
        if len(self.config['presets']) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "You must keep at least one preset.")
            return
            
        reply = QMessageBox.question(
            self, "Delete Preset", f"Delete preset '{active_preset}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config['presets'].pop(active_preset)
            new_active = list(self.config['presets'].keys())[0]
            self.config['active_preset'] = new_active
            self.save_config()
            
            self.presets_combo.blockSignals(True)
            self.presets_combo.clear()
            self.presets_combo.addItems(list(self.config['presets'].keys()))
            self.presets_combo.setCurrentText(new_active)
            self.presets_combo.blockSignals(False)
            
            self.presets_status_label.setText(f"{len(self.config['presets'][new_active])} keys in '{new_active}'")
            self.on_settings_changed()

    def export_preset(self):
        active_preset = self.presets_combo.currentText()
        if not active_preset:
            return
            
        keys_list = self.config['presets'].get(active_preset, [])
        export_data = {"preset_name": active_preset, "keys": keys_list}
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Preset", f"{active_preset}.json", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                QMessageBox.information(self, "Export Success", f"Preset saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")

    def import_preset(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Preset", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                
                preset_name = None
                keys_list = None
                if isinstance(import_data, dict):
                    preset_name = import_data.get("preset_name")
                    keys_list = import_data.get("keys")
                elif isinstance(import_data, list):
                    keys_list = import_data
                
                if keys_list is None or not isinstance(keys_list, list):
                    raise ValueError("File must contain a list of keys.")
                    
                if not preset_name:
                    preset_name = os.path.splitext(os.path.basename(file_path))[0]
                
                if preset_name in self.config['presets']:
                    new_name, ok = QInputDialog.getText(
                        self, "Duplicate Preset Name",
                        f"Preset '{preset_name}' exists.\nEnter a new name:",
                        text=f"{preset_name}_imported"
                    )
                    if ok and new_name.strip():
                        preset_name = new_name.strip()
                    else:
                        return
                
                self.config['presets'][preset_name] = keys_list
                self.config['active_preset'] = preset_name
                self.save_config()
                
                self.presets_combo.blockSignals(True)
                self.presets_combo.clear()
                self.presets_combo.addItems(list(self.config['presets'].keys()))
                self.presets_combo.setCurrentText(preset_name)
                self.presets_combo.blockSignals(False)
                
                self.presets_status_label.setText(f"{len(keys_list)} keys in '{preset_name}'")
                self.mode_custom.setChecked(True)
                self.on_settings_changed()
                QMessageBox.information(self, "Import Success", f"Preset '{preset_name}' imported.")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import:\n{str(e)}")

    def confirm_reset(self):
        reply = QMessageBox.question(
            self, "Reset Settings", "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.stop_overlay()
            if os.path.exists(self.config_file):
                try:
                    os.remove(self.config_file)
                except Exception:
                    pass
            self.config = self.load_config()
            self.init_presets()
            self.on_settings_changed()
            QMessageBox.information(self, "Reset", "Settings reset to defaults.")

    # =========================================================================
    # SYSTEM TRAY
    # =========================================================================
    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(self.icon_path):
            self.tray_icon.setIcon(QIcon(self.icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        
        self.tray_menu = QMenu()
        self.action_show = QAction("Show Control Panel", self)
        self.action_show.triggered.connect(self.show_normal)
        self.tray_menu.addAction(self.action_show)
        self.tray_menu.addSeparator()
        
        self.action_toggle = QAction("Start Overlay", self)
        self.action_toggle.triggered.connect(self.toggle_overlay)
        self.tray_menu.addAction(self.action_toggle)
        self.tray_menu.addSeparator()
        
        action_quit = QAction("Exit KeyViz", self)
        action_quit.triggered.connect(self.quit_app)
        self.tray_menu.addAction(action_quit)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_activated)

    def show_normal(self):
        self.show()
        self.activateWindow()

    def update_tray_menu(self):
        if self.overlay_instance is None:
            self.action_toggle.setText("Start Overlay")
        else:
            self.action_toggle.setText("Stop Overlay")

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "KeyViz",
                "KeyViz is minimized to the system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                1500
            )
            event.ignore()
        else:
            self.quit_app()

    def quit_app(self):
        self.stop_overlay()
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.tray_icon.hide()
        QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            title_geo = self.title_bar.geometry()
            pos_in_win = self.title_bar.mapTo(self, QPoint(0, 0))
            title_geo.moveTo(pos_in_win)
            if title_geo.contains(event.pos()):
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
            else:
                super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and getattr(self, 'drag_position', None):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        super().mouseReleaseEvent(event)

    # =========================================================================
    # COMPACT SLATE STYLESHEET WITH CRISP TYPOGRAPHY
    # =========================================================================
    def get_stylesheet(self):
        return """
        QWidget {
            background-color: transparent;
            color: #e2e8f0;
            font-family: 'Segoe UI Variable Text', 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
            font-size: 11px;
        }

        QFrame#mainCard {
            background-color: #111216;
            border-radius: 8px;
            border: 1px solid #20222b;
        }

        QFrame#innerCard {
            background-color: #16171e;
            border-radius: 6px;
            border: 1px solid #252834;
        }

        QFrame#navContainer {
            background-color: #0d0e12;
            border-radius: 5px;
            border: 1px solid #1f212a;
        }

        QPushButton#navPillBtn {
            background-color: transparent;
            color: #94a3b8;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 11px;
        }
        QPushButton#navPillBtn:hover {
            color: #f8fafc;
            background-color: #1a1c24;
        }
        QPushButton#navPillBtn:checked {
            background-color: #22252e;
            color: #ffffff;
            border: 1px solid #333846;
            font-weight: 600;
        }

        QPushButton#profilePillBtn {
            background-color: #14151b;
            color: #94a3b8;
            border: 1px solid #272a36;
            padding: 5px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
        }
        QPushButton#profilePillBtn:hover {
            background-color: #1e2029;
            color: #f1f5f9;
            border-color: #383c4c;
        }
        QPushButton#profilePillBtn:checked {
            background-color: #2563eb;
            color: #ffffff;
            border: 1px solid #3b82f6;
            font-weight: 600;
        }

        QPushButton#toggleButton {
            background-color: #2563eb;
            color: #ffffff;
            border: 1px solid #3b82f6;
            font-size: 11px;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 5px;
        }
        QPushButton#toggleButton:hover {
            background-color: #1d4ed8;
        }
        QPushButton#toggleButton:pressed {
            background-color: #1e40af;
        }

        QPushButton {
            background-color: #1a1b22;
            border: 1px solid #282b36;
            color: #e2e8f0;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: 600;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #242632;
            color: #ffffff;
            border-color: #3a3d4c;
        }
        QPushButton:pressed {
            background-color: #2c2f3e;
        }
        QPushButton:disabled {
            background-color: #131418;
            color: #4b5563;
            border-color: #1c1d23;
        }

        QRadioButton {
            spacing: 6px;
            color: #e2e8f0;
            font-size: 11px;
            font-weight: 500;
        }
        QRadioButton:hover {
            color: #ffffff;
        }
        QRadioButton::indicator {
            width: 14px;
            height: 14px;
            border-radius: 7px;
            border: 1.5px solid #475569;
            background-color: #0d0e12;
        }
        QRadioButton::indicator:hover {
            border-color: #94a3b8;
        }
        QRadioButton::indicator:checked {
            border: 4px solid #3b82f6;
            background-color: #0d0e12;
        }

        QCheckBox {
            spacing: 6px;
            color: #e2e8f0;
            font-size: 11px;
            font-weight: 500;
        }
        QCheckBox:hover {
            color: #ffffff;
        }
        QCheckBox::indicator {
            width: 14px;
            height: 14px;
            border-radius: 3px;
            border: 1.5px solid #475569;
            background-color: #0d0e12;
        }
        QCheckBox::indicator:hover {
            border-color: #94a3b8;
        }
        QCheckBox::indicator:checked {
            background-color: #2563eb;
            border: 1.5px solid #60a5fa;
        }

        QLineEdit {
            background-color: #0d0e12;
            border: 1px solid #242632;
            border-radius: 5px;
            padding: 4px 6px;
            color: #ffffff;
            font-size: 11px;
        }
        QLineEdit:focus {
            border: 1px solid #4b5563;
        }

        QComboBox {
            background-color: #0d0e12;
            border: 1px solid #242632;
            border-radius: 5px;
            padding: 4px 6px;
            color: #ffffff;
            font-size: 11px;
            font-weight: 500;
        }
        QComboBox:hover {
            border-color: #4b5563;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 0px;
        }
        QComboBox::down-arrow {
            border: 3px solid transparent;
            border-top-color: #94a3b8;
            margin-top: 2px;
        }
        QComboBox QAbstractItemView {
            background-color: #14151b;
            border: 1px solid #242632;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
            color: #ffffff;
            outline: none;
            padding: 3px;
        }

        QSlider::groove:horizontal {
            height: 3px;
            background: #20222b;
            border-radius: 1px;
        }
        QSlider::sub-page:horizontal {
            background: #4b5563;
            border-radius: 1px;
        }
        QSlider::handle:horizontal {
            background: #f1f5f9;
            border: 1px solid #64748b;
            width: 12px;
            margin-top: -5px;
            margin-bottom: -5px;
            border-radius: 6px;
        }
        QSlider::handle:horizontal:hover {
            background: #ffffff;
        }

        QScrollBar:vertical {
            border: none;
            background: transparent;
            width: 4px;
        }
        QScrollBar::handle:vertical {
            background: #252834;
            min-height: 16px;
            border-radius: 2px;
        }
        QScrollBar::handle:vertical:hover {
            background: #3b3f4e;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        """
