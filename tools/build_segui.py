# Genera segui.html (pagina per allenatore e dirigenti) da index.html:
# stessa app in sola visualizzazione, senza manifest né installazione. Rilanciare a ogni rilascio.
import os,re
d=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s=open(os.path.join(d,'index.html'),encoding='utf-8').read()
for pat in [r'<link rel="manifest"[^>]*>\n',r'<meta name="apple-mobile-web-app-capable"[^>]*>\n',r'<meta name="mobile-web-app-capable"[^>]*>\n']:
    s,n=re.subn(pat,'',s);assert n==1,pat
s=s.replace('<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">','<meta name="viewport" content="width=device-width,initial-scale=1">')
s=s.replace('<title>Azzurra WP Stat</title>','<title>Azzurra U16 · Statistiche</title>')
open(os.path.join(d,'segui.html'),'w',encoding='utf-8').write(s)
print('segui.html ok')
