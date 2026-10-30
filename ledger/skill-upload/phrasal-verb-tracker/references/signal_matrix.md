# Overall Signal lookup matrix

For sanity-checking `recalc.py`'s output by eye. This is never assigned by judgment —
always this fixed lookup of Mastery Status × Recency Status:

| Mastery \ Recency | Green                | Yellow             | Red                        |
|--------------------|-----------------------|---------------------|-----------------------------|
| Activated          | Solid & Active         | Solid but Cooling   | Fading Despite Strong Base |
| In Progress        | Building Momentum      | Stalling            | At Risk                    |
| Emerging           | Fresh Start            | Early Fade          | Lost Spark                 |
| Not Yet Observed   | —                      | —                   | Untested (no dates → blank Recency, so this cell doesn't actually occur) |

Mastery bands (from Come-up Count):
- 0 → Not Yet Observed
- 1–2 → Emerging
- 3–5 → In Progress
- 6+ → Activated

Recency bands (from days elapsed since the most recent Come-up Date, vs. today):
- ≤7 days → Green
- 8–14 days → Yellow
- 15+ days → Red
- No dates yet → blank / not applicable
