"""Rebuild the Prepositions & Collocations quiz page from src/.
Usage: python3 prep-quiz/build.py  ->  writes prep-quiz/prep-quiz.html (publish that file to the artifact URL)."""
import os
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
r = lambda f: open(os.path.join(d, f), encoding='utf-8').read()
html = r('template.html').replace('/*__STATS__*/', r('stats.js') + r('stats_adv.js')).replace('/*__BANK__*/', r('bank.js') + r('bank_adv.js'))
out = os.path.join(os.path.dirname(d), 'prep-quiz.html')
open(out, 'w', encoding='utf-8').write(html)
print('wrote', out, len(html), 'bytes')
