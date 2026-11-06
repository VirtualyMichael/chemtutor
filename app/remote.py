"""Phone access: an optional access key so ChemTutor can be opened from another device.

Off by default (the server then listens on 127.0.0.1 only). When switched on, the server listens on the
network but every request that does not come straight from this computer must carry the access key,
either as a cookie (set once by opening the pairing link) or as a Bearer header.
Stdlib only. The key lives in <library>/remote.json next to the progress database.
"""
from __future__ import annotations
import hmac, json, secrets, shutil, socket, subprocess
from urllib.parse import urlparse

from . import library

COOKIE = "ct_auth"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}
LOCAL_ADDRS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
# reachable without a key: no personal data, and the browser fetches them without cookies
PUBLIC_PATHS = ("/api/health", "/manifest.webmanifest", "/sw.js", "/icons/")


def _file():
    return library.HOME / "remote.json"


def load() -> dict:
    try:
        d = json.loads(_file().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(d: dict) -> None:
    _file().parent.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps(d), encoding="utf-8")


def enabled() -> bool:
    return bool(load().get("enabled")) and bool(load().get("token"))


def token() -> str:
    """The access key, created on first use."""
    d = load()
    if not d.get("token"):
        d["token"] = secrets.token_urlsafe(24)
        _save(d)
    return d["token"]


def set_enabled(on: bool) -> str:
    d = load()
    d["enabled"] = bool(on)
    if not d.get("token"):
        d["token"] = secrets.token_urlsafe(24)
    _save(d)
    return d["token"]


def reset_token() -> str:
    """New key: every paired phone has to be paired again."""
    d = load()
    d["token"] = secrets.token_urlsafe(24)
    _save(d)
    return d["token"]


def is_public(path: str) -> bool:
    return any(path == p or (p.endswith("/") and path.startswith(p)) for p in PUBLIC_PATHS)


def is_local_request(client_ip: str, headers) -> bool:
    """True only for a browser on this computer talking to us directly.
    A reverse proxy on this computer (e.g. `tailscale serve`) connects from 127.0.0.1 too, so any
    forwarding header, or a Host that is not localhost, marks the request as remote."""
    if client_ip not in LOCAL_ADDRS:
        return False
    for name in headers.keys():
        low = name.lower()
        if low in ("x-forwarded-for", "x-forwarded-host", "x-forwarded-proto", "forwarded", "x-real-ip") or low.startswith("tailscale-"):
            return False
    host = (headers.get("Host") or "").strip().lower()
    host = host.rsplit(":", 1)[0] if not host.endswith("]") and ":" in host else host
    return host in LOCAL_HOSTS


def _cookie_value(headers) -> str:
    for part in (headers.get("Cookie") or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE:
            return v
    return ""


def has_key(headers, key: str) -> bool:
    want = token()
    cands = [key or "", _cookie_value(headers)]
    auth = headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        cands.append(auth[7:].strip())
    return any(c and hmac.compare_digest(c.encode(), want.encode()) for c in cands)


# ---------- finding the addresses a phone can use ----------
def _is_tailscale(ip: str) -> bool:
    try:
        a, b = (int(x) for x in ip.split(".")[:2])
    except ValueError:
        return False
    return a == 100 and 64 <= b <= 127


def local_addresses() -> list[str]:
    ips: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:  # no packet is sent; this picks the main interface
            s.connect(("192.0.2.1", 9))
            ips.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.append(info[4][0])
    except OSError:
        pass
    out: list[str] = []
    for ip in ips:
        if ip and not ip.startswith(("127.", "169.254.", "0.")) and ip not in out:
            out.append(ip)
    return out


def tailscale_exe() -> str | None:
    exe = shutil.which("tailscale")
    if exe:
        return exe
    for p in (r"C:\Program Files\Tailscale\tailscale.exe", r"C:\Program Files (x86)\Tailscale\tailscale.exe"):
        try:
            if __import__("os").path.isfile(p):
                return p
        except OSError:
            pass
    return None


def tailscale_info() -> dict:
    """{'ip': '100.x.y.z', 'dns': 'pc.tailnet.ts.net'} when Tailscale is installed and connected, else {}."""
    exe = tailscale_exe()
    if not exe:
        return {}
    try:
        out = subprocess.run([exe, "status", "--json"], capture_output=True, text=True, timeout=6)
        d = json.loads(out.stdout or "{}")
        me = d.get("Self") or {}
        ips = [i for i in me.get("TailscaleIPs", []) if "." in i]
        dns = (me.get("DNSName") or "").rstrip(".")
        if d.get("BackendState") == "Running" and ips:
            return {"ip": ips[0], "dns": dns}
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return {}


def pairing_links(port: int) -> list[dict]:
    """Links to open on the phone, best first. Each carries the access key once; the phone then keeps a cookie."""
    key = token()
    links = []
    ts = tailscale_info()
    if ts:
        links.append({"kind": "tailscale", "label": "Anywhere (Tailscale)", "url": f"http://{ts['ip']}:{port}/?key={key}"})
    for ip in local_addresses():
        if _is_tailscale(ip):
            if not ts:
                links.append({"kind": "tailscale", "label": "Anywhere (Tailscale)", "url": f"http://{ip}:{port}/?key={key}"})
        else:
            links.append({"kind": "wifi", "label": "Same Wi-Fi only", "url": f"http://{ip}:{port}/?key={key}"})
    return links


def display_host(url: str) -> str:
    return urlparse(url).netloc
