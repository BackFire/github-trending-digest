#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python3 -m unittest -v
python3 -m py_compile main.py scraper.py summarizer.py notifier.py
bash -n cron_wrapper.sh
python3 - <<'PY'
import yaml

with open("config.yaml", encoding="utf-8") as config_file:
    config = yaml.safe_load(config_file)
assert config["llm"]["provider"] == "gpt-model-proxy"
assert config["llm"]["model"] == "gpt-6-sol"
assert not any(config.get("feishu", {}).values())
PY
