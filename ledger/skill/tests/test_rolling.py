"""Rolling settled rule: 12 voice uses, 80%+, over 4+ sessions."""
import json, os, subprocess, sys, tempfile
here = os.path.dirname(os.path.abspath(__file__))
meta = {"rule": {"target": 0.8, "window_uses": 12, "min_sessions": 4}, "items": [{"id": "c1", "status": "open"}]}
def run(per_session):            # list of lists of ok-flags, oldest first
    d = tempfile.mkdtemp(); os.mkdir(os.path.join(d, "sessions"))
    for i, oks in enumerate(per_session[:-1]):
        doc = {"chunks": {"c1": {"items": [{"mode": "voice", "ok": o, "caught": False} for o in oks]}}}
        json.dump(doc, open(os.path.join(d, "sessions", f"s_202610{10+i:02d}_x.json"), "w"))
    cur = {"chunks": {"c1": {"items": [{"mode": "voice", "ok": o, "caught": False} for o in per_session[-1]]}}}
    json.dump(cur, open(os.path.join(d, "session_doc.json"), "w")); json.dump(meta, open(os.path.join(d, "meta.json"), "w"))
    env = dict(os.environ, DOC_ID="s_20261031_cur")
    return subprocess.run([sys.executable, os.path.join(here, "..", "chunks.py"), "rolling", os.path.join(d, "sessions"),
                           os.path.join(d, "session_doc.json"), os.path.join(d, "meta.json")], capture_output=True, text=True, env=env).stdout
T, F = True, False
cases = [
 ("12 right over 4 sessions", [[T]*3, [T]*3, [T]*3, [T]*3], True),
 ("12 right but only 3 sessions", [[T]*4, [T]*4, [T]*4], False),
 ("only 11 uses", [[T]*3, [T]*3, [T]*3, [T]*2], False),
 ("10 of 12 right (83%)", [[T,F,T], [T]*3, [T,F,T], [T]*3], True),
 ("9 of 12 right (75%)", [[F,F,T], [T]*3, [T,F,T], [T]*3], False),
 ("old misses drop out of the window", [[F]*5, [T]*3, [T]*3, [T]*3, [T]*3], True),
]
bad = 0
for name, sessions, want in cases:
    got = "SUGGEST SETTLED" in run(sessions)
    print(("ok " if got == want else "BAD"), name, "->", got); bad += got != want
print(f"{len(cases)-bad}/{len(cases)} correct"); sys.exit(1 if bad else 0)
