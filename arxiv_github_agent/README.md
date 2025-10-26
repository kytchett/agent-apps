# ArXiv + GitHub Top-100 Agent

这是一个轻量级的 Python agent，用于自动抓取：

- arXiv 的 Computer Science（cs）类别（默认）最新 top 100 论文，支持按关键词检索。
- GitHub 上按 Star 排序的 top 100 仓库，支持关键词或语言过滤。

特性：

- 可通过命令行一次性抓取或定时运行（简易轮询模式）。
- 支持把抓取结果保存为 JSON 文件（按时间戳保存到 data/ 目录）。
- 支持通过环境变量 `GITHUB_TOKEN` 提供 GitHub 访问令牌以避免速率限制。

先决条件

- Python 3.8+
- 推荐设置 `GITHUB_TOKEN`（若无 token，仍可运行但可能受速率限制）

安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

示例用法

一次性抓取 arXiv（默认 cs 分类最近 100 篇）和 GitHub（默认 stars 排序）并保存：

```bash
python agent.py --once
```

按关键词抓取：

```bash
python agent.py --arxiv-keywords "graph neural" --github-keywords "graph neural network" --once
```

按语言过滤 GitHub：

```bash
python agent.py --github-language Python --once
```

定时轮询（每 60 秒抓取一次）：

```bash
python agent.py --interval 60
```

输出目录

抓取数据会保存到 `data/` 目录，文件名中包含时间戳，例如：

- `data/2025-10-20T12-00-00_arxiv.json`
- `data/2025-10-20T12-00-00_github.json`

注意与假设

- arXiv 没有明确的“热度”排名；此 agent 默认把 `top 100` 解释为按提交时间排序的最近 100 篇（可通过关键词检索以缩小范围）。
- GitHub 的“关注度最高”用 Star 数排序实现，搜索结果依赖查询关键词和 language 限定。

扩展建议（可选）

- 使用更复杂的调度器（APScheduler / cron）以实现生产级定时。
- 根据下载量/引用/社交分享等指标对 arXiv 论文进行“热度”排序（需额外数据源）。

如果你想，我可以：
- 添加对 arXiv 按引用/altmetrics 的热度估算（需要第三方数据源）。
- 把结果推送到 Slack / 邮件 / Notion 等。

---

文件说明：
- `agent.py`：程序入口。
- `fetchers/arxiv.py`：arXiv 抓取逻辑。
- `fetchers/github.py`：GitHub 抓取逻辑。
- `utils/output.py`：保存输出的工具。
- `requirements.txt`：Python 依赖。
- `.env.example`：环境变量示例。
