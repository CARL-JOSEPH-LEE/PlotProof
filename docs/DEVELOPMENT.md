<h1>Development and packaging</h1>

<p>PlotProof uses Python 3.10+ and PySide6 Essentials. The desktop is built with Qt Widgets. The checking engine, importers and JSON storage use the Python standard library. Windows x64 is the packaged target; other desktop platforms require a source environment and separate validation.</p>

<h2>Run the source</h2>

<pre><code>python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m plotproof</code></pre>

<p>On macOS/Linux, use .venv/bin/python. On Windows, start.bat can prepare a source environment and open the desktop when Python is already installed. End users can use the <a href="../installers/README.md">portable Windows download</a>.</p>

<h2>Validate changes</h2>

<pre><code>.venv\Scripts\python -m ruff check plotproof tools tests
.venv\Scripts\python -m ruff format --check plotproof tools tests
.venv\Scripts\python -m pytest -q</code></pre>

<p>The test suite includes source coordinates, false-positive examples, provider protocol fixtures, draft recovery, version conflicts and real native-widget workflows. See <a href="VALIDATION.txt">the validation record</a> for the tested environment and scope.</p>

<h2>Build the Windows package</h2>

<pre><code>.venv\Scripts\python -m pip install -r requirements-build.txt
.venv\Scripts\python tools/package_windows.py
.venv\Scripts\python tools/smoke_windows.py installers/PlotProof-0.2.0-windows-x64/PlotProof.exe</code></pre>

<p>Build output is written to installers: the portable ZIP, its SHA-256 checksum, and an extracted application folder. The ZIP and checksum belong in Git; the extracted folder and all .exe files are ignored. Keep the executable with its _internal directory when running or redistributing the app.</p>

<p>Build intermediates use a temporary directory outside the repository. The build isolates DLL discovery from unrelated developer tools. The smoke test also uses a temporary Unicode path and a child environment without Python/Node development paths. A successful test removes its temporary files. Use --report with a path to save a diagnostic JSON record; failed smoke tests retain their temporary directory for inspection.</p>

<p>After a documentation-only change, tools/package_windows.py --refresh-assets updates the included source archive, notices, checksums and outer ZIP while preserving the executable. Rebuild normally after changing application code or dependencies.</p>

<h2>GitHub workflow</h2>

<p>The Checks workflow runs core tests on Linux and native checks on Windows. The Build Windows package workflow can be run manually from Actions and provides the ZIP and checksum as downloadable artifacts. A maintainer can also attach that same ZIP to a GitHub Release. The main README links to the package committed in installers, so a Release is optional for the first download.</p>

<p>For a version change, update plotproof/__init__.py, pyproject.toml, the download links in all five READMEs, installers/README.md and the versioned path in the packaging workflow. Build, test and replace the published ZIP and checksum together. Do not commit local manuscripts, model credentials, virtual environments or extracted runtime libraries.</p>

<h2>Repository layout</h2>

<pre>plotproof/     Native application, analysis engine, importers and storage
tests/         Core, provider, document and native desktop tests
tools/         Windows builder, entry point and package smoke test
docs/          Technical guides, screenshots and third-party license texts
installers/    Portable Windows ZIP, checksum and local extracted runtime
.github/       Continuous integration and package workflow</pre>

<p><a href="TECHNICAL_OVERVIEW.md">Technical overview</a> · <a href="../CONTRIBUTING.md">Contributing</a></p>
