# 03 · 图片处理：为什么抠图会缺边

> 这一章是整个项目里技术含量最高的部分。核心一句话：
> **白色圆盘放在白色背景上，颜色抠图会把圆盘边缘一起吃掉的——必须用几何方法。**

---

## 1. 问题起点

你手上有一张图：**1600 × 1568 的 PNG，中间一个圆形徽章，四周白色背景。**

目标：

```
一个能旋转的圆形徽章，圆外完全透明
```

看起来很简单——删掉白色不就行了？

---

## 2. 第一次尝试：颜色抠图（失败）

### 思路

```
白色像素 → 透明
非白色像素 → 保留
```

### 实现

```python
from PIL import Image
import numpy as np

im = Image.open("badge.png").convert("RGBA")
a = np.array(im)
lum = a[..., :3].mean(axis=2)      # 亮度
alpha = np.where(lum > 240, 0, 255)  # 亮的变透明
a[..., 3] = alpha
```

### 结果：**圆盘缺边**

因为：

```
圆盘外缘是白色（#ffffff）
外部背景也是白色（#ffffff）
```

两者**颜色完全一样**，无法用颜色区分。

`lum > 240` 这个条件会把圆盘外圈的白色也判定为"背景"，一起删掉。

现象就是：**圆盘边缘出现一块块缺口，圆的轮廓被啃掉一圈。**

---

## 3. 第二次尝试：洪水填充（也失败）

### 思路

从这个图的最外圈开始，沿着「白色且连通」的区域往里扩散，只把**和外部连通**的白色删掉。

理论依据：圆盘内部的白色（如果有）不连通外部，会被保留。

### 实现在哪失败

`PIL.ImageDraw.floodfill` 从四边填充：

```python
for seed in seeds:
    if is_white(seed):
        ImageDraw.floodfill(marked, seed, SENTINEL, thresh=26)
```

**但圆盘外缘的白色和外部白色是连通的！** 洪水会一路灌进圆盘内部，直到撞上绿色圆环为止。

结果：

```
圆盘外圈白色 → 被灌掉了
绿色圆环 → 挡住了洪水，保留
圆盘内侧白色 → 保留
```

现象仍然是**缺边**，而且这次缺的更多，能看到一圈半透明白边。

---

## 4. 正确解法：几何圆遮罩

### 核心思路

**不判断颜色，用数学找圆心和半径，然后按圆裁。**

```
1. 找出所有"有墨"的像素（非白）
2. 取每个角度上最外的那个点 → 得到 360~720 个边界点
3. 用最小二乘法拟合出一个圆
4. 用这个圆做遮罩
```

### 4.1 提取边界点

```python
a = np.asarray(im).astype(np.float32)
lum = a[..., :3].mean(axis=2)
ink = (lum < 235).astype(np.uint8)       # 有墨的像素

ys, xs = np.nonzero(ink > 0)
cx0, cy0 = xs.mean(), ys.mean()          # 粗略中心

r = np.hypot(xs - cx0, ys - cy0)         # 到中心的距离
th = np.arctan2(ys - cy0, xs - cx0)      # 角度（-π 到 π）

# 按角度分 720 个箱，每箱取半径最大的点
nb = 720
idx = ((th + np.pi) / (2 * np.pi) * nb).astype(np.int32) % nb
order = np.lexsort((-r, idx))            # 按角度排序，同角度内半径降序
_, first = np.unique(idx[order], return_index=True)
P = np.c_[xs[order[first]], ys[order[first]]].astype(np.float64)
```

**为什么按角度分箱？**

因为圆环上的文字、装饰会导致同一角度有多个墨点，我们只要**最外缘**那个。

### 4.2 Kasa 最小二乘圆拟合

圆的方程：

```
(x - a)² + (y - b)² = R²
```

展开：

```
x² + y² = 2ax + 2by + (R² - a² - b²)
```

令 `c = R² - a² - b²`，变成线性方程：

```
x² + y² = 2ax + 2by + c
```

**这是对 `(a, b, c)` 的线性方程**，可以用最小二乘直接解：

```python
A = np.c_[2*P[:, 0], 2*P[:, 1], np.ones(len(P))]
b = (P ** 2).sum(axis=1)
(a, bb, c), *_ = np.linalg.lstsq(A, b, rcond=None)

cx, cy = a, bb
R = np.sqrt(c + cx*cx + cy*cy)
```

### 4.3 鲁棒迭代（剔除离群点）

第一遍拟合可能被文字、装饰带偏。迭代几次，每次踢掉偏差大的点：

```python
for _ in range(6):
    d = np.abs(np.hypot(P[:, 0] - cx, P[:, 1] - cy) - R)
    keep = d < max(1.5, 2.5 * d.mean())     # 保留近圆的点
    if keep.sum() < 60:
        break
    Pk = P[keep]
    A = np.c_[2*Pk[:, 0], 2*Pk[:, 1], np.ones(len(Pk))]
    b = (Pk ** 2).sum(axis=1)
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    R = np.sqrt(c + cx*cx + cy*cy)
    P = Pk
```

### 4.4 残差 = 拟合质量的判据

```python
resid = np.abs(np.hypot(P[:, 0] - cx, P[:, 1] - cy) - R).mean()
```

| 残差 | 说明 |
|---|---|
| < 1 px | 完美，标准圆形 |
| 1–3 px | 可接受，有轻微文字干扰 |
| **> 3 px** | **警告：不是正圆，或者墨迹不在于圆环上** |

我们这次的结果：

```
center=(800.7, 785.6)  R=790.8  残差=3.98px
```

残差接近 4，是因为圆环上有毛笔字（粗细不均）。但圆心和半径是准的：
- 图是 1600×1568，中心应该是 (800, 784)
- 拟合出 (800.7, 785.6) —— **误差不到 2 像素**

### 4.5 画布不够大，要外扩

```
R = 790.8 → 直径 1581.6
原图高度只有 1568
```

**圆盘上下被切掉了！** 所以不能直接裁，要先外扩画布：

```python
side = int(np.ceil(2 * R + 8))          # 1590
x0 = int(round(cx - side / 2))
y0 = int(round(cy - side / 2))

canvas = Image.new("RGBA", (side, side), (255, 255, 255, 255))
canvas.paste(im, (-x0, -y0), im)        # 负数偏移 = 向右下推
```

### 4.6 生成圆形 alpha

```python
yy, xx = np.mgrid[0:side, 0:side]
rr = np.hypot(xx - (cx - x0), yy - (cy - y0))

# 圆内 = 1，圆外 = 0，边缘 1.2px 渐变（抗锯齿）
alpha = np.clip((R - rr) / 1.2, 0, 1)

# 再高斯模糊 0.8px，让边缘更柔
alpha = np.asarray(
    Image.fromarray((alpha * 255).astype(np.uint8))
         .filter(ImageFilter.GaussianBlur(0.8))
).astype(np.float32) / 255.0

out = np.array(canvas, dtype=np.float32)
out[..., 3] *= alpha
```

### 为什么不要反预乘

反预乘是去掉"半透明边缘的白色残留"：

```python
rgb = (rgb - 255*(1-a)) / a
```

**但对这张图有害**，因为圆盘外缘本来就是白色。反预乘会把边缘的白色除掉，导致：

```
a 很小时，rgb / a 爆炸 → 边缘出现一圈白晕
```

我们的实际现象：第一次做出来后，徽章外围有一圈比背景更亮的柔和光环。

**解法：干脆不做反预乘。**

```python
# 直接乘 alpha，改 rgb
out[..., 3] *= alpha

# alpha 很小的直接归零，避免边缘杂色
alpha = np.where(alpha < 0.20, 0.0, alpha)
```

---

## 5. 压缩：227 KB → 57 KB

### 为什么大

```
1000 × 1000 px，quality 96 → 227 KB
```

对手机首屏来说太重了。

### 三步压缩

| 步骤 | 参数 | 效果 |
|---|---|---|
| 降分辨率 | 1000 → 700 px | 显示尺寸最多 400px，2x 屏 800px，700 够用 |
| 降质量 | 96 → 76 | 视觉几乎无差 |
| WebP | 本身就是 WebP | 比 JPEG 小 25–35% |

### 试算表

| 尺寸 | 质量 | 大小 |
|---|---|---|
| 820 | 82 | 86 KB |
| **700** | **76** | **57.5 KB** ✅ |
| 700 | 70 | 54 KB |
| 640 | 70 | 47 KB |
| 560 | 70 | 40 KB |

**最终选 700 / 76**：57.5 KB，在 400px 显示尺寸下仍然锐利。

### 什么时候该更狠

如果网络实测只有 15 KB/s（我们就是这样），57 KB 要 3.8 秒。

那时候可以考虑：
- 560px / 70 → 40 KB（2.7 秒）
- 但 3x 屏（iPhone Pro）下会软

**权衡**：清晰度 vs 首屏速度。过场页只显示 4 秒，轻微模糊无所谓，所以可以更狠。

---

## 6. 完整代码

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = 700          # 输出边长
QUALITY = 76       # WebP 质量


def fit_circle(ink):
    """从墨迹掩膜拟合圆心和半径"""
    ys, xs = np.nonzero(ink > 0)
    cx0, cy0 = xs.mean(), ys.mean()

    r = np.hypot(xs - cx0, ys - cy0)
    th = np.arctan2(ys - cy0, xs - cx0)

    nb = 720
    idx = ((th + np.pi) / (2 * np.pi) * nb).astype(np.int32) % nb
    order = np.lexsort((-r, idx))
    _, first = np.unique(idx[order], return_index=True)
    P = np.c_[xs[order[first]], ys[order[first]]].astype(np.float64)

    A = np.c_[2*P[:, 0], 2*P[:, 1], np.ones(len(P))]
    b = (P ** 2).sum(axis=1)
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    R = float(np.sqrt(c + cx*cx + cy*cy))

    # 鲁棒迭代
    for _ in range(6):
        d = np.abs(np.hypot(P[:, 0]-cx, P[:, 1]-cy) - R)
        keep = d < max(1.5, 2.5 * float(d.mean()))
        if keep.sum() < 60:
            break
        Pk = P[keep]
        A = np.c_[2*Pk[:, 0], 2*Pk[:, 1], np.ones(len(Pk))]
        b = (Pk ** 2).sum(axis=1)
        (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
        R = float(np.sqrt(c + cx*cx + cy*cy))
        P = Pk

    resid = float(np.abs(np.hypot(P[:, 0]-cx, P[:, 1]-cy) - R).mean())
    return cx, cy, R, resid


def main(src, dst):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    a = np.asarray(im).astype(np.float32)
    ink = (a[..., :3].mean(axis=2) < 235).astype(np.uint8)

    cx, cy, R, resid = fit_circle(ink)
    print(f"[fit] center=({cx:.1f},{cy:.1f})  R={R:.1f}  残差={resid:.2f}px")

    # 外扩画布，保证圆完整
    side = int(np.ceil(2*R + 8))
    x0 = int(round(cx - side/2))
    y0 = int(round(cy - side/2))
    canvas = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    canvas.paste(im, (-x0, -y0), im)

    # 几何圆遮罩
    yy, xx = np.mgrid[0:side, 0:side]
    rr = np.hypot(xx - (cx-x0), yy - (cy-y0))
    alpha = np.clip((R - rr) / 1.2, 0, 1)
    alpha = np.asarray(
        Image.fromarray((alpha*255).astype(np.uint8))
             .filter(ImageFilter.GaussianBlur(0.8))
    ).astype(np.float32) / 255.0

    out = np.array(canvas, dtype=np.float32)
    alpha = np.where(alpha < 0.20, 0.0, alpha)
    out[..., 3] *= alpha

    res = Image.fromarray(out.astype(np.uint8), "RGBA")
    res = res.resize((OUT, OUT), Image.LANCZOS)
    res.save(dst, "WEBP", quality=QUALITY, method=6)
    print(f"[out] {dst}  {res.size}  {os.path.getsize(dst)/1024:.1f} KB")


if __name__ == "__main__":
    main("assets-src/final-badge.png", "site/badge.webp")
```

---

## 7. 检查清单

生成后**必须亲眼看一遍**：

```
□ 圆的边缘完整，没有缺口
□ 圆外完全透明（叠在白底上看不出方块）
□ 圆外没有白晕/光晕
□ 文字环清晰可读
□ 旋转测试：把图转 90° 看边缘是否依然规整
□ 文件大小 < 100 KB
```

---

## 8. 一句话总结

> **颜色相同的两个东西，不要用颜色去分。**
> **白色圆盘 + 白色背景 = 必须用几何形状去裁，而不是用像素颜色去判断。**
