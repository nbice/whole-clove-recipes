#!/usr/bin/env python3
"""Static site generator for The Whole Clove."""

import datetime
import json
import os
import re
import shutil
# import build_recipe

ROOT = os.path.dirname(os.path.abspath(__file__))

# Matches markdown-style recipe links: [link text](recipes/slug)
# The slug maps to an HTML page at the site root (slug.html).
RECIPE_LINK_RE = re.compile(r'\[([^\]]+)\]\(recipes/([a-z0-9_\-]+)\)')


def render_links(text):
    """Convert [label](recipes/slug) markdown links to HTML anchors."""
    if not isinstance(text, str):
        return text
    return RECIPE_LINK_RE.sub(r'<a href="/\2">\1</a>', text)


def plain_text(text):
    """Strip [label](recipes/slug) markdown links to just the label."""
    if not isinstance(text, str):
        return text
    return RECIPE_LINK_RE.sub(r'\1', text)


DURATION_RE = re.compile(
    r'^\s*(?:(?P<h>\d+(?:\.\d+)?)\s*hours?)?\s*(?:(?P<m>\d+)\s*minutes?)?\s*$',
    re.IGNORECASE,
)


def to_iso_duration(text):
    """Convert '10 minutes', '2 hours', '2.5 hours', '2 hours 55 minutes' to ISO 8601.

    Returns None for empty/unparseable values (ranges, bare numbers, days, etc.).
    """
    if not isinstance(text, str) or not text.strip():
        return None
    m = DURATION_RE.match(text)
    if not m or not (m.group("h") or m.group("m")):
        return None
    total_minutes = 0.0
    if m.group("h"):
        total_minutes += float(m.group("h")) * 60
    if m.group("m"):
        total_minutes += int(m.group("m"))
    total_minutes = int(round(total_minutes))
    if total_minutes <= 0:
        return None
    hours, minutes = divmod(total_minutes, 60)
    out = "PT"
    if hours:
        out += f"{hours}H"
    if minutes:
        out += f"{minutes}M"
    return out
RECIPES_DIR = os.path.join(ROOT, "../recipes")
TEMPLATES_DIR = os.path.join(ROOT, "../templates")
STATIC_DIR = os.path.join(ROOT, "../static")
OUTPUT_DIR = os.path.join(ROOT, "../output")

SITE_URL = "https://thewholeclove.com"
SITE_TAGLINE = "A collection of recipes from The Whole Clove."


def page_url(filename):
    """Canonical URL for a given output filename. Strips .html for clean URLs."""
    if filename == "index.html":
        return SITE_URL + "/"
    slug = filename[:-5] if filename.endswith(".html") else filename
    return f"{SITE_URL}/{slug}"


def escape_attr(text):
    return (
        text.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def slugify(text):
    return text.lower().replace(" ", "-")


def load_recipe(filepath):
    with open(filepath) as f:
        data = json.load(f)
    data["slug"] = os.path.splitext(os.path.basename(filepath))[0]
    return data


def format_ingredient(item, include_prep=True, text_transform=render_links):
    if isinstance(item, str):
        return text_transform(item)
    result = ""
    if item.get("qty") is not None:
        result += str(item["qty"])
    if item.get("unit"):
        result += item["unit"]
    if item.get("item"):
        if result:
            result += " "
        result += item["item"]
    if include_prep and item.get("prep"):
        result += ", " + item["prep"]
    return text_transform(result)


def format_step_ingredient(ingredients, ref):
    """Format an ingredient reference for display below a direction step.

    ref can be:
      - an int (index into ingredients list)
      - a dict with "index" and optional "qty"/"unit" overrides
    """
    if isinstance(ref, int):
        return format_ingredient(ingredients[ref], include_prep=False)
    idx = ref["index"]
    base = ingredients[idx]
    if isinstance(base, str):
        return base
    ingredient = dict(base)
    if "qty" in ref:
        ingredient["qty"] = ref["qty"]
    if "unit" in ref:
        ingredient["unit"] = ref["unit"]
    return format_ingredient(ingredient, include_prep=False)


def render_step(step, all_ingredients):
    """Render a single direction step, with optional ingredient list below."""
    if isinstance(step, str):
        return f'                <li>{render_links(step)}</li>\n'
    text = render_links(step["step"])
    html = f'                <li>\n'
    html += f'                    <p>{text}</p>\n'
    if step.get("ingredients"):
        items = [format_step_ingredient(all_ingredients, ref) for ref in step["ingredients"]]
        html += f'                    <span class="step-ingredients">{", ".join(items)}</span>\n'
    html += '                </li>\n'
    return html


def render_recipe(r):
    html = '<article class="recipe">\n'

    # Header
    html += '    <div class="recipe-header">\n'
    cat_slug = slugify(r["category"])
    html += f'        <a href="/{cat_slug}" class="recipe-category">{r["category"]}</a>\n'
    html += f'        <h1>{r["title"]}</h1>\n'
    html += f'        <p class="description">{render_links(r["description"])}</p>\n'
    html += '    </div>\n\n'

    # Meta bar
    html += '    <div class="recipe-meta">\n'
    for label, key in [("Prep", "prep_time"), ("Cook", "cook_time"), ("Inactive", "inactive_time"), ("Total", "total_time"), ("Serves", "serves")]:
        value = r.get(key, "")
        if not value:
            continue
        html += '        <div class="meta-item">\n'
        html += f'            <span class="meta-label">{label}</span>\n'
        html += f'            <span class="meta-value">{value}</span>\n'
        html += '        </div>\n'
    html += '    </div>\n\n'

    html += '    <div class="recipe-body">\n'

    # Equipment
    if r.get("equipment"):
        html += '        <section class="equipment">\n'
        html += '            <h2>special equipment</h2>\n'
        html += '            <ul>\n'
        for item in r["equipment"]:
            html += f'                <li>{render_links(item)}</li>\n'
        html += '            </ul>\n'
        html += '        </section>\n\n'

    # Ingredients
    if r.get("ingredients"):
        html += '        <section class="ingredients">\n'
        html += '            <h2>ingredients</h2>\n'
        has_groups = any(isinstance(g, dict) and "group" in g for g in r["ingredients"])
        if has_groups:
            for group in r["ingredients"]:
                if isinstance(group, dict) and "group" in group:
                    html += f'            <h3>{group["group"]}</h3>\n'
                    html += '            <ul>\n'
                    for item in group["items"]:
                        html += f'                <li>{format_ingredient(item)}</li>\n'
                    html += '            </ul>\n'
        else:
            html += '            <ul>\n'
            for item in r["ingredients"]:
                html += f'                <li>{format_ingredient(item)}</li>\n'
            html += '            </ul>\n'
        html += '        </section>\n\n'

    # Directions
    if r.get("directions"):
        all_ingredients = r.get("ingredients", [])
        html += '        <section class="instructions">\n'
        html += '            <h2>directions</h2>\n'
        has_groups = any(isinstance(s, dict) and "group" in s for s in r["directions"])
        if has_groups:
            # Build a lookup from group name to its ingredient items
            ingredient_groups = {}
            for g in all_ingredients:
                if isinstance(g, dict) and "group" in g:
                    ingredient_groups[g["group"]] = g.get("items", [])
            for group in r["directions"]:
                if isinstance(group, dict) and "group" in group:
                    html += f'            <h3>{group["group"]}</h3>\n'
                    html += '            <ol>\n'
                    group_ingredients = ingredient_groups.get(group["group"], [])
                    for step in group["directions"]:
                        html += render_step(step, group_ingredients)
                    html += '            </ol>\n'
        else:
            html += '            <ol>\n'
            for step in r["directions"]:
                html += render_step(step, all_ingredients)
            html += '            </ol>\n'
        html += '        </section>\n\n'

    # Notes
    if r.get("notes"):
        html += '        <section class="notes">\n'
        html += '            <h2>notes</h2>\n'
        html += '            <ul>\n'
        for note in r["notes"]:
            html += f'            <li>{render_links(note)}</li>\n'
        html += '            </ul>\n'
        html += '        </section>\n'

    html += '    </div>\n'
    html += '</article>'
    return html


def build_page(template, title, content, description, url, search_index_json="[]", jsonld=""):
    page = template.replace("{{title}}", title)
    page = page.replace("{{content}}", content)
    page = page.replace("{{description}}", escape_attr(description))
    page = page.replace("{{url}}", url)
    page = page.replace("{{search_index}}", search_index_json)
    page = page.replace("{{jsonld}}", jsonld)
    return page


def recipe_description(r):
    desc = (r.get("description") or "").strip()
    if desc:
        return desc
    return f'{r["title"]} — a {r["category"]} recipe from The Whole Clove.'


def flatten_ingredients_plain(ingredients):
    """Flatten (possibly grouped) ingredients into a list of plain-text strings."""
    out = []
    has_groups = any(isinstance(g, dict) and "group" in g for g in ingredients)
    groups = ingredients if has_groups else [{"items": ingredients}]
    for g in groups:
        for item in g.get("items", []):
            out.append(format_ingredient(item, text_transform=plain_text))
    return out


def flatten_directions_plain(directions):
    """Flatten (possibly grouped) directions into a list of plain-text step strings."""
    out = []
    has_groups = any(isinstance(s, dict) and "group" in s for s in directions)
    groups = directions if has_groups else [{"directions": directions}]
    for g in groups:
        for step in g.get("directions", []):
            text = step if isinstance(step, str) else step["step"]
            out.append(plain_text(text))
    return out


def build_recipe_jsonld(r):
    """Build a schema.org Recipe JSON-LD <script> block for a recipe."""
    data = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r["title"],
        "description": recipe_description(r),
        "recipeCategory": r["category"],
        "author": {"@type": "Organization", "name": "The Whole Clove"},
        "url": page_url(r["slug"] + ".html"),
    }
    if r.get("yields"):
        data["recipeYield"] = r["yields"]
    for key, schema_key in [("prep_time", "prepTime"), ("cook_time", "cookTime"), ("total_time", "totalTime")]:
        iso = to_iso_duration(r.get(key, ""))
        if iso:
            data[schema_key] = iso
    tags = [t.strip() for t in (r.get("tags") or "").split(",") if t.strip()]
    if tags:
        data["keywords"] = ", ".join(tags)
    if r.get("ingredients"):
        ings = flatten_ingredients_plain(r["ingredients"])
        if ings:
            data["recipeIngredient"] = ings
    if r.get("directions"):
        steps = flatten_directions_plain(r["directions"])
        if steps:
            data["recipeInstructions"] = [{"@type": "HowToStep", "text": s} for s in steps]
    if r.get("image"):
        data["image"] = r["image"]
    # Escape </ so the JSON can't close the surrounding <script> tag.
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def _category_dropdown(categories, current_slug=None):
    """Render the category dropdown nav used on /recipes and category pages.

    current_slug:
      - "recipes": on the /recipes page (no 'all recipes' link needed).
      - "<cat-slug>": on a category page — includes 'all recipes', excludes current.
    """
    html = '        <div class="category-dropdown">\n'
    html += '            <button type="button" class="category-dropdown-toggle" aria-label="select category" aria-expanded="false" aria-haspopup="true">\n'
    html += '                <svg class="chevron" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4 L6 8 L10 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>\n'
    html += '            </button>\n'
    html += '            <ul class="category-dropdown-menu" role="menu" hidden>\n'
    if current_slug and current_slug != "recipes":
        html += '                <li role="none"><a role="menuitem" href="/recipes">all recipes</a></li>\n'
    for cat in sorted(categories):
        cat_slug = slugify(cat)
        if cat_slug == current_slug:
            continue
        html += f'                <li role="none"><a role="menuitem" href="/{cat_slug}">{cat}</a></li>\n'
    html += '            </ul>\n'
    html += '        </div>\n'
    return html


def build_index(template, recipes, search_json="[]"):
    by_cat = {}
    for r in sorted(recipes, key=lambda r: r["title"]):
        by_cat.setdefault(r["category"], []).append(r)

    html = '<div class="recipe-index">\n'
    html += '    <div class="recipe-index-header">\n'
    html += '        <h1>all recipes</h1>\n'
    html += _category_dropdown(by_cat.keys(), current_slug="recipes")
    html += '    </div>\n'
    for cat in sorted(by_cat):
        html += f'    <h2 class="category-heading"><a href="/{slugify(cat)}">{cat}</a></h2>\n'
        html += '    <ul class="recipe-list">\n'
        for r in by_cat[cat]:
            html += (
                f'        <li><a href="/{r["slug"]}">'
                f'<span class="recipe-name">{r["title"]}</span>'
                f'<span class="recipe-desc">{r.get("description", "")}</span>'
                f'</a></li>\n'
            )
        html += '    </ul>\n'
    html += '</div>\n'

    description = f"All {len(recipes)} recipes from The Whole Clove, organized by category."
    return build_page(template, "recipes", html, description, page_url("recipes.html"), search_json)


def build_category(template, category, recipes, all_categories, search_json="[]"):
    html = '<div class="recipe-index">\n'
    html += '    <div class="recipe-index-header">\n'
    html += f'        <h1>{category}</h1>\n'
    html += _category_dropdown(all_categories, current_slug=slugify(category))
    html += '    </div>\n'
    html += '    <ul class="recipe-list">\n'
    for r in sorted(recipes, key=lambda r: r["title"]):
        html += (
            f'        <li><a href="/{r["slug"]}">'
            f'<span class="recipe-name">{r["title"]}</span>'
            f'<span class="recipe-desc">{r.get("description", "")}</span>'
            f'</a></li>\n'
        )
    html += '    </ul>\n'
    html += '</div>\n'

    description = f"{category.capitalize()} recipes from The Whole Clove."
    return build_page(template, category, html, description, page_url(slugify(category) + ".html"), search_json)


def load_favorites():
    """Load the ordered list of chef's favorite recipe slugs, if present."""
    path = os.path.join(ROOT, "../favorites.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _render_home_list(recipes_list, indent="            "):
    html = ""
    for r in recipes_list:
        html += (
            f'{indent}<li><a href="/{r["slug"]}">'
            f'<span class="recipe-name">{r["title"]}</span>'
            f'<span class="recipe-desc">{r.get("description", "")}</span>'
            f'</a></li>\n'
        )
    return html


def _render_category_tiles(recipes, indent="        "):
    by_cat = {}
    for r in recipes:
        by_cat.setdefault(r["category"], []).append(r)
    html = f'{indent}<ul class="category-tiles">\n'
    for cat in sorted(by_cat):
        count = len(by_cat[cat])
        noun = "recipe" if count == 1 else "recipes"
        html += (
            f'{indent}    <li><a href="/{slugify(cat)}">'
            f'<span class="category-tile-name">{cat}</span>'
            f'<span class="category-tile-count">{count} {noun}</span>'
            f'</a></li>\n'
        )
    html += f'{indent}</ul>\n'
    return html


def build_home(template, recipes, search_json="[]"):
    # Recents: sort by created_at descending, then title as tiebreaker
    recent = sorted(
        recipes,
        key=lambda r: (r.get("created_at", ""), r["title"]),
        reverse=True,
    )[:5]

    # Chef's favorites: look up in the order specified by favorites.json
    by_slug = {r["slug"]: r for r in recipes}
    favorites = [by_slug[slug] for slug in load_favorites() if slug in by_slug]

    html = '<div class="home">\n'
    html += '    <div class="recipe-index">\n'
    html += '        <div class="home-lists">\n'
    html += '            <div class="home-list">\n'
    html += '                <h2>recently added</h2>\n'
    html += '                <ul class="recipe-list">\n'
    html += _render_home_list(recent, indent="                    ")
    html += '                </ul>\n'
    html += '            </div>\n'
    if favorites:
        html += '            <div class="home-list">\n'
        html += "                <h2>featured</h2>\n"
        html += '                <ul class="recipe-list">\n'
        html += _render_home_list(favorites, indent="                    ")
        html += '                </ul>\n'
        html += '            </div>\n'
    html += '        </div>\n'
    html += '        <h2>categories</h2>\n'
    html += _render_category_tiles(recipes)
    html += '        <a class="more-link" href="/recipes">more recipes &rarr;</a>\n'
    html += '    </div>\n'
    html += '</div>\n'

    return build_page(template, "The Whole Clove", html, SITE_TAGLINE, page_url("index.html"), search_json)


def build_sitemap(recipes, categories):
    """Generate sitemap.xml listing every page with a lastmod hint."""
    today = datetime.date.today().isoformat()
    entries = [(page_url("index.html"), today), (page_url("recipes.html"), today)]
    for cat in sorted(categories):
        entries.append((page_url(slugify(cat) + ".html"), today))
    for r in recipes:
        lastmod = r.get("created_at") or today
        entries.append((page_url(r["slug"] + ".html"), lastmod))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in entries:
        lines.append(f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>")
    lines.append("</urlset>\n")
    return "\n".join(lines)


def build_robots():
    return (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )


def _recipe_time_line(r):
    parts = []
    for label, key in [("Prep", "prep_time"), ("Cook", "cook_time"),
                       ("Inactive", "inactive_time"), ("Total", "total_time")]:
        val = r.get(key)
        if val:
            parts.append(f"{label}: {val}")
    if r.get("yields"):
        parts.append(f"Yields: {r['yields']}")
    return " | ".join(parts)


def build_llms_txt(recipes):
    """Concise site index for LLM agents (llmstxt.org)."""
    by_cat = {}
    for r in sorted(recipes, key=lambda r: r["title"]):
        by_cat.setdefault(r["category"], []).append(r)

    lines = [
        "# The Whole Clove",
        "",
        "> A collection of recipes. No life stories, just recipes.",
        "",
        f"{len(recipes)} recipes organized by category. Each recipe page includes "
        "ingredients, directions, timing, yield, and schema.org Recipe JSON-LD. "
        "See /llms-full.txt for the full content of every recipe inline.",
        "",
    ]
    for cat in sorted(by_cat):
        lines.append(f"## {cat}")
        lines.append("")
        for r in by_cat[cat]:
            desc = (r.get("description") or "").strip()
            if not desc and r.get("tags"):
                desc = r["tags"]
            link = f"[{r['title']}]({page_url(r['slug'] + '.html')})"
            lines.append(f"- {link}: {desc}" if desc else f"- {link}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_llms_full_txt(recipes):
    """Full-content LLM-friendly dump of every recipe."""
    lines = [
        "# The Whole Clove",
        "",
        "> A collection of recipes. No life stories, just recipes.",
        "",
    ]
    for r in sorted(recipes, key=lambda r: r["title"]):
        lines.append(f"## {r['title']}")
        lines.append("")
        lines.append(f"- URL: {page_url(r['slug'] + '.html')}")
        lines.append(f"- Category: {r['category']}")
        if r.get("tags"):
            lines.append(f"- Tags: {r['tags']}")
        time_line = _recipe_time_line(r)
        if time_line:
            lines.append(f"- {time_line}")
        if r.get("description"):
            lines.append("")
            lines.append(r["description"])

        if r.get("equipment"):
            lines.append("")
            lines.append("### Equipment")
            for item in r["equipment"]:
                lines.append(f"- {plain_text(item)}")

        if r.get("ingredients"):
            lines.append("")
            lines.append("### Ingredients")
            has_groups = any(isinstance(g, dict) and "group" in g for g in r["ingredients"])
            groups = r["ingredients"] if has_groups else [{"items": r["ingredients"]}]
            for g in groups:
                if g.get("group"):
                    lines.append("")
                    lines.append(f"**{g['group']}**")
                for item in g.get("items", []):
                    lines.append(f"- {format_ingredient(item, text_transform=plain_text)}")

        if r.get("directions"):
            lines.append("")
            lines.append("### Directions")
            has_groups = any(isinstance(s, dict) and "group" in s for s in r["directions"])
            groups = r["directions"] if has_groups else [{"directions": r["directions"]}]
            for g in groups:
                if g.get("group"):
                    lines.append("")
                    lines.append(f"**{g['group']}**")
                for i, step in enumerate(g.get("directions", []), 1):
                    text = step if isinstance(step, str) else step["step"]
                    lines.append(f"{i}. {plain_text(text)}")

        if r.get("notes"):
            lines.append("")
            lines.append("### Notes")
            for note in r["notes"]:
                lines.append(f"- {plain_text(note)}")

        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_search_index(recipes):
    """Return a compact JSON string of the search index for inlining."""
    index = []
    for r in sorted(recipes, key=lambda r: r["title"]):
        tags_raw = r.get("tags", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        index.append({
            "slug": r["slug"],
            "title": r["title"],
            "description": r.get("description", ""),
            "category": r["category"],
            "tags": tags,
        })
    return json.dumps(index, separators=(",", ":"))


def main():
    # Clean output
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # Load template
    with open(os.path.join(TEMPLATES_DIR, "base.html")) as f:
        template = f.read()

    # Load all recipes
    recipes = []
    for fname in sorted(os.listdir(RECIPES_DIR)):
        if not fname.endswith(".json"):
            continue
        data = load_recipe(os.path.join(RECIPES_DIR, fname))
        recipes.append(data)

    # Build search index (inline into every page)
    search_json = build_search_index(recipes)

    # Build recipe pages
    for data in recipes:
        out_name = data["slug"] + ".html"
        page = build_page(
            template,
            data["title"],
            render_recipe(data),
            recipe_description(data),
            page_url(out_name),
            search_json,
            jsonld=build_recipe_jsonld(data),
        )
        with open(os.path.join(OUTPUT_DIR, out_name), "w") as f:
            f.write(page)

    # Build category pages
    by_cat = {}
    for r in recipes:
        by_cat.setdefault(r["category"], []).append(r)
    for cat, cat_recipes in by_cat.items():
        with open(os.path.join(OUTPUT_DIR, slugify(cat) + ".html"), "w") as f:
            f.write(build_category(template, cat, cat_recipes, by_cat.keys(), search_json))

    # Build index and home
    with open(os.path.join(OUTPUT_DIR, "recipes.html"), "w") as f:
        f.write(build_index(template, recipes, search_json))
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w") as f:
        f.write(build_home(template, recipes, search_json))

    # Copy static assets
    if os.path.exists(STATIC_DIR):
        shutil.copytree(STATIC_DIR, os.path.join(OUTPUT_DIR, "static"))

    # SEO: sitemap + robots
    with open(os.path.join(OUTPUT_DIR, "sitemap.xml"), "w") as f:
        f.write(build_sitemap(recipes, by_cat.keys()))
    with open(os.path.join(OUTPUT_DIR, "robots.txt"), "w") as f:
        f.write(build_robots())

    # LLM discoverability (llmstxt.org)
    with open(os.path.join(OUTPUT_DIR, "llms.txt"), "w") as f:
        f.write(build_llms_txt(recipes))
    with open(os.path.join(OUTPUT_DIR, "llms-full.txt"), "w") as f:
        f.write(build_llms_full_txt(recipes))

    # Write CNAME for GitHub Pages
    with open(os.path.join(OUTPUT_DIR, "CNAME"), "w") as f:
        f.write("thewholeclove.com\n")

    print(f"Built {len(recipes)} recipe(s) → output/")


if __name__ == "__main__":
    main()
