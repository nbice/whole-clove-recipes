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
    return RECIPE_LINK_RE.sub(r'<a href="\2.html">\1</a>', text)
RECIPES_DIR = os.path.join(ROOT, "../recipes")
TEMPLATES_DIR = os.path.join(ROOT, "../templates")
STATIC_DIR = os.path.join(ROOT, "../static")
OUTPUT_DIR = os.path.join(ROOT, "../output")

SITE_URL = "https://thewholeclove.com"
SITE_TAGLINE = "A collection of recipes from The Whole Clove."


def page_url(filename):
    if filename == "index.html":
        return SITE_URL + "/"
    return f"{SITE_URL}/{filename}"


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


def format_ingredient(item, include_prep=True):
    if isinstance(item, str):
        return render_links(item)
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
    return render_links(result)


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
    html += f'        <a href="{cat_slug}.html" class="recipe-category">{r["category"]}</a>\n'
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


def build_page(template, title, content, description, url, search_index_json="[]"):
    page = template.replace("{{title}}", title)
    page = page.replace("{{content}}", content)
    page = page.replace("{{description}}", escape_attr(description))
    page = page.replace("{{url}}", url)
    page = page.replace("{{search_index}}", search_index_json)
    return page


def recipe_description(r):
    desc = (r.get("description") or "").strip()
    if desc:
        return desc
    return f'{r["title"]} — a {r["category"]} recipe from The Whole Clove.'


def build_index(template, recipes, search_json="[]"):
    by_cat = {}
    for r in sorted(recipes, key=lambda r: r["title"]):
        by_cat.setdefault(r["category"], []).append(r)

    html = '<div class="recipe-index">\n'
    html += '    <div class="recipe-index-header">\n'
    html += '        <h1>all recipes</h1>\n'
    html += '        <div class="category-dropdown">\n'
    html += '            <button type="button" class="category-dropdown-toggle" aria-label="filter by category" aria-expanded="false" aria-haspopup="true">\n'
    html += '                <svg class="chevron" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 4 L6 8 L10 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>\n'
    html += '            </button>\n'
    html += '            <ul class="category-dropdown-menu" role="menu" hidden>\n'
    for cat in sorted(by_cat):
        html += f'                <li role="none"><a role="menuitem" href="{slugify(cat)}.html">{cat}</a></li>\n'
    html += '            </ul>\n'
    html += '        </div>\n'
    html += '    </div>\n'
    for cat in sorted(by_cat):
        html += f'    <h2 class="category-heading"><a href="{slugify(cat)}.html">{cat}</a></h2>\n'
        html += '    <ul class="recipe-list">\n'
        for r in by_cat[cat]:
            html += (
                f'        <li><a href="{r["slug"]}.html">'
                f'<span class="recipe-name">{r["title"]}</span>'
                f'<span class="recipe-desc">{r.get("description", "")}</span>'
                f'<span class="arrow">&rarr;</span>'
                f'</a></li>\n'
            )
        html += '    </ul>\n'
    html += '</div>\n'
    html += '''<script>
(function () {
  var btn = document.querySelector('.category-dropdown-toggle');
  var menu = document.querySelector('.category-dropdown-menu');
  if (!btn || !menu) return;
  function close() {
    menu.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
  }
  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    var open = !menu.hidden;
    menu.hidden = open;
    btn.setAttribute('aria-expanded', String(!open));
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.category-dropdown')) close();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
})();
</script>
'''

    description = f"All {len(recipes)} recipes from The Whole Clove, organized by category."
    return build_page(template, "recipes", html, description, page_url("recipes.html"), search_json)


def build_category(template, category, recipes, search_json="[]"):
    html = '<div class="recipe-index">\n'
    html += f'    <h1>{category}</h1>\n'
    html += '    <ul class="recipe-list">\n'
    for r in sorted(recipes, key=lambda r: r["title"]):
        html += (
            f'        <li><a href="{r["slug"]}.html">'
            f'<span class="recipe-name">{r["title"]}</span>'
            f'<span class="recipe-desc">{r.get("description", "")}</span>'
            f'<span class="arrow">&rarr;</span>'
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
            f'{indent}<li><a href="{r["slug"]}.html">'
            f'<span class="recipe-name">{r["title"]}</span>'
            f'<span class="recipe-desc">{r.get("description", "")}</span>'
            f'<span class="arrow">&rarr;</span>'
            f'</a></li>\n'
        )
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
    html += '        <h2>recently added</h2>\n'
    html += '        <ul class="recipe-list">\n'
    html += _render_home_list(recent)
    html += '        </ul>\n'
    if favorites:
        html += "        <h2>featured</h2>\n"
        html += '        <ul class="recipe-list">\n'
        html += _render_home_list(favorites)
        html += '        </ul>\n'
    html += '        <a class="more-link" href="recipes.html">more recipes &rarr;</a>\n'
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
        )
        with open(os.path.join(OUTPUT_DIR, out_name), "w") as f:
            f.write(page)

    # Build category pages
    by_cat = {}
    for r in recipes:
        by_cat.setdefault(r["category"], []).append(r)
    for cat, cat_recipes in by_cat.items():
        with open(os.path.join(OUTPUT_DIR, slugify(cat) + ".html"), "w") as f:
            f.write(build_category(template, cat, cat_recipes, search_json))

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

    # Write CNAME for GitHub Pages
    with open(os.path.join(OUTPUT_DIR, "CNAME"), "w") as f:
        f.write("thewholeclove.com\n")

    print(f"Built {len(recipes)} recipe(s) → output/")


if __name__ == "__main__":
    main()
