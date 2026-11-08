# Book Note

按章节整理中文读书笔记，解释概念、机制、实践方法、研究条件和适用范围，并提供复习问题与自测参考要点。

## 当前内容

[《Protocols》读书笔记目录](Notes/Protocols/README.md)包含七个主题、47 个方案及 57 道自测参考要点。

下载现成的 [EPUB 电子书](Exports/Protocols/Protocols-中文读书笔记.epub)，导入支持 EPUB 的阅读器即可阅读，无需安装 Python 或编译。电子书已包含封面、完整笔记、目录、书内跳转、表格和自测参考要点；外部研究链接需要网络。

HTML 演示共 50 页，默认 35 页分享路线适合约 25–30 分钟。操作与节奏见[演示说明](Presentations/Protocols/README.md)。

## 工程结构

```text
Notes/Protocols/             中文分章笔记、速查和研究资料
Presentations/Protocols/     演示内容、模板、样式、交互和素材
Exports/Protocols/          可直接阅读的 EPUB 与生成脚本
requirements.txt            EPUB 封面生成依赖
THIRD_PARTY_NOTICES.md       第三方素材说明
```

公开工程不包含书籍全文。封面采用自制排版，三个场景照片的来源与许可单独列明。

## 生成 HTML 演示

使用 Python 3.9 或更新版本，无第三方依赖：

```bash
python3 -B Presentations/Protocols/build_deck.py
python3 -B Presentations/Protocols/build_portable.py
```

生成文件：

- `Presentations/Protocols/index.html`：分文件演示，与样式、脚本和素材一起使用。
- `Presentations/Protocols/Protocols-读书分享.html`：可单独发送的离线便携版，内置完整笔记。

## 更新 EPUB（维护者）

读者直接使用上方下载链接。维护者修改笔记后，安装 Pillow 并重新生成：

```bash
python3 -m pip install -r requirements.txt
python3 -B Exports/Protocols/build_epub.py
```

生成 `Exports/Protocols/Protocols-中文读书笔记.epub`，包含完整笔记、章节导航、表格、研究链接和自测参考要点。

封面需要系统中文字体。macOS 自动查找黑体等字体；Linux 可安装 Noto CJK，或通过环境变量 `BOOK_NOTE_CJK_FONT` 指定本地中文字体文件。

## 修改内容

- 笔记：编辑 `Notes/Protocols/` 中对应 Markdown。
- 演示文案与讲解：编辑 `deck_content.py`。
- 演示页面结构：编辑 `template.html`；样式和交互分别在 `theme.css`、`presentation.js`。
- 修改后重新执行相应生成命令。

生成的 HTML 已列入 `.gitignore`。笔记 EPUB 随仓库提供，更新笔记后应重新导出并一起提交，也可附在发布页面供下载。

## 整理原则

1. 按主题组织内容，保留核心问题和必要论据。
2. 方法写清步骤、时间、强度、频率与条件。
3. 区分研究结果、机制假说、实践建议和个人经验。
4. 用复习问题、参考要点和情境应用检验理解。
