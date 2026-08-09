import os
import tempfile
import unittest
from unittest.mock import patch

from watcher import watcher as app


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
