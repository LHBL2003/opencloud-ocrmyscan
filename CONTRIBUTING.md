# Contributing

Contributions are welcome.

## Development setup

Install the Python dependencies and run the test suite before opening a pull request:

```bash
pip install -r watcher/requirements.txt
python -m unittest watcher.test_watcher
```

## Running tests in Visual Studio Code

1. Install Python 3.12 and the Microsoft **Python** extension for Visual Studio Code.
2. Open this repository in VS Code and select the Python 3.12 interpreter with **Python: Select Interpreter** from the Command Palette.
3. Open a VS Code terminal and install the project dependencies:

   ```powershell
   python -m pip install -r watcher/requirements.txt
   ```

4. Select the beaker icon (**Testing**) in the Activity Bar. If prompted, choose **Configure Python Tests**, select **unittest**, then select the `watcher` folder.
5. Run all tests with the play button in the Testing view, or run/debug a single test there.

The same test suite can always be run in the terminal with `python -m unittest watcher.test_watcher`.

Docker Desktop is required only for building or running the container; the Python unit tests above do not require Docker.

Build the container when changing `watcher/Dockerfile`, `watcher/requirements.txt`, or OCR packages:

```bash
docker build --tag opencloud-ocrmyscan:local --file watcher/Dockerfile .
```

## Versioning and releases

Maintainers store the current application version in the root [`VERSION`](VERSION) file. Releases use [Semantic Versioning](https://semver.org/): beta releases use a version such as `0.1.0-beta.1`, and the matching annotated Git tag uses a `v` prefix, for example `v0.1.0-beta.1`.

Do not move or reuse a published tag. Create a new version, commit it, and create a new annotated tag for each release.

## Pull requests

- Keep changes focused and document user-visible behavior in `README.md`.
- Add or update tests for changes to mapping, OCR command, or upload behavior.
- Do not commit `.env`, `config/mappings.yaml`, access tokens, or other secrets.
- Preserve the original PDF on processing or upload errors.
