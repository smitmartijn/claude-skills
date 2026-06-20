---
name: redash
description: Create, run, and manage Redash queries, visualizations, and dashboards through the Redash REST API. Use when the user says "create a Redash query", "build a Redash dashboard", "run this SQL in Redash", "add a chart to a dashboard", "what tables are in my data source", or any variant of working with Redash programmatically.
author: Martijn Smit
---

# Redash Agent

Drive a Redash instance over its REST API: introspect data sources, write and run queries, create visualizations, and assemble dashboards. A bundled zero-dependency Python helper (`redash.py`, stdlib only) wraps every endpoint and prints JSON so you can chain steps.

## Prerequisites

Two environment variables must be set before any command:

```bash
export REDASH_URL="https://redash.example.com"   # your instance, no trailing slash
export REDASH_API_KEY="<user API key>"
```

- Get the **user API key** from Redash → top-right avatar → **Settings → Account → API Key**. A user key inherits that user's permissions and is required to *create or modify* anything.
- A **per-query API key** (shown on a query page) only reads that one query's results — not enough for this skill.
- `python3` must be on PATH (stdlib only — no `pip install` needed).
- If the instance sits behind Cloudflare/a WAF, a `403` with `error code: 1010` means the default agent is banned. The helper already sends a normal `User-Agent`; override it with `REDASH_USER_AGENT` (e.g. a browser string) if a stricter rule still blocks you.

**Always run `test` first** to confirm credentials before doing real work:

```bash
python3 redash.py test
```

If the user hasn't given you a URL or key, ask for them. Never hardcode them into files; they're secrets.

## How Redash objects fit together

```
data source ──> query (SQL) ──> visualization(s) ──┐
                                                    ├─> widget ──> dashboard
                              text ─────────────────┘
```

- A **query** holds SQL + a data source. Running it produces a **query result**.
- A **visualization** is a view of a query's result (TABLE, CHART, COUNTER, …). A query can have several.
- A **dashboard** is a grid of **widgets**. Each widget embeds one visualization (or is a free text/markdown box).
- New queries and dashboards are created as **drafts** (`is_draft: true`) — invisible in lists until published.

## The commands

| Command | What it does |
|---|---|
| `test` | Verify URL + key (`GET /api/session`) |
| `data-sources` | List data sources and their numeric ids |
| `dashboards` | List dashboards (id, slug, name) — use to resolve a slug to its id |
| `schema --data-source-id N` | List tables and columns for a data source |
| `exec-sql --data-source-id N --sql "..."` | Run ad-hoc SQL **without saving**; returns rows. Use to explore/validate before saving. |
| `create-query --name --sql --data-source-id [--publish] [--description] [--options JSON]` | Create a saved query |
| `update-query --id [--name] [--sql] [--options] [--publish]` | Edit a query / publish it |
| `get-query --id` | Fetch a query (includes its `visualizations` array with their ids) |
| `run-query --id [--max-age N]` | Execute a saved query, return rows (`--max-age 0` = always fresh; default 0) |
| `create-viz --query-id --type --name [--options JSON] [--description]` | Add a visualization to a query |
| `create-dashboard --name` | Create an empty draft dashboard (returns `id` and `slug`) |
| `add-widget --dashboard-id [--viz-id] [--text] [--col --row --size-x --size-y]` | Place a widget on the grid |
| `publish-dashboard --id` | Clear `is_draft` so it's visible |
| `get-dashboard --id` | Fetch a dashboard by numeric id (preferred) or slug |
| `delete-query --id` / `delete-dashboard --id` | Archive a query / dashboard |

Run each from the skill directory, e.g. `python3 redash.py data-sources`.

---

## Workflow A — write and run a query

1. **Find the data source.** `data-sources` → note the `id` the user means. If unsure which, ask.
2. **Learn the schema.** `schema --data-source-id N` → use real table/column names. Don't guess.
3. **Validate the SQL** with `exec-sql` (nothing saved yet) so you catch errors before committing:
   ```bash
   python3 redash.py exec-sql --data-source-id 1 --sql "SELECT count(*) FROM users"
   ```
4. **Save it** once it works:
   ```bash
   python3 redash.py create-query --name "Active users" \
     --sql "SELECT date, count(*) FROM users GROUP BY 1" \
     --data-source-id 1 --publish
   ```
   Capture the returned `id` — you need it for visualizations and widgets.

## Workflow B — build a dashboard

A widget needs a **visualization id**, and a query has **no chart visualization** by default (only an implicit table). So the order is: query → visualization → dashboard → widgets → publish.

1. **Create + publish each query** (Workflow A). Keep each `query id`.
2. **Decide the visualization per query, then confirm.** Look at the result columns and propose a fit (table / line / bar / counter) with the intended axis mapping, and confirm with the user before creating it — don't silently pick. Then create it, capturing each returned `id`:
   ```bash
   python3 redash.py create-viz --query-id 42 --type CHART --name "Signups over time" \
     --options '{"globalSeriesType":"line","columnMapping":{"date":"x","count":"y"}}'
   ```
   For a plain table widget, you can reuse the query's built-in table viz — `get-query --id 42` and read `visualizations[].id` (the one with `"type":"TABLE"`).
3. **Create the dashboard** and capture `id` + `slug`:
   ```bash
   python3 redash.py create-dashboard --name "Growth"
   ```
4. **Add a widget per visualization**, laying them out on the grid (check its width first — see the note below):
   ```bash
   python3 redash.py add-widget --dashboard-id 7 --viz-id 99 \
     --col 0 --row 0 --size-x 3 --size-y 8
   python3 redash.py add-widget --dashboard-id 7 --viz-id 100 \
     --col 3 --row 0 --size-x 3 --size-y 8
   ```
   - **Check the grid width first.** It's not fixed — Redash dashboards are commonly 6 *or* 12 columns. When adding to an *existing* dashboard, `get-dashboard --id` and read the largest `sizeX`/`col`+`sizeX` among current widgets to learn the width, then match it (a full-width widget = that width). For a brand-new dashboard, 6 is the safe default.
   - **Place new widgets below existing ones.** Compute the next free row as `max(row + sizeY)` over current widgets so you don't overlap.
   - Increment `row` (by the previous `size-y`) to start a new row.
   - Text/markdown box: omit `--viz-id`, pass `--text "## Section"`.
5. **Publish** so it appears for others:
   ```bash
   python3 redash.py publish-dashboard --id 7
   ```
6. Report the dashboard URL: `$REDASH_URL/dashboards/<id>-<slug>` (the URL path is the id followed by the slug, e.g. `/dashboards/7-growth`).

---

## Visualization `--options` reference

`create-viz` takes a `--type` and a JSON `--options` blob whose shape depends on the type. Common ones:

- **TABLE** — `{}` works (Redash auto-derives columns). Every query already has a table viz, so you rarely need to create one.
- **CHART** — set the chart kind and map result columns to axes:
  ```json
  {
    "globalSeriesType": "line",
    "columnMapping": {"<x_column>": "x", "<y_column>": "y"},
    "seriesOptions": {},
    "legend": {"enabled": true}
  }
  ```
  `globalSeriesType` ∈ `line` `column` `area` `pie` `scatter` `bubble` `heatmap`. For a grouped series add the grouping column with `"series"` in `columnMapping`.
- **COUNTER** — a single big number:
  ```json
  {"counterColName": "<value_column>", "rowNumber": 1, "counterLabel": "Total"}
  ```
- **PIVOT** — `{}`; configure in UI, or pass pivot config if known.

When unsure of a chart option's exact key, create the viz with a minimal options blob, then tell the user they can fine-tune it in the Redash UI — the API and UI edit the same object.

## Parameterized queries

If the SQL contains `{{ param }}` placeholders, declare them in query `--options`:
```json
{"parameters": [{"name": "country", "type": "text", "title": "Country"}]}
```
Then `run-query` accepts values — extend the helper or run via the UI for parameter entry. For ad-hoc runs, inline the value instead.

---

## Pitfalls — don't repeat these

- **Don't skip `test`.** A wrong URL or a per-query key (vs. user key) fails confusingly later. Verify first.
- **Don't invent table/column names.** Always pull `schema` first; Redash errors are opaque.
- **Don't forget to publish.** Freshly created queries and dashboards are drafts and won't show in lists until `--publish` / `publish-dashboard`.
- **Don't expect a query to have a chart automatically.** Only an implicit TABLE viz exists; you must `create-viz` for any chart before it can go in a widget.
- **Don't overflow the grid width.** `col + size-x` must stay ≤ the dashboard's column count (6 or 12 — read it off existing widgets; see Workflow B step 4), or widgets overlap.
- **Don't add a widget with a stale viz id.** Use the `id` returned by `create-viz` (or from `get-query`), not the query id.
- **Don't hardcode secrets.** Read `REDASH_URL`/`REDASH_API_KEY` from the environment; if missing, ask the user.
- **Don't poll yourself.** `run-query`/`exec-sql`/`schema` already poll the job to completion and return final data. (`schema` returns a refresh job on a cold cache — the helper waits and re-fetches.)
- **Fetch dashboards by numeric id, not slug.** On 26.x a slug passed to `get-dashboard` returns HTTP 500 (id-only routing). Run `dashboards` to resolve a name/slug to its id first. (The id is also the leading number in a dashboard URL like `/dashboards/7-growth`.)
- **Don't assume a 6-column grid.** Width varies per dashboard (6 or 12 are both common). Read it off existing widgets before placing new ones, or they'll overlap or leave gaps.

Verified end-to-end against Redash 26.3.0 (MySQL data source): data-sources → schema → exec-sql → create-query → run-query → create-viz (CHART) → create-dashboard → add-widget → publish → delete all succeeded.

Keep this skill focused: introspect, query, visualize, and assemble dashboards via the Redash API — leave deep chart styling to the UI.
