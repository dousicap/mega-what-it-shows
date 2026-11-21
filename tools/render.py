"""Rendu de la page .svx telle que le desk la verra (layout runbook), sans exécuter le code du kb :
les composants Callout, ProblemSplit et RenderStamp sont réécrits ici à l'identique de leur logique.
Usage : python3 -I render.py <support-kb> <page.svx> <sortie.html> [AAAA-MM-JJ]"""
import sys, re, json, html, datetime, importlib.util
spec = importlib.util.spec_from_file_location('count', __file__.replace('render.py', 'count.py')); count = importlib.util.module_from_spec(spec); spec.loader.exec_module(count)
import glob

ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
def fnv1a(t, h):
    for ch in t: h = ((h ^ ord(ch)) * 0x01000193) & 0xFFFFFFFF
    return h
def desk_ref(sig):
    t = sig.strip(); bits = (fnv1a(t, 0x811C9DC5) << 8) | (fnv1a(t, 0x9E3779B9) & 0xFF); o = ''
    for _ in range(8): o = ALPHABET[bits & 31] + o; bits >>= 5
    return f'DR-{o[:4]}-{o[4:]}'
assert desk_ref('dousicap') == 'DR-16QP-YWFD'  # même valeur qu'une réécriture JS indépendante

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)

def problem_split(kb, ticket, issues):
    d = kb + '/src/lib/data'; R = json.load(open(d + '/reports-4471.json'))
    T = {t['handle']: t for t in (json.load(open(f)) for f in glob.glob(d + '/tenants/*.json'))}
    notes = set(json.load(open(d + '/desk-notes.json'))['oneDayMove'])
    res = count.classify([r for r in R if r['mergedInto'] == ticket], T, set())  # la vue du desk (causes.ts) : pas de retrait
    res['one-day-move'] = sorted(i for i in notes if any(i in v for v in res.values()))
    tenants = {r['id']: r['tenant'] for r in R}
    order = sorted([k for k in ('parser', 'hint', 'unplaced') if res[k]], key=lambda k: -len(res[k])) + (['one-day-move'] if res['one-day-move'] else [])
    total = sum(len(res[k]) for k in ('parser', 'hint', 'unplaced'))
    note = ''.join(f'<p class="note">{n} of the <code>{k}</code> reports read as a one-day move: filed under <code>{k}</code> by tenant, and counted again in <code>one-day-move</code>.</p>'
                   for k in order if k != 'one-day-move' for n in [len(set(res[k]) & set(res['one-day-move']))] if n)
    rows = ''.join(f'<tr><td><code>{k}</code></td><td>{len(res[k])}</td><td>{len({tenants[i] for i in res[k]})}</td><td>'
                   + (f'<a href="{issues[k]}">#{issues[k].split("/")[-1]}</a>' if k in issues else 'no ticket') + '</td></tr>' for k in order)
    return (f'<p class="sum"><strong>{total}</strong> reports merged into #{ticket} · <strong>{len(order)}</strong> {"problem" if len(order) == 1 else "problems"}</p>'
            '<table><thead><tr><th>problem</th><th>reports</th><th>tenants</th><th>ticket</th></tr></thead><tbody>' + rows + '</tbody></table>' + note)

def render(kb, svx, today):
    src = open(svx).read()
    fm, body = re.match(r'---\n(.*?)\n---\n(.*)', src, re.S).groups()
    meta = {k: v.strip().strip("'") for k, v in re.findall(r'^(\w+):\s*(.*)$', fm, re.M)}
    for k in ('title', 'owner', 'status', 'reviewed', 'signature'): assert meta.get(k), f'frontmatter sans {k}'
    body = re.sub(r'<script>.*?</script>', '', body, flags=re.S)
    assert body.rstrip().endswith('<RenderStamp {signature} />'), 'la page ne finit pas par RenderStamp'
    out = []
    for blk in re.split(r'\n\s*\n', body.strip()):
        if blk.startswith('<ProblemSplit'):
            issues = dict(re.findall(r"'?([\w-]+)'?:\s*'([^']+)'", blk)); out.append(problem_split(kb, int(re.search(r'ticket=\{(\d+)\}', blk)[1]), issues))
        elif blk.startswith('<Callout'):
            kind = re.search(r'kind="(\w+)"', blk); out.append(f'<aside class="{kind[1] if kind else "note"}">{inline(re.sub(r"</?Callout[^>]*>", "", blk).strip())}</aside>')
        elif blk.startswith('<RenderStamp'):
            out.append(f'<p class="stamp">desk ref <b>{desk_ref(meta["signature"])}</b></p>')
        elif blk.startswith('## '): out.append(f'<h2>{inline(blk[3:])}</h2>')
        elif blk.startswith('- '): out.append('<ul>' + ''.join(f'<li>{inline(" ".join(i.split()))}</li>' for i in re.split(r'\n- ', blk[2:])) + '</ul>')
        else: out.append(f'<p>{inline(" ".join(blk.split()))}</p>')
    age = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(meta['reviewed'])).days
    stale = age > 180
    layout = open(kb + '/src/lib/layouts/runbook.svelte').read()
    css = re.search(r'<style>(.*?)</style>', layout, re.S)[1]
    css = re.sub(r':global\(([^()]*)\)', r'\1', css)
    css += '.sum{font-size:1.1rem}aside{border-left:4px solid var(--accent);padding:.5rem 1rem;margin:1rem 0;background:var(--note-bg)}aside.warn{border-color:var(--warn);background:var(--warn-bg)}.stamp{margin:2rem 0 0;font:.85rem var(--mono);color:var(--muted)}.stamp b{color:var(--accent);letter-spacing:.04em}.note{color:var(--muted);font-size:.85em}'
    e = html.escape
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{e(meta["title"])} · support kb</title><style>{css}</style></head><body><div class="kb">'
            f'<header><a class="crumb" href="/kb">support desk · kb</a><h1>{e(meta["title"])}</h1><p class="meta"><span>owner <b>{e(meta["owner"])}</b></span>'
            f'<span class="status {e(meta["status"])}">{e(meta["status"])}</span><span class="{"stale" if stale else ""}">reviewed {meta["reviewed"]} · {age} days ago{" · stale" if stale else ""}</span></p></header>'
            + (f'<p class="banner">Nobody has re-read this page in {age} days. Check it against the live views before you rely on it.</p>' if stale else '')
            + '<main>' + '\n'.join(out) + '</main><footer>Pages are written by people. Tables and charts are built from data at render time.</footer></div></body></html>')

if __name__ == '__main__':
    kb, svx, dst = sys.argv[1:4]; today = sys.argv[4] if len(sys.argv) > 4 else datetime.date.today().isoformat()
    open(dst, 'w').write(render(kb, svx, today)); print('écrit', dst)
