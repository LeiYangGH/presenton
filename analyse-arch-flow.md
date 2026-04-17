# Presenton 架构与编译/运行流程分析

## 1. 项目总体定位

Presenton 是一个多形态交付的 AI 幻灯片生成系统，核心能力包括：

- **基于 LLM 生成演示文稿大纲与幻灯片内容**
- **基于图片/图标/图表等资产增强页面内容**
- **导出为 PPTX / PDF**
- **支持默认模板与用户自定义模板**
- **同时支持 Desktop（Electron）与 Web/Docker 部署形态**

它不是单体前端或单体后端，而是一个由多个子系统协同组成的桌面/Web 混合架构。

## 2. 核心技术栈

### 2.1 顶层技术分层

- **桌面壳**：Electron
- **前端 UI**：Next.js 14 + React 18 + TypeScript
- **后端 API**：FastAPI + SQLModel + Alembic
- **数据库**：SQLite 默认，也支持 PostgreSQL / MySQL
- **Python 依赖管理**：`uv`
- **Node 依赖管理**：`npm`
- **桌面打包**：`electron-builder`
- **Python 后端打包**：PyInstaller
- **静态构建产物服务**：`serve-handler`
- **文档/PPT 处理**：LibreOffice、python-pptx、pdfplumber、docling
- **浏览器自动化/截图能力**：Puppeteer + Chromium
- **本地/自托管模型支持**：Ollama
- **向量/检索相关**：ChromaDB
- **样式/UI**：Tailwind CSS、Radix UI、TipTap、Recharts

### 2.2 目录职责

#### 根目录

- `start.js`
  - Web / Docker 形态下的统一启动脚本
  - 负责启动 FastAPI、Next.js、MCP server、Ollama、Nginx
- `Dockerfile`
  - 生产镜像构建定义
- `Dockerfile.dev`
  - 开发镜像构建定义
- `docker-compose.yml`
  - 生产/开发、GPU/非 GPU 的运行编排

#### `servers/nextjs`

- 主要前端应用
- 负责页面、编辑器、设置页、模板展示、生成流程交互
- 也承载部分“模板代码/动态渲染相关”的前端能力

#### `servers/fastapi`

- 主要后端 API
- 负责生成、导出、模板、图片、数据库、异步任务等逻辑

#### `electron`

- 桌面端工程
- 包含 Electron 主进程、IPC、依赖检查、构建脚本、桌面资源打包逻辑
- 会把 Next.js 和 FastAPI 的产物封装到桌面应用中

## 3. 两种主要运行形态

项目实际上有两种主模式：

### 3.1 Web / Docker 模式

用户通过浏览器访问系统：

- Nginx 暴露 `80`
- Node `start.js` 启动 Next.js + FastAPI + MCP + Ollama
- 浏览器访问 Next.js 页面
- 页面请求 FastAPI API
- 导出、文件处理、数据库持久化都在容器里完成

### 3.2 Electron Desktop 模式

用户运行桌面程序：

- Electron 主进程启动
- Electron 先检查本地依赖（如 LibreOffice、Chrome/Chromium、ImageMagick）
- 再启动内嵌 FastAPI 服务和 Next.js 服务
- 最后 BrowserWindow 加载本地 Next.js 页面

这里 Electron 本质上是一个**桌面宿主 + 进程编排器**，而不是把业务逻辑全部写进 Electron。

## 4. 编译期 / 构建期总体视角

“编译期”在这个项目里不是单一编译，而是多条构建链路并行存在：

- **前端构建链**：Next.js build
- **桌面主进程构建链**：TypeScript -> `app_dist`
- **Python 后端打包链**：PyInstaller -> 可执行 FastAPI
- **Electron 打包链**：electron-builder -> 安装包 / portable 包
- **Docker 镜像构建链**：apt + pip + npm + next build + runtime assembly

所以你要把它理解为一个“多产物工程”：

- Web 产物
- Desktop 产物
- Python 二进制产物
- Electron 安装包产物

## 5. 开发环境首次安装会下载什么

## 5.1 Electron 桌面开发模式

`electron/package.json` 中的 `setup:env`：

```json
"setup:env": "npm install && cd servers/fastapi && uv sync && cd ../../servers/nextjs && cross-env CYPRESS_INSTALL_BINARY=0 npm install && cd ../.. && npm run setup:export-runtime"
```

首次安装会做这些事：

- **安装 Electron 根依赖**
  - 下载 Electron
  - 下载 electron-builder
  - 下载 TypeScript、Tailwind CLI、Puppeteer、Sharp 等

- **安装 FastAPI Python 依赖**
  - 通过 `uv sync` 根据 `pyproject.toml` / `uv.lock` 安装 Python 包
  - 包括：
    - `fastapi[standard]`
    - `sqlmodel`
    - `alembic`
    - `aiohttp`
    - `aiosqlite`
    - `asyncpg`
    - `aiomysql`
    - `chromadb`
    - `docling`
    - `pdfplumber`
    - `python-pptx`
    - `openai`
    - `fastmcp`
    - `dirtyjson`
    - `redis`

- **安装 Next.js 前端依赖**
  - `next`
  - `react`
  - `@radix-ui/*`
  - `@reduxjs/toolkit`
  - `tiptap`
  - `recharts`
  - `sharp`
  - `puppeteer`
  - `cypress`（通过 `CYPRESS_INSTALL_BINARY=0` 避免下载 Cypress 二进制）

- **同步 export runtime**
  - 通过 `sync_export_runtime.js` 准备导出相关运行时资源
  - 这是桌面导出链路的一部分

## 5.2 Docker 构建期会下载什么

`Dockerfile` / `Dockerfile.dev` 会安装：

### 系统级依赖（apt）

- `nginx`
- `curl`
- `libreoffice`
- `fontconfig`
- `chromium`
- `zstd`

### Node 运行时

- Node.js 20（通过 NodeSource）

### Python 包（pip）

- FastAPI 相关
- SQL / DB 相关
- ChromaDB
- OpenAI / Anthropic / Google 相关 SDK
- docling（额外走 PyTorch CPU index）

### Node 包（npm install in `servers/nextjs`）

- Next.js 前端所有依赖

### 可选本地模型运行时

- 生产 Dockerfile 还会安装 **Ollama**

## 6. 编译期各主要流程如何互相配合

## 6.1 Electron 开发运行 `npm run dev`

脚本：

```json
"dev": "shx rm -rf app_dist && tsc && electron . --no-sandbox"
```

流程：

1. 清理旧的 `app_dist`
2. TypeScript 编译 Electron 主进程代码到 `app_dist`
3. 启动 Electron
4. Electron 主进程再去启动：
   - FastAPI 开发服务
   - Next.js 开发服务
5. BrowserWindow 打开 Next.js 页面

这里要注意：

- **Electron 主进程代码是预编译的**
- **Next.js 与 FastAPI 在开发模式是运行源码**
- 所以开发态是“主进程编译 + 前后端热运行”的混合模式

## 6.2 Electron 完整打包 `npm run build:all`

核心脚本：

```json
"build:all": "npm config set registry https://registry.npmmirror.com && pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && npm run clean:build && npm run setup:env && npm run build:ts && npm run install:pyinstaller && npm run build:nextjs && npm run build:fastapi && npm run build:electron"
```

它把整个工程串起来：

### 阶段 A：依赖准备

- 切 npm registry
- 切 pip index
- 清理旧产物
- 安装 Node / Python / Next.js 依赖

### 阶段 B：构建 Electron 主进程

`build:ts`

- TypeScript -> `app_dist`

### 阶段 C：构建 Next.js 前端产物

`build:nextjs`

```json
"build:nextjs": "shx rm -rf resources/nextjs && shx rm -rf servers/nextjs/.next-build && cd servers/nextjs && cross-env BUILD_TARGET=electron npm run build && shx cp -r .next-build ../../resources/nextjs && shx cp -r app/presentation-templates ../../resources/nextjs/presentation-templates"
```

这里做了几件关键事情：

- 执行 `next build`
- 构建产物输出到 `.next-build`
- 将 `.next-build` 拷贝到 `electron/resources/nextjs`
- 额外把 `app/presentation-templates` 拷贝过去

这意味着：

- 桌面版不会在生产态运行 `next start`
- 而是把构建好的静态/服务资源复制进 Electron resources
- 最终通过 `serve-handler` 直接提供这些构建产物

### 阶段 D：构建 FastAPI 可执行产物

`build:fastapi`

```json
"build:fastapi": "shx rm -rf resources/fastapi && npm run build:vectorstore && node scripts/prepare_fastapi_migrations.js && cd servers/fastapi && uv run python -m PyInstaller --distpath ../../resources server.spec"
```

主要动作：

- 构建向量库相关资源
- 预处理迁移脚本
- 用 PyInstaller 将 FastAPI 后端打包成可执行程序
- 输出到 `electron/resources/fastapi`

因此桌面生产态里，FastAPI **不是解释执行 Python 源码**，而是运行 PyInstaller 打包出来的二进制。

### 阶段 E：构建 Electron 包

`build:electron`

- 生成版本信息
- 同步 export runtime
- 重新编译 `app_dist`
- 执行 `node build.js`
- `electron-builder` 根据配置打包

`electron/build.js` 会把这些内容作为安装包资源：

- `resources`
- `app_dist`
- `node_modules`
- `NOTICE`

也就是说最终安装包里会带着：

- 编译后的 Electron 主进程
- Next.js 构建产物
- FastAPI 可执行二进制
- 导出运行时资源
- UI 资源

## 6.3 Docker 镜像构建期

Docker 形态和 Electron 不同，它不会把 FastAPI 打成独立二进制。

### 生产 Dockerfile 的流程

1. 基于 `python:3.11-slim-bookworm`
2. 安装系统工具和 LibreOffice / Chromium / Nginx
3. 安装 Node.js 20
4. 设置环境变量：
   - `APP_DATA_DIRECTORY=/app_data`
   - `TEMP_DIRECTORY=/tmp/presenton`
   - `PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium`
5. 安装 Ollama
6. `pip install` FastAPI 依赖
7. 拷贝 `servers/nextjs/package.json` 并 `npm install`
8. 拷贝 Next.js 源码并执行 `npm run build`
9. 拷贝 FastAPI 源码和 `start.js`
10. 以 `node /app/start.js` 启动

### 这说明什么

- Docker 产物偏向 **源码 + 构建产物混合运行**
- Next.js 是预编译的
- FastAPI 仍然以 Python 解释执行
- 最外层由 Node `start.js` 统一拉起多个服务

## 7. 运行时总体架构

## 7.1 Web / Docker 运行时进程关系

`start.js` 会启动：

- **FastAPI**：`python server.py --port 8000`
- **App MCP Server**：`python mcp_server.py --port 8001`
- **Next.js**：`npm run start -- -H 127.0.0.1 -p 3000`
- **Ollama**：`ollama serve`
- **Nginx**：`service nginx start`

典型请求路径：

```text
Browser
  -> Nginx:80
    -> Next.js 页面
      -> 调用 FastAPI:8000 API
        -> 数据库 / 文件系统 / LLM / 图像服务 / 导出服务
```

Node 在这里扮演的是**supervisor / orchestrator**：

- 负责拉起多个子进程
- 负责写入 userConfig
- 负责开发态自动安装 `servers/nextjs` 的 node_modules

## 7.2 Electron 运行时进程关系

Electron 主进程 `electron/app/main.ts` 启动后：

1. 创建 BrowserWindow
2. 检查依赖：
   - LibreOffice
   - Chrome/Chromium（供 Puppeteer）
   - ImageMagick
3. 初始化用户配置
4. 动态寻找空闲端口
5. 启动 FastAPI
6. 启动 Next.js
7. BrowserWindow 加载 `http://localhost:<nextjsPort>`

运行时结构：

```text
Electron Main Process
  -> FastAPI process
  -> Next.js process / static server
  -> BrowserWindow(Renderer)
       -> 调用 FastAPI API
```

## 8. Electron 运行时：开发态 vs 生产态

## 8.1 FastAPI 启动差异

来自 `electron/app/utils/servers.ts`：

### 开发态

- 命令：`uv run python server.py --port <port> --reload true`
- 直接运行 Python 源码
- 支持热重载

### 生产态

- 命令：运行打包后的 `fastapi` / `fastapi.exe`
- 即 PyInstaller 二进制

## 8.2 Next.js 启动差异

### 开发态

- 命令：`npm run dev -- -p <port>`
- 真正启动 Next.js dev server

### 生产态

- 不跑 `next start`
- 直接通过 `serve-handler` 对目录进行静态服务
- 目录就是打包进 Electron 的 `resources/nextjs`

这一点很关键，说明 Electron 生产态把 Next.js 当成“已构建资源集合”来提供，而不是完整 Node SSR 服务器。

## 9. FastAPI 运行时主流程

## 9.1 启动入口

`servers/fastapi/server.py`：

- 强制一些离线环境变量：
  - `TRANSFORMERS_OFFLINE=1`
  - `HF_HUB_OFFLINE=1`
  - `HF_DATASETS_OFFLINE=1`
- 通过 `uvicorn.run("api.main:app")` 启动 FastAPI

## 9.2 FastAPI 应用装配

`api/main.py`：

- 挂载 PPT 路由
- 挂载 webhook 路由
- 挂载 mock 路由
- 注册 CORS
- 注册用户配置中间件

## 9.3 lifespan 启动阶段

`api/lifespan.py` 中应用启动时会：

1. 创建 `APP_DATA_DIRECTORY`
2. 执行数据库迁移
3. 创建缺失的数据表
4. 检查 LLM / 图像 provider 可用性

这意味着 FastAPI 不只是一个请求处理器，它在启动阶段还承担：

- 基础设施自初始化
- 数据库 schema 自修复 / 迁移
- 外部模型/服务可用性检查

## 10. Next.js 运行时主职责

Next.js 在本项目里不只是一个普通 UI 层，它还承担：

- 演示文稿编辑与预览
- 模板管理与模板展示
- 富文本/拖拽/主题设置/图表组件
- 与 FastAPI API 对接
- Electron Renderer 页面承载

依赖侧可以看出其职责较重：

- `@radix-ui/*`：交互组件
- `@reduxjs/toolkit`：状态管理
- `@tiptap/*`：富文本编辑
- `recharts`：图表
- `html2canvas`：页面截图类能力
- `@paciolan/remote-component`、`@babel/standalone`：动态模板/代码处理能力
- `puppeteer`、`sharp`：部分前端/渲染链路相关支持

## 11. 模板系统在架构里的位置

模板系统分成两类：

### 默认模板

存放在：

- `servers/nextjs/app/presentation-templates/`

特点：

- 是源码级 TSX 组件
- 随前端一起构建
- Electron 打包时会额外复制到 `resources/nextjs/presentation-templates`

### 自定义模板

存放在数据库：

- `templates`
- `presentation_layout_codes`
- Electron 版本还有 `template_create_infos`

特点：

- 元数据存 DB
- 布局代码本身也是文本形式存 DB
- 前后端共同参与模板编辑/加载/预览

所以模板系统是一个**源码模板 + 数据库存储模板**并存的双轨架构。

## 12. 导出链路在整体架构中的位置

导出不是纯前端行为，而是跨层协作：

- 前端提交导出请求
- FastAPI 组装 presentation / slides 数据
- 使用导出服务、PPTX 生成器、外部运行时资源
- 依赖系统工具：
  - LibreOffice
  - Chromium / Puppeteer
  - ImageMagick（桌面依赖检查中也能看出）

因此导出链路依赖：

- Python 业务逻辑
- Node / Chromium 运行时
- OS 级二进制工具

这也是为什么桌面启动前要检查本地依赖是否齐全。

## 13. 数据与运行时资源的耦合方式

系统运行时同时依赖两类存储：

### 结构化数据

- 数据库存储 presentation、slides、template、imageasset 等记录

### 文件型资源

- `APP_DATA_DIRECTORY/images`
- `APP_DATA_DIRECTORY/exports`
- `APP_DATA_DIRECTORY/uploads`
- `TEMP_DIRECTORY`

因此运行时常见调用链是：

```text
UI 请求
  -> FastAPI 生成/更新数据库记录
  -> 生成或读取文件资源
  -> 再把路径/元数据返回给 UI
```

## 14. 关键协作关系总结

## 14.1 编译期协作

- **Electron TS 编译** 产出主进程代码
- **Next.js build** 产出前端资源
- **PyInstaller** 产出 FastAPI 二进制
- **electron-builder** 把上述内容和资源打包成桌面应用
- **Docker build** 则是将系统依赖、Node、Python、Next.js 构建产物、FastAPI 源码封装到镜像中

## 14.2 运行期协作

- **Electron 或 Node 启动器** 负责拉起各个子服务
- **Next.js** 提供用户界面
- **FastAPI** 提供业务 API、数据库访问、导出和生成逻辑
- **数据库 + 文件系统** 提供持久化
- **LibreOffice / Chromium / ImageMagick / Ollama** 提供外部能力支撑

## 15. 你可以如何理解这个项目

如果用一句话总结：

> Presenton 是一个以 FastAPI 为业务核心、以 Next.js 为交互前端、由 Electron 或 Docker 提供运行宿主的多进程 AI 幻灯片生成系统。

如果用架构角色来理解：

- **Electron / start.js**：进程编排层
- **Next.js**：交互与编辑层
- **FastAPI**：业务与生成核心层
- **DB + 文件系统**：持久化层
- **LibreOffice / Chromium / Ollama / ImageMagick**：能力扩展层

## 16. 最值得关注的工程特点

### 优点

- 桌面与 Web 共用大部分业务逻辑
- 前后端职责相对清晰
- 打包链比较完整
- 同时支持源码运行与二进制分发
- 本地化 / 自托管能力很强

### 复杂点

- 构建链路多，维护成本高
- Electron 生产态与开发态行为差异较大
- Docker 与 Electron 的 FastAPI 交付形态不同
- 导出链依赖多个外部系统工具，环境兼容性要求高
- 模板系统同时有源码模板与数据库模板，理解成本较高

## 17. 建议后续继续深入的方向

如果你后面还想继续深挖，最值得继续看的几个点是：

- **导出链路全流程**：从前端点击导出到 PPTX/PDF 文件生成
- **模板渲染链路**：默认模板和自定义模板在前端/后端如何被解析和使用
- **LLM 调用链**：Prompt、结构化输出、工具调用、图片生成如何串联
- **桌面依赖检查链**：LibreOffice / Chromium / ImageMagick 缺失时如何引导安装
- **生产构建产物目录结构**：`electron/resources` 里最终实际包含哪些东西

---

如果你愿意，我下一步可以继续帮你补一版：

- **“按时序展开的编译期流程图”**
- 或 **“运行时进程图 + 调用链图”**

这样你读源码时会更快。
