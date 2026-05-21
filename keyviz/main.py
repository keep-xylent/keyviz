import sys
import argparse
import signal
import os
import traceback
import time
import keyboard
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Import decoupled core packages
from keyviz.config_manager import (
    CONFIG_DIR,
    load_config,
    save_config,
    load_packaged_json
)
from keyviz.input_handler import (
    KeyboardSignaller,
    InputHandler,
    verify_cli_consent
)
from keyviz.ui import (
    ConsentDialog,
    KeyboardOverlay
)

DEBUG_MODE = False

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)
        sys.stdout.flush()

def terminal_record_mode(mode, config_data, key_mapping):
    """Console key recorder utility."""
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
    
    if "recorded_keys" not in config_data:
        config_data["recorded_keys"] = {}
    config_data["recorded_keys"][mode] = list(recorded_keys)
    save_config(config_data)
    
    print("\n>>> RECORDING FINISHED. Configuration updated. <<<")
    os._exit(0)

def exception_hook(exctype, value, tb):
    if exctype == KeyboardInterrupt:
        print("\nKeyViz terminated.")
        os._exit(0)
    else:
        sys.__excepthook__(exctype, value, tb)

def main():
    global DEBUG_MODE
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.excepthook = exception_hook
    
    try:
        # Load user configuration
        config = load_config()

        # Initialize argument parser with rich documentation help and usage descriptions
        parser = argparse.ArgumentParser(
            description="KeyViz - Live Aesthetic Keyboard Overlay Visualizer\n"
                        "Intercepts keyboard events locally to render keys onto an overlay screen widget.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples of Usage:
  1. Standard launch:
     python main.py
     
  2. Setup positions (reposition the complete overlay framework):
     python main.py -p all
     
  3. Setup keys (customize single key coordinates inside overlay layout):
     python main.py -p custom
     
  4. Launch with explicit layout filter:
     python main.py -m gaming
     
  5. Record active keys from command line:
     python main.py -m gaming -k
     
  6. Reset saved coordinates and configs to clean installation status:
     python main.py -k reset
            """
        )
        
        parser.add_argument("-m", "--mode", type=str, choices=["normal", "gaming", "custom"], default=None,
                            help="Visual mode filter determining which keys show up on screen.")
        parser.add_argument("-k", "--keys", type=str, nargs='?', const='RECORD', default=None,
                            help="Record keys interactively ('RECORD' or omit value), 'reset' to clean configurations, "
                                 "or pass comma-separated scan codes (e.g. 'w,a,s,d').")
        parser.add_argument("-c", "--color", type=str, default=None,
                            help="RGB styles for buttons: 'rgb' (rainbow), 'white', or hexadecimal color code (e.g. '#a855f7').")
        parser.add_argument("-p", "--pos", type=str, nargs='?', const='all', default=None,
                            help="Calibration offset configurations: 'all' (overlay window dragging), 'custom' (key buttons dragging).")
        parser.add_argument("--no-mouse", action="store_true", default=None,
                            help="Applies WA_TransparentForMouseEvents to lock clicks from interacting with the overlay frame.")
        parser.add_argument("--debug", action="store_true",
                            help="Enables diagnostic messages.")
        parser.add_argument("-v", "--version", action="version", version="KeyViz 0.1.1",
                            help="Prints version number.")
                            
        args = parser.parse_args()

        DEBUG_MODE = args.debug
        debug_print("Initializing modules...")

        res_mode = args.mode if args.mode else config.get("mode", "normal")
        res_color = args.color if args.color else config.get("color", "default")
        res_no_mouse = args.no_mouse if args.no_mouse is not None else config.get("no_mouse", False)
        
        debug_print(f"Loaded config values - Mode: {res_mode}, Color: {res_color}, NoMouse: {res_no_mouse}")

        if args.keys == 'reset':
            config_file = os.path.join(CONFIG_DIR, 'config.json')
            for f in [config_file, os.path.join(CONFIG_DIR, 'recorded_keys.json'), os.path.join(CONFIG_DIR, 'settings.json')]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception as e:
                        debug_print(f"Failed to delete {f}: {e}")
            print("Settings and positional configurations reset successfully.")
            return

        if args.keys == 'RECORD':
            # Check consent inside terminal before starting keyboard hook
            verify_cli_consent(config, save_config)
            mapping = load_packaged_json('key.json')
            terminal_record_mode(res_mode, config, mapping)

        # Standard launch launches the PyQt6 QApplication
        app = QApplication(sys.argv)
        
        # Check security consent inside GUI prior to establishing global driver hooks
        if not config.get("consent_granted", False):
            dialog = ConsentDialog()
            if dialog.exec() == ConsentDialog.DialogCode.Accepted:
                config["consent_granted"] = True
                save_config(config)
            else:
                print("[INFO] Security permission rejected. KeyViz will exit.")
                sys.exit(0)

        setup_mode = None
        if args.pos in ['all', 'custom', 'SETUP']:
            setup_mode = 'custom' if args.pos == 'custom' else 'all'
            
        force_pos = args.pos if (args.pos and ',' in args.pos) else None
        
        # Load asset maps
        key_mapping = load_packaged_json('key.json')
        
        # Instantiate decoupled signals & keyboard interface components
        signaller = KeyboardSignaller()
        input_handler = InputHandler(key_mapping, signaller)

        import keyviz.config_manager as cm
        ex = KeyboardOverlay(
            config_manager=cm,
            input_handler=input_handler,
            mode=res_mode,
            custom_keys=args.keys,
            color_mode=res_color,
            setup_mode=setup_mode,
            force_pos=force_pos,
            force_no_mouse=res_no_mouse
        )
        
        def cleanup():
            ex.save_overlay_config()
            input_handler.stop_hook()
            
        app.aboutToQuit.connect(cleanup)
        
        debug_print("Starting main event loop...")
        sys.exit(app.exec())
        
    except Exception:
        log_file = os.path.join(CONFIG_DIR, 'crash.log')
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- CRASH AT {time.ctime()} ---\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
