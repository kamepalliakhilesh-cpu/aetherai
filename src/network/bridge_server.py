import asyncio
import base64
import datetime
import hashlib
import io
import json
import logging
import os
import random
import secrets
import socket
import ssl
import string
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("AetherBridgeServer")

# Allowlisted actions permitted for remote execution
SAFE_REMOTE_ACTIONS = {
    "lock", "pc_lock",
    "mute", "pc_mute",
    "unmute", "pc_unmute",
    "volume", "pc_set_volume",
    "volume_up", "pc_volume_up",
    "volume_down", "pc_volume_down",
    "screenshot", "pc_screenshot",
    "launch_app", "pc_launch_app",
    "type_text", "pc_type_text",
    "voice_command", "pc_voice_command",
    "get_battery", "get_status", "get_telemetry",
    "media_play_pause", "media_toggle", "media_play", "media_pause",
    "media_next", "next_track", "media_prev", "prev_track", "control_media"
}

# High-impact / restricted actions requiring explicit workstation confirmation
RESTRICTED_REMOTE_ACTIONS = {
    "sleep", "pc_sleep",
    "shutdown", "pc_shutdown",
    "restart", "pc_restart",
}

def _encrypt_secret(secret_str: str) -> str:
    """Encrypt secret string using Windows DPAPI (CryptProtectData)."""
    if not secret_str:
        return ""
    try:
        import win32crypt
        enc_bytes = win32crypt.CryptProtectData(
            secret_str.encode("utf-8"),
            "AetherBridgeSecret",
            None, None, None, 0
        )
        return "dpapi:" + base64.b64encode(enc_bytes).decode("ascii")
    except Exception as e:
        logger.debug(f"DPAPI protect fallback: {e}")
        return secret_str

def _decrypt_secret(raw_val: str) -> str:
    """Decrypt secret string using Windows DPAPI (CryptUnprotectData)."""
    if not raw_val:
        return ""
    if raw_val.startswith("dpapi:"):
        try:
            import win32crypt
            b64_str = raw_val[len("dpapi:"):]
            enc_bytes = base64.b64decode(b64_str.encode("ascii"))
            dec_bytes = win32crypt.CryptUnprotectData(enc_bytes, None, None, None, 0)[1]
            return dec_bytes.decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to unprotect DPAPI secret: {e}")
            return ""
    return raw_val

def get_local_ip() -> str:
    """Detect the machine's primary local LAN IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def ensure_tls_certificates(cert_dir: str) -> Tuple[str, str, str]:
    """
    Ensures self-signed X.509 TLS certificate and private key exist for WSS encryption.
    Returns (cert_path, key_path, sha256_fingerprint).
    """
    os.makedirs(cert_dir, exist_ok=True)
    cert_path = os.path.join(cert_dir, "aether_bridge_cert.pem")
    key_path = os.path.join(cert_dir, "aether_bridge_key.pem")

    if os.path.exists(cert_path) and os.path.exists(key_path):
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import serialization
            with open(cert_path, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
            der = cert.public_bytes(serialization.Encoding.DER)
            fp = hashlib.sha256(der).hexdigest().upper()
            fp_formatted = ":".join(fp[i:i+2] for i in range(0, len(fp), 2))
            return cert_path, key_path, fp_formatted
        except Exception as e:
            logger.warning(f"Re-generating TLS certificate due to read error: {e}")

    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "AetherBridge"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Aether Systems")
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650)
    ).sign(key, hashes.SHA256())

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    der = cert.public_bytes(serialization.Encoding.DER)
    fp = hashlib.sha256(der).hexdigest().upper()
    fp_formatted = ":".join(fp[i:i+2] for i in range(0, len(fp), 2))
    return cert_path, key_path, fp_formatted


def generate_qr_data_url(data_str: str) -> str:
    """Generate a high-contrast base64 PNG Data URL QR code."""
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(data_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#09090b", back_color="#ffffff")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to generate QR data URL: {e}")
        return ""


class AetherDiscoveryServer:
    """
    Lightweight UDP discovery service on port 8767:
    - Listens for probe '{"type": "aether_discover"}' and replies with PC connection payload.
    - Broadcasts periodic beacon every 5 seconds to local subnet so mobile companions auto-detect PC.
    """
    def __init__(self, bridge_server: "AetherBridgeServer", discovery_port: int = 8767):
        self.bridge = bridge_server
        self.discovery_port = discovery_port
        self.sock: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def get_beacon_payload(self) -> bytes:
        payload = {
            "type": "aether_beacon",
            "v": 1,
            "pc_name": socket.gethostname(),
            "host": self.bridge.local_ip,
            "port": self.bridge.port,
            "tls": self.bridge.use_tls,
            "fp": self.bridge.cert_fingerprint,
            "timestamp": time.time()
        }
        return json.dumps(payload).encode("utf-8")

    def _run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("0.0.0.0", self.discovery_port))
            self.sock.settimeout(2.0)
            logger.info(f"Aether UDP Discovery beacon active on port {self.discovery_port}")
        except Exception as e:
            logger.warning(f"Could not bind UDP discovery socket on port {self.discovery_port}: {e}")
            return

        last_beacon_time = 0
        while self.running:
            now = time.time()
            if now - last_beacon_time >= 5.0:
                try:
                    beacon_data = self.get_beacon_payload()
                    self.sock.sendto(beacon_data, ("255.255.255.255", self.discovery_port))
                    last_beacon_time = now
                except Exception:
                    pass

            try:
                data, addr = self.sock.recvfrom(2048)
                msg = json.loads(data.decode("utf-8", errors="ignore"))
                if msg.get("type") in ("aether_discover", "probe", "ping"):
                    beacon_data = self.get_beacon_payload()
                    self.sock.sendto(beacon_data, addr)
            except (socket.timeout, TimeoutError):
                continue
            except Exception:
                pass

        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, name="AetherDiscoveryThread", daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


def configure_windows_startup(enable: bool = True) -> Dict[str, Any]:
    """Configures automatic start on Windows login via Startup folder."""
    import sys
    startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
    vbs_path = os.path.join(startup_dir, "AetherBridge.vbs")

    if not enable:
        if os.path.exists(vbs_path):
            try:
                os.remove(vbs_path)
                return {"success": True, "message": "Startup auto-launch disabled"}
            except Exception as e:
                return {"success": False, "message": f"Failed to remove startup script: {e}"}
        return {"success": True, "message": "Startup auto-launch already disabled"}

    try:
        current_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        python_exe = sys.executable
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw_exe):
            pythonw_exe = python_exe

        app_py = os.path.join(current_dir, "src", "app.py")
        vbs_content = (
            f'Set WshShell = CreateObject("WScript.Shell")\r\n'
            f'WshShell.CurrentDirectory = "{current_dir}"\r\n'
            f'WshShell.Run """{pythonw_exe}"" ""{app_py}""", 0, False\r\n'
        )
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        return {"success": True, "message": f"Startup shortcut configured: {vbs_path}"}
    except Exception as e:
        return {"success": False, "message": f"Failed to configure startup: {e}"}


class AetherBridgeServer:
    """
    Hardened Bi-Directional WebSocket Bridge connecting Aether.ai (Android)
    with Aether.ai-PC (Laptop/Windows) with Rotating Session Secrets,
    Self-Signed TLS (WSS), Action Allowlisting, and QR-Code Pairing.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8766,
        config_dir: str = "data",
        use_tls: Optional[bool] = None
    ):
        self.host = host
        self.port = port
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "bridge_config.json")
        self.cert_dir = os.path.join(config_dir, "certs")
        self.local_ip = get_local_ip()
        self.explicit_tls = use_tls
        self.use_tls = False

        # Callbacks for UI and Brain integration
        self.on_telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_notification_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_status_change_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.action_executor: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None

        # Connected clients: websocket -> client_info
        self.clients: Dict[Any, Dict[str, Any]] = {}
        self._lock = threading.Lock()

        # Telemetry cache
        self.mobile_telemetry: Dict[str, Any] = {
            "connected": False,
            "device_name": None,
            "battery": None,
            "is_charging": False,
            "wifi_ssid": None,
            "last_seen": 0,
        }

        # Lifecycle
        self.server = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.is_running = False

        # Load/generate TLS certificates
        try:
            self.cert_path, self.key_path, self.cert_fingerprint = ensure_tls_certificates(self.cert_dir)
            self.use_tls = bool(self.cert_path and self.key_path)
        except Exception as ex:
            logger.warning(f"TLS setup bypassed: {ex}")
            self.cert_path = self.key_path = self.cert_fingerprint = ""
            self.use_tls = False

        if self.explicit_tls is not None:
            self.use_tls = bool(self.explicit_tls and self.cert_path)

        self.discovery = AetherDiscoveryServer(self)
        self._load_config()

    def _generate_pairing_code(self) -> str:
        chars = string.ascii_uppercase + string.digits
        return "".join(random.choice(chars) for _ in range(6))

    def _load_config(self):
        os.makedirs(self.config_dir, exist_ok=True)
        self.session_secrets: Dict[str, Dict[str, Any]] = {}
        self.pairing_code = self._generate_pairing_code()

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.pairing_code = data.get("pairing_code") or self.pairing_code
                    raw_secrets = data.get("session_secrets", {})
                    if self.explicit_tls is not None:
                        self.use_tls = bool(self.explicit_tls and self.cert_path)
                    elif "use_tls" in data:
                        self.use_tls = bool(data.get("use_tls")) and bool(self.cert_path)
                    
                    # Decrypt DPAPI protected secrets and clean expired (>30 days)
                    now = time.time()
                    self.session_secrets = {}
                    for k, v in raw_secrets.items():
                        if isinstance(v, dict) and v.get("expires_at", 0) > now:
                            sec_copy = dict(v)
                            sec_copy["secret"] = _decrypt_secret(v.get("secret", ""))
                            self.session_secrets[k] = sec_copy
                    return
            except Exception as e:
                logger.warning(f"Failed to read bridge config: {e}")

        self._save_config()

    def _save_config(self):
        try:
            # Encrypt session secrets with DPAPI before writing to disk
            protected_secrets = {}
            for k, v in self.session_secrets.items():
                sec_copy = dict(v)
                sec_copy["secret"] = _encrypt_secret(v.get("secret", ""))
                protected_secrets[k] = sec_copy

            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({
                    "pairing_code": self.pairing_code,
                    "session_secrets": protected_secrets,
                    "port": self.port,
                    "use_tls": self.use_tls,
                    "cert_fingerprint": self.cert_fingerprint
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write bridge config: {e}")

    def get_pairing_payload(self) -> Dict[str, Any]:
        """Structured payload encoded in the QR code."""
        protocol = "wss" if self.use_tls else "ws"
        return {
            "v": 1,
            "host": self.local_ip,
            "port": self.port,
            "code": self.pairing_code,
            "tls": self.use_tls,
            "fp": self.cert_fingerprint,
            "url": f"{protocol}://{self.local_ip}:{self.port}"
        }

    def get_connection_info(self) -> Dict[str, Any]:
        """Return pairing information and QR code for UI display."""
        payload = self.get_pairing_payload()
        qr_string = json.dumps(payload)
        qr_data_url = generate_qr_data_url(qr_string)

        return {
            "ip": self.local_ip,
            "port": self.port,
            "ws_url": payload["url"],
            "pairing_code": self.pairing_code,
            "use_tls": self.use_tls,
            "cert_fingerprint": self.cert_fingerprint,
            "qr_payload": payload,
            "qr_data_url": qr_data_url,
            "is_running": self.is_running,
            "connected_devices": len(self.clients),
            "mobile_telemetry": self.mobile_telemetry,
        }

    def rotate_pairing_code(self) -> Dict[str, Any]:
        """Manually rotate the one-time pairing code and return fresh connection info."""
        self.pairing_code = self._generate_pairing_code()
        self._save_config()
        logger.info(f"Rotated Aether pairing code to: {self.pairing_code}")
        return self.get_connection_info()

    async def _handle_connection(self, websocket):
        client_info = None
        try:
            async for raw_message in websocket:
                try:
                    msg = json.loads(raw_message)
                except Exception:
                    continue

                msg_type = msg.get("type")

                # Unified Handshake (Supports pairing token, session secret, or both)
                if msg_type in ("auth", "reauth"):
                    token = msg.get("token", "").strip().upper()
                    provided_secret = msg.get("session_secret", "").strip()
                    device_id = msg.get("device_id", "unknown_device")
                    device_name = msg.get("device_name") or "Aether Mobile"

                    device_record = self.session_secrets.get(device_id) or next(
                        (v for k, v in self.session_secrets.items() if k.lower() == device_id.lower()),
                        None
                    )

                    is_valid_secret = (
                        device_record is not None and
                        bool(provided_secret) and
                        secrets.compare_digest(device_record.get("secret", ""), provided_secret) and
                        device_record.get("expires_at", 0) > time.time()
                    )

                    is_valid_token = (
                        bool(token) and
                        bool(self.pairing_code) and
                        token == self.pairing_code.strip().upper()
                    )

                    if is_valid_secret or is_valid_token:
                        if not is_valid_secret or not device_record:
                            session_secret = secrets.token_hex(32)
                            expires_at = time.time() + (86400 * 30) # 30 days valid
                            self.session_secrets[device_id] = {
                                "secret": session_secret,
                                "device_name": device_name,
                                "created_at": time.time(),
                                "expires_at": expires_at
                            }
                            # Keep pairing code stable so the on-screen QR code remains valid!
                            self._save_config()
                        else:
                            session_secret = device_record.get("secret", "")
                            expires_at = device_record.get("expires_at", time.time() + (86400 * 30))
                            if device_name:
                                device_record["device_name"] = device_name
                                self.session_secrets[device_id] = device_record

                        client_info = {
                            "device_id": device_id,
                            "device_name": device_name,
                            "authenticated": True,
                            "connected_at": time.time(),
                        }
                        with self._lock:
                            self.clients[websocket] = client_info
                            self.mobile_telemetry["connected"] = True
                            self.mobile_telemetry["device_name"] = device_name
                            self.mobile_telemetry["last_seen"] = time.time()

                        ack = {
                            "type": "auth_ack",
                            "success": True,
                            "session_secret": session_secret,
                            "expires_at": expires_at,
                            "pc_name": socket.gethostname(),
                            "message": f"Synaptic link established with {socket.gethostname()}, Sir.",
                        }
                        await websocket.send(json.dumps(ack))

                        if self.on_status_change_callback:
                            try:
                                self.on_status_change_callback(self.mobile_telemetry)
                            except Exception as ce:
                                logger.debug(f"Status callback notice: {ce}")
                    else:
                        reject = {
                            "type": "auth_ack",
                            "success": False,
                            "message": "Invalid pairing token or expired session secret.",
                        }
                        await websocket.send(json.dumps(reject))
                        await websocket.close(1008, "Authentication failed")
                        return

                # All other messages require authentication
                elif websocket in self.clients:
                    await self._process_authenticated_message(websocket, msg)

        except Exception as e:
            logger.debug(f"Bridge connection closed: {e}")
        finally:
            with self._lock:
                if websocket in self.clients:
                    del self.clients[websocket]
                if not self.clients:
                    self.mobile_telemetry["connected"] = False
                    if self.on_status_change_callback:
                        self.on_status_change_callback(self.mobile_telemetry)

    async def _process_authenticated_message(self, websocket, msg: Dict[str, Any]):
        msg_type = msg.get("type")
        self.mobile_telemetry["last_seen"] = time.time()

        if msg_type == "telemetry":
            battery = msg.get("battery")
            is_charging = msg.get("is_charging", False)
            wifi_ssid = msg.get("wifi_ssid")

            self.mobile_telemetry["battery"] = battery
            self.mobile_telemetry["is_charging"] = is_charging
            self.mobile_telemetry["wifi_ssid"] = wifi_ssid

            if self.on_telemetry_callback:
                self.on_telemetry_callback(self.mobile_telemetry)

        elif msg_type == "notification":
            notif_data = {
                "package": msg.get("package", ""),
                "app_name": msg.get("app_name", "Android"),
                "title": msg.get("title", ""),
                "text": msg.get("text", ""),
                "timestamp": msg.get("timestamp", time.time()),
            }
            if self.on_notification_callback:
                self.on_notification_callback(notif_data)

        elif msg_type == "clipboard_sync":
            text = msg.get("text", "")
            if text:
                try:
                    import pyperclip
                    pyperclip.copy(text)
                except Exception as e:
                    logger.warning(f"Failed to set clipboard: {e}")

        elif msg_type == "memory_sync":
            fact = msg.get("fact", "")
            if fact:
                try:
                    from src.memory.second_brain import SecondBrain
                    brain = SecondBrain()
                    brain.store.save_fact("mobile_sync", "phone", fact)
                except Exception as e:
                    logger.warning(f"Failed to sync memory: {e}")

        elif msg_type == "pc_action":
            action = msg.get("action", "")
            params = msg.get("params", {})
            request_id = msg.get("request_id")

            # 1. Action Allowlist Enforcement
            if action not in SAFE_REMOTE_ACTIONS and action not in RESTRICTED_REMOTE_ACTIONS:
                err_resp = {
                    "type": "action_result",
                    "request_id": request_id,
                    "action": action,
                    "success": False,
                    "message": f"Action '{action}' is rejected: Not in remote execution allowlist."
                }
                await websocket.send(json.dumps(err_resp))
                return

            # 2. Confirmation Check for Restricted Commands
            if action in RESTRICTED_REMOTE_ACTIONS:
                try:
                    from core.confirm import request_and_wait as confirm_request_and_wait
                    
                    # Request confirmation and wait for user response
                    def _run_action():
                        if self.action_executor:
                            return self.action_executor(action, params)
                        return {"success": False, "message": "No executor registered"}
                    
                    accepted, msg = confirm_request_and_wait(
                        key=f"remote_{action}",
                        title=f"Remote {action.replace('_', ' ').title()}",
                        detail=f"Mobile device requests to execute {action}. Allow?",
                        run=_run_action,
                        timeout=30
                    )
                    
                    if not accepted:
                        err_resp = {
                            "type": "action_result",
                            "request_id": request_id,
                            "action": action,
                            "success": False,
                            "message": msg
                        }
                        await websocket.send(json.dumps(err_resp))
                        return
                    
                    # Action was executed by the confirmation system, send success
                    response = {
                        "type": "action_result",
                        "request_id": request_id,
                        "action": action,
                        "success": True,
                        "message": msg
                    }
                    await websocket.send(json.dumps(response))
                    return
                    
                except Exception as e:
                    logger.warning(f"Confirmation gate check error: {e}")
                    err_resp = {
                        "type": "action_result",
                        "request_id": request_id,
                        "action": action,
                        "success": False,
                        "message": f"Confirmation system error: {e}"
                    }
                    await websocket.send(json.dumps(err_resp))
                    return

            # Safe actions execute directly
            result = {"success": False, "message": "No executor registered"}
            if self.action_executor:
                try:
                    result = self.action_executor(action, params)
                except Exception as ex:
                    result = {"success": False, "message": str(ex)}

            response = {
                "type": "action_result",
                "request_id": request_id,
                "action": action,
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "data": result.get("data", {}),
            }
            await websocket.send(json.dumps(response))

    def broadcast_to_mobile(self, message: Dict[str, Any]):
        """Thread-safe broadcast of JSON message to all connected Android companions."""
        if not self.loop or not self.clients:
            return

        payload = json.dumps(message)

        async def _send_all():
            with self._lock:
                sockets = list(self.clients.keys())
            for ws in sockets:
                try:
                    await ws.send(payload)
                except Exception:
                    pass

        asyncio.run_coroutine_threadsafe(_send_all(), self.loop)

    def send_phone_command(self, action: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Send a remote action request to the phone."""
        if not self.mobile_telemetry["connected"]:
            return False

        message = {
            "type": "phone_action",
            "action": action,
            "params": params or {},
            "timestamp": time.time(),
        }
        self.broadcast_to_mobile(message)
        return True

    def sync_clipboard_to_mobile(self, text: str):
        """Send PC clipboard content to mobile."""
        self.broadcast_to_mobile({
            "type": "clipboard_sync",
            "text": text,
            "timestamp": time.time(),
        })

    def _run_server(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Build SSL Context if TLS enabled
        ssl_ctx = None
        if self.use_tls and self.cert_path and self.key_path:
            try:
                ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_ctx.load_cert_chain(self.cert_path, self.key_path)
            except Exception as e:
                logger.error(f"Failed to initialize SSLContext for WSS: {e}. Falling back to plain WS.")
                ssl_ctx = None
                self.use_tls = False

        async def _main():
            import websockets
            protocol_name = "wss" if ssl_ctx else "ws"
            server_kwargs = {
                "max_size": 64 * 1024,
                "ping_interval": 20,
                "ping_timeout": 20,
            }
            if ssl_ctx:
                server_kwargs["ssl"] = ssl_ctx

            if hasattr(websockets, "serve"):
                server_coro = websockets.serve(self._handle_connection, self.host, self.port, **server_kwargs)
            else:
                from websockets.asyncio.server import serve
                server_coro = serve(self._handle_connection, self.host, self.port, **server_kwargs)

            self.server = await server_coro
            self.is_running = True
            logger.info(f"Aether Bridge Server listening on {protocol_name}://{self.local_ip}:{self.port}")
            await asyncio.Future()

        try:
            self.loop.run_until_complete(_main())
        except Exception as e:
            logger.debug(f"Bridge server terminated: {e}")
        finally:
            self.is_running = False

    def start(self):
        """Start the bridge server in a background daemon thread."""
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run_server, name="AetherBridgeThread", daemon=True)
        self.thread.start()
        self.discovery.start()
        time.sleep(0.1)

    def stop(self):
        """Stop the bridge server cleanly."""
        self.discovery.stop()
        if self.loop and self.server:
            try:
                self.server.close()
                self.loop.call_soon_threadsafe(self.loop.stop)
            except Exception:
                pass
        self.is_running = False


# Global singleton instance
_bridge_instance: Optional[AetherBridgeServer] = None

def get_bridge_server() -> AetherBridgeServer:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = AetherBridgeServer()
    return _bridge_instance
