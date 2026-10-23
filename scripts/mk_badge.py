#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把合成好的完整徽章图 → site/badge.webp
用几何圆遮罩（而不是抠白底）：圆盘是白色的，和外部白底连通，
洪水填充会把圆盘外圈一起吃掉，导致缺边。这里直接按拟合出的
圆心/半径做圆形 alpha，圆盘边缘完整保留。
"""
import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = 700


def fit_outer(ink):
    ys, xs = np.nonzero(ink > 0)
    cx0, cy0 = xs.mean(), ys.mean()
    r = np.hypot(xs - cx0, ys - cy0)
    th = np.arctan2(ys - cy0, xs - cx0)
    nb = 720
    idx = ((th + np.pi) / (2 * np.pi) * nb).astype(np.int32) % nb
    order = np.lexsort((-r, idx))
    _, first = np.unique(idx[order], return_index=True)
    P = np.c_[xs[order[first]], ys[order[first]]].astype(np.float64)

    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    b = (P ** 2).sum(1)
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    R = float(np.sqrt(c + cx * cx + cy * cy))
    for _ in range(6):
        d = np.abs(np.hypot(P[:, 0] - cx, P[:, 1] - cy) - R)
        keep = d < max(1.5, 2.5 * float(d.mean()))
        if keep.sum() < 60:
            break
        Pk = P[keep]
        A = np.c_[2 * Pk[:, 0], 2 * Pk[:, 1], np.ones(len(Pk))]
        b = (Pk ** 2).sum(1)
        (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
        R = float(np.sqrt(c + cx * cx + cy * cy))
        P = Pk
    return cx, cy, R, float(np.abs(np.hypot(P[:, 0] - cx, P[:, 1] - cy) - R).mean())


def main():
    src = os.path.join(ROOT, "assets-src", "final-badge.png")
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    a = np.asarray(im).astype(np.float32)
    ink = (a[..., :3].mean(2) < 235).astype(np.uint8)
    cx, cy, R, resid = fit_outer(ink)
    print(f"[fit] center=({cx:.1f},{cy:.1f})  R={R:.1f}  残差={resid:.2f}px")

    # 画布必须能完整容纳这个圆：不够就外扩（用圆内最近的像素填充，避免出现缺口）
    side = int(np.ceil(2 * R + 8))
    x0 = int(round(cx - side / 2))
    y0 = int(round(cy - side / 2))
    canvas = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    canvas.paste(im, (-x0, -y0), im)
    print(f"[canvas] {side}x{side}  (原图 {w}x{h}，外扩以容纳整圆)")

    # 几何圆遮罩，抗锯齿羽化 1.2px
    yy, xx = np.mgrid[0:side, 0:side]
    rr = np.hypot(xx - (cx - x0), yy - (cy - y0))
    alpha = np.clip((R - rr) / 1.2, 0, 1)
    alpha = np.asarray(
        Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    ).astype(np.float32) / 255.0

    out = np.array(canvas, dtype=np.float32)
    # 圆盘外缘本身就是白色，不做反预乘（否则边缘会炸出一圈白晕）
    alpha = np.where(alpha < 0.20, 0.0, alpha)
    out[..., 3] *= alpha

    res = Image.fromarray(out.astype(np.uint8), "RGBA").resize((OUT, OUT), Image.LANCZOS)
    res.save(os.path.join(ROOT, "site", "badge.webp"), "WEBP", quality=76, method=6)
    res.save(os.path.join(ROOT, "_badge_check.png"))
    print(f"[out] badge.webp {res.size}  R/边长 = {R/side*2:.3f}")


if __name__ == "__main__":
    main()


