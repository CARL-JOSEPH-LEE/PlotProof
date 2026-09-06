<h1>Contributing to PlotProof</h1>
<p>Start with a minimal manuscript that demonstrates a real continuity problem or a false positive. Include the expected result and enough surrounding text to explain dreams, flashbacks, repairs, aliases, or other valid changes. Use original or permission-cleared material.</p>
<p>The checking engine uses the Python standard library. The native desktop uses PySide6 Essentials. Keep source quotes exact and locatable, preserve author decisions only when their evidence is unchanged, and surface partial coverage instead of claiming a clean manuscript. Changes to checking behavior need regression examples, including valid narrative explanations.</p>
<h2>Run locally</h2>
<pre>python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m plotproof</pre>
<p>On macOS or Linux, use .venv/bin/python. Windows is the supported packaged desktop; other desktop platforms are source builds.</p>
<h2>Validate your change</h2>
<pre>python -m ruff check plotproof tools tests
python -m ruff format --check plotproof tools tests
python -m pytest -q</pre>
<p>For desktop or packaging changes, also install requirements-build.txt and run tools/package_windows.py followed by tools/smoke_windows.py installers/PlotProof-0.2.0-windows-x64/PlotProof.exe. The smoke test copies the app into a Unicode directory, strips the development PATH, and exercises native widgets, saved decisions, revisions, and exports. Run the packaged window interactively before sharing it. See <a href="docs/DEVELOPMENT.md">the development guide</a> for package output and GitHub workflows.</p>
<h2>Design and data contracts</h2>
<p>The desktop uses a dark pine navigation rail, warm paper workspace, and amber evidence highlights. Prefer native widgets, keyboard access, readable manuscript text, and restrained motion. Preserve Chinese and English labels and accessible names. User-facing controls must have working behavior and clear empty, loading, and failure states.</p>
<p>Typing saves a recoverable draft; explicit saves create revisions. Restoring an old version creates a new revision. Project switches and shutdown must preserve drafts and review notes. Never silently overwrite another revision, erase a manuscript after a read error, invent a source quote, or report model failures as a clean result.</p>
<p>Keep personal manuscripts, API credentials, caches, development environments, and generated executables out of pull requests. Use the bundled fictional examples in screenshots. PlotProof code remains MIT; bundled Qt libraries remain replaceable under their own licenses.</p>
