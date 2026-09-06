<h1>How PlotProof works</h1>

<p>PlotProof turns continuity review into an inspectable sequence: extract explicit facts, verify their quotations, propose competing values, review the context, and retain the author's decision. The application connects the analysis to revision through a native manuscript editor, evidence navigation and version history.</p>

<h2>A candidate, from source to decision</h2>

<pre>Chapter 2: The brass key was destroyed.
           brass key · object_state · destroyed · exact source position

Chapter 7: She used the brass key to unlock the door.
           brass key · object_state · intact · exact source position

Same subject + same attribute + competing states
    → candidate
    → contextual model review, when configured
    → suspected issue, explained change or insufficient evidence
    → author decision</pre>

<p>An explicit repair or reforging is represented as a transition and resets the earlier state group. Ordinary progression such as intact → destroyed is handled differently from a destroyed object unexpectedly returning.</p>

<h2>The pipeline</h2>

<p>Parsing: document.py recognizes Chinese and English chapter headings and Markdown headings. Paragraphs retain chapter labels, normalized manuscript line numbers and character offsets. Content-derived paragraph IDs include an occurrence counter for duplicate paragraphs. The native editor converts Python Unicode positions to Qt's UTF-16 cursor positions.</p>

<p>Extraction: offline mode uses conservative rules. Model mode requests structured JSON facts containing subject, attribute, value, category, paragraph_id, quote and transition. Models are provided by the user through Ollama or a compatible Chat Completions endpoint; PlotProof does not contain a trained proprietary model.</p>

<p>Verification: every accepted quotation must appear exactly once in the referenced paragraph. Invented quotations, ambiguous matches, invalid paragraph IDs and malformed fact fields are rejected. This establishes the quotation's source, not whether the model has interpreted that quotation correctly.</p>

<p>Candidate generation: facts are ordered by source position and grouped by normalized subject name and attribute using Python data structures. Competing values generate candidates; explicit transitions reset a group. Alias resolution and cross-batch name normalization are not generally solved. There is no vector database in the current implementation.</p>

<p>Context review: model mode reviews one candidate at a time. Short spans include intervening paragraphs. Long spans use nearby paragraphs around each quotation and are explicitly marked as incomplete context. Valid suspected issues enter the review desk; missing or invalid model reviews generate warnings.</p>

<h2>Decisions across revisions</h2>

<p>A finding identity includes the subject/attribute, both quotations and the intervening text. Edits outside that evidence span can retain an author's existing decision. Adding an explanation between the quotations changes the identity and reopens the candidate instead of silently reusing the old judgment.</p>

<p>Drafts are stored separately from committed text. A formal revision checkpoints the previous version; restoring an older manuscript creates a new revision. Individual JSON files are flushed with fsync and replaced atomically. Saving a report checks both the manuscript hash and revision so a late analysis cannot attach to newer text.</p>

<h2>Caching and responsiveness</h2>

<p>Extraction uses batches of about 10,000 characters. A cache key covers the analysis version, provider, endpoint, model and batch payload. Identical batches can reuse extracted facts; candidate interpretation is rerun. Small edits can change batch boundaries, so the cache is not a guarantee of paragraph-level incremental analysis. Reports record requests and token usage returned by the provider.</p>

<p>The desktop uses PySide6 / Qt Widgets. QThread workers deliver progress and results through signals. QLockFile and local IPC manage the desktop instance. QPainter renders chapter connections; Qt document and PDF classes export reports. PyInstaller bundles the Python and Qt runtime as a Windows directory distribution with replaceable shared libraries.</p>

<h2>Code map</h2>

<table>
<tr><th>Module</th><th>Responsibility</th></tr>
<tr><td><a href="../plotproof/document.py">document.py</a></td><td>Chapters, paragraph IDs, exact quotation checks and positions</td></tr>
<tr><td><a href="../plotproof/rules.py">rules.py</a></td><td>Offline extraction, transitions and candidate grouping</td></tr>
<tr><td><a href="../plotproof/engine.py">engine.py</a></td><td>Structured extraction, batch cache, contextual review and coverage warnings</td></tr>
<tr><td><a href="../plotproof/storage.py">storage.py</a></td><td>Drafts, versions, atomic file writes and author decisions</td></tr>
<tr><td><a href="../plotproof/desktop/window.py">desktop/window.py</a></td><td>Library, evidence review, manuscript editor, map and history</td></tr>
</table>

<h2>Limits and useful next contributions</h2>

<p>Current bounds are 300,000 characters per manuscript, 100 extracted model facts per batch and 120 candidate pairs per review. Limits and incomplete reviews generate warnings. Offline coverage is restricted to a small set of explicit eye-color, handedness, blood-type, birth-year, object-state and life-state statements.</p>

<p>Aliases, implicit chronology, unreliable narrators, complex world rules and model quality need further work. Automated tests establish program behavior, source navigation and desktop workflows; they are not a literary-accuracy benchmark. A permission-cleared collection of real counterexamples and repeatable evaluations across models would be especially valuable.</p>

<p><a href="TECHNICAL_OVERVIEW.zh-CN.md">简体中文</a> · <a href="../README.md">Project home</a> · <a href="VALIDATION.txt">Validation record</a></p>
