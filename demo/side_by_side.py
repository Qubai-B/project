"""Build the supervisor demo: for one trajectory, a composite per step showing
   what the browser displays | what the model receives (task-aware guard)
and an animated GIF of the whole trajectory.

usage: .venv/bin/python demo/side_by_side.py [trajectory_id]   (default T02_tax_self_assessment_I0001)
out:   demo/<trajectory_id>/step_NNN.png, demo/<trajectory_id>.gif
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PIL import Image, ImageDraw, ImageFont
from common.paths import TRAJECTORIES, REDACTED, ROOT

tid = sys.argv[1] if len(sys.argv) > 1 else "T02_tax_self_assessment_I0001"
task = json.loads((TRAJECTORIES / tid / "task.json").read_text())
out = ROOT / "demo" / tid; out.mkdir(parents=True, exist_ok=True)
font = ImageFont.load_default()
frames = []
for sdir in sorted((TRAJECTORIES / tid / "steps").iterdir()):
    act = json.loads((sdir / "action.json").read_text())
    raw = Image.open(sdir / "screenshot.png").convert("RGB")
    red = Image.open(REDACTED / "trajectories" / tid / "steps" / sdir.name / "task_aware.png").convert("RGB")
    w, h = raw.size; scale = 0.5
    raw, red = raw.resize((int(w * scale), int(h * scale))), red.resize((int(w * scale), int(h * scale)))
    canvas = Image.new("RGB", (raw.width * 2 + 30, raw.height + 70), "white")
    canvas.paste(raw, (10, 60)); canvas.paste(red, (raw.width + 20, 60))
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), f"{tid}   step {act['step']}   goal: {task['goal']}", fill="black", font=font)
    nxt = f"next action: {act['action']} {act['target_field']}" + (f" = {act['value']}" if act["value"] else "")
    d.text((10, 24), nxt, fill="#008751", font=font)
    d.text((10, 44), "BROWSER (what the user sees)", fill="black", font=font)
    d.text((raw.width + 20, 44), "MODEL INPUT (after task-aware guard)", fill="black", font=font)
    canvas.save(out / f"step_{act['step']:03d}.png"); frames.append(canvas)
frames[0].save(ROOT / "demo" / f"{tid}.gif", save_all=True, append_images=frames[1:], duration=1800, loop=0)
print(f"wrote {len(frames)} composites -> demo/{tid}/, demo/{tid}.gif")
