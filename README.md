# EGC Research Assistant：高延性地聚合物复合材料研究智能助手

基于 RAG 问答、实时网络搜索和 ReAct Agent 三大核心技术，为 EGC（Engineered Geopolymer Composites）领域研究人员提供智能文献检索、力学性能预测、配比优化和实验数据查询一站式服务。

## 核心功能

### 1. 智能文献问答（RAG）
- 上传 PDF 论文，自动解析、分块、向量化并索引至 Elasticsearch
- 混合检索（BM25 + 向量相似度）+ DashScope Rerank 精排，确保检索精度
- 意图识别自动判断是否需要检索，通用问题直接由 LLM 回答

### 2. 实时网络搜索
- 集成 Serper API（Google 搜索），动态获取最新研究进展、行业动态
- 支持图片搜索、视频搜索和相关推荐问题
- 搜索结果经向量重排后注入回答上下文

### 3. Deep Research（智能 Agent）
- 基于 Plan-Execute-Reflect 模式的多步推理 Agent
- 自动规划并调度四大工具：学术论文检索、网络搜索、性能预测、文档分析
- 反思机制评估信息充分性，不足时自动补充检索
- 最终答案综合所有来源，附带文献引用

### 4. 力学性能预测
- 输入配合比参数（胶凝材料、纤维、养护条件等）
- 基于实验数据库相似配比 + 文献检索，由 LLM 预测六大力学指标
- 输出预测值、置信区间、应变硬化分析及参考文献

### 5. 配比优化
- 设定目标性能（抗压强度、极限拉伸应变等范围）
- 系统检索相似实验数据和文献，生成优化建议与推荐配合比
- 包含参数建议值、预期效果、权衡分析和完整推荐配比

### 6. 实验数据查询
- 结构化查询 EGC 实验数据库
- 支持按纤维类型、胶凝材料类型、力学性能范围等多维筛选
- 分页返回，便于浏览大规模实验数据

## 技术架构

| 层级 | 技术栈 |
|------|--------|
| 前端 | React + TypeScript + Vite + Ant Design + Valtio |
| 后端 | FastAPI + Python 3.11 + Uvicorn |
| 数据库 | PostgreSQL 15（结构化数据）+ Elasticsearch 8.11（向量检索）+ ChromaDB（网络搜索缓存） |
| LLM | DeepSeek-V4-Pro / Flash（通过阿里 DashScope 调用）、Qwen2.5-72B（意图分类） |
| 搜索 | Serper API（Google 搜索 / 图片 / 视频） |
| 文档处理 | DeepDoc（PDF 解析 + OCR + 版面识别） |

## 启动流程

本地开发推荐将 PostgreSQL 和 Elasticsearch 放在 Docker 中运行，FastAPI 与 Vite 在本地启动。这样无需每次重建后端镜像，调试和查看日志也更直接。

| 服务 | 默认地址 | 说明 |
|------|----------|------|
| 前端 | http://localhost:5181 | Vite 开发服务 |
| 后端 API 文档 | http://localhost:8000/docs | FastAPI Swagger UI |
| PostgreSQL | localhost:5432 | 结构化实验数据 |
| Elasticsearch | http://localhost:1200 | 文献与向量索引 |

### 1. 首次准备

安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)、Python 3.11 和 Node.js。编辑 `backend/.env`，至少填写：

```dotenv
DASHSCOPE_API_KEY="你的 DashScope API Key"
SERPER_API_KEY="你的 Serper API Key"
DATABASE_URL="postgresql://postgres:pg123456@localhost:5432/gsk"
ES_URL="http://localhost:1200"
```

请勿将真实 API Key 提交到代码仓库。

### 2. 日常启动：本地开发方式

在第一个终端启动数据库和检索服务：

```powershell
cd backend
docker compose -f docker-compose-base.yml up -d
docker ps
```

在第二个终端启动 FastAPI：

```powershell
cd backend\app
..\.venv\Scripts\python.exe app_main.py
```

看到 `Uvicorn running on http://0.0.0.0:8000` 表示后端就绪。

在第三个终端启动前端：

```powershell
cd frontend
npm run dev
```

浏览器访问 [http://localhost:5181](http://localhost:5181) 即可使用系统。

### 3. Windows 首次安装本地依赖

如果 `backend/.venv` 或 `frontend/node_modules` 尚不存在，先执行以下步骤。Windows 本地开发使用项目内置的 `datrie.py` 和 `chromadb.py` 兼容层，以避免安装 C++ 编译工具。

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
cd app
$deps = Get-Content .\requirements.txt | Where-Object { $_ -and ($_ -notmatch '^(datrie|chromadb)==') }
..\.venv\Scripts\python.exe -m pip install @deps -i https://pypi.tuna.tsinghua.edu.cn/simple

cd ..\..\frontend
npm install
```

### 4. Windows 后台启动辅助脚本

当前工作区已提供后台启动脚本。先按第 2 节启动基础容器，再在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\launch-backend-detached.ps1
powershell -ExecutionPolicy Bypass -File .\frontend\launch-frontend-detached.ps1
```

运行日志位置：

```text
backend/backend-dev.combined.log
frontend/frontend-dev.combined.log
```

受限制的终端可能不允许后台进程脱离当前会话；出现权限错误时，请在管理员 PowerShell 中执行脚本，或直接采用第 2 节的前台启动方式。

### 5. 全容器后端方式

需要将 PostgreSQL、Elasticsearch 与 FastAPI 全部放进 Docker 时执行：

```powershell
cd backend
docker compose up -d --build
```

该命令只启动后端及基础服务；前端仍需在 `frontend` 目录运行 `npm run dev`。如果构建过程中无法拉取 `python:3.11.7-slim` 镜像，请切换到第 2 节的本地开发方式。

### 6. 检查与停止

检查前后端是否可访问：

```powershell
Invoke-WebRequest http://localhost:8000/docs -UseBasicParsing
Invoke-WebRequest http://localhost:5181 -UseBasicParsing
```

前台启动的服务使用 `Ctrl+C` 停止。停止基础容器：

```powershell
cd backend
docker compose -f docker-compose-base.yml down
```

停止后台脚本启动的前后端进程：

```powershell
Get-NetTCPConnection -LocalPort 8000,5181 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  Stop-Process
```

### 7. 常见问题

- `Cannot find module`：进入 `frontend` 后重新执行 `npm install`。
- `Microsoft Visual C++ 14.0 or greater is required`：Windows 本地安装后端时使用第 3 节的依赖命令。
- `8000` 或 `5181` 端口被占用：用 `Get-NetTCPConnection -LocalPort 8000,5181` 查看占用进程后停止旧实例。
- Docker 镜像拉取超时：保持 PostgreSQL 和 Elasticsearch 已启动，改为本地运行 FastAPI。

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── app_main.py              # FastAPI 入口
│   │   ├── router/                  # API 路由
│   │   │   ├── ai_serarch_rt.py     # 问答 / Agent / 搜索
│   │   │   ├── egc_rt.py            # 性能预测 / 配比优化 / 实验数据
│   │   │   ├── history_rt.py        # 会话历史
│   │   │   └── user_rt.py           # 用户认证
│   │   ├── service/
│   │   │   ├── agent/               # ReAct Agent（规划-执行-反思）
│   │   │   ├── core/
│   │   │   │   ├── rag/             # RAG 检索管线
│   │   │   │   ├── web_search/      # 网络搜索
│   │   │   │   └── file_parse/      # 文档解析
│   │   │   └── egc/                 # EGC 领域服务
│   │   └── utils/
│   │       ├── prompt.py            # 通用提示词
│   │       └── egc_prompts.py       # EGC 领域提示词
│   ├── docker-compose.yml           # 全量 Docker 启动
│   ├── docker-compose-base.yml      # 基础服务（PG + ES）
│   └── .env                         # 环境变量配置
├── frontend/
│   ├── src/
│   │   ├── api/                     # API 请求层
│   │   ├── pages/                   # 页面组件（首页 / 对话 / 知识库）
│   │   ├── components/              # 通用组件
│   │   └── store/                   # Valtio 状态管理
│   ├── .env                         # 前端环境变量
│   └── vite.config.ts               # Vite 配置（含代理）
└── README.md
```
