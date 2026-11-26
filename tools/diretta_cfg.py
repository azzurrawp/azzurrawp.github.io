"""Cifra gli indirizzi HLS della diretta privata con il codice dei genitori (PBKDF2-SHA256 150000 + AES-GCM 256).
Uso: python3 diretta_cfg.py <codice> <hls_mux> [<hls_gcore> ...]   → stampa la riga da mettere in CFG in diretta.html.
La pagina controlla gli indirizzi nell'ordine dato e mostra il primo in onda."""
import base64, json, os, sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
code = sys.argv[1].strip().upper()
sources = [{"hls": u.strip()} for u in sys.argv[2:]]
salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=150000).derive(code.encode())
d = AESGCM(key).encrypt(iv, json.dumps({"sources": sources}).encode(), None)
b = lambda x: base64.b64encode(x).decode()
print(json.dumps({"s": b(salt), "iv": b(iv), "d": b(d)}))
