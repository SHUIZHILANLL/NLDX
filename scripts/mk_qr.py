#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成扫码即开的二维码（punycode 最兼容，扫完浏览器会显示中文域名）"""
import os

import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://xn--psszg58cgv6a4t1cr1l.xyz/"
LABEL = "沈阳奶龙大学.xyz"

qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=16, border=3)
qr.add_data(URL)
qr.make(fit=True)
img = qr.make_image(fill_color=(28, 26, 22), back_color=(255, 255, 255)).convert("RGB")

# 底部加一行说明
W, H = img.size
pad = 130
canvas = Image.new("RGB", (W, H + pad), (255, 255, 255))
canvas.paste(img, (0, 0))

FONTS = [r"C:\Windows\Fonts\msyhbd.ttc", r"C:\Windows\Fonts\msyh.ttc",
         r"C:\Windows\Fonts\simhei.ttf"]
font = None
for p in FONTS:
    if os.path.exists(p):
        font = ImageFont.truetype(p, 54)
        break
if font is None:
    font = ImageFont.load_default()

d = ImageDraw.Draw(canvas)
tw = d.textlength(LABEL, font=font)
d.text(((W - tw) / 2, H + 18), LABEL, font=font, fill=(30, 28, 24))

sub = "扫码 → 4 秒 → 沈阳理工大学官网"
f2 = ImageFont.truetype(FONTS[0], 30) if os.path.exists(FONTS[0]) else font
sw = d.textlength(sub, font=f2)
d.text(((W - sw) / 2, H + 82), sub, font=f2, fill=(150, 142, 125))

out = os.path.join(ROOT, "qr.png")
canvas.save(out, "PNG", optimize=True)
print(f"[out] {out}  {canvas.size}  ->  {URL}")
