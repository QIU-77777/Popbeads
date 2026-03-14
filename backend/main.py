from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import os
import sys
import tempfile
import logging
import traceback
import base64
from pathlib import Path

from dotenv import load_dotenv
from src.api import (
    ConvertRequest,
    PipelineOptions,
    RenderOptions,
    generate_svg_in_memory,
    ParameterValidationError,
    DependencyMissingError,
)
from src.core import PaletteMethod, ResizeMode
from src.image_edit import generate_edited_image
from src.image_archive import archive_ai_image, list_history

# 加载项目根目录的 .env 文件（backend/ 的上一级）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── 日志配置：输出到终端和 backend/pingdou.log ──
_LOG_FILE = Path(__file__).resolve().parent / "pingdou.log"
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 避免重复添加 handler
if not root_logger.handlers:
    formatter = logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
    # 终端 handler
    terminal_handler = logging.StreamHandler()
    terminal_handler.setFormatter(formatter)
    root_logger.addHandler(terminal_handler)
    # 文件 handler
    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

# watchfiles 热重载日志只输出到终端，不写入文件
logging.getLogger("watchfiles").setLevel(logging.WARNING)

# 确保所有子 logger 都传播到 root handler
logging.getLogger("src").propagate = True

logger = logging.getLogger(__name__)

# Ensure src module is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(title="Pingdou API", description="API for Pingdou Pixel Art Generator")

# Configure CORS for Next.js frontend
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://10.0.0.39:3000",
]
# Allow adding production origins via environment variable, e.g.
#   CORS_ORIGINS=https://your-app.vercel.app,https://custom-domain.com
_extra = os.environ.get("CORS_ORIGINS", "")
if _extra:
    _cors_origins.extend([o.strip() for o in _extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "message": "Pingdou API is running",
    }


def _format_stats_payload(color_stats, table_data):
    total_beads = sum(color_stats.values())
    color_table = [
        {
            "code": row[0],
            "name": row[1],
            "count": int(row[2]),
            "percentage": float(row[3]),
            "rgb": row[4],
            "hex": row[5],
        }
        for row in table_data
    ]
    return {
        "total_beads": total_beads,
        "unique_colors": len(color_stats),
        "color_table": color_table,
    }


@app.post("/api/generate")
async def generate_pattern(
    file: UploadFile = File(...),
    # Grid options
    size_mode: str = Form("rows"),
    size_value: int = Form(40),
    # Pipeline options
    quantization_method: PaletteMethod = Form("lab"),
    dithering: bool = Form(False),
    resize_mode: ResizeMode = Form("fit"),
    max_colors: int = Form(0),
    merge_threshold: float = Form(0),
    pixel_style: bool = Form(False),
    grayscale: bool = Form(False),
    # Render options
    show_grid: bool = Form(False),
    show_labels: bool = Form(True),
    show_color_codes: bool = Form(True),
):
    temp_path = None
    try:
        # Create a temporary file to save the uploaded image
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_path = tmp_file.name

        # Parse grid size
        rows, cols = None, None
        if size_mode == "rows":
            rows = size_value
        else:
            cols = size_value

        # Parse max colors
        mc = max_colors if max_colors > 0 else None

        # Create request object
        request = ConvertRequest(
            image_path=temp_path,
            rows=rows,
            cols=cols,
            pipeline=PipelineOptions(
                quantization_method=quantization_method,
                dithering=dithering,
                resize_mode=resize_mode,
                max_colors=mc,
                merge_threshold=merge_threshold,
                grayscale=grayscale,
            ),
            render=RenderOptions(
                cell_size=None,
                show_grid=show_grid,
                show_labels=show_labels,
                show_color_codes=show_color_codes,
                round_beads=pixel_style,
            ),
        )

        # Generate SVG pattern in memory
        svg_str, color_stats, table_data = generate_svg_in_memory(request)

        formatted_stats = _format_stats_payload(color_stats, table_data)

        return JSONResponse(
            content={"status": "success", "svg": svg_str, "stats": formatted_stats}
        )

    except ParameterValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DependencyMissingError as e:
        raise HTTPException(status_code=500, detail=f"Missing dependency: {str(e)}")
    except Exception as e:
        logger.error("generate_pattern failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


# 提供一个接口，接受 SVG 内容并返回 PDF 文件，供用户下载。后续可以增加参数支持调整 PDF 质量或尺寸。
@app.post("/api/export/pdf")
async def export_pdf(request: Request):
    """Convert SVG content to PDF for download."""
    try:
        svg_bytes = await request.body()
        if not svg_bytes:
            raise HTTPException(status_code=400, detail="No SVG content provided")

        # Try cairosvg first, fall back to reportlab
        try:
            import cairosvg

            pdf_bytes = cairosvg.svg2pdf(bytestring=svg_bytes)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=pingdou.pdf"},
            )
        except ImportError:
            pass

        # Fallback: render SVG → PNG → PDF via Pillow
        try:
            import cairosvg as _cs

            png_bytes = _cs.svg2png(bytestring=svg_bytes, dpi=150)
        except ImportError:
            # Last resort: use the built-in SVG-to-PNG via Pillow + svglib
            try:
                from svglib.svglib import svg2rlg  # type: ignore[import]
                from reportlab.graphics import renderPDF
                from io import BytesIO

                drawing = svg2rlg(BytesIO(svg_bytes))
                if drawing is None:
                    raise ValueError("Could not parse SVG")
                buf = BytesIO()
                renderPDF.drawToFile(drawing, buf, fmt="PDF")
                buf.seek(0)
                return Response(
                    content=buf.read(),
                    media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=pingdou.pdf"},
                )
            except ImportError:
                raise HTTPException(
                    status_code=501,
                    detail="PDF export requires 'cairosvg' or 'svglib+reportlab'. Install one: pip install cairosvg  OR  pip install svglib reportlab",
                )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


@app.post("/api/image/edit")
async def ai_image_edit(
    request: Request,
    file: UploadFile = File(...),
    prompt: str = Form(...),
):
    """接收用户上传的图片和提示词，调用 AI 模型进行图片编辑。

    流程: 读取上传文件 → base64 data URI → 调用 nano-banana-2 API → 返回编辑后图片 URL。
    前端拿到 URL 后可展示预览，或直接用该 URL 继续生成拼豆图纸。
    Header: X-Session-ID — 前端浏览器唯一会话 ID，用于在 DB 中区分不同用户。
    """
    session_id = request.headers.get("X-Session-ID", "")
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="上传文件为空")

        # 根据文件类型构建 data URI（API 支持 base64 data URI 作为 image_urls）
        ext = os.path.splitext(file.filename or "img.png")[1].lower().lstrip(".")
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/png")
        b64_str = base64.b64encode(content).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_str}"

        # 调用 AI 编辑 API
        edited_url = generate_edited_image(prompt=prompt, image_url=data_uri)

        # 后端下载生成图片，转为 base64 dataUrl 返回给前端
        # 避免前端跨域 fetch 外部图片 URL（CORS 限制）
        edited_data_url: str | None = None
        try:
            import requests as _req

            img_resp = _req.get(edited_url, timeout=60)
            img_resp.raise_for_status()
            img_bytes = img_resp.content
            img_mime = img_resp.headers.get("content-type", "image/png").split(";")[0]
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")
            edited_data_url = f"data:{img_mime};base64,{img_b64}"
        except Exception as dl_err:
            logger.warning("后端下载生成图片失败，前端将使用 URL: %s", dl_err)

        # 异步存档：写入 SQLite（失败不影响主流程）
        try:
            record_id = archive_ai_image(
                edited_url=edited_url,
                prompt=prompt,
                original_filename=file.filename or "upload",
                model=os.environ.get("IMAGE_EDIT_MODEL", ""),
                session_id=session_id,
            )
        except Exception as archive_err:
            logger.warning("AI 图片存档失败（不影响正常响应）: %s", archive_err)

        return JSONResponse(
            content={
                "status": "success",
                "edited_image_url": edited_url,
                "edited_image_data": edited_data_url,  # base64 dataUrl，前端优先用这个
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ai_image_edit failed: %s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"AI 图片编辑失败: {str(e)}")


@app.get("/api/image/history")
async def get_image_history(limit: int = 50, offset: int = 0):
    """查询 AI 图片生成历史记录，按时间倒序返回。

    Query params:
        limit:  每页条数（默认 50，最大 200）
        offset: 翻页偏移量（默认 0）

    Response:
        {
            "status": "success",
            "total": <int>,
            "items": [ { id, created_at, prompt, original_name, local_filename, source_url }, ... ]
        }
    """
    try:
        limit = min(max(1, limit), 200)
        items = list_history(limit=limit, offset=offset)
        return JSONResponse(
            content={"status": "success", "total": len(items), "items": items}
        )
    except Exception as e:
        logger.error("get_image_history failed: %s", e)
        raise HTTPException(status_code=500, detail=f"查询历史记录失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
