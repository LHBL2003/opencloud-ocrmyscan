# OpenCloud OCR Scanner

A lightweight Docker service that watches one or more scan folders for incoming PDF files, runs them through [OCRmyPDF](https://ocrmypdf.readthedocs.io/) (with Tesseract), and uploads the OCR'd result to an [OpenCloud](https://opencloud.eu/) instance via WebDAV. It automatically routes files to different OpenCloud users or spaces based on the source subfolder.

OCR recognizes the text in scanned documents and embeds it as a searchable, selectable text layer in the PDF. This lets you copy text from the document and search it when accessing files through the Windows or macOS file-share app. OpenCloud's web interface and app can search document contents without an embedded text layer, but desktop file-share clients benefit from OCR embedded in the PDF.

The service can run on a NAS or any other Docker-capable host. It is particularly well suited to scan-to-folder workflows, for example with an NFS- or SMB-capable scanner or multifunction device: the server-side Tesseract OCR can provide better text recognition than the device itself. The Compose setup is designed for OpenCloud, but may also work with other WebDAV-compatible services.

## How it works

1. A scanner (or any process) drops a PDF into a subfolder under the shared **scan root**. In this example, `/volume1/docker-ssd/opencloud-ocrmypdf/scan/` is the scan root monitored on the NAS or host. It contains subfolders for the individual scan destinations, for example for different scanners or for one scanner that supports multiple scan targets. `/volume1/docker-ssd/opencloud-ocrmypdf/scan/daniela/` is the actual scan destination where the scanner places Daniela's PDFs.
2. The watcher container detects the new file (via `watchdog`, event-based — typically within seconds) and waits until the file size stops changing, to make sure the write is complete.
3. It matches the file's source subfolder against the configured `SCAN_MAPPING__*` rules to determine which OpenCloud WebDAV target it belongs to.
4. `ocrmypdf` processes the file (deskew, rotate, clean, etc., depending on configuration), embeds the recognized text, and writes a PDF/A result to a temporary processing folder, for example `/volume1/docker-ssd/opencloud-ocrmypdf/process/`. PDF/A is an archival PDF format intended to help keep documents compatible and readable for many years.
5. The processed PDF is uploaded to the matching OpenCloud WebDAV target (creating the remote folder if needed).
6. On successful upload, the original and temporary files are deleted. On failure, the original file is preserved so nothing is lost.
7. On startup (and optionally on a periodic interval), the watcher also scans for any pre-existing PDFs in the scan roots, so files that arrived while the container was stopped are not missed.

## Project structure

```
.
├── compose.yaml          # Docker Compose service definition
├── .env.example          # Configuration template
├── .env                  # Your local configuration (create from .env.example)
└── watcher/
    ├── Dockerfile         # Container image (Python + ocrmypdf + tesseract)
    └── watcher.py         # The watcher/OCR/upload logic
```



## System-Requirements

- Docker and Docker Compose
- An OpenCloud instance reachable over WebDAV
- An OpenCloud user with a valid app token (see [WebDAV credentials](#webdav-credentials) below)
- A shared folder on your NAS or host where the scanner drops PDFs, with one subfolder per mapping target (e.g. `/volume1/docker-ssd/opencloud-ocrmypdf/scan/daniela/` and `/volume1/docker-ssd/opencloud-ocrmypdf/scan/denis/`)
- A writable temporary processing folder for OCR output before upload (e.g. `/volume1/docker-ssd/opencloud-ocrmypdf/process/`)

Example host directories for a Docker deployment:

```text
/volume1/docker-ssd/opencloud-ocrmypdf/
|- scan/
|  |- daniela/            # Incoming PDFs for Daniela
|  `- denis/              # Incoming PDFs for Denis
`- process/               # Temporary OCR output
```

## Quick start

1. Create your configuration from the template and adjust the values for your environment — scan root path, WebDAV credentials, and folder mappings:

   ```bash
   cp .env.example .env
   ```

   Do not commit `.env`, as it contains your WebDAV credential. If you manage the Compose stack with a Docker management tool such as Dockhand, use `.env.example` as the template and copy its variables and values into that tool's environment-variable configuration instead of creating a local `.env` file.
2. Make sure the host paths referenced by `SCAN_ROOT_HOST` and `FOLDER_PROCESS` exist and are writable.
3. Build and start the service:

   ```bash
   docker compose up -d --build
   ```

4. Check the logs to confirm the scan roots were mounted correctly and mappings were loaded:

   ```bash
   docker compose logs -f opencloud-ocrmyscan
   ```

5. Drop a test PDF into one of the mapped subfolders (e.g. `/volume1/docker-ssd/opencloud-ocrmypdf/scan/daniela/test.pdf`) and watch it get OCR'd and uploaded.

## Configuration

All configuration is done through environment variables. For a local Docker Compose deployment, copy `.env.example` to `.env` and edit the copy. `compose.yaml` loads this file with `env_file`, so all variables defined in it are available to the watcher. In Docker management tools such as Dockhand, transfer the contents of `.env.example` to the stack's environment-variable configuration.

`TESSERACT_PACKAGES` is an exception: it is a build argument, so rebuilding the image is required after changing it. Other changed variables take effect when Docker Compose recreates the container (for example, with `docker compose up -d`).

### Container timezone

| Variable | Default | Description |
|---|---|---|
| `TZ` | `Europe/Berlin` | Container timezone. |


### Temporary processing folder

| Variable | Default | Description |
|---|---|---|
| `FOLDER_PROCESS` | `/opencloud-ocrmypdf/process` | Host path used for temporary OCR output before upload. |

### Watcher settings

| Variable | Default | Description |
|---|---|---|
| `SCAN_ROOT_HOST` | `/opencloud-ocrmypdf/scan` | Host path mounted into the container as the central scan root. Must contain one subfolder per mapping target. |
| `WATCHER_POLL_INTERVAL` | `10` | Idle loop interval in seconds. Detection itself is event-based (via `watchdog`), not polling — new files are typically picked up within seconds. |
| `WATCHER_REPROCESS_INTERVAL_MINUTES` | `0` | If greater than `0`, the watcher re-scans all scan roots for leftover/unprocessed PDFs every N minutes, as a safety net. `0` disables this periodic re-check (only the one-time startup check runs). |

### OCR settings (OCRmyPDF)

See the [OCRmyPDF cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html) for details on each option.

| Variable | Default | Description |
|---|---|---|
| `TESSERACT_PACKAGES` | `tesseract-ocr-deu tesseract-ocr-eng` | Build-time argument (image build only) — Tesseract language packages to install in the image. |
| `OCR_LANGUAGE` / `OCR_LANGUAGES` | `deu eng` | OCR recognition language(s), space-separated. Prefer `OCR_LANGUAGES`; `OCR_LANGUAGE` is kept as a fallback. `OCR_LANGUAGE_*`-prefixed variables are also merged in if present. |
| `OCR_DESKEW` | `true` | Corrects skewed pages by rotating them back into place. |
| `OCR_ROTATE_PAGES` | `true` | Detects and corrects page orientation. |
| `OCR_CLEAN` | `false` | Uses `unpaper` to clean pages before OCR (does not alter the final output). |
| `OCR_CLEAN_FINAL` | `false` | Like `OCR_CLEAN`, but the cleaned image is used in the final output — review carefully, as content can be removed. |
| `OCR_REMOVE_BACKGROUND` | `false` | Attempts to remove noisy backgrounds from grayscale/color scans. **Currently unreliable in this environment** — enabling it is logged as a warning. |
| `OCR_SKIP_TEXT` | `false` | Skips OCR on pages that already contain text; copies them through unchanged. |
| `OCR_REDO_OCR` | `false` | Re-OCRs invisible/damaged text layers. Incompatible with `OCR_DESKEW` / `OCR_CLEAN` / `OCR_REMOVE_BACKGROUND` — if any of those are enabled, `--redo-ocr` is skipped and a warning is logged. |
| `OCR_FORCE_OCR` | `false` | Rasterizes all pages and forces OCR, discarding existing text layers. |

All OCR variables shown above are read directly from `.env` via `env_file`; they do not need to be repeated in the `environment:` block in `compose.yaml`.

### WebDAV credentials

| Variable | Description |
|---|---|
| `WEBDAV_USER` | OpenCloud username used for uploads. |
| `WEBDAV_PASSWORD` | OpenCloud credential. For OpenCloud, this often needs to be a **personal access / app token** generated under the user's app-token settings, rather than the account password. |

### Scan-source → WebDAV-target mapping

Each mapping is defined with a pair of variables sharing a name, `SCAN_MAPPING__<NAME>_SOURCE` and `SCAN_MAPPING__<NAME>_TARGET`:

```env
SCAN_MAPPING__DANIELA_SOURCE=daniela
SCAN_MAPPING__DANIELA_TARGET=https://opencloud.example.com/dav/Daniela

SCAN_MAPPING__DENIS_SOURCE=denis
SCAN_MAPPING__DENIS_TARGET=https://opencloud.example.com/dav/spaces/<SpaceId>/Denis
```

- `_SOURCE` is the folder name (or relative subfolder path) under the scan root, e.g. `daniela` for `/volume1/docker-ssd/opencloud-ocrmypdf/scan/daniela/`.
- `_TARGET` is the full WebDAV URL the OCR'd file should be uploaded to. The target folder is created automatically if it doesn't exist yet.
- `<NAME>` is just a label to group the pair together — it doesn't need to match anything else, but must be consistent between the `_SOURCE` and `_TARGET` variables.
- You can define as many mappings as you need. Files from folders that don't match any mapping are logged and left untouched.
- The mapping variables are read from `.env` via `env_file`; they do not need to be listed individually in `compose.yaml`.

## Volumes

| Container path | Purpose | Host variable |
|---|---|---|
| `/opencloud-ocrmypdf/scan` | Central scan root, containing per-user/space subfolders. | `SCAN_ROOT_HOST` |
| `/opencloud-ocrmypdf/process` | Temporary OCR output before upload. | `FOLDER_PROCESS` |

## Logging & troubleshooting

- The container logs scan root contents on startup — check `docker compose logs` if a mapping isn't matching, to confirm the folder is actually mounted and visible.
- A missing or unmounted scan root logs a `WARNING` but does not crash the container.
- Upload failures (WebDAV errors, connection issues) preserve the original source PDF so no data is lost; the file will be retried on the next periodic re-check if `WATCHER_REPROCESS_INTERVAL_MINUTES` is set, or on container restart.
- `MKCOL` (folder creation) errors and non-2xx upload responses are logged with status code and server response body.

## License

No license specified — add one if you intend to share or distribute this project.
