# GitHub Trending Digest

## 项目目标

定时抓取 GitHub Trending，读取项目 README、topics 等上下文，通过本机 `gpt-model-proxy` 生成中文简报，推送到飞书群。

- 日报：工作日 9:00 抓取当日榜单。
- 周报：周一 9:00 抓取本周榜单；周一也会执行日报。
- 每个项目用中文说明是什么、解决什么问题、适合什么场景；不要编造 README 未提供的事实。

## 技术方案

- Python 脚本解析 `github.com/trending`，并通过 GitHub API 补充 README、topics、主页和许可证信息。
- 默认通过本机 `gpt-model-proxy` 的 Responses API 调用 `gpt-6-sol`。上游凭证由代理管理，本项目不持有。
- `anthropic` 是可选的手动切换 provider，不是默认模型失败后的自动降级。
- 生产代码位于 `/opt/github-trending-digest`，root crontab 调用 `cron_wrapper.sh`；工作区修改不会自动影响定时任务。
- `notifier.py` 使用飞书 `post` 消息格式发送日报或周报。正式发送会产生可见消息，不要用它做测试。

## 配置与公开仓库约束

- `config.yaml` 中的 `trending.language` 留空表示所有语言，`trending.top_n` 默认 10。
- `llm.provider` 默认 `gpt-model-proxy`，`llm.model` 为 `gpt-6-sol`，`llm.base_url` 为 `http://127.0.0.1:8787/v1`。
- 生产环境的 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID` 均由 `/opt/github-trending-digest/.env` 提供，该文件权限为 `0600`。`config.yaml` 的 `feishu` 保持空对象。
- 不要向公开仓库提交真实凭证、应用或群标识、私有域名、`.env`、日志、虚拟环境；也不要把这些信息写进文档、示例或提交历史。

## 项目结构

```text
github-trending-digest/
├── AGENTS.md          # 项目维护与部署约定
├── README.md          # 使用说明
├── requirements.txt   # Python 依赖
├── config.yaml        # 非敏感配置
├── main.py            # 入口；daily/weekly 与 dry-run
├── scraper.py         # Trending 抓取及仓库信息补充
├── summarizer.py      # 中文摘要生成、解析和校验
├── notifier.py        # 飞书 post 消息发送
├── cron_wrapper.sh    # 生产环境加载 .env 并记录日志
├── crontab.example    # 定时调度示例
├── test_pipeline.py   # 主流程及发送保护测试
├── test_summarizer.py # 模型调用及摘要校验测试
└── verify.sh          # 本地测试、语法与配置检查
```

仓库不包含运行时 Skill；运行依赖这些 Python 脚本、配置和部署环境中的 crontab。

## 摘要与失败处理

- `scraper.py` 从 Trending HTML 取得榜单，再逐项读取 GitHub API；单项补充信息获取失败时继续处理该项目，README 摘要最长 1800 字符。
- `summarizer.py` 批量总结榜单，单次最大输出 8192 tokens；提示词要求每个项目用 5-7 句简体中文说明具体问题、用户和适用场景。
- 摘要解析保留多行内容，并检查每个项目均有中文分析。模型调用失败、缺少项目或分析不符合中文校验时，整批最多尝试 3 次，重试间隔为 30 秒、60 秒；OpenAI 客户端单次超时 180 秒、内部重试 2 次。
- 榜单为空或摘要最终失败时，程序非零退出，不发送占位简报。`--dry-run` 仍会实际抓取榜单并调用模型，但只打印预览，不发送飞书消息。
- 日志只记录执行过程，不保存已发送简报正文。重新运行日报或周报会抓取当时的榜单；正式运行会再次发送一条消息。故障后先核实送达情况，再决定是否补发，避免重复消息。

## 部署、调度与日志

生产环境从 `/opt/github-trending-digest` 运行；代码或配置变更需按范围同步到该目录。`cron_wrapper.sh` 启动时加载同目录 `.env`，执行 `main.py`，并把输出分别写入 `logs/daily.log`、`logs/weekly.log`，每个日志保留最近 2000 行。

root crontab 示例与 `crontab.example` 一致：

```cron
0 9 * * 1-5  /opt/github-trending-digest/cron_wrapper.sh daily
0 9 * * 1    /opt/github-trending-digest/cron_wrapper.sh weekly
```

## 验证与手动运行

本地代码检查，不访问 GitHub、模型或飞书：

```bash
./verify.sh
```

该脚本运行单元测试、Python 编译检查、`cron_wrapper.sh` 语法检查，并核对 `config.yaml` 的默认模型与空飞书配置。需要依赖安装完成；它不检查远端仓库、实际 cron 或部署目录，也不做模型 dry-run。

生产环境预览，不发送飞书，但会访问 GitHub 和本机模型代理：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -u /opt/github-trending-digest/main.py \
  --mode daily --dry-run --config /opt/github-trending-digest/config.yaml
```

手动运行 `python3 main.py --mode daily --dry-run` 或将模式改为 `weekly` 可在工作区预览。确认发送目标及是否已有消息后，才通过 `/opt/github-trending-digest/cron_wrapper.sh daily` 正式发送。
