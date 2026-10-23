# 01 · 域名与 DNS

> 这一章是整个项目里最容易懵的部分。看懂它，你就理解了「为什么买了域名还要折腾一堆设置」。

---

## 1. 域名 = 门牌号

```
沈阳奶龙大学.xyz
└────┬────┘ └┬┘
   主体     后缀（TLD）
```

- **主体**：你自己起的名字
- **后缀**：`.com` / `.cn` / `.xyz` / `.online`…… 由不同注册局管理

买域名 = 在一段时间内（通常 1 年）独占这个名字。

---

## 2. 中文域名会被自动转码（punycode）

### 现象

你在浏览器地址栏输入：

```
沈阳奶龙大学.xyz
```

浏览器**不会**拿这串中文去查网。它会先翻译成：

```
xn--psszg58cgv6a4t1cr1l.xyz
```

这叫 **punycode**，是国际化域名（IDN）的 ASCII 编码形式。

### 后果

| 场景 | 该填什么 |
|---|---|
| 浏览器地址栏 | 中文（浏览器自动转） |
| Cloudflare 加站点 | **punycode** |
| Cloudflare 绑自定义域 | **punycode** |
| DNS 查询工具 | **punycode** |
| 证书签发 | **punycode** |

**只要不是"给人看"的地方，全都填 punycode。**

### 怎么转

```python
python3 -c "print('沈阳奶龙大学.xyz'.encode('idna').decode())"
# xn--psszg58cgv6a4t1cr1l.xyz
```

Windows PowerShell：

```powershell
[System.Globalization.IdnMapping]::new().GetAscii('沈阳奶龙大学.xyz')
```

### 为什么会有这个机制

DNS 协议诞生于 1983 年，只支持 ASCII 字符（a-z、0-9、连字符）。
后来想支持中文、日文、阿拉伯文域名，又不能改协议，于是在前面加一层编码转换。

`xn--` 是 punycode 的固定前缀，看到它就说明这是个国际化域名。

---

## 3. DNS = 电话簿

域名是给人看的，机器只认 IP 地址。DNS 负责翻译：

```
问：xn--psszg58cgv6a4t1cr1l.xyz 住哪？
答：104.21.57.5
```

### 查询过程（简化）

```
你的电脑
  ↓ 问本地递归 DNS（比如 8.8.8.8）
递归 DNS
  ↓ 问 .xyz 注册局：这个域名谁管？
注册局
  ↓ 答：miki.ns.cloudflare.com
递归 DNS
  ↓ 问 miki：这个域名解析到哪？
miki
  ↓ 答：104.21.57.5
递归 DNS
  ↓ 缓存结果，返回给你
你的电脑拿到 IP，开始连网站
```

---

## 4. NS = 谁管这本电话簿

**NS（Name Server，名称服务器）** 记录的是「这个域名的 DNS 由谁负责回答」。

我们的情况：

```
改之前：Spaceship 管
  launch1.spaceship.net
  launch2.spaceship.net

改之后：Cloudflare 管
  miki.ns.cloudflare.com
  pablo.ns.cloudflare.com
```

### 为什么要改

1. **Spaceship 的 DNS 功能弱**，没有 Workers/Pages 集成
2. **Cloudflare 要在自己的 DNS 上才能代理流量**（隐藏源站、缓存、证书）
3. **绑 Pages / Workers 自定义域必须用 CF 的 DNS**

### 怎么改（Spaceship 为例）

```
Spaceship → Domain Manager → 点域名
→ 「名称服务器」区块 → 点「更改」
→ 选「自定义名称服务器」
→ 填 miki.ns.cloudflare.com 和 pablo.ns.cloudflare.com
→ 保存
```

⚠️ **旧的 NS 必须删干净**。留着会形成「混合委托」，Cloudflare 永远检测不到活跃状态。

### 生效时间

```
5 分钟 ~ 24 小时
```

因为全球有几十万台递归 DNS 服务器，它们各自缓存。改了委托后要逐个过期。

---

## 5. DNSSEC —— 这个坑能让网站彻底打不开

### 它是什么

DNSSEC 是在 DNS 上再加一层**数字签名校验**，防止 DNS 被劫持。

### 关键概念：DS 记录在注册局，不在你的 DNS 提供商

```
你的域名
  ├── NS 记录（谁管 DNS）      → 在注册局
  └── DS 记录（DNSSEC 公钥指纹）→ 也在注册局
```

**DS 记录只有注册商能改，你的 DNS 提供商改不了。**

### 为什么换 NS 会炸

```
改 NS 前：
  NS = launch1.spaceship.net
  DS = 指向 Spaceship 的密钥  ✅ 匹配

改 NS 后：
  NS = miki.ns.cloudflare.com
  DS = 还指向 Spaceship 的密钥  ❌ 不匹配
```

递归 DNS 验证时发现密钥对不上，直接返回：

```
SERVFAIL（服务器故障）
```

**结果就是：域名彻底解析失败，网站完全打不开。**

### 症状 vs 误判

| 你以为 | 实际 |
|---|---|
| 网站挂了 | 域名解析挂了 |
| 托管有问题 | DNSSEC 校验失败 |
| DNS 没生效 | DNS 生效了但被拒绝返回结果 |

因为问题不在 NS 本身，所以无论怎么等、怎么刷新缓存都没用。

### 怎么查

```bash
# 1. 查 DS 记录
nslookup -type=DS xn--psszg58cgv6a4t1cr1l.xyz 8.8.8.8

# 有输出 → DNSSEC 开着，且注册局有 DS
# 无输出 → 没有 DS，安全

# 2. 查 A 记录，看是否返回 SERVFAIL
nslookup xn--psszg58cgv6a4t1cr1l.xyz 8.8.8.8
# 正常：返回 IP 或 NXDOMAIN
# 出错：DNS server failure
```

PowerShell：

```powershell
Resolve-DnsName -Name xn--psszg58cgv6a4t1cr1l.xyz -Type DS -Server 8.8.8.8
Resolve-DnsName -Name xn--psszg58cgv6a4t1cr1l.xyz -Type A  -Server 8.8.8.8
```

### 怎么解决

```
1. 登录注册商（Spaceship）
2. 找到 DNSSEC / DNS 安全 设置
3. 删除所有 DS 记录 / 关闭 DNSSEC
4. 等 20 分钟 ~ 2 小时，注册局同步
```

### 我们这次的实际经历

| 时间 | 状态 |
|---|---|
| 19:17 | 改完 NS，Spaceship 显示「传播中」 |
| 19:20 | DS `708/13` 仍在，A 查询 SERVFAIL |
| 19:51 | 8.8.8.8 / 1.1.1.1 已无 DS，SERVFAIL 解除 |

**用了 34 分钟。**

### 教训

> **换 NS 之前，先去注册商确认 DNSSEC 是关闭的。**

如果开着，有两种选择：
- 先关 DNSSEC → 改 NS → 等服务生效 → 在 Cloudflare 重新开启（推荐）
- 或者接受一段时间的 SERVFAIL

---

## 6. 那位「停车页」A 记录

加域名到 Cloudflare 时，它自动扫描现有记录，扫到两条：

```
A  沈阳奶龙大学.xyz  54.149.79.189     ← AWS 俄勒冈
A  沈阳奶龙大学.xyz  34.216.117.25     ← AWS 俄勒冈
```

这是 **Spaceship 给未配置域名的默认停放页**（parking page）。

不删的后果：访问你的域名会看到 Spaceship 的「此域名已注册」页面。

**解法：全部删除。** 绑 Workers 自定义域时，Cloudflare 会自动加上正确的记录。

---

## 7. 验证命令速查

```bash
# 我常用的一整套
DOMAIN=xn--psszg58cgv6a4t1cr1l.xyz

# NS 是否已切到 Cloudflare
dig NS $DOMAIN +short @8.8.8.8

# 是否还有 DNSSEC
dig DS $DOMAIN +short @8.8.8.8

# 解析是否正常
dig A $DOMAIN +short @8.8.8.8

# 直接问 Cloudflare 权威（绕过缓存）
dig A $DOMAIN +short @miki.ns.cloudflare.com
```

PowerShell 版本：

```powershell
$d = 'xn--psszg58cgv6a4t1cr1l.xyz'
foreach($s in @('8.8.8.8','1.1.1.1','223.5.5.5')){
  "--- $s ---"
  Resolve-DnsName -Name $d -Type NS -Server $s | Where-Object {$_.NameHost} | Select-Object -Expand NameHost
}
```

---

## 8. 一句话总结

> **域名是名字，DNS 是翻译，NS 决定谁来翻译，DNSSEC 是翻译的防伪印章。**
> **换翻译之前，先把防伪印章摘掉，否则没人敢信翻译结果。**
