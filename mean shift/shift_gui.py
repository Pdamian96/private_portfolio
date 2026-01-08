#!/usr/bin/env python3
# pixel_palette_gui.py
#
# Pixel-art palette extractor / quantizer with a GUI.
# Core: OKLab mean-shift on UNIQUE colors (fast), single sensitivity knob,
# accent rescue, outline de-bias, tiny spatial coherence.
# New toggles: Exact-K palette, Medoid centers, Hue protection (with ranges),
# Performance mode (caps unique colors, faster iterations).
# Built-in progress bar, inline previews, optional 3D OKLab scatter.
#
# Deps: pip install pillow numpy  (matplotlib optional for 3D)
# Run:  python pixel_palette_gui.py

import os, io, sys, time, json, threading
import numpy as np
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ----------------------------
# Color space utilities
# ----------------------------
def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def linear_to_srgb(c):
    c = np.asarray(c, dtype=np.float32)
    out = np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1/2.4)) - 0.055)
    return np.clip(out, 0.0, 1.0)

def linear_rgb_to_oklab(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_c = np.cbrt(np.maximum(l_, 1e-10))
    m_c = np.cbrt(np.maximum(m_, 1e-10))
    s_c = np.cbrt(np.maximum(s_, 1e-10))
    L = 0.2104542553 * l_c + 0.7936177850 * m_c - 0.0040720468 * s_c
    a = 1.9779984951 * l_c - 2.4285922050 * m_c + 0.4505937099 * s_c
    b = 0.0259040371 * l_c + 0.7827717662 * m_c - 0.8086757660 * s_c
    return np.stack([L, a, b], axis=-1)

def _oklab_of_srgb01(c01):
    return linear_rgb_to_oklab(srgb_to_linear(np.asarray(c01, dtype=np.float32)))

def _hue_deg_from_ab(a, b):
    ang = np.degrees(np.arctan2(b, a))
    return np.where(ang < 0, ang + 360.0, ang)

def _circ_dist_deg(h1, h2):
    return np.abs((h1 - h2 + 180.0) % 360.0 - 180.0)

# ----------------------------
# Progress helper (GUI-friendly)
# ----------------------------
def _progress_cb_factory(setter_fn):
    last = {'t': 0.0}
    def cb(i, total):
        now = time.time()
        if i == 0 or i == total or (now - last['t']) >= 0.03:
            last['t'] = now
            frac = 1.0 if total <= 0 else max(0.0, min(1.0, i/total))
            setter_fn(frac)
    return cb

# ----------------------------
# Mean-shift (Gaussian kernel)
# ----------------------------
def mean_shift(points: np.ndarray, bandwidth: float, max_iters: int = 15, eps: float = 2e-4,
               weights: np.ndarray = None, progress_cb=None):
    """
    Weighted Gaussian mean-shift on points (N, D).
    Here N is #unique colors (hundreds/thousands), not total pixels.
    """
    N, D = points.shape
    if N == 0:
        return np.empty_like(points), np.zeros(0, dtype=np.int32)
    X = points.astype(np.float32, copy=False)
    modes = X.copy()
    iters = np.zeros(N, dtype=np.int32)
    w = np.ones(N, dtype=np.float32) if weights is None else weights.astype(np.float32)
    bw2 = max(1e-9, bandwidth * bandwidth)

    for i in range(N):
        if progress_cb: progress_cb(i, N)
        y = modes[i]
        for _ in range(max_iters):
            diff = X - y
            d2 = np.einsum('ij,ij->i', diff, diff)
            kw = np.exp(-0.5 * d2 / bw2) * w
            s = kw.sum()
            if s <= 1e-12:
                break
            y_new = (kw[:, None] * X).sum(axis=0) / s
            if np.linalg.norm(y_new - y) < eps:
                y = y_new; iters[i]+=1; break
            y = y_new; iters[i]+=1
        modes[i] = y
    if progress_cb: progress_cb(N, N)
    return modes, iters

def assign_clusters(modes: np.ndarray, merge_radius: float):
    """Greedy merge: assign each mode to the first center within merge_radius, else create new."""
    labels = -np.ones(modes.shape[0], dtype=np.int32)
    centers = []
    for i, m in enumerate(modes):
        for k, c in enumerate(centers):
            if np.linalg.norm(m - c) <= merge_radius:
                labels[i] = k
                break
        if labels[i] < 0:
            labels[i] = len(centers)
            centers.append(m.copy())
    if centers:
        centers = np.vstack(centers)
    else:
        centers = np.zeros((0, modes.shape[1]), dtype=np.float32)
    return labels, centers

# ----------------------------
# Sensitivity mapping
# ----------------------------
def map_sensitivity(sens: float, perf=False):
    s = float(np.clip(sens, 0.0, 1.0))
    bandwidth       = (1.0 - s) * 0.095 + s * 0.045   # 0:0.095 .. 1:0.045
    merge_radius    = bandwidth * 0.30
    min_cluster_frac= (1.0 - s) * 0.015 + s * 0.001   # 0:1.5% .. 1:0.1%
    spatial_lambda  = (1.0 - s) * 0.009 + s * 0.003   # tiny spatial coherence
    rescue_delta    = 0.045 - 0.02 * s
    min_accent_frac = min_cluster_frac * 0.3

    if perf:
        bandwidth *= 1.05
        merge_radius *= 1.1
        spatial_lambda = 0.0
        min_cluster_frac = max(min_cluster_frac, 0.002)

    return bandwidth, merge_radius, min_cluster_frac, spatial_lambda, rescue_delta, min_accent_frac

# ----------------------------
# Hue protection helpers
# ----------------------------
def _parse_hue_ranges(spec: str):
    ranges = []
    for tok in (spec or "").split(","):
        tok = tok.strip()
        if not tok or "-" not in tok: continue
        a, b = tok.split("-", 1)
        try:
            lo = float(a) % 360.0
            hi = float(b) % 360.0
            ranges.append((lo, hi))
        except Exception:
            pass
    return ranges

def _hue_in_ranges(h, ranges):
    for lo, hi in ranges:
        if lo <= hi:
            if (h >= lo) and (h <= hi): return True
        else:  # wraparound (e.g., 350-20)
            if (h >= lo) or (h <= hi): return True
    return False

# ----------------------------
# Core pipeline on UNIQUE colors (fast path)
# ----------------------------
def palette_oklab_meanshift(
    img: Image.Image,
    sensitivity: float,
    progress_cb=None,
    perf=False,
    hue_protect=False,
    protect_ranges=None,
    topN_unique=5000
):
    arr_rgba = np.asarray(img.convert("RGBA"))
    alpha_mask = arr_rgba[..., 3] > 127
    if not np.any(alpha_mask):
        raise ValueError("No opaque pixels found.")

    H, W = arr_rgba.shape[:2]
    rgb8 = arr_rgba[alpha_mask, :3]  # (P,3) uint8
    uniq, inverse, counts = np.unique(rgb8, axis=0, return_inverse=True, return_counts=True)

    # Performance cap for unique colors
    if perf and uniq.shape[0] > topN_unique:
        order = np.argsort(-counts)
        keep = order[:topN_unique]
        old2new = -np.ones(uniq.shape[0], dtype=np.int32)
        old2new[keep] = np.arange(keep.shape[0], dtype=np.int32)
        inverse_new = old2new[inverse]
        dropped_mask = inverse_new < 0
        if np.any(dropped_mask):
            src = uniq[inverse[dropped_mask]].astype(np.int16)
            pal = uniq[keep].astype(np.int16)
            d2 = np.sum((src[:, None, :] - pal[None, :, :])**2, axis=2)
            nearest = np.argmin(d2, axis=1)
            inverse_new[dropped_mask] = nearest
        counts_new = np.zeros(keep.shape[0], dtype=np.int64)
        np.add.at(counts_new, inverse_new, 1)
        uniq = uniq[keep]; counts = counts_new; inverse = inverse_new

    U = uniq.shape[0]
    total_pixels = float(counts.sum())

    # Average (x,y) per unique color
    ys, xs = np.nonzero(alpha_mask)
    xs = xs.astype(np.float32); ys = ys.astype(np.float32)
    sum_x = np.zeros(U, dtype=np.float32); np.add.at(sum_x, inverse, xs)
    sum_y = np.zeros(U, dtype=np.float32); np.add.at(sum_y, inverse, ys)
    nx = (sum_x / counts) / max(1.0, (W - 1))
    ny = (sum_y / counts) / max(1.0, (H - 1))

    srgb_u = uniq.astype(np.float32) / 255.0
    rgb_lin = srgb_to_linear(srgb_u)
    lab_u   = linear_rgb_to_oklab(rgb_lin)
    a_u, b_u = lab_u[:,1], lab_u[:,2]
    hue_u    = _hue_deg_from_ab(a_u, b_u)
    chroma_u = np.sqrt(a_u*a_u + b_u*b_u)

    # Outline de-bias (only near-black penalized)
    L = lab_u[:, 0]
    debias = 0.4 + 0.6 * np.clip((L - 0.10) / 0.70, 0.0, 1.0)

    bandwidth, merge_radius, min_cluster_frac, spatial_lambda, rescue_delta, min_accent_frac = map_sensitivity(sensitivity, perf=perf)

    feat = lab_u if spatial_lambda <= 0 else np.concatenate([lab_u, np.stack([nx, ny], axis=1) * spatial_lambda], axis=1)

    weights = counts.astype(np.float32) * debias
    ms_iters = 10 if perf else 15
    ms_eps   = 5e-4 if perf else 2e-4
    modes, iters = mean_shift(feat, bandwidth=bandwidth, max_iters=ms_iters, eps=ms_eps, weights=weights, progress_cb=progress_cb)

    labels_u, centers = assign_clusters(modes, merge_radius=merge_radius)

    clusters = []
    label_to_kept = {}
    kept_labs = []
    dropped = []

    for k in range(centers.shape[0]):
        idx = np.where(labels_u == k)[0]
        if idx.size == 0: continue
        frac = float(counts[idx].sum()) / total_pixels
        wsum = float(weights[idx].sum())
        if wsum <= 1e-12: continue

        mean_lin  = (rgb_lin[idx] * weights[idx, None]).sum(axis=0) / wsum
        mean_srgb = linear_to_srgb(mean_lin)
        mean_lab  = (lab_u[idx] * weights[idx, None]).sum(axis=0) / wsum
        m_a, m_b = mean_lab[1], mean_lab[2]
        mean_hue = float(_hue_deg_from_ab(m_a, m_b))
        mean_chroma = float(np.sqrt(m_a*m_a + m_b*m_b))

        keep = frac >= min_cluster_frac
        if hue_protect:
            if protect_ranges and _hue_in_ranges(mean_hue, protect_ranges):
                keep = frac >= min(0.0005, min_accent_frac*0.5) or keep
            if (mean_chroma >= 0.05) and (frac >= min(0.0005, min_accent_frac*0.5)):
                keep = True or keep

        if keep:
            kept_index = len(clusters)
            clusters.append({"center_srgb": mean_srgb.tolist(), "weight": frac, "size": int(counts[idx].sum()),
                             "hue": mean_hue, "chroma": mean_chroma})
            label_to_kept[k] = kept_index
            kept_labs.append((k, mean_lab, mean_hue, mean_chroma))
        else:
            dropped.append((k, frac, int(counts[idx].sum()), mean_lab, mean_srgb, mean_hue, mean_chroma))

    # Accent / hue rescue
    if kept_labs:
        kept_means = np.stack([ml for (_, ml, _, _) in kept_labs], axis=0)
        kept_hues  = np.array([hh for (_, _, hh, _) in kept_labs], dtype=np.float32)
        for (k, frac, size, mean_lab, mean_srgb, mean_hue, mean_chroma) in dropped:
            if frac < min_accent_frac:
                if hue_protect:
                    if protect_ranges and _hue_in_ranges(mean_hue, protect_ranges):
                        pass
                    elif mean_chroma >= 0.06:
                        pass
                    else:
                        continue
                else:
                    continue
            eu = np.sqrt(((kept_means - mean_lab)**2).sum(axis=1))
            hue_d = np.min(_circ_dist_deg(kept_hues, mean_hue)) if kept_hues.size else 180.0
            rescue_by_lab = (np.min(eu) > (rescue_delta if not hue_protect else (rescue_delta * 0.9)))
            rescue_by_hue = hue_protect and (hue_d > 18.0) and (mean_chroma >= 0.045)
            if rescue_by_lab or rescue_by_hue:
                kept_index = len(clusters)
                clusters.append({"center_srgb": mean_srgb.tolist(), "weight": frac, "size": size,
                                 "hue": mean_hue, "chroma": mean_chroma})
                label_to_kept[k] = kept_index
    elif dropped:
        k, frac, size, mean_lab, mean_srgb, mean_hue, mean_chroma = max(dropped, key=lambda t: t[1])
        kept_index = len(clusters)
        clusters.append({"center_srgb": mean_srgb.tolist(), "weight": frac, "size": size,
                         "hue": mean_hue, "chroma": mean_chroma})
        label_to_kept[k] = kept_index

    # Normalize weights
    sw = sum(c["weight"] for c in clusters) or 1.0
    for c in clusters: c["weight"] /= sw

    # Palette-aware global average
    avg_lin = np.zeros(3, dtype=np.float32)
    for c in clusters:
        avg_lin += srgb_to_linear(np.array(c["center_srgb"])) * c["weight"]
    avg_srgb = linear_to_srgb(avg_lin)

    debug = {
        "num_input_pixels": int(total_pixels),
        "num_unique_colors": int(U),
        "num_clusters": len(clusters),
        "mean_iters": float(iters.mean() if len(iters) else 0.0),
        "max_iters": int(iters.max() if len(iters) else 0),
        "bandwidth": float(bandwidth),
        "merge_radius": float(merge_radius),
        "min_cluster_frac": float(min_cluster_frac),
        "spatial_lambda": float(spatial_lambda),
        "rescue_delta": float(rescue_delta),
        "min_accent_frac": float(min_accent_frac),
        "sensitivity": float(sensitivity),
        "perf": bool(perf)
    }

    return clusters, avg_srgb.tolist(), labels_u, inverse, alpha_mask, (H, W), label_to_kept, uniq, counts, debug

# ----------------------------
# Exact-K merge & Medoid centers
# ----------------------------
def merge_to_k_clusters(clusters, target_k, hue_protect=False):
    if target_k is None or target_k <= 0 or len(clusters) <= target_k:
        return clusters
    C = np.array([c["center_srgb"] for c in clusters], dtype=np.float32)
    W = np.array([c["weight"] for c in clusters], dtype=np.float32)
    L = _oklab_of_srgb01(C)
    H = _hue_deg_from_ab(L[:,1], L[:,2])
    K = list(range(len(clusters)))
    while len(K) > target_k:
        Li = L[K]; Wi = W[K]; Hi = H[K]
        d2 = np.sum((Li[:,None,:]-Li[None,:,:])**2, axis=2); np.fill_diagonal(d2, np.inf)
        if hue_protect:
            hue_d = _circ_dist_deg(Hi[:,None], Hi[None,:])
            small = (Wi[:,None] < 0.08) & (Wi[None,:] < 0.08)
            d2 = d2 * (1.0 + 3.0*(hue_d/45.0)*small)
        a,b = np.unravel_index(np.argmin(d2), d2.shape)
        i,j = K[a], K[b]
        wi,wj = W[i], W[j]
        C[i] = (C[i]*wi + C[j]*wj)/(wi+wj) if (wi+wj)>1e-12 else (C[i]+C[j])*0.5
        W[i] = wi+wj
        Li_i = _oklab_of_srgb01(C[i][None,:])[0]
        L[i] = Li_i; H[i] = _hue_deg_from_ab(Li_i[1], Li_i[2])
        K.remove(j)
    W = W / (W.sum() if W.sum()>0 else 1.0)
    merged = []
    for k in K:
        merged.append({
            "center_srgb": C[k].tolist(),
            "weight": float(W[k]),
            "size": None,
            "hue": float(H[k]),
            "chroma": float(np.sqrt(L[k,1]*L[k,1] + L[k,2]*L[k,2]))
        })
    sw = sum(c["weight"] for c in merged) or 1.0
    for c in merged: c["weight"] /= sw
    return merged

def apply_medoid_centers(clusters, unique_labels, label_to_kept, uniq_srgb):
    if not clusters: return clusters
    centers = np.array([c["center_srgb"] for c in clusters], dtype=np.float32)
    centers_lab = _oklab_of_srgb01(centers)
    uniq01 = (uniq_srgb.astype(np.float32)/255.0)
    uniq_lab = _oklab_of_srgb01(uniq01)
    members = [[] for _ in range(len(clusters))]
    for u, lab in enumerate(unique_labels):
        if lab in label_to_kept:
            members[label_to_kept[lab]].append(u)
    new_clusters = []
    for k, c in enumerate(clusters):
        if not members[k]: new_clusters.append(c); continue
        m = np.array(members[k], dtype=np.int32)
        d2 = np.sum((uniq_lab[m] - centers_lab[k][None,:])**2, axis=1)
        u_best = m[np.argmin(d2)]
        cc = dict(c)
        cc["center_srgb"] = (uniq01[u_best]).tolist()
        new_clusters.append(cc)
    return new_clusters

# ----------------------------
# Render helpers (return PIL Images)
# ----------------------------
def render_palette_strip(clusters, height=60, width=420):
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    x = 0
    for c in clusters:
        w = max(1, int(width * c["weight"]))
        r, g, b = [int(round(255 * v)) for v in c["center_srgb"]]
        draw.rectangle([x, 0, x + w - 1, height - 1], fill=(r, g, b))
        x += w
    return img

def _map_unique_to_colors(unique_labels, uniq_srgb, clusters, label_to_kept):
    U = unique_labels.shape[0]
    if len(clusters) == 0: return uniq_srgb.copy()
    centers_srgb = np.array([c["center_srgb"] for c in clusters], dtype=np.float32)
    centers_lab  = linear_rgb_to_oklab(srgb_to_linear(centers_srgb))
    kept_mask_u = np.array([ul in label_to_kept for ul in unique_labels], dtype=bool)
    out = np.zeros((U, 3), dtype=np.uint8)
    if np.any(kept_mask_u):
        kept_idx = np.where(kept_mask_u)[0]
        kept_cluster_idx = np.array([label_to_kept[unique_labels[u]] for u in kept_idx], dtype=np.int32)
        kept_colors = (centers_srgb[kept_cluster_idx] * 255.0).round().astype(np.uint8)
        out[kept_idx] = kept_colors
    dropped_idx = np.where(~kept_mask_u)[0]
    if dropped_idx.size > 0:
        uniq_lin = srgb_to_linear(uniq_srgb[dropped_idx].astype(np.float32) / 255.0)
        uniq_lab = linear_rgb_to_oklab(uniq_lin)
        d2 = np.sum((uniq_lab[:, None, :] - centers_lab[None, :, :]) ** 2, axis=2)
        nearest = np.argmin(d2, axis=1)
        out[dropped_idx] = (centers_srgb[nearest] * 255.0).round().astype(np.uint8)
    return out

def render_cluster_viz(unique_labels, inverse, alpha_mask, shape_hw, clusters, label_to_kept, uniq_srgb):
    H, W = shape_hw
    uniq_to_color = _map_unique_to_colors(unique_labels, uniq_srgb, clusters, label_to_kept)
    pix_colors = uniq_to_color[inverse]
    out = np.zeros((H, W, 3), dtype=np.uint8)
    ys, xs = np.nonzero(alpha_mask)
    out[ys, xs] = pix_colors
    return Image.fromarray(out, mode="RGB")

def render_quantized(unique_labels, inverse, alpha_mask, shape_hw, clusters, label_to_kept, uniq_srgb):
    return render_cluster_viz(unique_labels, inverse, alpha_mask, shape_hw, clusters, label_to_kept, uniq_srgb)

def render_oklab3d(uniq_srgb, counts, figsize=(800, 600)):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa
    except Exception:
        return None
    sr = uniq_srgb.astype(np.float32) / 255.0
    lab = linear_rgb_to_oklab(srgb_to_linear(sr))
    n = lab.shape[0]
    cnt = counts.astype(np.float32)
    max_points = 8000
    if n > max_points:
        p = cnt / cnt.sum()
        idx = np.random.choice(n, size=max_points, replace=False, p=p)
        lab = lab[idx]; sr = sr[idx]; cnt = cnt[idx]
    sizes = 5.0 + 45.0 * (cnt / cnt.max())
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(figsize[0]/100, figsize[1]/100), dpi=100)
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(lab[:,0], lab[:,1], lab[:,2], s=sizes, c=sr, depthshade=False)
    ax.set_xlabel('L'); ax.set_ylabel('a'); ax.set_zlabel('b')
    ax.set_title('OKLab scatter of unique pixel colors')
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)

# ----------------------------
# GUI
# ----------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pixel Palette (OKLab mean-shift)")
        self.geometry("1220x780")
        self.minsize(1000, 660)

        self.input_path = None
        self.input_image = None
        self.results = None

        # Left: controls
        ctrl = ttk.Frame(self)
        ctrl.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        ttk.Label(ctrl, text="Controls", font=("TkDefaultFont", 12, "bold")).pack(anchor="w", pady=(0,6))
        ttk.Button(ctrl, text="Open Image...", command=self.on_open).pack(fill=tk.X, pady=4)

        # Sensitivity
        self.sens_var = tk.DoubleVar(value=0.6)
        ttk.Label(ctrl, text="Sensitivity (0..1)").pack(anchor="w", pady=(10,0))
        ttk.Scale(ctrl, from_=0.0, to=1.0, orient=tk.HORIZONTAL, variable=self.sens_var).pack(fill=tk.X, pady=2)

        # Exact-K
        self.k_var = tk.IntVar(value=0)
        krow = ttk.Frame(ctrl); krow.pack(fill=tk.X, pady=(6,0))
        ttk.Label(krow, text="Exact K (0=off)").pack(side=tk.LEFT)
        ttk.Spinbox(krow, from_=0, to=64, textvariable=self.k_var, width=6).pack(side=tk.RIGHT)

        # Toggles
        self.medoid_var = tk.BooleanVar(value=False)
        self.hue_var = tk.BooleanVar(value=False)
        self.perf_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text="Medoid centers (use real colors)", variable=self.medoid_var).pack(anchor="w", pady=(8,0))
        ttk.Checkbutton(ctrl, text="Hue protection (keep tiny accents)", variable=self.hue_var).pack(anchor="w")
        # Hue ranges
        rngrow = ttk.Frame(ctrl); rngrow.pack(fill=tk.X)
        ttk.Label(rngrow, text="Protect ranges (deg):").pack(side=tk.LEFT)
        self.ranges_entry = ttk.Entry(rngrow)
        self.ranges_entry.insert(0, "350-20,30-60")
        self.ranges_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        ttk.Checkbutton(ctrl, text="Performance mode", variable=self.perf_var).pack(anchor="w", pady=(6,0))

        # 3D scatter
        self.gen3d_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctrl, text="Generate 3D OKLab scatter (if matplotlib installed)", variable=self.gen3d_var).pack(anchor="w", pady=(6,0))

        ttk.Button(ctrl, text="Run", command=self.on_run).pack(fill=tk.X, pady=(10,4))

        # Progress
        ttk.Label(ctrl, text="Progress").pack(anchor="w", pady=(10,2))
        self.prog_var = tk.DoubleVar(value=0.0)
        ttk.Progressbar(ctrl, orient=tk.HORIZONTAL, mode='determinate', variable=self.prog_var, maximum=100.0).pack(fill=tk.X, pady=2)
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(ctrl, textvariable=self.status_var, foreground="#555").pack(anchor="w")

        ttk.Separator(ctrl).pack(fill=tk.X, pady=12)

        # Save outputs
        ttk.Button(ctrl, text="Save Outputs...", command=self.on_save).pack(fill=tk.X, pady=4)
        self.prefix_entry = ttk.Entry(ctrl); self.prefix_entry.insert(0, "result")
        ttk.Label(ctrl, text="Output prefix").pack(anchor="w", pady=(8,2))
        self.prefix_entry.pack(fill=tk.X)

        # Right: previews
        right = ttk.Frame(self)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        top = ttk.Frame(right); top.pack(fill=tk.BOTH, expand=True)
        self.input_canvas = tk.Label(top, bg="#222"); self.input_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,6))
        self.palette_canvas = tk.Label(top, bg="#333"); self.palette_canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        bottom = ttk.Frame(right); bottom.pack(fill=tk.BOTH, expand=True, pady=(6,0))
        self.cluster_canvas = tk.Label(bottom, bg="#222"); self.cluster_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,6))
        self.quant_canvas   = tk.Label(bottom, bg="#222"); self.quant_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.oklab3d_canvas = tk.Label(bottom, bg="#222"); self.oklab3d_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,0))

        # Summary
        self.summary_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.summary_var, justify=tk.LEFT, foreground="#444").pack(anchor="w", pady=(6,0))

        self._tk_images = {}

    # --- UI helpers ---
    def _set_progress(self, frac):
        self.prog_var.set(frac * 100.0)

    def _set_status(self, text):
        self.status_var.set(text)
        self.update_idletasks()

    def _pil_to_tk(self, img: Image.Image, max_w, max_h):
        if img is None: return None
        w, h = img.size
        scale = min(max_w / max(1, w), max_h / max(1, h))
        scale = max(1e-6, min(1.0, scale))
        nw, nh = max(1, int(w*scale)), max(1, int(h*scale))
        im = img if (nw==w and nh==h) else img.resize((nw, nh), Image.NEAREST)
        return ImageTk.PhotoImage(im)

    def _display(self, widget, pil_img, key, max_w=4096, max_h=4096):
        tkimg = self._pil_to_tk(pil_img, max_w, max_h)
        if tkimg:
            widget.configure(image=tkimg)
            self._tk_images[key] = tkimg

    # --- Buttons ---
    def on_open(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All files","*.*")])
        if not path: return
        try:
            img = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open image:\n{e}")
            return
        self.input_path = path
        self.input_image = img
        self._display(self.input_canvas, img.convert("RGB"), "input", max_w=560, max_h=360)
        self.summary_var.set(f"Loaded: {os.path.basename(path)}  [{img.width}×{img.height}]")
        self.status_var.set("Ready")

    def on_run(self):
        if self.input_image is None:
            messagebox.showinfo("Select Image", "Open an image first.")
            return
        sens = float(self.sens_var.get())
        exact_k = int(self.k_var.get())
        use_medoid = bool(self.medoid_var.get())
        hue_protect = bool(self.hue_var.get())
        perf = bool(self.perf_var.get())
        protect_ranges = _parse_hue_ranges(self.ranges_entry.get()) if hue_protect else None

        self._set_progress(0.0)
        self._set_status("Running...")
        self.results = None

        def work():
            try:
                cb = _progress_cb_factory(lambda frac: self.after(0, self._set_progress, frac))
                clusters, avg_srgb, labels_u, inverse, alpha_mask, shape_hw, label_to_kept, uniq, counts, debug = \
                    palette_oklab_meanshift(
                        self.input_image, sens,
                        progress_cb=cb, perf=perf,
                        hue_protect=hue_protect, protect_ranges=protect_ranges
                    )

                # Post steps
                if exact_k and exact_k > 0:
                    clusters = merge_to_k_clusters(clusters, exact_k, hue_protect=hue_protect)
                if use_medoid:
                    clusters = apply_medoid_centers(clusters, labels_u, label_to_kept, uniq)

                palette_img = render_palette_strip(clusters, height=60, width=420)
                cluster_img = render_cluster_viz(labels_u, inverse, alpha_mask, shape_hw, clusters, label_to_kept, uniq)
                quant_img   = render_quantized(labels_u, inverse, alpha_mask, shape_hw, clusters, label_to_kept, uniq)
                oklab3d_img = render_oklab3d(uniq, counts) if self.gen3d_var.get() else None

                self.results = {
                    "clusters": clusters,
                    "avg_srgb": avg_srgb,
                    "debug": debug,
                    "palette_img": palette_img,
                    "cluster_img": cluster_img,
                    "quant_img": quant_img,
                    "oklab3d_img": oklab3d_img
                }

                def ui_update():
                    self._display(self.palette_canvas, palette_img, "palette", max_w=420, max_h=120)
                    self._display(self.cluster_canvas, cluster_img, "cluster", max_w=560, max_h=360)
                    self._display(self.quant_canvas,   quant_img,   "quant",   max_w=560, max_h=360)
                    if oklab3d_img:
                        self._display(self.oklab3d_canvas, oklab3d_img, "ok3d", max_w=360, max_h=360)
                    else:
                        self.oklab3d_canvas.configure(image="")
                    k = len(clusters)
                    avg = [round(v, 3) for v in avg_srgb]
                    self.summary_var.set(
                        f"Clusters: {k} | Avg sRGB: {avg} | Unique: {debug['num_unique_colors']} | "
                        f"bw={debug['bandwidth']:.4f} merge={debug['merge_radius']:.4f} "
                        f"{'PERF ' if debug.get('perf') else ''}"
                        f"{' MEDOID' if use_medoid else ''}{' K='+str(exact_k) if exact_k else ''}"
                    )
                    self._set_status("Done")
                    self._set_progress(1.0)
                self.after(0, ui_update)

            except Exception as e:
                def ui_err():
                    self._set_status("Error")
                    messagebox.showerror("Processing Error", str(e))
                self.after(0, ui_err)

        threading.Thread(target=work, daemon=True).start()

    def on_save(self):
        if not self.results:
            messagebox.showinfo("Nothing to save", "Run the analysis first.")
            return
        prefix = self.prefix_entry.get().strip() or "result"
        base_dir = filedialog.askdirectory(title="Choose output folder")
        if not base_dir: return

        try:
            palette_path = os.path.join(base_dir, prefix + "_palette.png")
            cluster_path = os.path.join(base_dir, prefix + "_clusters.png")
            quant_path   = os.path.join(base_dir, prefix + "_quantized.png")
            self.results["palette_img"].save(palette_path)
            self.results["cluster_img"].save(cluster_path)
            self.results["quant_img"].save(quant_path)
            oklab3d_path = None
            if self.results.get("oklab3d_img") is not None:
                oklab3d_path = os.path.join(base_dir, prefix + "_oklab3d.png")
                self.results["oklab3d_img"].save(oklab3d_path)

            json_path = os.path.join(base_dir, prefix + "_palette.json")
            out = {
                "clusters": self.results["clusters"],
                "palette_aware_average_srgb": self.results["avg_srgb"],
                "debug": self.results["debug"]
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)

            msg = f"Saved:\n- {os.path.basename(palette_path)}\n- {os.path.basename(cluster_path)}\n- {os.path.basename(quant_path)}\n- {os.path.basename(json_path)}"
            if oklab3d_path: msg += f"\n- {os.path.basename(oklab3d_path)}"
            messagebox.showinfo("Saved", msg)
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

if __name__ == "__main__":
    App().mainloop()
