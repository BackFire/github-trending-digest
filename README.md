# GitHub Trending Digest

A scheduled Chinese digest of GitHub Trending projects. Each entry uses the repository README and topics to explain the project, the problem it addresses, and where it fits.

## Setup

The default model is `gpt-6-sol`, called through a local OpenAI-compatible proxy at `http://127.0.0.1:8787/v1` using the Responses API. Set `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, and `FEISHU_CHAT_ID` in the runtime environment to enable delivery. No deployment identifiers or credentials belong in `config.yaml`.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --mode daily --dry-run
./verify.sh
```

Use `--mode weekly` for the weekly digest. `crontab.example` and `cron_wrapper.sh` show the `/opt/github-trending-digest` deployment schedule; the wrapper loads that directory's `.env` file. A failed summary or empty list exits without sending.
