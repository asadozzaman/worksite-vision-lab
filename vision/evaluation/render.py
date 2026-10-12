"""Embed local review data without interpreting HTML or template tokens in labels."""

import json
import re
from pathlib import Path


def render_editor(bundle, reference):
    folder = Path(__file__).parent
    replacements = {
        "/*DATA*/": json.dumps(bundle, allow_nan=False).replace("<", "\\u003c"),
        "/*REFERENCE*/": json.dumps(reference, allow_nan=False).replace("<", "\\u003c"),
        "/*ANNOTATION_CORE*/": (folder / "annotation-core.js").read_text(encoding="utf-8"),
        "/*ANNOTATION_UI*/": (folder / "annotation-ui.js").read_text(encoding="utf-8"),
    }
    # One pass: token-like text in source attribution is data, never a second template.
    pattern = "|".join(re.escape(key) for key in replacements)
    return re.sub(
        pattern,
        lambda match: replacements[match.group()],
        (folder / "review.html").read_text(encoding="utf-8-sig"),
    )
