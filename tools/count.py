"""Compte les signalements de #4471 par problème. Lit le kb exporté comme donnée (rien de kb/ n'est exécuté).
Règle reprise de kb/.../causes.ts : tenant day-first + canal form + booking-v3 -> hint, sinon parser.
En plus : les rapports de desk-notes.oneDayMove (décalage d'un jour, pas d'inversion jour/mois) sortent de parser.
Usage : python3 -I count.py <dossier support-kb> [dossier de sortie]"""
import json, glob, re, sys, os

MONTHS = {m: i + 1 for i, m in enumerate('January February March April May June July August September October November December'.split())}
DAY_FIRST = {'de-DE', 'es-ES', 'en-GB', 'nl-NL', 'cs-CZ', 'it-IT', 'fr-FR', 'pl-PL', 'pt-PT', 'da-DK', 'en-IE'}  # vérifié avec Intl (Node) le 2026-11-21

def is_swap(body):
    ds = [(int(d), MONTHS[m]) for d, m in re.findall(r'(\d{1,2}) (' + '|'.join(MONTHS) + ')', body)]
    return len(ds) == 2 and ds[0] == (ds[1][1], ds[1][0])

def classify(reports, tenants, one_day):
    out = {'parser': [], 'hint': [], 'one-day-move': [], 'unplaced': []}
    for r in {r['id']: r for r in reports}.values():  # pages d'export qui se recouvrent : un id, un rapport
        if r['mergedInto'] != 4471: continue
        t = tenants.get(r['tenant'])
        if not t or t['locale'] not in DAY_FIRST: k = 'unplaced'
        elif r['id'] in one_day: k = 'one-day-move'
        elif r['channel'] == 'form' and t['form'] == 'booking-v3': k = 'hint'
        else: k = 'parser'
        out[k].append(r['id'])
    return {k: sorted(v) for k, v in out.items()}

def selftest():
    T = {'a': {'locale': 'de-DE', 'form': 'booking-v3'}, 'b': {'locale': 'fr-FR', 'form': 'booking-v2'}}
    R = [dict(id='1', tenant='a', channel='form', mergedInto=4471), dict(id='1', tenant='a', channel='form', mergedInto=4471),
         dict(id='2', tenant='a', channel='app', mergedInto=4471), dict(id='3', tenant='b', channel='form', mergedInto=4471),
         dict(id='4', tenant='x', channel='app', mergedInto=4471), dict(id='5', tenant='b', channel='email', mergedInto=4471),
         dict(id='6', tenant='b', channel='app', mergedInto=9)]
    assert classify(R, T, {'5'}) == {'parser': ['2', '3'], 'hint': ['1'], 'one-day-move': ['5'], 'unplaced': ['4']}
    assert is_swap('Booked for 2 July. The invite says 7 February.') and not is_swap('Invite says Tuesday 12 May. Calendar says Monday 11 May.')

if __name__ == '__main__':
    selftest()
    kb = sys.argv[1]; d = kb + '/src/lib/data'
    reports = json.load(open(d + '/reports-4471.json'))
    tenants = {t['handle']: t for t in (json.load(open(f)) for f in glob.glob(d + '/tenants/*.json'))}
    one_day = set(json.load(open(d + '/desk-notes.json'))['oneDayMove'])
    res = classify(reports, tenants, one_day)
    body = {r['id']: r['body'] for r in reports}
    assert all(not is_swap(body[i]) for i in res['one-day-move']), 'un oneDayMove décrit une inversion'
    total = sum(map(len, res.values()))
    print(f'lignes {len(reports)}, uniques {total}')
    for k, v in res.items(): print(f'{k}: {len(v)}')
    print('non-inversions hors oneDayMove :', [i for i in res['parser'] + res['hint'] if not is_swap(body[i])])
    if len(sys.argv) > 2:
        os.makedirs(sys.argv[2], exist_ok=True)
        for k, v in res.items():
            if v: open(f'{sys.argv[2]}/{k}.txt', 'w').write('\n'.join(v) + '\n')
