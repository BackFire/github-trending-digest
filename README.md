# GitHub Trending Digest

定时抓取 GitHub Trending，并结合项目 README 和 topics 生成中文日报、周报。每个项目的简介侧重实际用途、解决的问题和适用场景，最后以飞书 `post` 消息发送。

## 安装与配置

需要 Python 3，以及可访问的 GitHub、本机 `gpt-model-proxy`。默认使用 `gpt-6-sol`，经 `http://127.0.0.1:8787/v1` 的 Responses API 调用；代理负责上游凭证。

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

`config.yaml` 可设置 `trending.language`（空字符串表示所有语言）、`trending.top_n`（默认 10）、`llm.provider`、`llm.model` 和 `llm.base_url`。生产环境把 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID` 放在 `/opt/github-trending-digest/.env`，文件权限设为 `0600`；仓库中的 `feishu` 配置保持空对象。不要提交凭证、实际群或应用标识、私有域名、日志或 `.env`。

## 预览与验证

```bash
./verify.sh
python3 main.py --mode daily --dry-run
python3 main.py --mode weekly --dry-run
```

`verify.sh` 运行单元测试、语法和配置检查，不访问模型或发送消息。`--dry-run` 会实际抓取 GitHub Trending 并调用模型，只在终端打印简报预览，不发送飞书。未安装依赖或无法访问 GitHub、模型代理时，预览无法完成。

正式运行去掉 `--dry-run`；此时必须提供飞书三项环境变量，且会发送消息。榜单为空、模型请求失败或某个项目缺少有效中文分析时，程序不会发送；摘要最多尝试 3 次，间隔 30 秒、60 秒。

## 定时运行

生产环境使用 `/opt/github-trending-digest`，由 root crontab 调用 `cron_wrapper.sh`；工作区修改不会自动部署。示例见 `crontab.example`：

```cron
0 9 * * 1-5  /opt/github-trending-digest/cron_wrapper.sh daily
0 9 * * 1    /opt/github-trending-digest/cron_wrapper.sh weekly
```

周一 9:00 会分别执行日报和周报。包装脚本从部署目录加载 `.env`，把过程日志写入 `logs/daily.log` 和 `logs/weekly.log`，每个日志保留最近 2000 行，不保存已发送的简报正文。再次正式运行会重新抓取并发送一条消息；故障后先核实是否已送达。

部署目录的安全预览命令：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -u /opt/github-trending-digest/main.py \
  --mode daily --dry-run --config /opt/github-trending-digest/config.yaml
```

项目结构及维护约定见 [AGENTS.md](AGENTS.md)。
