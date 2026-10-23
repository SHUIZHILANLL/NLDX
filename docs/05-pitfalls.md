# 05 · 踩坑记录

> 每一个坑都是实际踩的。按**踩到的顺序**排列，包含症状、原因、排查方法、解法。

---

## 坑 1 · Cloudflare 加站点报 `not a valid domain`

### 症状

```
输入：沈阳奶龙大学.xyz
报错：not a valid domain / 不是有效的域名
```

### 原因

Cloudflare 的后台只接受 ASCII 域名。中文域名必须先转成 punycode。

### 排查

```python
python3 -c "print('沈阳奶龙大学.xyz'.encode('idna').decode())"
# xn--psszg58cgv6a4t1cr1l.xyz
```

### 解法

所有后台配置一律填 punycode。浏览器负责转码，你不用管。

### 记住

```
给人看的地方 → 中文
给机器填的地方 → punycode
```

---

## 坑 2 · Spaceship 的「停车页」A 记录

### 症状

加域名到 Cloudflare 时，自动扫描出两条记录：

```
A  @  54.149.79.189    已代理
A  @  34.216.117.25    已代理
```

### 原因

这两个 IP 是 **AWS 俄勒冈**的地址，是 Spaceship 给未配置域名自动挂的**默认停放页**（parking page）。

如果不删，访问你的域名会看到 Spaceship 的「此域名已注册」页面。

### 解法

**全部删除。** 之后绑 Worker 自定义域时，Cloudflare 会自动加正确的记录。

### 怎么识别这类「垃圾记录」

| 特征 | 判断 |
|---|---|
| 注册商刚给的域名，还没配任何东西 | 大概率是停放页 |
| IP 属于 AWS / 注册商自有网段 | 停放页 |
| 内容是一个「此域名待售」的页面 | 确定是停放页 |

---

## 坑 3 · 换 NS 后网站彻底打不开（SERVFAIL）⭐️ 最严重

### 症状

```
改完 NS，等了一小时
浏览器打开：无法访问此网站
nslookup 查询：DNS server failure
```

**域名看起来一切正常，但就是解析不了。**

### 原因

**DNSSEC 的 DS 记录还挂在注册局，指向旧 NS 的密钥。**

```
新 NS = miki.ns.cloudflare.com
旧 DS = 指向 Spaceship 的密钥
→ 递归 DNS 验证签名失败 → 返回 SERVFAIL
```

### 排查命令

```bash
DOMAIN=xn--psszg58cgv6a4t1cr1l.xyz

# 查 DS（有输出 = DNSSEC 开着）
dig DS $DOMAIN +short @8.8.8.8
# 708 13 2 40F27104...

# 查 A（看是否 SERVFAIL）
dig A $DOMAIN +short @8.8.8.8
# 正常：IP 或空
# 出错：;; ->>HEADER<<- status: SERVFAIL
```

PowerShell：

```powershell
Resolve-DnsName -Name xn--psszg58cgv6a4t1cr1l.xyz -Type DS -Server 8.8.8.8
Resolve-DnsName -Name xn--psszg58cgv6a4t1cr1l.xyz -Type A  -Server 8.8.8.8
# 报错信息：DNS server failure
```

### 解法

```
1. 登录注册商（Spaceship）
2. 找 DNSSEC / DNS 安全 设置
3. 删除所有 DS 记录 / 关闭 DNSSEC
4. 等 20 分钟 ~ 2 小时
```

### 实际时间线

```
19:17  改完 NS，Spaceship 显示"传播中"
19:20  DS 708/13 仍在，SERVFAIL
19:51  8.8.8.8 / 1.1.1.1 已无 DS，SERVFAIL 解除
```

**34 分钟。**

### 关键教训

> **换 NS 之前，先去注册商确认 DNSSEC 是关闭状态。**

### 一个反直觉的点

Spaceship 的 DNSSEC 页面当时显示「0 条记录」，但注册局那边还挂着。

**界面显示 ≠ 注册局实际状态。** 只有用命令查 DS 才知道真相。

---

## 坑 4 · 圆盘「缺边」⭐️ 技术含量最高

### 症状

生成的徽章图，圆的边缘出现一圈缺口，轮廓被啃掉。

### 原因

```
圆盘外缘 = 白色 (#ffffff)
图片背景 = 白色 (#ffffff)
```

用「删掉白色」的方式抠图，会把圆盘边缘也一起删掉。

洪水填充也一样：**圆盘的白色和外部背景是连通的**，洪水会一路灌进去。

### 错误做法

```python
# ❌ 颜色判断
alpha = np.where(lum > 240, 0, 255)

# ❌ 洪水填充
ImageDraw.floodfill(marked, seed, SENTINEL, thresh=26)
```

### 正确做法

```python
# ✅ 几何圆遮罩
cx, cy, R, resid = fit_circle(ink)      # 先拟合圆
rr = np.hypot(xx - cx, yy - cy)
alpha = np.clip((R - rr) / 1.2, 0, 1)   # 按半径做遮罩
```

### 判断拟合是否可信

```python
resid = np.abs(np.hypot(P[:, 0]-cx, P[:, 1]-cy) - R).mean()
```

| 残差 | 含义 |
|---|---|
| < 1 px | 完美 |
| 1–3 px | 可接受 |
| > 3 px | 警告：不是正圆，或边界点找错了 |

我们这次：`center=(800.7, 785.6) R=790.8 残差=3.98px`

图是 1600×1568，理论中心 (800, 784)，拟合 (800.7, 785.6) —— **误差 < 2px**。

### 附带问题：画布不够大

```
R = 790.8 → 直径 1581.6
原图高度 1568
```

**圆的上下被切掉了。** 必须先外扩画布：

```python
side = int(np.ceil(2 * R + 8))
canvas = Image.new("RGBA", (side, side), (255,255,255,255))
canvas.paste(im, (-x0, -y0), im)
```

---

## 坑 5 · 旋转时看到白色方块

### 症状

徽章在转，但外面有个白色正方形一起转。

### 原因

图片是方形 PNG，外部没有透明。

### 解法

圆形 alpha 遮罩（同坑 4）。圆外 alpha = 0。

### 验证方法

把图叠在深色背景上看：

```python
bg = Image.new("RGB", im.size, (40, 40, 40))
bg.paste(im, (0, 0), im)
bg.save("check.png")
```

如果看到白色方块 → 没抠干净。

---

## 坑 6 · 图片 227 KB，手机上加载极慢

### 症状

用户反馈：「有点卡，加载不出来就转了」

### 原因

```
1000 × 1000 px，quality 96 → 227 KB
```

按 15 KB/s 的链路算，要 15 秒。

### 解法

```
① 降分辨率 1000 → 700
② 降质量  96 → 76
③ 保持 WebP
→ 57.5 KB
```

### 试算表

| 尺寸 | 质量 | 大小 |
|---|---|---|
| 1000 | 96 | 227 KB |
| 820 | 82 | 86 KB |
| **700** | **76** | **57.5 KB** ✅ |
| 640 | 70 | 47 KB |
| 560 | 70 | 40 KB |

---

## 坑 7 · 图没加载完，页面就在转

### 症状

打开页面，看到一个空白在旋转，几秒后图才出现。

### 原因

```css
.mark { animation: spin 26s linear infinite; }
```

CSS animation 从元素渲染的那一刻就开始跑，不等图片。

### 错误做法

```css
/* ❌ 一上来就转 */
.mark { background: url(/badge.webp); animation: spin 26s ...; }
```

### 正确做法

```css
/* ✅ 默认不动 */
.mark { opacity: 0; transition: opacity .28s; }
/* ✅ 加 .ready 才转 */
.mark.ready { opacity: 1; animation: spin 26s linear infinite; }
```

```javascript
mark.onload = () => {
  mark.classList.add("ready");   // 图到了才加类
  arm(2600);                      // 才开始倒计时
};
setTimeout(startSpin, 6000);      // 6 秒兜底
```

### 兜底逻辑要分情况

```javascript
function startSpin() {
  if (mark.naturalWidth > 0) {
    // 图到了：正常播放
    mark.classList.add("ready");
    arm(DUR);
  } else {
    // 图没到：别让用户看空白，直接跳
    setTimeout(go, 700);
  }
}
```

**「图没到就跳」比「图没到还转」体验好得多。** 用户至少看到了结果。

---

## 坑 8 · Cloudflare 一直显示「待更新名称服务器」

### 症状

```
概览页：正在等待注册机构传播新的名称服务器
等了 3 小时还是这个状态
```

### 原因

两种可能：

**① 注册商那边根本没保存成功**

很多界面有二次确认弹窗，没点就白改。

**② 旧的 NS 没删干净（混合委托）**

```
名称服务器：
  miki.ns.cloudflare.com     ← 新
  launch1.spaceship.net      ← 旧，必须删
```

Cloudflare 检测到混合委托会认为「还没完全切过来」。

### 排查

```bash
dig NS xn--psszg58cgv6a4t1cr1l.xyz +short @8.8.8.8

# ✅ 正确
miki.ns.cloudflare.com.
pablo.ns.cloudflare.com.

# ❌ 混合
miki.ns.cloudflare.com.
launch1.spaceship.net.

# ❌ 没改
launch1.spaceship.net.
launch2.spaceship.net.
```

### 解法

注册商后台只保留 Cloudflare 给的两条，其他全删。

---

## 坑 9 · 改了代码但线上还是旧版

### 症状

本地预览是新的，线上还是旧的。

### 原因

Cloudflare CDN 缓存。

### 排查

```bash
curl -sSI https://你的域名/ | grep -i cf-cache-status
# HIT  → 命中缓存（可能是旧的）
# MISS → 回源（新的）
```

### 解法

**① 清缓存（推荐）**

```
Cloudflare → 你的域名 → 缓存 → 清除缓存 → 清除所有内容
```

**② 无痕窗口验证**

**③ 加查询参数绕过缓存**

```
https://xn--psszg58cgv6a4t1cr1l.xyz/?v=2
```

---

## 坑 10 · 部署后资源全部 404

### 症状

页面能打开，但图片不显示，样式全丢。

### 原因

两条：

**① 拖了文件夹而不是文件**

```
❌ https://xxx.workers.dev/site/index.html
✅ https://xxx.workers.dev/index.html
```

**② 页面里用了绝对路径**

```html
<img src="/badge.webp">   <!-- 必须部署在根目录 -->
```

如果部署在子目录，`/badge.webp` 会指向错误位置。

### 解法

- 拖文件，不拖文件夹
- 或者把页面里的路径改成相对路径 `./badge.webp`

### 验证

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://你的域名/badge.webp
# 期望 200
```

---

## 坑 11 · `workers.dev` 地址在国内打不开

### 症状

```
https://nailong.3510083235.workers.dev  → 连接超时
```

### 原因

`workers.dev` 在中国大陆被 DNS 污染 + IP 阻断。

### 这不是故障

部署本身是成功的，只是这个调试地址被墙。

### 解法

直接绑自定义域名。观众访问的是 `沈阳奶龙大学.xyz`，走 CDN anycast IP，国内能访问。

---

## 坑 12 · 反预乘导致边缘白晕

### 症状

徽章外围有一圈比背景更亮的柔和光环。

### 原因

去白边的标准做法是反预乘：

```python
rgb = (rgb - 255*(1-a)) / a
```

当 `a` 很小时，`rgb / a` 会爆炸，边缘产生亮色。

### 解法

对这张图**不做反预乘**，因为圆盘外缘本来就是白色：

```python
# 直接乘 alpha
out[..., 3] *= alpha

# alpha 很小的直接归零
alpha = np.where(alpha < 0.20, 0.0, alpha)
```

---

## 13. 快速排查决策树

```
网站打不开
├─ nslookup 报 SERVFAIL
│   └─ 查 DS 记录 → 有 → 坑 3（DNSSEC）
├─ nslookup 报 NXDOMAIN
│   └─ 域名没注册 / 注册局还没生效
├─ nslookup 正常但浏览器打不开
│   ├─ curl 报证书错误 → 等证书签发（30 分钟内）
│   └─ 只有 workers.dev 打不开 → 坑 11（被墙）
└─ 能打开但内容不对
    ├─ 图片 404 → 坑 10（目录层级）
    ├─ 还是旧版 → 坑 9（缓存）
    └─ 圆缺边 → 坑 4（抠图方法）
```

---

## 14. 一句话总结

> **域名问题看 DNS，DNS 问题看 DNSSEC，图片问题看几何，加载问题看大小。**
> **剩下都是缓存。**
