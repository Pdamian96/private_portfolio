#!/usr/bin/env python3
# make_mask.py
#
# Create a binary mask for Poisson cloning.
# Modes:
#   - alpha: derive from source alpha
#   - range: select by color range in OKLab (via --hex or --pick_x/--pick_y)
#   - flood: magic-wand from a seed (OKLab distance tolerance)
#   - grabcut: OpenCV-based foreground extraction from a rectangle (optional)
#
# Outputs a 1-channel "L" PNG where white(255)=inside, black(0)=outside.
#
# Examples:
#   # 1) Use alpha channel
#   python make_mask.py input.png --mode alpha --out mask.png
#
#   # 2) Color range around a hex color in OKLab (tolerance ~0.05..0.10)
#   python make_mask.py flower.png --mode range --hex FF00AA --tol 0.06 --out mask.png
#
#   # 3) Pick color at (x,y) and use tolerance
#   python make_mask.py flower.png --mode range --pick_x 120 --pick_y 86 --tol 0.055 --out mask.png
#
#   # 4) Magic-wand flood from (x,y) with tolerance
#   python make_mask.py flower.png --mode flood --seed_x 120 --seed_y 86 --tol 0.06 --out mask.png
#
#   # 5) GrabCut from rectangle (x,y,w,h) — requires OpenCV
#   python make_mask.py person.jpg --mode grabcut --rect 80 40 220 300 --out mask.png
#
# Optional cleanups (work in any mode):
#   --erode 1 --dilate 2 --close 1 --feather 1
#
import argparse, numpy as np
from PIL import Image, ImageFilter

# ---------- Color utils (sRGB↔linear, OKLab) ----------
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055) ** 2.4)
def linear_to_srgb(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.0031308, c*12.92, 1.055*(c**(1/2.4)) - 0.055)
def linear_rgb_to_oklab(rgb):
    r,g,b = rgb[...,0], rgb[...,1], rgb[...,2]
    l_ = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m_ = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s_ = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    l_c = np.cbrt(np.maximum(l_,1e-10)); m_c = np.cbrt(np.maximum(m_,1e-10)); s_c = np.cbrt(np.maximum(s_,1e-10))
    L = 0.2104542553*l_c + 0.7936177850*m_c - 0.0040720468*s_c
    a = 1.9779984951*l_c - 2.4285922050*m_c + 0.4505937099*s_c
    b = 0.0259040371*l_c + 0.7827717662*m_c - 0.8086757660*s_c
    return np.stack([L,a,b], axis=-1)

def srgb8_to_oklab(img_rgb8):
    sr = img_rgb8.astype(np.float32)/255.0
    return linear_rgb_to_oklab(srgb_to_linear(sr))

# ---------- Morphology helpers (Pillow-based) ----------
def bin_im(img_bool):
    return Image.fromarray((img_bool.astype(np.uint8)*255), mode="L")
def pil_to_bool(imgL):
    arr = np.asarray(imgL, dtype=np.uint8)
    return arr >= 128

def erode_pil(maskL, n=1):
    out = maskL
    for _ in range(n):
        out = out.filter(ImageFilter.MinFilter(size=3))
    return out
def dilate_pil(maskL, n=1):
    out = maskL
    for _ in range(n):
        out = out.filter(ImageFilter.MaxFilter(size=3))
    return out
def close_pil(maskL, n=1):
    # dilation followed by erosion
    return erode_pil(dilate_pil(maskL, n), n)
def feather_pil(maskL, radius=1.0):
    if radius <= 0: return maskL
    blurred = maskL.filter(ImageFilter.GaussianBlur(radius=radius))
    # Re-binarize at 128 to keep output strictly binary for Poisson
    arr = np.asarray(blurred, dtype=np.uint8)
    return Image.fromarray((arr >= 128).astype(np.uint8)*255, mode="L")

# ---------- Mode implementations ----------
def mode_alpha(img: Image.Image, thr=127):
    A = np.asarray(img.convert("RGBA"))[...,3]
    return Image.fromarray(((A > thr).astype(np.uint8)*255), mode="L")

def _parse_hex(s):
    s = s.strip().lstrip("#")
    if len(s)!=6: raise ValueError("hex must be 6 digits like FF00AA")
    r = int(s[0:2],16); g = int(s[2:4],16); b = int(s[4:6],16)
    return np.array([r,g,b], dtype=np.uint8)

def mode_range(img: Image.Image, tol=0.06, hex_color=None, pick_xy=None):
    """Select pixels within OKLab distance tol of the reference color."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    lab = srgb8_to_oklab(rgb)
    if hex_color is not None:
        ref_rgb = _parse_hex(hex_color)
    elif pick_xy is not None:
        x,y = pick_xy
        H,W = rgb.shape[:2]
        x = int(np.clip(x,0,W-1)); y = int(np.clip(y,0,H-1))
        ref_rgb = rgb[y,x,:]
    else:
        raise ValueError("Provide --hex or --pick_x/--pick_y")
    ref_lab = srgb8_to_oklab(ref_rgb.reshape(1,1,3))[0,0,:]
    d2 = np.sum((lab - ref_lab[None,None,:])**2, axis=2)
    mask = (np.sqrt(d2) <= float(tol))
    return bin_im(mask)

def mode_flood(img: Image.Image, seed_xy, tol=0.06, connectivity=4):
    """Magic-wand: region grow in OKLab from seed within tol."""
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    H,W = rgb.shape[:2]
    sx, sy = int(seed_xy[0]), int(seed_xy[1])
    sx = int(np.clip(sx,0,W-1)); sy = int(np.clip(sy,0,H-1))
    lab = srgb8_to_oklab(rgb)
    ref = lab[sy, sx, :]
    # We’ll accept pixels whose distance to the *seed* is <= tol.
    # (Alternative: mean of region; but seed metric is predictable.)
    d2 = np.sum((lab - ref[None,None,:])**2, axis=2)
    allowed = (np.sqrt(d2) <= float(tol))
    # BFS constrained to allowed pixels
    from collections import deque
    q = deque()
    mask = np.zeros((H,W), dtype=bool)
    if allowed[sy, sx]:
        mask[sy, sx] = True; q.append((sy,sx))
    nb = [(-1,0),(1,0),(0,-1),(0,1)] if connectivity==4 else [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    while q:
        y,x = q.popleft()
        for dy,dx in nb:
            yy = y+dy; xx = x+dx
            if 0<=yy<H and 0<=xx<W and (not mask[yy,xx]) and allowed[yy,xx]:
                mask[yy,xx] = True
                q.append((yy,xx))
    return bin_im(mask)

def mode_grabcut(img: Image.Image, rect_xywh):
    """GrabCut foreground extraction; requires OpenCV."""
    try:
        import cv2
    except Exception:
        raise RuntimeError("OpenCV not available. Install: pip install opencv-python")
    rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)
    H,W = rgb.shape[:2]
    x,y,w,h = rect_xywh
    x = int(np.clip(x,0,W-1)); y = int(np.clip(y,0,H-1))
    w = int(np.clip(w,1,W-x)); h = int(np.clip(h,1,H-y))
    mask = np.zeros((H,W), np.uint8)
    bgdModel = np.zeros((1,65), np.float64)
    fgdModel = np.zeros((1,65), np.float64)
    cv2.grabCut(rgb, mask, (x,y,w,h), bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
    # mask: 0=bg, 2=prob bg → 0 ; 1=fg, 3=prob fg → 1
    m = np.where((mask==1) | (mask==3), 255, 0).astype(np.uint8)
    return Image.fromarray(m, mode="L")

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="Create a binary mask for Poisson cloning.")
    ap.add_argument("image", help="Input image")
    ap.add_argument("--mode", choices=["alpha","range","flood","grabcut"], required=True)
    ap.add_argument("--out", required=True, help="Output mask path (PNG recommended)")

    # alpha
    ap.add_argument("--alpha_thr", type=int, default=127)

    # range
    ap.add_argument("--hex", type=str, default=None, help="Ref color hex like FF00AA")
    ap.add_argument("--pick_x", type=int, default=None, help="Pick reference from this x")
    ap.add_argument("--pick_y", type=int, default=None, help="Pick reference from this y")
    ap.add_argument("--tol", type=float, default=0.06, help="OKLab distance tolerance (~0.04 tight … 0.1 loose)")

    # flood
    ap.add_argument("--seed_x", type=int, default=None)
    ap.add_argument("--seed_y", type=int, default=None)
    ap.add_argument("--conn", type=int, default=4, choices=[4,8])

    # grabcut
    ap.add_argument("--rect", type=int, nargs=4, metavar=("x","y","w","h"),
                    help="GrabCut rectangle in the input image (requires OpenCV)")

    # cleanups
    ap.add_argument("--erode", type=int, default=0, help="Erode N times (shrinks mask)")
    ap.add_argument("--dilate", type=int, default=0, help="Dilate N times (grows mask)")
    ap.add_argument("--close", type=int, default=0, help="Close N (dilate then erode) to fill small holes")
    ap.add_argument("--feather", type=float, default=0.0, help="Feather radius (px); re-binarizes at 128")

    args = ap.parse_args()
    img = Image.open(args.image)

    if args.mode == "alpha":
        mask = mode_alpha(img, thr=args.alpha_thr)

    elif args.mode == "range":
        ref = None
        if args.hex is not None:
            ref = args.hex
        elif args.pick_x is not None and args.pick_y is not None:
            ref = (args.pick_x, args.pick_y)
        else:
            raise SystemExit("range mode needs --hex FF00AA or --pick_x/--pick_y")
        if isinstance(ref, tuple):
            mask = mode_range(img, tol=args.tol, pick_xy=ref)
        else:
            mask = mode_range(img, tol=args.tol, hex_color=ref)

    elif args.mode == "flood":
        if args.seed_x is None or args.seed_y is None:
            raise SystemExit("flood mode needs --seed_x and --seed_y")
        mask = mode_flood(img, seed_xy=(args.seed_x, args.seed_y), tol=args.tol, connectivity=args.conn)

    elif args.mode == "grabcut":
        if not args.rect:
            raise SystemExit("grabcut mode needs --rect x y w h")
        mask = mode_grabcut(img, rect_xywh=tuple(args.rect))

    # post-process
    if args.erode > 0:   mask = erode_pil(mask, n=args.erode)
    if args.dilate > 0:  mask = dilate_pil(mask, n=args.dilate)
    if args.close > 0:   mask = close_pil(mask, n=args.close)
    if args.feather > 0: mask = feather_pil(mask, radius=args.feather)

    mask.save(args.out)
    print(f"Saved mask to {args.out}")

if __name__ == "__main__":
    main()
