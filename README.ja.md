<div align="center">
<h1>PlotProof</h1>
<h3>物語の矛盾を見つけ、原文で確かめる。</h3>
<p>物語の整合性を見直すための、無料でオープンソースのデスクトップアプリ。二つの文章を比較し、原文に戻り、判断を次の改稿へ引き継げます。</p>
<p>Windows x64 · Native desktop · Local first · MIT</p>
<p><a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.es.md">Español</a></p>
<p><a href="https://github.com/CARL-JOSEPH-LEE/PlotProof/raw/refs/heads/main/installers/PlotProof-0.2.0-windows-x64.zip"><strong>Windows 版をダウンロード · v0.2.0</strong></a> · <a href="#quick-start">クイックスタート</a> · <a href="#source">ソースから実行</a></p>
</div>

<p><img src="docs/screenshots/workbench.en.jpg" alt="PlotProof native desktop review" width="100%"></p>
<p align="center"><sub>PlotProof 0.2.0 · 実際の Windows アプリ · 同梱の架空のサンプル原稿</sub></p>

<h2>第2章で溶かされた鍵が、なぜ第7章で扉を開けるのでしょう？</h2>
<p>物語の矛盾は、離れた文章の間に潜んでいます。PlotProof は変化の前後を同じ画面に並べ、何が変わり、どの章に根拠があるかを示します。矛盾なのか、意図した展開なのかを決めるのは作者です。</p>

<h2>疑問の発見から、次の改稿まで</h2>
<table>
<tr><td><strong>根拠をたどれる指摘</strong></td><td>二つの引用を文脈とともに強調表示し、章と行番号を示します。クリックすると原稿エディターの該当箇所へ移動します。</td></tr>
<tr><td><strong>物語のつながりを可視化</strong></td><td>章をまたぐ変化をマップで確認。人物や物ごとに整理された事実の索引から、出典を調べられます。</td></tr>
<tr><td><strong>改稿をまたいで判断を保持</strong></td><td>問題として確認するか、説明を記録できます。無関係な編集では判断を保持し、根拠の範囲内が変わると再確認の対象になります。</td></tr>
<tr><td><strong>執筆と確認を一つの作業環境で</strong></td><td>TXT、Markdown、DOCX の読み込み、自動保存、版の保存と復元、PDF・HTML・JSON の書き出しに対応します。</td></tr>
</table>

<details>
<summary>章のつながりと事実の索引は、実際の原稿の確認結果から生成されます。</summary>
<p><img src="docs/screenshots/story-map.jpg" alt="PlotProof chapter connections and fact index" width="100%"></p>
</details>

<h2 id="quick-start">クイックスタート</h2>
<ol>
<li>Windows 用 ZIP をダウンロードし、フォルダー全体を展開します。</li>
<li>PlotProof.exe をダブルクリックします。隣の _internal フォルダーはそのまま残してください。実行環境を同梱しており、独立したネイティブウィンドウで開きます。</li>
<li>“Try a sample story” を選択し、壊された鍵の指摘を確認して原文へ移動し、改稿と再チェックを試してください。サンプルはモデル設定なしでオフライン実行できます。</li>
</ol>
<p>デスクトップ UI は英語と中国語に対応しています。両言語のサンプル原稿を同梱しています。</p>

<h2>オフラインで始め、自分のモデルを接続</h2>
<table>
<tr><td><strong>オフラインルール</strong></td><td>設定不要。明示的な人物属性、物の状態、生死に関する一部の変化を確認します。操作の体験や単純な記述の変化の確認に向いています。</td></tr>
<tr><td><strong>Ollama</strong></td><td>インストール済みのローカルモデルを接続し、意味に基づく事実抽出と候補の再確認を行います。“Review engine” でアドレスとモデルを設定します。</td></tr>
<tr><td><strong>互換 API</strong></td><td>任意の Chat Completions サービスに接続できます。モデルによる確認を実行すると、関連する原稿の文章がそのサービスへ送信されます。</td></tr>
</table>
<p>プロジェクト、下書き、各版は端末に保存されます。アカウントやテレメトリーはありません。認証情報は実行中のメモリーにのみ保持され、モデルの重みは同梱していません。</p>

<h2>根拠を確認する仕組み</h2>
<p>章の解析 → 明示的な事実の抽出 → 引用の照合 → 値の比較 → 文脈の再確認 → 作者の判断</p>
<p>引用を根拠として採用するには、対応する段落に原文と完全一致する箇所が一つだけ存在する必要があります。主体と属性で事実をまとめ、異なる値を候補にします。モデルモードでは周囲の文脈を使って、変化に説明があるかを再確認します。</p>
<p><a href="docs/TECHNICAL_OVERVIEW.md">技術概要を読む</a></p>

<details>
<summary>現在の対応範囲</summary>
<p>原稿1件につき最大30万文字。オフラインルールの対象は限定的です。モデルは別名、暗黙の時系列、与えられた文脈の外にある説明を見落とすことがあります。引用の照合は出典の確認であり、解釈の正しさを保証するものではありません。最終判断は作者が行います。</p>
</details>

<h2 id="source">ソースから実行</h2>
<p>Python 3.10+ · PySide6 / Qt Widgets · Windows x64 ポータブル版。Windows でソースから実行：</p>
<pre><code>git clone https://github.com/CARL-JOSEPH-LEE/PlotProof.git
cd PlotProof
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m plotproof</code></pre>
<p><a href="docs/DEVELOPMENT.md">開発・テスト・パッケージ作成ガイド</a></p>

<h2>次の改稿を、もっと良くするために</h2>
<p>見落とされた矛盾や、誤って指摘された自然な変化があれば、短い原稿例と期待する結果をお寄せください。別名、時系列、モデル評価、アクセシビリティーの改善を歓迎します。</p>
<p><a href="CONTRIBUTING.md">Contributing</a> · <a href="https://github.com/CARL-JOSEPH-LEE/PlotProof/issues">Issues</a> · <a href="docs/VALIDATION.txt">Validation</a></p>

<hr>
<p>アプリケーションのソースコードは MIT ライセンスです。同梱コンポーネントには各ライセンスが適用されます。 <a href="LICENSE">MIT</a> · <a href="THIRD_PARTY_NOTICES.txt">Third-party notices</a></p>
