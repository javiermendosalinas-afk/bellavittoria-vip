"""Arma la pestaña "Envío" de la hoja Directorio_inmobiliarias_EasyBroker: cruza EasyBroker (pestaña Directorio),
NeoJaus (pestaña NeoJaus) y el directorio de AMPI (secreto cifrado), sin duplicados, con mensaje personalizado,
liga de WhatsApp a un clic y columnas de control. NUNCA imprime teléfonos ni correos (los registros son públicos).
Conserva las marcas de control (Enviado, 2.º mensaje, Respondió, BAJA, Notas Javier) al volver a correr."""
import base64, csv, io, json, os, re, unicodedata, urllib.parse
import gspread
from google.oauth2.service_account import Credentials
HOJA = "1fKudPDoznm76sdsDWElLGsyl-FtqAs03mW2cSUw_tYk"
ZMG = {"guadalajara", "zapopan", "tlaquepaque", "san pedro tlaquepaque", "tlajomulco", "tlajomulco de zuniga", "tonala"}
NUMEROS = ["33 2497 0007", "33 4444 1444", "33 2577 3277"]   # desde dónde se envía (rotación)
POR_DIA_Y_NUMERO = 60
cr = Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_CREDENTIALS"]), scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
libro = gspread.authorize(cr).open_by_key(HOJA)
sa = lambda s: unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
VACIAS = r"\b(inmobiliaria|inmobiliario|grupo|bienes raices|real estate|realty|inmuebles|asesores|asesoria|consultores|s\.?a\.? de c\.?v\.?|sa de cv|de|del|la|el|los|las|the|y|and)\b"
def clave(n): return re.sub(r"[^a-z0-9]", "", re.sub(VACIAS, " ", sa(n)))
def tel10(t):
    d = re.sub(r"\D", "", str(t or ""))
    if len(d) == 12 and d.startswith("52"): d = d[2:]
    if len(d) == 13 and d.startswith("521"): d = d[3:]
    if len(d) == 8: d = "33" + d
    return d if len(d) == 10 else ""
def tabla(nombre):
    try: ws = libro.worksheet(nombre)
    except Exception: return []
    v = ws.get_all_values()
    i = next((i for i, r in enumerate(v) if any(sa(c) == "inmobiliaria" for c in r)), None)
    if i is None: return []
    h = [sa(c) for c in v[i]]
    return [dict(zip(h, r)) for r in v[i + 1:] if any(r)]
def col(r, *nombres):
    for n in nombres:
        for k, val in r.items():
            if k.startswith(n) and str(val).strip(): return str(val).strip()
    return ""
reg = {}
def sumar(fuente, nombre, **d):
    k = clave(nombre)
    if not k or k in ("aciertamax", "neojaus", "neojausdemo"): return
    x = reg.setdefault(k, {"inmobiliaria": nombre.strip(), "fuentes": set(), "contacto": "", "municipio": "", "cel": "", "tel": "", "correo": "",
                           "ampi": "", "comparte": "", "estatus_eb": "", "publicaciones": 0})
    x["fuentes"].add(fuente)
    for c in ("contacto", "municipio", "correo", "ampi", "comparte", "estatus_eb"):
        if d.get(c) and not x[c]: x[c] = d[c]
    for c in ("cel", "tel"):
        t = tel10(d.get(c))
        if t and not x[c]: x[c] = t
    if d.get("publicaciones"): x["publicaciones"] = max(x["publicaciones"], int(re.sub(r"\D", "", d["publicaciones"]) or 0))
for r in tabla("Directorio"):
    if sa(col(r, "zona")) != "zmg" and sa(col(r, "municipio")) not in ZMG: continue
    if "no contactar" in sa(col(r, "notas")): continue
    sumar("EasyBroker", col(r, "inmobiliaria"), contacto=col(r, "asesor de contacto", "contacto"), municipio=col(r, "municipio"),
          cel=col(r, "celular"), tel=col(r, "telefono oficina", "telefono"), correo=col(r, "correo"), estatus_eb=col(r, "estatus en easybroker"),
          comparte=col(r, "comparte comision"), publicaciones=col(r, "num. publicaciones", "num publicaciones"))
for r in tabla("NeoJaus"):
    if "no contactar" in sa(col(r, "notas")): continue
    sumar("NeoJaus", col(r, "inmobiliaria"), contacto=col(r, "asesor"), municipio=col(r, "municipio"), cel=col(r, "celular"),
          tel=col(r, "telefono oficina", "telefono"), correo=col(r, "correo"), ampi=col(r, "socio ampi"), comparte=col(r, "comparte comision"))
try:
    for r in csv.DictReader(io.StringIO(base64.b64decode(os.environ.get("AMPI_CSV", "")).decode("utf-8"))):
        tel = r.get("tel", "")
        sumar("AMPI", r.get("inmobiliaria") or r.get("nombre", ""), contacto=r.get("nombre", ""), correo=r.get("correo", ""), ampi="Sí",
              cel=next((t for t in re.split(r"[/,]", tel) if len(re.sub(r"\D", "", t)) >= 10), ""), tel=tel)
except Exception as e:
    print("AMPI no disponible:", type(e).__name__)
# ---- mensajes (5 versiones), con línea de colaboración según estatus en EasyBroker
PROMO = ("del 14 de octubre al 15 de noviembre compartimos *4% de comisión (IVA incluido) en Bella Vittoria*: 16 departamentos con entrega inmediata en Lomas de la Victoria, "
         "Tlaquepaque, desde $3,450,000 (14 de 71 m² y 2 de 78 m² a $3,800,000), apartado con $100,000, Infonavit, Cofinavit, banco o contado. "
         "Aplica para clientes registrados antes de su visita que escrituren a más tardar el 5 de enero de 2027; la comisión se paga al recibir el pago total, contra factura. "
         "Fichas: EasyBroker EB-VI0283 · NeoJaus NJ-B341 · bellavittoria.vip. Open House el sábado 31 de octubre, de 10 a 2.")
def linea_eb(est):
    e = sa(est)
    if "colaborando" in e: return "Gracias por colaborar con nosotros en EasyBroker 🤝."
    if "invitacion" in e: return ("Hace unos días te envié una invitación para colaborar en EasyBroker y compartir inventario y comisión todo el año; "
                                  "la aceptas en Bolsa Inmobiliaria → Colaboraciones → Invitaciones recibidas.")
    if e: return "Me encantaría que colaboremos en EasyBroker para compartir inventario y comisión todo el año; te envío la invitación."
    return ""
INICIOS = ["Hola, {n}{c} 👋 Soy Javier Mendoza, director de Acierta Max (AMPI Guadalajara y NAR).",
           "¡Buen día, {n}{c}! Te saluda Javier Mendoza, de Acierta Max (AMPI Guadalajara).",
           "Hola, {n}{c}. Soy Javier Mendoza, de Acierta Max; colega de AMPI Guadalajara y NAR.",
           "¡Qué tal, {n}{c}! Te escribe Javier Mendoza, director de Acierta Max.",
           "Hola, {n}{c} 🤝 Soy Javier Mendoza, de Acierta Max (AMPI Guadalajara y NAR)."]
PUENTES = ["Te comparto una promoción para colegas:", "Quiero invitarte a una promoción especial para corredores:", "Tengo una oportunidad para tus clientes:",
           "Te cuento de una promoción que creo que te puede interesar:", "Te comparto una promoción para inmobiliarias aliadas:"]
CIERRES = ["Para registrar a tu cliente (nombre y últimos 4 dígitos de su celular) o coordinar una visita, escríbeme a este número: 33 2497 0007. ¡Saludos!",
           "Para registrar clientes o agendar visita, aquí estoy: 33 2497 0007. ¡Gracias!",
           "Cualquier duda o registro de clientes, al 33 2497 0007. ¡Un abrazo!",
           "Registra a tu cliente o pide información al 33 2497 0007. ¡Éxito!",
           "Para registros y visitas: 33 2497 0007. ¡Quedo a tus órdenes!"]
BAJA = "Si prefieres no recibir más información, respóndeme BAJA."
def mensaje(x, v):
    c = f" ({x['contacto'].split()[0].title()})" if x["contacto"] and sa(x["contacto"]) != sa(x["inmobiliaria"]) and len(x["contacto"].split()) <= 5 else ""
    partes = [INICIOS[v].format(n=x["inmobiliaria"].strip(), c=c), PUENTES[v] + " " + PROMO]
    l = linea_eb(x["estatus_eb"]);  l and partes.append(l)
    partes += [CIERRES[v], BAJA]
    return "\n\n".join(partes)
# ---- orden: AMPI y comparte comisión primero, luego más publicaciones
lista = sorted(reg.values(), key=lambda x: (-(("AMPI" in x["fuentes"]) or sa(x["ampi"]) in ("si", "sí")), -(sa(x["comparte"]) in ("si", "sí")), -x["publicaciones"], sa(x["inmobiliaria"])))
ws = None
try: ws = libro.worksheet("Envío")
except Exception: ws = libro.add_worksheet("Envío", rows=max(len(lista) + 10, 100), cols=24)
previo = {}
v = ws.get_all_values()
if v:
    h = v[0]
    for r in v[1:]:
        d = dict(zip(h, r))
        if d.get("Clave"): previo[d["Clave"]] = d
CAB = ["Clave", "Inmobiliaria", "Contacto", "Municipio", "Socio AMPI", "Comparte comisión", "Estatus EasyBroker", "Publicaciones EB", "Fuentes",
       "Celular / WhatsApp", "Teléfono oficina", "Correo", "Canal", "Enviar desde", "Día de envío", "Versión", "Enviar WhatsApp",
       "Enviado", "2.º mensaje", "Respondió", "BAJA", "Notas Javier", "Mensaje"]
filas, n_wa = [], 0
for x in lista:
    k = clave(x["inmobiliaria"]); numero_wa = x["cel"] or (x["tel"] if x["tel"].startswith("33") else "")
    canal = "WhatsApp" if numero_wa else ("Correo" if "@" in x["correo"] else "Formulario EasyBroker" if "EasyBroker" in x["fuentes"] else "Sin contacto")
    ver = len(filas) % 5; msj = mensaje(x, ver)
    desde = dia = liga = ""
    if numero_wa:
        desde = NUMEROS[n_wa % 3]; dia = str(1 + n_wa // (POR_DIA_Y_NUMERO * 3)); n_wa += 1
        url = "https://wa.me/52" + numero_wa + "?text=" + urllib.parse.quote(msj)
        liga = url
    p = previo.get(k, {})
    filas.append([k, x["inmobiliaria"], x["contacto"], x["municipio"], "Sí" if ("AMPI" in x["fuentes"] or sa(x["ampi"]) in ("si", "sí")) else (x["ampi"] or ""),
                  x["comparte"], x["estatus_eb"], x["publicaciones"] or "", ", ".join(sorted(x["fuentes"])), numero_wa, x["tel"] if x["tel"] != numero_wa else "",
                  x["correo"], canal, desde, dia, ver + 1, liga, p.get("Enviado", ""), p.get("2.º mensaje", ""), p.get("Respondió", ""), p.get("BAJA", ""),
                  p.get("Notas Javier", ""), msj])
ws.clear()
ws.resize(rows=len(filas) + 5, cols=len(CAB))
ws.update(values=[CAB] + filas, range_name="A1", value_input_option="USER_ENTERED")
ws.freeze(rows=1, cols=2)
# Contactos para importar a Google Contacts (pestaña aparte, formato CSV de Google)
try: wc = libro.worksheet("Contactos para importar")
except Exception: wc = libro.add_worksheet("Contactos para importar", rows=len(filas) + 10, cols=6)
cc = [["Name", "Organization 1 - Name", "Phone 1 - Type", "Phone 1 - Value", "E-mail 1 - Value", "Notes"]]
for f in filas:
    if f[9] or f[11]:
        nombre = (f"{f[2].title()} · {f[1]}" if f[2] and sa(f[2]) != sa(f[1]) else f[1])[:80]
        cc.append([nombre, f[1], "Mobile", ("+52 " + f[9]) if f[9] else "", f[11], "Inmobiliaria · " + f[8]])
wc.clear(); wc.update(values=cc, range_name="A1")
import collections
print("Inmobiliarias únicas:", len(filas), "| por canal:", dict(collections.Counter(f[12] for f in filas)),
      "| días de envío por WhatsApp:", max([int(f[14]) for f in filas if f[14]] or [0]), "| contactos para importar:", len(cc) - 1)
