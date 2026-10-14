"""Trae el material de la carpeta de Drive de Bella Vittoria: fotos optimizadas, videos para web y hojas de contacto numeradas."""
import io, json, os, re, subprocess, tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image, ImageOps, ImageDraw
creds = service_account.Credentials.from_service_account_info(json.loads(os.environ["GOOGLE_CREDENTIALS"]), scopes=["https://www.googleapis.com/auth/drive.readonly"])
drive = build("drive", "v3", credentials=creds, cache_discovery=False)
CARPETA = os.environ["DRIVE_CARPETA"]
os.makedirs("material/fotos", exist_ok=True); os.makedirs("material/videos", exist_ok=True); os.makedirs("material/hojas", exist_ok=True)

def bajar(fid):
    b = io.BytesIO(); d = MediaIoBaseDownload(b, drive.files().get_media(fileId=fid), chunksize=32 * 1024 * 1024); h = False
    while not h: _, h = d.next_chunk()
    return b.getvalue()

archivos, tok = [], None
while True:
    r = drive.files().list(q=f"'{CARPETA}' in parents and trashed=false", fields="nextPageToken,files(id,name,mimeType,size,md5Checksum)", pageSize=200, pageToken=tok).execute()
    archivos += r["files"]; tok = r.get("nextPageToken")
    if not tok: break
indice, vistos, registro = [], set(), []
for a in sorted(archivos, key=lambda x: x["name"].lower()):
    if a.get("md5Checksum") in vistos:
        registro.append(f"DUPLICADO {a['name']}"); continue
    vistos.add(a.get("md5Checksum"))
    try:
        if a["mimeType"].startswith("image/"):
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(bajar(a["id"])))).convert("RGB")
            w, h = im.size; im.thumbnail((1800, 1800))
            n = len([x for x in indice if x["tipo"] == "foto"]) + 1
            ruta = f"material/fotos/f{n:03d}.jpg"; im.save(ruta, "JPEG", quality=80, optimize=True, progressive=True)
            indice.append({"n": n, "tipo": "foto", "archivo": ruta, "origen": a["name"], "ancho": w, "alto": h})
        elif a["mimeType"].startswith("video/"):
            n = len([x for x in indice if x["tipo"] == "video"]) + 1
            with tempfile.TemporaryDirectory() as t:
                src = os.path.join(t, "v.mp4"); open(src, "wb").write(bajar(a["id"]))
                ruta = f"material/videos/v{n:02d}.mp4"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-preset", "slow", "-crf", "27", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", ruta], check=True)
                for k, seg in enumerate(("1", "4")):
                    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", seg, "-i", ruta, "-frames:v", "1", "-q:v", "4", f"material/videos/v{n:02d}-{k}.jpg"], check=False)
            indice.append({"n": n, "tipo": "video", "archivo": ruta, "origen": a["name"]})
    except Exception as e:
        registro.append(f"ERROR {a['name']}: {type(e).__name__}: {str(e)[:200]}")
json.dump(indice, open("material/indice.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# hojas de contacto numeradas (fotos y cuadros de video)
items = [(f"F{x['n']}", x["archivo"]) for x in indice if x["tipo"] == "foto"] + [(f"V{x['n']}", f"material/videos/v{x['n']:02d}-0.jpg") for x in indice if x["tipo"] == "video"]
por_hoja = 20
for h in range(0, len(items), por_hoja):
    hoja = Image.new("RGB", (5 * 260, 4 * 200), (235, 235, 235)); dr = ImageDraw.Draw(hoja)
    for i, (et, ruta) in enumerate(items[h:h + por_hoja]):
        try:
            im = Image.open(ruta).convert("RGB"); im.thumbnail((250, 175))
            x, y = (i % 5) * 260 + 5, (i // 5) * 200 + 5; hoja.paste(im, (x, y)); dr.rectangle([x, y, x + 48, y + 22], fill=(214, 40, 40)); dr.text((x + 6, y + 5), et, fill=(255, 255, 255))
        except Exception:
            pass
    hoja.save(f"material/hojas/hoja-{h // por_hoja + 1}.jpg", quality=72)
open("material/registro.txt", "w", encoding="utf-8").write(f"{len(archivos)} archivos · {len([x for x in indice if x['tipo']=='foto'])} fotos · {len([x for x in indice if x['tipo']=='video'])} videos\n" + "\n".join(registro) + "\n")
print(open("material/registro.txt").read())
