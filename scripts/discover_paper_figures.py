"""Find article figures on official publisher pages and cache local previews."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

MAX_BYTES = 8 * 1024 * 1024
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RoboticsResearchWeekly/1.0)"}
VOID_TAGS = {"img", "meta", "link", "br", "hr", "input", "source", "wbr", "area", "base", "embed", "param", "track", "col"}


def supported_image(data: bytes, mime_type: str = "") -> str:
    """Require image file bytes and useful dimensions, not just a MIME header."""
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 33 and b"IEND" in data[-16:]:
        width, height = struct.unpack(">II", data[16:24])
        return ".png" if min(width, height) >= 120 else ""
    if data.startswith(b"\xff\xd8\xff") and data.rstrip().endswith(b"\xff\xd9"):
        offset = 2
        while offset + 9 < len(data):
            if data[offset] != 255:
                break
            marker = data[offset + 1]
            if marker == 255:
                offset += 1
                continue
            length = int.from_bytes(data[offset + 2:offset + 4], "big")
            if marker in {192, 193, 194, 195, 197, 198, 199, 201, 202, 203, 205, 206, 207}:
                height, width = struct.unpack(">HH", data[offset + 5:offset + 9])
                return ".jpg" if min(width, height) >= 120 else ""
            if length < 2:
                break
            offset += 2 + length
    return ""


def read_url(url: str, timeout: int, referer: str = "") -> tuple[bytes, str]:
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("response exceeds 8 MiB")
        return data, response.url


class FigureParser(HTMLParser):
    def __init__(self, page_url: str, doi: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.doi = doi.lower()
        self.stack: list[tuple[str, bool]] = []
        self.candidates: list[dict[str, Any]] = []
        self.declared_doi = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs)
        marker = " ".join(str(attrs.get(key) or "") for key in ("id", "class", "aria-describedby"))
        context = tag == "figure" or bool(re.search(r"(?:^|[ _-])fig(?:ure)?[ _-]?\d|article-section__figure|fig-group", marker, re.I))
        inside_figure = context or any(flag for _, flag in self.stack)
        if tag == "meta" and str(attrs.get("name") or "").lower() == "citation_doi":
            self.declared_doi = str(attrs.get("content") or "").lower().removeprefix("https://doi.org/")
        if tag == "img":
            source = attrs.get("data-src") or attrs.get("data-original") or attrs.get("src") or ""
            if not source or str(source).startswith("data:"):
                source = str(attrs.get("data-srcset") or attrs.get("srcset") or "").split(",")[0].strip().split(" ")[0]
            url = urllib.parse.urljoin(self.page_url, str(source))
            decoded = urllib.parse.unquote(url).lower()
            alt = str(attrs.get("alt") or "")
            signal = decoded + " " + marker.lower() + " " + alt.lower()
            figure_url = bool(re.search(r"fig(?:ure)?[._-]?0?\d|/figures/|gr\d+|/fig-", signal))
            unwanted = re.search(r"logo|advert|placeholder|tracking|banner|icon|cover-image", signal)
            wrong_article = "/art:" in decoded and bool(self.doi) and self.doi not in decoded
            if (inside_figure or figure_url) and not unwanted and not wrong_article and urllib.parse.urlparse(url).scheme == "https":
                score = 10 if re.search(r"fig(?:ure)?[._-]?0?1(?:\D|$)|gr1(?:\D|$)", signal) else 0
                if re.search(r"overview|architecture|platform|design|schematic|framework|structure|robot", alt, re.I):
                    score += 5
                self.candidates.append({"url": url, "alt": alt, "score": score})
        if tag not in VOID_TAGS:
            self.stack.append((tag, context))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def article_urls(paper: dict[str, Any]) -> list[str]:
    doi = str(paper.get("doi") or "").removeprefix("https://doi.org/")
    urls: list[str] = []
    if doi.startswith("10.1038/"):
        urls.append("https://www.nature.com/articles/" + doi.split("/", 1)[1])
    elif doi.startswith("10.1007/"):
        urls.append("https://link.springer.com/article/" + doi)
    elif doi.startswith("10.1371/"):
        urls.append("https://journals.plos.org/plosone/article?id=" + doi)
    if doi:
        urls.append("https://doi.org/" + doi)
    original = str(paper.get("url") or "")
    if "arxiv.org/abs/" in original:
        urls.insert(0, original.replace("/abs/", "/html/"))
    if original.startswith("https://"):
        urls.append(original)
    return list(dict.fromkeys(urls))


def discover_paper(paper: dict[str, Any], assets_dir: Path, timeout: int) -> dict[str, Any]:
    result: dict[str, Any] = {"id": paper.get("id"), "doi": paper.get("doi"), "title": paper.get("title"), "attempts": []}
    current = str(paper.get("figure_url") or "")
    if re.fullmatch(r"\./assets/papers/[a-zA-Z0-9._-]+", current):
        local = assets_dir / Path(current).name
        if local.is_file() and supported_image(local.read_bytes()):
            return {**result, "status": "cached_existing"}
    digest = hashlib.sha256(str(paper.get("id") or paper.get("title")).encode()).hexdigest()[:20]

    def download(candidate: dict[str, Any], page: str) -> bool:
        try:
            content, resolved = read_url(candidate["url"], timeout, page)
            extension = supported_image(content)
            if not extension:
                raise ValueError("not a valid supported figure, or image too small")
            target = assets_dir / (digest + extension)
            target.write_bytes(content)
            result.update(status="cached", figure_url="./assets/papers/" + target.name,
                          figure_source_url=resolved, figure_page_url=page,
                          figure_alt=candidate.get("alt") or "论文插图：" + str(paper.get("title")))
            return True
        except Exception as exc:
            result["attempts"].append({"url": candidate["url"], "error": type(exc).__name__ + ": " + str(exc)})
            return False

    if current.startswith("https://") and download({"url": current}, str(paper.get("url") or "")):
        return result
    for url in article_urls(paper):
        try:
            content, page = read_url(url, timeout)
            parser = FigureParser(page, str(paper.get("doi") or ""))
            parser.feed(content.decode("utf-8", errors="replace"))
            expected = str(paper.get("doi") or "").lower()
            if expected and parser.declared_doi and expected != parser.declared_doi:
                raise ValueError("publisher page DOI does not match paper")
            candidates = sorted(parser.candidates, key=lambda item: item["score"], reverse=True)
            seen: set[str] = set()
            for candidate in candidates:
                if candidate["url"] in seen:
                    continue
                seen.add(candidate["url"])
                if download(candidate, page):
                    return result
                if len(seen) >= 3:
                    break
            result["attempts"].append({"url": page, "error": "No downloadable article figure found in accessible HTML"})
        except Exception as exc:
            result["attempts"].append({"url": url, "error": type(exc).__name__ + ": " + str(exc)})
    result["status"] = "unavailable"
    return result


def cache_figures(data_path: Path, assets_dir: Path, timeout: int = 12, workers: int = 4,
                  report_path: Path = Path("outputs/figure_diagnostics.json")) -> tuple[int, int]:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    assets_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(discover_paper, paper, assets_dir, timeout): paper for paper in data.get("papers", [])}
        for future in as_completed(futures):
            paper = futures[future]
            result = future.result()
            results.append(result)
            if result["status"] == "cached":
                paper.update({key: result[key] for key in ("figure_url", "figure_alt", "figure_source_url", "figure_page_url")})
            elif result["status"] == "unavailable":
                paper["figure_url"] = ""
            print(f"[{len(results)}/{len(futures)}] {result['status']}: {paper.get('title', '')[:85]}", flush=True)
    cached = sum(result["status"] in {"cached", "cached_existing"} for result in results)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"checked_at": datetime.now().isoformat(timespec="seconds"), "total": len(results),
                                      "cached": cached, "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cached, len(results) - cached


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="site/data/papers.json")
    parser.add_argument("--assets", default="site/assets/papers")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    cached, missing = cache_figures(Path(args.data), Path(args.assets), args.timeout, args.workers)
    print(f"Cached figures: {cached}; unavailable figures hidden: {missing}")


if __name__ == "__main__":
    main()
