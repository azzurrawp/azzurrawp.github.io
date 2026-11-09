"""Aggiorna distinte.enc dalle distinte Word (.docx) della cartella OneDrive "Distinte".

uso: python3 sync_distinte.py CODICE CARTELLA_DOCX distinte.enc [--dry]

- Legge ogni "Distinta U16 <n>a giornata - DD.MM hHH.MM Casa - Trasferta (Città, piscina ...).docx"
- Per ogni giornata aggiorna data, ora, casa/trasferta, avversario, piscina e i 15 nomi.
- Le partite già registrate (con log) non vengono toccate: solo segnalate.
- Riscrive distinte.enc cifrato con il codice squadra (AES-GCM, PBKDF2 310000).
- Stampa un riepilogo delle modifiche. Con --dry non scrive nulla.
Nessun nome è contenuto in questo file: i nomi stanno solo nei .docx privati e nel .enc cifrato.
"""
import sys, os, re, json, glob, base64, datetime
import docx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

IT = 310000
TEAM = re.compile(r'azzurra', re.I)


def kdf(pin, salt, it=IT):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=it).derive(pin.encode())


def dec(path, pin):
    o = json.load(open(path)); b = base64.b64decode
    return json.loads(AESGCM(kdf(pin, b(o['salt']), o['it'])).decrypt(b(o['iv']), b(o['data']), None))


def enc(obj, pin, path):
    data = json.dumps(obj, ensure_ascii=False, separators=(',', ':')).encode()
    salt = os.urandom(16); iv = os.urandom(12)
    ct = AESGCM(kdf(pin, salt)).encrypt(iv, data, None)
    b = lambda x: base64.b64encode(x).decode()
    json.dump({"v": 1, "it": IT, "salt": b(salt), "iv": b(iv), "data": b(ct)}, open(path, 'w'))


def short(full, role):
    p = full.split()
    if len(p) < 2:
        n = full.strip()
    else:
        # cognome = tutte le parole iniziali con maiuscola tranne l'ultima parte che è il nome;
        # i doppi cognomi (De Crescenzo, Di Fronzo) restano interi: il nome è la prima parola dopo il cognome.
        # Regola: nome = prima parola dopo il cognome; il cognome si riconosce perché nelle distinte è scritto per primo.
        # Per i cognomi composti con particella (De, Di, Del, Della, Da, Lo, La) si uniscono le prime due parole.
        part = {'de', 'di', 'del', 'della', 'da', 'lo', 'la', 'dal', 'dalla', 'van', 'von'}
        if p[0].lower() in part and len(p) >= 3:
            cogn, nome = p[0] + ' ' + p[1], p[2]
        else:
            cogn, nome = p[0], p[1]
        n = f"{cogn} {nome[0].upper()}."
    r = (role or '').upper().replace(' ', '')
    if r.startswith('CAP'):
        n += ' (C)'
    elif r.startswith('V.CAP') or r.startswith('VCAP') or r.startswith('VICE'):
        n += ' (VC)'
    return n


def parse(path):
    fn = os.path.basename(path)
    m = re.match(r'Distinta U16 (\d+)a giornata - (\d{2})\.(\d{2}) h(\d{1,2})[.:](\d{2}) (.+?) - (.+?) \((.+)\)\.docx$', fn, re.I)
    if not m:
        return None, f"nome file non riconosciuto: {fn}"
    gn, dd, mm, hh, mi, casa, trasf, luogo = m.groups()
    d = docx.Document(path)
    txt = '\n'.join(p.text for p in d.paragraphs)
    # anno dalla riga "Partita del DD/MM/YYYY"
    y = re.search(r'(\d{2})/(\d{2})/(\d{4})', txt)
    year = int(y.group(3)) if y else datetime.date.today().year
    # orario e avversario dal testo (prevalgono sul nome del file)
    t = re.search(r'alle h\s*(\d{1,2})[.:](\d{2})', txt)
    if t:
        hh, mi = t.groups()
    vs = re.search(r'\bvs\s+(.+?)\s+-\s+Girone', txt)
    home = bool(TEAM.search(casa))
    opp = (vs.group(1).strip() if vs else (trasf if home else casa)).strip()
    pl = re.search(r'c/o\s+(.+)', txt)
    if pl:
        a = [s.strip() for s in pl.group(1).split(' - ', 1)]
        place = a[0] + (', ' + a[1][0].lower() + a[1][1:] if len(a) > 1 and a[1] else '')
    else:
        place = luogo.strip()
    names = [''] * 15
    for tb in d.tables:
        hdr = [c.text.strip().lower() for c in tb.rows[0].cells]
        if not any('calotta' in h for h in hdr) or not any('giocatore' in h for h in hdr):
            continue
        ic = next(i for i, h in enumerate(hdr) if 'calotta' in h)
        ig = next(i for i, h in enumerate(hdr) if 'giocatore' in h)
        ir = next((i for i, h in enumerate(hdr) if 'cap' in h and i != ic), None)
        for r in tb.rows[1:]:
            c = [x.text.strip() for x in r.cells]
            if not c[ic].isdigit() or not c[ig]:
                continue
            k = int(c[ic])
            if 1 <= k <= 15:
                names[k - 1] = short(c[ig], c[ir] if ir is not None else '')
    date = f"{year:04d}-{int(mm):02d}-{int(dd):02d}"
    return {'gn': int(gn), 'gio': f"{int(gn)}ª giornata", 'date': date, 'time': f"{int(hh):02d}:{mi}",
            'home': home, 'opp': opp, 'place': place, 'names': names, 'file': fn}, None


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    dry = '--dry' in sys.argv
    pin, folder, encf = a[0], a[1], a[2]
    D = dec(encf, pin)
    rep, changed = [], False
    files = sorted(glob.glob(os.path.join(folder, '*.docx')))
    if not files:
        print('Nessuna distinta .docx trovata.'); return
    for f in files:
        if os.path.basename(f).startswith('~$'):
            continue
        r, err = parse(f)
        if err:
            rep.append('⚠ ' + err); continue
        if sum(1 for n in r['names'] if n) < 7:
            rep.append(f"⚠ {r['file']}: trovati solo {sum(1 for n in r['names'] if n)} nomi, non la uso"); continue
        ex = next((m for m in D['matches'] if re.match(r'(\d+)', m.get('gio', '')) and int(re.match(r'(\d+)', m['gio']).group(1)) == r['gn']), None)
        tag = f"{r['gio']} {r['date'][8:]}/{r['date'][5:7]} h{r['time']} vs {r['opp']} ({'casa' if r['home'] else 'trasferta'})"
        if ex is None:
            new = {'id': f"g{r['gn']}-{r['date']}", 'gio': r['gio'], 'date': r['date'], 'time': r['time'], 'home': r['home'],
                   'opp': r['opp'], 'place': r['place'], 'names': r['names']}
            D['matches'].append(new); changed = True
            rep.append(f"+ {tag}: nuova partita, {sum(1 for n in r['names'] if n)} nomi"); continue
        if ex.get('log'):
            diff = [i + 1 for i in range(15) if (ex['names'][i] if i < len(ex['names']) else '') != r['names'][i]]
            if diff:
                rep.append(f"= {tag}: già registrata, non modificata (nella distinta differiscono le calotte {', '.join(map(str, diff))})")
            else:
                rep.append(f"= {tag}: già registrata, distinta uguale")
            continue
        ch = []
        for k in ('date', 'time', 'home', 'opp', 'place'):
            if ex.get(k) != r[k]:
                ch.append(f"{k}: {ex.get(k)} → {r[k]}"); ex[k] = r[k]
        old = ex.get('names') or [''] * 15
        dn = [f"cal. {i + 1}: {old[i] if i < len(old) else ''} → {r['names'][i]}" for i in range(15) if (old[i] if i < len(old) else '') != r['names'][i]]
        if dn:
            ex['names'] = r['names']
        if ch or dn:
            changed = True
            rep.append(f"~ {tag}: " + '; '.join(ch + dn))
        else:
            rep.append(f"  {tag}: nessuna modifica")
    D['matches'].sort(key=lambda m: (m.get('date', ''), m.get('time', '')))
    print('\n'.join(rep))
    if changed and not dry:
        enc(D, pin, encf)
        print('SCRITTO distinte.enc')
    elif changed:
        print('(prova: nulla scritto)')
    else:
        print('NESSUNA MODIFICA')


if __name__ == '__main__':
    main()
