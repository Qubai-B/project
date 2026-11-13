"""Collect the files a hosting service needs into one small folder, deploy/bundle/.

usage: python deploy/make_bundle.py

The folder holds the Dockerfile, the guard, the web interface, the form manifests and the three
sample screenshots (about 1 MB), so it can be uploaded through a host's web page without the rest
of the repository. Its README.md carries the header a Hugging Face Docker Space reads; other hosts
ignore it. The folder is rebuilt from scratch on every run and is not kept in git.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deploy" / "bundle"

README = """---
title: Redaction guard
emoji: "\\U0001F512"
colorFrom: green
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Masks personal data on a form screenshot before a model sees it
---

# Redaction guard: web interface

Demonstration server for an undergraduate project on data minimization at the perception layer
of screenshot-driven agents. Load one of the sample forms, choose the full or the task-aware
policy, and compare the original screenshot with the copy that would be sent to a model.

An access code is required. Set it as a **secret** named `GUARD_ACCESS_CODE` in the host's
settings; the server will not start without it.

All data on the sample forms is synthetic. Do not upload real personal data: in real use the
guard runs on the user's own device, and this hosted copy exists only so that evaluators can try it.

Source: https://github.com/Qubai-B/project
"""

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for name in ("guard", "common", "forms"):
    shutil.copytree(ROOT / name, OUT / name, ignore=shutil.ignore_patterns("__pycache__"))
(OUT / "demo").mkdir()
for name in ("live_app.py", "live_page.html"):
    shutil.copy2(ROOT / "demo" / name, OUT / "demo" / name)
(OUT / "deploy").mkdir()
for name in ("requirements-web.txt", "constraints-web.txt"):
    shutil.copy2(ROOT / "deploy" / name, OUT / "deploy" / name)
shutil.copy2(ROOT / "Dockerfile", OUT / "Dockerfile")
for form in sorted(p.name for p in (ROOT / "forms").iterdir() if (p / "form.json").exists()):
    rel = Path("data/benchmark") / form / "I0001" / "filled" / "screenshot.png"
    (OUT / rel).parent.mkdir(parents=True)
    shutil.copy2(ROOT / rel, OUT / rel)
(OUT / "README.md").write_text(README, encoding="utf-8")

files = [p for p in OUT.rglob("*") if p.is_file()]
print(f"wrote {OUT}  ({len(files)} files, {sum(p.stat().st_size for p in files) / 1024:.0f} KB)")
