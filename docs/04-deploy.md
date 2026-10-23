# 04 · 部署：Cloudflare Workers

> 免费、无需服务器、自动 HTTPS 证书、全球 CDN。
> 整个部署过程 = 拖 4 个文件 + 点一次按钮。

---

## 1. 为什么选 Cloudflare

| 需求 | Cloudflare 免费版 |
|---|---|
| 静态文件托管 | ✅ 无限 |
| HTTPS 证书 | ✅ 自动签发、自动续期 |
| 全球 CDN | ✅ |
| 自定义域名 | ✅ 数量不限 |
| 流量费用 | ✅ 0 |
| 需要服务器 | ❌ 不需要 |

对比其他选择：

| 方案 | 问题 |
|---|---|
| 阿里云 ECS | 要买服务器、要备案、要配 Nginx |
| GitHub Pages | 国内访问极慢，自定义域名证书麻烦 |
| Vercel | 国内访问不稳定 |
| Netlify | 同上 |
| **Cloudflare Workers** | 唯一缺点：`*.workers.dev` 子域在国内被封 |

---

## 2. Workers 和 Pages 的区别

两个产品都能做静态托管，门槛不同：

| | Pages | Workers（静态资产） |
|---|---|---|
| 定位 | 纯静态站点 | 边缘函数 + 静态资产 |
| 入口 | Create → Pages → Upload assets | Create → Upload static files |
| 默认域名 | `xxx.pages.dev` | `xxx.账户.workers.dev` |
| 静态资源计费 | 免费 | 免费（请求不计费） |
| 自定义域 | 支持 | 支持 |
| 证书 | 自动 | 自动 |

**我们最后用的是 Workers**（因为新版界面把「Upload your static files」导向了 Worker），功能完全够用。

### 一个关键点

```
*.workers.dev 在中国大陆无法访问（DNS 污染 + IP 阻断）
```

**但这不影响最终效果**，因为观众访问的是你的自定义域名 `沈阳奶龙大学.xyz`，走的是 Cloudflare CDN 的 anycast IP，国内可以访问。

只有你自己调试时的 `xxx.workers.dev` 打不开。

---

## 3. 完整部署流程

### 3.1 准备工作

```
☑ Cloudflare 账号（免费注册，需邮箱验证）
☑ 本地准备好 4 个文件
```

文件清单：

```
index.html      7.3 KB
badge.webp     57.5 KB
favicon.png      84 KB
og.jpg         62.5 KB
```

### 3.2 上传

```
1. dash.cloudflare.com
2. 左侧菜单 → 计算 → Workers 和 Pages
3. Create / 创建
4. 选「Upload your static files」/「上传静态文件」
5. 项目名填：nailong
6. 把 4 个文件全选拖进去
7. Deploy / 部署
```

⚠️ **拖的是文件，不是文件夹。**

如果拖了 `site` 文件夹本身，会多套一层目录：

```
https://xxx.workers.dev/site/index.html   ← 错
https://xxx.workers.dev/index.html        ← 对
```

页面里用的是绝对路径 `/badge.webp`，多套一层会导致全部 404。

### 3.3 得到临时地址

```
https://nailong.3510083235.workers.dev
```

**这个地址在国内打不开**（正常）。跳过，直接绑域名。

---

## 4. 绑定自定义域名

### 4.1 前置条件

```
☑ 域名已经添加到 Cloudflare（NS 已指向 CF）
☑ Cloudflare 概览页状态是 Active
☑ DNSSEC 已关闭（见 docs/01-dns.md）
```

### 4.2 操作

```
Workers 和 Pages → nailong
→ 「域名和路由」区块
→ 「连接自定义域」/ Add custom domain
→ 填：xn--psszg58cgv6a4t1cr1l.xyz    ← punycode！
→ 确认
```

### 4.3 Cloudflare 自动做的事

```
✔ 在你的 DNS 里加记录（指向 Worker）
✔ 签发 SSL 证书（Let's Encrypt / Google Trust Services）
✔ 配上 CDN
```

**不用手动加 DNS 记录。**

### 4.4 证书签发时间

```
1 分钟 ~ 30 分钟
```

刚绑完访问可能报证书错误，等一下再试。

---

## 5. 验证清单

### 5.1 命令行验证

```bash
DOMAIN=xn--psszg58cgv6a4t1cr1l.xyz

# 1. HTTP 状态
curl -sSI "https://$DOMAIN/" | head -1
# 期望：HTTP/2 200

# 2. 内容正确
curl -sS "https://$DOMAIN/" | grep -c '沈阳奶龙大学'
# 期望：>= 1

# 3. 资源都在
for f in badge.webp favicon.png og.jpg; do
  printf '%s -> ' "$f"
  curl -sS -o /dev/null -w '%{http_code}\n' "https://$DOMAIN/$f"
done
# 期望：全部 200

# 4. 服务器是 Cloudflare
curl -sSI "https://$DOMAIN/" | grep -i '^server'
# 期望：server: cloudflare
```

PowerShell 版本：

```powershell
$d = 'xn--psszg58cgv6a4t1cr1l.xyz'
curl.exe -4 -sS -o NUL -w "%{http_code} %{size_download}B %{time_total}s" "https://$d/"
```

### 5.2 浏览器验证

```
1. 手机打开 沈阳奶龙大学.xyz
2. 观察三件事：
   □ 白色圆盘出现
   □ 徽章淡入并开始旋转
   □ 约 4 秒后跳到沈阳理工大学官网
3. 看地址栏有没有小锁（HTTPS）
```

### 5.3 自动跳转验证

用 Playwright 或手动：

```javascript
// 在控制台跑
location.href
// 4 秒后再看，应该是 https://www.sylu.edu.cn/
```

---

## 6. 更新已部署的站点

改完文件后要重新上传：

```
Workers 和 Pages → nailong
→ 「部署」标签
→ 「新部署」/「Create new deployment」
→ 拖新的文件
→ Deploy
```

### 缓存问题

Cloudflare 会缓存静态资源。如果上传后看到旧版：

```
Cloudflare → 你的域名 → 缓存 → 清除缓存 → 清除所有内容
```

或者用无痕窗口 / 加查询参数：

```
https://xn--psszg58cgv6a4t1cr1l.xyz/?v=2
```

---

## 7. 国内访问速度问题（重要）

### 实测数据（2026-10）

```
IPv6 → 完全超时（30s，0 字节）
IPv4 → 200，但 86 KB 要 5.5 秒（约 15 KB/s）
```

### 原因

Cloudflare 免费版在中国大陆没有专用节点，流量路由到境外（香港/新加坡/日本/美国），速度不稳定。

### 缓解手段

**① 压缩资源（最有效）**

```
86 KB → 57 KB   （第一轮优化）
```

**② 加载策略**

```
图片 preload，优先加载
图没到就不转（避免空转）
6 秒兜底，直接跳转
```

**③ 浏览器自动回退**

现代浏览器有 **Happy Eyeballs** 机制：

```
先尝试 IPv6（250ms 超时）
→ 失败就立刻回退 IPv4
```

所以真实用户不会卡在 IPv6 超时上，只是整体速度受限于 IPv4 链路。

**④ 如果还是太慢**

| 方案 | 代价 |
|---|---|
| 继续压图（560px / q70 → 40 KB） | 3x 屏会软 |
| 升级 Cloudflare Pro（$20/月） | 有中国大陆优化路由 |
| 换国内 CDN + 备案 | 要备案，流程长 |

**对过场页来说，57 KB / 4 秒是可以接受的。** 因为观众只需要看 4 秒。

---

## 8. 成本核算

| 项 | 费用 |
|---|---|
| Cloudflare 账号 | ¥0 |
| Workers 静态托管 | ¥0（10 万请求/天） |
| DNS | ¥0 |
| HTTPS 证书 | ¥0 |
| **总计** | **¥0** |

真正花的只有域名：**¥13.75 / 首年**。

---

## 9. 常见错误

| 错误信息 | 原因 | 解法 |
|---|---|---|
| `not a valid domain` | 填了中文域名 | 改填 punycode |
| `DNS record already exists` | 有旧的 A/CNAME 记录 | 先删除旧记录再绑 |
| 绑域名后 404 | 文件传到了子目录 | 重新上传，只传文件 |
| 样式全丢 | 同上（资源 404） | 同上 |
| 页面出来了但没证书 | 证书还在签发 | 等 1–30 分钟 |
| 上传后还是旧版 | CDN 缓存 | 清缓存 / 无痕窗口 |
| Worker 部署成功但打不开 | `workers.dev` 被墙 | 绑自定义域名 |

---

## 10. 小结

> **部署 = 拖文件 + 点按钮 + 绑域名。**
> **全程不需要碰服务器、不需要命令行、不需要备案。**
