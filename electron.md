# Presenton Electron 架构与本地开发指南 (Windows)

本文档旨在帮助中国大陆开发者在 Windows 环境下顺利编译、魔改并运行 Presenton Electron 桌面版本。

## 1. 演进背景：为什么从 Docker 转向 Electron？

维护者逐步引入 Electron 是为了解决 Web 版在本地环境下的局限性：

*   **部署零门槛**：不再需要用户安装 Docker、配置 WSL2，通过一个 `.exe` 安装包即可完成 Next.js 前端和 FastAPI 后端的全量部署。
*   **硬件加速**：Electron 窗口直接调用系统 GPU 资源，PPT 生成和图片渲染性能显著优于浏览器容器。
*   **本地生态集成**：Electron 能以原生方式访问本地 127.0.0.1 上的 Ollama 服务，避开了 Docker 网络复杂的端口映射问题。
*   **离线能力**：内置 Python 环境和打包好的二进制后端，支持在无网环境下进行基础的文档处理。

---

## 2. 中国大陆环境下的“编译魔改” (必做)

由于 Electron 构建依赖大量国外服务器资源，直接运行 `npm run build` 极易失败。请务必执行以下优化。

### 2.1 设置国内镜像源 (PowerShell)
在编译前，在终端执行以下命令：

```powershell
# 1. NPM 镜像
npm config set registry https://registry.npmmirror.com

# 2. Electron 二进制加速 (解决构建时卡在 "Downloading electron...")
$env:ELECTRON_MIRROR="https://npmmirror.com/mirrors/electron/"
$env:ELECTRON_BUILDER_BINARIES_MIRROR="https://npmmirror.com/mirrors/electron-builder-binaries/"

# 3. Python 镜像 (用于 FastAPI 后端打包)
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2.2 自动编译脚本
项目已封装好一键构建流程：
```powershell
cd electron
npm install
npm run build:all
```
*该脚本会自动完成：Next.js 导出 -> FastAPI (PyInstaller) 打包 -> Electron 封装。*

---

## 3. 关于生成的 .exe 文件：安装 vs 直接运行

### 3.1 默认：安装包 (NSIS)
项目目前默认生成的是 **NSIS 安装包**。
*   **位置**：`electron/dist/Presenton-X.X.X.exe`
*   **行为**：双击后会运行安装程序，将软件安装到系统目录并创建桌面图标。

### 3.2 魔改：如何生成“绿色便携版” (Portable)
如果您希望生成一个“双击即运行、无需安装”的单个 `.exe`，请修改 `electron/build.js`：

找到 `win` 配置项，修改为：
```javascript
win: {
  target: ["portable"], // 将 nsis 改为 portable
  icon: "build/icon.ico",
  artifactName: "Presenton-Portable-${version}.${ext}",
}
```
再次运行 `npm run build:electron`，在 `dist` 目录下即可获得便携版。

---

## 4. 代理层魔改建议
如果您在大陆环境使用时遇到 LLM 接口连接问题（如访问 OpenAI/Claude 报错），建议在 `electron/app/main.ts` (或相关主进程文件) 中引入代理支持。

在 Electron 初始化位置添加：
```typescript
import { session } from 'electron';

// 强制 Electron 使用本地代理 (例如 Clash/V2Ray)
session.defaultSession.setProxy({
  proxyRules: "http://127.0.0.1:7890", // 替换为你的本地代理端口
});
```

---

## 5. 总结
*   **优点**：更强性能、更低门槛、更原生。
*   **编译关键**：必须配置 `ELECTRON_MIRROR` 环境变量。
*   **输出**：默认是安装包，可魔改为便携版。
