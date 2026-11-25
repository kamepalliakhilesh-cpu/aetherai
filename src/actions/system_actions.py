import ctypes
import os
import subprocess
from pathlib import Path

# Windows Virtual-Key Codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

def _send_key(vk_code: int):
    # key down
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    # key up
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)

def set_volume(action: str, steps: int = 5, record_undo: bool = True) -> dict:
    act = action.strip().lower()
    
    # Import undo if available
    push_undo = None
    try:
        from core.undo import push_undo
    except ImportError:
        pass

    if "up" in act or "increase" in act or "raise" in act:
        for _ in range(steps):
            _send_key(VK_VOLUME_UP)
        if record_undo and push_undo:
            push_undo(f"Increase volume by {steps * 2}%", lambda: set_volume("down", steps, record_undo=False))
        return {"success": True, "message": f"Volume increased by {steps * 2}%."}
    elif "down" in act or "decrease" in act or "lower" in act:
        for _ in range(steps):
            _send_key(VK_VOLUME_DOWN)
        if record_undo and push_undo:
            push_undo(f"Decrease volume by {steps * 2}%", lambda: set_volume("up", steps, record_undo=False))
        return {"success": True, "message": f"Volume decreased by {steps * 2}%."}
    elif "mute" in act or "unmute" in act or "toggle" in act:
        _send_key(VK_VOLUME_MUTE)
        if record_undo and push_undo:
            push_undo("Mute/unmute volume toggle", lambda: set_volume("mute", 1, record_undo=False))
        return {"success": True, "message": "Volume muted/unmuted."}
    else:
        # Default mild boost
        for _ in range(3):
            _send_key(VK_VOLUME_UP)
        if record_undo and push_undo:
            push_undo("Volume bump", lambda: set_volume("down", 3, record_undo=False))
        return {"success": True, "message": "Volume adjusted."}

def lock_workstation() -> dict:
    try:
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "message": "Screen locked."}
    except Exception as e:
        return {"success": False, "message": f"Failed to lock workstation: {str(e)}"}

def sleep_pc(require_confirm: bool = False) -> dict:
    if require_confirm:
        try:
            from core.confirm import request as confirm_request
            req = confirm_request("sleep_pc", "Sleep PC", "Put computer into low-power sleep mode", lambda: sleep_pc(require_confirm=False).get("message", "PC slept."))
            return {"success": True, "message": req}
        except Exception:
            pass
    try:
        subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        return {"success": True, "message": "Entering sleep mode."}
    except Exception as e:
        return {"success": False, "message": f"Failed to sleep PC: {str(e)}"}

def empty_recycle_bin(require_confirm: bool = False) -> dict:
    if require_confirm:
        try:
            from core.confirm import request as confirm_request
            req = confirm_request("empty_recycle_bin", "Empty Recycle Bin", "Permanently delete all files in Recycle Bin", lambda: empty_recycle_bin(require_confirm=False).get("message", "Emptied."))
            return {"success": True, "message": req}
        except Exception:
            pass
    try:
        # Flags: SHERB_NOCONFIRMATION = 0x00000001, SHERB_NOPROGRESSUI = 0x00000002, SHERB_NOSOUND = 0x00000004
        flags = 7
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        return {"success": True, "message": "Recycle Bin emptied."}
    except Exception as e:
        return {"success": False, "message": f"Failed to empty Recycle Bin: {str(e)}"}

def open_folder(folder_name: str) -> dict:
    f_lower = folder_name.strip().lower()
    user_home = Path.home()
    
    target_path = None
    if "download" in f_lower:
        target_path = user_home / "Downloads"
    elif "document" in f_lower:
        target_path = user_home / "Documents"
    elif "desktop" in f_lower:
        target_path = user_home / "Desktop"
    elif "picture" in f_lower or "photo" in f_lower:
        target_path = user_home / "Pictures"
    elif "music" in f_lower:
        target_path = user_home / "Music"
    elif "video" in f_lower:
        target_path = user_home / "Videos"
    else:
        target_path = Path(folder_name)
        
    if target_path and target_path.exists():
        os.startfile(str(target_path))
        return {"success": True, "message": f"Opened folder: {target_path.name}."}
    else:
        return {"success": False, "message": f"Folder not found: {folder_name}"}

def open_file(file_path: str) -> dict:
    try:
        p = Path(file_path)
        if p.exists():
            os.startfile(str(p))
            return {"success": True, "message": f"Opened file: {p.name}."}
        return {"success": False, "message": f"File not found: {file_path}"}
    except Exception as e:
        return {"success": False, "message": f"Error opening file: {e}"}

# ==========================================
# AETHER MOBILE COMPANION TELE-LINK ACTIONS
# ==========================================

def get_mobile_link_status() -> dict:
    """Check connection status and telemetry of linked Aether Mobile device."""
    try:
        from src.network.bridge_server import get_bridge_server
        bridge = get_bridge_server()
        telem = bridge.mobile_telemetry
        if telem.get("connected"):
            bat = telem.get("battery")
            bat_str = f"{bat}%" if bat is not None else "unknown"
            charging_str = " (charging)" if telem.get("is_charging") else ""
            device = telem.get("device_name", "Aether Mobile")
            return {
                "success": True,
                "connected": True,
                "message": f"Mobile device '{device}' is linked. Battery: {bat_str}{charging_str}.",
                "telemetry": telem,
            }
        else:
            return {
                "success": False,
                "connected": False,
                "message": f"No mobile device currently connected. Pair using code: {bridge.pairing_code} at ws://{bridge.local_ip}:{bridge.port}",
                "pairing_code": bridge.pairing_code,
                "ws_url": f"ws://{bridge.local_ip}:{bridge.port}",
            }
    except Exception as e:
        return {"success": False, "message": f"Bridge error: {e}"}

def ring_phone() -> dict:
    """Trigger audible alarm / find my phone on linked mobile device."""
    try:
        from src.network.bridge_server import get_bridge_server
        bridge = get_bridge_server()
        if not bridge.mobile_telemetry.get("connected"):
            return {"success": False, "message": "Cannot ring phone: No mobile device connected."}
        bridge.send_phone_command("ring_phone", {"volume": 100})
        return {"success": True, "message": "Ringing mobile device at maximum volume, Sir."}
    except Exception as e:
        return {"success": False, "message": f"Failed to ring phone: {e}"}

def get_phone_battery() -> dict:
    """Retrieve the battery percentage of the linked mobile phone."""
    try:
        from src.network.bridge_server import get_bridge_server
        bridge = get_bridge_server()
        telem = bridge.mobile_telemetry
        if not telem.get("connected"):
            return {"success": False, "message": "Mobile device is offline."}
        bat = telem.get("battery")
        if bat is not None:
            charging = " and charging" if telem.get("is_charging") else ""
            return {"success": True, "battery": bat, "message": f"Mobile battery is at {bat}%{charging}, Sir."}
        bridge.send_phone_command("get_battery")
        return {"success": True, "message": "Requesting latest battery telemetry from phone, Sir."}
    except Exception as e:
        return {"success": False, "message": f"Failed to read phone battery: {e}"}

def send_phone_whatsapp(contact: str, message: str) -> dict:
    """Dispatch a WhatsApp message via linked mobile phone."""
    try:
        from src.network.bridge_server import get_bridge_server
        bridge = get_bridge_server()
        if not bridge.mobile_telemetry.get("connected"):
            return {"success": False, "message": "Cannot send WhatsApp: Mobile companion is offline."}
        bridge.send_phone_command("send_whatsapp", {"contact": contact, "message": message})
        return {"success": True, "message": f"Dispatched WhatsApp to {contact}: '{message}', Sir."}
    except Exception as e:
        return {"success": False, "message": f"Failed to dispatch WhatsApp: {e}"}

def send_phone_sms(contact: str, message: str) -> dict:
    """Dispatch an SMS message via linked mobile phone."""
    try:
        from src.network.bridge_server import get_bridge_server
        bridge = get_bridge_server()
        if not bridge.mobile_telemetry.get("connected"):
            return {"success": False, "message": "Cannot send SMS: Mobile companion is offline."}
        bridge.send_phone_command("send_sms", {"contact": contact, "message": message})
        return {"success": True, "message": f"Dispatched SMS to {contact}: '{message}', Sir."}
    except Exception as e:
        return {"success": False, "message": f"Failed to dispatch SMS: {e}"}

def toggle_phone_torch(enabled: bool = True) -> dict:
    """Toggle the flashlight / torch on the linked mobile device."""
    try:
        from src.network.bridge_server import get_bridge_server
        bridge = get_bridge_server()
        if not bridge.mobile_telemetry.get("connected"):
            return {"success": False, "message": "Mobile companion is offline."}
        bridge.send_phone_command("toggle_flashlight", {"enabled": enabled})
        state = "enabled" if enabled else "disabled"
        return {"success": True, "message": f"Mobile flashlight {state}, Sir."}
    except Exception as e:
        return {"success": False, "message": f"Failed to toggle mobile torch: {e}"}

def sync_clipboard_to_phone() -> dict:
    """Sync current Windows clipboard text directly to the linked mobile phone."""
    try:
        import pyperclip
        text = pyperclip.paste()
        if not text:
            return {"success": False, "message": "Windows clipboard is empty."}
        from src.network.bridge_server import get_bridge_server
        bridge = get_bridge_server()
        if not bridge.mobile_telemetry.get("connected"):
            return {"success": False, "message": "Mobile companion is offline."}
        bridge.sync_clipboard_to_mobile(text)
        preview = text[:40] + "..." if len(text) > 40 else text
        return {"success": True, "message": f"Clipboard synced to phone: '{preview}', Sir."}
    except Exception as e:
        return {"success": False, "message": f"Failed to sync clipboard: {e}"}


