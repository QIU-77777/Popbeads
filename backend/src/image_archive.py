# -*- coding: utf-8 -*-
"""AI 图片存档模块 — 将每次 AI 编辑的元数据持久化到 SQLite。

设计:
  - 只保存 URL 到数据库，不下载图片到本地
  - 元数据（prompt、时间、源 URL）写入 ai_images.db (SQLite)
  - 对外暴露:
      archive_ai_image(edited_url, prompt, original_filename) → int  (record id)
      list_history(limit, offset) → list[dict]
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── 存储根目录：backend/ 同级的 ai_images/（即项目根目录下）
_BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
_PROJECT_ROOT = _BACKEND_DIR.parent  # 项目根
DB_PATH = _PROJECT_ROOT / "ai_images" / "ai_images.db"


def _ensure_storage() -> None:
    """确保 SQLite 数据库存在，执行建表 DDL（幂等）。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        # 目标列顺序：id, session_id, original_name, model, prompt, source_url, created_at
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_images (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT    NOT NULL DEFAULT '',
                original_name   TEXT             DEFAULT '',
                model           TEXT    NOT NULL DEFAULT '',
                prompt          TEXT    NOT NULL,
                source_url      TEXT    NOT NULL,
                created_at      TEXT    NOT NULL
            )
        """)

        # 兼容迁移：检查现有列，若列顺序/结构与目标不符则重建表
        rows = conn.execute("PRAGMA table_info(ai_images)").fetchall()
        existing_cols = [row[1] for row in rows]  # 保留顺序

        target_cols = [
            "id",
            "session_id",
            "original_name",
            "model",
            "prompt",
            "source_url",
            "created_at",
        ]
        needs_rebuild = existing_cols != target_cols

        if needs_rebuild:
            # 确保所有目标列都存在（用 ALTER TABLE 补缺失列，再重建排序）
            existing_set = set(existing_cols)
            for col, definition in [
                ("session_id", "TEXT NOT NULL DEFAULT ''"),
                ("original_name", "TEXT DEFAULT ''"),
                ("model", "TEXT NOT NULL DEFAULT ''"),
            ]:
                if col not in existing_set:
                    conn.execute(f"ALTER TABLE ai_images ADD COLUMN {col} {definition}")

            # 重建表以统一列顺序
            conn.execute("""
                CREATE TABLE ai_images_new (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id      TEXT    NOT NULL DEFAULT '',
                    original_name   TEXT             DEFAULT '',
                    model           TEXT    NOT NULL DEFAULT '',
                    prompt          TEXT    NOT NULL,
                    source_url      TEXT    NOT NULL,
                    created_at      TEXT    NOT NULL
                )
            """)
            conn.execute("""
                INSERT INTO ai_images_new
                    (id, session_id, original_name, model, prompt, source_url, created_at)
                SELECT
                    id,
                    COALESCE(session_id, ''),
                    COALESCE(original_name, ''),
                    COALESCE(model, ''),
                    prompt,
                    source_url,
                    created_at
                FROM ai_images
            """)
            conn.execute("DROP TABLE ai_images")
            conn.execute("ALTER TABLE ai_images_new RENAME TO ai_images")

        conn.commit()


def archive_ai_image(
    edited_url: str,
    prompt: str,
    original_filename: Optional[str] = None,
    model: Optional[str] = None,
    session_id: Optional[str] = None,
) -> int:
    """将 AI 编辑结果写入 SQLite，返回新记录 id。

    Args:
        edited_url:        AI API 返回的图片 URL
        prompt:            用户输入的提示词
        original_filename: 原始上传文件名（可选，仅用于记录）
        model:             生图所用的模型名称（可选）
        session_id:        前端浏览器唯一会话 ID（可选，用于区分不同用户）

    Returns:
        新插入记录的 id
    """
    _ensure_storage()
    now = datetime.now().isoformat(timespec="seconds")

    record_id = 0
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO ai_images (session_id, original_name, model, prompt, source_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id or "",
                original_filename or "",
                model or "",
                prompt,
                edited_url,
                now,
            ),
        )
        conn.commit()
        record_id = int(cursor.lastrowid or 0)

    logger.info('存档记录写入 SQLite, | record_id=%d | 查看请输入[sqlite3 ai_images/ai_images.db "SELECT * FROM ai_images;"]', record_id)
    return record_id


def list_history(limit: int = 50, offset: int = 0) -> list[dict[str, object]]:
    """查询 AI 图片历史记录，按时间倒序返回。

    Args:
        limit:  最多返回条数（默认 50）
        offset: 翻页偏移量

    Returns:
        list of dict，每条包含: id, session_id, original_name, model, prompt, source_url, created_at
    """
    _ensure_storage()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, session_id, original_name, model, prompt, source_url, created_at
            FROM ai_images
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return [dict(r) for r in rows]
