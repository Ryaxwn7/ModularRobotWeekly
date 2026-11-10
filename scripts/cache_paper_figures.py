"""Cache approved paper-figure URLs as validated local site assets.

The website deliberately never renders remote figure URLs.  This tool makes a
best-effort local copy only when the response is a supported raster image; any
failed, non-image, or oversized download simply remains absent from the site.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import urllib.request
from pathlib import Path
from typing import Any


MAX_BYTES = 8 * 1024 * 1024
MIME_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def supported_image(data: bytes, mime_type: str) -> str:
    mime_type = mime_type.split(";", 1)[0].lower().strip()
    if mime_type in MIME_EXTENSIONS:
        return MIME_EXTENSIONS[mime_type]
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ""


def cache_figure(url: str, destination: Path) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "DailyResearchAgent/0.1"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
        extension = supported_image(data, response.headers.get_content_type())
    if not extension or len(data) > MAX_BYTES:
        return ""
    target = destination.with_suffix(extension)
    target.write_bytes(data)
    return target.name


def cache_figures(data_path: Path, assets_dir: Path) -> tuple[int, int]:
    data: dict[str, Any] = json.loads(data_path.read_text(encoding="utf-8"))
    assets_dir.mkdir(parents=True, exist_ok=True)
    cached = 0
    missing = 0
    for paper in data.get("papers", []):
        url = str(paper.get("figure_url") or "")
        if not url or url.startswith("./assets/papers/"):
            continue
        digest = hashlib.sha256(str(paper.get("id") or paper.get("title") or url).encode()).hexdigest()[:20]
        try:
            filename = cache_figure(url, assets_dir / digest)
        except Exception:
            filename = ""
        if filename:
            paper["figure_url"] = f"./assets/papers/{filename}"
            cached += 1
        else:
            paper["figure_url"] = ""
            missing += 1
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cached, missing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="site/data/papers.json")
    parser.add_argument("--assets", default="site/assets/papers")
    args = parser.parse_args()
    cached, missing = cache_figures(Path(args.data), Path(args.assets))
    print(f"Cached figures: {cached}; unavailable figures hidden: {missing}")


if __name__ == "__main__":
    main()
