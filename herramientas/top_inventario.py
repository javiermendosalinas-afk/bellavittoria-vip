"""Top de inmobiliarias de la ZMG por inventario publicado en EasyBroker (solo nombre, estatus y número de publicaciones)."""
import json, os, re, gspread
from google.oauth2.service_account import Credentials
cr = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_CREDENTIALS"]), scopes=["https://www.googleapis.com/auth/spreadsheets"])
v = gspread.authorize(cr).open_by_key("1fKudPDoznm76sdsDWElLGsyl-FtqAs03mW2cSUw_tYk").worksheet("Directorio").get_all_values()
i = next(i for i, r in enumerate(v) if any(c.strip().lower() == "inmobiliaria" for c in r))
h = [c.strip().lower() for c in v[i]]
def col(r, *n):
    for k in n:
        for j, c in enumerate(h):
            if c.startswith(k) and j < len(r): return r[j]
    return ""
filas = []
for r in v[i + 1:]:
    n = re.sub(r"\D", "", col(r, "núm. publicaciones", "num. publicaciones", "núm", "publicaciones"))
    if not n: continue
    zona = col(r, "zona").strip().upper(); mun = col(r, "municipio")
    filas.append((int(n), col(r, "inmobiliaria").strip(), col(r, "estatus en easybroker").strip(), zona, mun))
filas.sort(reverse=True)
zmg = [f for f in filas if f[3] == "ZMG"]
out = {"total_inmobiliarias": len(filas), "zmg": len(zmg), "publicaciones_zmg": sum(f[0] for f in zmg),
       "top15": [{"inmobiliaria": f[1], "publicaciones": f[0], "estatus": f[2], "municipio": f[4]} for f in zmg[:15]],
       "colaborando": sum(1 for f in zmg if "colabor" in f[2].lower()), "pub_colaborando": sum(f[0] for f in zmg if "colabor" in f[2].lower())}
json.dump(out, open("herramientas/top_inventario.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")
