#!/usr/bin/env python3
"""
make-ascii-card.py — genera assets/ascii-avatar.svg: la TARJETA SUPERIOR del perfil.

Regla de oro (no violar): esta tarjeta lleva SOLO el art del avatar + presentación
mínima (nombre, rol, contacto). Las habilidades, proyectos y logros viven en el
README, en Markdown aparte. Nada de eso aquí dentro.

Uso:
    python3 tools/make-ascii-card.py --preview                    # medio-bloques (recomendado)
    python3 tools/make-ascii-card.py --variant chars              # ASCII puro
    python3 tools/make-ascii-card.py --box 0.06,0.10,0.90,0.70    # encuadre fino
"""
import argparse, os, subprocess
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

BG, TITLE, KEY, VAL, DOTS = "#0d1117", "#c9d1d9", "#39FF14", "#a5d6ff", "#616e7f"
FONT = "'JetBrains Mono','Cascadia Code','DejaVu Sans Mono',Consolas,monospace"
FS = 14.0
CELL_W = FS * 0.601          # ancho de una celda monoespaciada (columna de texto)
PXSIZE = 7.0                 # lado (px) de cada 'pixel' del art (independiente del texto)
PAD = 20
CHARS = "@%#WM8&$Q0Omwqpxvun[]{}?*+=-:,. "
GRAYS = ["#0d1117", "#161b22", "#21262d", "#30363d", "#484f58",
         "#6e7681", "#8b949e", "#b1bac4", "#d0d7de", "#e6edf3"]

# presentación mínima: SIN skills, SIN proyectos, SIN logros
INFO = [
    ("head", "p4Rd0x-zuD@github"),
    ("rule", "─" * 43),
    ("kv", "Name",    "Julian Andres Pardo Hurtado"),
    ("kv", "Role",    "Tecnólogo en Redes de Datos"),
    ("kv", "Uptime",  "desde 2025-03-10"),
    ("kv", "Contact", "pardojulian189@gmail.com"),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_art(path, box, blur, contrast, invert):
    im = Image.open(path).convert("L")
    w, h = im.size
    if box:
        x0, y0, x1, y1 = box
        im = im.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    im = ImageOps.autocontrast(im, cutoff=2)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    return ImageOps.invert(im) if invert else im


def art_chars(im, cols):
    rows = max(1, round(cols * (im.height / im.width) * 0.52))
    px = im.resize((cols, rows), Image.LANCZOS).load()
    n = len(CHARS) - 1
    return ["".join(CHARS[int((1.0 - px[x, y] / 255.0) * n)] for x in range(cols))
            for y in range(rows)]


def art_blocks(im, cols, levels):
    rows_px = max(2, round(cols * (im.height / im.width)))
    px = im.resize((cols, rows_px), Image.LANCZOS).load()
    n = levels - 1
    # mapeo correcto: pixel CLARO -> nivel alto -> color claro (y viceversa)
    return [[min(n, int((px[x, y] / 255.0) * (n + 1))) for x in range(cols)]
            for y in range(rows_px)]


def runs(row):
    out, start, cur = [], 0, row[0]
    for i, v in enumerate(row[1:], 1):
        if v != cur:
            out.append((start, i, cur)); start, cur = i, v
    out.append((start, len(row), cur))
    return out


def build(args):
    im = load_art(args.source, tuple(float(v) for v in args.box.split(",")),
                  args.blur, args.contrast, args.invert)
    parts = []

    px = args.px_size
    if args.variant == "chars":
        art = art_chars(im, args.cols)
        art_w, art_h = args.cols * CELL_W, len(art) * FS
        for i, ln in enumerate(art):
            parts.append(f'<text opacity="1" x="{PAD}" y="{PAD + FS * 0.86 + i * FS:.1f}">'
                         f'<animate attributeName="opacity" from="0" to="1" '
                         f'begin="{0.05 + i * 0.04:.2f}s" dur="0.45s" fill="freeze"/>{esc(ln)}</text>')
    else:
        grid = art_blocks(im, args.cols, args.levels)
        rows_px = len(grid)
        art_w, art_h = args.cols * px, rows_px * px
        pal = GRAYS[:args.levels]
        per = max(1, rows_px // 8)
        for b in range(0, rows_px, per):
            by_lvl = {}
            for y in range(b, min(b + per, rows_px)):
                for x0, x1, lvl in runs(grid[y]):
                    if lvl == 0:
                        continue
                    by_lvl.setdefault(lvl, []).append(
                        f"M{x0 * px:.1f} {PAD + y * px:.1f}"
                        f"h{(x1 - x0) * px:.1f}v{px:.1f}h-{(x1 - x0) * px:.1f}z")
            delay = 0.05 + (b // per) * 0.07
            for lvl, segs in sorted(by_lvl.items()):
                parts.append(f'<path opacity="1" fill="{pal[lvl]}" d="{"".join(segs)}">'
                             f'<animate attributeName="opacity" from="0" to="1" '
                             f'begin="{delay:.2f}s" dur="0.45s" fill="freeze"/></path>')

    # columna de información
    info_x = PAD + art_w + 26
    ty = PAD + 2
    est = 0
    for i, (kind, *r) in enumerate(INFO):
        d = 0.60 + i * 0.10
        if kind == "kv":
            k, v = r
            dots = "." * max(1, int((9 * CELL_W - len(k) * CELL_W) / CELL_W))
            parts.append(f'<text opacity="1" x="{info_x:.0f}" '
                         f'y="{ty + FS * 0.9:.0f}"><animate attributeName="opacity" from="0" to="1" '
                         f'begin="{d:.2f}s" dur="0.45s" fill="freeze"/>'
                         f'<tspan fill="{KEY}" font-weight="700">{esc(k)}</tspan>'
                         f'<tspan fill="{DOTS}">{dots}</tspan><tspan fill="{VAL}"> {esc(v)}</tspan></text>')
            est = max(est, (len(k) + len(dots) + 1 + len(v)) * CELL_W)
        else:
            big = kind == "head"
            extra = ' font-size="15" font-weight="700"' if big else ""
            parts.append(f'<text opacity="1" x="{info_x:.0f}" '
                         f'y="{ty + FS * 0.9:.0f}" fill="{TITLE if big else DOTS}"{extra}>'
                         f'<animate attributeName="opacity" from="0" to="1" '
                         f'begin="{d:.2f}s" dur="0.45s" fill="freeze"/>{esc(r[0])}</text>')
            est = max(est, len(r[0]) * CELL_W)
        ty += FS * 1.5

    W = info_x + est + PAD
    H = max(PAD * 2 + art_h, ty + PAD) + 6
    style = f'text{{font-family:{FONT};font-size:{FS}px;white-space:pre}}'
    cursor = (f'<rect opacity="1" x="{info_x + est - CELL_W:.0f}" y="{ty - FS * 1.35:.0f}" '
              f'width="{CELL_W:.1f}" height="{FS * 1.0:.0f}" fill="{KEY}">'
              f'<animate attributeName="opacity" values="1;0;1" dur="1.2s" '
              f'begin="1.4s" repeatCount="indefinite"/></rect>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
            f'viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="@p4Rd0x-zuD">\n'
            f'<style>{style}</style>\n<rect width="{W:.0f}" height="{H:.0f}" rx="12" fill="{BG}"/>\n'
            + "\n".join(parts) + f'\n{cursor}\n</svg>\n')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["blocks", "chars"], default="blocks")
    ap.add_argument("--source", default=os.path.expanduser("~/Proyectos/p4Rd0x-zuD/assets/avatar-src.jpg"))
    ap.add_argument("--out", default=os.path.expanduser("~/Proyectos/p4Rd0x-zuD/assets/ascii-avatar.svg"))
    ap.add_argument("--box", default="0.06,0.10,0.90,0.70")
    ap.add_argument("--cols", type=int, default=64)
    ap.add_argument("--px-size", type=float, default=7.0)
    ap.add_argument("--levels", type=int, default=8)
    ap.add_argument("--blur", type=float, default=2.4)
    ap.add_argument("--contrast", type=float, default=1.35)
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    svg = build(a)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write(svg)
    print(f"{a.out}  {len(svg)/1024:.1f} KB  variant={a.variant} cols={a.cols} box={a.box}")
    if a.preview:
        slug = a.box.replace(".", "").replace(",", "_") + ("_inv" if a.invert else "")
        png = f"/tmp/ghprof/card_{a.variant}_{a.cols}_{slug}.png"
        tmp = "/tmp/ghprof/_static.svg"
        open(tmp, "w").write(svg)
        subprocess.run(["rsvg-convert", "-b", BG, "-o", png, tmp], check=True)
        print("preview:", png)
