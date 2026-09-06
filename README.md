<div align="center">
<h1>PlotProof</h1>
<h3>Find plot holes. Keep the evidence.</h3>
<p>A free, open-source desktop app for reviewing story continuity. Compare conflicting passages, jump to the source, and carry your decisions into the next draft.</p>
<p>Windows x64 · Native desktop · Local first · MIT</p>
<p><a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.es.md">Español</a></p>
<p><a href="https://github.com/CARL-JOSEPH-LEE/PlotProof/raw/refs/heads/main/installers/PlotProof-0.2.0-windows-x64.zip"><strong>Download for Windows · v0.2.0</strong></a> · <a href="#quick-start">Quick start</a> · <a href="#source">Run from source</a></p>
</div>

<p><img src="docs/screenshots/workbench.en.jpg" alt="PlotProof native desktop review" width="100%"></p>
<p align="center"><sub>PlotProof 0.2.0 · actual Windows application · included fictional sample</sub></p>

<h2>The key was destroyed in chapter 2. Why does it open a door in chapter 7?</h2>
<p>Continuity problems live between passages. PlotProof brings both sides onto one desk: what changed, where it happened, and the original words behind the finding. You decide whether it is a plot hole or part of the plan.</p>

<h2>Everything you need for the next revision</h2>
<table>
<tr><td><strong>Evidence you can follow</strong></td><td>Two exact quotations, highlighted in context, with chapter and line positions. One click opens the corresponding passage in the manuscript editor.</td></tr>
<tr><td><strong>A map of the story</strong></td><td>See which chapters are connected by suspected changes. Explore a source-backed fact index grouped by character or object.</td></tr>
<tr><td><strong>Review that survives edits</strong></td><td>Confirm an issue or record an explanation. Unrelated edits retain your decisions; changes inside the evidence span reopen the finding for review.</td></tr>
<tr><td><strong>A complete writing workspace</strong></td><td>Import TXT, Markdown or DOCX; edit with autosave; save and restore versions; export PDF, HTML or JSON.</td></tr>
</table>

<details>
<summary>Chapter connections and the fact index are generated from the manuscript review.</summary>
<p><img src="docs/screenshots/story-map.jpg" alt="PlotProof chapter connections and fact index" width="100%"></p>
</details>

<h2 id="quick-start">Quick start</h2>
<ol>
<li>Download the Windows ZIP and extract the complete folder.</li>
<li>Double-click PlotProof.exe. Keep the _internal folder beside it. Python and Qt are included; the app opens its own native window.</li>
<li>Choose “Try a sample story”. Review the destroyed key, jump to its source, and try a revision. The samples run offline without model setup.</li>
</ol>
<p>Desktop interface: English and Chinese. Sample stories are included in both languages.</p>

<h2>Start offline, or bring your own model</h2>
<table>
<tr><td><strong>Offline rules</strong></td><td>Ready to use. Checks a small set of explicit character attributes and object/life states. Best for trying the workflow and catching simple, clearly stated changes.</td></tr>
<tr><td><strong>Ollama</strong></td><td>Connect an installed local model for semantic fact extraction and candidate review. Choose “Review engine” to set the address and model.</td></tr>
<tr><td><strong>Compatible API</strong></td><td>Connect a Chat Completions service of your choice. Relevant manuscript text is sent to that service when you run a model review.</td></tr>
</table>
<p>Projects, drafts and versions are stored on your device. No account or telemetry. Service credentials stay in memory for the current session; model weights are not bundled.</p>

<h2>How the evidence pipeline works</h2>
<p>Parse chapters → extract explicit facts → verify quotations → compare values → review context → author decision</p>
<p>A model cannot invent a quote and have it displayed as verified evidence: each accepted quote must match exactly once in its source paragraph. Facts are grouped by subject and attribute. Competing values become candidates; model mode then checks the surrounding context before presenting suspected issues.</p>
<p><a href="docs/TECHNICAL_OVERVIEW.md">Read the technical overview</a></p>

<details>
<summary>Current scope</summary>
<p>Up to 300,000 characters per manuscript. Offline rules are intentionally narrow. Model review can miss aliases, implicit chronology and explanations outside the supplied context. A verified quotation confirms its source, not the correctness of an interpretation. The author makes the final call.</p>
</details>

<h2 id="source">Run from source</h2>
<p>Python 3.10+ · PySide6 / Qt Widgets · Windows x64 portable build. On Windows:</p>
<pre><code>git clone https://github.com/CARL-JOSEPH-LEE/PlotProof.git
cd PlotProof
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m plotproof</code></pre>
<p><a href="docs/DEVELOPMENT.md">Development, tests and packaging</a></p>

<h2>Help make the next draft better</h2>
<p>Found a missed contradiction or a valid change flagged as an issue? A short story example with the expected result is an excellent contribution. We especially welcome work on aliases, chronology, model evaluation and accessibility.</p>
<p><a href="CONTRIBUTING.md">Contributing</a> · <a href="https://github.com/CARL-JOSEPH-LEE/PlotProof/issues">Issues</a> · <a href="docs/VALIDATION.txt">Validation</a></p>

<hr>
<p>Application code is MIT licensed. Bundled components retain their own licenses. <a href="LICENSE">MIT</a> · <a href="THIRD_PARTY_NOTICES.txt">Third-party notices</a></p>
