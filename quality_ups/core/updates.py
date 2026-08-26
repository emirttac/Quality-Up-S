from __future__ import annotations

import base64
import json
import platform
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass

from quality_ups.config import APP_VERSION, GITHUB_REPO, GITHUB_URL, ICON_DIR


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    update_available: bool
    latest: str | None
    url: str
    current: str = APP_VERSION


def _parse_version(value: str) -> tuple[int, ...]:
    digits: list[int] = []
    for part in value.lstrip("vV").replace("-", ".").split("."):
        if part.isdigit():
            digits.append(int(part))
        else:
            break
    return tuple(digits or [0])


def check_for_updates() -> UpdateResult:
    latest, url = _latest_from_github()
    if not latest:
        return UpdateResult(ok=False, update_available=False, latest=None, url=GITHUB_URL)
    newer = _parse_version(latest) > _parse_version(APP_VERSION)
    return UpdateResult(ok=True, update_available=newer, latest=latest, url=url)


def notify_update(title: str, body: str) -> None:
    system = platform.system()
    if system == "Darwin":
        script = f"display notification {json.dumps(body)} with title {json.dumps(title)}"
        try:
            subprocess.run(["osascript", "-e", script], check=False, timeout=5)
        except Exception:
            pass
        return
    if system == "Windows":
        _notify_windows(title, body)


def _notify_windows(title: str, body: str) -> None:
    ico = ICON_DIR / "app.ico"
    ico_literal = json.dumps(str(ico)) if ico.exists() else ""
    icon_line = (
        f"$n.Icon = New-Object System.Drawing.Icon({ico_literal})"
        if ico_literal
        else "$n.Icon = [System.Drawing.SystemIcons]::Application"
    )
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$n = New-Object System.Windows.Forms.NotifyIcon
{icon_line}
$n.Visible = $true
$n.ShowBalloonTip(5000, {json.dumps(title)}, {json.dumps(body)}, [System.Windows.Forms.ToolTipIcon]::None)
Start-Sleep -Seconds 6
$n.Dispose()
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-EncodedCommand", encoded],
            creationflags=flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _latest_from_github() -> tuple[str | None, str]:
    release = _get_json(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
    if isinstance(release, dict) and release.get("tag_name") and not release.get("message"):
        tag = str(release["tag_name"])
        url = str(release.get("html_url") or GITHUB_URL)
        return tag, url
    tags = _get_json(f"https://api.github.com/repos/{GITHUB_REPO}/tags")
    if isinstance(tags, list) and tags:
        tag = str(tags[0].get("name") or "")
        if tag:
            return tag, f"{GITHUB_URL}/releases/tag/{tag}"
    return None, GITHUB_URL


def _get_json(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"Quality-Up-S/{APP_VERSION}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
