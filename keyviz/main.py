import sys
import json
import random
import colorsys
import keyboard
import argparse
import traceback
import time
import signal
import os
from PyQt6.QtWidgets import QApplication, QWidget, QFrame, QLabel
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QFontDatabase

# Base directory for static files (inside keyviz package directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Determine CONFIG_DIR for dynamic config files (config.json, crash.log, etc.)
if "site-packages" in BASE_DIR or "dist-packages" in BASE_DIR:
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".keyviz")
    os.makedirs(CONFIG_DIR, exist_ok=True)
else:
    # Use parent directory of keyviz/ (which is the root directory of the project)
    CONFIG_DIR = os.path.dirname(BASE_DIR)

# Global debug flag
DEBUG_MODE = False

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)
        sys.stdout.flush()

class KeyboardSignaller(QObject):
    press_sig = pyqtSignal(int, str)
    release_sig = pyqtSignal(int, str)

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
    def __init__(self, mode="normal", custom_keys=None, color_mode="default", setup_mode=None, force_pos=None, force_no_mouse=False):
        super().__init__()
        self.mode = mode
        self.custom_keys = custom_keys
        self.color_mode = color_mode
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
        
        if self.is_in_setup:
            self.is_locked = False
        else:
            self.is_locked = force_no_mouse

        self.initUI()
        self.load_config()
        
        if force_pos:
            try:
                x, y = map(int, force_pos.split(','))
                self.move(x, y)
                debug_print(f"Position override: {x},{y}")
            except: pass

        self.apply_behavior()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_anim)
        self.timer.start(16)

        self.signal_timer = QTimer()
        self.signal_timer.timeout.connect(lambda: None)
        self.signal_timer.start(100)

        self.signaller.press_sig.connect(self.handle_press)
        self.signaller.release_sig.connect(self.handle_release)
        
        QTimer.singleShot(500, self.start_keyboard_hook)

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
            btn.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self.is_locked and not self.is_in_setup)
            
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
            migration_data = {"pos": [100, 100], "recorded_keys": {}, "mode": "normal", "color": "default", "no_mouse": False}
            settings_path = os.path.join(CONFIG_DIR, 'settings.json')
            recorded_path = os.path.join(CONFIG_DIR, 'recorded_keys.json')
            
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, 'r') as f: migration_data["pos"] = json.load(f).get("pos", [100, 100])
                except: pass
            if os.path.exists(recorded_path):
                try:
                    with open(recorded_path, 'r') as f: migration_data["recorded_keys"] = json.load(f)
                except: pass
            config_data = migration_data
            self.save_config(migration_data)
        else:
            try:
                with open(self.main_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except Exception as e:
                debug_print(f"Failed to load config: {e}")

        pos = config_data.get('pos')
        if pos: self.move(pos[0], pos[1])
        
        self.custom_pos = config_data.get('custom_pos', {})

        debug_print(f"Final Overlay Config - Mode: {self.mode}, Color: {self.color_mode}, Setup: {self.is_in_setup}, Locked: {self.is_locked}")

        if not self.custom_keys:
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
                        with open(self.main_config_file, 'r') as f: current_config = json.load(f)
                    except: pass
                
                current_config['pos'] = [self.x(), self.y()]
                current_config['mode'] = self.mode
                current_config['color'] = self.color_mode
                
                if not self.is_in_setup:
                    current_config['no_mouse'] = self.is_locked
                
                if 'recorded_keys' not in current_config: current_config['recorded_keys'] = {}
                if self.recorded_keys:
                    current_config['recorded_keys'][self.mode] = list(self.recorded_keys)
                
                current_config['custom_pos'] = self.custom_pos
                data_to_save = current_config
            else:
                data_to_save = data_override

            with open(self.main_config_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2)
            debug_print(f"Config saved.")
        except Exception as e:
            print(f"Failed to save config: {e}")

    def update_button_pos(self, sc_key, x, y):
        if self.mode not in self.custom_pos: self.custom_pos[self.mode] = {}
        self.custom_pos[self.mode][sc_key] = [x, y]

    def initUI(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(1200, 500)
        self.rebuild_ui()

    def rebuild_ui(self):
        for btn in self.buttons: btn.deleteLater()
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
            if target_keys and sc_key.lower() not in target_keys: continue

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
                    if code not in self.keys_map: self.keys_map[code] = []
                    self.keys_map[code].append(btn)

    def on_key_event(self, e):
        sc = e.scan_code
        if self.is_in_setup and e.name == 'enter' and e.event_type == 'down':
            self.save_config()
            debug_print("Position confirmed via ENTER. Exiting.")
            os._exit(0)

        if e.event_type == 'down':
            self.signaller.press_sig.emit(sc, e.name)
        else:
            self.signaller.release_sig.emit(sc, e.name)

    def handle_press(self, sc, name):
        if sc in self.keys_map:
            for btn in self.keys_map[sc]:
                if ("right" in name or "alt gr" in name) and btn.x() < 500: continue
                if "right" not in name and "alt gr" not in name and (sc in [29, 56, 42]) and btn.x() > 500: continue
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
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
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
            self.save_config()
            self.apply_behavior()
            debug_print("Locked & Click-through enabled.")

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.setup_mode == 'all':
            self.move(event.globalPosition().toPoint() - self.dragPos)

def terminal_record_mode(mode, config_file, key_mapping):
    print(f"\n>>> RECORDING for '{mode}' Mode... (Press ESC to stop) <<<")
    recorded_keys = set()
    def on_press(e):
        if e.name == 'esc': return False
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
            with open(config_file, 'r') as f: config = json.load(f)
        except: pass
    
    if "recorded_keys" not in config: config["recorded_keys"] = {}
    config["recorded_keys"][mode] = list(recorded_keys)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
    print("\n>>> RECORDING FINISHED <<<")
    os._exit(0)

def exception_hook(exctype, value, tb):
    if exctype == KeyboardInterrupt:
        print("\nkeyviz terminated.")
        os._exit(0)
    else: sys.__excepthook__(exctype, value, tb)

def main():
    global DEBUG_MODE
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.excepthook = exception_hook
    try:
        debug_print(f"System ARGV: {sys.argv}")
        config_file = os.path.join(CONFIG_DIR, 'config.json')
        config = {}
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f: config = json.load(f)
                debug_print(f"Loaded config: {config}")
            except Exception as e:
                print(f"[ERROR] Failed to read config: {e}")

        parser = argparse.ArgumentParser(description="KeyViz")
        parser.add_argument("-m", "--mode", type=str, choices=["normal", "gaming", "custom"], default=None)
        parser.add_argument("-k", "--keys", type=str, nargs='?', const='RECORD', default=None)
        parser.add_argument("-c", "--color", type=str, default=None)
        parser.add_argument("-p", "--pos", type=str, nargs='?', const='all', default=None, help="Position setup: 'all' to move overlay, 'custom' to move keys")
        parser.add_argument("--no-mouse", action="store_true", default=None, help="Force unlock click-through")
        parser.add_argument("--debug", action="store_true", help="Enable debug messages")
        parser.add_argument("-v", "--version", action="version", version="KeyViz 0.1.0")
        args = parser.parse_args()

        DEBUG_MODE = args.debug
        debug_print("Initialization...")

        res_mode = args.mode if args.mode else config.get("mode", "normal")
        res_color = args.color if args.color else config.get("color", "default")
        res_no_mouse = args.no_mouse if args.no_mouse is not None else config.get("no_mouse", False)
        
        debug_print(f"Resolved - Mode: {res_mode}, Color: {res_color}, NoMouse: {res_no_mouse}")

        if args.keys == 'reset':
            for f in [config_file, os.path.join(CONFIG_DIR, 'recorded_keys.json'), os.path.join(CONFIG_DIR, 'settings.json')]:
                if os.path.exists(f): os.remove(f)
            print("Settings reset."); return

        args_mode = res_mode
        if args.keys == 'RECORD':
            with open(os.path.join(BASE_DIR, 'key.json'), 'r', encoding='utf-8') as f: mapping = json.load(f)
            terminal_record_mode(args_mode, config_file, mapping)

        app = QApplication(sys.argv)
        
        setup_mode = None
        if args.pos in ['all', 'custom', 'SETUP']:
            setup_mode = 'custom' if args.pos == 'custom' else 'all'
            
        force_pos = args.pos if (args.pos and ',' in args.pos) else None
        
        ex = KeyboardOverlay(mode=res_mode, custom_keys=args.keys, color_mode=res_color, 
                             setup_mode=setup_mode, force_pos=force_pos, force_no_mouse=res_no_mouse)
        
        def cleanup():
            ex.save_config()
            keyboard.unhook_all()
        app.aboutToQuit.connect(cleanup)
        
        debug_print("Entering event loop...")
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
