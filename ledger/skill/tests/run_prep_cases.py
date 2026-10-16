"""Checks preps.key_of on real slips: which word the row belongs to, and the right preposition."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from preps import key_of
cases = json.load(open(os.path.join(os.path.dirname(__file__), "prep_cases.json")))
bad = 0
for q, f, k, r in cases:
    got = key_of(q, f)
    if got != (k, r): bad += 1; print("FAIL", q, "->", got, "expected", (k, r))
print(f"{len(cases)-bad} of {len(cases)} pass")
sys.exit(1 if bad else 0)
