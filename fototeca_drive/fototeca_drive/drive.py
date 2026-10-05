"""Conexión con Google Drive (OAuth + subida de archivos)."""

from __future__ import annotations

import mimetypes
import time
from pathlib import Path

from .estado import DIR_APP

# drive.file: la app solo ve y modifica los archivos que ella misma crea.
# No puede leer ni borrar el resto de tu Drive.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
MIME_CARPETA = "application/vnd.google-apps.folder"

mimetypes.add_type("image/heic", ".heic")
mimetypes.add_type("image/heif", ".heif")
mimetypes.add_type("image/webp", ".webp")


def autenticar(credenciales: Path | None = None):
    """Abre el navegador para autorizar la app (solo la primera vez)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credenciales = credenciales or DIR_APP / "credentials.json"
    token = DIR_APP / "token.json"
    creds = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credenciales.exists():
                raise FileNotFoundError(
                    f"No se encontró {credenciales}.\n"
                    "Descarga el archivo OAuth 'credentials.json' desde Google Cloud Console "
                    "y cópialo ahí (ver README)."
                )
            flujo = InstalledAppFlow.from_client_secrets_file(str(credenciales), SCOPES)
            creds = flujo.run_local_server(port=0)
        token.parent.mkdir(parents=True, exist_ok=True)
        token.write_text(creds.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _escapar(nombre: str) -> str:
    return nombre.replace("\\", "\\\\").replace("'", "\\'")


class Drive:
    def __init__(self, servicio):
        self.s = servicio
        self._carpetas: dict[tuple[str, str], str] = {}

    def carpeta(self, nombre: str, padre: str = "root") -> str:
        """Devuelve el id de la carpeta `nombre` dentro de `padre`, creándola si no existe."""
        clave = (padre, nombre)
        if clave in self._carpetas:
            return self._carpetas[clave]
        q = (
            f"name = '{_escapar(nombre)}' and mimeType = '{MIME_CARPETA}' "
            f"and '{padre}' in parents and trashed = false"
        )
        res = self.s.files().list(q=q, fields="files(id)", spaces="drive", pageSize=1).execute()
        if res.get("files"):
            fid = res["files"][0]["id"]
        else:
            meta = {"name": nombre, "mimeType": MIME_CARPETA, "parents": [padre]}
            fid = self.s.files().create(body=meta, fields="id").execute()["id"]
        self._carpetas[clave] = fid
        return fid

    def ruta_carpetas(self, partes: list[str], raiz: str) -> str:
        actual = raiz
        for p in partes:
            actual = self.carpeta(p, actual)
        return actual

    def md5_existentes(self) -> dict[str, str]:
        """md5 -> id de todos los archivos que esta app ya subió (en cualquier equipo)."""
        resultado: dict[str, str] = {}
        token = None
        while True:
            res = self.s.files().list(
                q=f"trashed = false and mimeType != '{MIME_CARPETA}'",
                fields="nextPageToken, files(id, md5Checksum)",
                pageSize=1000,
                pageToken=token,
                spaces="drive",
            ).execute()
            for f in res.get("files", []):
                if f.get("md5Checksum"):
                    resultado[f["md5Checksum"]] = f["id"]
            token = res.get("nextPageToken")
            if not token:
                return resultado

    def subir(self, ruta: Path, carpeta_id: str, reintentos: int = 5) -> str:
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        mime = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
        meta = {"name": ruta.name, "parents": [carpeta_id]}
        for intento in range(reintentos):
            try:
                media = MediaFileUpload(str(ruta), mimetype=mime, resumable=True, chunksize=8 * 1024 * 1024)
                pet = self.s.files().create(body=meta, media_body=media, fields="id")
                resp = None
                while resp is None:
                    _, resp = pet.next_chunk(num_retries=3)
                return resp["id"]
            except HttpError as e:
                if e.resp.status in (403, 429, 500, 502, 503, 504) and intento < reintentos - 1:
                    time.sleep(2 ** intento)
                    continue
                raise
            except (OSError, TimeoutError):
                if intento < reintentos - 1:
                    time.sleep(2 ** intento)
                    continue
                raise
        raise RuntimeError("No se pudo subir " + str(ruta))
