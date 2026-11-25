import os
import subprocess
import shutil
import re
import winreg
import psutil

# Dynamic cache of installed Windows apps: Name -> (OriginalName, AppID)
_INSTALLED_APPS_CACHE = {}

def refresh_installed_apps():
    """Queries Windows Get-StartApps to find all installed UWP & desktop applications"""
    global _INSTALLED_APPS_CACHE
    try:
        cmd = 'powershell -NoProfile -Command "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json"'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8)
        if res.returncode == 0 and res.stdout.strip():
            import json
            data = json.loads(res.stdout)
            if isinstance(data, list):
                for item in data:
                    name = item.get("Name", "").strip()
                    appid = item.get("AppID", "").strip()
                    if name and appid:
                        _INSTALLED_APPS_CACHE[name.lower()] = (name, appid)
            elif isinstance(data, dict):
                name = data.get("Name", "").strip()
                appid = data.get("AppID", "").strip()
                if name and appid:
                    _INSTALLED_APPS_CACHE[name.lower()] = (name, appid)
            print(f"[AppActions] Indexed {len(_INSTALLED_APPS_CACHE)} installed applications.")
    except Exception as e:
        print(f"[AppActions] Error loading installed apps catalog: {e}")

def _get_registry_app_path(name: str) -> str:
    """Checks Windows App Paths registry for registered application executables"""
    clean_name = name.lower().replace(".exe", "").strip()
    for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
        for sub in [
            f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{clean_name}.exe",
            f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{clean_name}"
        ]:
            try:
                with winreg.OpenKey(root, sub) as key:
                    val, _ = winreg.QueryValueEx(key, "")
                    if val and os.path.exists(val):
                        return val
            except Exception:
                pass
    return None

# Common command & URI shortcuts for instant zero-latency launches
COMMON_SHORTCUTS = {
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "brave": "start brave",
    "brave browser": "start brave",
    "edge": "start msedge",
    "microsoft edge": "start msedge",
    "msedge": "start msedge",
    "notepad": "start notepad",
    "calculator": "start calc:",
    "calc": "start calc:",
    "vscode": "start code",
    "vs code": "start code",
    "visual studio code": "start code",
    "code": "start code",
    "spotify": "start spotify:",
    "discord": "start discord:",
    "steam": "start steam:",
    "terminal": "start wt",
    "windows terminal": "start wt",
    "wt": "start wt",
    "cmd": "start cmd",
    "command prompt": "start cmd",
    "powershell": "start powershell",
    "task manager": "start taskmgr",
    "taskmgr": "start taskmgr",
    "explorer": "start explorer",
    "file explorer": "start explorer",
    "files": "start explorer",
    "my computer": "start explorer",
    "paint": "start mspaint",
    "mspaint": "start mspaint",
    "settings": "start ms-settings:",
    "windows settings": "start ms-settings:",
    "whatsapp": "start whatsapp:",
    "word": "start winword",
    "excel": "start excel",
    "powerpoint": "start powerpnt",
    "camera": "start microsoft.windows.camera:",
    "clock": "start ms-clock:",
    "alarms": "start ms-clock:",
    "store": "start ms-windows-store:",
    "microsoft store": "start ms-windows-store:"
}

def open_application(app_name: str) -> dict:
    if not app_name or not app_name.strip():
        return {"success": False, "message": "No application specified."}

    app_lower = app_name.strip().lower()
    # Strip common leading noise words
    clean_target = re.sub(r"^(can you open|please open|could you launch|open|launch|start|run|the|an|a|my)\s+", "", app_lower).strip()
    clean_target = re.sub(r"\s+app$", "", clean_target).strip()

    # 1. Check known fast shortcuts & URIs
    if clean_target in COMMON_SHORTCUTS:
        cmd = COMMON_SHORTCUTS[clean_target]
        try:
            subprocess.Popen(cmd, shell=True)
            return {"success": True, "message": f"Opening {clean_target.title()}, Sir."}
        except Exception as e:
            print(f"[AppActions] Shortcut launch error: {e}")

    # 2. Check Windows App Paths Registry (.exe)
    reg_path = _get_registry_app_path(clean_target)
    if reg_path:
        try:
            subprocess.Popen(f'start "" "{reg_path}"', shell=True)
            return {"success": True, "message": f"Opening {clean_target.title()}, Sir."}
        except Exception as e:
            print(f"[AppActions] Registry launch error: {e}")

    # 3. Search dynamic installed Windows apps (Get-StartApps)
    if not _INSTALLED_APPS_CACHE:
        refresh_installed_apps()

    # Look for exact or word matches in StartApps
    best_match = None
    for key, (orig_name, appid) in _INSTALLED_APPS_CACHE.items():
        if clean_target == key:
            best_match = (orig_name, appid)
            break
        elif key.startswith(clean_target) or clean_target.startswith(key):
            if not best_match:
                best_match = (orig_name, appid)
        elif clean_target in key:
            if not best_match:
                best_match = (orig_name, appid)

    if best_match:
        orig_name, appid = best_match
        try:
            subprocess.Popen(f'explorer.exe "shell:appsFolder\\{appid}"', shell=True)
            return {"success": True, "message": f"Launching {orig_name}, Sir."}
        except Exception as e:
            print(f"[AppActions] Failed to launch {appid}: {e}")

    # 4. Try standard startfile if it's a file path or known protocol
    try:
        os.startfile(clean_target)
        return {"success": True, "message": f"Opening {clean_target}."}
    except Exception:
        pass

    return {"success": False, "message": f"Could not locate application '{app_name}' on this PC."}


# Process name aliases for clean termination
PROCESS_ALIASES = {
    "vscode": "Code.exe",
    "vs code": "Code.exe",
    "visual studio code": "Code.exe",
    "code": "Code.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "brave": "brave.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "notepad": "Notepad.exe",
    "calculator": "CalculatorApp.exe",
    "calc": "CalculatorApp.exe",
    "terminal": "WindowsTerminal.exe",
    "windows terminal": "WindowsTerminal.exe",
    "cmd": "cmd.exe",
    "task manager": "Taskmgr.exe",
    "steam": "steam.exe"
}

def close_application(process_name: str) -> dict:
    if not process_name or not process_name.strip():
        return {"success": False, "message": "No process specified."}

    p_raw = process_name.strip().lower()
    p_clean = re.sub(r"^(can you close|please close|close|kill|terminate|stop|exit|the|an|a|my)\s+", "", p_raw).strip()
    p_clean = re.sub(r"\s+app$", "", p_clean).strip()

    target_exe = PROCESS_ALIASES.get(p_clean)

    # 1. Try psutil process search and termination
    terminated_count = 0
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            p_name = (proc.info['name'] or '').lower()
            should_kill = False
            if target_exe and p_name == target_exe.lower():
                should_kill = True
            elif p_name == p_clean or p_name == f"{p_clean}.exe":
                should_kill = True
            elif p_clean in p_name and len(p_clean) >= 4:
                should_kill = True

            if should_kill:
                proc.terminate()
                terminated_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if terminated_count > 0:
        return {"success": True, "message": f"Closed {p_clean.title()} ({terminated_count} process{'es' if terminated_count > 1 else ''} terminated), Sir."}

    # 2. Fallback to taskkill
    exe_name = target_exe or (p_clean if p_clean.endswith(".exe") else f"{p_clean}.exe")
    try:
        res = subprocess.run(["taskkill", "/F", "/IM", exe_name], capture_output=True, text=True)
        if res.returncode == 0:
            return {"success": True, "message": f"Terminated {p_clean.title()}, Sir."}
    except Exception:
        pass

    return {"success": False, "message": f"Could not find any running process matching '{process_name}'."}
