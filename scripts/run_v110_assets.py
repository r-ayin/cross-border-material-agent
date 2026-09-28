#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Drive the project's own v1.1.0 copy/strategy pipeline over the lk888 chat channel.

Rebuilds product_description_{en,ko,pt}.md, strategy_document.md, listing.json and
the offline inspection report into build/lk888-run-<RUN_ID>/ using copy_gen's schema-
validated generation (<=2 chat calls per language) and assemble's extension fixer.
"""
import json
import os
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "agent"))

from src import assemble, copy_gen, strategy
from src.budget import Budget
from src.input_parse import load_input

RUN_ID = os.environ.get("LK888_RUN_ID", "20260922")
OUT = os.path.join(REPO, "build", "lk888-run-" + RUN_ID)
BASE = os.environ.get("LK888_BASE_URL", "https://api.lk888.ai:18443/v1").rstrip("/")
KEY_FILE = os.path.expanduser("~/.dsh/credentials/lk888.key")
CHAT_MODEL = os.environ.get("LK888_CHAT_MODEL", "tt-5.5")
DATA_DIR = os.path.join(REPO, "data", "Task_Data", "Data_for_Users(2)")


class LKChat:
    """Minimal chat client matching copy_gen's chat.chat(model, messages, ...) contract."""

    def __init__(self, base=BASE, key_path=KEY_FILE, default_model=CHAT_MODEL):
        self.base = base
        with open(key_path) as f:
            self.key = f.read().strip()
        self.default_model = default_model

    def chat(self, model, messages, temperature=0.2, max_tokens=8000, timeout=120):
        try:
            timeout = min(float(timeout or 120), 180.0)
        except (TypeError, ValueError):
            timeout = 180.0
        body = json.dumps({"model": model or self.default_model,
                           "messages": messages,
                           "temperature": temperature,
                           "max_tokens": max_tokens}).encode()
        req = urllib.request.Request(
            self.base + "/chat/completions", data=body, method="POST",
            headers={"Authorization": "Bearer " + self.key,
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            j = json.loads(r.read())
        return j["choices"][0]["message"]["content"]


def main():
    os.makedirs(OUT, exist_ok=True)
    ctx = load_input("product 8822221153828 input %s output %s" % (DATA_DIR, OUT))
    ctx.update({
        "output_dir": OUT,
        "chat": LKChat(),
        "budget": Budget(),
        "style_profile": {"style_name": "premium-editorial"},
    })
    cq = os.path.join(OUT, "copy_quality.json")
    if os.environ.get("SKIP_COPIES") and os.path.exists(cq):
        with open(cq) as f:
            ctx["copy_quality"] = json.load(f)
        print("copies: reused existing copy_quality.json")
    else:
        copy_gen.generate_copies(ctx)
    print("product:", (ctx.get("product") or {}).get("offer_id"),
          "| category_info keys:", list((ctx.get("category_info") or {}).keys())[:4])
    print("copy_quality:", json.dumps(ctx.get("copy_quality"), ensure_ascii=False)[:300])
    ret = strategy.generate_strategy(ctx)
    print("strategy return:", type(ret), str(ret)[:120])
    assemble.fix_asset_extensions(OUT)
    listing = assemble.build_listing_json(ctx)
    print("listing keys:", list(listing.keys())[:10] if isinstance(listing, dict) else listing)
    report = assemble.inspect_outputs(OUT, ctx)
    print("inspect:", json.dumps(report, ensure_ascii=False)[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
