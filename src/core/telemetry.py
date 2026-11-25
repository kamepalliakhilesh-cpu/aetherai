import psutil
import datetime
import platform

def get_system_telemetry() -> dict:
    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True)

    # Memory
    mem = psutil.virtual_memory()
    ram_percent = mem.percent
    ram_used_gb = round(mem.used / (1024 ** 3), 1)
    ram_total_gb = round(mem.total / (1024 ** 3), 1)

    # Disk C:
    try:
        disk = psutil.disk_usage("C:\\")
        disk_percent = disk.percent
        disk_free_gb = round(disk.free / (1024 ** 3), 1)
    except Exception:
        disk_percent = 0
        disk_free_gb = 0

    # Battery
    battery = psutil.sensors_battery()
    if battery is not None:
        battery_percent = int(battery.percent)
        battery_plugged = battery.power_plugged
        secs_left = battery.secsleft
        if secs_left == psutil.POWER_TIME_UNLIMITED or secs_left == psutil.POWER_TIME_UNKNOWN:
            battery_time = "Plugged in" if battery_plugged else "Calculating..."
        else:
            hours = secs_left // 3600
            mins = (secs_left % 3600) // 60
            battery_time = f"{hours}h {mins}m"
    else:
        battery_percent = 100
        battery_plugged = True
        battery_time = "Desktop / AC"

    # Process count
    proc_count = len(psutil.pids())

    # System boot time
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime_duration = datetime.datetime.now() - boot_time
    hours, remainder = divmod(int(uptime_duration.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m"

    return {
        "cpu_percent": cpu_percent,
        "cpu_cores": cpu_count,
        "ram_percent": ram_percent,
        "ram_used_gb": ram_used_gb,
        "ram_total_gb": ram_total_gb,
        "disk_percent": disk_percent,
        "disk_free_gb": disk_free_gb,
        "battery_percent": battery_percent,
        "battery_plugged": battery_plugged,
        "battery_time": battery_time,
        "process_count": proc_count,
        "uptime": uptime_str,
        "os": f"{platform.system()} {platform.release()}",
        "node": platform.node()
    }
