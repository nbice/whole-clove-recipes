# The Whole Clove

No life stories. Just recipes.

A static recipe site built with a custom Python static site generator. Recipes are JSON files that get turned into HTML pages at build time.

## Build

Requires Python 3. No dependencies.

```
python3 scripts/build.py
```

Output goes to `output/`. Preview locally with `python3 scripts/serve.py` and visit http://localhost:8000 (handles clean URLs the same way GitHub Pages does).

Validate every recipe (used by CI):

```
python3 scripts/test_recipes.py
```

## Adding a Recipe

Create a `.json` file in `recipes/`. The canonical schema lives in `templates/recipe.json` (flat) and `templates/recipe_grouped.json` (multi-component recipes with sub-sections like cookies + frosting). Look at any file in `recipes/` for a real example.

A few conventions worth knowing:

- `title` is lowercase; the filename matches (`bourbon_butter_pecan_ice_cream.json`).
- `tags` is a single comma-separated string, not an array.
- Time fields (`prep_time`, `cook_time`, `inactive_time`, `total_time`) are human strings like `"1 hour 30 minutes"` — they're parsed to ISO 8601 for JSON-LD at build time.
- Ingredients are structured: `{"qty": 1, "unit": "C", "item": "flour"}`. `qty` is a number when possible, a string for fractions (`"1/2"`).
- Directions can be plain strings or `{"step": "...", "ingredients": [0, 2]}` objects that highlight specific ingredients beneath the step.
- Cross-link to other recipes with `[pepper jam](recipes/pepper_jam)`.
- Number ranges use a tight hyphen with no surrounding spaces: `2-5 minutes`, `15-18 minutes`, `2-5 days` — never `2 - 5 minutes`.

## Adding a Recipe from a Photo

If you have a photo of a handwritten or printed recipe, use the `/recipe-from-photo` Claude Code skill (`.claude/skills/recipe-from-photo/`) — it transcribes the image into the JSON schema, runs the build, and proofreads the result.

## Deployment

Push to `main` — GitHub Actions builds the site and deploys to GitHub Pages automatically.
