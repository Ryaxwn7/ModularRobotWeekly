from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .models import Paper


class Summarizer:
    def summarize(self, papers: list[Paper], config: dict[str, Any]) -> str:
        raise NotImplementedError


class TemplateSummarizer(Summarizer):
    def summarize(self, papers: list[Paper], config: dict[str, Any]) -> str:
        if not papers:
            return "本轮没有发现达到阈值的新增论文。"
        top_topics: dict[str, int] = {}
        top_tags: dict[str, int] = {}
        for paper in papers:
            for topic in paper.topics:
                top_topics[topic] = top_topics.get(topic, 0) + 1
            for tag in paper.tags:
                top_tags[tag] = top_tags.get(tag, 0) + 1
        topic_text = ", ".join(f"{name}({count})" for name, count in sorted(top_topics.items()))
        tag_text = ", ".join(f"{name}({count})" for name, count in sorted(top_tags.items()))
        return (
            f"本轮筛选出 {len(papers)} 篇候选论文。主题分布：{topic_text or '暂无'}。"
            f"研究类型标签：{tag_text or '暂无'}。建议优先阅读高分论文，并重点检查带有 "
            f"structure、system、control、swarm、reconfiguration 标签的工作。"
        )


class ChatCompletionsSummarizer(Summarizer):
    def __init__(self, provider: str, api_key_env: str, base_url: str, default_model: str) -> None:
        self.provider = provider
        self.api_key_env = api_key_env
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    def summarize(self, papers: list[Paper], config: dict[str, Any]) -> str:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            return TemplateSummarizer().summarize(papers, config)

        summarizer_config = config.get("summarizer", {})
        model = summarizer_config.get("model") or os.getenv(f"{self.provider.upper()}_MODEL") or self.default_model
        base_url = summarizer_config.get("base_url") or self.base_url
        prompt = build_summary_prompt(papers)
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You summarize robotics research progress in concise Chinese for a researcher.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": summarizer_config.get("temperature", 0.2),
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


class GeminiSummarizer(Summarizer):
    def summarize(self, papers: list[Paper], config: dict[str, Any]) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return TemplateSummarizer().summarize(papers, config)
        model = config.get("summarizer", {}).get("model") or os.getenv("GEMINI_MODEL") or "gemini-1.5-pro"
        prompt = build_summary_prompt(papers)
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def build_summary_prompt(papers: list[Paper]) -> str:
    items = []
    for index, paper in enumerate(papers[:20], start=1):
        items.append(
            "\n".join(
                [
                    f"{index}. {paper.title}",
                    f"Venue: {paper.venue}",
                    f"Published: {paper.published or paper.year or 'unknown'}",
                    f"Tags: {', '.join(paper.tags)}",
                    f"Abstract: {paper.abstract[:1200]}",
                ]
            )
        )
    return (
        "请根据以下论文候选列表，用中文生成一段科研进展简报：\n"
        "1. 先给 3-5 条趋势判断。\n"
        "2. 再指出最值得跟进的论文方向。\n"
        "3. 区分算法、结构设计、系统设计、理论研究。\n\n"
        + "\n\n".join(items)
    )


def build_summarizer(config: dict[str, Any]) -> Summarizer:
    provider = config.get("summarizer", {}).get("provider", "template").lower()
    if provider == "gemini":
        return GeminiSummarizer()
    if provider == "deepseek":
        return ChatCompletionsSummarizer(
            provider="deepseek",
            api_key_env="DEEPSEEK_API_KEY",
            base_url="https://api.deepseek.com",
            default_model="deepseek-chat",
        )
    if provider == "doubao":
        return ChatCompletionsSummarizer(
            provider="doubao",
            api_key_env="DOUBAO_API_KEY",
            base_url=os.getenv("DOUBAO_BASE_URL", ""),
            default_model=os.getenv("DOUBAO_MODEL", ""),
        )
    if provider == "openai_compatible":
        return ChatCompletionsSummarizer(
            provider="openai_compatible",
            api_key_env="OPENAI_COMPATIBLE_API_KEY",
            base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL", ""),
            default_model=os.getenv("OPENAI_COMPATIBLE_MODEL", ""),
        )
    return TemplateSummarizer()

