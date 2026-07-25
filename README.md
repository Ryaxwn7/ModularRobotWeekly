# ModularRobotWeekly

面向机器人领域的科研进展采集、周报生成与 GitHub Pages 展示项目。

关注方向：

- 模块化可重构机器人
- 自重构机器人与形态重组
- 群体智能与群体机器人
- 多机器人系统工程、协同控制、结构设计、算法与理论

网站地址：

```text
https://ryaxwn7.github.io/ModularRobotWeekly/
```

仓库地址：

```text
https://github.com/Ryaxwn7/ModularRobotWeekly
```

## 功能

- 从 arXiv、Crossref、Semantic Scholar 等公开源采集论文。
- 可选接入 IEEE、Elsevier、Gemini、DeepSeek、豆包等 API。
- 按期刊来源、主题相关性、算法/结构/系统/理论标签评分。
- 过滤未来日期论文和非机器人主题论文。
- 生成 Markdown 周报。
- 同步生成 `site/data/papers.json`，供静态网站展示。
- 通过 GitHub Actions 每周一、周四自动更新并发布到 GitHub Pages。

## 本地运行

生成最近 4 天的周报和网站数据：

```powershell
python -m daily_research_agent --config config.weekly.json --days 4
```

报告输出目录：

```text
outputs/weekly_reports/
```

网站数据文件：

```text
site/data/papers.json
```

## 本地预览网站

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\preview_site.ps1 -Port 8000
```

然后打开：

```text
http://localhost:8000
```

## 网站展示字段

每篇论文展示：

- 原文链接
- 标题
- 论文总结
- 论文主图字段 `figure_url`
- DOI
- 期刊/来源
- 发布日期
- 主题标签
- 评分

如果数据源没有提供论文主图，网页会显示本地占位图。后续可以通过人工补充或脚本抽取真实主图链接。

## Consensus 额度策略

Consensus 是高价值、限额检索源。当前策略：

- Free tier 每月 30 uses。
- 每周一和周四生成周报。
- 每次周报默认最多使用 2 次 Consensus search。
- 先读取 `consensus_usage.json` 统计当月已用额度。
- 如果剩余额度不足，则自动减少搜索次数。

详细策略见：

```text
docs/consensus_quota_policy.md
prompts/weekly_consensus_report.md
```

## GitHub Pages

工作流文件：

```text
.github/workflows/research-site.yml
```

默认计划：

- 周一运行一次
- 周四运行一次
- 生成最新 `site/data/papers.json`
- 发布 `site/` 到 GitHub Pages

需要在 GitHub 仓库设置中启用 Pages，并选择 GitHub Actions 作为发布源。

