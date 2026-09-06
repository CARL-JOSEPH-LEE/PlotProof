<div align="center">
<h1>PlotProof</h1>
<h3>Encuentra fallos de continuidad. Conserva las pruebas.</h3>
<p>Una aplicación de escritorio gratuita y de código abierto para revisar la continuidad narrativa. Compara pasajes, vuelve al original y conserva tus decisiones en el siguiente borrador.</p>
<p>Windows x64 · Native desktop · Local first · MIT</p>
<p><a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.es.md">Español</a></p>
<p><a href="https://github.com/CARL-JOSEPH-LEE/PlotProof/raw/refs/heads/main/installers/PlotProof-0.2.0-windows-x64.zip"><strong>Descargar para Windows · v0.2.0</strong></a> · <a href="#quick-start">Inicio rápido</a> · <a href="#source">Ejecutar desde el código</a></p>
</div>

<p><img src="docs/screenshots/workbench.en.jpg" alt="PlotProof native desktop review" width="100%"></p>
<p align="center"><sub>PlotProof 0.2.0 · aplicación real de Windows · manuscrito ficticio incluido</sub></p>

<h2>La llave se fundió en el capítulo 2. ¿Por qué abre una puerta en el capítulo 7?</h2>
<p>Los fallos de continuidad viven entre pasajes separados. PlotProof reúne ambas partes: qué cambió, en qué capítulo y con qué palabras se describe. Tú decides si es un error o parte de la historia.</p>

<h2>Desde la primera duda hasta el siguiente borrador</h2>
<table>
<tr><td><strong>Pruebas que puedes seguir</strong></td><td>Dos citas exactas, resaltadas en su contexto, con capítulo y número de línea. Un clic abre el pasaje en el editor del manuscrito.</td></tr>
<tr><td><strong>Un mapa de la historia</strong></td><td>Consulta qué capítulos conecta cada cambio sospechoso. Explora un índice de hechos con sus fuentes, agrupados por personaje u objeto.</td></tr>
<tr><td><strong>Decisiones que sobreviven a las revisiones</strong></td><td>Confirma un problema o registra su explicación. Los cambios ajenos al tramo de evidencia conservan tu decisión; si ese tramo cambia, el hallazgo vuelve a revisión.</td></tr>
<tr><td><strong>Un espacio de escritura completo</strong></td><td>Importa TXT, Markdown y DOCX; edita con guardado automático; guarda y restaura versiones; exporta PDF, HTML y JSON.</td></tr>
</table>

<details>
<summary>Las conexiones entre capítulos y el índice de hechos proceden de la revisión del manuscrito.</summary>
<p><img src="docs/screenshots/story-map.jpg" alt="PlotProof chapter connections and fact index" width="100%"></p>
</details>

<h2 id="quick-start">Inicio rápido</h2>
<ol>
<li>Descarga el ZIP para Windows y extrae la carpeta completa.</li>
<li>Haz doble clic en PlotProof.exe. Mantén la carpeta _internal a su lado. El entorno de ejecución está incluido y la aplicación abre su propia ventana nativa.</li>
<li>Elige “Try a sample story”. Revisa la llave destruida, salta al original y prueba una modificación. Los ejemplos funcionan sin conexión y sin configurar un modelo.</li>
</ol>
<p>La interfaz de escritorio y los manuscritos de ejemplo están disponibles en inglés y chino.</p>

<h2>Empieza sin conexión o conecta tu propio modelo</h2>
<table>
<tr><td><strong>Reglas sin conexión</strong></td><td>Listas para usar. Cubren un conjunto reducido de atributos explícitos de personajes y estados de objetos o de vida. Son útiles para probar el flujo y detectar cambios sencillos y claramente expresados.</td></tr>
<tr><td><strong>Ollama</strong></td><td>Conecta un modelo local instalado para extraer hechos y revisar candidatos con análisis semántico. Configura la dirección y el modelo en “Review engine”.</td></tr>
<tr><td><strong>API compatible</strong></td><td>Conecta el servicio Chat Completions que prefieras. Al ejecutar una revisión con modelo, los pasajes pertinentes se envían a ese servicio.</td></tr>
</table>
<p>Los proyectos, borradores y versiones se guardan en tu dispositivo. Sin cuentas ni telemetría. Las credenciales permanecen en memoria durante la sesión; no se incluyen los pesos de ningún modelo.</p>

<h2>Cómo se comprueban las pruebas</h2>
<p>Analizar capítulos → extraer hechos explícitos → verificar citas → comparar valores → revisar el contexto → decisión del autor</p>
<p>Cada cita aceptada debe coincidir exactamente una sola vez con su párrafo original. Los hechos se agrupan por sujeto y atributo; los valores diferentes generan candidatos. El modo con modelo revisa después el contexto para comprobar si el cambio tiene una explicación.</p>
<p><a href="docs/TECHNICAL_OVERVIEW.md">Leer la descripción técnica</a></p>

<details>
<summary>Alcance actual</summary>
<p>Hasta 300.000 caracteres por manuscrito. Las reglas sin conexión tienen un alcance limitado. Los modelos pueden pasar por alto alias, cronología implícita y explicaciones fuera del contexto proporcionado. Verificar una cita confirma su origen, no la corrección de la interpretación. La decisión final pertenece al autor.</p>
</details>

<h2 id="source">Ejecutar desde el código</h2>
<p>Python 3.10+ · PySide6 / Qt Widgets · versión portátil para Windows x64. En Windows:</p>
<pre><code>git clone https://github.com/CARL-JOSEPH-LEE/PlotProof.git
cd PlotProof
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m plotproof</code></pre>
<p><a href="docs/DEVELOPMENT.md">Guía de desarrollo, pruebas y empaquetado</a></p>

<h2>Ayuda a mejorar el siguiente borrador</h2>
<p>¿Una contradicción omitida o un cambio válido marcado por error? Un ejemplo breve con el resultado esperado es una gran contribución. Agradecemos mejoras en alias, cronología, evaluación de modelos y accesibilidad.</p>
<p><a href="CONTRIBUTING.md">Contributing</a> · <a href="https://github.com/CARL-JOSEPH-LEE/PlotProof/issues">Issues</a> · <a href="docs/VALIDATION.txt">Validation</a></p>

<hr>
<p>El código de la aplicación tiene licencia MIT. Los componentes incluidos conservan sus propias licencias. <a href="LICENSE">MIT</a> · <a href="THIRD_PARTY_NOTICES.txt">Third-party notices</a></p>
