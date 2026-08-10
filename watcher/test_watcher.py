import os
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

try:
    # Running `python -m unittest watcher.test_watcher` from the repository root.
    from watcher import watcher as app
except ImportError:
    # VS Code's unittest discovery can use watcher/ as its start directory.
    import watcher as app


class MappingConfigurationTests(unittest.TestCase):
    def test_reads_valid_yaml_mapping(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as config_file:
            config_file.write(
                "mappings:\n"
                "  - source: daniela/eingang\n"
                "    target: https://opencloud.example.test/dav/Daniela\n"
            )
            filename = config_file.name

        try:
            self.assertEqual(
                app.parse_file_target_mapping(filename),
                {
                    "1": {
                        "source": "daniela/eingang",
                        "target": "https://opencloud.example.test/dav/Daniela",
                    }
                },
            )
        finally:
            os.unlink(filename)

    def test_relative_source_matches_folder_below_scan_root(self):
        with patch.object(app, "SCAN_ROOT", "/opencloud-ocrmypdf/scan"):
            self.assertTrue(
                app.matches_source_path(
                    "/opencloud-ocrmypdf/scan/daniela/eingang", "daniela/eingang"
                )
            )
            self.assertFalse(
                app.matches_source_path("/opencloud-ocrmypdf/scan/daniela", "denis")
            )


class OcrCommandTests(unittest.TestCase):
    def test_default_command_contains_configured_default_flags(self):
        with patch.multiple(
            app,
            OCR_LANGUAGES=["deu", "eng"],
            OCR_DESKEW=True,
            OCR_ROTATE_PAGES=True,
            OCR_CLEAN=True,
            OCR_CLEAN_FINAL=False,
            OCR_REMOVE_BACKGROUND=False,
            OCR_SKIP_TEXT=True,
            OCR_REDO_OCR=False,
            OCR_FORCE_OCR=False,
        ):
            command = app.build_ocr_command("source.pdf", "output.pdf")

        self.assertEqual(command[-3:], ["deu+eng", "source.pdf", "output.pdf"])
        self.assertTrue({"--deskew", "--rotate-pages", "--clean", "--skip-text"}.issubset(command))
        self.assertNotIn("--redo-ocr", command)

    def test_invalid_webdav_target_is_rejected(self):
        self.assertFalse(app.create_webdav_folder("not-a-url"))


class UploadFilenameTests(unittest.TestCase):
    def test_adds_millisecond_timestamp_before_extension(self):
        timestamp = datetime(2026, 5, 22, 14, 3, 4, 123456)

        self.assertEqual(
            app.add_timestamp_to_filename("AnnualQuackAudit.pdf", timestamp),
            "AnnualQuackAudit_20260522-140304-123.pdf",
        )

    @patch.object(app, "create_webdav_folder", return_value=True)
    @patch.object(app, "webdav_file_exists", return_value=False)
    @patch.object(app.requests, "put")
    def test_upload_uses_original_scanner_filename_when_available(
        self, put, _file_exists, _create_folder
    ):
        put.return_value = SimpleNamespace(status_code=201, text="")

        with tempfile.TemporaryDirectory() as temp_directory:
            output = os.path.join(temp_directory, "internal-output.pdf")
            with open(output, "wb") as output_file:
                output_file.write(b"test PDF data")
            success = app.upload_file(
                output,
                "https://opencloud.example.test/dav/scans",
                destination_basename="Annual Quack Audit.pdf",
            )

        self.assertTrue(success)
        self.assertEqual(
            put.call_args.args[0],
            "https://opencloud.example.test/dav/scans/Annual%20Quack%20Audit.pdf",
        )
        self.assertEqual(put.call_args.kwargs["headers"]["If-None-Match"], "*")

    @patch.object(app, "add_timestamp_to_filename", return_value="scan_20260522-140304-123.pdf")
    @patch.object(app, "create_webdav_folder", return_value=True)
    @patch.object(app, "webdav_file_exists", return_value=True)
    @patch.object(app.requests, "put")
    def test_upload_adds_timestamp_when_filename_exists(
        self, put, _file_exists, _create_folder, _add_timestamp
    ):
        put.return_value = SimpleNamespace(status_code=201, text="")

        with tempfile.TemporaryDirectory() as temp_directory:
            output = os.path.join(temp_directory, "internal-output.pdf")
            with open(output, "wb") as output_file:
                output_file.write(b"test PDF data")
            success = app.upload_file(
                output,
                "https://opencloud.example.test/dav/scans",
                destination_basename="scan.pdf",
            )

        self.assertTrue(success)
        self.assertEqual(
            put.call_args.args[0],
            "https://opencloud.example.test/dav/scans/scan_20260522-140304-123.pdf",
        )
