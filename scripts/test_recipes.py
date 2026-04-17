#!/usr/bin/env python3
"""Validate that every recipe produces correct Recipe JSON-LD.

Checks the JSON-LD block that build.py would emit for each recipe:
- parses as valid JSON
- has @context/@type set to schema.org Recipe
- has non-empty name, description, ingredients, and instructions
- prepTime/cookTime/totalTime (when present) are ISO 8601 durations

Exit 0 on success, 1 on any failure. Safe to wire into a git pre-commit hook.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import RECIPES_DIR, build_recipe_jsonld, load_recipe  # noqa: E402

ISO_DURATION_RE = re.compile(r"^PT(?:\d+H)?(?:\d+M)?$")
SCRIPT_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)


def validate(ld):
    errors = []
    if ld.get("@context") != "https://schema.org":
        errors.append(f"@context={ld.get('@context')!r}")
    if ld.get("@type") != "Recipe":
        errors.append(f"@type={ld.get('@type')!r}")
    for key in ("name", "description"):
        val = ld.get(key)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{key} missing or empty")

    ings = ld.get("recipeIngredient")
    if not isinstance(ings, list) or not ings:
        errors.append("recipeIngredient missing or empty")
    elif not all(isinstance(x, str) and x.strip() for x in ings):
        errors.append("recipeIngredient contains empty/non-string entries")

    steps = ld.get("recipeInstructions")
    if not isinstance(steps, list) or not steps:
        errors.append("recipeInstructions missing or empty")
    else:
        for i, step in enumerate(steps):
            if not isinstance(step, dict) or step.get("@type") != "HowToStep":
                errors.append(f"recipeInstructions[{i}] not a HowToStep")
            elif not isinstance(step.get("text"), str) or not step["text"].strip():
                errors.append(f"recipeInstructions[{i}].text missing")

    for key in ("prepTime", "cookTime", "totalTime"):
        if key in ld and not ISO_DURATION_RE.match(ld[key]):
            errors.append(f"{key}={ld[key]!r} is not ISO 8601")

    return errors


def main():
    total = 0
    failed = 0
    for fname in sorted(os.listdir(RECIPES_DIR)):
        if not fname.endswith(".json"):
            continue
        total += 1
        path = os.path.join(RECIPES_DIR, fname)
        try:
            r = load_recipe(path)
            block = build_recipe_jsonld(r)
            m = SCRIPT_RE.search(block)
            if not m:
                raise ValueError("no JSON-LD script block emitted")
            ld = json.loads(m.group(1).replace("<\\/", "</"))
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            failed += 1
            print(f"FAIL {fname}: {type(e).__name__}: {e}")
            continue

        errors = validate(ld)
        if errors:
            failed += 1
            print(f"FAIL {fname}")
            for err in errors:
                print(f"   - {err}")
        else:
            print(f"ok   {fname}")

    print(f"\n{total - failed}/{total} recipes passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
