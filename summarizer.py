import os

from openai import OpenAI

SUMMARY_MAX_TOKENS = 8192
SUMMARY_UNAVAILABLE = "本次未能生成该项目的中文分析，请通过项目链接查看 README。"


def summarize(repos: list[dict], api_key: str = "", model: str = "", cfg: dict = None) -> list[dict]:
    cfg = cfg or {}
    llm_cfg = cfg.get("llm", {})

    provider = llm_cfg.get("provider", "gpt-model-proxy")
    if not model:
        model = llm_cfg.get("model") or os.environ.get("SUMMARIZER_MODEL", "gpt-6-sol")

    project_lines = []
    for i, r in enumerate(repos, 1):
        project_lines.append(
            f"{i}. {r['full_name']}\n"
            f"   描述：{r['description'] or '（无描述）'}\n"
            f"   语言：{r['language'] or '未知'}\n"
            f"   Topics：{', '.join(r.get('topics') or []) or '无'}\n"
            f"   README 摘要：{r.get('readme_excerpt') or '（未获取到 README）'}\n"
            f"   链接：{r['url']}"
        )

    prompt = (
        "你是一个面向技术管理者和资深工程师的开源项目分析助手。以下是 GitHub Trending 上的热门项目列表，"
        "每个项目都包含 GitHub Trending 描述、topics 和 README 摘要。请基于 README 摘要分析，不要只翻译一句话描述。"
        "请为每个项目写一段中文简介，重点讲清楚『具体解决什么问题』和『应该在什么场景下关注/采用』。\n\n"
        "写作要求：\n"
        "1. 优先从 README 摘要提炼信息：核心功能、使用对象、工作流、输入输出、和同类工具相比的定位。\n"
        "2. 不要写泛泛而谈的夸奖，例如『强大』『高效』『创新』『提升效率』，除非说明具体提升了哪个环节。\n"
        "3. 必须把项目放到真实使用场景里解释：谁会用、在什么工作流/业务场景中用、替代了什么旧做法。\n"
        "4. 必须说明它解决的具体痛点，例如『摄像头监控有隐私风险』、『AI 编程代理跨会话丢失上下文』、『视觉检测结果后处理重复造轮子』。\n"
        "5. 如果 README 信息不足，不要编造细节；明确说『README 暂未说明』或『从描述看』。\n"
        "6. 每个项目输出 5-7 句完整的话，语言具体、克制、可读，不能只翻译一句项目描述。\n"
        "7. 所有自然语言必须使用简体中文；项目名、链接和必要技术专有名词可保留原文，不能直接输出英文描述或 README 原文。\n\n"
        "请严格按如下格式输出，每个项目之间用 \"---\" 分隔，不要添加额外说明：\n\n"
        "项目名：<full_name>\n"
        "简介：<基于 README 的具体分析：这是什么项目；解决的具体痛点；典型用户和使用流程；它替代/补充什么旧做法；什么时候值得关注，什么时候可能不适合。>\n\n---\n\n"
        "项目列表：\n" + "\n\n".join(project_lines)
    )

    if provider == "anthropic":
        text = _call_anthropic(prompt, api_key=api_key, model=model, cfg=cfg.get("anthropic", {}))
    else:
        text = _call_openai_compat(prompt, api_key=api_key, model=model, cfg=llm_cfg)

    summaries = _parse_summaries(text)
    invalid = [repo["full_name"] for repo in repos
               if not _is_chinese_summary(summaries.get(repo["full_name"], ""))]
    if invalid:
        raise ValueError("中文分析缺失或无效：" + ", ".join(invalid))
    for repo in repos:
        repo["summary"] = summaries[repo["full_name"]]

    return repos


def _call_openai_compat(prompt: str, api_key: str, model: str, cfg: dict) -> str:
    base_url = cfg.get("base_url") or "http://127.0.0.1:8787/v1"
    key = api_key or cfg.get("api_key") or "gpt-model-proxy"
    client = OpenAI(api_key=key, base_url=base_url, max_retries=2, timeout=180)
    resp = client.responses.create(
        model=model,
        max_output_tokens=SUMMARY_MAX_TOKENS,
        input=prompt,
    )
    return resp.output_text

def _call_anthropic(prompt: str, api_key: str, model: str, cfg: dict) -> str:
    import anthropic as _anthropic

    key = api_key or cfg.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    base_url = os.environ.get("ANTHROPIC_BASE_URL") or None
    client = _anthropic.Anthropic(api_key=key or None, base_url=base_url)
    if not model or model.startswith("gpt-"):
        model = os.environ.get("ANTHROPIC_DEFAULT_HAIKU_MODEL", "claude-haiku-4-5-20251001")
    message = client.messages.create(
        model=model,
        max_tokens=SUMMARY_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _parse_summaries(raw: str) -> dict[str, str]:
    result = {}
    for block in raw.split("---"):
        block = block.strip()
        name = ""
        summary_lines = []
        in_summary = False
        for line in block.splitlines():
            if line.startswith("项目名："):
                name = line.replace("项目名：", "").strip()
            elif line.startswith("简介："):
                summary_lines.append(line.replace("简介：", "").strip())
                in_summary = True
            elif in_summary:
                summary_lines.append(line)
        summary = "\n".join(summary_lines).strip()
        if name and summary:
            result[name] = summary
    return result


def _is_chinese_summary(summary: str) -> bool:
    return summary != SUMMARY_UNAVAILABLE and sum("\u4e00" <= char <= "\u9fff" for char in summary) >= 12
