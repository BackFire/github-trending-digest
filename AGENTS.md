# GitHub Trending Digest

## Project

Fetch GitHub Trending, enrich each entry with its README and topics, generate a Chinese daily or weekly digest, and send it to a Feishu chat. `main.py` is the entry point. `scraper.py`, `summarizer.py`, and `notifier.py` handle collection, analysis, and delivery.

## Public Repository Rules

- This repository is intended to be public. Never commit credentials, chat or app identifiers, private organization domains, `.env`, logs, or local virtual environments.
- Read `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, and `FEISHU_CHAT_ID` from the runtime environment. Keep `config.yaml` free of deployment identifiers.
- The default model is `gpt-6-sol` through the local `gpt-model-proxy` Responses API at `http://127.0.0.1:8787/v1`. The proxy owns upstream credentials.

## Behavior

- Run with `python3 main.py --mode daily` or `--mode weekly`; add `--dry-run` to preview without sending.
- An empty Trending list, a failed model request, or a missing/non-Chinese analysis must exit without sending. Transient summary failures retry at 30- and 60-second intervals.
- The output for each project should explain what it does, the problem it solves, and when it is useful. Do not invent facts absent from the README.
- Sending a digest is externally visible. Do not use a live send as a test.

## Validation And Deployment

- Run `./verify.sh` for local tests, compilation, configuration checks, and shell syntax. It does not send messages or call the model.
- Production runs from `/opt/github-trending-digest`; cron invokes `cron_wrapper.sh` there. Workspace edits do not change the deployed job.
- Keep credentials in `/opt/github-trending-digest/.env` with mode `0600`. The wrapper loads it before running the job.
