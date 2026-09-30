# vocab-session: one save instead of two (30.09.26)

Only SKILL.md Step 5 changes. record.py and every other script stay as they are.

Replace this paragraph in Step 5:

> Then write back only the changed list(s) named on its `WRITE:` line:
> `ArtifactData` `update` `meta/vocab_tracker` with `file_path: /tmp/vs/vocab_rows.json`, and/or
> `update` `meta/pv_tracker` with `file_path: /tmp/vs/pv_rows.json`, each with `if_version` from
> Step 2. If a write is refused because the version changed, fetch that list again, rerun record.py
> and write again.

with:

> Then save the changed list(s) named on its `WRITE:` line in ONE `ArtifactData` `batch` call, so
> Murat approves once. One `update` entry per list named there:
> `{"op": "update", "collection": "meta", "doc_id": "vocab_tracker", "file_path": "/tmp/vs/vocab_rows.json", "if_version": <vocab_tracker version from Step 2>}`
> and/or
> `{"op": "update", "collection": "meta", "doc_id": "pv_tracker", "file_path": "/tmp/vs/pv_rows.json", "if_version": <pv_tracker version from Step 2>}`.
> Never split this into two separate writes. If `WRITE:` names no list, don't save anything.
> If the batch is refused because a version changed, nothing was saved: fetch both lists again
> (with `out_dir: /tmp/vs`), rerun record.py on the fresh files and send the batch again with the
> new versions. (A word already recorded today is skipped, so a rerun never counts twice.)

Tested 30.09 on copies of the live lists (nothing written): record.py changed only the practised
rows; the two files together are about 134 KB, well under the 1 MiB batch limit.
