# Presenton Docker 精简重构计划

## 当前镜像分析

官方 Dockerfile 中包含以下组件，按体积从大到小排列：

| 组件 | 估算体积 | 用途 | 是否必需 |
|------|---------|------|---------|
| **docling** + PyTorch CPU | ~2-3 GB | 文档解析（PDF/DOCX等） | ❓ 需确认 |
| **Ollama** | ~500 MB+ | 本地运行 LLM 模型 | ❌ 不需要（你用外部 LLM） |
| **LibreOffice** | ~400-500 MB | PPTX 转 PDF、生成幻灯片截图 | ✅ 核心功能 |
| **Chromium** | ~300-400 MB | Puppeteer 截图、PDF 导出 | ✅ 核心功能 |
| **chromadb** | ~200 MB | 图标搜索的向量数据库 | ✅ 用于图标查找 |
| **Node.js 20** | ~100 MB | Next.js 前端运行 | ✅ 必需 |
| **Nginx** | ~10 MB | 反向代理 | ✅ 必需（统一入口） |
| **Python 依赖** | ~100 MB | FastAPI 后端 | ✅ 必需 |

## 需要你确认的删减项

### 1. Ollama（强烈建议删除）
- **体积**：~500 MB+
- **你的情况**：你使用外部 LLM（host.docker.internal:8080），完全不需要容器内的 Ollama
- **影响**：删除后无法在容器内运行本地模型
- **建议**：✅ 删除

### 2. docling + PyTorch CPU（建议删除）
- **体积**：~2-3 GB（这是最大的一个！）
- **用途**：解析上传的 PDF/DOCX 等文档，提取内容用于生成 PPT
- **影响**：删除后无法上传 PDF/DOCX 文件作为素材来源
- **你需要这个功能吗？** 如果你只是手动输入主题或文本来生成 PPT，则不需要
- **建议**：❓ 请确认

### 3. Nginx（可选删除）
- **体积**：~10 MB（很小）
- **用途**：反向代理，统一 80 端口入口
- **影响**：删除后需要直接暴露 Next.js(3000) 和 FastAPI(8000) 端口
- **你的情况**：你已经在用 `-p 3000:80` 映射 nginx，但如果服务直接绑定 0.0.0.0，可以不需要 nginx
- **建议**：❓ 请确认（删除可以简化架构，但需要暴露两个端口）

### 4. MCP Server（可选删除）
- **体积**：代码很小，几乎不占空间
- **用途**：提供 MCP 协议接口，供 AI 工具调用
- **建议**：❓ 你需要 MCP 功能吗？

## 必须保留的组件

- **Python 3.11** - FastAPI 后端
- **Node.js 20** - Next.js 前端
- **LibreOffice** - PPTX 转 PDF 截图（核心功能）
- **Chromium** - Puppeteer 截图/PDF 导出（核心功能）
- **chromadb** - 图标搜索
- **FastAPI 依赖** - 后端 API
- **Next.js 应用** - 前端界面

## 代码修改计划

### 修改 1: Dockerfile（新建 Dockerfile.lite）
- 删除 Ollama 安装
- 删除 docling + PyTorch（如确认不需要）
- 删除 Nginx（如确认不需要）
- 优化层缓存，合并 RUN 命令
- 清理 apt 缓存

### 修改 2: start.js
- 删除 Ollama 启动逻辑
- 删除 Nginx 启动逻辑（如确认不需要）
- **Next.js 绑定 0.0.0.0**（替换 127.0.0.1）
- **FastAPI 绑定 0.0.0.0**（需同步修改 server.py）
- 添加 `DISABLE_IMAGE_GENERATION` 环境变量支持

### 修改 3: servers/fastapi/server.py
- host 从 `127.0.0.1` 改为 `0.0.0.0`

### 修改 4: nginx.conf（如保留 Nginx）
- 保持 `listen 80` 不变

## 预估效果

| 项目 | 官方镜像 | 精简后（保留 docling） | 精简后（去掉 docling） |
|------|---------|----------------------|----------------------|
| 镜像大小 | ~5-6 GB | ~4-5 GB | ~2-3 GB |
| 构建时间 | 很长 | 较长 | 较短 |

## Windows Docker Desktop 构建

Windows Docker Desktop **完全支持** `docker build`。构建命令：

```powershell
docker build -t presenton-lite:latest -f Dockerfile.lite .
```

## 最终决策

| 组件 | 决策 | 原因 |
|------|------|------|
| Ollama | ❌ 删除 | 使用外部 LLM |
| docling + PyTorch | ❌ 删除 | 不需要上传文档，只用文本输入 |
| MCP Server | ❌ 删除 | 只用 Web 界面 |
| Nginx | ✅ 保留 | 统一端口入口 |
| LibreOffice | ✅ 保留 | 核心功能 |
| Chromium | ✅ 保留 | 核心功能 |

额外修改：
- Next.js 和 FastAPI 都绑定到 **0.0.0.0**
- 添加 **DISABLE_IMAGE_GENERATION** 环境变量支持
- 预估精简后镜像大小：**~2-3 GB**（原 ~5-6 GB）

docker build -t presenton-lite:latest -f Dockerfile.lite .