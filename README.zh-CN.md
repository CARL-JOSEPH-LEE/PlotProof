<div align="center">
<h1>PlotProof</h1>
<h3>找到剧情漏洞，拿出原文证据。</h3>
<p>免费开源的桌面剧情审阅工具。把前后矛盾的段落放到一起核对，随时定位原文，让审阅结论跟上你的每次改稿。</p>
<p>Windows x64 · Native desktop · Local first · MIT</p>
<p><a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="README.ja.md">日本語</a> · <a href="README.ko.md">한국어</a> · <a href="README.es.md">Español</a></p>
<p><a href="https://github.com/CARL-JOSEPH-LEE/PlotProof/raw/refs/heads/main/installers/PlotProof-0.2.0-windows-x64.zip"><strong>下载 Windows 版 · v0.2.0</strong></a> · <a href="#quick-start">快速开始</a> · <a href="#source">从源码运行</a></p>
</div>

<p><img src="docs/screenshots/workbench.zh-CN.jpg" alt="PlotProof native desktop review" width="100%"></p>
<p align="center"><sub>PlotProof 0.2.0 · Windows 软件实拍 · 项目自带的原创示例故事</sub></p>

<h2>第二章已经熔毁的钥匙，为什么在第七章又打开了门？</h2>
<p>剧情漏洞往往藏在两段文字之间。PlotProof 把变化前后的原文放到同一张审阅台：哪里变了、发生在哪一章、原文究竟怎么写。它负责把证据摆出来，是否修改由你决定。</p>

<h2>从发现疑点，到完成下一稿</h2>
<table>
<tr><td><strong>每处疑点，都有出处</strong></td><td>两段引文并排展示，高亮对应文字，保留章节与行号。点击即可跳到稿件编辑器中的原文。</td></tr>
<tr><td><strong>看见故事之间的联系</strong></td><td>章节地图展示疑点跨越的位置；事实索引按人物、物品分组，每条事实都能回到来源。</td></tr>
<tr><td><strong>改稿后，不必从头审阅</strong></td><td>确认问题或记录解释。无关修改保留已有结论；两处证据之间的内容变化后，相关疑点重新待审。</td></tr>
<tr><td><strong>完整的桌面写作工作区</strong></td><td>导入 TXT、Markdown、DOCX，编辑时自动保存，建立和恢复版本，导出 PDF、HTML、JSON。</td></tr>
</table>

<details>
<summary>章节连线与事实索引来自实际稿件检查结果。</summary>
<p><img src="docs/screenshots/story-map.jpg" alt="PlotProof chapter connections and fact index" width="100%"></p>
</details>

<h2 id="quick-start">快速开始</h2>
<ol>
<li>下载 Windows ZIP，并将整个文件夹完整解压。</li>
<li>双击 PlotProof.exe，保留旁边的 _internal 文件夹。运行环境已包含在内，直接打开独立原生窗口。</li>
<li>点击“体验示例故事”，核对那把已经熔毁的钥匙，定位原文，再试着修改和重检。示例离线运行，无需配置模型。</li>
</ol>
<p>桌面界面支持中文和英文，内置中英文示例故事。</p>

<h2>先离线体验，再接入你自己的模型</h2>
<table>
<tr><td><strong>离线规则</strong></td><td>开箱即用，检查少量明确的人物属性、物品与生死状态。适合体验审阅流程，以及发现简单、直接陈述的前后变化。</td></tr>
<tr><td><strong>Ollama 本地模型</strong></td><td>连接已安装的本地模型，进行语义事实提取与候选复核。在“检查方式与模型”中填写地址和模型名。</td></tr>
<tr><td><strong>兼容模型接口</strong></td><td>连接你选择的 Chat Completions 服务。运行模型检查时，相关稿件内容会发送给该服务。</td></tr>
</table>
<p>项目、草稿和版本保存在本机，无账号服务、无遥测。服务凭据仅保留在本次运行的内存中；软件不附带模型权重。</p>

<h2>证据是怎样找到的</h2>
<p>解析章节 → 提取明确事实 → 核对引文 → 比较属性值 → 复核上下文 → 作者判断</p>
<p>模型给出的引文，必须在对应原文段落中精确、唯一地出现，才能进入证据列表。程序按“主体＋属性”归组，将不同取值组合成候选；模型模式再结合上下文，判断变化是否已有解释。</p>
<p><a href="docs/TECHNICAL_OVERVIEW.zh-CN.md">阅读技术原理与代码导览</a></p>

<details>
<summary>当前能力范围</summary>
<p>每份稿件最多 30 万字符。离线规则覆盖范围较窄；模型检查对别名、隐含时间关系和上下文之外的解释仍可能漏检或误判。引文核对确认的是出处，无法保证剧情判断必然正确，最终由作者决定。</p>
</details>

<h2 id="source">从源码运行</h2>
<p>Python 3.10+ · PySide6 / Qt Widgets · Windows x64 免安装版。Windows 源码运行方式：</p>
<pre><code>git clone https://github.com/CARL-JOSEPH-LEE/PlotProof.git
cd PlotProof
python -m venv .venv
.venv\Scripts\python -m pip install -e .
.venv\Scripts\python -m plotproof</code></pre>
<p><a href="docs/DEVELOPMENT.md">开发、测试与打包指南</a></p>

<h2>一起让下一稿更好</h2>
<p>发现漏掉的矛盾，或被误报的合理变化？欢迎提交简短故事片段与预期结果。尤其欢迎一起改进别名处理、时间线、模型评测与无障碍体验。</p>
<p><a href="CONTRIBUTING.md">Contributing</a> · <a href="https://github.com/CARL-JOSEPH-LEE/PlotProof/issues">Issues</a> · <a href="docs/VALIDATION.txt">Validation</a></p>

<hr>
<p>应用源码采用 MIT 许可证，随包组件保留各自许可证。 <a href="LICENSE">MIT</a> · <a href="THIRD_PARTY_NOTICES.txt">Third-party notices</a></p>
