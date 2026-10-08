from __future__ import annotations

from importlib import resources

import yaml


def load_skills() -> list[dict[str, str | None]]:
    raw = yaml.safe_load(resources.files("learnloop.taxonomy").joinpath("skills.yaml").read_text("utf-8"))
    skills = raw["skills"]
    ids = {s["id"] for s in skills}
    out: list[dict[str, str | None]] = []
    for s in skills:
        parent = s["id"].rsplit(".", 1)[0] if "." in s["id"] else None
        if parent is not None and parent not in ids:
            raise ValueError(f"taxonomy: parent {parent!r} of {s['id']!r} is missing")
        out.append({"id": s["id"], "name": s["name"], "parent_id": parent})
    return out
