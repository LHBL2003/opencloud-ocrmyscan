# Contributing

Contributions are welcome while the project is in beta.

## Development setup

Install the Python dependencies and run the test suite before opening a pull request:

```bash
pip install -r watcher/requirements.txt
python -m unittest watcher.test_watcher
```

Build the container when changing `watcher/Dockerfile`, `watcher/requirements.txt`, or OCR packages:

```bash
docker build --tag opencloud-ocrmyscan:local --file watcher/Dockerfile .
```

## Pull requests

- Keep changes focused and document user-visible behavior in `README.md`.
- Add or update tests for changes to mapping, OCR command, or upload behavior.
- Do not commit `.env`, `config/mappings.yaml`, access tokens, or other secrets.
- Preserve the original PDF on processing or upload errors.
