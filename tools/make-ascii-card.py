#!/usr/bin/env python3
"""
make-ascii-card.py — genera la TARJETA SUPERIOR del perfil (assets/ascii-avatar-<theme>.svg).

Regla de oro (no violar): la tarjeta lleva SOLO el art del avatar + presentación mínima
(nombre, rol, uptime, contacto). Habilidades, proyectos y logros viven en el README,
en Markdown aparte. Nada de eso aquí dentro.

Dos temas (GitHub claro/oscuro se resuelve desde el README con <picture> + prefers-color-scheme):
    --theme dark   fondo #0d1117, tinta = fondo, papel = gris claro
    --theme light  fondo #ffffff, papel = fondo, tinta = gris oscuro

Uso:
    python3 tools/make-ascii-card.py --theme dark  --out assets/ascii-avatar-dark.svg  --preview
    python3 tools/make-ascii-card.py --theme light --out assets/ascii-avatar-light.svg --preview
"""
import argparse, os, subprocess
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

FONT = "'JetBrains Mono','Cascadia Code','DejaVu Sans Mono',Consolas,monospace"
FS = 14.0
CELL_W = FS * 0.601     # ancho de una celda monoespaciada (columna de texto)
PAD = 20
CHARS = "@%#WM8&$Q0Omwqpxvun[]{}?*+=-:,. "   # rampa ASCII puro (--variant chars)

THEMES = {
    "dark": dict(
        bg="#0d1117", title="#c9d1d9", key="#39FF14", val="#a5d6ff", dots="#616e7f",
        grays=["#0d1117", "#161b22", "#21262d", "#30363d", "#484f58",
               "#6e7681", "#8b949e", "#b1bac4", "#d0d7de", "#e6edf3"],
        skip="dark",   # el nivel más oscuro (tinta) se funde con el fondo
    ),
    "light": dict(
        bg="#ffffff", title="#1f2328", key="#116329", val="#0a3069", dots="#9ba3ae",
        grays=["#1f2328", "#32383f", "#424a53", "#57606a", "#6e7781",
               "#8b949e", "#afb8c1", "#d0d7de", "#eaeef2", "#ffffff"],
        skip="light",  # el nivel más claro (papel) se funde con el fondo
    ),
}

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
    # pixel oscuro -> caracter denso
    return ["".join(CHARS[int((1.0 - px[x, y] / 255.0) * n)] for x in range(cols))
            for y in range(rows)]


def art_blocks(im, cols, levels):
    rows_px = max(2, round(cols * (im.height / im.width)))
    px = im.resize((cols, rows_px), Image.LANCZOS).load()
    n = levels - 1
    # pixel CLARO -> nivel alto (y viceversa)
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
    th = THEMES[args.theme]
    im = load_art(args.source, tuple(float(v) for v in args.box.split(",")),
                  args.blur, args.contrast, args.invert)
    parts, px = [], args.px_size

    if args.variant == "chars":
        art = art_chars(im, args.cols)
        art_w, art_h = args.cols * CELL_W, len(art) * FS
        for i, ln in enumerate(art):
            parts.append(f'<text opacity="1" x="{PAD}" y="{PAD + FS * 0.86 + i * FS:.1f}" '
                         f'fill="{th["title"]}"><animate attributeName="opacity" from="0" to="1" '
                         f'begin="{0.05 + i * 0.04:.2f}s" dur="0.45s" fill="freeze"/>{esc(ln)}</text>')
    else:
        grid = art_blocks(im, args.cols, args.levels)
        rows_px = len(grid)
        art_w, art_h = args.cols * px, rows_px * px
        pal = th["grays"][:args.levels]
        n_lvl = args.levels - 1
        skip = 0 if th["skip"] == "dark" else n_lvl          # nivel que se funde con el fondo
        per = max(1, rows_px // 8)
        for b in range(0, rows_px, per):
            by_lvl = {}
            for y in range(b, min(b + per, rows_px)):
                for x0, x1, lvl in runs(grid[y]):
                    if lvl == skip:
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
    info_x, ty, est = PAD + art_w + 26, PAD + 2, 0
    for i, (kind, *r) in enumerate(INFO):
        d = 0.60 + i * 0.10
        if kind == "kv":
            k, v = r
            dots = "." * max(1, int((9 * CELL_W - len(k) * CELL_W) / CELL_W))
            parts.append(f'<text opacity="1" x="{info_x:.0f}" y="{ty + FS * 0.9:.0f}">'
                         f'<animate attributeName="opacity" from="0" to="1" begin="{d:.2f}s" '
                         f'dur="0.45s" fill="freeze"/>'
                         f'<tspan fill="{th["key"]}" font-weight="700">{esc(k)}</tspan>'
                         f'<tspan fill="{th["dots"]}">{dots}</tspan>'
                         f'<tspan fill="{th["val"]}"> {esc(v)}</tspan></text>')
            est = max(est, (len(k) + len(dots) + 1 + len(v)) * CELL_W)
        else:
            big = kind == "head"
            extra = ' font-size="15" font-weight="700"' if big else ""
            parts.append(f'<text opacity="1" x="{info_x:.0f}" y="{ty + FS * 0.9:.0f}" '
                         f'fill="{th["title"] if big else th["dots"]}"{extra}>'
                         f'<animate attributeName="opacity" from="0" to="1" begin="{d:.2f}s" '
                         f'dur="0.45s" fill="freeze"/>{esc(r[0])}</text>')
            est = max(est, len(r[0]) * CELL_W)
        ty += FS * 1.5

    W = info_x + est + PAD
    H = max(PAD * 2 + art_h, ty + PAD) + 6
    cursor = (f'<rect opacity="1" x="{info_x + est - CELL_W:.0f}" y="{ty - FS * 1.35:.0f}" '
              f'width="{CELL_W:.1f}" height="{FS * 1.0:.0f}" fill="{th["key"]}">'
              f'<animate attributeName="opacity" values="1;0;1" dur="1.2s" begin="1.4s" '
              f'repeatCount="indefinite"/></rect>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
            f'viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="@p4Rd0x-zuD">\n'
            f'<style>text{{font-family:{FONT};font-size:{FS}px;white-space:pre}}</style>\n'
            f'<rect width="{W:.0f}" height="{H:.0f}" rx="12" fill="{th["bg"]}"/>\n'
            + "\n".join(parts) + f'\n{cursor}\n</svg>\n')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", choices=["dark", "light"], default="dark")
    ap.add_argument("--variant", choices=["blocks", "chars"], default="blocks")
    ap.add_argument("--source", default=os.path.expanduser("~/Proyectos/p4Rd0x-zuD/assets/avatar-src.jpg"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--box", default="0.10,0.18,0.88,0.74")
    ap.add_argument("--cols", type=int, default=76)
    ap.add_argument("--px-size", type=float, default=6.0)
    ap.add_argument("--levels", type=int, default=10)
    ap.add_argument("--blur", type=float, default=1.6)
    ap.add_argument("--contrast", type=float, default=1.08)
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    if not a.out:
        a.out = os.path.expanduser(f"~/Proyectos/p4Rd0x-zuD/assets/ascii-avatar-{a.theme}.svg")
    svg = build(a)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w").write(svg)
    print(f"{a.out}  {len(svg)/1024:.1f} KB  theme={a.theme} variant={a.variant} cols={a.cols}")
    if a.preview:
        png = f"/tmp/ghprof/card_{a.theme}_{a.variant}_{a.cols}.png"
        subprocess.run(["rsvg-convert", "-b", THEMES[a.theme]["bg"], "-o", png, a.out], check=True)
        print("preview:", png)
