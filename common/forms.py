"""Load form manifests and templates; shared label→field vocabulary."""
from __future__ import annotations
import json
import re
from jinja2 import Template
from .paths import FORMS

FILL_STATES = ("empty", "partial", "filled")

# Keywords that identify a field from its on-screen label. Order matters: first match wins,
# so the more specific entries come before generic ones ("state" is last on purpose).
FIELD_LABEL_KEYWORDS = [
    ("date_of_birth", [r"date of birth", r"\bdob\b"]),
    ("tin",           [r"tax identification", r"\btin\b"]),
    ("nin",           [r"national identification", r"\bnin\b"]),
    ("bvn",           [r"bank verification", r"\bbvn\b"]),
    ("bank_account",  [r"account number", r"\bnuban\b"]),
    ("annual_income", [r"annual income", r"\bincome\b"]),
    ("email",         [r"e-?mail"]),
    ("phone",         [r"phone", r"mobile"]),
    ("passport_no",   [r"passport"]),
    ("licence_no",    [r"licen[cs]e"]),
    ("address_line",  [r"street", r"\baddress\b"]),
    ("lga",           [r"local government", r"\blga\b"]),
    ("last_name",     [r"surname", r"last name"]),
    ("first_name",    [r"first name", r"given name"]),
    ("state",         [r"\bstate\b"]),
]

FIELD_PII_TYPE = {
    "last_name": "PERSON", "first_name": "PERSON", "date_of_birth": "DOB", "tin": "TIN", "nin": "NIN",
    "bvn": "BVN", "bank_account": "BANK_ACCOUNT", "annual_income": "FINANCIAL", "email": "EMAIL",
    "phone": "PHONE", "passport_no": "PASSPORT", "licence_no": "LICENCE_NO", "address_line": "ADDRESS",
    "lga": "ADDRESS", "state": "ADDRESS",
}


def field_from_label(text: str) -> str | None:
    t = text.lower()
    for field, patterns in FIELD_LABEL_KEYWORDS:
        if any(re.search(p, t) for p in patterns):
            return field
    return None


def load_manifest(form_id: str) -> dict:
    m = json.loads((FORMS / form_id / "form.json").read_text())
    m["fields"].sort(key=lambda f: f["fill_order"])
    return m


def list_forms() -> list[str]:
    return sorted(p.name for p in FORMS.iterdir() if (p / "form.json").exists())


def render(form_id: str, values: dict) -> str:
    """Render the template with the given field values and inline the stylesheet so page.html is self-contained."""
    tpl = Template((FORMS / form_id / "index.html").read_text())
    css = (FORMS / "styles.css").read_text()
    html = tpl.render(v=values)
    return html.replace('<link rel="stylesheet" href="../styles.css">', f"<style>\n{css}</style>")


def values_for_state(manifest: dict, identity: dict, fill_state: str) -> dict:
    fields = manifest["fields"]
    n = len(fields)
    if fill_state == "empty":
        filled = set()
    elif fill_state == "partial":
        filled = {f["name"] for f in fields[: (n + 1) // 2]}
    else:
        filled = {f["name"] for f in fields}
    return {f["name"]: (identity[f["identity_key"]] if f["name"] in filled else "") for f in fields}
