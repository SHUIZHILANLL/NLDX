# 沈阳奶龙大学 —— 一个域名过场页的完整实践

> 从一个梗图到真正上线的域名：`沈阳奶龙大学.xyz`
> 打开 → 奶蛙校徽旋转 → 约 4 秒 → 自动跳进沈阳理工大学官网。

这不是教程搬运，是一次**从零到上线**的完整记录，包含所有踩过的坑和最后的解法。
零基础可以顺着读，做过前端的可以直接跳到 `docs/05-pitfalls.md`。

---

## 一、这件事由三部分组成

| 组成 | 通俗说法 | 本次实现 |
|---|---|---|
| **域名** | 门牌号 | `沈阳奶龙大学.xyz`（¥13.75/首年） |
| **页面** | 房子里面的东西 | 4 个静态文件，无后端 |
| **托管** | 房子盖在哪 | Cloudflare Workers（免费） |

**唯一花钱的是域名。** 托管、HTTPS 证书、DNS 全部免费。

---

## 二、最终效果

```
用户输入：沈阳奶龙大学.xyz
        ↓ 浏览器自动转 punycode
xn--psszg58cgv6a4t1cr1l.xyz
        ↓ DNS 查询（Cloudflare 的 miki / pablo 服务器）
104.21.57.5
        ↓ HTTPS
Cloudflare Worker 返回 index.html（7 KB）
        ↓ 加载 badge.webp（57 KB）
白色圆盘里，奶蛙徽章淡入 → 缓慢旋转
        ↓ 2.6 秒
location.replace("https://www.sylu.edu.cn/")
        ↓
沈阳理工大学官网
```

---

## 三、技术栈（就这些）

```
HTML          骨架：一张 <img>
CSS           样式：圆形布局 + 26 秒转一圈
JavaScript    逻辑：图片到了才转，转 2.6 秒后跳转
Python        图片处理：算圆心、抠圆、压缩
Cloudflare    托管 + DNS + 证书
```

没有框架、没有构建工具、没有后端、没有数据库。

---

## 四、目录

```
docs/
├── 01-dns.md          域名、punycode、NS、DNSSEC（最容易懵的部分）
├── 02-page.md         HTML / CSS / JS 三层怎么配合
├── 03-image.md        图片处理：为什么抠图会缺边，怎么用数学解决
├── 04-deploy.md       部署到 Cloudflare Workers + 绑域名
└── 05-pitfalls.md     全部踩坑清单（含症状 → 原因 → 解法）

scripts/
├── mk_badge.py        徽章图 → 几何圆遮罩 + 压缩
└── mk_qr.py           生成二维码

img/
└── preview.png        最终效果
```

---

## 五、复刻步骤（换个学校做一份）

### 1. 买域名

```
推荐：.com（约 ¥43/首年，风控最低）或 .cn（¥29，中文域名可手打）
注册商：Spaceship（支持支付宝）/ 阿里云（中文域名）
```

**中文域名注意**：只有国内注册商（阿里云、腾讯云）能注册完整的中文 IDN。
国外注册商对中文后缀支持很差。

### 2. 准备素材

```
① 校徽高清图 —— 从学校官网 logo.png 提取，或 urongda.com 找 1024px 版本
② 一张奶蛙/人物图 —— 白底最佳
```

### 3. 处理图片

```bash
pip install Pillow numpy qrcode
python scripts/mk_badge.py
```

输出 `badge.webp`，约 57 KB。

### 4. 生成页面

```bash
python tools/build.py --html-only
```

### 5. 部署

```
Cloudflare → Workers & Pages → Create → Upload static files
拖 4 个文件 → Deploy
```

### 6. 绑域名

```
Dynadot/Spaceship 改 NS → Cloudflare 的 miki / pablo
等 Active → Workers → 自定义域 → 填 punycode
```

### 7. 出二维码

```bash
python scripts/mk_qr.py
```

---

## 六、这份笔记最值钱的五个结论

### ① 中文域名必须用 punycode 配置

```
沈阳奶龙大学.xyz  →  xn--psszg58cgv6a4t1cr1l.xyz
```

所有服务器配置（Cloudflare 加站点、绑域名、DNS）都填**英文字母那串**。
浏览器负责自动转码，你不用管。

### ② 换 NS 之前必须确认 DNSSEC 是关的

DNSSEC 的 DS 记录挂在**注册局**，不在你的 DNS 提供商。
换 NS 后旧 DS 还在 → 全站 `SERVFAIL` → 域名彻底打不开。

**症状**：网站完全无法访问，但域名状态显示正常。
**解法**：去注册商后台删掉 DS 记录，等 20 分钟。

### ③ 白色圆盘和白色背景连成一片，颜色抠图会失败

圆盘是白的，背景也是白的，用"删掉白色"的办法会把圆盘边缘一起删掉 —— 表现为**缺边**。

**正确做法**：用几何圆遮罩。先拟合圆心和半径，再按圆裁。

```python
# 拟合残差 < 4px 才算准
(cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
R = np.sqrt(c + cx*cx + cy*cy)
```

### ④ 图没到就别转

```
错误：animation 一上来就跑 → 用户看到空白在转
正确：img.onload 之后才加 .ready 类 → 才显示、才转、才开始倒计时
兜底：6 秒图还没到 → 直接跳转，别让人干等
```

### ⑤ 国内访问 Cloudflare 免费节点速度不稳定

实测（2026-10）：

```
IPv6 → 完全超时（30s，0 字节）
IPv4 → 200，但 86 KB 要 5.5 秒（约 15 KB/s）
```

所以图片必须压到极致（57 KB），并且要有兜底逻辑。
浏览器有 Happy Eyeballs 机制会自动从 IPv6 回退到 IPv4，但速度仍然受限。

---

## 七、完整踩坑表

| # | 现象 | 原因 | 解法 |
|---|---|---|---|
| 1 | Cloudflare 加站点报 `not a valid domain` | 填了中文 | 改填 punycode |
| 2 | 加完域名自动出现两条 AWS IP 的 A 记录 | Spaceship 的停放页 | 全部删除 |
| 3 | 换 NS 后网站彻底打不开（SERVFAIL） | DNSSEC 的 DS 记录还挂在注册局 | 去注册商删 DS，等 20 分钟 |
| 4 | 圆盘缺边 | 白色圆盘和白色背景连通，颜色抠图吃掉边缘 | 改用几何圆遮罩 |
| 5 | 旋转时看到白色方块 | 图片外部没透明 | 圆形 alpha 遮罩 |
| 6 | 图片 227 KB，手机上加载极慢 | 分辨率过高 | 压到 700px / q76 → 57 KB |
| 7 | 图没加载完页面就在转 | CSS animation 立刻启动 | `img.onload` 后再加 `.ready` |
| 8 | 改了 NS 但 Cloudflare 一直显示「待更新」 | 旧的 NS 没删干净，形成混合委托 | 注册商后台只保留 CF 两条 |
| 9 | 改了代码但线上还是旧版 | Cloudflare 缓存 | 缓存 → 清除缓存 |
| 10 | 部署到子目录导致资源 404 | 页面里用的是绝对路径 `/badge.webp` | 必须部署在站点根目录 |

---

## 八、成本清单

| 项 | 费用 |
|---|---|
| 域名 `沈阳奶龙大学.xyz` | ¥13.75 / 首年（续费约 ¥100） |
| Cloudflare DNS | ¥0 |
| Cloudflare Workers 静态托管 | ¥0（10 万请求/天免费额度） |
| HTTPS 证书 | ¥0（自动签发） |
| **合计** | **¥13.75** |

---

## 九、免责

纯属娱乐的粉丝向作品，与任何学校**无官方关联**。校徽取自学校公开标识。
仅供学习 DNS、静态部署、图片处理等技术使用。
