#!/usr/bin/env bash
# Full pipeline, in order. Stages 6 and 7 need ANTHROPIC_API_KEY in .env and are skipped without it.
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
export PYTHONWARNINGS=ignore

$PY scripts/01_gen_identities.py
$PY scripts/02_render_benchmark.py
$PY scripts/03_record_trajectories.py
$PY scripts/04_run_guard.py
$PY scripts/04_run_guard.py --detector presidio --only benchmark --states filled --limit 10   # baseline for Exp. 1
$PY scripts/05_eval_detection.py
if grep -qE '^ANTHROPIC_API_KEY=.+' .env 2>/dev/null; then
  $PY scripts/06_eval_leakage.py
  $PY scripts/07_eval_step_accuracy.py
else
  echo ">> skipping Exp. 2 and 3: no ANTHROPIC_API_KEY in .env"
fi
$PY scripts/08_plot.py
$PY demo/side_by_side.py
$PY scripts/09_report.py
