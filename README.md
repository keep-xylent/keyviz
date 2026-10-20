<p align="center">
  <img src="https://cdn.discordapp.com/attachments/1200257185364586558/1507014607636533331/banner.png?ex=6a105c39&is=6a0f0ab9&hm=5d4353c2ac98188ea59c0367e5850e4abfe4f1d86ffc03e3333f475c06b4b3b1&" alt="KeyViz Banner" width="100%">
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python Version"></a>
  <a href="https://www.qt.io/"><img src="https://img.shields.io/badge/UI-PyQt6-41CD52?style=flat-square&logo=qt&logoColor=white" alt="UI Framework"></a>
  <img src="https://img.shields.io/badge/Platform-Windows-0078D4?style=flat-square&logo=windows&logoColor=white" alt="Platform Compatibility">
  <img src="https://img.shields.io/badge/License-MIT-F5A623?style=flat-square" alt="License">
</p>

<img src="divider.svg" width="100%" height="3">

KeyViz is a real-time keyboard overlay application built with Python and PyQt6. Designed for streamers, content creators, gamers, or anyone who wants to display their keystrokes on-screen in an interactive way with clean visual ripple effects.

<img src="divider.svg" width="100%" height="3">

## Key Features

* **Real-Time Keyboard Overlay** <img src="https://img.shields.io/badge/-Core-333333?style=flat-square" valign="middle">
  Instantly displays keystrokes on-screen with zero latency and transparent wireframe keycaps that never block screen content.

* **GUI Control Panel** <img src="https://img.shields.io/badge/-GUI-2563eb?style=flat-square" valign="middle">
  Modern, compact desktop control panel with dynamic content-fitting window size, Segoe UI typography, and live interactive preview.

* **Ripple & Tactile Physics** <img src="https://img.shields.io/badge/-Visual-4433ff?style=flat-square" valign="middle">
  Smooth expanding ripple waves radiating from pressed keys with responsive key depression physics.

* **Layout Modes & Profiles** <img src="https://img.shields.io/badge/-UI-ff3366?style=flat-square" valign="middle">
  * `normal`: Full keyboard layout (standard 75% exploded + knob).
  * `gaming`: Essential gaming keys (WASD, Space, Shift, Ctrl, Numbers).
  * `custom`: Multi-preset manager with direct in-app key recording and JSON import/export.

* **Curated Subdued Color Schemes** <img src="https://img.shields.io/badge/-Visual-4433ff?style=flat-square" valign="middle">
  Elegant non-neon palette (`white`, `slate`, `blue`, `green`, `amber`, `rose`, `spectrum`) plus custom Hex picker.

* **Performance & Zero-CSS Churn** <img src="https://img.shields.io/badge/-Performance-00aa55?style=flat-square" valign="middle">
  High-performance vector `QPainter` drawing with adaptive animation loop that idles at 0% CPU when no keys are pressed.

* **Click-Through Mode** <img src="https://img.shields.io/badge/-Utility-ffa500?style=flat-square" valign="middle">
  Locks the overlay so mouse clicks pass directly into underlying games or apps.

<img src="divider.svg" width="100%" height="3">

## Requirements

* **Python 3.8+** <img src="https://img.shields.io/badge/-Required-blue?style=flat-square" valign="middle">
* **Administrator Privileges** <img src="https://img.shields.io/badge/-Required-red?style=flat-square" valign="middle">
  The `keyboard` library requires administrator privileges on Windows to hook global keystrokes.

<img src="divider.svg" width="100%" height="3">

## Installation

Follow these steps to set up KeyViz on your system:

### 1. Installing Dependencies
Open Terminal or Command Prompt (as Administrator) in this project directory, then run:

```bash
pip install -r requirements.txt
```

Or install dependencies manually:

```bash
pip install PyQt6 keyboard
```

### 2. Registering keyviz Command (Global Alias)
To call the application directly using the `keyviz` command from any terminal directory, choose one of the following installation methods:

* **Standard Installation** <img src="https://img.shields.io/badge/-Recommended-green?style=flat-square" valign="middle">
  Installs the application permanently to your Python site-packages. Once complete, you can safely move or delete the source code folder.
  ```bash
  pip install .
  ```

* **Editable Installation** <img src="https://img.shields.io/badge/-Developer-orange?style=flat-square" valign="middle">
  Links the command directly to this project folder. Best if you plan to modify the source code or configurations locally.
  ```bash
  pip install -e .
  ```
  *Note: If you move the project folder to another path, you must run the editable installation command again in the new directory.*

<img src="divider.svg" width="100%" height="3">

## Usage Guide

The application can be executed directly via Python, using the batch file, or as a global package command.

### Execution Methods

1. **Using the Global Command** <img src="https://img.shields.io/badge/-Global-blue?style=flat-square" valign="middle">
   ```bash
   keyviz -m normal
   ```
2. **Running Python Directly** <img src="https://img.shields.io/badge/-Local-gray?style=flat-square" valign="middle">
   ```bash
   python main.py -m normal
   ```
3. **Using the Batch File** <img src="https://img.shields.io/badge/-Windows-0078d4?style=flat-square" valign="middle">
   ```bash
   .\keyviz.bat -m normal
   ```

<img src="divider.svg" width="100%" height="3">

## Command Line Arguments (CLI Flags)

The application supports the following parameters for customization:

| Flag | Parameter | Description |
| :--- | :--- | :--- |
| `-m`, `--mode` | `normal`, `gaming`, `custom` | Choose the layout profile to display. |
| `-c`, `--color` | `white`, `slate`, `blue`, `green`, `amber`, `rose`, `spectrum`, `#HEX` | Select the keycap highlight color. |
| `--scale` | `0.5` to `1.5` | Adjust overlay scaling factor (e.g. `0.8`, `1.0`, `1.2`). |
| `--compact` | (no argument) | Auto-crop empty canvas space tightly around active keys (ideal for Gaming WASD mode). |
| `-k`, `--keys` | `RECORD`, `reset`, `"k,e,y,s"` | Set active keys (comma-separated list), record new keys, or reset configurations. |
| `-p`, `--pos` | `all`, `custom`, `x,y` | Enter setup mode for overlay positioning (`all`), key positioning (`custom`), or force specific coordinates. |
| `--no-mouse` | (no argument) | Lock overlay click-through. |
| `--debug` | (no argument) | Enable debug log output in the console. |
| `-v`, `--version` | (no argument) | Display the installed KeyViz version. |

### Usage Examples

* **Running Gaming Mode with Clean White Wireframe and Compact Window**:
  ```bash
  keyviz -m gaming -c white --compact --scale 1.1
  ```
* **Running Normal Mode with Click-Through Enabled**:
  ```bash
  keyviz -m normal --no-mouse
  ```
* **Recording Custom Keys for Gaming Mode**:
  ```bash
  keyviz -m gaming -k RECORD
  ```
  *Press keys sequentially in the terminal, then press and hold `ESC` to save.*
  
* **Resetting Configuration and Window Position**:
  ```bash
  keyviz -k reset
  ```

<img src="divider.svg" width="100%" height="3">

## Interactive Setup

Adjust the overlay window position and button layouts visually:

1. **Adjusting Overlay Window Position**:
   ```bash
   keyviz -p all
   ```
   * Drag the overlay window using left-click to your desired location.
   * Press **ENTER** on your keyboard to confirm and exit, or **Right-Click** your mouse to lock the position and enable click-through.

2. **Adjusting Individual Key Positions**:
   ```bash
   keyviz -m gaming -p custom
   ```
   * Drag individual keys using left-click to rearrange them.
   * Press **ENTER** to save the new layout and exit.

<img src="divider.svg" width="100%" height="3">

## Custom Layout Mapping (manual_mapping.py)

Run the built-in scan-code recorder to map non-standard keyboards or capture special keys:

1. Run the mapping utility:
   ```bash
   python manual_mapping.py
   ```
2. Press keys sequentially on your keyboard following the terminal prompts.
3. Press and hold `ESC` to exit.
4. Results will be saved to `mapping_layout.txt`. Use this data to update `layout.json` or `key.json`.

<img src="divider.svg" width="100%" height="3">

## Configuration File Structure

The application reads and saves settings to the following files:
* **`layout.json`** <img src="https://img.shields.io/badge/-Static-blue?style=flat-square" valign="middle">
  Stores button labels, initial coordinates, and dimensions.
* **`key.json`** <img src="https://img.shields.io/badge/-Static-blue?style=flat-square" valign="middle">
  Stores operating system scan-code mappings.
* **`config.json`** <img src="https://img.shields.io/badge/-User--Config-green?style=flat-square" valign="middle">
  Stores latest overlay position, recorded keys, color preferences, and customized button layouts.

<img src="divider.svg" width="100%" height="3">

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
