# ModularRobotWeekly

面向机器人领域的科研进展采集、周报生成与 GitHub Pages 展示项目。

关注方向：

- 模块化可重构机器人
- 自重构机器人与形态重组
- 群体智能与群体机器人
- 多机器人系统工程、协同控制、结构设计、算法与理论
- 仿生结构设计与仿生机器人机构
- 仿生群体算法、蚁群/粒子群等自然启发式多机器人协同方法

网站地址：

```text
https://ryaxwn7.github.io/ModularRobotWeekly/
```

仓库地址：

```text
https://github.com/Ryaxwn7/ModularRobotWeekly
```

## 功能

- 从 arXiv、Crossref、Semantic Scholar、OpenAlex 等公开源采集论文。
- 使用 21 天重叠回采窗口，补偿数据库延迟收录、任务中断和电脑离线。
- 对 Nature、Science、IEEE、ACM 及机器人、AI、计算机视觉、机器学习高水平期刊进行定向巡检和分级加权。
- 可选接入 IEEE、Elsevier、Gemini、DeepSeek、豆包等 API。
- 按期刊来源、主题相关性、算法/结构/系统/理论标签评分。
- 过滤未来日期论文和非机器人主题论文。
- 生成 Markdown 周报。
- 同步生成 `site/data/papers.json`，供静态网站展示。
- 通过 GitHub Actions 每周一、周四自动更新并发布到 GitHub Pages。

## 本地运行

按配置生成最近 21 天的重叠回采周报和网站数据：

```powershell
python -m daily_research_agent --config config.weekly.json
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

发布逻辑：

- 本地 Codex 周报自动化负责搜索、总结并更新 `site/data/papers.json`。
- 本地脚本 `scripts/publish_site_data.ps1` 负责把 Codex 周报结果提交并推送到 GitHub。
- GitHub Actions 只负责把仓库里的 `site/` 目录部署到 GitHub Pages。
- GitHub Actions 不再执行论文搜索，避免覆盖本地 Codex/Consensus 周报结果。

需要在 GitHub 仓库设置中启用 Pages，并选择 GitHub Actions 作为发布源。
