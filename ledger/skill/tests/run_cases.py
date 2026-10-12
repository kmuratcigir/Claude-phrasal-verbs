import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import chunks
cases = json.load(open(os.path.join(os.path.dirname(__file__), 'cases.json')))
bad = 0
for sent, item, want in cases:
    found = chunks.FINDERS[item](chunks.clean(sent))
    got = (found[0]["suggest"] if found[0]["suggest"] is not None else "decide") if found else None
    flag = "ok " if got == want else "BAD"
    if got != want: bad += 1
    print(f"{flag} {item} want={want!s:5} got={got!s:5} | {sent}")
print(f"\n{len(cases)-bad}/{len(cases)} correct")
sys.exit(1 if bad else 0)
