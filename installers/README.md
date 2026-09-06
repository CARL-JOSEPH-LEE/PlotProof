<h1>Windows downloads</h1>

<p><a href="PlotProof-0.2.0-windows-x64.zip?raw=true">Download PlotProof 0.2.0 for Windows x64</a> · <a href="PlotProof-0.2.0-windows-x64.zip.sha256">SHA-256 checksum</a></p>

<p>Extract the complete ZIP, then double-click PlotProof.exe. Keep the _internal folder beside the executable. The portable package includes its Python and Qt runtime, application source and third-party notices.</p>

<p>完整解压 ZIP 后，双击 PlotProof.exe 即可使用。请保留同目录下的 _internal 文件夹。无需安装 Python 或 Node。包内附完整应用源码与第三方许可说明。</p>

<h2>For maintainers</h2>

<p>The ZIP and its checksum are published with the repository. All .exe files, including uppercase extensions, are ignored by Git. The extracted PlotProof-*-windows-x64 directory is also ignored so its runtime libraries stay out of the source tree in Git.</p>

<p>Rebuild with tools/package_windows.py and verify with tools/smoke_windows.py. The build uses the system temporary directory for intermediates. See <a href="../docs/DEVELOPMENT.md">the development guide</a>.</p>
