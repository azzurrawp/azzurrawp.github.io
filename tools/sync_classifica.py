"""Aggiorna classifica.json con classifica e risultati ufficiali del girone dell'Azzurra.

uso: python3 tools/sync_classifica.py [classifica.json]

Fonte: FIN Comitato Regionale Toscano, settore Pallanuoto, campionato regionale Allievi
(pagina pubblica https://www.federnuoto.toscana.it/Pallanuoto/Index_Pallanuoto.asp).
Una sola lettura per esecuzione. Sono dati pubblici di squadra: nessun nome di atleta.
Se la lettura fallisce o i dati sono incompleti il file esistente non viene toccato.
"""
import sys, re, json, html, datetime, urllib.request, urllib.parse

BASE = 'https://ac.1x2db.it/framer_s_lib/common/1x2-php/'
CHAMP = '177'  # Allievi 1a Fase gir B
NAME = 'Allievi 1ª fase · girone B'
SRC = 'https://www.federnuoto.toscana.it/Pallanuoto/Index_Pallanuoto.asp'
MESI = {m: i + 1 for i, m in enumerate('gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre'.split())}


def post(page):
    req = urllib.request.Request(BASE + page, data=urllib.parse.urlencode({'champ': CHAMP}).encode(),
                                 headers={'User-Agent': 'Mozilla/5.0 (AzzurraWPStat; lettura classifica 1 volta per giornata)',
                                          'Referer': 'https://ac.1x2db.it/framer/fintos-cat-Allievi/frame.html'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode('utf-8', 'replace').lstrip('﻿')


def txt(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s)).replace("\\'", "'").strip()


def parse_table(h):
    out = []
    for row in re.findall(r'<tr>(.*?)</tr>', h, re.S):
        c = [txt(x) for x in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S)]
        if len(c) >= 10 and c[0].isdigit():
            # sito: Pos Squadra Pti V P N G Gf Gs Dr  (P = perse, N = pareggi)
            out.append({'pos': int(c[0]), 'team': c[1], 'pt': int(c[2]), 'v': int(c[3]), 'p': int(c[4]), 'n': int(c[5]),
                        'g': int(c[6]), 'gf': int(c[7]), 'gs': int(c[8]), 'dr': int(c[9])})
    return out


def parse_days(h):
    days, cur = [], None
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        d = re.search(r'match-head-day"><strong>\s*(\d+)', row)
        if d:
            cur = {'n': int(d.group(1)), 'm': []}
            days.append(cur)
            continue
        m = re.search(r'match_datelocation">(.*?)</div>\s*<strong>(.*?)</strong>.*?class="score">(.*?)</td>', row, re.S)
        if not m or cur is None:
            continue
        dl, teams, sc = txt(m.group(1)), txt(m.group(2)), txt(m.group(3))
        when, _, place = dl.partition(' - ')
        w = re.match(r'(\d{1,2}) (\w+) (\d{4})(?: (\d{1,2}):(\d{2}))?', when)
        date = time = ''
        if w and w.group(2).lower() in MESI:
            date = '%s-%02d-%02d' % (w.group(3), MESI[w.group(2).lower()], int(w.group(1)))
            if w.group(4):
                time = '%02d:%s' % (int(w.group(4)), w.group(5))
        home, _, away = teams.partition(' - ')
        s = re.match(r'(\d+)\s*-\s*(\d+)$', sc)
        cur['m'].append({'date': date, 'time': time, 'place': place.strip(), 'home': home.strip(), 'away': away.strip(),
                         'sh': int(s.group(1)) if s else None, 'sa': int(s.group(2)) if s else None})
    return [d for d in days if d['m']]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'classifica.json'
    table, days = parse_table(post('generaClassifica.php')), parse_days(post('generaCalendario.php'))
    if len(table) < 4 or not days or not any('azzurra' in t['team'].lower() for t in table):
        print('LETTURA INCOMPLETA: classifica.json non modificato (%d squadre, %d giornate)' % (len(table), len(days)))
        sys.exit(1)
    try:
        old = json.load(open(out, encoding='utf-8'))
    except Exception:
        old = {}
    same = old.get('table') == table and old.get('days') == days
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    D = {'name': NAME, 'src': SRC, 'chk': now, 'upd': old.get('upd', now) if same else now, 'table': table, 'days': days}
    json.dump(D, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(('NESSUNA VARIAZIONE' if same else 'CLASSIFICA AGGIORNATA') + ': %d squadre, %d giornate' % (len(table), len(days)))


if __name__ == '__main__':
    main()
