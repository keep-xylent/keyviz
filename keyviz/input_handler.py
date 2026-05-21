import sys
import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

class KeyboardSignaller(QObject):
    press_sig = pyqtSignal(int, str)
    release_sig = pyqtSignal(int, str)

class InputHandler:
    """Encapsulates the global keyboard intercept hook and translates scan codes via Qt Signals."""
    
    def __init__(self, key_mapping: dict, signaller: KeyboardSignaller):
        self.key_mapping = key_mapping
        self.signaller = signaller
        self.is_hooked = False
        
    def start_hook(self):
        """Attaches global keyboard listener callback."""
        if self.is_hooked:
            return
        try:
            keyboard.hook(self.on_key_event)
            self.is_hooked = True
        except Exception as e:
            raise RuntimeError(f"Failed to establish keyboard hook driver: {e}")

    def stop_hook(self):
        """Detaches all keyboard hooks."""
        if self.is_hooked:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
            self.is_hooked = False

    def on_key_event(self, e):
        """Callback from keyboard library receiving event e."""
        sc = e.scan_code
        # Propagate through signaller signals safely
        if e.event_type == 'down':
            self.signaller.press_sig.emit(sc, str(e.name))
        else:
            self.signaller.release_sig.emit(sc, str(e.name))

def verify_cli_consent(config_data: dict, save_callback) -> bool:
    """Prompts user inside standard input stream to grant permissions for global keyboard capture."""
    if config_data.get("consent_granted", False):
        return True

    print("\n" + "=" * 60)
    print("                  SECURITY & PRIVACY NOTICE")
    print("=" * 60)
    print("KeyViz requires monitoring your keyboard strokes globally so it")
    print("can highlight pressed keys on the visual screen overlay.")
    print("\n- ALL key interception happens LOCALLY on your computer.")
    print("- NO keystrokes are stored, written to disk, or sent online.")
    print("- Works entirely offline.")
    print("=" * 60)
    
    try:
        ans = input("Do you grant permission to intercept keyboard inputs? [y/N]: ").strip().lower()
        if ans in ["y", "yes"]:
            config_data["consent_granted"] = True
            save_callback(config_data)
            print("[SUCCESS] Consent recorded. Starting KeyViz.")
            return True
        else:
            print("[INFO] Consent was denied. KeyViz cannot operate without keyboard permissions. Exiting.")
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n[INFO] Operation cancelled. Exiting.")
        sys.exit(0)
