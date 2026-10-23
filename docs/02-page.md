# 02 · 页面：HTML / CSS / JS 三层

> 整个页面只有 1 张图 + 7 KB 的 HTML。没有框架、没有构建、没有 npm install。

---

## 1. 三层分工

| 技术 | 管什么 | 类比 |
|---|---|---|
| **HTML** | 有什么东西 | 骨架 |
| **CSS** | 长什么样、怎么动 | 衣服 + 动作设计 |
| **JavaScript** | 什么时候干什么 | 大脑 |

一句话记住：

> **HTML 说"这里有一张图"，CSS 说"它是圆的、在转"，JS 说"图加载完再转，转 2.6 秒跳走"。**

---

## 2. HTML：只有一张图

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>沈阳奶龙大学 · 正在前往沈阳理工大学官网</title>

  <!-- 关键：让浏览器优先加载这张大图 -->
  <link rel="preload" as="image" href="/badge.webp" fetchpriority="high">

  <!-- 无 JS 时的兜底：直接 meta 跳转 -->
  <noscript><meta http-equiv="refresh" content="3;url=https://www.sylu.edu.cn/"></noscript>
</head>
<body>
  <div class="badge">
    <img class="mark" id="mark" src="/badge.webp" alt="沈阳奶龙大学" decoding="async">
  </div>
  <script>/* 见第 4 节 */</script>
</body>
</html>
```

### 三个容易被忽略的属性

| 属性 | 作用 |
|---|---|
| `rel="preload"` | 提前请求图片，不等到解析到 `<img>` 才开始 |
| `fetchpriority="high"` | 告诉浏览器这比别的资源更急 |
| `decoding="async"` | 图片解码不阻塞主线程 |
| `viewport-fit=cover` | iPhone 刘海屏下不留白边 |

---

## 3. CSS：圆形布局 + 旋转

### 3.1 整体居中

```css
html, body {
  height: 100%;
  margin: 0;
  overflow: hidden;                 /* 旋转时不会出现滚动条 */
  background: #ffde59;              /* 黄色背景 */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;          /* 垂直水平居中 */
}
```

### 3.2 徽章容器：保持正方形

```css
.badge {
  position: relative;
  width: min(80vw, 80vh, 400px);    /* 三个限制取最小 */
  aspect-ratio: 1;                  /* 高度 = 宽度，永远正方形 */
  cursor: pointer;                  /* 鼠标变手型，暗示可点 */
}
```

**`min(80vw, 80vh, 400px)` 的用意**：

| 值 | 防的是什么 |
|---|---|
| `80vw` | 屏幕太窄时，别横向溢出 |
| `80vh` | 屏幕太矮（横屏手机）时，别纵向溢出 |
| `400px` | 桌面大屏上别铺满整个屏幕 |

三个一起用，保证任何设备上都是"合适大小"。

### 3.3 白色圆盘占位

图片可能加载慢，先画一个白圆盘顶着：

```css
.badge::before {
  content: "";
  position: absolute;
  inset: 7%;                        /* 比容器小一圈 */
  border-radius: 50%;               /* 变成圆 */
  background: #fff;
  box-shadow: 0 10px 34px -10px rgba(120,96,20,.22),
              inset 0 0 0 1px rgba(120,96,20,.05);
}
```

### 3.4 图片：淡入 + 旋转

```css
.mark {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;              /* 等比缩放，不裁切 */
  opacity: 0;                       /* 默认隐藏 */
  transition: opacity .28s ease;    /* 淡入过渡 */
  filter: drop-shadow(0 14px 38px rgba(120,96,20,.16));
}

/* 关键：加了 .ready 才开始显示和旋转 */
.mark.ready {
  opacity: 1;
  animation: spin 26s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

**为什么用 `.ready` 类而不是直接写动画？**

因为图片还没下载完就开始转，用户会看到"空白在转"。改成 JS 控制：

```
图片 onload → 加 .ready 类 → 才显示 + 才转
```

### 3.5 无障碍：尊重系统的"减少动态效果"

```css
@media (prefers-reduced-motion: reduce) {
  .mark { animation: none; }
}
```

有些用户开了"减少动效"（前庭功能障碍患者），这时候不应该强制旋转。

---

## 4. JavaScript：三段逻辑

### 4.1 配置

```javascript
var TARGET = "https://www.sylu.edu.cn/";   // 最后跳到哪
var DUR = 2600;                             // 停留多久（毫秒）
var STAY = /[?&]stay\b/.test(location.search);  // 调试模式：?stay 不跳走
var REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
if (REDUCED) DUR = 900;                     // 减少动效时缩短停留
```

**`?stay` 是调试神器**：本地预览时加在网址后面，页面就不会自己跳走，方便反复看效果。

```
http://127.0.0.1:8791/?stay
```

### 4.2 跳转

```javascript
function go() {
  location.replace(TARGET);   // replace 而不是 href
}
```

**为什么用 `location.replace` 而不是 `location.href`？**

| | 行为 |
|---|---|
| `location.href = url` | 会**留下历史记录**，用户按返回键会回到过场页 |
| `location.replace(url)` | **替换**当前历史记录，按返回键直接回上一个网站 |

用过场页时应该用 `replace`，否则用户点返回又看到奶蛙在转，很烦。

### 4.3 核心：图片到了才开始

```javascript
var mark = document.getElementById("mark");
var markStarted = false;

function startSpin() {
  if (markStarted) return;          // 只执行一次
  markStarted = true;

  if (mark.naturalWidth > 0) {
    // 图片真的加载成功了
    mark.classList.add("ready");    // 淡入 + 开始旋转
    if (!STAY) arm(DUR);            // 开始倒计时
  } else if (!STAY) {
    // 图片没到（加载失败或太慢）→ 别让用户干等，直接跳
    setTimeout(go, 700);
  }
}

// 图片已缓存？立刻开始
if (mark.complete && mark.naturalWidth > 0) {
  startSpin();
} else {
  mark.addEventListener("load", startSpin);
  mark.addEventListener("error", startSpin);
  setTimeout(startSpin, 6000);      // 6 秒兜底
}
```

**这段是整个页面最关键的 20 行。** 解决了三个问题：

| 问题 | 解法 |
|---|---|
| 图没到就空转 | `mark.naturalWidth > 0` 才启动 |
| 图加载失败卡死 | `error` 事件也触发 `startSpin`，走"直接跳"分支 |
| 图永远不来 | 6 秒超时兜底 |

### 4.4 倒计时（可暂停）

```javascript
var timer = null, left = 0, started = 0, paused = false;

function arm(ms) {
  started = Date.now();
  timer = setTimeout(go, ms);
}

function pause() {
  if (paused || !timer) return;
  clearTimeout(timer);
  timer = null;
  paused = true;
  left = Math.max(0, DUR - (Date.now() - started));   // 算剩余时间
}

function resume() {
  if (!paused) return;
  paused = false;
  arm(left > 0 ? left : 400);
}
```

用途：打开"关于"弹窗时暂停倒计时，关掉继续。

### 4.5 交互：点任意处立刻走

```javascript
document.addEventListener("click", function (e) {
  if (e.target.closest("#aboutBtn")) return;   // 点"关于"不算
  if (STAY) return;
  go();
}, { passive: true });

document.addEventListener("keydown", function (e) {
  if (e.key === "Tab") return;                 // 保留键盘导航
  if (STAY) return;
  go();
});
```

---

## 5. 完整数据流

```
页面加载
   ↓
HTML 解析到 <img src="/badge.webp">
   ↓（preload 已经提前在下载了）
图片下载中… 此时显示白色圆盘占位
   ↓
图片 onload 触发
   ↓
加 .ready 类 → opacity 0→1 淡入 → animation 启动
   ↓
arm(2600) 开始倒计时
   ↓
2.6 秒后（或用户点击）
   ↓
location.replace("https://www.sylu.edu.cn/")
```

---

## 6. 文件大小

| 文件 | 大小 | 说明 |
|---|---|---|
| index.html | 7.3 KB | 含全部 CSS 和 JS，内联，零外部请求 |
| badge.webp | 57.5 KB | 唯一的大文件 |
| favicon.png | 84 KB | 只在标签页显示，不影响加载 |
| **首屏关键路径** | **≈ 65 KB** | |

**没有引入任何第三方库**。没有 jQuery、没有 React、没有 Google Fonts。
这意味着：没有额外的 DNS 查询、没有额外的连接建立、没有版本冲突。

---

## 7. 为什么不用框架

| 方案 | 代码量 | 首屏大小 | 适合度 |
|---|---|---|---|
| 原生 HTML/CSS/JS | ~200 行 | 65 KB | ✅ |
| React + Vite | 500+ 行 | 150 KB+ | ❌ 杀鸡用牛刀 |
| Vue + Vite | 400+ 行 | 120 KB+ | ❌ |

一个"转 4 秒就跳走"的页面，引入框架纯粹是增加加载时间和故障点。

---

## 8. 本地预览

```bash
cd site
python -m http.server 8791

# 浏览器打开
http://127.0.0.1:8791/?stay     # ?stay = 不跳转，方便调试
http://127.0.0.1:8791/          # 正常模式，4 秒后跳走
```

**必须用 HTTP 服务器打开**，不能直接双击 `index.html`。
因为页面里用的是绝对路径 `/badge.webp`，`file://` 协议下会 404。

```bash
# 如果 8791 端口被占用
python -m http.server 8792
```

---

## 9. 小结

> **一个页面 = 一张图 + 一句 `location.replace` + 一段"等图到了再说"的逻辑。**
> 剩下的 CSS 都是为了让这张图看起来像个校徽。
