# The Whole Clove

No life stories. Just recipes.

A static recipe site built with a custom Python static site generator. Recipes are JSON files that get turned into HTML pages at build time.

## Build

Requires Python 3. No dependencies.

```
python3 build.py
```

Output goes to `output/`. Preview locally with `python3 scripts/serve.py` and visit http://localhost:8000 (handles clean URLs the same way GitHub Pages does).

## Adding a Recipe

Create a `.json` file in `recipes/`:

```json
{
    "title": "Recipe Name",
    "description": "Short description.",
    "category": "Category",
    "tags": ["tag1", "tag2"],
    "prep": "10 min",
    "cook": "20 min",
    "total": "30 min",
    "serves": 4,
    "equipment": ["Sheet pan", "Mixing bowl"],
    "ingredients": [
        {
            "group": "Group Name",
            "items": ["1 cup flour", "2 eggs"]
        }
    ],
    "directions": [
        "Step one.",
        "Step two."
    ],
    "notes": ["Optional tips."]
}
```

See `recipes/garlic-butter-smashed-potatoes.json` for a full example.

## Deployment

Push to `main` — GitHub Actions builds the site and deploys to GitHub Pages automatically.
