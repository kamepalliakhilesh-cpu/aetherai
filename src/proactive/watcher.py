import time
import threading
import ctypes
import psutil
from typing import Callable, Optional

class ProactiveSentinel:
    """
    JARVIS Proactive Sentinel:
    Continuously monitors laptop hardware, power, thermal/load spikes,
    and user environment transitions, speaking up autonomously when needed.
    """

    def __init__(self, on_proactive_alert: Optional[Callable[[dict], None]] = None):
        self.on_proactive_alert = on_proactive_alert
        self.is_running = False
        self.thread = None

        # Tracking states
        self.last_plugged_state = None
        self.last_alert_times = {} # key -> timestamp
        self.sustained_high_cpu_count = 0
        self.last_foreground_app = ""
        self.first_run = True

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._sentinel_loop, daemon=True)
        self.thread.start()
        print("[Sentinel] ✓ Proactive hardware & environment sentinel active.")

    def stop(self):
        self.is_running = False

    def _can_fire(self, alert_key: str, cooldown_seconds: float = 600.0) -> bool:
        """Enforces intelligent cooldowns so JARVIS never pesters the user"""
        now = time.time()
        last = self.last_alert_times.get(alert_key, 0)
        if now - last >= cooldown_seconds:
            self.last_alert_times[alert_key] = now
            return True
        return False

    def _emit(self, text: str, alert_type: str = "info", priority: str = "normal", speak: bool = True):
        print(f"[Sentinel] ⚡ Proactive Event [{alert_type.upper()}]: {text}")
        if self.on_proactive_alert:
            self.on_proactive_alert({
                "text": text,
                "type": alert_type,
                "priority": priority,
                "speak": speak,
                "timestamp": time.time()
            })

    def _get_active_window_title(self) -> str:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                return buff.value.strip()
        except Exception:
            pass
        return ""

    def _check_power_and_battery(self):
        bat = psutil.sensors_battery()
        if bat is None:
            return

        pct = int(bat.percent)
        is_plugged = bat.power_plugged

        # Initialize baseline state on boot without firing
        if self.last_plugged_state is None:
            self.last_plugged_state = is_plugged
            return

        # 1. AC Power Disconnect Event
        if self.last_plugged_state is True and is_plugged is False:
            self.last_plugged_state = False
            self._emit(
                f"Sir, main power disconnected. Operating on battery at {pct}%.",
                alert_type="power",
                priority="high",
                speak=True
            )

        # 2. AC Power Reconnect Event
        elif self.last_plugged_state is False and is_plugged is True:
            self.last_plugged_state = True
            self._emit(
                f"AC power re-established, Sir. Battery charging at {pct}%.",
                alert_type="power",
                priority="normal",
                speak=True
            )

        # 3. Critical Low Battery Warning (< 12%)
        if not is_plugged and pct <= 12:
            if self._can_fire("bat_critical", cooldown_seconds=300): # every 5 mins
                self._emit(
                    f"Critical power warning, Sir. Battery reserves at {pct}%. System shutdown is imminent without power.",
                    alert_type="battery",
                    priority="critical",
                    speak=True
                )

        # 4. Low Battery Warning (13% - 20%)
        elif not is_plugged and pct <= 20:
            if self._can_fire("bat_low", cooldown_seconds=600): # every 10 mins
                self._emit(
                    f"Warning, Sir. Battery reserves have dropped to {pct}%. Connecting your charger is advised.",
                    alert_type="battery",
                    priority="high",
                    speak=True
                )

        # 5. Full Charge Notification (100% plugged in)
        elif is_plugged and pct >= 99:
            if self._can_fire("bat_full", cooldown_seconds=3600): # once an hour
                self._emit(
                    "Battery fully replenished at 100%, Sir. You may disconnect AC power to preserve cell longevity.",
                    alert_type="battery",
                    priority="normal",
                    speak=True
                )

    def _check_hardware_stress(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()

        # Track sustained CPU spikes
        if cpu >= 90.0:
            self.sustained_high_cpu_count += 1
            if self.sustained_high_cpu_count >= 4: # ~12 seconds sustained
                if self._can_fire("cpu_spike", cooldown_seconds=900): # every 15 mins
                    self._emit(
                        f"Sir, sustained CPU spike detected at {cpu:.0f}%. Heavy computational workload is active.",
                        alert_type="hardware",
                        priority="high",
                        speak=True
                    )
        else:
            self.sustained_high_cpu_count = 0

        # Memory pressure alert (> 93%)
        if mem.percent >= 93.0:
            if self._can_fire("ram_pressure", cooldown_seconds=900):
                used_gb = round(mem.used / (1024 ** 3), 1)
                total_gb = round(mem.total / (1024 ** 3), 1)
                self._emit(
                    f"Memory pressure elevated, Sir. System is utilizing {used_gb} of {total_gb} gigabytes ({mem.percent}%).",
                    alert_type="hardware",
                    priority="high",
                    speak=True
                )

    def _check_focus_environment(self):
        title = self._get_active_window_title().lower()
        if not title:
            return

        # Detect focus mode transitions
        current_mode = None
        if any(k in title for k in ["visual studio code", "android studio", "pycharm", "intellij", "sublime", ".py", ".ts", ".js"]):
            current_mode = "Coding"
        elif any(k in title for k in ["steam", "epic games", "valorant", "cyberpunk", "minecraft"]):
            current_mode = "Gaming"

        if current_mode and current_mode != self.last_foreground_app:
            self.last_foreground_app = current_mode
            if self._can_fire(f"mode_{current_mode}", cooldown_seconds=1800):
                self._emit(
                    f"Focus transition detected: {current_mode} environment active, Sir.",
                    alert_type="mode",
                    priority="info",
                    speak=False # Visual toast on screen without interrupting flow
                )

    def _sentinel_loop(self):
        # Initial settle delay
        time.sleep(3.0)
        while self.is_running:
            try:
                self._check_power_and_battery()
                self._check_hardware_stress()
                self._check_focus_environment()
            except Exception as e:
                print(f"[Sentinel] Inspection error: {e}")
            time.sleep(2.5)
