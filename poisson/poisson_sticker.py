#!/usr/bin/env python3
# poisson_sticker.py
# Seamless cloning ("Poisson sticker"): paste a masked region from src into dst.
# Modes: classic Poisson (use src gradients) or mixed gradients.
# Deps: numpy, Pillow; SciPy optional (for fast solve).

import argparse, numpy as np
from PIL import Image

# -------- sRGB <-> linear helpers (avoid gamma artifacts) --------
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055)/1.055) ** 2.4)

def linear_to_srgb(c):
    c = np.asarray(c, dtype=np.float32)
    out = np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1/2.4)) - 0.055)
    return np.clip(out, 0.0, 1.0)

# -------- sparse solver (SciPy if available; else Gauss-Seidel) --------
def solve_spd(A_data, A_rows, A_cols, b, shape, use_scipy=True, tol=1e-6, max_iter=4000):
    """
    Solve A x = b for SPD A. A given in COO lists. Returns x (float32).
    """
    if use_scipy:
        try:
            import scipy.sparse as sp
            import scipy.sparse.linalg as spla
            A = sp.coo_matrix((A_data, (A_rows, A_cols)), shape=shape).tocsr()
            x = spla.spsolve(A, b)
            return x.astype(np.float32)
        except Exception:
            pass  # fall back to Gauss–Seidel

    # Build CSR-ish structure for naive Gauss–Seidel (small masks only)
    N = shape[0]
    diag = np.zeros(N, dtype=np.float32)
    rows = [[] for _ in range(N)]
    vals = [[] for _ in range(N)]
    for a, r, c in zip(A_data, A_rows, A_cols):
        if r == c:
            diag[r] = a
        else:
            rows[r].append(c)
            vals[r].append(a)
    x = np.zeros_like(b, dtype=np.float32)
    for it in range(max_iter):
        max_res = 0.0
        for i in range(N):
            s = 0.0
            for j, aij in zip(rows[i], vals[i]):
                s += aij * x[j]
            new_xi = (b[i] - s) / (diag[i] if diag[i] != 0 else 1.0)
            max_res = max(max_res, abs(new_xi - x[i]))
            x[i] = new_xi
        if max_res < tol:
            break
    return x

# -------- core Poisson/mixed cloning --------
def poisson_clone(src_img: Image.Image,
                  dst_img: Image.Image,
                  mask_img: Image.Image,
                  offset_xy=(0,0),
                  mode="mixed",   # "poisson" or "mixed"
                  use_scipy=True):
    """
    src_img: RGBA/RGB pasted onto dst_img (RGB/RGBA) using mask_img (same size as src).
    offset_xy: (y, x) top-left where src(0,0) maps into dst.
    Returns: PIL.Image RGB
    """
    # Prepare arrays
    src_rgba = src_img.convert("RGBA")
    dst_rgb  = dst_img.convert("RGB")
    mask     = np.asarray(mask_img.convert("L")) > 127

    sh, sw = src_rgba.height, src_rgba.width
    dh, dw = dst_rgb.height,  dst_rgb.width
    oy, ox = int(offset_xy[0]), int(offset_xy[1])

    # Compute which mask pixels land INSIDE dst
    ys, xs = np.nonzero(mask)
    yd = ys + oy
    xd = xs + ox
    inside = (yd >= 0) & (yd < dh) & (xd >= 0) & (xd < dw)
    ys, xs, yd, xd = ys[inside], xs[inside], yd[inside], xd[inside]

    # Rebuild a compact mask Ω only for valid placements
    omega = np.zeros((sh, sw), dtype=bool)
    omega[ys, xs] = True

    # Early exit if nothing to do
    if ys.size == 0:
        return dst_rgb.copy()

    # Index map: pixel in Ω -> linear unknown index
    idx_map = -np.ones((sh, sw), dtype=np.int32)
    idx_map[ys, xs] = np.arange(ys.size, dtype=np.int32)
    N = ys.size

    # Convert to linear RGB float
    src_arr = np.asarray(src_rgba, dtype=np.float32) / 255.0  # RGBA
    dst_arr = np.asarray(dst_rgb,  dtype=np.float32) / 255.0  # RGB
    src_lin = srgb_to_linear(src_arr[..., :3])
    dst_lin = srgb_to_linear(dst_arr)

    # Build sparse system A x = b per channel (A same for all)
    A_rows, A_cols, A_data = [], [], []
    # neighbor offsets (4-connectivity)
    nbs = [(-1,0), (1,0), (0,-1), (0,1)]

    # Precompute destination samples for guidance (in dst coords)
    def sample_dst(y, x):
        y = np.clip(y, 0, dh-1); x = np.clip(x, 0, dw-1)
        return dst_lin[y, x]

    # Assemble A once; assemble b per channel later
    # A has 4 on diagonal, -1 for each neighbor inside Ω
    for k, (sy, sx, dy, dx) in enumerate(zip(ys, xs, yd, xd)):
        A_rows.append(k); A_cols.append(k); A_data.append(4.0)
        for (dy_off, dx_off) in nbs:
            sy2, sx2 = sy + dy_off, sx + dx_off
            dy2, dx2 = dy + dy_off, dx + dx_off
            if 0 <= sy2 < sh and 0 <= sx2 < sw and omega[sy2, sx2]:
                # neighbor inside Ω → -1 coefficient
                A_rows.append(k); A_cols.append(idx_map[sy2, sx2]); A_data.append(-1.0)

    # Build and solve per channel
    out_lin = dst_lin.copy()
    for ch in range(3):
        b = np.zeros(N, dtype=np.float32)
        for k, (sy, sx, dy, dx) in enumerate(zip(ys, xs, yd, xd)):
            acc = 0.0
            for (dy_off, dx_off) in nbs:
                sy2, sx2 = sy + dy_off, sx + dx_off
                dy2, dx2 = dy + dy_off, dx + dx_off

                # Guidance (v_pq)
                v = 0.0
                if 0 <= sy2 < sh and 0 <= sx2 < sw:
                    src_grad = src_lin[sy, sx, ch] - src_lin[sy2, sx2, ch]
                else:
                    src_grad = 0.0
                dst_grad = sample_dst(dy, dx)[ch] - sample_dst(dy2, dx2)[ch]
                if mode == "mixed":
                    v = src_grad if abs(src_grad) >= abs(dst_grad) else dst_grad
                else:  # "poisson"
                    v = src_grad

                if 0 <= sy2 < sh and 0 <= sx2 < sw and omega[sy2, sx2]:
                    # neighbor inside Ω: b accumulates guidance only
                    acc += v
                else:
                    # neighbor outside Ω: add guidance + boundary term (dst neighbor value)
                    acc += v + sample_dst(dy2, dx2)[ch]
            b[k] = acc

        x = solve_spd(np.array(A_data, dtype=np.float32),
                      np.array(A_rows, dtype=np.int32),
                      np.array(A_cols, dtype=np.int32),
                      b, (N, N), use_scipy=use_scipy)

        # place solution back into dst (linear domain)
        out_lin[yd, xd, ch] = x

    # Back to sRGB 8-bit
    out_srgb = linear_to_srgb(out_lin)
    out_uint8 = (np.clip(out_srgb, 0, 1) * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(out_uint8, mode="RGB")

# -------- CLI --------
def main():
    ap = argparse.ArgumentParser(description="Poisson (seamless) cloning / mixed gradients.")
    ap.add_argument("--src",  required=True, help="Source image (RGB/RGBA)")
    ap.add_argument("--dst",  required=True, help="Destination image (RGB/RGBA)")
    ap.add_argument("--mask", required=True, help="Binary mask (white=in region). Same size as src.")
    ap.add_argument("--x", type=int, required=True, help="Left X in destination")
    ap.add_argument("--y", type=int, required=True, help="Top Y in destination")
    ap.add_argument("--mode", choices=["poisson","mixed"], default="mixed", help="Guidance field mode")
    ap.add_argument("--no-scipy", action="store_true", help="Force fallback (slow) iterative solver")
    ap.add_argument("--out", default="sticker_out.png", help="Output image")
    args = ap.parse_args()

    src  = Image.open(args.src)
    dst  = Image.open(args.dst)
    mask = Image.open(args.mask)

    out = poisson_clone(src, dst, mask, offset_xy=(args.y, args.x), mode=args.mode, use_scipy=not args.no_scipy)
    out.save(args.out)
    print(f"Saved {args.out}")

if __name__ == "__main__":
    main()
