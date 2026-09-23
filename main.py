import argparse
import os
import sys
import time
import yaml

from scraper import fetch_trending
from summarizer import summarize
from notifier import send_feishu


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="GitHub Trending Digest")
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不推送飞书")
    args = parser.parse_args()

    cfg = load_config(args.config)

    since = "daily" if args.mode == "daily" else "weekly"
    language = cfg.get("trending", {}).get("language", "")
    top_n = cfg.get("trending", {}).get("top_n", 10)

    llm_cfg = cfg.get("llm", {})
    provider = llm_cfg.get("provider", "gpt-model-proxy")
    if provider == "anthropic":
        api_key = cfg.get("anthropic", {}).get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        model = cfg.get("anthropic", {}).get("model", "claude-haiku-4-5-20251001")
    else:
        api_key = llm_cfg.get("api_key", "")
        model = llm_cfg.get("model", "gpt-6-sol")

    feishu_cfg = cfg.get("feishu", {})
    app_id     = feishu_cfg.get("app_id")     or os.environ.get("FEISHU_APP_ID", "")
    app_secret = feishu_cfg.get("app_secret") or os.environ.get("FEISHU_APP_SECRET", "")
    chat_id    = feishu_cfg.get("chat_id")    or os.environ.get("FEISHU_CHAT_ID", "")

    if not args.dry_run and not (app_id and app_secret and chat_id):
        sys.exit("错误：未配置飞书凭证（需要 app_id、app_secret、chat_id）")

    print(f"[1/3] 抓取 GitHub Trending（since={since}, language={language or '全部'}）...")
    repos = fetch_trending(language=language, since=since)[:top_n]
    print(f"      获取到 {len(repos)} 个项目")
    if not repos:
        sys.exit("错误：榜单为空，取消推送")

    print(f"[2/3] 调用 {model} 生成中文简介...")
    for attempt in range(3):
        try:
            repos = summarize(repos, api_key=api_key, model=model, cfg=cfg)
            break
        except Exception as exc:
            print(f"      摘要生成失败（{attempt + 1}/3）：{exc}", file=sys.stderr)
            if attempt == 2:
                sys.exit("错误：无法生成完整中文分析，取消推送")
            time.sleep(30 * (attempt + 1))

    if args.dry_run:
        print("\n[dry-run] 推送内容预览：\n")
        for i, r in enumerate(repos, 1):
            print(f"{i}. {r['full_name']}\n   {r.get('summary', '')}\n")
        return

    print("[3/3] 推送到飞书...")
    send_feishu(repos, app_id=app_id, app_secret=app_secret, chat_id=chat_id, mode=args.mode)
    print("完成！")


if __name__ == "__main__":
    main()
