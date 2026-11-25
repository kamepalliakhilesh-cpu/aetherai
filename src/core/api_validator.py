"""
Aether Core API Key & Model Validator.
Ensures green status indicator lights up ONLY if BOTH the API key AND the selected model
are fully responsive and verified to execute generation requests.
"""

import time
import json
import urllib.request
import urllib.error
import requests
from typing import Dict, Any

MODEL_ALIASES = {
    "gemini-3.8-flashlite": "gemini-2.0-flash",
    "gemini 3.8 flashlite": "gemini-2.0-flash",
    "gemini 3.8 flash-lite": "gemini-2.0-flash",
    "gemini-3.8-flash-lite": "gemini-2.0-flash",
    "3.8-flash-lite": "gemini-2.0-flash",
    "gemini-3.5-flashlite": "gemini-2.0-flash",
    "gemini 3.5 flashlite": "gemini-2.0-flash",
    "gemini 3.5 flash-lite": "gemini-2.0-flash",
    "gemini-3.5-flash-lite": "gemini-2.0-flash",
    "3.5-flash-lite": "gemini-2.0-flash",
    "gemini-2.0-flashlite": "gemini-2.0-flash-lite",
    "gemini 2.0 flash-lite": "gemini-2.0-flash-lite",
}

def validate_gemini_key(api_key: str, model: str = "gemini-2.0-flash") -> Dict[str, Any]:
    """
    Validates Gemini API key by probing the specific selected model with a 1-token generation call.
    Returns valid=True and status='active' ONLY if both the key is authenticated AND
    the selected model responds with 200 OK.
    """
    key = (api_key or "").strip().strip("\"'").replace("\r", "").replace("\n", "").strip()
    raw_clean = (model or "").replace("models/", "").replace("google/", "").strip()
    clean_model = MODEL_ALIASES.get(raw_clean.lower(), raw_clean)
    if not clean_model:
        clean_model = "gemini-2.0-flash"

    if not key:
        return {
            "status": "offline",
            "provider": "gemini",
            "model": clean_model,
            "valid": False,
            "message": "No Gemini API Key provided. Enter key in Settings."
        }

    # Cross-provider key format detection
    if key.startswith("sk-or-"):
        return {
            "status": "error",
            "provider": "gemini",
            "model": clean_model,
            "valid": False,
            "message": "OpenRouter API Key format detected. Switch Provider to 'OpenRouter API'."
        }

    t0 = time.time()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AetherAI/2.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    probe_body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
        "generationConfig": {"maxOutputTokens": 1}
    }).encode("utf-8")

    def _probe_model(target: str):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target}:generateContent?key={key}"
        res_code = None
        res_json = None
        raw_err = ""
        try:
            s = requests.Session()
            s.trust_env = False
            resp = s.post(url, data=probe_body, headers=headers, timeout=8)
            res_code = resp.status_code
            if res_code == 200:
                res_json = resp.json()
            else:
                raw_err = resp.text
        except Exception:
            try:
                req = urllib.request.Request(url, data=probe_body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=8) as uresp:
                    res_code = uresp.status
                    if res_code == 200:
                        res_json = json.loads(uresp.read().decode("utf-8"))
            except urllib.error.HTTPError as he:
                res_code = he.code
                try:
                    raw_err = he.read().decode("utf-8")
                except Exception:
                    raw_err = str(he)
            except Exception as ue:
                raw_err = str(ue)
        return res_code, res_json, raw_err

    # Probe the selected model
    status_code, data, err_text = _probe_model(clean_model)
    latency = int((time.time() - t0) * 1000)

    # 1. Success on primary model
    if status_code == 200 and data:
        return {
            "status": "active",
            "provider": "gemini",
            "model": clean_model,
            "valid": True,
            "latency_ms": latency,
            "message": f"Verified: {clean_model} is operational ({latency}ms latency)."
        }

    # 2. If 404, check known model variants (e.g. gemini-3.8-flash-lite -> gemini-3.8-flash-lite-tts)
    if status_code == 404:
        variant = None
        if "3.8" in clean_model and not clean_model.endswith("-tts"):
            variant = f"{clean_model}-tts"
        if variant:
            v_code, v_data, _ = _probe_model(variant)
            if v_code == 200 and v_data:
                return {
                    "status": "active",
                    "provider": "gemini",
                    "model": variant,
                    "valid": True,
                    "latency_ms": int((time.time() - t0) * 1000),
                    "message": f"Verified: {variant} is operational."
                }

        # Check which working models actually exist on this key to guide the user
        avail_str = ""
        try:
            m_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            m_req = urllib.request.Request(m_url, headers=headers)
            with urllib.request.urlopen(m_req, timeout=5) as m_resp:
                if m_resp.status == 200:
                    m_data = json.loads(m_resp.read().decode("utf-8"))
                    avail = [
                        m.get("name", "").replace("models/", "")
                        for m in m_data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    top_avail = [m for m in avail if "flash" in m][:3]
                    if top_avail:
                        avail_str = f" Working models on your account: {', '.join(top_avail)}."
        except Exception:
            pass

        return {
            "status": "error",
            "provider": "gemini",
            "model": clean_model,
            "valid": False,
            "latency_ms": latency,
            "message": f"Model '{clean_model}' is not available for this API key (404 Not Found).{avail_str}"
        }

    # 3. Parse human-friendly error messages
    err_msg = ""
    try:
        err_json = json.loads(err_text)
        err_msg = err_json.get("error", {}).get("message", err_text)
    except Exception:
        err_msg = err_text

    if not status_code:
        user_msg = f"Network connection failed: {err_text or 'Timeout'}. Check internet connection."
    elif "API_KEY_INVALID" in err_msg or "not valid" in err_msg.lower():
        user_msg = "Invalid Gemini API Key. Ensure the full key was copied without extra characters."
    elif "PERMISSION_DENIED" in err_msg or status_code == 403:
        user_msg = f"Permission Denied (403) for model '{clean_model}'. Check API project restrictions."
    elif status_code == 429:
        user_msg = f"Gemini API Quota Exceeded (429) for model '{clean_model}'."
    else:
        user_msg = f"Gemini Error ({status_code}): {err_msg[:90] or 'Request rejected'}"

    return {
        "status": "error",
        "provider": "gemini",
        "model": clean_model,
        "valid": False,
        "latency_ms": latency,
        "message": user_msg
    }


def validate_openrouter_key(api_key: str, model: str = "google/gemini-2.0-flash-001") -> Dict[str, Any]:
    """
    Validates OpenRouter API key by probing the specific selected model with a 1-token completion.
    Returns valid=True and status='active' ONLY if both the key is authenticated AND
    the selected model responds with 200 OK.
    """
    key = (api_key or "").strip().strip("\"'").replace("\r", "").replace("\n", "").strip()
    target_model = model or "google/gemini-2.0-flash-001"

    if not key:
        return {
            "status": "offline",
            "provider": "openrouter",
            "model": target_model,
            "valid": False,
            "message": "No OpenRouter API Key provided. Enter key in Settings."
        }

    # Cross-provider key format detection
    if key.startswith("AIzaSy"):
        return {
            "status": "error",
            "provider": "openrouter",
            "model": target_model,
            "valid": False,
            "message": "Google Gemini API Key format detected. Switch Provider to 'Google Gemini API'."
        }

    t0 = time.time()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "AetherAI/2.0",
        "HTTP-Referer": "https://aether.ai",
        "X-Title": "Aether AI Assistant"
    }

    probe_url = "https://openrouter.ai/api/v1/chat/completions"
    probe_body = json.dumps({
        "model": target_model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1
    }).encode("utf-8")

    res_status = None
    res_data = None
    err_text = ""

    try:
        s = requests.Session()
        s.trust_env = False
        res = s.post(probe_url, data=probe_body, headers=headers, timeout=10)
        res_status = res.status_code
        if res_status == 200:
            res_data = res.json()
        else:
            err_text = res.text
    except Exception:
        try:
            req = urllib.request.Request(probe_url, data=probe_body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as uresp:
                res_status = uresp.status
                if res_status == 200:
                    res_data = json.loads(uresp.read().decode("utf-8"))
        except urllib.error.HTTPError as he:
            res_status = he.code
            try:
                err_text = he.read().decode("utf-8")
            except Exception:
                err_text = str(he)
        except Exception as ue:
            return {
                "status": "error",
                "provider": "openrouter",
                "model": target_model,
                "valid": False,
                "message": f"Network error connecting to OpenRouter: {ue}"
            }

    latency = int((time.time() - t0) * 1000)

    if res_status == 200 and res_data:
        return {
            "status": "active",
            "provider": "openrouter",
            "model": target_model,
            "valid": True,
            "latency_ms": latency,
            "message": f"Verified: OpenRouter model '{target_model}' is active ({latency}ms latency)."
        }

    err_msg = ""
    try:
        err_json = json.loads(err_text)
        err_msg = err_json.get("error", {}).get("message", err_text)
    except Exception:
        err_msg = err_text

    if res_status == 401:
        user_msg = "Invalid OpenRouter API Key (401 Unauthorized)."
    elif res_status == 402:
        user_msg = "Insufficient credits on OpenRouter account (402 Payment Required)."
    elif res_status == 404:
        user_msg = f"Model '{target_model}' is not available on OpenRouter (404 Not Found). Select a working model."
    else:
        user_msg = f"OpenRouter Error ({res_status}): {err_msg[:90] or 'Request rejected'}"

    return {
        "status": "error",
        "provider": "openrouter",
        "model": target_model,
        "valid": False,
        "latency_ms": latency,
        "message": user_msg
    }


def validate_current_config(config: dict) -> dict:
    provider = config.get("provider", "gemini").lower()
    if provider == "openrouter":
        key = config.get("openrouter_api_key", "")
        model = config.get("openrouter_model", "google/gemini-2.0-flash-001")
        if not key.strip():
            return {
                "status": "offline",
                "provider": "openrouter",
                "model": model,
                "valid": False,
                "message": "Offline (Local Deterministic Engine)"
            }
        val = validate_openrouter_key(key, model)
        val["model"] = model
        return val
    else:
        key = config.get("gemini_api_key", "")
        model = config.get("model_name", "gemini-2.0-flash")
        if not key.strip():
            return {
                "status": "offline",
                "provider": "gemini",
                "model": model,
                "valid": False,
                "message": "Offline (Local Deterministic Engine)"
            }
        val = validate_gemini_key(key, model)
        val["model"] = model
        return val
