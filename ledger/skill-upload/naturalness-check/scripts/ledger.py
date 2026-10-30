"""Save guard for Murat's Fluency Ledger (since 30.10.26).

The ledger's data lives in published files inside the ledger artifact (data/index.json,
data/meta/<name>.json, data/sessions/<id>.json, data/reading/<id>.json). A skill reads the files
it needs into a work folder at the same paths without "data/" (e.g. /tmp/nc/meta/pv_tracker.json),
and saves by publishing only the files that changed. This script makes that save safe.

  python3 ledger.py snapshot <workdir>
      Run right after reading. Copies what was read (index.json, meta/, sessions/, reading/)
      to <workdir>/_before/, the baseline every later check compares with, and prints the counts.

  python3 ledger.py stage <workdir> [--session <doc_id>] <target>=<file>[:merge][?] ...
      <target> is a ledger path without "data/" and ".json": meta/pv_tracker, sessions/<id>,
      reading/<id>. ":merge" lays the file's top-level fields over the read copy (for files that
      hold only the changed fields, like vocab-session's rows files). A trailing "?" marks a file
      that a step writes only sometimes: it is skipped when it doesn't exist. --session names the session
      being saved, so a rerun of the same chat may take back the prep_watch rows it added itself.
      Checks every file, refuses the whole save if any list would lose a row (or a row would lose
      a date or a review), adds new session/reading ids to index.json, and writes the files to
      publish under <workdir>/publish/data/. Prints "PUBLISH: ..." with the paths to publish, or
      "REFUSED: ..." (exit 1, nothing staged).
"""
import json, os, shutil, sys

PARTS = ("index.json", "meta", "sessions", "reading")
# list field, row key ("dict" = a keyed object): a save may never drop a row or a key
RULES = {
    "meta/pv_tracker": ("rows", "word"), "meta/vocab_tracker": ("rows", "id"),
    "meta/prep_watch": ("rows", "word"), "meta/interference": ("patterns", "key"),
    "meta/chunks": ("items", "id"), "meta/phave": ("items", "word"),
    "meta/vocab_items": ("items", "id"), "meta/lexicon": ("words", "dict"),
    "meta/registry": ("concepts", "dict"),
}
GROWING = {"meta/pv_tracker", "meta/vocab_tracker"}   # rows whose dates and reviews only ever grow


def load(p):
    d = json.load(open(p))
    return d.get("data", d) if isinstance(d, dict) and set(d) <= {"data", "version", "id"} else d


def snapshot(wd):
    b = os.path.join(wd, "_before")
    shutil.rmtree(b, ignore_errors=True); os.makedirs(b)
    if not os.path.exists(os.path.join(wd, "index.json")):
        sys.exit("REFUSED: index.json is missing. Read data/index.json first.")
    for p in PARTS:
        s = os.path.join(wd, p)
        if os.path.isdir(s): shutil.copytree(s, os.path.join(b, p))
        elif os.path.exists(s): shutil.copy(s, os.path.join(b, p))
    print("SNAPSHOT:", ", ".join(f"{t} {len(load(os.path.join(b, t + '.json'))[f])}"
                                 for t, (f, _) in RULES.items() if os.path.exists(os.path.join(b, t + ".json"))))


def keys(doc, field, key):
    v = doc.get(field)
    if key == "dict":
        if not isinstance(v, dict): raise ValueError(f"'{field}' is not an object")
        return {k: None for k in v}
    if not isinstance(v, list): raise ValueError(f"'{field}' is not a list")
    out = {}
    for r in v:
        k = r.get(key) if isinstance(r, dict) else None
        if k is None: raise ValueError(f"a row in '{field}' has no '{key}'")
        out[k] = r
    return out


def check(target, old, new, session, problems, lines):
    if not isinstance(new, dict): problems.append(f"{target}: not a JSON object"); return
    if target.startswith("sessions/") and not new.get("date"): problems.append(f"{target}: no 'date'")
    if target not in RULES or old is None: return
    field, key = RULES[target]
    try: o, n = keys(old, field, key), keys(new, field, key)
    except ValueError as e: problems.append(f"{target}: {e}"); return
    gone = [k for k in o if k not in n
            and not (target == "meta/prep_watch" and session and o[k].get("added") == session)]
    if gone: problems.append(f"{target}: {len(gone)} row(s) would be lost: {', '.join(map(str, gone[:8]))}")
    if target in GROWING:
        for k, r in o.items():
            m = n.get(k)
            if not m: continue
            if len(m.get("dates") or []) < len(r.get("dates") or []):
                problems.append(f"{target}: '{k}' would lose dates ({len(r['dates'])} -> {len(m.get('dates') or [])})")
            if ((m.get("practice") or {}).get("count") or 0) < ((r.get("practice") or {}).get("count") or 0):
                problems.append(f"{target}: '{k}' would lose reviews")
    lines.append(f"  {target} {field}: {len(o)} -> {len(n)}")


def stage(wd, args):
    session = None
    if "--session" in args:
        i = args.index("--session"); session = args[i + 1]; del args[i:i + 2]
    b = os.path.join(wd, "_before")
    if not os.path.exists(os.path.join(b, "index.json")):
        sys.exit("REFUSED: no snapshot. Run 'ledger.py snapshot' right after reading the files.")
    idx = load(os.path.join(b, "index.json")); idx0 = json.loads(json.dumps(idx))
    out_root = os.path.join(wd, "publish"); shutil.rmtree(out_root, ignore_errors=True)
    problems, lines, staged = [], [], {}
    for a in args:
        target, _, src = a.partition("=")
        optional = src.endswith("?"); src = src[:-1] if optional else src
        if optional and not os.path.exists(os.path.join(wd, src)): continue
        merge = src.endswith(":merge"); src = src[:-6] if merge else src
        target = target.strip().removeprefix("data/").removesuffix(".json")
        col = target.split("/")[0]
        if col not in ("meta", "sessions", "reading") or target.count("/") != 1:
            problems.append(f"{target}: not a ledger path (meta/<name>, sessions/<id>, reading/<id>)"); continue
        bp = os.path.join(b, target + ".json")
        old = load(bp) if os.path.exists(bp) else None
        if old is None and col == "meta" and target.split("/")[1] in idx.get("meta", []):
            problems.append(f"{target}: exists in the ledger but wasn't read; read it first"); continue
        if old is None and col == "sessions" and target.split("/")[1] in idx.get("sessions", []):
            problems.append(f"{target}: this session is already saved but wasn't read; read it first"); continue
        try: new = load(os.path.join(wd, src) if not os.path.isabs(src) else src)
        except Exception as e: problems.append(f"{target}: can't read {src} ({e})"); continue
        if merge:
            if old is None: problems.append(f"{target}: ':merge' needs the read copy"); continue
            new = {**old, **new}
        check(target, old, new, session, problems, lines)
        staged[target] = new
        ids = idx.setdefault(col, [])
        if target.split("/")[1] not in ids: ids.append(target.split("/")[1]); ids.sort()
    for col, ids in idx0.items():
        if isinstance(ids, list) and not set(ids) <= set(idx.get(col, [])): problems.append(f"index.json: {col} would lose ids")
    if not staged: problems.append("nothing to save")
    if problems:
        print("REFUSED: nothing was staged. Fix these, or tell Murat if a list really would shrink:")
        for p in problems: print("  - " + p)
        sys.exit(1)
    for target, doc in staged.items():
        p = os.path.join(out_root, "data", target + ".json"); os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(doc, open(p, "w"), ensure_ascii=False)
    paths = [f"data/{t}.json" for t in staged]
    if idx != idx0:
        json.dump(idx, open(os.path.join(out_root, "data", "index.json"), "w"), ensure_ascii=False, indent=1)
        paths.append("data/index.json")
    print("CHECKS PASSED (no list loses a row):"); print("\n".join(lines) if lines else "  (no tracker lists in this save)")
    print(f"PUBLISH: {len(paths)} file(s) from {out_root}: " + " ".join(paths))


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("snapshot", "stage"): sys.exit(__doc__)
    snapshot(sys.argv[2]) if sys.argv[1] == "snapshot" else stage(sys.argv[2], sys.argv[3:])
