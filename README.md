<p align="center">
  <img src="banner.png" alt="Keyviz Banner">
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version"></a>
  <a href="https://www.qt.io/"><img src="https://img.shields.io/badge/UI-PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="UI Framework"></a>
  <img src="https://img.shields.io/badge/License-MIT-F5A623?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/github/repo-size/keep-xylent/keyviz?style=for-the-badge" alt="Size">
</p>

<img src="divider.svg" width="100%" height="3">

> **KeyViz** is a high-performance, real-time keyboard overlay application built with Python and PyQt6. Designed specifically for streamers, content creators, gamers, and presenters, it displays keystrokes on-screen in an interactive overlay featuring clean visual ripple effects and dynamic scaling.

<img src="divider.svg" width="100%" height="3">

## <img src="https://img.shields.io/badge/-%20-f43f5e?style=flat-square" height="18" valign="middle"> Key Features

- <img src="https://img.shields.io/badge/-%20-fbbf24?style=flat-square" height="12" valign="middle"> **Real-Time Visualization**
  Instantly displays keyboard inputs on-screen with zero latency.
- <img src="https://img.shields.io/badge/-%20-38bdf8?style=flat-square" height="12" valign="middle"> **Elegant Ripple Effects**
  Clean wave animations radiating outward from pressed keys, accompanied by dynamic font scaling for maximum clarity.
- <img src="https://img.shields.io/badge/-%20-a855f7?style=flat-square" height="12" valign="middle"> **Adaptive Layout Modes**
  * `normal`: Displays the full standard QWERTY keyboard layout.
  * `gaming`: Displays a minimized layout containing only gaming-essential keys (WASD, Space, Shift, etc.).
  * `custom`: Displays a customizable selection of keys tailored to your exact workflow.
> [!NOTE]
> **Current Layout Support**
>
> At the moment, the default `layout.json` configuration is designed specifically for **75% exploded knob keyboards**.  
> Other layouts may still function partially, but key positioning and spacing might not align correctly without manual customization.
>
> Future updates may include additional presets for TKL, 65%, 60%, and full-size layouts.
- <img src="https://img.shields.io/badge/-%20-ec4899?style=flat-square" height="12" valign="middle"> **Vibrant Color Themes**
  Supports dynamic rainbow colors (`rgb`), solid white, the default system theme, or any custom HEX color code (e.g., `#FF5733`).
- <img src="https://img.shields.io/badge/-%20-06b6d4?style=flat-square" height="12" valign="middle"> **Click-Through Mode**
  Locks the overlay in place so that mouse clicks pass right through, letting you play games or work in underlying windows uninterrupted.
- <img src="https://img.shields.io/badge/-%20-64748b?style=flat-square" height="12" valign="middle"> **Interactive GUI Positioning**
  * Position the entire overlay window anywhere on your screen via interactive drag-and-drop.
  * Rearrange individual keys visually directly from the overlay window.
- <img src="https://img.shields.io/badge/-%20-6366f1?style=flat-square" height="12" valign="middle"> **Scan-Code Recorder**
  Includes a built-in interactive utility (`manual_mapping.py`) to easily record and map non-standard keys.

<img src="divider.svg" width="100%" height="3">

## <img src="https://img.shields.io/badge/-%20-ef4444?style=flat-square" height="18" valign="middle"> Requirements & Prerequisite

> [!WARNING]
> **Administrator Privileges Required**
>
> On Windows, the system-level `keyboard` library requires Administrator privileges to hook global keystrokes. Ensure you run your terminal or Command Prompt as **Administrator** when running KeyViz.

* **Python 3.8+**
* **Windows OS**

---

### 🛡️ Security, Privacy & Consent Model

KeyViz intercepts keyboard inputs globally to display active keys on the overlay dashboard. Because global key logging can represent a security risk, KeyViz adopts a strict local-only safety design:

1. **User Permission Prompt**: On first launch (either via GUI dialog or terminal prompt), KeyViz requires you to explicitly grant consent to intercept keys. Your decision is stored in `config.json` as `"consent_granted": true`.
2. **Local and Offline Execution**: KeyViz performs all interception and rendering logic locally on your machine.
3. **No Network Access**: The application does not communicate with external servers, log keys to remote systems, or save key histories.


<img src="divider.svg" width="100%" height="3">

## <img src="https://img.shields.io/badge/-%20-10b981?style=flat-square" height="18" valign="middle"> Installation & Setup

Follow these steps to set up KeyViz on your machine:

### 1. Install Dependencies
Open your terminal or Command Prompt as **Administrator**, navigate to this project directory, and run:

```bash
pip install -r requirements.txt
```

Or install the required packages manually:
```bash
pip install PyQt6 keyboard
```

### 2. Register Global Command Link (CLI Alias)
Choose one of the following methods to register the `keyviz` command so you can call it from any folder:

* **Recommended for Users (Standard Build)**:
  Installs the application permanently into your Python site-packages. Once complete, you can safely move or delete the source folder.
  ```bash
  pip install .
  ```
* **Recommended for Developers (Editable Build)**:
  Links the command directly back to this development folder. Best if you plan to tweak configurations or modify the source code.
  ```bash
  pip install -e .
  ```
  > [!TIP]
  > If you move this project folder to another path, you must run the editable installation command again to update the links.

<img src="divider.svg" width="100%" height="3">

## <img src="https://img.shields.io/badge/-%20-3b82f6?style=flat-square" height="18" valign="middle"> Usage Guide

KeyViz can be launched globally, locally, or using the Windows batch helper.

### Execution Methods
- **Global Command** (if registered via pip):
  ```bash
  keyviz -m normal
  ```
- **Local Python Script**:
  ```bash
  python main.py -m normal
  ```
- **Windows Batch Shortcut**:
  ```bash
  .\keyviz.bat -m normal
  ```

---

### <img src="https://img.shields.io/badge/-%20-8b5cf6?style=flat-square" height="16" valign="middle"> Command Line Interface (CLI) Flags

Tailor the overlay behavior and styling using the following parameters:

| Flag | Parameter | Description |
| :--- | :--- | :--- |
| **`-m`, `--mode`** | `normal`, `gaming`, `custom` | Choose the layout profile to display. |
| **`-c`, `--color`** | `default`, `rgb`, `white`, `#HEX` | Select the color scheme for ripple effects and key borders. |
| **`-k`, `--keys`** | `RECORD`, `reset`, `"k,e,y,s"` | Set active keys: specify inline keys, trigger `RECORD` mode, or `reset` configurations. |
| **`-p`, `--pos`** | `all`, `custom`, `x,y` | Toggle setup: reposition overlay (`all`), reposition individual keys (`custom`), or force `x,y` coordinates. |
| **`--no-mouse`** | *(none)* | Lock the overlay window and allow mouse click-through behavior. |
| **`--debug`** | *(none)* | Enable detailed debug log output in the console. |
| **`-v`, `--version`**| *(none)* | Display the currently installed KeyViz version. |

### <img src="https://img.shields.io/badge/-%20-eab308?style=flat-square" height="16" valign="middle"> Examples of CLI Usage

* **Vibrant RGB Gaming Overlay**:
  ```bash
  keyviz -m gaming -c rgb
  ```
* **Click-Through Standard Overlay**:
  ```bash
  keyviz -m normal --no-mouse
  ```
* **Record Custom Gaming Layout**:
  ```bash
  keyviz -m gaming -k RECORD
  ```
  *(Press keys sequentially in the terminal, then hold `ESC` to save and exit)*
* **Reset All Configurations & Positioning**:
  ```bash
  keyviz -k reset
  ```

<img src="divider.svg" width="100%" height="3">

## <img src="https://img.shields.io/badge/-%20-d946ef?style=flat-square" height="18" valign="middle"> Interactive GUI Positioning

Fine-tune your layout placement using interactive drag-and-drop modes:

### 1. Repositioning the Overlay Window
```bash
keyviz -p all
```
* **Left-Click & Drag** the window to move it anywhere on your screen.
* Press **`ENTER`** to save the position and exit.
* **Right-Click** the overlay to lock it in place and activate click-through.

### 2. Custom Key Layout Adjustment
```bash
keyviz -m gaming -p custom
```
* **Left-Click & Drag** individual keys to rearrange their placement on the overlay.
* Press **`ENTER`** to save the customized layout and exit.

<img src="divider.svg" width="100%" height="3">

## <img src="https://img.shields.io/badge/-%20-f97316?style=flat-square" height="18" valign="middle"> Custom Layout Mapping

For non-standard or mechanical keyboards, run the scan-code utility to map raw hardware inputs:

1. Launch the utility:
   ```bash
   python keyviz/manual_mapping.py
   ```
2. Follow the terminal prompts by pressing the requested keys.
3. Hold **`ESC`** to save your layout configuration.
4. The output is stored in `mapping_layout.txt`. Use this data to update [layout.json](keyviz/layout.json) or [key.json](keyviz/key.json).

<img src="divider.svg" width="100%" height="3">

## <img src="https://img.shields.io/badge/-%20-14b8a6?style=flat-square" height="18" valign="middle"> Configuration Files Architecture & System Architecture

### Configuration Directories
- **Development / Local Execution**: Configuration is loaded directly from the project root (`config.json`).
- **Production Package Execution**: If installed globally via `pip`, configuration is managed in `~/.keyviz/config.json` inside your user profile folder to avoid system directories access issues.

### Decoupled System Architecture
KeyViz is refactored into decoupled, testable modules. You can inspect detailed specifications in the [Architecture Documentation](keyviz/architecture.md):
- **`config_manager.py`**: Validates JSON formatting and data types (schema validation) before loading settings. If corruption is detected, it automatically loads fallback default variables and saves a backup `config.json.bak`.
- **`input_handler.py`**: Intercepts keyboard events and translates them to PyQt signals.
- **`ui.py`**: Standardizes interactive components like buttons, transparent overlays, and consent interfaces.

### Configuration Schema Definition
The user configuration (`config.json`) implements the following validation schema:
- `version` (int): Config versioning schema.
- `pos` ([int, int]): XY coordinate values for overlay window placement.
- `recorded_keys` (dict): Dict of mode names mapped to list of active keys.
- `mode` (string): Current layout selection (`normal`, `gaming`, `custom`).
- `color` (string): Active RGB border styles.
- `custom_pos` (dict): Mode-based nested coordinate sets for individual key custom locations.
- `no_mouse` (bool): Click-through state indicator.
- `consent_granted` (bool): Security consent check status.

---

<p align="center">
  <sub>Developed by Xylent &bull; Licensed under the MIT License</sub>
</p>
