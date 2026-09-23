import base64
import requests
from bs4 import BeautifulSoup


GITHUB_API = "https://api.github.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; GithubTrendingDigest/1.0)"}


def fetch_trending(language: str = "", since: str = "daily") -> list[dict]:
    url = f"https://github.com/trending/{language}?since={since}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    repos = []

    for article in soup.select("article.Box-row"):
        name_tag = article.select_one("h2 a")
        if not name_tag:
            continue

        full_name = name_tag.get("href", "").strip("/")
        desc_tag = article.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        lang_tag = article.select_one("[itemprop='programmingLanguage']")
        language_detected = lang_tag.get_text(strip=True) if lang_tag else ""

        stars_tag = article.select_one("a[href$='/stargazers']")
        stars = stars_tag.get_text(strip=True).replace(",", "") if stars_tag else "0"

        today_stars_tag = article.select_one("span.d-inline-block.float-sm-right")
        today_stars = today_stars_tag.get_text(strip=True) if today_stars_tag else ""

        repo = {
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": description,
            "language": language_detected,
            "stars": stars,
            "today_stars": today_stars,
        }
        repo.update(fetch_repo_details(full_name))
        repos.append(repo)

    return repos


def fetch_repo_details(full_name: str) -> dict:
    details = {
        "topics": [],
        "homepage": "",
        "license": "",
        "readme_excerpt": "",
    }
    try:
        repo_resp = requests.get(f"{GITHUB_API}/repos/{full_name}", headers=HEADERS, timeout=20)
        if repo_resp.ok:
            data = repo_resp.json()
            details["topics"] = data.get("topics") or []
            details["homepage"] = data.get("homepage") or ""
            details["license"] = (data.get("license") or {}).get("name") or ""

        readme_resp = requests.get(f"{GITHUB_API}/repos/{full_name}/readme", headers=HEADERS, timeout=20)
        if readme_resp.ok:
            readme = readme_resp.json()
            content = base64.b64decode(readme.get("content", "")).decode("utf-8", errors="ignore")
            details["readme_excerpt"] = _readme_excerpt(content)
    except requests.RequestException:
        pass
    return details


def _readme_excerpt(content: str, max_chars: int = 1800) -> str:
    lines = []
    in_code = False
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line:
            continue
        if line.startswith(("[!", "<", "<!--", "---")):
            continue
        if line.lower().startswith(("badge", "license", "stars")):
            continue
        lines.append(line)
        if len("\n".join(lines)) >= max_chars:
            break
    return "\n".join(lines)[:max_chars]
