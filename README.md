# OpenCloud OCR Scanner

This Docker service watches scan folders for new PDF files, processes them with [OCRmyPDF](https://ocrmypdf.readthedocs.io/) and Tesseract, then uploads the result to [OpenCloud](https://opencloud.eu/) through WebDAV. The source subfolder decides which OpenCloud user or space receives the file.

OCR recognizes the text in scanned documents and embeds it as a searchable, selectable text layer in the PDF. You can then copy text from the document and search its contents in the Windows or macOS file-share app. OpenCloud's web interface and app can search document contents without an embedded text layer, but desktop file-share clients benefit from the embedded OCR text.

The service runs on a NAS or any other host that supports Docker. It works especially well with an NFS- or SMB-capable scanner or multifunction device that saves scans to a shared folder. Server-side Tesseract OCR can provide better text recognition than the scanner itself. The Compose setup is designed for OpenCloud, but may also work with other WebDAV-compatible services.

## How it works

1. A scanner (or any other process) saves a PDF in a subfolder of the shared **scan root**. In this example, `/volume1/docker-ssd/opencloud-ocrmypdf/scan/` is the monitored root folder. Its subfolders are individual scan destinations, for different scanners or for several destinations configured on one scanner. `/volume1/docker-ssd/opencloud-ocrmypdf/scan/daniela/` is the destination for Daniela's scans.
2. The container detects the new PDF and waits until the file is fully written.
3. The folder name is matched to the configured destination in OpenCloud. (SCAN_MAPPING__DANIELA_SOURCE <> SCAN_MAPPING__DANIELA_TARGET)
4. OCRmyPDF improves the scan as configured (for example, straightening or rotating pages), embeds the recognized text, and creates a PDF/A file in a temporary folder such as `/volume1/docker-ssd/opencloud-ocrmypdf/process/`. PDF/A is an archival PDF format intended to keep documents readable for many years.
5. The processed PDF is uploaded to the matching OpenCloud folder. The folder is created automatically if it does not exist.
6. After a successful upload, the original and temporary files are deleted. If an upload fails, the original PDF remains in the scan folder.
7. When the container starts, it also checks for PDFs that were already in the scan folders. An optional periodic check can retry files after a temporary problem.

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



## System requirements

- Docker and Docker Compose
- An OpenCloud instance reachable over WebDAV
- An OpenCloud user with a valid app token (see [WebDAV credentials](#webdav-credentials) below)
- A shared folder on your NAS or host where the scanner drops PDFs, with one subfolder per mapping target (e.g. `/volume1/docker-ssd/opencloud-ocrmypdf/scan/daniela/` and `/volume1/docker-ssd/opencloud-ocrmypdf/scan/denis/`)
- A writable temporary processing folder for OCR output before upload (e.g. `/volume1/docker-ssd/opencloud-ocrmypdf/process/`)

Example folder layout on the NAS or host:

```text
/volume1/docker-ssd/opencloud-ocrmypdf/
|- scan/
|  |- daniela/            # Incoming PDFs for Daniela
|  `- denis/              # Incoming PDFs for Denis
`- process/               # Temporary OCR output
```

## Quick start

1. Clone this repository to the NAS or host where Docker runs:

   ```bash
   git clone https://github.com/LHBL2003/opencloud-ocrmyscan.git
   cd opencloud-ocrmyscan
   ```

   If you use a Docker management interface such as Dockhand, clone the repository there instead and open the stack configuration.
2. Copy the configuration template:

   ```bash
   cp .env.example .env
   ```

   Open `.env` in a text editor and set the scan root path, processing path, WebDAV credentials, and folder mappings. If you use a Docker management interface such as Dockhand, use `.env.example` as the template for its environment variables instead.
3. Create the folders configured as `SCAN_ROOT_HOST` and `FOLDER_PROCESS` and make sure Docker can write to them. For example: `/volume1/docker-ssd/opencloud-ocrmypdf/scan/` and `/volume1/docker-ssd/opencloud-ocrmypdf/process/`.
4. Build and start the service:

   ```bash
   docker compose up -d --build
   ```

5. Check the logs. They should confirm that the scan folder and mappings were found:

   ```bash
   docker compose logs -f opencloud-ocrmyscan
   ```

6. Place a test PDF in a mapped folder, for example `/volume1/docker-ssd/opencloud-ocrmypdf/scan/daniela/test.pdf`. It should be processed and uploaded automatically.

## Configuration

Most installations only require editing `.env`, which is created from `.env.example` in the quick-start guide. The variable names and their purpose are listed below. In Docker management interfaces such as Dockhand, enter the same values as environment variables for the stack.

After changing `TESSERACT_PACKAGES`, rebuild the image with `docker compose up -d --build`. For other settings, run `docker compose up -d` to recreate the container.

### Time zone

| Variable | Default | Description |
|---|---|---|
| `TZ` | `Europe/Berlin` | Time zone used by the container. |


### Temporary processing folder

| Variable | Default | Description |
|---|---|---|
| `FOLDER_PROCESS` | `/opencloud-ocrmypdf/process` | Folder on the host for temporary OCR output before upload. |

### Watcher settings

| Variable | Default | Description |
|---|---|---|
| `SCAN_ROOT_HOST` | `/opencloud-ocrmypdf/scan` | Folder on the host that contains the scan-destination subfolders. |
| `WATCHER_POLL_INTERVAL` | `10` | Internal wait interval in seconds. New files are detected automatically, usually within seconds. |
| `WATCHER_REPROCESS_INTERVAL_MINUTES` | `0` | Checks existing PDFs again every N minutes. Use this as a retry safety net after temporary problems; `0` disables periodic checks. |

### OCR settings (OCRmyPDF)

See the [OCRmyPDF cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html) for details on each option.

| Variable | Default | Description |
|---|---|---|
| `TESSERACT_PACKAGES` | `tesseract-ocr-deu tesseract-ocr-eng` | Tesseract language packages installed in the image. Add packages when you need more recognition languages. |
| `OCR_LANGUAGE` / `OCR_LANGUAGES` | `deu eng` | Recognition languages, separated by spaces. Normally set `OCR_LANGUAGES`. |
| `OCR_DESKEW` | `true` | Straightens skewed pages. |
| `OCR_ROTATE_PAGES` | `true` | Detects and corrects page orientation. |
| `OCR_CLEAN` | `true` | Cleans scan noise before text recognition. |
| `OCR_CLEAN_FINAL` | `false` | Uses the cleaned page in the final PDF. Review the results carefully, as details may be removed. |
| `OCR_REMOVE_BACKGROUND` | `false` | Attempts to remove noisy backgrounds. **Currently unreliable in this environment**; leave disabled unless you have tested it. |
| `OCR_SKIP_TEXT` | `true` | Leaves pages that already contain text unchanged. |
| `OCR_REDO_OCR` | `false` | Recreates an existing invisible or damaged OCR text layer. It cannot be combined with deskew, clean, or background removal. |
| `OCR_FORCE_OCR` | `false` | Recreates OCR for every page and replaces existing text layers. |

OCRmyPDF creates PDF/A files by default. Leave the advanced options at their default values unless you have a specific reason to change them.

### WebDAV credentials

| Variable | Description |
|---|---|
| `WEBDAV_USER` | OpenCloud username used for uploads. |
| `WEBDAV_PASSWORD` | OpenCloud app token used for uploads. Create it in the user's app-token settings; the normal account password often does not work. |

### Folder mapping: scan folder to OpenCloud folder

Each mapping has two variables with the same name: `SCAN_MAPPING__<NAME>_SOURCE` and `SCAN_MAPPING__<NAME>_TARGET`.

```env
SCAN_MAPPING__DANIELA_SOURCE=daniela
SCAN_MAPPING__DANIELA_TARGET=https://opencloud.example.com/dav/Daniela

SCAN_MAPPING__DENIS_SOURCE=denis
SCAN_MAPPING__DENIS_TARGET=https://opencloud.example.com/dav/spaces/<SpaceId>/Denis
```

- `_SOURCE` is the folder name, or a relative subfolder path, below the scan root. For example, `daniela` matches `/volume1/docker-ssd/opencloud-ocrmypdf/scan/daniela/`.
- `_TARGET` is the complete WebDAV address of the OpenCloud folder. The service creates that folder when necessary.
- `<NAME>` is only a label that links the two variables. It must be the same for the `_SOURCE` and `_TARGET` pair, but can otherwise be chosen freely.
- Add as many mappings as needed. PDFs in folders without a mapping stay untouched and are reported in the log.

## Docker folder mapping

| Path in the container | Purpose | Setting for the host folder |
|---|---|---|
| `/opencloud-ocrmypdf/scan` | Monitored scan root, containing subfolders such as `daniela/` and `denis/`. | `SCAN_ROOT_HOST` |
| `/opencloud-ocrmypdf/process` | Temporary OCR output before upload. | `FOLDER_PROCESS` |

## Troubleshooting

- If a PDF is not processed, run `docker compose logs -f opencloud-ocrmyscan`. At startup, the log lists the folders and mappings that were found.
- If the scan root is missing or was not mounted, the container writes a warning to the log. Check the path in `SCAN_ROOT_HOST` and the Docker folder mapping.
- If an upload fails, the original PDF remains in the scan folder. It is retried on the next periodic check (when enabled) or after restarting the container.
- For WebDAV errors, check the OpenCloud address, username, and app token in `.env`.

## License

No license specified — add one if you intend to share or distribute this project.
