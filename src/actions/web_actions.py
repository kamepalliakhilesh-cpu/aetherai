"""
Web Actions Module for JARVIS / Aether.
Provides URL sanitization, search engine dispatch, multi-browser fallback,
and direct YouTube video resolution and playback.
"""

import os
import re
import time
import subprocess
import urllib.parse
import webbrowser
import requests
from typing import Dict, Any, Optional

URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

def search_google(query: str) -> Dict[str, Any]:
    """Encodes and launches a Google web search."""
    q = query.strip()
    if not q:
        return {"success": False, "message": "Search query is empty."}
    encoded = urllib.parse.quote_plus(q)
    url = f"https://www.google.com/search?q={encoded}"
    return open_url(url, f"Searching Google for '{q}'")

_YT_VIDEO_FILTER = "EgIQAQ%3D%3D"
_LAST_YOUTUBE_QUERY: Optional[str] = None
_LAST_YOUTUBE_RESULTS: list[str] = []

def resolve_youtube_first_video_id(query: str, max_results: int = 5) -> Optional[str]:
    """
    Scrapes video IDs for a query from YouTube search results, filtering out Shorts and channels.
    Stores the top IDs in _LAST_YOUTUBE_RESULTS and returns the first 11-char video ID or None.
    """
    global _LAST_YOUTUBE_QUERY, _LAST_YOUTUBE_RESULTS
    clean_q = query.strip()
    _LAST_YOUTUBE_QUERY = clean_q
    encoded = urllib.parse.quote_plus(clean_q)
    url = f"https://www.youtube.com/results?search_query={encoded}&sp={_YT_VIDEO_FILTER}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "close"
    }
    for attempt in range(2):
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                html = res.text
                all_ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
                filtered = []
                for vid in all_ids:
                    if vid not in filtered and f"/shorts/{vid}" not in html:
                        filtered.append(vid)
                    if len(filtered) >= max_results:
                        break
                _LAST_YOUTUBE_RESULTS = filtered
                if filtered:
                    return filtered[0]
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)
                continue
            print(f"[WebActions] YouTube scrape error: {e}")
    return None

def search_youtube(query: str, auto_play: bool = True) -> Dict[str, Any]:
    """
    Searches YouTube and optionally launches the top result directly to auto-play!
    If auto_play is True, resolves the top video ID and opens https://www.youtube.com/watch?v=ID.
    Falls back to search results if resolution fails.
    """
    global _LAST_YOUTUBE_QUERY
    q = query.strip()
    if not q:
        return {"success": False, "message": "Search query is empty."}

    _LAST_YOUTUBE_QUERY = q

    if auto_play:
        video_id = resolve_youtube_first_video_id(q)
        if video_id:
            direct_url = f"https://www.youtube.com/watch?v={video_id}"
            open_url(direct_url)
            return {
                "success": True,
                "video_id": video_id,
                "url": direct_url,
                "auto_play": True,
                "message": f"Playing '{q}' on YouTube, Sir."
            }

    # Fallback to standard search list
    encoded = urllib.parse.quote_plus(q)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    return open_url(url, f"Searching YouTube for '{q}'")

def play_youtube_result(index: int = 1) -> Dict[str, Any]:
    """
    Executes 'play the <N>th video' / 'click video <N>' action.
    1. If a previous search query cached top video IDs, launches the exact URL.
    2. Brings YouTube/Browser window to foreground using Windows AppActivate.
    3. Attempts UIA Accessibility element click via screenview.look().
    4. Falls back to viewport coordinate click & Enter.
    """
    global _LAST_YOUTUBE_RESULTS, _LAST_YOUTUBE_QUERY
    from .computer_use import focus_window, mouse_click, keyboard_press, list_open_windows
    import ctypes

    idx = max(1, min(10, int(index)))
    ord_str = "first" if idx == 1 else ("second" if idx == 2 else ("third" if idx == 3 else f"{idx}th"))

    # 1. Check if we have cached results from the recent query
    if _LAST_YOUTUBE_RESULTS and len(_LAST_YOUTUBE_RESULTS) >= idx:
        target_id = _LAST_YOUTUBE_RESULTS[idx - 1]
        direct_url = f"https://www.youtube.com/watch?v={target_id}"
        open_url(direct_url)
        return {
            "success": True,
            "method": "cached_url_dispatch",
            "video_id": target_id,
            "index": idx,
            "url": direct_url,
            "message": f"Playing the {ord_str} video from your search, Sir."
        }

    # 2. If we had a query but no cached list, scrape and open now
    if _LAST_YOUTUBE_QUERY:
        resolve_youtube_first_video_id(_LAST_YOUTUBE_QUERY, max_results=max(5, idx))
        if _LAST_YOUTUBE_RESULTS and len(_LAST_YOUTUBE_RESULTS) >= idx:
            target_id = _LAST_YOUTUBE_RESULTS[idx - 1]
            direct_url = f"https://www.youtube.com/watch?v={target_id}"
            open_url(direct_url)
            return {
                "success": True,
                "method": "scraped_query_dispatch",
                "video_id": target_id,
                "index": idx,
                "url": direct_url,
                "message": f"Playing the {ord_str} video result for '{_LAST_YOUTUBE_QUERY}', Sir."
            }

    # 3. Bring active YouTube or Browser window to front using Windows Shell AppActivate
    try:
        script = '(New-Object -ComObject WScript.Shell).AppActivate("YouTube")'
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=3, creationflags=0x08000000 if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        )
    except Exception:
        focus_window("YouTube")

    time.sleep(0.25)

    # 4. Try UI Automation element targeting
    try:
        from core.screenview import look
        from core.screenact import click
        view = look(budget_s=0.5, allow_ocr=False)
        if view and view.usable and view.elements:
            # Filter elements for potential video cards/links
            candidates = [
                e for e in view.elements
                if e.interactable and e.role in ("link", "button", "hyperlink", "text")
                and e.name and not any(nav in e.name.lower() for nav in ["home", "subscriptions", "shorts", "explore", "trending", "history", "library", "search"])
            ]
            if candidates and len(candidates) >= idx:
                target_elem = candidates[idx - 1]
                click(target_elem)
                return {
                    "success": True,
                    "method": "uia_element_click",
                    "element_name": target_elem.name,
                    "index": idx,
                    "message": f"Activated '{target_elem.name}' via UI Automation, Sir."
                }
    except Exception as e:
        print(f"[WebActions] UIA video target attempt: {e}")

    # 5. Fallback: viewport coordinate click and Enter
    user32 = ctypes.windll.user32
    scr_w = user32.GetSystemMetrics(0) or 1920
    scr_h = user32.GetSystemMetrics(1) or 1080

    click_x = int(scr_w * 0.30)
    click_y = int(scr_h * (0.32 + (idx - 1) * 0.16))

    mouse_click(click_x, click_y)
    time.sleep(0.1)
    keyboard_press("enter")

    return {
        "success": True,
        "method": "coordinate_click",
        "index": idx,
        "coordinates": (click_x, click_y),
        "message": f"Playing the {ord_str} video result, Sir."
    }

def play_first_youtube_result() -> Dict[str, Any]:
    return play_youtube_result(1)

def search_github(query: str) -> Dict[str, Any]:
    """Encodes and launches a GitHub repository/code search."""
    q = query.strip()
    encoded = urllib.parse.quote_plus(q)
    url = f"https://github.com/search?q={encoded}"
    return open_url(url, f"Searching GitHub for '{q}'")

def open_url(url: str, custom_message: Optional[str] = None) -> Dict[str, Any]:
    """
    Sanitizes, validates, and launches a web URL.
    Uses resilient multi-tier browser dispatch:
    1. webbrowser.open_new_tab()
    2. os.startfile() (Windows native shell handler)
    3. PowerShell Start-Process fallback
    """
    clean_url = url.strip()
    if not clean_url:
        return {"success": False, "message": "Empty URL provided."}

    # Auto-prepend https:// if protocol is omitted
    if not re.match(r"^[a-zA-Z]+://", clean_url):
        clean_url = "https://" + clean_url

    # SSRF Guard (Ported from J.A.R.V.I.S. policy.mjs)
    try:
        from ..core.policy import vet_target_url
        safe, reason = vet_target_url(clean_url)
        if not safe:
            return {"success": False, "url": clean_url, "error": reason, "message": f"Security Policy Blocked: {reason}"}
    except Exception:
        pass

    # Tier 1: Python standard webbrowser module
    try:
        opened = webbrowser.open_new_tab(clean_url)
        if opened:
            msg = custom_message or f"Navigating to {clean_url}, Sir."
            return {"success": True, "url": clean_url, "method": "browser_tab", "message": msg}
    except Exception:
        pass

    # Tier 2: Windows native os.startfile
    try:
        os.startfile(clean_url)
        msg = custom_message or f"Navigating to {clean_url}, Sir."
        return {"success": True, "url": clean_url, "method": "os_startfile", "message": msg}
    except Exception:
        pass

    # Tier 3: PowerShell Start-Process
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", f"Start-Process '{clean_url}'"], check=True, timeout=5)
        msg = custom_message or f"Navigating to {clean_url}, Sir."
        return {"success": True, "url": clean_url, "method": "powershell_launch", "message": msg}
    except Exception as e:
        return {"success": False, "url": clean_url, "error": str(e), "message": f"Failed to open {clean_url}: {e}"}
