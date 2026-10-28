#!/usr/bin/env python3
"""
Folder er sob image e logo boshanor script.

Install:  pip install Pillow pillow-heif

Use:
  python add_logo.py -i ./photos -l ./logo.png -o ./output -p bottom-right
  python add_logo.py -i ./photos -l ./logo.png -p top-left --scale 0.2 --opacity 0.8

Position gulo:
  top-left      top-center      top-right
  middle-left   middle-center   middle-right
  bottom-left   bottom-center   bottom-right
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()  # Pillow ke HEIC/HEIF porte ar likhte shekhay
    HEIF_OK = True
except ImportError:
    HEIF_OK = False

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
if HEIF_OK:
    SUPPORTED |= {".heic", ".heif"}

# (column, row) -> 0 = left/top, 1 = center/middle, 2 = right/bottom
POSITIONS = {
    "top-left": (0, 0),    "top-center": (1, 0),    "top-right": (2, 0),
    "middle-left": (0, 1), "middle-center": (1, 1), "middle-right": (2, 1),
    "bottom-left": (0, 2), "bottom-center": (1, 2), "bottom-right": (2, 2),
}


def prepare_logo(logo, img_w, img_h, scale, opacity):
    """Image er size onujayi logo resize kore (LANCZOS = best quality resampling)."""
    target_w = max(1, int(min(img_w, img_h) * scale))
    target_h = max(1, round(logo.height * target_w / logo.width))
    resized = logo.resize((target_w, target_h), Image.LANCZOS)
    if opacity < 1.0:
        alpha = resized.getchannel("A").point(lambda a: int(a * opacity))
        resized.putalpha(alpha)
    return resized


def calc_position(position, img_w, img_h, logo_w, logo_h, margin):
    col, row = POSITIONS[position]
    x = [margin, (img_w - logo_w) // 2, img_w - logo_w - margin][col]
    y = [margin, (img_h - logo_h) // 2, img_h - logo_h - margin][row]
    return x, y


def save_high_quality(img, out_path, fmt, exif, icc):
    """Format onujayi sobcheye high quality setting diye save kore."""
    params = {}
    if fmt in ("JPEG", "PNG", "WEBP", "TIFF", "HEIF"):
        if icc:
            params["icc_profile"] = icc
        if exif:
            params["exif"] = exif

    if fmt == "JPEG":
        if img.mode != "RGB":
            img = img.convert("RGB")
        params.update(quality=100, subsampling=0)  # 4:4:4, kono color loss nai
    elif fmt == "WEBP":
        params.update(lossless=True, quality=100)
    elif fmt == "HEIF":
        params.update(quality=100)               # sobcheye high quality
    elif fmt == "TIFF":
        params.update(compression="tiff_lzw")    # lossless
    # PNG / BMP emnitei lossless

    img.save(out_path, fmt, **params)


def process_image(path, logo, out_dir, args):
    with Image.open(path) as original:
        fmt = original.format or "PNG"
        icc = original.info.get("icc_profile")
        had_alpha = original.mode in ("RGBA", "LA", "P") and fmt != "JPEG"

        # Phone er chobi ulta/ghurano thakle thik kore nei
        exif = original.getexif()
        img = ImageOps.exif_transpose(original)
        if 0x0112 in exif:
            exif[0x0112] = 1  # orientation already fix kora hoyeche
        exif_bytes = exif.tobytes() if len(exif) else None

        base = img.convert("RGBA")
        w, h = base.size
        logo_img = prepare_logo(logo, w, h, args.scale, args.opacity)
        margin = int(min(w, h) * args.margin)
        x, y = calc_position(args.position, w, h, *logo_img.size, margin)

        base.alpha_composite(logo_img, (x, y))
        result = base if had_alpha else base.convert("RGB")

        out_path = out_dir / f"{path.stem}{args.suffix}{path.suffix}"
        save_high_quality(result, out_path, fmt, exif_bytes, icc)
        return out_path


def main():
    p = argparse.ArgumentParser(description="Folder er sob image e logo boshao")
    p.add_argument("-i", "--input", required=True, help="Image folder")
    p.add_argument("-l", "--logo", required=True, help="Logo file (transparent PNG best)")
    p.add_argument("-o", "--output", default=None, help="Output folder (default: input/with_logo)")
    p.add_argument("-p", "--position", default="bottom-right", choices=POSITIONS.keys())
    p.add_argument("--scale", type=float, default=0.15,
                   help="Logo er width, image er choto side er koto bhag (default 0.15 = 15%%)")
    p.add_argument("--margin", type=float, default=0.03,
                   help="Kinara theke dure thakbe, choto side er koto bhag (default 0.03)")
    p.add_argument("--opacity", type=float, default=1.0, help="0.0 - 1.0 (default 1.0)")
    p.add_argument("--suffix", default="", help="Output file namer sheshe ja jog hobe, jemon _logo")
    args = p.parse_args()

    in_dir = Path(args.input)
    if not in_dir.is_dir():
        sys.exit(f"Folder pawa jayni: {in_dir}")
    out_dir = Path(args.output) if args.output else in_dir / "with_logo"
    out_dir.mkdir(parents=True, exist_ok=True)

    logo = Image.open(args.logo).convert("RGBA")
    if not HEIF_OK and any(f.suffix.lower() in (".heic", ".heif") for f in in_dir.iterdir()):
        print("⚠ HEIC file ache kintu pillow-heif install nai. Chalao: pip install pillow-heif\n")

    files = [f for f in sorted(in_dir.iterdir())
             if f.is_file() and f.suffix.lower() in SUPPORTED]
    if not files:
        sys.exit("Folder e kono supported image nai.")

    ok = 0
    for f in files:
        try:
            out = process_image(f, logo, out_dir, args)
            print(f"✔ {f.name} -> {out}")
            ok += 1
        except Exception as e:
            print(f"✘ {f.name}: {e}")
    print(f"\nShesh! {ok}/{len(files)} ta image save hoyeche: {out_dir}")


if __name__ == "__main__":
    main()