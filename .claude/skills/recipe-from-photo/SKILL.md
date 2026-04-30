---
name: recipe-from-photo
description: Transcribe a photo of a handwritten or printed recipe into a JSON file at recipes/<slug>.json that follows the project schema. Use when the user provides an image of a recipe and wants it added to the site.
user-invocable: true
---

# /recipe-from-photo — add a recipe from a photo

Transcribe a recipe image into the project's JSON schema and write it to `recipes/<slug>.json`.

## Inputs

The user provides one or more images (file paths, dropped attachments, or screenshot paths). If no image is referenced in the message, ask for one before doing anything.

## Steps

1. **Read the image** with the Read tool. If multiple photos cover one recipe (front/back of a card, multi-page), read all of them.
2. **Read the schema** if you don't already have it in context: `templates/recipe.json` (flat) and `templates/recipe_grouped.json` (multi-component). Use the grouped form only when the recipe has distinct sub-recipes (e.g. cookies + frosting).
3. **Transcribe everything you can read clearly.** For unclear handwriting, list the ambiguous items and ask the user to confirm before writing the file. Don't guess at quantities — if the qty is illegible, ask.
4. **Build the JSON** following project conventions (below).
5. **Write to `recipes/<slug>.json`** with the Write tool.
6. **Verify the build** by running `python3 scripts/build.py`. Confirm the recipe count went up by one and there were no errors.
7. **Proofread the transcription.** After writing, re-read the recipe text (description, directions, notes) and flag any spelling or grammar issues you noticed in the original — for example, misspelled words, missing articles, awkward phrasing, or punctuation slips. Transcribe faithfully into the JSON, then list suggested edits in your reply for the user to accept or ignore. Don't silently "correct" the original wording.

## Project conventions

- **`title`**: lowercase (e.g. `"barbacoa"`, not `"Barbacoa"`).
- **filename / slug**: lowercase, spaces → underscores, ASCII only. Example: `Bourbon Butter Pecan Ice Cream` → `bourbon_butter_pecan_ice_cream.json`. Match the style of existing files in `recipes/`.
- **`category`**: prefer an existing category — `mains`, `sides`, `desserts`, `soups`, `sauces`, `beverages`, `preserves`. Only invent a new category when none fit, and warn the user when you do (it creates a new top-level page).
- **`tags`**: a single comma-separated **string**, NOT an array. Example: `"beef, mexican"`.
- **`created_at`**: today's date in `YYYY-MM-DD` format.
- **time fields**: format as `"10 minutes"`, `"2 hours"`, `"1 hour 30 minutes"` — they're parsed to ISO 8601 for JSON-LD. Leave empty if the photo doesn't list timing; don't guess.
- **ingredient `qty`**: a number when possible (`1`, `2.5`); a string for fractions (`"1/2"`, `"3/4"`). `unit` should be short: `C`, `t`, `T`, `g`, `oz`, `lbs`, `ml`. Omit `unit` for countable items (eggs, onions).
- **number ranges**: use a tight hyphen with no surrounding spaces — `2-5 minutes`, `15-18 minutes`, `2-5 days`. Never `2 - 5 minutes`.
- **`description`**: only fill in if the photo has a tagline; otherwise leave as `""`.
- **`notes`**: only include notes actually written on the photo.
- **ingredient order**: list ingredients in the order they're first used in the directions. Photos are often written out of order (e.g. spices grouped together, liquids at the bottom) — don't blindly preserve the photo's order. Reorder so a reader scanning the ingredient list reads it top-to-bottom in the same sequence the recipe uses each item. If the photo's order differs meaningfully from the use order, mention the reorder in your proofread reply so the user can confirm.
- **`amount_variations`**: leave as-is from the template or omit; this field is reserved for future use.

## Step ingredient refs

When using object-form steps `{"step": "...", "ingredients": [...]}`:
- For **flat ingredients**: indices refer to the flat ingredient list.
- For **grouped ingredients**: indices refer to ingredients within the **same-named group** as the direction group. The build script matches `ingredients[i].group` to `directions[j].group`.

If the same ingredient is reused at a different qty in a step, use the override form: `{"index": 0, "qty": "1/2", "unit": "C"}`.

**Introduce each ingredient only once.** Once an ingredient is highlighted in a step (in its full quantity), do not list it again in later steps — even if the prose mentions it. The highlight is for "this is when this ingredient enters the recipe," not for "this ingredient is involved in this step."

The one exception is when an ingredient is **split across steps** at partial quantities (use the override form for each split). For example, in `recipes/strawberry_habanero_jam.json`, sugar is split — `1/4 C` enters in step 3 and the remaining `1 3/4 C` enters in step 4. Strawberries, by contrast, are introduced in step 1 and referenced again in steps 2 and 3 in the prose, but the `ingredients` array on those later steps does not list index 0 again.

## Cross-references

If the recipe references another recipe on the site (e.g. "serve with pepper jam" and there's a `pepper_jam.json`), use markdown-style links in the relevant text: `[pepper jam](recipes/pepper_jam)`. Check `recipes/` for the right slug before linking.

## When in doubt

Show the JSON to the user before writing if:
- Handwriting is hard to read on any quantity, ingredient name, or step.
- The recipe doesn't clearly fit an existing category.
- Ingredients and step references don't line up cleanly.

Otherwise, write the file directly and run the build to verify.
