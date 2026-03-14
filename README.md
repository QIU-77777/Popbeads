<div align="center">

# Popbeads

**将任意图片转换为拼豆手工图纸的开源工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg?logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

上传 JPG / PNG / WEBP 图片 →（可选）AI 风格化编辑 → 自动匹配 221 种 Mard 官方拼豆色 → 生成带色号标注的 SVG 矢量图纸 + 颜色用量统计

[快速开始](#-快速开始) · [功能特性](#-功能特性) · [AI 图片编辑](#-ai-图片编辑) · [API 文档](#-api-文档) · [项目结构](#-项目结构) · [部署](#-部署) · [贡献指南](#-贡献)

</div>

---

## 📸 截图

![Popbeads Web 界面](web_screenshot.png)

## ✨ 功能特性

### 核心能力

| 功能                   | 说明                                                                     |
| ---------------------- | ------------------------------------------------------------------------ |
| 🎨 **Lab 感知色彩匹配** | 基于 CIE Lab 色彩空间计算感知距离，比 RGB 欧氏距离更贴合人眼             |
| 🔢 **221 色官方色卡**   | 内置 Mard 拼豆全系列色卡（A–M 系），支持按套装筛选（24/36/48/72/120 色） |
| 📐 **自动比例计算**     | 指定行数或列数，另一维按原图比例自动推算                                 |
| 🖼️ **SVG 矢量输出**     | 图纸为无损矢量格式，支持无限缩放，适合打印                               |
| 📊 **颜色用量统计**     | 每种颜色的色号、名称、用量、占比一目了然                                 |
| 📱 **响应式设计**       | 桌面端三栏布局 + 独立移动端界面，自动适配                                |

### 高级功能

- **Floyd-Steinberg 抖动** — 渐变过渡更自然
- **单色（灰度）模式** — ITU-R BT.601 标准灰度转换
- **智能调色板缩减** — K-Means 聚类分析主色调，自动筛选最相关的拼豆色子集
- **合并相似颜色** — 量化后将 ΔE 接近的颜色合并，减少零星颜色种类，简化采购
- **像素风格化** — Canny 边缘检测 + HSL 自适应描边，照片呈现像素画风格
- **多格式导出** — SVG / PNG / JPG / PDF 一键下载
- **颜色高亮** — 点击统计面板中的颜色，图纸上对应色块高亮显示

### 🤖 AI 图片编辑（新功能）

- **AI 风格化** — 上传图片后可输入提示词，调用 AI 模型对图片进行风格化编辑（如：转换为像素艺术风格、卡通风格等）
- **一键覆盖** — AI 生成结果自动替换原图，直接用于后续图纸生成，无需手动重新上传
- **生成记录存档** — 每次 AI 生成的提示词、模型、原文件名、结果 URL 自动写入本地 SQLite 数据库（`ai_images/ai_images.db`）
- **用户隔离** — 浏览器自动生成唯一 Session ID（存于 localStorage），写入 DB 便于区分多用户
- **图片悬浮预览** — 桌面端鼠标悬浮图片时在右侧弹出放大预览；移动端点击图片全屏预览

## 🛠️ 技术栈

| 层       | 技术                                                                         |
| -------- | ---------------------------------------------------------------------------- |
| **前端** | Next.js 16 · React 19 · Tailwind CSS v4 · shadcn/ui · Radix UI               |
| **后端** | FastAPI · Uvicorn · Pillow · NumPy · OpenCV · requests                       |
| **存储** | SQLite（AI 生成记录）· IndexedDB（前端图片缓存）· localStorage（参数持久化） |
| **语言** | TypeScript · Python 3.10+                                                    |

## 🚀 快速开始

### 前置要求

- **Python** 3.10+（推荐 3.12）
- **Node.js** 18+
- **npm** 或 **pnpm**

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/popbeads.git
cd popbeads
```

### 2. 配置环境变量（可选，AI 编辑功能需要）

复制 `.env.example` 为 `.env` 并填入配置：

```bash
cp .env.example .env
```

```env
# AI 图片编辑 API 配置（不配置则 AI 编辑功能不可用）
IMAGE_EDIT_API_KEY=your_api_key_here
IMAGE_EDIT_BASE_URL=https://image.onerouter.pro/v1/images/edits
IMAGE_EDIT_MODEL=google/nano-banana-image-to-image
```

### 3. 启动后端

```bash
cd backend
pip install -r ../requirements.txt
python main.py
```

后端启动在 `http://localhost:8000`，可通过 `GET /api/health` 验证。
运行日志同时写入终端和 `backend/pingdou.log`。

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:3000` 即可使用。

### 5.（可选）安装额外依赖

```bash
# PDF 导出支持（二选一）
pip install cairosvg
# 或
pip install svglib reportlab
```

### 依赖文件一览

| 文件                        | 用途                                                     |
| --------------------------- | -------------------------------------------------------- |
| `requirements.txt`          | 后端核心依赖（FastAPI、Pillow、NumPy、OpenCV、requests） |
| `requirements-optional.txt` | 可选依赖（cairosvg、svglib、reportlab，PDF 导出用）      |
| `requirements-dev.txt`      | 开发与测试依赖                                           |
| `frontend/package.json`     | 前端依赖                                                 |

## 📖 使用方式

### Web 界面（推荐）

1. 启动前后端服务
2. 浏览器打开 `http://localhost:3000`
3. 拖拽或点击上传图片
4. **（可选）开启 AI 编辑** — 输入提示词，点击「AI 生成」，等待结果自动覆盖原图
5. 左侧面板调整参数（网格尺寸、配色数量、颜色匹配方式、抖动等）
6. 点击「生成拼豆图纸」
7. 右侧预览结果，导出所需格式

### cURL 调用

```bash
curl -X POST http://localhost:8000/api/generate \
  -F "file=@photo.png" \
  -F "size_mode=rows" \
  -F "size_value=50" \
  -F "quantization_method=lab" \
  -F "dithering=false" \
  -F "max_colors=36"
```

### Python SDK

```python
from src.api import ConvertRequest, PipelineOptions, RenderOptions, generate_svg_in_memory

request = ConvertRequest(
    image_path="photo.jpg",
    rows=50,
    pipeline=PipelineOptions(quantization_method="lab", dithering=True),
    render=RenderOptions(round_beads=True),
)
svg_str, color_stats, table_data = generate_svg_in_memory(request)
```

## ⚙️ API 文档

后端启动后，访问 `http://localhost:8000/docs` 查看 Swagger 交互式文档。

### `POST /api/generate`

生成拼豆图纸，返回 SVG 字符串和颜色统计。

| 参数                  | 类型   | 默认值   | 说明                               |
| --------------------- | ------ | -------- | ---------------------------------- |
| `file`                | File   | **必填** | 图片文件（JPG / PNG / WEBP）       |
| `size_mode`           | string | `"rows"` | `rows` 按行数 / `cols` 按列数      |
| `size_value`          | int    | `40`     | 行数或列数                         |
| `quantization_method` | string | `"lab"`  | 色彩匹配：`lab`（推荐）/ `rgb`     |
| `dithering`           | bool   | `false`  | Floyd-Steinberg 抖动               |
| `max_colors`          | int    | `0`      | 最大颜色数（0 = 不限）             |
| `merge_threshold`     | float  | `0`      | 合并相似色阈值（0 = 不合并，1~30） |
| `pixel_style`         | bool   | `false`  | 圆形珠子样式                       |
| `grayscale`           | bool   | `false`  | 单色灰度模式                       |
| `show_grid`           | bool   | `false`  | 显示网格线                         |
| `show_labels`         | bool   | `true`   | 显示行列标签                       |
| `show_color_codes`    | bool   | `true`   | 格子内显示色号                     |

**响应：**

```json
{
  "status": "success",
  "svg": "<svg ...>...</svg>",
  "stats": {
    "total_beads": 3072,
    "unique_colors": 27,
    "color_table": [
      { "code": "B23", "name": "橄榄绿", "count": 1011, "percentage": 32.91, "rgb": [78, 83, 42], "hex": "#4E532A" }
    ]
  }
}
```

### `POST /api/image/edit`

调用 AI 模型对图片进行风格化编辑。

| 参数 / Header  | 类型   | 说明                                          |
| -------------- | ------ | --------------------------------------------- |
| `file`         | File   | 原始图片（JPG / PNG / WEBP）                  |
| `prompt`       | string | 编辑提示词（如"转换为像素艺术风格"）          |
| `X-Session-ID` | Header | 浏览器唯一会话 ID，用于 DB 中区分用户（可选） |

**响应：**

```json
{
  "status": "success",
  "edited_image_url": "https://...",
  "edited_image_data": "data:image/png;base64,..."
}
```

> `edited_image_data` 为后端预下载的 base64 dataURL，前端优先使用，避免 CORS 问题。

### `GET /api/image/history`

查询 AI 图片生成历史记录，按时间倒序返回。

| Query Param | 类型 | 默认值 | 说明       |
| ----------- | ---- | ------ | ---------- |
| `limit`     | int  | `50`   | 每页条数   |
| `offset`    | int  | `0`    | 翻页偏移量 |

### `POST /api/export/pdf`

将 SVG 转换为 PDF。请求体为 SVG 字符串，`Content-Type: image/svg+xml`。

### `GET /api/health`

健康检查，返回 `{"status": "ok"}`。

## 📁 项目结构

```
popbeads/
├── .env                           # 环境变量（本地，不提交 git）
├── .env.example                   # 环境变量模板
├── backend/
│   ├── main.py                    # FastAPI 入口（路由、CORS、日志配置）
│   ├── pingdou.log                # 运行日志文件（自动生成）
│   └── src/
│       ├── api.py                 # 编排层：参数校验 → 管线调度 → SVG 生成
│       ├── core.py                # 类型别名、调色板缓存、rgb_to_lab
│       ├── palette.py             # 221 色 Mard 官方色卡定义
│       ├── color.py               # Lab/RGB 最近色匹配 + Floyd-Steinberg 抖动
│       ├── palette_reduction.py   # K-Means 聚类 → 调色板子集筛选
│       ├── color_merge.py         # 后量化颜色合并（ΔE 阈值 + Union-Find）
│       ├── image_processing.py    # 归一化、网格缩放、邻域平滑
│       ├── render_svg.py          # SVG 矢量图纸渲染
│       ├── render.py              # PNG 位图图纸渲染
│       ├── stats.py               # 颜色用量统计
│       ├── pixelart.py            # Canny 边缘检测 + HSL 描边
│       ├── image_edit.py          # AI 图片编辑（调用外部 API）
│       └── image_archive.py       # AI 生成记录存档（SQLite）
├── ai_images/
│   └── ai_images.db               # AI 生成记录数据库（自动生成）
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # 桌面端主页面（三栏布局 + AI 编辑 + 悬浮预览）
│   │   │   ├── mobile-page.tsx    # 移动端页面（单栏 + 点击放大预览）
│   │   │   ├── layout.tsx         # 根布局
│   │   │   └── globals.css        # 全局样式 + Tailwind 主题
│   │   ├── components/ui/         # shadcn/ui 组件
│   │   └── lib/
│   │       ├── constants.ts       # API 地址 + Logo 路径
│   │       ├── use-media-query.ts # SSR 安全的响应式 Hook
│   │       └── use-persistence.ts # localStorage / IndexedDB / Session ID 工具
│   ├── package.json
│   └── next.config.ts
├── requirements.txt
├── requirements-optional.txt
├── requirements-dev.txt
├── pytest.ini
└── LICENSE
```

### 处理管线

```
原图 → [AI 风格化编辑（可选）] → 归一化(1500px) → 缩放到网格尺寸 → [灰度转换] → [调色板缩减] → Lab/RGB 量化 → [抖动] → [合并相似色] → SVG 渲染
```

## 🎨 内置色卡

内置 **221 种** Mard 拼豆官方颜色，覆盖 9 个系列：

| 系列 | 色号范围 | 数量 | 色系             |
| ---- | -------- | ---- | ---------------- |
| A    | A1 – A26 | 26   | 黄色、橙色、米色 |
| B    | B1 – B32 | 32   | 绿色、黄绿、墨绿 |
| C    | C1 – C29 | 29   | 蓝色、青色、天蓝 |
| D    | D1 – D26 | 26   | 紫色、蓝紫、深紫 |
| E    | E1 – E24 | 24   | 粉色、玫红、肤粉 |
| F    | F1 – F25 | 25   | 红色、深红、珊瑚 |
| G    | G1 – G21 | 21   | 棕色、肤色、咖啡 |
| H    | H1 – H23 | 23   | 黑白灰、中性色   |
| M    | M1 – M15 | 15   | 莫兰迪色、灰调色 |

支持按套装筛选：全部 221 色 / 120 色（大套装）/ 72 色（标准套装）/ 48 色（入门套装）/ 36 色（基础套装）/ 24 色（迷你套装）。

## 🚢 部署

### 环境变量

| 变量                   | 默认值                                        | 说明                              |
| ---------------------- | --------------------------------------------- | --------------------------------- |
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000`                       | 后端 API 地址（前端构建时注入）   |
| `IMAGE_EDIT_API_KEY`   | —                                             | AI 编辑 API 密钥（必填，启用 AI） |
| `IMAGE_EDIT_BASE_URL`  | `https://image.onerouter.pro/v1/images/edits` | AI 编辑 API 端点                  |
| `IMAGE_EDIT_MODEL`     | `google/nano-banana-image-to-image`           | AI 编辑模型名称                   |

### 生产构建

```bash
# 前端
cd frontend
NEXT_PUBLIC_API_BASE=https://your-api.example.com npm run build
npm start

# 后端（去掉 reload，多 worker）
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker（推荐）

> *TODO: 添加 Dockerfile 和 docker-compose.yml*

## 🧪 测试

```bash
cd backend
python -m pytest test -q
```

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. **Fork** 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "feat: add your feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 **Pull Request**

### 开发环境

```bash
# 安装所有开发依赖
pip install -r requirements-dev.txt
cd frontend && npm install
```

### Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `style:` 格式（不影响逻辑）
- `refactor:` 重构
- `test:` 测试
- `chore:` 构建/工具

## ❓ FAQ

<details>
<summary><strong>转换后颜色和原图差异较大？</strong></summary>

拼豆颜色有限（221 种），色彩量化会将所有颜色映射到最接近的拼豆色，这是正常现象。使用 Lab 模式可减小色差。

</details>

<details>
<summary><strong>不想安装 OpenCV？</strong></summary>

将量化方式设为 `rgb` 即可，仅需 Pillow 和 NumPy，但匹配精度会降低。

</details>

<details>
<summary><strong>PDF 导出报错？</strong></summary>

需安装 `cairosvg` 或 `svglib + reportlab`，参见[可选依赖](#5可选安装额外依赖)。若均未安装，系统会回退到浏览器打印。

</details>

<details>
<summary><strong>如何知道需要采购哪些颜色和数量？</strong></summary>

生成图纸后，颜色统计面板会显示每种颜色的色号、名称和用量。也可导出后在 SVG 文件中查看。

</details>

<details>
<summary><strong>智能调色板缩减是什么？</strong></summary>

设置最大颜色数后，系统用 K-Means 聚类分析图片主色调，从 221 色中筛选最相关的 N 种拼豆色。适合采购预算有限的场景。

</details>

<details>
<summary><strong>「合并相似色」和「配色数量」有什么区别？</strong></summary>

「配色数量」在量化**前**限定可用调色板范围（如只用 36 色套装）；「合并相似色」在量化**后**将结果中色差小于阈值的颜色合并为一种，减少零星颜色。两者可叠加使用。

</details>

<details>
<summary><strong>AI 编辑功能如何配置？</strong></summary>

在项目根目录创建 `.env` 文件（参考 `.env.example`），填入 `IMAGE_EDIT_API_KEY`、`IMAGE_EDIT_BASE_URL`、`IMAGE_EDIT_MODEL` 三个环境变量后重启后端即可。AI 编辑记录会自动保存到 `ai_images/ai_images.db`，可用以下命令查看：

```bash
sqlite3 ai_images/ai_images.db "SELECT * FROM ai_images;"
```

</details>

## 📄 许可证

[MIT License](LICENSE) © 2026 Popbeads Contributors
