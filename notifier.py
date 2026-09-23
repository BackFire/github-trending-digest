import json
import re
import urllib.request
from datetime import date

FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_MSG_URL   = "https://open.feishu.cn/open-apis/im/v1/messages"


def _get_token(app_id: str, app_secret: str) -> str:
    body = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(
        FEISHU_TOKEN_URL, data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    token = data.get("tenant_access_token")
    if not token:
        raise RuntimeError(f"获取飞书 token 失败: {data}")
    return token


def _md_to_post_content(md: str) -> list:
    paragraphs = []
    for line in md.split("\n"):
        raw = line.strip()
        if not raw:
            continue
        text = re.sub(r'^#{1,3}\s*', '', raw)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = text.strip(" -_—")
        if text:
            elem = {"tag": "text", "text": text}
            if raw.startswith("#"):
                elem["style"] = ["bold"]
            paragraphs.append([elem])
    return paragraphs[:200]


def _render_md(repos: list[dict], mode: str) -> tuple[str, str]:
    today = date.today().strftime("%Y-%m-%d")
    title = f"GitHub Trending 日报 · {today}" if mode == "daily" else f"GitHub Trending 周报 · {today}"

    lines = []
    for i, repo in enumerate(repos, 1):
        lang = f" [{repo['language']}]" if repo.get("language") else ""
        stars = f"  ⭐ {repo['stars']}" if repo.get("stars") else ""
        growth = re.search(r"[\d,]+", str(repo.get("today_stars", "")))
        period = "今日" if mode == "daily" else "本周"
        today_stars = f"  ({period} +{growth.group()})" if growth else ""
        lines.append(f"## {i}. {repo['full_name']}{lang}{stars}{today_stars}")
        lines.append(repo.get("summary") or repo.get("description", ""))
        lines.append(f"链接：{repo['url']}")
        lines.append("")

    return title, "\n".join(lines)


def send_feishu(repos: list[dict], app_id: str, app_secret: str,
                chat_id: str, mode: str) -> None:
    token = _get_token(app_id, app_secret)
    title, md = _render_md(repos, mode)
    paragraphs = _md_to_post_content(md)

    content = json.dumps(
        {"zh_cn": {"title": title, "content": paragraphs}},
        ensure_ascii=False
    )
    body = json.dumps(
        {"receive_id": chat_id, "msg_type": "post", "content": content},
        ensure_ascii=False
    ).encode()

    req = urllib.request.Request(
        f"{FEISHU_MSG_URL}?receive_id_type=chat_id",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
    if resp.get("code", -1) != 0:
        raise RuntimeError(f"飞书推送失败: {resp}")
