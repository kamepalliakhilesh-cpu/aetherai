import re
import subprocess
import ctypes
from pathlib import Path

def get_display_topology() -> dict:
    """
    Returns real-time multi-monitor topology and screen metrics using Windows EnumDisplayMonitors.
    """
    try:
        user32 = ctypes.windll.user32
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                        ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

        monitors = []
        def _enum_cb(hmon, hdc, lprect, lparam):
            r = lprect.contents
            w = r.right - r.left
            h = r.bottom - r.top
            monitors.append({
                "index": len(monitors) + 1,
                "width": w,
                "height": h,
                "resolution": f"{w}x{h}",
                "is_primary": (r.left == 0 and r.top == 0)
            })
            return True

        MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(RECT), ctypes.c_double)
        user32.EnumDisplayMonitors(0, 0, MONITORENUMPROC(_enum_cb), 0)

        count = len(monitors)
        desc = "Single Laptop Display" if count == 1 else f"Multi-Monitor Array ({count} Displays Active)"
        return {
            "success": True,
            "display_count": count,
            "displays": monitors,
            "description": desc,
            "is_multi_monitor": count > 1
        }
    except Exception as e:
        return {"success": False, "display_count": 1, "description": "Single Display", "error": str(e)}

def switch_display_mode(mode: str) -> dict:
    """
    Switches Windows display presentation mode:
    'extend', 'clone' / 'duplicate', 'internal' / 'pc_screen', 'external' / 'second_screen'
    """
    m = mode.lower().strip()
    flag = "/extend"
    if m in ["clone", "duplicate"]: flag = "/clone"
    elif m in ["internal", "pc", "laptop", "single"]: flag = "/internal"
    elif m in ["external", "second", "projector"]: flag = "/external"

    try:
        subprocess.run(["displayswitch.exe", flag], check=True)
        return {
            "success": True,
            "mode": flag.lstrip("/"),
            "message": f"Display topology configured to '{flag.lstrip('/')}' mode, Sir."
        }
    except Exception as e:
        return {"success": False, "message": f"Display switch failed: {e}"}

def get_audio_endpoint() -> dict:
    """
    Detects the current active audio output routing (Headphones vs Built-in Laptop Speakers).
    """
    try:
        ps_cmd = "Get-PnpDevice -Class 'AudioEndpoint' -Status 'OK' | Select-Object -Property FriendlyName | ConvertTo-Json"
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)

        is_headphones = False
        device_name = "Speakers (Realtek Audio)"

        if res.stdout:
            import json
            try:
                data = json.loads(res.stdout)
                devices = data if isinstance(data, list) else [data]
                for d in devices:
                    name = d.get("FriendlyName", "")
                    if any(k in name.lower() for k in ["headphone", "headset", "buds", "airpods", "wh-1000", "earphones"]):
                        is_headphones = True
                        device_name = name
                        break
                    elif "speaker" in name.lower():
                        device_name = name
            except Exception:
                pass

        return {
            "success": True,
            "active_device": device_name,
            "device_name": device_name,
            "is_headphones": is_headphones,
            "endpoint_type": "headphones" if is_headphones else "speakers",
            "routing": "Headphones / Headset" if is_headphones else "Built-in Laptop Speakers",
            "message": f"Audio output active via {device_name}."
        }
    except Exception as e:
        return {"success": False, "active_device": "Default Speakers", "device_name": "Default Speakers", "is_headphones": False, "endpoint_type": "speakers", "error": str(e)}

def get_bluetooth_devices() -> dict:
    """
    Scans paired and connected Bluetooth peripherals (Smartphones, watches, wireless audio).
    """
    try:
        ps_cmd = "Get-PnpDevice -Class 'Bluetooth' -Status 'OK' | Select-Object -Property FriendlyName | ConvertTo-Json"
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, timeout=5)

        devices_found = []
        has_phone = False
        phone_name = None

        if res.stdout:
            import json
            try:
                data = json.loads(res.stdout)
                dev_list = data if isinstance(data, list) else [data]
                for d in dev_list:
                    name = d.get("FriendlyName", "").strip()
                    if name and not any(k in name.lower() for k in ["adapter", "radio", "enumerator", "wireless bluetooth"]):
                        devices_found.append(name)
                        if any(p in name.lower() for p in ["phone", "galaxy", "iphone", "pixel", "oneplus", "xiaomi", "redmi"]):
                            has_phone = True
                            phone_name = name
            except Exception:
                pass

        return {
            "success": True,
            "connected_peripherals": devices_found,
            "has_phone_nearby": has_phone,
            "phone_name": phone_name,
            "message": f"Detected {len(devices_found)} active Bluetooth devices (Phone nearby: {has_phone})."
        }
    except Exception as e:
        return {"success": False, "connected_peripherals": [], "has_phone_nearby": False, "error": str(e)}

def get_network_environment() -> dict:
    """
    Retrieves real-time WiFi telemetry: SSID, 5GHz/2.4GHz Band, Signal Strength, PHY Rate.
    """
    try:
        res = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=5)
        out = res.stdout

        ssid_m = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
        band_m = re.search(r"^\s*Band\s*:\s*(.+)$", out, re.MULTILINE)
        sig_m = re.search(r"^\s*Signal\s*:\s*(\d+)%", out, re.MULTILINE)
        rx_m = re.search(r"^\s*Receive rate \(Mbps\)\s*:\s*(\d+)", out, re.MULTILINE)
        tx_m = re.search(r"^\s*Transmit rate \(Mbps\)\s*:\s*(\d+)", out, re.MULTILINE)

        ssid = ssid_m.group(1).strip() if ssid_m else "Offline / Local"
        band = band_m.group(1).strip() if band_m else "N/A"
        signal = int(sig_m.group(1)) if sig_m else 0
        rx = int(rx_m.group(1)) if rx_m else 0
        tx = int(tx_m.group(1)) if tx_m else 0

        is_conn = bool(ssid and ssid not in ["Offline / Local", "N/A"])
        return {
            "success": True,
            "is_connected": is_conn,
            "ssid": ssid,
            "band": band,
            "signal_percent": signal,
            "rx_mbps": rx,
            "tx_mbps": tx,
            "phy_rate_mbps": rx or tx,
            "status": f"Connected to '{ssid}' ({band}, {signal}% Signal, {rx} Mbps)"
        }
    except Exception as e:
        return {"success": False, "is_connected": False, "ssid": "Local Link", "signal_percent": 100, "error": str(e)}

def get_peripheral_snapshot() -> dict:
    """
    Aggregates full peripheral environment status for proactive awareness and HUD telemetry.
    """
    disp = get_display_topology()
    audio = get_audio_endpoint()
    bt = get_bluetooth_devices()
    net = get_network_environment()

    return {
        "success": True,
        "display_count": disp.get("display_count", 1),
        "displays": disp.get("displays", []),
        "display_topology": disp,
        "audio": audio,
        "bluetooth": bt,
        "network": net,
        "summary": f"{disp.get('description', 'Display')} | Audio: {audio.get('routing', 'Speakers')} | WiFi: {net.get('ssid', 'Local')} ({net.get('signal_percent', 0)}%)"
    }
