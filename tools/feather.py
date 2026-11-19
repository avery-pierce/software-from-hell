#!/usr/bin/env python3
"""feather.py — blend a render's edges into the site's page background.

Standardized image finishing step: every image we generate (hero plates,
figures) gets its border feathers blended into the page background with a
smoothstep profile, so the plate dissolves into the page instead of sitting
on a visible rectangle. The recipe is the one the site hero settled on
(80px sides / 48px top-bottom, commit 47acf59) — this script is that recipe,
kept as a writer.

The background color is read from the site's own CSS (the --bg custom
property in _layouts/site.html), so a palette change changes the feather
with it.

Stdlib only. PNG in, PNG out (alpha, if present, is flattened onto the
background first, then feathered).

Usage:
  feather.py IMAGE [--out PATH] [--sides N] [--tb N] [--bg #RRGGBB]
Default: in-place (--out = input). Git history is the backup.
Feathering is NOT idempotent — run it once per render, before committing.
"""
import argparse, os, re, struct, sys, zlib

def read_png(path):
    d = open(path, "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n", f"not a PNG: {path}"
    pos, idat, w, h, ctype, depth = 8, b"", None, None, None, None
    while pos < len(d):
        ln, typ = struct.unpack(">I4s", d[pos:pos+8])
        chunk = d[pos+8:pos+8+ln]
        if typ == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", chunk[:10])
        elif typ == b"IDAT":
            idat += chunk
        pos += 12 + ln
    assert depth == 8, f"only 8-bit PNGs supported (got depth {depth})"
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    assert bpp, f"unsupported color type {ctype}"
    raw = zlib.decompress(idat)
    stride = w * bpp
    out = bytearray()
    prev = bytearray(stride)
    p = 0
    for _ in range(h):
        ft = raw[p]; p += 1
        line = bytearray(raw[p:p+stride]); p += stride
        if ft == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x-bpp]) & 0xFF
        elif ft == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif ft == 3:
            for x in range(stride):
                a = line[x-bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 0xFF
        elif ft == 4:
            for x in range(stride):
                a = line[x-bpp] if x >= bpp else 0
                b = prev[x]; c = prev[x-bpp] if x >= bpp else 0
                pn = a + b - c
                pa, pb, pc = abs(pn-a), abs(pn-b), abs(pn-c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        out += line
        prev = line
    return w, h, ctype, bytes(out)

def write_png(path, w, h, ctype, pixels):
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = w * bpp
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter type 0 (none)
        raw += pixels[y*stride:(y+1)*stride]
    idat = zlib.compress(bytes(raw), 9)
    def chunk(typ, data):
        return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))  # 13 bytes: w,h,bits,ctype,compression,filter,interlace
    for i in range(0, len(idat), 65536):
        out += chunk(b"IDAT", idat[i:i+65536])
    out += chunk(b"IEND", b"")
    open(path, "wb").write(out)

def smoothstep(t):
    return t * t * (3 - 2 * t)

def site_bg(layout_path):
    css = open(layout_path).read()
    m = re.search(r"--bg:\s*(#[0-9a-fA-F]{6})", css)
    if not m:
        sys.exit(f"could not find --bg in {layout_path}")
    h = m.group(1)
    return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out", default=None)
    ap.add_argument("--sides", type=int, default=80, help="feather width, left/right (default 80)")
    ap.add_argument("--tb", type=int, default=48, help="feather width, top/bottom (default 48)")
    ap.add_argument("--bg", default=None, help="#RRGGBB (default: --bg from the layout CSS)")
    ap.add_argument("--layout", default=None, help="layout file holding --bg (default: repo _layouts/site.html)")
    a = ap.parse_args()
    out = a.out or a.image
    layout = a.layout or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_layouts", "site.html")
    bg = tuple(int(a.bg[i:i+2], 16) for i in (1, 3, 5)) if a.bg else site_bg(layout)
    w, h, ctype, px = read_png(a.image)
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    px = bytearray(px)
    bgpx = list(bg) + [255]
    # flatten alpha onto bg first, if present
    if ctype in (4, 6):
        for y in range(h):
            for x in range(w):
                i = (y * w + x) * bpp
                al = px[i + bpp - 1] / 255.0
                for c in range(bpp - 1):
                    px[i + c] = round(px[i + c] * al + bgpx[c] * (1 - al))
                px[i + bpp - 1] = 0  # will be feathered + reset below
    sw, tw = min(a.sides, w // 2), min(a.tb, h // 2)
    if sw < 2 or tw < 2:
        sys.exit("image smaller than its feather widths")
    stride = w * bpp
    for y in range(h):
        row = y * stride
        if tw <= y < h - tw:   # interior rows: only the side bands feather
            for x in list(range(sw)) + list(range(w - sw, w)):
                i = row + x * bpp
                tx = smoothstep(x / sw) if x < sw else smoothstep((w - 1 - x) / sw)
                for c in range(bpp):
                    v = bgpx[c] * (1 - tx) + px[i + c] * tx
                    px[i + c] = int(v + 0.5)
                if ctype in (4, 6):
                    px[i + bpp - 1] = 255
            continue
        ty = smoothstep(y / tw) if y < tw else smoothstep((h - 1 - y) / tw)
        for x in range(w):
            tx = smoothstep(x / sw) if x < sw else (smoothstep((w - 1 - x) / sw) if x >= w - sw else 1.0)
            m = tx * ty
            i = row + x * bpp
            for c in range(bpp):
                v = bgpx[c] * (1 - m) + px[i + c] * m
                px[i + c] = int(v + 0.5)
            if ctype in (4, 6):
                px[i + bpp - 1] = 255
    write_png(out, w, h, ctype, bytes(px))
    print(f"feathered {a.image} -> {out}  ({w}x{h}, sides={sw} tb={tw}, bg={'#%02x%02x%02x' % bg})")

if __name__ == "__main__":
    main()
