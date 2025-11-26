from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def load_sent_urls(path: Path) -> Dict[str, str]:
    """保存済みURLを読み込む。"""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        logger.warning("Failed to decode JSON at %s; starting fresh", path)
        return {}
    except OSError as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return {}

    if not isinstance(data, dict):
        logger.warning("Unexpected JSON format at %s; expected object, got %s", path, type(data))
        return {}

    return {str(url): str(ts) for url, ts in data.items()}


def save_sent_urls(urls: Dict[str, str], path: Path) -> None:
    """URLの辞書をJSONとして保存する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(urls, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)
    except OSError as exc:
        logger.error("Failed to write %s: %s", path, exc)
