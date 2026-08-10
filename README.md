# OpenCloud OCR Scanner — Automatic PDF OCR and WebDAV Uploads with Docker

OpenCloud OCR Scanner is a self-hosted Docker service that automatically turns scanned PDFs into searchable PDF/A documents and uploads them to [OpenCloud](https://opencloud.eu/) through WebDAV. It watches shared scan folders, runs [OCRmyPDF](https://ocrmypdf.readthedocs.io/) with [Tesseract OCR](https://tesseract-ocr.github.io/), and routes each processed document to an OpenCloud user folder or space based on its source subfolder.

Use it when a network scanner or multifunction printer saves PDFs to an NFS or SMB share and you want an automatic scanner-to-OpenCloud workflow. The embedded OCR text layer makes text selectable and searchable in desktop file-share clients on Windows and macOS. OpenCloud's web interface and app can search document contents without an embedded text layer, but desktop clients benefit from OCR inside the PDF itself.

The service runs on a NAS or any other Docker host. Server-side Tesseract OCR can provide better text recognition than OCR built into a scanner. The included Docker Compose setup is designed for OpenCloud and may also work with other WebDAV-compatible services.

## Key features

- Automatically detects new PDF scans in shared folders.
- Creates searchable, selectable PDF/A documents with OCRmyPDF and Tesseract.
- Straightens pages, corrects page orientation, and cleans scans before text recognition by default.
- Maps scanner folders to different OpenCloud user folders or spaces.
- Uploads processed documents over WebDAV and creates the final destination folder when needed.
- Preserves the original scan if processing or upload fails.
- Processes PDFs already present at startup and can periodically retry files after temporary failures.

Ready to install it? Go directly to the [Docker quick start](#docker-quick-start).

## How automatic PDF OCR and upload work

1. A scanner (or any other process) saves a PDF in a subfolder of the shared **scan root**. In this example, `/volume1/docker-ssd/opencloud-ocrmyscan/scan/` is the monitored root folder. Its subfolders are individual scan destinations, for different scanners or for several destinations configured on one scanner. `/volume1/docker-ssd/opencloud-ocrmyscan/scan/daniela/` is the destination for Daniela's scans.
2. The container detects the new PDF and waits until the file is fully written.
3. The folder name is matched to the configured destination in OpenCloud (`mappings.yaml`).
4. OCRmyPDF improves the scan as configured (for example, straightening or rotating pages), embeds the recognized text, and creates a PDF/A file in a temporary folder such as `/volume1/docker-ssd/opencloud-ocrmyscan/process/`. PDF/A is an archival PDF format intended to keep documents readable for many years.
5. The processed PDF is uploaded to the matching OpenCloud folder (`mappings.yaml`). The folder is created automatically if it does not exist.
6. After a successful upload, the original and temporary files are deleted. If an upload fails, the original PDF remains in the scan folder.
7. When the container starts, it also checks for PDFs that were already in the scan folders. An optional periodic check can retry files after a temporary problem.

## Repository structure

```
.
|- compose.yaml                  # Standard Docker Compose service
|- .env.example                  # Configuration template
|- config/mappings.yaml.example  # Mapping configuration template
`- watcher/
   |- Dockerfile                 # Container image (Python + OCRmyPDF + Tesseract)
   |- requirements.txt           # Pinned Python dependencies
   |- watcher.py                 # Watcher, OCR, and upload logic
   `- test_watcher.py             # Automated unit tests
```

## Requirements for running the OCR service

- Docker and Docker Compose
- An OpenCloud instance reachable over WebDAV
- An OpenCloud user with a valid app token (see [WebDAV credentials](#webdav-credentials) below)
- A shared folder on your NAS or host where the scanner drops PDFs, with one subfolder per mapping target (e.g. `/volume1/docker-ssd/opencloud-ocrmyscan/scan/daniela/` and `/volume1/docker-ssd/opencloud-ocrmyscan/scan/denis/`)
- A writable temporary processing folder for OCR output before upload (e.g. `/volume1/docker-ssd/opencloud-ocrmyscan/process/`)
- A persistent configuration folder containing `mappings.yaml` (e.g. `/volume1/docker-ssd/opencloud-ocrmyscan/config/mappings.yaml`), created from [`config/mappings.yaml.example`](config/mappings.yaml.example)

Example folder layout on the NAS or host:

```text
/volume1/docker-ssd/opencloud-ocrmyscan/
|- config/
|  `- mappings.yaml       # Scan folder -> OpenCloud WebDAV destination mappings
|- scan/
|  |- daniela/            # Incoming PDFs for Daniela
|  `- denis/              # Incoming PDFs for Denis
`- process/               # Temporary OCR output
```

## Docker quick start

1. Clone this repository to the NAS or host where Docker runs:

   ```bash
   git clone https://github.com/LHBL2003/opencloud-ocrmyscan.git
   cd opencloud-ocrmyscan
   ```

2. Create the folders configured as `SCAN_ROOT_HOST`, `FOLDER_PROCESS`, and `CONFIG_DIR_HOST`. For example: `/volume1/docker-ssd/opencloud-ocrmyscan/scan/`, `/volume1/docker-ssd/opencloud-ocrmyscan/process/`, and `/volume1/docker-ssd/opencloud-ocrmyscan/config/`. Make sure Docker can write to the scan and processing folders, and can read the configuration folder (it is mounted read-only).

3. Configure the required environment variables. For Docker Compose, copy the configuration template.<br>
   ℹ️: If you use Dockhand or other Docker-Management, add the repository with **From Git**, open the stack configuration, and enter the same values as stack variables instead of creating a local `.env` file.

   ```bash
   cp .env.example .env
   ```

   Open `.env` in a text editor and set at least these values:

   ```env
   FOLDER_PROCESS=/volume1/docker-ssd/opencloud-ocrmyscan/process
   SCAN_ROOT_HOST=/volume1/docker-ssd/opencloud-ocrmyscan/scan
   CONFIG_DIR_HOST=/volume1/docker-ssd/opencloud-ocrmyscan/config
   WEBDAV_USER=ScanUser
   WEBDAV_PASSWORD=<OPEN_CLOUD_APP_TOKEN>
   ```



4. Create `/volume1/docker-ssd/opencloud-ocrmyscan/config/mappings.yaml` from the repository's [`config/mappings.yaml.example`](config/mappings.yaml.example) template. Edit its `source` and `target` values for your folders and WebDAV destinations. The Compose file mounts this host folder directly into the container.

5. Build and start the service:

   ```bash
   docker compose up -d --build
   ```

6. Check the logs. They should confirm that the scan folder and mappings were found:

   ```bash
   docker compose logs -f opencloud-ocrmyscan
   ```

7. Place a test PDF in a mapped folder, for example `/volume1/docker-ssd/opencloud-ocrmyscan/scan/daniela/test.pdf`. It should be processed and uploaded automatically.

## Configure OCR, scan folders, and WebDAV uploads

The following sections describe all available settings and their defaults or required values.

### Set the container time zone

| Variable | Default | Description |
|---|---|---|
| `TZ` | `Europe/Berlin` | Time zone used by the container. |


### Set the temporary processing folder

| Variable | Default | Description |
|---|---|---|
| `FOLDER_PROCESS` | Required | Folder on the host for temporary OCR output before upload. Example: `/volume1/docker-ssd/opencloud-ocrmyscan/process`. |

### Set the mapping configuration folder

| Variable | Default | Description |
|---|---|---|
| `CONFIG_DIR_HOST` | Required | Host folder containing `mappings.yaml`; mounted read-only into the container. Example: `/volume1/docker-ssd/opencloud-ocrmyscan/config`. |

### Configure scan-folder monitoring and retries

New PDFs are detected event-based. After a file is created, the service waits until its size no longer changes, then processes it automatically. The periodic re-check below is only a safety net for existing PDFs after temporary processing or upload problems.

| Variable | Default | Description |
|---|---|---|
| `SCAN_ROOT_HOST` | Required | Folder on the host that contains the scan-destination subfolders. Example: `/volume1/docker-ssd/opencloud-ocrmyscan/scan`. |
| `WATCHER_SAFETY_RECHECK_INTERVAL_MINUTES` | `1440` | Checks existing PDFs again every N minutes. The default is once per 24 hours as a retry safety net after temporary problems; `0` disables periodic checks. Very short intervals such as `1` minute are not recommended. |

### Configure OCRmyPDF and Tesseract OCR

See the [OCRmyPDF cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html) for details on each option.

| Variable | Default | Description |
|---|---|---|
| `TESSERACT_PACKAGES` | `tesseract-ocr-deu tesseract-ocr-eng` | Tesseract language packages installed in the image (Dockerfile). Add packages when you need more recognition languages. (Compose --build required) |
| `OCR_LANGUAGES` | `deu eng` | Recognition languages, separated by spaces (for example, `deu eng`). |
| `OCR_DESKEW` | `true` | Straightens skewed pages. |
| `OCR_ROTATE_PAGES` | `true` | Detects and corrects page orientation. |
| `OCR_CLEAN` | `true` | Cleans the page only before text recognition, helping to avoid false OCR text from background noise (for example, text showing through from the reverse side). It does **not** change the visible page in the final PDF. |
| `OCR_CLEAN_FINAL` | `false` | Uses the cleaned page in the final PDF. Review the results carefully, as details may be removed. |
| `OCR_REMOVE_BACKGROUND` | `false` | Attempts to remove noisy backgrounds. **Currently unreliable in this environment**; leave disabled unless you have tested it. |
| `OCR_SKIP_TEXT` | `true` | Leaves pages that already contain text unchanged. |
| `OCR_REDO_OCR` | `false` | Recreates an existing invisible or damaged OCR text layer. It cannot be combined with deskew, clean, or background removal. |
| `OCR_FORCE_OCR` | `false` | Recreates OCR for every page and replaces existing text layers. |

Keep the language settings aligned: every language code in `OCR_LANGUAGES` must have its matching package installed through `TESSERACT_PACKAGES`. For example, add `tesseract-ocr-fra` and `fra` when French OCR is needed. `OCR_LANGUAGES` may be a subset of the installed packages. The available language codes are listed in the official [Tesseract language data](https://github.com/tesseract-ocr/tessdata) repository. After rebuilding the image, verify the installed codes with `docker compose exec opencloud-ocrmyscan tesseract --list-langs`.

Leave the advanced options at their default values unless you have a specific reason to change them.

### Configure OpenCloud WebDAV credentials

| Variable | Description |
|---|---|
| `WEBDAV_USER` | OpenCloud username used for uploads. |
| `WEBDAV_PASSWORD` | OpenCloud app token used for uploads. Create it in the user's app-token settings; using a token instead of the normal account password is more secure and the account password often does not work. |

### Map scan folders to OpenCloud destinations

Mappings are configured in `CONFIG_DIR_HOST/mappings.yaml`. The file uses a YAML list:

```yaml
mappings:
  - source: daniela
    target: "https://opencloud.MyDomain.com/dav/Daniela"

  - source: denis
    target: "https://opencloud.MyDomain.com/dav/spaces/<SpaceId>/Denis"
```

- `source` is the folder name, or a relative subfolder path, below the scan root. For example, `daniela` matches `/volume1/docker-ssd/opencloud-ocrmyscan/scan/daniela/`, while `daniela/eingang` matches `/volume1/docker-ssd/opencloud-ocrmyscan/scan/daniela/eingang/`.
- `target` is the complete WebDAV address of the OpenCloud folder. The service creates the final folder when necessary; its parent folders must already exist.
- Add as many list entries as needed. PDFs in folders without a mapping stay untouched and are reported in the log.
- The mapping file is read when the container starts. Restart the container after editing it.

To find a folder's WebDAV URL in OpenCloud, click the user icon in the top right, open **Settings** and then **Settings** again, and enable **Show WebDAV information in the detail view**. The WebDAV URL is then shown in the properties/details of each folder.

## Docker volume mappings

| Path in the container | Purpose | Setting for the host folder |
|---|---|---|
| `/opencloud-ocrmypdf/scan` | Monitored scan root e.g. `/volume1/docker-ssd/opencloud-ocrmyscan/scan/`, containing subfolders such as `/volume1/docker-ssd/opencloud-ocrmyscan/scan/daniela/` and `/volume1/docker-ssd/opencloud-ocrmyscan/scan/denis/`. | `SCAN_ROOT_HOST` (required) |
| `/opencloud-ocrmypdf/process` | Temporary OCR output before upload. On the NAS / host, e.g. `/volume1/docker-ssd/opencloud-ocrmyscan/process/` | `FOLDER_PROCESS` (required) |
| `/opencloud-ocrmypdf/config` | Read-only configuration folder containing `mappings.yaml`, e.g. `/volume1/docker-ssd/opencloud-ocrmyscan/config/mappings.yaml`. | `CONFIG_DIR_HOST` (required) |

## Troubleshoot PDF processing and WebDAV uploads

### Updates are not applied after a Git sync

`compose.yaml` mounts `watcher/watcher.py` from the checked-out repository into the container. After an update from Git, restarting or redeploying the container is enough to apply changes to this Python file. This works with Docker Compose and Docker management interfaces such as Dockhand or Komodo.

Changes to the `Dockerfile`, `requirements.txt`, or `TESSERACT_PACKAGES` require a new image build; restarting the existing container is not enough. If your Docker management interface does not provide a **Build image** action for Git repositories, delete only the existing `opencloud-ocrmyscan` image and deploy the stack again. The manager should then build a new image from the current Git checkout.

Check the image creation date or image ID before starting the container to confirm that the image was regenerated. Also make sure the manager supports building the Compose `build` configuration from the Git repository.

### Other processing and upload problems

- If a PDF is not processed, run `docker compose logs -f opencloud-ocrmyscan`. At startup, the log lists the folders and mappings that were found.
- If the scan root is missing or was not mounted, the container writes a warning to the log. Check the path in `SCAN_ROOT_HOST` and the Docker folder mapping.
- If an upload fails, the original PDF remains in the scan folder. It is retried on the next periodic check (when enabled) or after restarting the container.
- For WebDAV errors, check the OpenCloud address in `mappings.yaml`, plus username and app token in `.env`.
- To test the WebDAV connection, use a WebDAV client on Windows or macOS with the same HTTPS address, username, and app token. Opening the WebDAV address in Google Chrome can also provide a basic login check: after entering the username and token, a blank page may be shown. This only indicates that authentication may work; use a WebDAV client to verify folder access and uploads.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, tests, and pull-request guidelines.

## License

This project is licensed under the [MIT License](LICENSE). It may be used, modified, and distributed for private or commercial purposes. The software is provided without warranty, and the authors accept no liability for its functionality, security, or any damages resulting from its use.

### Third-party licenses

The MIT License applies only to this project's own code and configuration. The Docker image includes third-party components such as OCRmyPDF, Tesseract, Python, and their dependencies. These components remain subject to their respective license terms. When using, modifying, or distributing the image, you are responsible for reviewing and complying with those terms.
