import datetime
import psutil
import requests
from ..core.telemetry import get_system_telemetry

def get_live_weather(timeout: float = 2.5) -> str:
    """Fetches fast, API-key-free local weather report"""
    try:
        r = requests.get("https://wttr.in/?format=%C+%t", timeout=timeout)
        if r.status_code == 200 and r.text.strip():
            # Clean extra spaces
            clean = " ".join(r.text.strip().split())
            return clean
    except Exception:
        pass
    return None

def generate_situational_briefing(assistant_name: str = "Aether") -> dict:
    """Generates a comprehensive JARVIS-style situational status briefing"""
    now = datetime.datetime.now()
    hour = now.hour

    if hour < 12:
        salutation = "Good morning, Sir."
    elif hour < 17:
        salutation = "Good afternoon, Sir."
    elif hour < 21:
        salutation = "Good evening, Sir."
    else:
        salutation = "Good night, Sir."

    telem = get_system_telemetry()
    weather = get_live_weather()

    # Compose conversational briefing
    parts = [salutation]

    # Time & Date
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d")
    parts.append(f"It is {time_str} on {date_str}.")

    # Weather
    if weather:
        parts.append(f"Current local conditions are {weather}.")

    # Power status
    bat_pct = telem.get("battery_percent", 100)
    is_plugged = telem.get("battery_plugged", True)
    if is_plugged:
        parts.append(f"Laptop power is connected with battery at {bat_pct}%.")
    else:
        runtime = telem.get("battery_time", "calculating")
        parts.append(f"Operating on battery at {bat_pct}%, with approximately {runtime} of estimated runtime.")

    # Hardware load
    cpu = telem.get("cpu_percent", 0)
    ram_gb = telem.get("ram_used_gb", 0)
    total_ram = telem.get("ram_total_gb", 16)
    disk_free = telem.get("disk_free_gb", 0)

    if cpu > 75:
        parts.append(f"CPU load is elevated at {cpu}%, utilizing {ram_gb} of {total_ram} gigabytes memory.")
    else:
        parts.append(f"Core hardware telemetry is nominal: CPU load is {cpu}%, RAM utilization is {telem.get('ram_percent')}%.")

    if disk_free > 0:
        parts.append(f"Primary storage drive has {disk_free} gigabytes free.")

    parts.append("All background monitoring systems are vigilant and standing by.")

    full_text = " ".join(parts)

    return {
        "text": full_text,
        "salutation": salutation,
        "time": time_str,
        "date": date_str,
        "weather": weather,
        "battery": f"{bat_pct}% ({'Plugged in' if is_plugged else 'Battery'})",
        "cpu": f"{cpu}%",
        "ram": f"{ram_gb}/{total_ram} GB"
    }
