"""Which local AI server and model ChemTutor uses: Ollama or LM Studio (any OpenAI-compatible server works).

Order of precedence: LLM_URL / LLM_MODEL (or --llm-url / --model) > the choice saved in <library>/ai.json
(made from the model badge in the app) > automatic: the default model if a server has it, else the best-looking
chat model on the first server found. Stdlib only.
"""
from __future__ import annotations
import json, re, urllib.request
from urllib.parse import urlparse, urlunparse

from . import library

DEFAULT_MODEL = "qwen2.5:7b"
BACKENDS = [("Ollama", "http://127.0.0.1:11434/v1"), ("LM Studio", "http://127.0.0.1:1234/v1")]  # 127.0.0.1, not "localhost": that can resolve to IPv6 and time out
ALIASES = {"ollama": BACKENDS[0][1], "lmstudio": BACKENDS[1][1], "lm-studio": BACKENDS[1][1], "lm studio": BACKENDS[1][1]}
NOT_CHAT = ("embed", "rerank", "whisper", "tts", "clip", "voxtral", "audio", "vision-only")
AVOID = ("uncensored", "abliterated", "heretic", "coder", "roleplay", "nsfw")  # fine-tunes that make worse tutors
SWEET_SPOT_B = 14  # largest size picked automatically: bigger models are often too slow on a home PC (you can still choose them)


def resolve_url(value: str) -> str:
    """Accepts a full URL or the words 'ollama' / 'lmstudio'."""
    return ALIASES.get((value or "").strip().lower(), value)


def backend_name(url: str) -> str:
    u = urlparse(url or "")
    for name, b in BACKENDS:
        if u.netloc.replace("localhost", "127.0.0.1") == urlparse(b).netloc:
            return name
    return {11434: "Ollama", 1234: "LM Studio"}.get(u.port, "AI server")  # same ports on another address of this computer


def _file():
    return library.HOME / "ai.json"


def load() -> dict:
    try:
        d = json.loads(_file().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save(url: str, model: str) -> None:
    _file().parent.mkdir(parents=True, exist_ok=True)
    _file().write_text(json.dumps({"url": url, "model": model}), encoding="utf-8")


def forget() -> None:
    try:
        _file().unlink()
    except OSError:
        pass


def list_models(url: str, timeout: float = 1.0) -> list[str] | None:
    """Chat model ids offered by the server, or None if it is not reachable."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/models", timeout=timeout) as r:
            ids = [m.get("id", "") for m in json.load(r).get("data", [])]
    except Exception:  # noqa: BLE001  (refused, timeout, not JSON...)
        return None
    return [i for i in ids if i and not any(w in i.lower() for w in NOT_CHAT)]


def _other_addresses() -> list[str]:
    """This computer's other addresses (Wi-Fi, Tailscale): LM Studio can be set to listen on just one of them."""
    try:
        from . import remote
        ips = remote.local_addresses()
        ts = remote.tailscale_info().get("ip")
        return ips + ([ts] if ts and ts not in ips else [])
    except Exception:  # noqa: BLE001
        return []


def detect(extra_url: str | None = None) -> list[dict]:
    """[{name, url, up, models}] for every known server (plus the configured one if it is somewhere else).
    If a server does not answer on 127.0.0.1 its port is tried on this computer's other addresses."""
    urls = [u for _, u in BACKENDS]
    others: list[str] | None = None
    if extra_url:
        host, port = urlparse(extra_url).hostname or "", urlparse(extra_url).port
        known_ports = [urlparse(u).port for u in urls]
        if port in known_ports and host not in ("127.0.0.1", "localhost"):
            others = _other_addresses()
        same_machine = host in ("127.0.0.1", "localhost") or host in (others or [])
        if not (port in known_ports and same_machine):
            urls.append(extra_url)  # a server somewhere else the user pointed us at
    out = []
    for u in urls:
        m = list_models(u, 0.6)
        if m is None and u in [b for _, b in BACKENDS]:
            others = _other_addresses() if others is None else others
            port = urlparse(u).port
            for ip in others:
                alt = urlunparse(urlparse(u)._replace(netloc=f"{ip}:{port}"))
                m2 = list_models(alt, 0.6)
                if m2 is not None:
                    u, m = alt, m2
                    break
        out.append({"name": backend_name(u), "url": u, "up": m is not None, "models": m or []})
    return out


def has_model(model: str, names: list[str]) -> bool:
    """Exact match; for Ollama a name without a tag ('qwen2.5') matches any tag."""
    base = model.split(":")[0]
    return any(n == model or (":" not in model and n.split(":")[0] == base) for n in names)


def _size(name: str) -> float:
    m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", name.lower().replace("-", " ").replace("_", " "))
    return float(m.group(1)) if m else 0.0


def best_model(names: list[str]) -> str | None:
    """A sensible default tutor: a plain chat model, the largest up to ~14B (bigger ones are slow on most PCs);
    if everything is bigger, the smallest. Models that do not say their size come last. You can always choose another."""
    if not names:
        return None
    plain = [n for n in names if not any(w in n.lower() for w in AVOID)] or names
    sized = [n for n in plain if _size(n)]
    fit = [n for n in sized if _size(n) <= SWEET_SPOT_B]
    if fit:
        return max(fit, key=lambda n: (_size(n), -plain.index(n)))
    if sized:
        return min(sized, key=_size)
    return plain[0]


def auto_pick(found: list[dict], wanted: str = DEFAULT_MODEL, prefer_url: str | None = None) -> tuple[str, str] | None:
    """(url, model) from detect() output, or None if no server has any chat model."""
    ups = [b for b in found if b["up"] and b["models"]]
    if prefer_url:
        ups.sort(key=lambda b: b["url"].rstrip("/") != prefer_url.rstrip("/"))
    for b in ups:
        if has_model(wanted, b["models"]):
            exact = wanted if wanted in b["models"] else next(n for n in b["models"] if n.split(":")[0] == wanted.split(":")[0])
            return b["url"], exact
    return (ups[0]["url"], best_model(ups[0]["models"])) if ups else None
