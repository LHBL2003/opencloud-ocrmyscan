import os
import re
import time
import subprocess
import uuid
from urllib.parse import quote
import requests
import yaml

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def read_app_version():
    """Read the packaged version, with an environment override for deployments."""
    configured = os.environ.get("APP_VERSION")
    if configured:
        return configured.strip()

    try:
        with open(os.path.join(os.path.dirname(__file__), "VERSION"), encoding="utf-8") as version_file:
            return version_file.read().strip() or "unknown"
    except OSError:
        return "development"


APP_VERSION = read_app_version()
SCAN_ROOT = os.environ.get("WATCHER_SCAN_ROOT", "/opencloud-ocrmypdf/scan")
TMP_ROOT = os.environ.get("WATCHER_TMP_ROOT", "/opencloud-ocrmypdf/process")
POLL_INTERVAL_SECONDS = int(os.environ.get("WATCHER_POLL_INTERVAL_SECONDS", "10"))
REPROCESS_INTERVAL_MINUTES = int(os.environ.get("WATCHER_REPROCESS_INTERVAL_MINUTES", "1440") or "1440")
OCR_DESKEW = os.environ.get("OCR_DESKEW", "true").lower() in {"1", "true", "yes", "on"}
OCR_ROTATE_PAGES = os.environ.get("OCR_ROTATE_PAGES", "true").lower() in {"1", "true", "yes", "on"}
OCR_CLEAN = os.environ.get("OCR_CLEAN", "true").lower() in {"1", "true", "yes", "on"}
OCR_CLEAN_FINAL = os.environ.get("OCR_CLEAN_FINAL", "false").lower() in {"1", "true", "yes", "on"}
OCR_REMOVE_BACKGROUND = os.environ.get("OCR_REMOVE_BACKGROUND", "false").lower() in {"1", "true", "yes", "on"}
OCR_SKIP_TEXT = os.environ.get("OCR_SKIP_TEXT", "true").lower() in {"1", "true", "yes", "on"}
OCR_REDO_OCR = os.environ.get("OCR_REDO_OCR", "false").lower() in {"1", "true", "yes", "on"}
OCR_FORCE_OCR = os.environ.get("OCR_FORCE_OCR", "false").lower() in {"1", "true", "yes", "on"}


def parse_languages():
    languages = []

    configured = os.environ.get("OCR_LANGUAGES", "deu eng")
    for raw_value in re.split(r"[\s,]+", configured):
        value = raw_value.strip()
        if value and value not in languages:
            languages.append(value)

    return languages or ["deu"]


OCR_LANGUAGES = parse_languages()


SCAN_ROOTS = [SCAN_ROOT]
MAPPING_CONFIG_FILE = os.environ.get(
    "MAPPING_CONFIG_FILE", "/opencloud-ocrmypdf/config/mappings.yaml"
)


# -------------------------------------------------
# Configuration
# -------------------------------------------------

def log(*args):
    print(*args, flush=True)


def parse_file_target_mapping(filename):
    """Read scan-to-WebDAV mappings from a YAML file."""
    if not os.path.isfile(filename):
        log("Mapping configuration file not found:", filename)
        return {}

    try:
        with open(filename, "r", encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file) or {}
    except (OSError, yaml.YAMLError) as exc:
        log("WARNING: Could not read mapping configuration:", filename, repr(exc))
        return {}

    mappings = data.get("mappings", []) if isinstance(data, dict) else []
    if not isinstance(mappings, list):
        log("WARNING: 'mappings' in", filename, "must be a YAML list")
        return {}

    result = {}
    for index, mapping in enumerate(mappings, start=1):
        if not isinstance(mapping, dict):
            log("WARNING: Ignoring invalid mapping #", index, "in", filename)
            continue

        source = mapping.get("source")
        target = mapping.get("target")
        if not isinstance(source, str) or not source.strip() or not isinstance(target, str) or not target.strip():
            log("WARNING: Ignoring incomplete mapping #", index, "in", filename)
            continue

        result[str(index)] = {"source": source.strip(), "target": target.strip()}

    return result


config = parse_file_target_mapping(MAPPING_CONFIG_FILE)
if config:
    log("Loaded", len(config), "mapping(s) from:", MAPPING_CONFIG_FILE)
else:
    log("WARNING: No valid scan-to-WebDAV mappings configured")

WEBDAV_USER = os.environ.get("WEBDAV_USER")
WEBDAV_PASSWORD = os.environ.get("WEBDAV_PASSWORD")
WEBDAV_CONFIGURED = bool(WEBDAV_USER and WEBDAV_PASSWORD)


log("--------------------------------")
log("OpenCloud OCR Scanner started")
log("Version:", APP_VERSION)
log("Scan roots:", SCAN_ROOTS)
log("Temp:", TMP_ROOT)
if not WEBDAV_CONFIGURED:
    log("ERROR: WEBDAV_USER and WEBDAV_PASSWORD must both be configured")
for scan_root in SCAN_ROOTS:
    if os.path.exists(scan_root):
        try:
            entries = sorted(os.listdir(scan_root))
            log("Scan root contents:", scan_root, entries[:20] if entries else "<empty>")
        except Exception as exc:
            log("Scan root listing failed:", scan_root, repr(exc))
    else:
        log("WARNING: Scan root does not exist or is not mounted:", scan_root)
log("--------------------------------")


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def wait_until_file_ready(filename):

    log("Waiting for completed file:", filename)

    last_size = -1

    while True:

        size = os.path.getsize(filename)

        if size == last_size:
            break

        last_size = size
        time.sleep(3)



def build_target_url(target):
    if target.startswith("http://") or target.startswith("https://"):
        return target.rstrip("/")

    log("ERROR: Invalid WebDAV target:", target)
    return None


def discover_existing_pdfs(roots):
    discovered = []

    for root in roots:
        if not os.path.exists(root):
            continue

        for current_root, _, files in os.walk(root):
            for filename in files:
                if filename.lower().endswith(".pdf"):
                    discovered.append(os.path.join(current_root, filename))

    return sorted(discovered)


def create_webdav_folder(target):

    """
    Erstellt Zielordner falls nötig.
    Existierende Ordner werden ignoriert.
    """

    target_url = build_target_url(target)
    if not target_url:
        return False

    try:

        r = requests.request(
            "MKCOL",
            target_url,
            auth=(
                WEBDAV_USER,
                WEBDAV_PASSWORD
            ),
            timeout=30
        )


        if r.status_code in [
            201,  # erstellt
            405   # existiert bereits
        ]:
            return True


        log(
            "MKCOL:",
            target_url,
            r.status_code,
            r.text
        )
        return False


    except Exception as e:

        log(
            "MKCOL error:",
            repr(e)
        )
        return False



def upload_file(filename, target):

    basename = os.path.basename(filename)


    if not create_webdav_folder(target):
        log("Upload skipped because the WebDAV target folder could not be prepared")
        return False


    target_url = build_target_url(target)
    if not target_url:
        return False
    url = target_url + "/" + quote(basename, safe="")


    log("")
    log("Upload:")
    log(url)


    try:

        with open(filename, "rb") as data:

            r = requests.put(
                url,
                auth=(
                    WEBDAV_USER,
                    WEBDAV_PASSWORD
                ),
                data=data,
                headers={
                    "Content-Type": "application/pdf"
                },
                timeout=120
            )


        log(
            "Upload Status:",
            r.status_code
        )


        if r.text:
            log(
                "Server Antwort:",
                r.text
            )


        return r.status_code in [
            200,
            201,
            204
        ]


    except Exception as e:

        log(
            "Upload exception:",
            repr(e)
        )

        return False



# -------------------------------------------------
# Processing
# -------------------------------------------------

def normalize_path(path):
    cleaned = path.replace("\\", "/").strip("/")
    parts = [part for part in cleaned.split("/") if part not in {"", "."}]
    return "/".join(part.casefold() for part in parts)


def matches_source_path(current_folder, source_config):
    current_candidates = [normalize_path(current_folder)]

    if SCAN_ROOT:
        try:
            scan_root = os.path.normpath(SCAN_ROOT)
            relative_path = os.path.relpath(os.path.normpath(current_folder), scan_root)
            if relative_path not in {"", ".", os.pardir} and not relative_path.startswith(".."):
                current_candidates.append(normalize_path(relative_path))
        except Exception:
            pass

    return normalize_path(source_config) in current_candidates


def build_ocr_command(source, output):
    """Build the OCRmyPDF command from the selected OCR options."""
    command = ["ocrmypdf", "--language", "+".join(OCR_LANGUAGES), source, output]

    if OCR_DESKEW:
        command.insert(1, "--deskew")
    if OCR_ROTATE_PAGES:
        command.insert(1, "--rotate-pages")
    if OCR_CLEAN:
        command.insert(1, "--clean")
    if OCR_CLEAN_FINAL:
        command.insert(1, "--clean-final")
    if OCR_REMOVE_BACKGROUND:
        log("OCR remove-background is enabled, but OCRmyPDF currently raises NotImplementedError in this environment")
        command.insert(1, "--remove-background")
    if OCR_SKIP_TEXT:
        command.insert(1, "--skip-text")
    if OCR_REDO_OCR and not any([OCR_DESKEW, OCR_CLEAN, OCR_REMOVE_BACKGROUND]):
        command.insert(1, "--redo-ocr")
    elif OCR_REDO_OCR:
        log("OCR redo-ocr disabled because it is incompatible with deskew/clean/remove-background")
    if OCR_FORCE_OCR:
        command.insert(1, "--force-ocr")

    return command


def process_file(source):

    log("")
    log("==============================")
    log("New file:")
    log(source)
    log("==============================")


    try:

        wait_until_file_ready(source)

        if not WEBDAV_CONFIGURED:
            log("Upload skipped because WebDAV credentials are not configured")
            return


        source_folder = os.path.dirname(source)
        target_url = None

        log("Resolved source folder:", source_folder)
        for mapping in config.values():
            source_config = mapping.get("source", "")
            target_config = mapping.get("target", "")

            if not source_config or not target_config:
                continue

            current_folder = os.path.normpath(source_folder)

            if matches_source_path(current_folder, source_config):
                target_url = target_config
                log("Matched mapping:", source_config, "for scan folder:", source_folder)
                break

        if not target_url:
            log(
                "No matching mapping in configuration",
                MAPPING_CONFIG_FILE,
                "for scan folder:",
                source_folder,
            )

            return


        os.makedirs(
            TMP_ROOT,
            exist_ok=True
        )


        output = os.path.join(
            TMP_ROOT,
            f"{uuid.uuid4().hex}-{os.path.basename(source)}"
        )


        log("Starting OCR")
        log("OCR options: deskew=%s rotate_pages=%s clean=%s clean_final=%s remove_background=%s skip_text=%s redo_ocr=%s force_ocr=%s" % (
            OCR_DESKEW,
            OCR_ROTATE_PAGES,
            OCR_CLEAN,
            OCR_CLEAN_FINAL,
            OCR_REMOVE_BACKGROUND,
            OCR_SKIP_TEXT,
            OCR_REDO_OCR,
            OCR_FORCE_OCR
        ))

        command = build_ocr_command(source, output)

        subprocess.run(
            command,
            check=True
        )


        log(
            "OCR completed:",
            output
        )


        if not os.path.exists(output):

            log(
                "ERROR: OCR output file missing"
            )

            return


        log(
            "Starting upload"
        )


        success = upload_file(
            output,
            target_url
        )


        if success:

            log(
                "Upload successful"
            )


            os.remove(source)

            os.remove(output)


            log(
                "Source file deleted"
            )


        else:

            log(
                "Upload failed - original file preserved"
            )


    except subprocess.CalledProcessError as e:

        log(
            "OCR error:",
            e
        )


    except Exception as e:

        log(
            "General error:",
            repr(e)
        )



# -------------------------------------------------
# Watcher
# -------------------------------------------------

class ScannerHandler(
    FileSystemEventHandler
):

    def on_created(self, event):

        if event.is_directory:
            return


        if not event.src_path.lower().endswith(".pdf"):
            return


        process_file(
            event.src_path
        )



def main():
    """Start filesystem monitoring and the optional periodic retry."""
    observer = Observer()

    for scan_root in SCAN_ROOTS:
        if os.path.isdir(scan_root):
            observer.schedule(ScannerHandler(), scan_root, recursive=True)

    observer.start()

    existing_pdfs = discover_existing_pdfs(SCAN_ROOTS)
    if existing_pdfs:
        log("Starting initial check for existing PDFs")
        for pdf_path in existing_pdfs:
            process_file(pdf_path)

    log("Monitoring active")

    try:
        while True:
            if REPROCESS_INTERVAL_MINUTES > 0:
                time.sleep(REPROCESS_INTERVAL_MINUTES * 60)
                existing_pdfs = discover_existing_pdfs(SCAN_ROOTS)
                if existing_pdfs:
                    log("Starting periodic check for existing PDFs")
                    for pdf_path in existing_pdfs:
                        process_file(pdf_path)
                continue

            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    main()
