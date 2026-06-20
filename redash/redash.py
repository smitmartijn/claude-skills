#!/usr/bin/env python3
"""Zero-dependency Redash API client (Python stdlib only).

Auth via environment variables:
  REDASH_URL      e.g. https://redash.example.com   (no trailing slash needed)
  REDASH_API_KEY  a user API key (Settings → Account) — needed for create/update.
                  A per-query API key only works for reading that one query's results.

Every command prints JSON to stdout so the calling agent can parse it.
Errors print to stderr and exit non-zero.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _cfg():
    url = os.environ.get("REDASH_URL", "").rstrip("/")
    key = os.environ.get("REDASH_API_KEY", "")
    if not url or not key:
        sys.exit("ERROR: set REDASH_URL and REDASH_API_KEY environment variables")
    return url, key


def _req(method, path, body=None):
    url, key = _cfg()
    full = url + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(full, data=data, method=method)
    req.add_header("Authorization", "Key " + key)
    req.add_header("Content-Type", "application/json")
    # Some instances sit behind Cloudflare/WAFs that ban the default
    # "Python-urllib" agent (Cloudflare error 1010). Send a normal UA.
    req.add_header("User-Agent", os.environ.get("REDASH_USER_AGENT", "redash-skill/1.0"))
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:1000]
        sys.exit("HTTP %s on %s %s\n%s" % (e.code, method, path, detail))
    except urllib.error.URLError as e:
        sys.exit("Connection error to %s: %s" % (full, e.reason))


def _out(obj):
    print(json.dumps(obj, indent=2, default=str))


def _parse_opts(s):
    if not s:
        return {}
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        sys.exit("--options is not valid JSON: %s" % e)


# ---- result polling -------------------------------------------------------

def _poll(job):
    """Block until a job finishes; return its query_result_id or exit on failure."""
    while job["status"] not in (3, 4):
        time.sleep(1)
        job = _req("GET", "/api/jobs/%s" % job["id"])["job"]
    if job["status"] == 4:
        sys.exit("Query execution failed: %s" % job.get("error", "unknown error"))
    return job["query_result_id"]


# ---- commands -------------------------------------------------------------

def cmd_test(a):
    _out(_req("GET", "/api/session"))


def cmd_data_sources(a):
    _out(_req("GET", "/api/data_sources"))


def cmd_schema(a):
    # On a cold cache the endpoint returns a refresh {"job": ...}; once warm it
    # returns {"schema": [...]}. Poll the job (if any), then re-fetch the schema.
    path = "/api/data_sources/%s/schema" % a.data_source_id
    res = _req("GET", path)
    job = res.get("job")
    if job:
        while job["status"] not in (3, 4):
            time.sleep(1)
            job = _req("GET", "/api/jobs/%s" % job["id"])["job"]
        res = _req("GET", path)
    _out(res.get("schema", res))


def cmd_exec_sql(a):
    """Run ad-hoc SQL without saving a query. Returns columns + rows."""
    body = {"query": a.sql, "data_source_id": int(a.data_source_id), "max_age": a.max_age}
    res = _req("POST", "/api/query_results", body)
    if "query_result" in res:
        _out(res["query_result"]["data"])
        return
    result_id = _poll(res["job"])
    qr = _req("GET", "/api/query_results/%s.json" % result_id)
    _out(qr["query_result"]["data"])


def cmd_create_query(a):
    body = {
        "name": a.name,
        "query": a.sql,
        "data_source_id": int(a.data_source_id),
        "options": _parse_opts(a.options) or {"parameters": []},
    }
    if a.description:
        body["description"] = a.description
    res = _req("POST", "/api/queries", body)
    if a.publish:
        res = _req("POST", "/api/queries/%s" % res["id"], {"is_draft": False})
    _out(res)


def cmd_update_query(a):
    body = {}
    if a.name is not None:
        body["name"] = a.name
    if a.sql is not None:
        body["query"] = a.sql
    if a.options is not None:
        body["options"] = _parse_opts(a.options)
    if a.publish:
        body["is_draft"] = False
    if not body:
        sys.exit("update-query: nothing to update")
    _out(_req("POST", "/api/queries/%s" % a.id, body))


def cmd_get_query(a):
    _out(_req("GET", "/api/queries/%s" % a.id))


def cmd_run_query(a):
    """Execute a saved query and return its result rows."""
    res = _req("POST", "/api/queries/%s/results" % a.id, {"max_age": a.max_age})
    if "query_result" in res:
        _out(res["query_result"]["data"])
        return
    result_id = _poll(res["job"])
    qr = _req("GET", "/api/queries/%s/results/%s.json" % (a.id, result_id))
    _out(qr["query_result"]["data"])


def cmd_create_viz(a):
    body = {
        "query_id": int(a.query_id),
        "type": a.type,
        "name": a.name,
        "options": _parse_opts(a.options),
    }
    if a.description:
        body["description"] = a.description
    _out(_req("POST", "/api/visualizations", body))


def cmd_create_dashboard(a):
    _out(_req("POST", "/api/dashboards", {"name": a.name}))


def cmd_add_widget(a):
    position = {
        "col": a.col,
        "row": a.row,
        "sizeX": a.size_x,
        "sizeY": a.size_y,
        "autoHeight": False,
    }
    body = {
        "dashboard_id": int(a.dashboard_id),
        "visualization_id": int(a.viz_id) if a.viz_id else None,
        "text": a.text or "",
        "width": 1,
        "options": {"position": position},
    }
    _out(_req("POST", "/api/widgets", body))


def cmd_publish_dashboard(a):
    _out(_req("POST", "/api/dashboards/%s" % a.id, {"is_draft": False}))


def cmd_dashboards(a):
    res = _req("GET", "/api/dashboards?page_size=250")
    rows = res.get("results", res)
    _out([{"id": d["id"], "slug": d.get("slug"), "name": d["name"],
           "is_draft": d.get("is_draft"), "is_archived": d.get("is_archived")} for d in rows])


def cmd_get_dashboard(a):
    # 26.x resolves dashboards by numeric id only; a slug here 500s. Use `dashboards` to find the id.
    _out(_req("GET", "/api/dashboards/%s" % a.id))


def cmd_delete_query(a):
    _req("DELETE", "/api/queries/%s" % a.id)
    _out({"archived_query": a.id})


def cmd_delete_dashboard(a):
    _req("DELETE", "/api/dashboards/%s" % a.id)
    _out({"archived_dashboard": a.id})


def main():
    p = argparse.ArgumentParser(description="Minimal Redash API client")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("test", help="verify URL + API key (GET /api/session)").set_defaults(fn=cmd_test)
    sub.add_parser("data-sources", help="list data sources with their ids").set_defaults(fn=cmd_data_sources)
    sub.add_parser("dashboards", help="list dashboards (id, slug, name) — use to resolve a slug to its id").set_defaults(fn=cmd_dashboards)

    s = sub.add_parser("schema", help="list tables/columns for a data source")
    s.add_argument("--data-source-id", required=True)
    s.set_defaults(fn=cmd_schema)

    s = sub.add_parser("exec-sql", help="run ad-hoc SQL (not saved); returns rows")
    s.add_argument("--data-source-id", required=True)
    s.add_argument("--sql", required=True)
    s.add_argument("--max-age", type=int, default=0, help="0 = always fresh")
    s.set_defaults(fn=cmd_exec_sql)

    s = sub.add_parser("create-query", help="create a saved query")
    s.add_argument("--name", required=True)
    s.add_argument("--sql", required=True)
    s.add_argument("--data-source-id", required=True)
    s.add_argument("--description")
    s.add_argument("--options", help="JSON; defaults to {\"parameters\": []}")
    s.add_argument("--publish", action="store_true", help="publish (clear is_draft)")
    s.set_defaults(fn=cmd_create_query)

    s = sub.add_parser("update-query", help="update fields of an existing query")
    s.add_argument("--id", required=True)
    s.add_argument("--name")
    s.add_argument("--sql")
    s.add_argument("--options")
    s.add_argument("--publish", action="store_true")
    s.set_defaults(fn=cmd_update_query)

    s = sub.add_parser("get-query", help="fetch a query object (incl. its visualizations)")
    s.add_argument("--id", required=True)
    s.set_defaults(fn=cmd_get_query)

    s = sub.add_parser("run-query", help="execute a saved query, return rows")
    s.add_argument("--id", required=True)
    s.add_argument("--max-age", type=int, default=0)
    s.set_defaults(fn=cmd_run_query)

    s = sub.add_parser("create-viz", help="create a visualization on a query")
    s.add_argument("--query-id", required=True)
    s.add_argument("--type", required=True, help="TABLE | CHART | COUNTER | PIVOT | BOXPLOT | MAP | WORD_CLOUD | FUNNEL")
    s.add_argument("--name", required=True)
    s.add_argument("--description")
    s.add_argument("--options", help="JSON viz options (see SKILL.md)")
    s.set_defaults(fn=cmd_create_viz)

    s = sub.add_parser("create-dashboard", help="create an (empty, draft) dashboard")
    s.add_argument("--name", required=True)
    s.set_defaults(fn=cmd_create_dashboard)

    s = sub.add_parser("add-widget", help="add a visualization (or text) widget to a dashboard")
    s.add_argument("--dashboard-id", required=True)
    s.add_argument("--viz-id", help="omit for a text-only widget")
    s.add_argument("--text", help="markdown text for a text widget")
    s.add_argument("--col", type=int, default=0, help="grid column 0-5 (grid is 6 wide)")
    s.add_argument("--row", type=int, default=0)
    s.add_argument("--size-x", type=int, default=3, help="width in grid cols (1-6)")
    s.add_argument("--size-y", type=int, default=8, help="height in grid rows")
    s.set_defaults(fn=cmd_add_widget)

    s = sub.add_parser("publish-dashboard", help="clear is_draft so the dashboard is visible")
    s.add_argument("--id", required=True)
    s.set_defaults(fn=cmd_publish_dashboard)

    s = sub.add_parser("get-dashboard", help="fetch a dashboard by id (preferred) or slug")
    s.add_argument("--id", required=True, help="numeric id (reliable) or slug")
    s.set_defaults(fn=cmd_get_dashboard)

    s = sub.add_parser("delete-query", help="archive a query")
    s.add_argument("--id", required=True)
    s.set_defaults(fn=cmd_delete_query)

    s = sub.add_parser("delete-dashboard", help="archive a dashboard")
    s.add_argument("--id", required=True)
    s.set_defaults(fn=cmd_delete_dashboard)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
