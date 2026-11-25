import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
import ctypes

# Try importing pyautogui, pygetwindow, pyperclip
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False

# PDF reading support
try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

USER_HOME = Path.home()
COMMON_SEARCH_DIRS = [
    USER_HOME / "Downloads",
    USER_HOME / "Documents",
    USER_HOME / "Desktop"
]

# ─── Low-Level Mouse & Keyboard Input (Pillar 2 Core) ──────────────────────────

def get_screen_resolution() -> dict:
    """Returns the primary monitor resolution in pixels"""
    try:
        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        return {"width": w, "height": h}
    except Exception as e:
        return {"width": 1920, "height": 1080, "error": str(e)}

def get_cursor_position() -> dict:
    """Returns current cursor X and Y coordinates"""
    try:
        if HAS_PYAUTOGUI:
            pos = pyautogui.position()
            return {"x": pos.x, "y": pos.y}
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return {"x": pt.x, "y": pt.y}
    except Exception as e:
        return {"x": 0, "y": 0, "error": str(e)}

def mouse_move(x: int, y: int, smooth: bool = True) -> dict:
    """Moves the mouse cursor to (x, y) coordinates"""
    try:
        screen = get_screen_resolution()
        target_x = max(0, min(screen["width"] - 1, int(x)))
        target_y = max(0, min(screen["height"] - 1, int(y)))

        if HAS_PYAUTOGUI:
            duration = 0.25 if smooth else 0.0
            pyautogui.moveTo(target_x, target_y, duration=duration)
        else:
            ctypes.windll.user32.SetCursorPos(target_x, target_y)

        return {"success": True, "message": f"Cursor moved to ({target_x}, {target_y}).", "x": target_x, "y": target_y}
    except Exception as e:
        return {"success": False, "message": f"Mouse move failed: {e}"}

def mouse_click(x: int = None, y: int = None, button: str = "left", clicks: int = 1) -> dict:
    """Clicks at the specified coordinates or current cursor position"""
    try:
        if x is not None and y is not None:
            mouse_move(x, y, smooth=False)

        btn = button.lower().strip()
        if HAS_PYAUTOGUI:
            if clicks == 2:
                pyautogui.doubleClick(button=btn)
            else:
                pyautogui.click(button=btn, clicks=clicks)
        else:
            user32 = ctypes.windll.user32
            # MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_LEFTUP = 0x0004
            # MOUSEEVENTF_RIGHTDOWN = 0x0008, MOUSEEVENTF_RIGHTUP = 0x0010
            down_flag = 0x0002 if btn == "left" else 0x0008
            up_flag = 0x0004 if btn == "left" else 0x0010
            for _ in range(clicks):
                user32.mouse_event(down_flag, 0, 0, 0, 0)
                time.sleep(0.04)
                user32.mouse_event(up_flag, 0, 0, 0, 0)
                time.sleep(0.05)

        curr = get_cursor_position()
        return {"success": True, "message": f"Mouse {btn}-click executed ({clicks}x) at ({curr['x']}, {curr['y']})."}
    except Exception as e:
        return {"success": False, "message": f"Mouse click failed: {e}"}

def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int) -> dict:
    """Drags mouse from start coordinates to end coordinates"""
    try:
        if HAS_PYAUTOGUI:
            pyautogui.moveTo(start_x, start_y)
            pyautogui.dragTo(end_x, end_y, duration=0.4, button="left")
            return {"success": True, "message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."}
        else:
            mouse_move(start_x, start_y, smooth=False)
            ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0) # left down
            time.sleep(0.1)
            mouse_move(end_x, end_y, smooth=True)
            time.sleep(0.1)
            ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0) # left up
            return {"success": True, "message": f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."}
    except Exception as e:
        return {"success": False, "message": f"Mouse drag failed: {e}"}

def mouse_scroll(clicks: int = 3, direction: str = "down") -> dict:
    """Scrolls mouse wheel up or down"""
    try:
        amount = abs(clicks) if direction.lower() == "up" else -abs(clicks)
        if HAS_PYAUTOGUI:
            pyautogui.scroll(amount * 100)
        else:
            # MOUSEEVENTF_WHEEL = 0x0800
            ctypes.windll.user32.mouse_event(0x0800, 0, 0, amount * 120, 0)
        return {"success": True, "message": f"Scrolled mouse {direction} by {clicks} increments."}
    except Exception as e:
        return {"success": False, "message": f"Mouse scroll failed: {e}"}

def keyboard_type(text: str, press_enter: bool = False, use_clipboard: bool = False) -> dict:
    """Types text directly or pastes via clipboard for high-speed long text insertion"""
    try:
        if not text:
            return {"success": True, "message": "No text provided to type."}

        # If text is long (> 30 chars) or use_clipboard is requested, paste it for instant input
        if (len(text) > 30 or use_clipboard or "\n" in text) and HAS_PYPERCLIP:
            old_clip = ""
            try:
                old_clip = pyperclip.paste()
            except Exception:
                pass
            pyperclip.copy(text)
            time.sleep(0.05)
            keyboard_hotkey(["ctrl", "v"])
            time.sleep(0.1)
        elif HAS_PYAUTOGUI:
            pyautogui.write(text, interval=0.01)
        else:
            # Fallback simple typing via SendKeys / PowerShell
            escaped = text.replace("`", "``").replace('"', '`"')
            subprocess.run(
                ["powershell", "-Command", f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{escaped}")'],
                capture_output=True, timeout=5
            )

        if press_enter:
            time.sleep(0.05)
            keyboard_press("enter")

        return {"success": True, "message": f"Typed {len(text)} characters into active window."}
    except Exception as e:
        return {"success": False, "message": f"Typing error: {e}"}

def keyboard_hotkey(keys) -> dict:
    """Presses a hotkey combination (e.g. ['ctrl', 'c'] or 'ctrl+shift+esc')"""
    try:
        if isinstance(keys, str):
            key_list = [k.strip().lower() for k in keys.replace("+", " ").split()]
        else:
            key_list = [str(k).strip().lower() for k in keys]

        if HAS_PYAUTOGUI:
            pyautogui.hotkey(*key_list)
        else:
            # Fallback via PowerShell SendKeys
            combo_str = ""
            for k in key_list:
                if k in ["ctrl", "control"]: combo_str += "^"
                elif k in ["alt"]: combo_str += "%"
                elif k in ["shift"]: combo_str += "+"
                elif k in ["enter", "return"]: combo_str += "{ENTER}"
                elif k in ["esc", "escape"]: combo_str += "{ESC}"
                elif k in ["tab"]: combo_str += "{TAB}"
                elif k in ["backspace"]: combo_str += "{BACKSPACE}"
                elif k in ["win", "windows"]: combo_str += "^{ESC}"
                else: combo_str += k
            subprocess.run(
                ["powershell", "-Command", f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait("{combo_str}")'],
                capture_output=True, timeout=5
            )

        return {"success": True, "message": f"Pressed hotkey combo: {'+'.join(key_list)}."}
    except Exception as e:
        return {"success": False, "message": f"Hotkey execution failed: {e}"}

def keyboard_press(key: str) -> dict:
    """Presses a single key (e.g. enter, esc, tab, space, up, down, backspace)"""
    try:
        k = key.strip().lower()
        if HAS_PYAUTOGUI:
            pyautogui.press(k)
        else:
            keyboard_hotkey([k])
        return {"success": True, "message": f"Pressed key '{k}'."}
    except Exception as e:
        return {"success": False, "message": f"Key press failed: {e}"}


# ─── Window Management & Active Window Context ────────────────────────────────

def get_active_window_info() -> dict:
    """Returns details of the currently focused Windows application"""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"title": "Desktop / No Active Window", "hwnd": 0}

        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value or "Untitled Window"

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))

        return {
            "title": title,
            "hwnd": hwnd,
            "bounds": {
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top
            }
        }
    except Exception as e:
        return {"title": "Unknown", "error": str(e)}

def focus_window(title_query: str) -> dict:
    """Finds and focuses a running application window matching title_query using resilient Shell AppActivate and PyGetWindow."""
    q = title_query.strip()
    if not q:
        return {"success": False, "message": "Window title query is empty."}

    # 1. Primary: WScript.Shell AppActivate (bypasses Windows foreground lock)
    try:
        script = f'(New-Object -ComObject WScript.Shell).AppActivate("{q}")'
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=3,
            creationflags=0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        )
        if res.stdout.strip().lower() == "true":
            time.sleep(0.15)
            return {"success": True, "message": f"Brought window matching '{q}' to foreground.", "title": q}
    except Exception:
        pass

    # 2. PyGetWindow fallback
    try:
        if HAS_PYGETWINDOW:
            windows = gw.getAllWindows()
            for w in windows:
                if w.title and q.lower() in w.title.lower():
                    if w.isMinimized:
                        w.restore()
                    w.activate()
                    time.sleep(0.1)
                    return {"success": True, "message": f"Brought window '{w.title}' to foreground.", "title": w.title}
    except Exception:
        pass

    return {"success": False, "message": f"No open window found matching '{title_query}'."}

def find_and_click_element(name_or_label: str) -> dict:
    """
    Locates an interactive UI element by name/label using Windows UI Automation
    and clicks its exact center coordinates.
    """
    try:
        from core.screenview import look
        from core.screenact import click

        view = look(budget_s=0.8, allow_ocr=False)
        if not view.usable or not view.elements:
            return {"success": False, "message": f"Screen perception could not read active window ({view.reason})."}

        target = None
        q = name_or_label.lower().strip()
        for el in view.elements:
            if el.interactable and el.name and q == el.name.lower():
                target = el
                break
        if not target:
            for el in view.elements:
                if el.interactable and el.name and q in el.name.lower():
                    target = el
                    break

        if not target:
            return {"success": False, "message": f"Element '{name_or_label}' was not found in the active window."}

        res = click(target)
        if res.ok:
            return {"success": True, "element": target.name, "message": f"Clicked '{target.name}' via UI Automation."}
        return {"success": False, "message": f"Failed to click '{target.name}': {res.reason}"}
    except Exception as e:
        return {"success": False, "message": f"Error during UI Automation element click: {e}"}

def find_and_type(name_or_label: str, text: str) -> dict:
    """
    Locates an interactive field by name/label, clicks it to focus, and types the requested text.
    """
    try:
        from core.screenview import look
        from core.screenact import click, type_text

        view = look(budget_s=0.8, allow_ocr=False)
        if not view.usable or not view.elements:
            return {"success": False, "message": f"Screen perception unavailable ({view.reason})."}

        target = None
        q = name_or_label.lower().strip()
        for el in view.elements:
            if el.interactable and el.name and q in el.name.lower():
                target = el
                break

        if not target:
            return {"success": False, "message": f"Field '{name_or_label}' not found."}

        c_res = click(target)
        if not c_res.ok:
            return {"success": False, "message": f"Could not focus '{target.name}': {c_res.reason}"}

        t_res = type_text(text)
        if t_res.ok:
            return {"success": True, "message": f"Typed into '{target.name}' via UI Automation."}
        return {"success": False, "message": f"Failed to type: {t_res.reason}"}
    except Exception as e:
        return {"success": False, "message": f"Error during UI Automation type: {e}"}

def list_open_windows() -> list:
    """Returns a list of titles of all visible desktop application windows"""
    results = []
    try:
        if HAS_PYGETWINDOW:
            windows = gw.getAllWindows()
            for w in windows:
                if w.title and w.visible and w.width > 100 and w.height > 100:
                    results.append({"title": w.title, "width": w.width, "height": w.height})
        else:
            ps = "Get-Process | Where-Object { $_.MainWindowTitle } | Select-Object -Property MainWindowTitle"
            res = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True, timeout=5)
            for line in res.stdout.splitlines():
                t = line.strip()
                if t and not t.startswith("MainWindowTitle") and not t.startswith("---"):
                    results.append({"title": t})
    except Exception:
        pass
    return results


# ─── File System Intelligence & Deep Search ────────────────────────────────────

def find_files(query: str, search_locations: list = None, extensions: list = None, days_back: int = None, limit: int = 10) -> list:
    """
    Locates files matching keywords (e.g. 'neural networks', 'research paper', 'invoice')
    across Downloads, Documents, Desktop, or specified directories, sorted by recency.
    """
    targets = search_locations or COMMON_SEARCH_DIRS
    exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions] if extensions else []
    tokens = [t.lower() for t in query.split() if len(t) > 2]

    time_cutoff = None
    if days_back:
        time_cutoff = datetime.now() - timedelta(days=days_back)

    found = []

    for d in targets:
        p = Path(d)
        if not p.exists():
            continue

        try:
            # Search top 2 levels of directories for fast execution (< 200ms)
            for item in p.glob("*"):
                try:
                    if item.is_file():
                        # Extension check
                        if exts and item.suffix.lower() not in exts:
                            continue

                        # Modification time check
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        if time_cutoff and mtime < time_cutoff:
                            continue

                        name_lower = item.name.lower()
                        # Score match: if query tokens match name
                        match_score = sum(1 for t in tokens if t in name_lower)
                        if not tokens or match_score > 0 or query.lower() in name_lower:
                            size_mb = round(item.stat().st_size / (1024 * 1024), 2)
                            found.append({
                                "name": item.name,
                                "path": str(item.resolve()),
                                "size_mb": size_mb,
                                "modified": mtime.strftime("%Y-%m-%d %H:%M"),
                                "mtime_ts": item.stat().st_mtime,
                                "match_score": match_score
                            })
                except Exception:
                    continue
        except Exception:
            continue

    # Sort by score first, then most recently modified
    found.sort(key=lambda x: (x["match_score"], x["mtime_ts"]), reverse=True)
    return found[:limit]


# ─── Document Content Extraction ──────────────────────────────────────────────

def read_document_text(file_path: str, max_chars: int = 12000) -> dict:
    """
    Extracts text from PDF, TXT, MD, Python, JSON, CSV, or code files.
    """
    # Credential Isolation Policy (Ported from J.A.R.V.I.S. policy.mjs)
    try:
        from ..core.policy import vet_file_path
        safe, reason = vet_file_path(file_path)
        if not safe:
            return {"success": False, "message": reason}
    except Exception:
        pass

    p = Path(file_path)
    if not p.exists():
        return {"success": False, "message": f"File '{file_path}' does not exist."}

    ext = p.suffix.lower()

    try:
        # 1. PDF Document
        if ext == ".pdf":
            if HAS_PYPDF:
                reader = pypdf.PdfReader(str(p))
                full_text = []
                for idx, page in enumerate(reader.pages):
                    t = page.extract_text()
                    if t:
                        full_text.append(f"--- Page {idx + 1} ---\n{t}")
                    if sum(len(x) for x in full_text) > max_chars:
                        break
                text_content = "\n\n".join(full_text)[:max_chars]
                return {
                    "success": True,
                    "file_name": p.name,
                    "pages": len(reader.pages),
                    "content": text_content,
                    "message": f"Extracted {len(text_content)} characters from PDF '{p.name}'."
                }
            else:
                return {"success": False, "message": "pypdf library not available for reading PDF."}

        # 2. Text, Code, Markdown, CSV, JSON
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            text_content = f.read(max_chars)
            return {
                "success": True,
                "file_name": p.name,
                "content": text_content,
                "message": f"Read {len(text_content)} characters from '{p.name}'."
            }
    except Exception as e:
        return {"success": False, "message": f"Error reading document: {e}"}


# ─── Notepad Drafting & Auto-Documentation ────────────────────────────────────

def draft_in_notepad(content: str, filename: str = None) -> dict:
    """
    Saves text content to a file on Desktop/Documents and opens it in Notepad,
    bringing it immediately to focus for the user.
    """
    try:
        desktop_dir = USER_HOME / "Desktop"
        if not desktop_dir.exists():
            desktop_dir = USER_HOME / "Documents"

        name = filename or f"Aether_Draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        if not name.endswith(".txt"):
            name += ".txt"

        target_file = desktop_dir / name
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Open Notepad with the saved file
        subprocess.Popen(["notepad.exe", str(target_file)])
        time.sleep(0.3)
        focus_window("Notepad")

        return {
            "success": True,
            "file_path": str(target_file),
            "file_name": name,
            "message": f"Summary drafted in Notepad and saved to '{name}' on your Desktop, Sir."
        }
    except Exception as e:
        return {"success": False, "message": f"Error drafting in Notepad: {e}"}


# ─── Terminal Command Runner & Autonomous CI/CD ───────────────────────────────

# Allowlisted commands for terminal execution (prevents shell injection)
# Dangerous commands removed: powershell, cmd, rm, mv, cp (can be abused)
ALLOWED_COMMANDS = {
    "git", "python", "python3", "pip", "npm", "node", "npx", "cargo", "go",
    "gradle", "mvn", "make", "cmake", "dotnet", "pytest",
    "dir", "ls", "cat", "type", "echo",
    "docker", "kubectl", "terraform", "ansible",
}

# Shell metacharacters that indicate command injection / chaining / redirection
SHELL_METACHARS = {">", "<", "|", "&", ";", "$", "`"}

# Dangerous arguments and subcommands that should never appear in allowed commands
DANGEROUS_ARGS = {
    "-command", "-encodedcommand", "-e", "-enc",
    "/c", "/k", "/s", "/q", "/f", "/r", "-rf", "-r", "-f",
    "rm", "del", "erase", "rmdir", "rd", "format", "shutdown", "restart",
    "reg", "net", "sc", "wmic", "bcdedit", "diskpart", "vssadmin",
}

def _is_command_allowed(command: str) -> bool:
    """Check if the command is in the allowlist and doesn't contain dangerous args."""
    if not command or not command.strip():
        return False
    
    # Check for shell metacharacters anywhere in the command
    for char in SHELL_METACHARS:
        if char in command:
            return False
    
    parts = command.strip().split()
    if not parts:
        return False
    
    base_cmd = parts[0].lower()
    # Handle paths like "C:\path\to\python.exe", "./python", or "/usr/bin/python"
    if "\\" in base_cmd or "/" in base_cmd:
        base_cmd = base_cmd.replace("\\", "/").split("/")[-1]
    base_cmd = base_cmd.replace(".exe", "").replace(".bat", "").replace(".cmd", "")
    
    if base_cmd not in ALLOWED_COMMANDS:
        return False
    
    # Check arguments individually to avoid substring collisions (e.g. 'script.py' containing 'sc')
    for arg in parts[1:]:
        clean_arg = arg.strip("\"'").lower()
        if clean_arg in DANGEROUS_ARGS:
            return False
        # Flags that start with dangerous prefixes (e.g. -Command, /c)
        if any(clean_arg.startswith(prefix) for prefix in ["/c", "/k", "-command", "-encodedcommand"]):
            return False
    
    return True


def run_system_command(command: str, cwd: str = None, timeout: int = 60, background: bool = False) -> dict:
    """
    Executes a terminal/shell command (git, gradle, python, npm, powershell).
    Supports both synchronous inspection and background execution.
    Uses allowlist to prevent shell injection - no shell=True.
    """
    if not _is_command_allowed(command):
        return {
            "success": False,
            "message": f"Command not allowed: '{command.split()[0] if command.split() else command}'. Only allowlisted commands permitted."
        }
    
    try:
        working_dir = cwd or str(USER_HOME)

        if background:
            # For background, still use list form but with Popen
            parts = command.strip().split()
            proc = subprocess.Popen(
                parts,
                shell=False,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return {
                "success": True,
                "pid": proc.pid,
                "message": f"Command launched in background (PID {proc.pid}): '{command}'."
            }

        t0 = time.time()
        parts = command.strip().split()
        res = subprocess.run(
            parts,
            shell=False,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        elapsed = round(time.time() - t0, 2)
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()

        combined = out if out else err
        return {
            "success": res.returncode == 0,
            "returncode": res.returncode,
            "output": combined[:1500],
            "elapsed_s": elapsed,
            "message": f"Command completed in {elapsed}s (Exit code {res.returncode}):\n{combined[:250]}"
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "message": f"Command timed out after {timeout} seconds."}
    except Exception as e:
        return {"success": False, "message": f"Terminal execution error: {e}"}
