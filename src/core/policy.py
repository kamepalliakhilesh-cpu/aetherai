"""
Aether Security & Tool Policy Guard.
Ported & adapted from J.A.R.V.I.S. (jarvis-main) policy.mjs & net.mjs

Enforces:
1. SSRF Guard: Blocks outbound agent requests to private LAN, localhost, or cloud metadata endpoints.
2. Credential Isolation: Prohibits reads or modifications to sensitive credential files (.env, .ssh, private keys).
"""

import ipaddress
import socket
import urllib.parse
from pathlib import Path
from typing import Tuple

PROTECTED_NAMES = {
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_ed25519", "id_ecdsa",
    "known_hosts", "authorized_keys"
}

PROTECTED_DIRS = {
    ".ssh", ".gnupg", ".aws", ".azure", ".claude"
}

def is_private_ip(ip_str: str) -> bool:
    """Checks if an IP address is private, loopback, link-local, or multicast (with RFC 6052 NAT64 awareness)"""
    try:
        ip = ipaddress.ip_address(ip_str)
        # Handle RFC 6052 NAT64 Well-Known Prefix (64:ff9b::/96)
        if ip.version == 6 and ip in ipaddress.ip_network("64:ff9b::/96"):
            embedded_v4 = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
            return (
                embedded_v4.is_private or
                embedded_v4.is_loopback or
                embedded_v4.is_link_local or
                embedded_v4.is_multicast or
                embedded_v4.is_reserved or
                embedded_v4.is_unspecified
            )

        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_reserved or
            ip.is_unspecified
        )
    except ValueError:
        return False

def vet_target_url(target_url: str) -> Tuple[bool, str]:
    """
    SSRF Guard: Verifies that a web request target does not resolve to
    localhost, 127.0.0.1, AWS/GCP 169.254.169.254 metadata, or private LAN.
    """
    try:
        parsed = urllib.parse.urlparse(target_url)
        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            return False, f"Prohibited scheme: '{scheme}'. Only HTTP and HTTPS are permitted."

        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL target: missing hostname."

        # Immediate string checks
        lower_host = hostname.lower()
        if lower_host in ("localhost", "0.0.0.0", "127.0.0.1", "::1", "metadata.google.internal"):
            return False, f"SSRF Protection: Access to '{hostname}' is blocked."

        # DNS resolution check against private/cloud metadata ranges
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_addr = item[4][0]
                if is_private_ip(ip_addr):
                    return False, f"SSRF Protection: Target '{hostname}' resolves to restricted IP {ip_addr}."
        except socket.gaierror:
            # Domain not resolving, let caller fail with standard network error
            pass

        return True, "Target verified safe."
    except Exception as e:
        return False, f"URL security verification failed: {e}"

def vet_file_path(file_path: str, allow_read: bool = True) -> Tuple[bool, str]:
    """
    Credential Isolation: Blocks tool access to sensitive keys, tokens, and SSH stores.
    """
    try:
        p = Path(file_path).resolve()
        name = p.name.lower()
        parts = [part.lower() for part in p.parts]

        # Check protected filenames
        if name in PROTECTED_NAMES:
            return False, f"Security Policy: Access to credential file '{name}' is restricted."

        # Check protected directories
        for pdir in PROTECTED_DIRS:
            if pdir in parts:
                return False, f"Security Policy: Access to sensitive folder '{pdir}' is restricted."

        return True, "Path verified safe."
    except Exception as e:
        return False, f"Path security verification failed: {e}"
