# Fototeca → Google Drive

App para respaldar todas las imágenes de tu fototeca en Google Drive.

- **Funciona en Windows y Mac.** Tiene ventana y también modo consola.
- **No sube duplicados.** Compara el contenido de cada archivo (MD5), así que una foto repetida con otro nombre se sube una sola vez.
- **Se puede reanudar.** Si se corta internet o la cierras, al volver a abrirla sigue donde quedó. Lo ya subido no se repite, aunque lo hayas subido desde otro computador.
- **Ordena las fotos** por año y mes (según la fecha EXIF en que se tomó la foto), o respeta tus carpetas, o deja todo junto.
- Acepta JPG, PNG, HEIC (iPhone), RAW (DNG, CR2, NEF, ARW…), y si quieres también videos (MOV, MP4…).
- **Es segura:** solo pide permiso `drive.file`, así que únicamente ve los archivos que ella misma sube. No puede leer ni borrar nada más de tu Drive.

---

## 1. Requisitos

- **Python 3.9 o superior** → https://www.python.org/downloads/
  (En Windows marca la casilla **"Add Python to PATH"** al instalar.)

## 2. Crear tu llave de Google (una sola vez, ~5 min)

Google exige que cada app tenga su propia credencial:

1. Entra a https://console.cloud.google.com/ y crea un proyecto (ej. "Fototeca").
2. Menú **APIs y servicios → Biblioteca** → busca **Google Drive API** → **Habilitar**.
3. **APIs y servicios → Pantalla de consentimiento de OAuth** (o "Google Auth Platform"):
   - Tipo de usuario: **Externo** → completa nombre de la app y tu correo.
   - En **Usuarios de prueba** (Audiencia) agrega tu propio Gmail.
4. **APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth**
   - Tipo de aplicación: **App de escritorio** → Crear → **Descargar JSON**.
5. Cambia el nombre del archivo descargado a `credentials.json` y cópialo en:
   - **Windows:** `C:\Users\TU_USUARIO\.fototeca_drive\credentials.json`
   - **Mac:** `~/.fototeca_drive/credentials.json` (en Finder: Cmd+Shift+G y pega la ruta; crea la carpeta si no existe)

## 3. Usarla

- **Windows:** doble clic en `iniciar_windows.bat`
- **Mac:** doble clic en `iniciar_mac.command` (si macOS lo bloquea: clic derecho → Abrir)

La primera vez instala lo necesario y abre el navegador para que autorices el acceso a tu Drive
(como la app está "en prueba", Google mostrará un aviso: **Continuar**).

En la ventana:

1. **Carpeta de fotos:** ya viene la fototeca detectada; puedes cambiarla con "Elegir…".
2. **Carpeta en Drive:** nombre de la carpeta donde quedará todo (por defecto `Fototeca`).
3. **Organizar:** por año/mes, igual que tus carpetas, o todo junto.
4. Marca **Solo simular** si primero quieres ver qué haría sin subir nada.
5. **Respaldar en Drive.** Puedes detener cuando quieras y continuar después.

Resultado en Drive (modo por año/mes):

```
Fototeca/
├── 2023/
│   ├── 07-Julio/
│   └── 12-Diciembre/
└── 2024/
    └── 01-Enero/
```

### Modo consola (opcional)

```bash
python -m fototeca_drive --consola --simular                       # ver qué haría
python -m fototeca_drive --consola                                 # respaldar la fototeca
python -m fototeca_drive --consola --origen "D:\Fotos" --videos    # otra carpeta, con videos
python -m fototeca_drive --consola --organizar original --destino "Respaldo Fotos"
```

## Notas importantes

**Fototeca de Fotos en Mac:** la app lee los originales dentro de
`~/Pictures/Photos Library.photoslibrary/originals`. Para que pueda entrar:

- Ve a **Ajustes del Sistema → Privacidad y seguridad → Acceso total al disco** y activa **Terminal**.
- Si usas **Fotos de iCloud con "Optimizar almacenamiento"**, muchos originales no están en el Mac.
  Antes de respaldar, en Fotos → Ajustes → iCloud elige **"Descargar originales a este Mac"**.

**Fotos del iPhone en Windows:** conecta el iPhone y usa la app **Fotos** de Windows → Importar
(o iCloud para Windows); luego apunta la app a la carpeta donde quedaron.

**Espacio:** Drive gratis trae 15 GB compartidos con Gmail. Usa **Solo simular** para ver cuántos GB
se subirían antes de empezar.

**Dónde guarda su estado:** en la carpeta `.fototeca_drive` de tu usuario (`estado.json` y `token.json`).
Para desconectar tu cuenta basta con borrar `token.json`.

## Para desarrolladores

```bash
pip install -r requirements.txt pytest
python -m pytest
```

Estructura: `escaneo.py` (busca fotos y calcula carpeta destino), `estado.py` (caché y lo ya subido),
`drive.py` (OAuth y subida reanudable con reintentos), `sincronizar.py` (motor), `gui.py` (ventana).
