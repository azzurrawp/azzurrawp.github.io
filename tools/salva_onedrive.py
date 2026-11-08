"""Scarica stats.enc dal sito, lo decifra con il codice squadra e crea i file Excel.
uso: python3 salva_onedrive.py CODICE CARTELLA_USCITA [file_stats.enc]"""
import sys, json, base64, os, urllib.request, datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

pin, out = sys.argv[1], sys.argv[2]
src = sys.argv[3] if len(sys.argv) > 3 else None
raw = open(src).read() if src else urllib.request.urlopen('https://azzurrawp.github.io/stats.enc?t=%d' % datetime.datetime.now().timestamp()).read().decode()
o = json.loads(raw); b = base64.b64decode
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=b(o['salt']), iterations=o['it']).derive(pin.encode())
data = json.loads(AESGCM(key).decrypt(b(o['iv']), b(o['data']), None))
ms = sorted([m for m in data['matches'] if m.get('log')], key=lambda m: (m.get('date', ''), m.get('time', '')))
LBL = {'g':'Gol','gu':'Gol UP','a':'Assist','au':'Assist UP','e':'Espuls.','x':'Espuls. avv','og':'Gol avv','ogu':'Gol avv UP'}
N = 15
def score(m): return sum(m['g'])+sum(m['gu']), m['og']+m['ogu']
def res(m):
    a, c = score(m); o_ = m.get('opp', '')
    return f"Azzurra {a}-{c} {o_}"   # sempre Azzurra prima; casa/trasferta in colonna a parte
def base(m):
    a, c = score(m); g = (m.get('gio','') or '').replace('ª','a')
    t = f"Azzurra U16 - {m.get('date','')}" + (f" - {g}" if g else '') + f" - vs {m.get('opp','')} ({'casa' if m.get('home') else 'trasferta'}) {a}-{c}" + ('' if m.get('done') else ' in corso')
    return ''.join('-' if ch in '\\/:*?"<>|' else ch for ch in t)
def parz(m):
    r = []
    for p in range(1, 5):
        a = sum(1 for e in m['log'] if e[2] == p and e[0] in ('g', 'gu')); c = sum(1 for e in m['log'] if e[2] == p and e[0] in ('og', 'ogu'))
        r.append(f"{a}-{c}")
    return ' / '.join(r)
H_P = ['Giornata','Data','Ora','Casa/Trasferta','Avversario','Piscina','Risultato','Parziali','Gol Azzurra','Gol avversari','Gol Azzurra in sup.','Gol avv. in sup.','Espulsioni Azzurra','Espulsioni avv.','Stato']
H_G = ['Calotta','Giocatore','Gol','di cui in sup.','Assist','di cui in sup.','Espulsioni']
H_E = ['Tempo','Ora','Evento','Calotta','Giocatore']
def prow(m):
    a, c = score(m)
    return [m.get('gio',''), m.get('date',''), m.get('time',''), 'Casa' if m.get('home') else 'Trasferta', m.get('opp',''), m.get('place',''), res(m), parz(m), a, c, sum(m['gu']), m['ogu'], sum(m['e']), sum(m['x']), 'Conclusa' if m.get('done') else 'In corso']
def grows(m):
    return [[i+1, m['names'][i] or f'Calotta {i+1}', m['g'][i]+m['gu'][i], m['gu'][i], m['a'][i]+m['au'][i], m['au'][i], m['e'][i]] for i in range(N) if m['names'][i] or m['g'][i] or m['gu'][i] or m['a'][i] or m['au'][i] or m['e'][i]]
def erows(m):
    r = []
    for e in m['log']:
        t = datetime.datetime.fromtimestamp(e[3]/1000).strftime('%H:%M:%S')
        c = e[1]+1 if e[1] >= 0 else ''
        nm = '' if e[0] in ('x','og','ogu') else m['names'][e[1]]
        r.append([f"{e[2]}T", t, LBL[e[0]], c, nm])
    return r
HF = Font(bold=True, color='FFFFFF'); HB = PatternFill('solid', fgColor='0B3D91')
def sheet(wb, name, head, rows, first=False):
    ws = wb.active if first else wb.create_sheet(name); ws.title = name
    ws.append(head)
    for c in ws[1]: c.font = HF; c.fill = HB; c.alignment = Alignment(horizontal='center', wrap_text=True)
    for r in rows: ws.append(r)
    for col in ws.columns:
        w = max(len(str(c.value or '')) for c in col); ws.column_dimensions[col[0].column_letter].width = min(max(8, w + 2), 40)
    ws.freeze_panes = 'A2'
os.makedirs(out, exist_ok=True); saved = []
# un file per ogni partita conclusa
for m in ms:
    if not m.get('done'): continue
    wb = Workbook()
    sheet(wb, 'Partita', H_P, [prow(m)], True); sheet(wb, 'Giocatori', H_G, grows(m)); sheet(wb, 'Eventi', H_E, erows(m))
    fn = base(m) + ' - Dati.xlsx'
    wb.save(os.path.join(out, fn)); saved.append(fn)
# riepilogo di stagione
T = {}
for m in ms:
    for r in grows(m):
        t = T.setdefault(r[1], [r[1], 0, 0, 0, 0, 0, 0]); t[1] += 1
        for k in range(2, 7): t[k] += r[k]
tot = sorted(T.values(), key=lambda t: (-t[2], -t[4]))
wb = Workbook()
sheet(wb, 'Totali stagione', ['Giocatore','Partite','Gol','di cui in sup.','Assist','di cui in sup.','Espulsioni'], tot, True)
sheet(wb, 'Partite', H_P, [prow(m) for m in ms])
ws = wb.create_sheet('Giocatori per partita'); ws.append(['Data','Avversario']+H_G)
for c in ws[1]: c.font = HF; c.fill = HB
for m in ms:
    for r in grows(m): ws.append([m.get('date',''), m.get('opp','')]+r)
fn = 'Azzurra U16 - Stagione 2026-27 - Dati (aggiornati).xlsx'; wb.save(os.path.join(out, fn)); saved.append(fn)
print(json.dumps({'partite': len(ms), 'concluse': sum(1 for m in ms if m.get('done')), 'file': saved}, ensure_ascii=False))
