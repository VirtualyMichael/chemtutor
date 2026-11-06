"""Draw the ChemTutor icon (a flask on a blue tile) with no image libraries; writes assets/chemtutor.ico + .png.
Run:  python scripts/make_icon.py
"""
from __future__ import annotations
import struct, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets"
BLUE, WHITE, LIQUID, BUBBLE = (37, 99, 235), (255, 255, 255), (125, 211, 252), (224, 242, 254)

FLASK = [(0.435, 0.20), (0.565, 0.20), (0.565, 0.43), (0.775, 0.76), (0.775, 0.79), (0.225, 0.79), (0.225, 0.76), (0.435, 0.43)]
LIP = [(0.395, 0.155), (0.605, 0.155), (0.605, 0.215), (0.395, 0.215)]
LIQ = [(0.298, 0.605), (0.702, 0.605), (0.775 - 0.04, 0.745), (0.225 + 0.04, 0.745)]
BUBBLES = [(0.43, 0.67, 0.032), (0.55, 0.64, 0.024), (0.50, 0.71, 0.02)]


def inside(poly, x, y):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def in_round_rect(x, y, r=0.2):
    cx = min(max(x, r), 1 - r)
    cy = min(max(y, r), 1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def pixel(x, y, maskable=False):
    """RGBA at unit coordinates (x, y). maskable: full-bleed tile with the flask shrunk into the safe zone (Android crops it)."""
    if maskable:
        x, y = (x - 0.5) / 0.72 + 0.5, (y - 0.5) / 0.72 + 0.5
    elif not in_round_rect(x, y):
        return (0, 0, 0, 0)
    col = BLUE
    if inside(FLASK, x, y) or inside(LIP, x, y):
        col = WHITE
        if inside(LIQ, x, y) and inside(FLASK, x, y):
            col = LIQUID
            if any((x - bx) ** 2 + (y - by) ** 2 <= br * br for bx, by, br in BUBBLES):
                col = BUBBLE
    return (*col, 255)


def render(size: int, ss: int = 3, maskable=False):
    out = []
    for py in range(size):
        row = []
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    r, g, b, a = pixel((px + (sx + .5) / ss) / size, (py + (sy + .5) / ss) / size, maskable)
                    acc[0] += r * a; acc[1] += g * a; acc[2] += b * a; acc[3] += a
            n = ss * ss
            a = acc[3] / n
            row.append((round(acc[0] / acc[3]), round(acc[1] / acc[3]), round(acc[2] / acc[3]), round(a)) if acc[3] else (0, 0, 0, 0))
        out.append(row)
    return out


def png(pixels) -> bytes:
    h, w = len(pixels), len(pixels[0])
    raw = b"".join(b"\x00" + b"".join(bytes(p) for p in row) for row in pixels)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def ico(images: dict[int, bytes]) -> bytes:
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for size, data in images.items():
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    return head + entries + blobs


def main():
    OUT.mkdir(exist_ok=True)
    imgs = {s: png(render(s)) for s in (16, 32, 48, 64, 128, 256)}
    (OUT / "chemtutor.png").write_bytes(imgs[256])
    (OUT / "chemtutor.ico").write_bytes(ico(imgs))
    web = ROOT / "web" / "icons"  # installable phone app (PWA) icons
    web.mkdir(parents=True, exist_ok=True)
    (web / "icon-192.png").write_bytes(png(render(192)))
    (web / "icon-512.png").write_bytes(png(render(512, 2)))
    (web / "maskable-512.png").write_bytes(png(render(512, 2, True)))
    print("wrote", OUT / "chemtutor.ico", f"({sum(map(len, imgs.values()))} bytes of PNG data)")


if __name__ == "__main__":
    main()
