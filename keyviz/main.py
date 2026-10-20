import sys
import json
import random
import math
import colorsys
import keyboard
import argparse
import traceback
import time
import signal
import os
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QPainter, QPen, QBrush, QLinearGradient, QRadialGradient,
    QFontDatabase, QFontInfo
)

# Base directory for static files (inside keyviz package directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Determine CONFIG_DIR for dynamic config files (config.json, crash.log, etc.)
if "site-packages" in BASE_DIR or "dist-packages" in BASE_DIR:
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".keyviz")
    os.makedirs(CONFIG_DIR, exist_ok=True)
else:
    # Use parent directory of keyviz/ (project root)
    CONFIG_DIR = os.path.dirname(BASE_DIR)

# Global debug flag
DEBUG_MODE = False

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)
        sys.stdout.flush()


def get_theme_color(color_mode, x_ratio=0.0, global_offset=0.0):
    """
    Subdued, elegant color generator.
    Returns non-neon, professional color tones.
    """
    mode = (color_mode or "white").lower().strip()
    
    if mode in ["white", "monochrome", "putih", "clean"]:
        return QColor("#ffffff")
        
    elif mode in ["slate", "gray", "default"]:
        return QColor("#94a3b8")
        
    elif mode in ["blue", "nordic", "tokyo"]:
        return QColor("#60a5fa")
        
    elif mode in ["green", "sage", "matrix"]:
        return QColor("#4ade80")
        
    elif mode in ["amber", "warm", "sunset"]:
        return QColor("#fbbf24")
        
    elif mode in ["rose", "subtle", "cyberpunk"]:
        return QColor("#f87171")
        
    elif mode in ["cyan", "teal"]:
        return QColor("#38bdf8")

    elif mode in ["rainbow", "spectrum", "rgb"]:
        hue = (global_offset + x_ratio) % 1.0
        # Gentle muted spectrum (low saturation, elegant, non-neon)
        rgb = colorsys.hls_to_rgb(hue, 0.65, 0.50)
        return QColor(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
        
    elif mode.startswith("#"):
        try:
            return QColor(mode)
        except Exception:
            return QColor("#ffffff")
            
    else:
        return QColor("#ffffff")


class KeyboardSignaller(QObject):
    press_sig = pyqtSignal(int, str)
    release_sig = pyqtSignal(int, str)


class RippleEffect:
    """Expanding radial shockwave effect radiating from pressed key."""
    def __init__(self, center, w, h, label, font, color, opacity=1.0):
        self.center = center
        self.orig_w = float(w)
        self.orig_h = float(h)
        self.label = label
        self.font = font
        self.color = color
        self.base_opacity = opacity
        self.life = 1.0
        self.scale = 1.0
        self.speed = 0.045
        self.fade_speed = 0.04

    def update(self):
        self.scale += self.speed
        self.life -= self.fade_speed
        return self.life > 0.0


class KeyButton(QWidget):
    """
    High-performance vector-rendered keycap with realistic 3D bevels,
    tactile depression physics, dynamic theme lighting, and zero CSS churn.
    """
    def __init__(self, sc_key, sc_list, display_name, width, height, is_knob=False, parent=None,
                 color_mode="rgb", scale=1.0, opacity=1.0, tactile_anim=True):
        super().__init__(parent)
        self.sc_key = sc_key
        self.sc_list = sc_list if isinstance(sc_list, list) else [sc_list]
        self.display_name = display_name
        self.base_w = width
        self.base_h = height
        self.is_knob = is_knob
        self.color_mode = color_mode
        self.scale = max(0.4, float(scale))
        self.opacity = max(0.1, min(1.0, float(opacity)))
        self.tactile_anim = tactile_anim
        
        self.is_active = False
        self.press_depth = 0.0
        self.active_color = None
        self.knob_angle = 0.0
        self.dragPos = QPoint()
        
        # Geometry
        w_scaled = int(round(self.base_w * self.scale))
        h_scaled = int(round(self.base_h * self.scale))
        self.setFixedSize(w_scaled, h_scaled)
        
        # Typography selection
        font_size = int(max(7, round(10 * self.scale)))
        self.font = QFont("Segoe UI Variable Text", font_size, QFont.Weight.DemiBold)
        if not QFontInfo(self.font).exactMatch():
            self.font = QFont("Segoe UI", font_size, QFont.Weight.DemiBold)
        self.font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

    def set_active(self, active, color=None):
        if self.is_active != active or (active and self.active_color != color):
            self.is_active = active
            self.active_color = color
            self.press_depth = 1.0 if active else 0.0
            if self.is_knob and active:
                self.knob_angle = (self.knob_angle + 30.0) % 360.0
            self.update()

    def update_geometry_scale(self, new_scale, new_opacity=None):
        self.scale = max(0.4, float(new_scale))
        if new_opacity is not None:
            self.opacity = max(0.1, min(1.0, float(new_opacity)))
        w_scaled = int(round(self.base_w * self.scale))
        h_scaled = int(round(self.base_h * self.scale))
        self.setFixedSize(w_scaled, h_scaled)
        
        font_size = int(max(7, round(10 * self.scale)))
        self.font = QFont("Segoe UI Variable Text", font_size, QFont.Weight.DemiBold)
        if not QFontInfo(self.font).exactMatch():
            self.font = QFont("Segoe UI", font_size, QFont.Weight.DemiBold)
        self.font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())

        # Original transparent wireframe style:
        # Idle: #40000000 (semi-transparent black), thin wireframe border #20FFFFFF
        # Active: #80000000, 2.5px solid theme color border

        # --- ROTARY KNOB RENDERING ---
        if self.is_knob:
            r = min(w, h) / 2.0 - 1.5
            cx, cy = w / 2.0, h / 2.0
            center = QPointF(cx, cy)

            if self.is_active:
                color = self.active_color or QColor("#ffffff")
                painter.setBrush(QColor(0, 0, 0, int(130 * self.opacity)))
                painter.setPen(QPen(color, 2.5 * self.scale))
                painter.drawEllipse(center, r, r)

                rad = math.radians(self.knob_angle)
                nx = cx + (r - 5.0 * self.scale) * math.cos(rad)
                ny = cy + (r - 5.0 * self.scale) * math.sin(rad)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(QPointF(nx, ny), 2.5 * self.scale, 2.5 * self.scale)
            else:
                painter.setBrush(QColor(0, 0, 0, int(64 * self.opacity)))
                painter.setPen(QPen(QColor(255, 255, 255, int(32 * self.opacity)), 0.6))
                painter.drawEllipse(center, r, r)

                rad = math.radians(self.knob_angle)
                nx = cx + (r - 5.0 * self.scale) * math.cos(rad)
                ny = cy + (r - 5.0 * self.scale) * math.sin(rad)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 255, 255, int(150 * self.opacity)))
                painter.drawEllipse(QPointF(nx, ny), 2.0 * self.scale, 2.0 * self.scale)
            return

        # --- RECTANGULAR WIREFRAME KEYCAP ---
        round_r = 4.0 * self.scale
        rect = QRectF(1.0, 1.0, w - 2.0, h - 2.0)

        if self.is_active:
            color = self.active_color or QColor("#ffffff")
            # Semi-transparent dark background (cleanly overlays on any desktop/game)
            painter.setBrush(QColor(0, 0, 0, int(130 * self.opacity)))
            painter.setPen(QPen(color, 2.5 * self.scale))
            painter.drawRoundedRect(rect, round_r, round_r)

            # Crisp white active text
            painter.setFont(self.font)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.display_name)
        else:
            # Original transparent wireframe style
            painter.setBrush(QColor(0, 0, 0, int(64 * self.opacity)))
            painter.setPen(QPen(QColor(255, 255, 255, int(32 * self.opacity)), 0.6))
            painter.drawRoundedRect(rect, round_r, round_r)

            # Crisp white idle text
            painter.setFont(self.font)
            painter.setPen(QColor(255, 255, 255, int(240 * self.opacity)))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.display_name)

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
                # Unscale coordinate back to base reference
                parent_scale = getattr(self.parent(), 'scale', 1.0)
                base_x = int(round(new_pos.x() / parent_scale))
                base_y = int(round(new_pos.y() / parent_scale))
                self.parent().update_button_pos(self.sc_key, base_x, base_y)
            event.accept()
        else:
            super().mouseMoveEvent(event)


class KeyboardOverlay(QWidget):
    closed_signal = pyqtSignal()
    request_close_signal = pyqtSignal()

    def __init__(self, mode="normal", custom_keys=None, color_mode="default", setup_mode=None,
                 force_pos=None, force_no_mouse=False, scale=1.0, opacity=1.0, compact_mode=False):
        super().__init__()
        self.mode = mode
        self.custom_keys = custom_keys
        self.color_mode = color_mode
        self.scale = max(0.4, float(scale))
        self.opacity = max(0.1, min(1.0, float(opacity)))
        self.compact_mode = compact_mode
        self.tactile_anim = True
        self.ripple_effect = True
        
        self.recorded_keys = set()
        self.custom_pos = {}
        self.keys_map = {}
        self.ripples = []
        self.signaller = KeyboardSignaller()
        self.buttons = []
        self.global_hue_offset = 0.0
        self.key_last_wave_time = {}
        self.dragPos = QPoint()
        
        self.main_config_file = os.path.join(CONFIG_DIR, 'config.json')
        self.load_files()
        
        config_exists = os.path.exists(self.main_config_file)
        legacy_exists = (os.path.exists(os.path.join(CONFIG_DIR, 'settings.json')) or 
                         os.path.exists(os.path.join(CONFIG_DIR, 'recorded_keys.json')))
        
        self.setup_mode = setup_mode
        if not self.setup_mode and not config_exists and not legacy_exists:
            self.setup_mode = 'all'
            
        self.is_in_setup = bool(self.setup_mode)
        self.is_locked = force_no_mouse if not self.is_in_setup else False

        self.initUI()
        self.load_config()
        
        if force_pos:
            try:
                x, y = map(int, force_pos.split(','))
                self.move(x, y)
                debug_print(f"Position override: {x},{y}")
            except Exception:
                pass

        self.apply_behavior()
        
        # High-performance adaptive animation timer (60 FPS when active, auto-sleeps when idle)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_anim)
        self.timer.start(16)
        
        self.signal_timer = QTimer(self)
        self.signal_timer.timeout.connect(lambda: None)
        self.signal_timer.start(250)

        self.request_close_signal.connect(self.confirm_and_close)
        self.signaller.press_sig.connect(self.handle_press)
        self.signaller.release_sig.connect(self.handle_release)
        
        QTimer.singleShot(400, self.start_keyboard_hook)

    def start_keyboard_hook(self):
        try:
            keyboard.hook(self.on_key_event)
            debug_print("Keyboard hook established.")
        except Exception as e:
            print(f"[ERROR] Failed to establish keyboard hook: {e}")
            sys.exit(1)

    def apply_behavior(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        
        if self.is_locked and not self.is_in_setup:
            flags |= Qt.WindowType.WindowTransparentForInput
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            debug_print("Mode: LOCKED (Click-through enabled)")
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            debug_print(f"Mode: SETUP ({self.setup_mode})")
        
        self.setWindowFlags(flags)
        
        for btn in self.buttons:
            btn.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked and not self.is_in_setup)
            
        self.show()
        self.update()

    def load_files(self):
        try:
            with open(os.path.join(BASE_DIR, 'key.json'), 'r', encoding='utf-8') as f:
                self.key_mapping = json.load(f)
            with open(os.path.join(BASE_DIR, 'layout.json'), 'r', encoding='utf-8') as f:
                self.layout_config = json.load(f)
        except Exception as e:
            print(f"Failed to load static JSON files: {e}")
            sys.exit(1)

    def load_config(self):
        config_data = {}
        if not os.path.exists(self.main_config_file):
            migration_data = {
                "pos": [100, 100],
                "recorded_keys": {},
                "mode": "normal",
                "color": "default",
                "no_mouse": False,
                "scale": 1.0,
                "opacity": 1.0,
                "compact_mode": False
            }
            settings_path = os.path.join(CONFIG_DIR, 'settings.json')
            recorded_path = os.path.join(CONFIG_DIR, 'recorded_keys.json')
            
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        migration_data["pos"] = json.load(f).get("pos", [100, 100])
                except Exception:
                    pass
            if os.path.exists(recorded_path):
                try:
                    with open(recorded_path, 'r', encoding='utf-8') as f:
                        migration_data["recorded_keys"] = json.load(f)
                except Exception:
                    pass
            config_data = migration_data
            self.save_config(migration_data)
        else:
            try:
                with open(self.main_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except Exception as e:
                debug_print(f"Failed to load config: {e}")

        pos = config_data.get('pos')
        if pos:
            self.move(pos[0], pos[1])
            
        self.custom_pos = config_data.get('custom_pos', {})
        self.scale = float(config_data.get('scale', self.scale))
        self.opacity = float(config_data.get('opacity', self.opacity))
        self.compact_mode = bool(config_data.get('compact_mode', self.compact_mode))
        self.ripple_effect = bool(config_data.get('ripple_effect', True))
        self.tactile_anim = bool(config_data.get('tactile_anim', True))

        debug_print(f"Overlay Config - Mode: {self.mode}, Color: {self.color_mode}, Scale: {self.scale}, Compact: {self.compact_mode}")

        if not self.custom_keys:
            if self.mode == 'custom':
                active_preset = config_data.get('active_preset')
                presets = config_data.get('presets', {})
                if active_preset and active_preset in presets:
                    self.recorded_keys = set(presets[active_preset])
                else:
                    recorded = config_data.get('recorded_keys', {})
                    keys_for_mode = recorded.get('custom', [])
                    if not keys_for_mode:
                        keys_for_mode = recorded.get('gaming', [])
                    self.recorded_keys = set(keys_for_mode)
            else:
                recorded = config_data.get('recorded_keys', {})
                keys_for_mode = recorded.get(self.mode, [])
                if keys_for_mode:
                    self.recorded_keys = set(keys_for_mode)
            self.rebuild_ui()

    def save_config(self, data_override=None):
        try:
            if data_override is None:
                current_config = {}
                if os.path.exists(self.main_config_file):
                    try:
                        with open(self.main_config_file, 'r', encoding='utf-8') as f:
                            current_config = json.load(f)
                    except Exception:
                        pass
                
                current_config['pos'] = [self.x(), self.y()]
                current_config['mode'] = self.mode
                current_config['color'] = self.color_mode
                current_config['scale'] = self.scale
                current_config['opacity'] = self.opacity
                current_config['compact_mode'] = self.compact_mode
                current_config['ripple_effect'] = self.ripple_effect
                current_config['tactile_anim'] = self.tactile_anim
                
                if not self.is_in_setup:
                    current_config['no_mouse'] = self.is_locked
                
                if self.recorded_keys:
                    if self.mode == 'custom':
                        active_preset = current_config.get('active_preset')
                        if active_preset:
                            if 'presets' not in current_config:
                                current_config['presets'] = {}
                            current_config['presets'][active_preset] = list(self.recorded_keys)
                    else:
                        if 'recorded_keys' not in current_config:
                            current_config['recorded_keys'] = {}
                        current_config['recorded_keys'][self.mode] = list(self.recorded_keys)
                
                current_config['custom_pos'] = self.custom_pos
                data_to_save = current_config
            else:
                data_to_save = data_override

            with open(self.main_config_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2)
            debug_print("Config saved successfully.")
        except Exception as e:
            print(f"Failed to save config: {e}")

    def update_button_pos(self, sc_key, x, y):
        if self.mode not in self.custom_pos:
            self.custom_pos[self.mode] = {}
        self.custom_pos[self.mode][sc_key] = [x, y]

    def initUI(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.rebuild_ui()

    def rebuild_ui(self):
        for btn in self.buttons:
            btn.deleteLater()
        self.buttons = []
        self.keys_map = {}

        gaming_keys_default = ["w", "a", "s", "d", "space", "l_shift", "l_ctrl", "r", "e", "q", "f"]
        target_keys = None

        if self.recorded_keys:
            target_keys = set(k.lower() for k in self.recorded_keys)
        elif self.custom_keys:
            target_keys = set(k.strip().lower() for k in self.custom_keys.split(","))
        elif self.mode in ["gaming", "custom"]:
            target_keys = set(gaming_keys_default)

        # Filter items to render
        items_to_render = []
        for item in self.layout_config:
            sc_key = item['sc_key']
            if target_keys and sc_key.lower() not in target_keys:
                continue
            sc_val = self.key_mapping.get(sc_key)
            if sc_val is not None:
                items_to_render.append((item, sc_key, sc_val))

        if not items_to_render:
            # Fallback if empty
            for item in self.layout_config:
                sc_key = item['sc_key']
                if sc_key.lower() in gaming_keys_default:
                    sc_val = self.key_mapping.get(sc_key)
                    if sc_val is not None:
                        items_to_render.append((item, sc_key, sc_val))

        # Calculate bounding box for compact mode or dynamic window sizing
        padding = 18.0
        mode_customs = self.custom_pos.get(self.mode, {})

        if self.compact_mode and items_to_render:
            min_x = min(mode_customs.get(k, [it['x'], it['y']])[0] for it, k, _ in items_to_render)
            min_y = min(mode_customs.get(k, [it['x'], it['y']])[1] for it, k, _ in items_to_render)
            max_x = max(mode_customs.get(k, [it['x'], it['y']])[0] + it['w'] for it, k, _ in items_to_render)
            max_y = max(mode_customs.get(k, [it['x'], it['y']])[1] + it['h'] for it, k, _ in items_to_render)
            
            offset_x = min_x - padding
            offset_y = min_y - padding
            win_w = int(round((max_x - min_x + padding * 2) * self.scale))
            win_h = int(round((max_y - min_y + padding * 2) * self.scale))
        else:
            offset_x = 0.0
            offset_y = 0.0
            win_w = int(round(1120 * self.scale))
            win_h = int(round(440 * self.scale))

        self.setFixedSize(max(150, win_w), max(100, win_h))

        for item, sc_key, sc_val in items_to_render:
            pos_x, pos_y = item['x'], item['y']
            if sc_key in mode_customs:
                pos_x, pos_y = mode_customs[sc_key]

            # Apply compact offset and scaling
            final_x = int(round((pos_x - offset_x) * self.scale))
            final_y = int(round((pos_y - offset_y) * self.scale))

            btn = KeyButton(
                sc_key=sc_key,
                sc_list=sc_val,
                display_name=item['label'],
                width=item['w'],
                height=item['h'],
                is_knob=item.get('is_knob', False),
                parent=self,
                color_mode=self.color_mode,
                scale=self.scale,
                opacity=self.opacity,
                tactile_anim=self.tactile_anim
            )
            btn.move(final_x, final_y)
            self.buttons.append(btn)
            
            codes = sc_val if isinstance(sc_val, list) else [sc_val]
            for code in codes:
                if code not in self.keys_map:
                    self.keys_map[code] = []
                self.keys_map[code].append(btn)

    def confirm_and_close(self):
        self.save_config()
        debug_print("Position confirmed via ENTER.")
        if getattr(self, 'launched_from_menu', False):
            self.close()
        else:
            os._exit(0)

    def on_key_event(self, e):
        sc = e.scan_code
        key_name = (e.name or "").lower()
        if self.is_in_setup and (key_name in ['enter', 'return'] or sc in [28, 156]) and e.event_type == 'down':
            self.request_close_signal.emit()
            return

        if e.event_type == 'down':
            self.signaller.press_sig.emit(sc, e.name or "")
        else:
            self.signaller.release_sig.emit(sc, e.name or "")

    def closeEvent(self, event):
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        self.closed_signal.emit()
        event.accept()

    def handle_press(self, sc, name):
        name_str = (name or "").lower()
        is_right = "right" in name_str or "alt gr" in name_str
        mid_x = (self.width() / 2.0)

        if sc in self.keys_map:
            # Wake up animation loop
            if not self.timer.isActive():
                self.timer.start(16)

            for btn in self.keys_map[sc]:
                # Disambiguate left/right modifier keys
                if is_right and btn.x() < mid_x:
                    continue
                if not is_right and (sc in [29, 56, 42]) and btn.x() > mid_x:
                    continue

                x_ratio = max(0.0, min(1.0, btn.x() / max(1.0, float(self.width()))))
                btn_color = get_theme_color(self.color_mode, x_ratio, self.global_hue_offset)
                btn.set_active(True, btn_color)
                
                now = time.time()
                if self.ripple_effect and (now - self.key_last_wave_time.get(sc, 0) > 0.2):
                    self.key_last_wave_time[sc] = now
                    center = QPointF(btn.x() + btn.width() / 2.0, btn.y() + btn.height() / 2.0)
                    self.ripples.append(RippleEffect(
                        center=center,
                        w=btn.width(),
                        h=btn.height(),
                        label=btn.display_name,
                        font=btn.font,
                        color=btn_color,
                        opacity=self.opacity
                    ))

    def handle_release(self, sc, name):
        if sc in self.keys_map:
            for btn in self.keys_map[sc]:
                btn.set_active(False)

    def update_anim(self):
        # Update animated themes (RGB / Cyberpunk / Tokyo etc.)
        self.global_hue_offset = (self.global_hue_offset + 0.008) % 1.0
        
        has_active_keys = False
        for btn in self.buttons:
            if btn.is_active:
                has_active_keys = True
                x_ratio = max(0.0, min(1.0, btn.x() / max(1.0, float(self.width()))))
                new_col = get_theme_color(self.color_mode, x_ratio, self.global_hue_offset)
                btn.active_color = new_col
                btn.update()

        # Update ripples
        if self.ripples:
            self.ripples = [r for r in self.ripples if r.update()]
            self.update()
        elif has_active_keys:
            self.update()
        elif self.is_in_setup:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Setup Mode Visual Guides
        if self.is_in_setup:
            painter.save()
            w, h = float(self.width()), float(self.height())
            
            # Clean Minimalist Setup HUD Border
            pen = QPen(QColor(140, 145, 160, 200), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 0, 0, 40))
            painter.drawRoundedRect(QRectF(1.0, 1.0, w - 2.0, h - 2.0), 8.0, 8.0)

            # Floating HUD Banner
            hud_w, hud_h = min(400.0, w - 20.0), 30.0
            hud_rect = QRectF((w - hud_w) / 2.0, 8.0, hud_w, hud_h)
            painter.setPen(QPen(QColor(60, 64, 75), 1.0))
            painter.setBrush(QColor(20, 22, 28, 230))
            painter.drawRoundedRect(hud_rect, 6.0, 6.0)

            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
            painter.setPen(QColor(230, 232, 240))
            mode_name = "Drag to move overlay" if self.setup_mode == 'all' else "Drag keys to rearrange"
            msg = f"{mode_name}  |  Press ENTER to save & lock"
            painter.drawText(hud_rect, Qt.AlignmentFlag.AlignCenter, msg)
            painter.restore()

        # Render Active Ripples
        for rip in self.ripples:
            painter.save()
            alpha = int(rip.life * 210 * self.opacity)
            color = QColor(rip.color.red(), rip.color.green(), rip.color.blue(), alpha)
            
            rw = rip.orig_w * rip.scale
            rh = rip.orig_h * rip.scale
            rrect = QRectF(rip.center.x() - rw / 2.0, rip.center.y() - rh / 2.0, rw, rh)
            
            # Radiant wave ring
            painter.setPen(QPen(color, 2.0 * self.scale))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), int(alpha * 0.12)))
            painter.drawRoundedRect(rrect, 6.0 * self.scale, 6.0 * self.scale)
            
            # Scaling label
            painter.setFont(rip.font)
            painter.setPen(color)
            painter.drawText(rrect, Qt.AlignmentFlag.AlignCenter, rip.label)
            painter.restore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.setup_mode == 'all':
            self.dragPos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton and self.is_in_setup:
            self.is_in_setup = False
            self.is_locked = True
            self.save_config()
            self.apply_behavior()
            debug_print("Locked & Click-through enabled via right click.")

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.setup_mode == 'all':
            self.move(event.globalPosition().toPoint() - self.dragPos)
            event.accept()


def terminal_record_mode(mode, config_file, key_mapping):
    print(f"\n>>> RECORDING for '{mode}' Mode... (Press ESC to stop) <<<")
    recorded_keys = set()
    def on_press(e):
        if e.name == 'esc':
            return False
        for key_name, codes in key_mapping.items():
            codes_list = codes if isinstance(codes, list) else [codes]
            if e.scan_code in codes_list:
                if key_name not in recorded_keys:
                    recorded_keys.add(key_name)
                    print(f" Registered: {key_name}")
                break
        return True
    keyboard.on_press(on_press)
    keyboard.wait('esc')
    
    config = {"pos": [100, 100], "recorded_keys": {}}
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception:
            pass
    
    if "recorded_keys" not in config:
        config["recorded_keys"] = {}
    config["recorded_keys"][mode] = list(recorded_keys)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print("\n>>> RECORDING FINISHED <<<")
    os._exit(0)


def exception_hook(exctype, value, tb):
    if exctype == KeyboardInterrupt:
        print("\nkeyviz terminated.")
        os._exit(0)
    else:
        sys.__excepthook__(exctype, value, tb)


def main():
    global DEBUG_MODE
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.excepthook = exception_hook
    try:
        config_file = os.path.join(CONFIG_DIR, 'config.json')
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except Exception as e:
                print(f"[ERROR] Failed to read config: {e}")

        parser = argparse.ArgumentParser(description="KeyViz - Premium Keystroke Visualizer")
        parser.add_argument("-m", "--mode", type=str, choices=["normal", "gaming", "custom"], default=None)
        parser.add_argument("-k", "--keys", type=str, nargs='?', const='RECORD', default=None)
        parser.add_argument("-c", "--color", type=str, default=None)
        parser.add_argument("-p", "--pos", type=str, nargs='?', const='all', default=None,
                            help="Position setup: 'all' to move overlay, 'custom' to move keys")
        parser.add_argument("--no-mouse", action="store_true", default=None, help="Force unlock click-through")
        parser.add_argument("--scale", type=float, default=None, help="Scale overlay factor (0.5 to 1.5)")
        parser.add_argument("--compact", action="store_true", default=None, help="Enable compact window mode")
        parser.add_argument("--debug", action="store_true", help="Enable debug messages")
        parser.add_argument("-v", "--version", action="version", version="KeyViz 0.2.1")
        args = parser.parse_args()

        DEBUG_MODE = args.debug
        debug_print("Initialization...")

        # If no core functional CLI arguments provided, launch the modern GUI Control Panel
        has_cli_args = any([
            args.mode is not None,
            args.keys is not None,
            args.color is not None,
            args.pos is not None,
            args.no_mouse is not None,
            args.scale is not None,
            args.compact is not None
        ])

        if not has_cli_args:
            debug_print("No functional CLI arguments. Launching GUI Control Panel.")
            from keyviz.menu import SettingsMenu
            app = QApplication(sys.argv)
            app_font = QFont("Segoe UI Variable Text", 9)
            if not QFontInfo(app_font).exactMatch():
                app_font = QFont("Segoe UI", 9)
            app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
            app.setFont(app_font)
            menu = SettingsMenu()
            menu.show()
            sys.exit(app.exec())

        res_mode = args.mode if args.mode else config.get("mode", "normal")
        res_color = args.color if args.color else config.get("color", "default")
        res_no_mouse = args.no_mouse if args.no_mouse is not None else config.get("no_mouse", False)
        res_scale = args.scale if args.scale is not None else config.get("scale", 1.0)
        res_compact = args.compact if args.compact is not None else config.get("compact_mode", False)

        if args.keys == 'reset':
            for f in [config_file, os.path.join(CONFIG_DIR, 'recorded_keys.json'), os.path.join(CONFIG_DIR, 'settings.json')]:
                if os.path.exists(f):
                    os.remove(f)
            print("Settings reset successfully.")
            return

        if args.keys == 'RECORD':
            with open(os.path.join(BASE_DIR, 'key.json'), 'r', encoding='utf-8') as f:
                mapping = json.load(f)
            terminal_record_mode(res_mode, config_file, mapping)

        app = QApplication(sys.argv)
        
        setup_mode = None
        if args.pos in ['all', 'custom', 'SETUP']:
            setup_mode = 'custom' if args.pos == 'custom' else 'all'
            
        force_pos = args.pos if (args.pos and ',' in args.pos) else None
        
        ex = KeyboardOverlay(
            mode=res_mode,
            custom_keys=args.keys,
            color_mode=res_color,
            setup_mode=setup_mode,
            force_pos=force_pos,
            force_no_mouse=res_no_mouse,
            scale=res_scale,
            compact_mode=res_compact
        )
        
        def cleanup():
            ex.save_config()
            keyboard.unhook_all()
        app.aboutToQuit.connect(cleanup)
        
        sys.exit(app.exec())
    except Exception:
        log_file = os.path.join(CONFIG_DIR, 'crash.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- CRASH AT {time.ctime()} ---\n")
            traceback.print_exc(file=f)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
