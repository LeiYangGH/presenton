# Presenton Electron 构建 — 中国大陆网络问题与依赖管理指南

> 本文档记录在中国大陆网络环境下从源码构建 Presenton Electron 应用时遇到的所有依赖下载/网络问题、解决方案，以及为避免重复下载所做的优化。

---

## 1. 问题总览

| # | 依赖 | 大小 | 原始来源 | 问题 | 解决方案 |
|---|------|------|----------|------|----------|
| 1 | Electron v36.9.5 | 122 MB | `github.com/electron/electron` | GitHub 连接超时 | 手动下载放入缓存 |
| 2 | Chromium (browser snapshots) | ~150 MB | `storage.googleapis.com` | 被墙 | 源码已改用 npmmirror 镜像；手动下载放入缓存 |
| 3 | LibreOffice | ~300 MB | `download.documentfoundation.org` | 极慢 | 源码已改用清华 TUNA 镜像 |
| 4 | winCodeSign / NSIS | ~7 MB | `github.com/electron-userland` | GitHub 连接超时 | `ELECTRON_BUILDER_BINARIES_MIRROR` 环境变量 |
| 5 | Cypress | ~250 MB | `download.cypress.io` | npm install 时自动下载，仅用于测试 | `CYPRESS_INSTALL_BINARY=0` 跳过 |
| 6 | Puppeteer 内置 Chromium | ~170 MB | `storage.googleapis.com` | npm install 时自动下载，运行时不需要 | `.puppeteerrc.cjs` 设置 `skipDownload: true` |
| 7 | fastembed 模型 | ~67 MB | HuggingFace | 首次构建向量库时下载 | 缓存在 `~/.cache/fastembed_cache/`，不重复下载 |
| 8 | ImageMagick | ~30 MB | `imagemagick.org` | 运行时安装，速度尚可 | 内置安装流程，缓存在 `%LOCALAPPDATA%\Presenton\runtime\imagemagick` |

---

## 2. Windows 命令兼容性

**问题**：`package.json` 脚本使用 `rm -rf`、`cp -r` 等 Unix 命令，Windows 上报错 `'rm' is not recognized`。

**解决**：安装 `shx` 并替换所有 Unix 命令：
```bash
npm install --save-dev shx
```
所有 `rm -rf` → `shx rm -rf`，`cp -r` → `shx cp -r`。已在 `package.json` 中修改完毕。

---

## 3. 各依赖详细解决方案

### 3.1 Electron 二进制 (electron-builder)

**缓存位置**（优先级从高到低）：
```
C:\Users\<用户>\AppData\Local\electron\Cache\           ← electron-builder 优先检查
C:\Users\<用户>\AppData\Local\electron-builder\Cache\   ← 备用
```

**手动放置**：下载 `electron-v36.9.5-win32-x64.zip`，放入：
```
C:\Users\<用户>\AppData\Local\electron\Cache\electron-v36.9.5-win32-x64.zip
```
> ⚠️ 注意：不要放到 `electron-builder\Cache\electron\v36.9.5\` 子目录，electron-builder 优先读 `electron\Cache\` 根目录。如果该目录存在不完整的 zip（如中断的下载），必须先删除再替换。

**代理方式**：
```powershell
$env:HTTPS_PROXY="http://127.0.0.1:7890"
npm run build:electron
```

### 3.2 electron-builder 附属工具 (winCodeSign, NSIS)

**缓存位置**：`C:\Users\<用户>\AppData\Local\electron-builder\Cache\`

**镜像加速**：
```powershell
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://ghfast.top/https://github.com/electron-userland/electron-builder-binaries/releases/download/"
```
> 下载后自动缓存，后续构建不再下载。

### 3.3 Chromium (运行时依赖)

应用运行时需要 Chromium 来渲染幻灯片/导出 PDF。

**源码优化**（已完成）：
- `app/ipc/setup_install_handlers.ts`：安装时从 npmmirror 镜像下载
- `app/utils/puppeteer-check.ts`：检测逻辑同时支持 `Browser.CHROMIUM` 和 `Browser.CHROME`

**手动放置**：下载 `chrome-win.zip`，解压到：
```
C:\Users\<用户>\.cache\puppeteer\chromium\win64-<buildId>\chrome-win\chrome.exe
```

**检测路径**（按优先级）：
1. `puppeteer.executablePath()` — Puppeteer 默认 Chrome for Testing
2. `~/.cache/puppeteer/` 下的 `Browser.CHROMIUM`
3. `~/.cache/puppeteer/` 下的 `Browser.CHROME`（fallback）

### 3.4 LibreOffice (运行时依赖)

用于 PPTX → PDF 高保真转换（headless 模式）。

**源码优化**（已完成）：`app/utils/libreoffice-urls.ts` 改用清华 TUNA 镜像：
```
https://mirrors.tuna.tsinghua.edu.cn/libreoffice/libreoffice/stable
```

**检测逻辑**：扫描 `Program Files` 和 `PATH`，已安装则不重复下载。

### 3.5 Puppeteer npm install 阶段

**问题**：`npm install` 时 puppeteer 自动下载 ~170MB Chrome for Testing。

**解决**：项目根目录 `.puppeteerrc.cjs`：
```js
module.exports = { skipDownload: true };
```
> ⚠️ 该文件仅影响 npm postinstall 行为。运行时检测已修复为不受 `skipDownload` 影响。

### 3.6 Cypress npm install 阶段

**问题**：`npm install` (nextjs) 时 Cypress 自动下载 ~250MB 测试浏览器。

**解决**：`setup:env` 脚本中已添加 `cross-env CYPRESS_INSTALL_BINARY=0`：
```json
"setup:env": "npm install && ... && cross-env CYPRESS_INSTALL_BINARY=0 npm install && ..."
```

---

## 4. 一键构建命令（推荐）

```powershell
# 1. 设置 electron-builder 镜像（可选，有代理可跳过）
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://ghfast.top/https://github.com/electron-userland/electron-builder-binaries/releases/download/"

# 2. 如果需要代理（可选）
# $env:HTTPS_PROXY="http://127.0.0.1:7890"

# 3. 构建
cd D:\0ly\presenton\electron
npm run build:all
```

---

## 5. 缓存复用总结

所有依赖下载后均有本地缓存，**二次构建不会重复下载**：

| 依赖 | 缓存位置 | 触发重新下载的条件 |
|------|----------|-------------------|
| Electron | `%LOCALAPPDATA%\electron\Cache\` | 升级 Electron 版本 |
| winCodeSign/NSIS | `%LOCALAPPDATA%\electron-builder\Cache\` | 版本变更 |
| Chromium | `%USERPROFILE%\.cache\puppeteer\chromium\` | 手动删除缓存 |
| Chrome for Testing | `%USERPROFILE%\.cache\puppeteer\chrome\` | puppeteer 大版本升级 |
| LibreOffice | 系统安装路径 | 卸载后 |
| ImageMagick | `%LOCALAPPDATA%\Presenton\runtime\imagemagick\` | 手动删除 |
| fastembed 模型 | `%USERPROFILE%\.cache\fastembed_cache\` | 手动删除 |
| npm 包 | `node_modules\` | 删除 node_modules 后 |
| Python 包 | `.venv\` (uv) | 删除 .venv 后 |

---

## 6. 源码修改清单

| 文件 | 修改内容 |
|------|----------|
| `package.json` | `rm`/`cp` → `shx` 版本；`setup:env` 加 `CYPRESS_INSTALL_BINARY=0` |
| `app/utils/puppeteer-check.ts` | 检测逻辑支持 Chrome + Chromium；移除 `shouldSkipDownload()` 对检测的干扰 |
| `app/ipc/setup_install_handlers.ts` | Chromium 安装使用 npmmirror 镜像 |
| `app/utils/libreoffice-urls.ts` | LibreOffice CDN 改为清华 TUNA 镜像 |
| `servers/fastapi/services/temp_file_service.py` | 临时文件清理加 `try/except` 容错 |
| `.puppeteerrc.cjs` (新增) | npm install 阶段跳过 Chromium 下载 |
| `servers/nextjs/.puppeteerrc.cjs` (新增) | 同上 |
| `.gitignore` | 忽略大二进制文件和 `.puppeteerrc.cjs` |

---

## 7. Windows Defender 注意事项

electron-builder 解压 `electron.exe` 后，Windows Defender 可能将其隔离。如构建报错：
```
ENOENT: rename 'electron.exe' -> 'Presenton.exe'
```
需在 Windows 安全中心添加排除项：
- `D:\0ly\presenton\electron\`
- `C:\Users\<用户>\AppData\Local\electron-builder\`
