# 论文配图采集

运行 `python scripts/discover_paper_figures.py` 会访问 DOI 对应的期刊页面，
为没有本地配图的记录查找正文插图，并下载到 `site/assets/papers/`。
`scripts/cache_paper_figures.py` 的原有命令也会执行此流程。
发布脚本会先执行配图采集，并将图片文件与论文数据一同提交。

优先选择 Figure 1、机器人平台、结构设计、算法框架或总览图。
排除出版社 Logo、广告、占位图和 Nature/Springer 相关文章配图。
页面声明 DOI 时必须与目标论文一致。仅缓存通过文件签名、尺寸和完整性标记
检查的 PNG/JPEG；网页端使用同站本地文件，并在加载失败时移除整个图块。

每轮诊断保存在 `outputs/figure_diagnostics.json`，包含每篇的访问页面、
图片源地址和失败原因。HTTP 403、超时、页面未暴露插图均表示本轮未获取，
并不表示论文没有图。程序不绕过访问限制；缺图下次仍可重试。
已缓存的有效图片不重复下载。图源页面与图片地址保存在 `figure_page_url`
和 `figure_source_url`，便于追溯。
