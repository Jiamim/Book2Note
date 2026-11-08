"""Package the current Chinese reading notes as an EPUB 3 ebook.

Uses the Python standard library; Pillow is needed only for the PNG cover.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo
import hashlib
import io
import os
import posixpath
import re
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NOTES = ROOT / "Notes" / "Protocols"
OUTPUT = HERE / "Protocols-中文读书笔记.epub"
TITLE = "《Protocols》中文读书笔记"
FILES = [
    "README.md", "00-导读与全书框架.md", "01-睡眠.md", "02-运动.md",
    "03-压力控制.md", "04-营养.md", "05-光照.md", "06-专注动机与学习.md",
    "07-个人成长.md", "08-全书速查与实践记录.md", "09-研究资料.md",
]
PATHS = {name: ("reading-guide.xhtml" if name == "README.md" else f"chapter-{name[:2]}.xhtml") for name in FILES}
XHTML = "http://www.w3.org/1999/xhtml"
EPUB = "http://www.idpf.org/2007/ops"
OPF = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"
NCX = "http://www.daisy.org/z3986/2005/ncx/"
XML = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("", XHTML)
ET.register_namespace("epub", EPUB)

CSS = """
@charset "UTF-8";
html { color: #202a35; background: transparent; }
body { margin: 0 5%; line-height: 1.8; font-family: serif; overflow-wrap: break-word; }
h1, h2, h3, h4 { line-height: 1.4; font-family: sans-serif; font-weight: bold; }
h1 { font-size: 1.8em; margin: 1.4em 0 1.2em; color: #17384a; }
h2 { font-size: 1.35em; margin-top: 1.8em; padding-bottom: .25em; border-bottom: 1px solid #98adb6; }
h3 { font-size: 1.15em; margin-top: 1.5em; }
h4 { font-size: 1em; margin-top: 1.3em; }
p { margin: .8em 0; text-align: justify; }
a { color: #1b6171; text-decoration: underline; }
li { margin: .5em 0; }
table { width: 100%; border-collapse: collapse; margin: 1.1em 0; font-size: .85em; line-height: 1.55; }
th, td { border: 1px solid #a8b6bc; padding: .45em .5em; vertical-align: top; text-align: left; }
th { background: #e9eff0; font-family: sans-serif; }
thead { display: table-header-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #edf1f2; padding: .8em; font-size: .85em; line-height: 1.55; }
code { font-family: monospace; font-size: .92em; }
blockquote { margin: 1em; padding-left: 1em; border-left: 3px solid #90adb7; }
nav.chapter-links { margin: 2em 0 1em; padding-top: .7em; border-top: 1px solid #98adb6; font-size: .85em; text-align: center; }
nav.chapter-links a { margin: 0 .45em; }
body.cover { margin: 0; padding: 0; text-align: center; }
.cover img { display: block; width: 100%; max-width: 100%; height: auto; }
nav#toc li { margin: .35em 0; }
nav#toc > ol { padding-left: 1.5em; }
nav#toc ol ol { font-size: .95em; }
"""


def element(tag: str, text: str | None = None, **attrs: str) -> ET.Element:
    result = ET.Element(f"{{{XHTML}}}{tag}", attrs)
    result.text = text
    return result


def add_text(parent: ET.Element, text: str) -> None:
    if len(parent):
        parent[-1].tail = (parent[-1].tail or "") + text
    else:
        parent.text = (parent.text or "") + text


def inline(parent: ET.Element, source: str) -> None:
    """Parse the inline syntax used by these notes without flattening markup."""
    at = 0
    while at < len(source):
        if source[at] == "`":
            end = source.find("`", at + 1)
            if end >= 0:
                parent.append(element("code", source[at + 1:end]))
                at = end + 1
                continue
        if source[at] == "[":
            end_label = source.find("](", at + 1)
            if end_label >= 0:
                end_url = source.find(")", end_label + 2)
                if end_url >= 0:
                    anchor = element("a", href=source[end_label + 2:end_url])
                    inline(anchor, source[at + 1:end_label])
                    parent.append(anchor)
                    at = end_url + 1
                    continue
        marker = "**" if source.startswith("**", at) else ("*" if source[at] == "*" else "")
        if marker:
            end = source.find(marker, at + len(marker))
            if end > at + len(marker):
                child = element("strong" if marker == "**" else "em")
                inline(child, source[at + len(marker):end])
                parent.append(child)
                at = end + len(marker)
                continue
        add_text(parent, source[at])
        at += 1


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*", line))


def markdown(source: str) -> tuple[ET.Element, list[tuple[int, str, str]]]:
    article = element("article")
    headings: list[tuple[int, str, str]] = []
    lines = source.splitlines()
    index = 0

    def block(line: str) -> bool:
        return bool(re.match(r"^(#{1,6})\s|^```|^\s*\||^[-*+]\s|^\d+\.\s|^>\s", line))

    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            level, text = len(heading[1]), heading[2]
            target_id = f"heading-{len(headings) + 1:03}"
            node = element(f"h{level}", id=target_id)
            inline(node, text)
            article.append(node)
            headings.append((level, "".join(node.itertext()), target_id))
            index += 1
            continue
        if line.startswith("```"):
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            if index == len(lines):
                raise ValueError("Unclosed fenced code block")
            node = element("pre")
            node.append(element("code", "\n".join(code)))
            article.append(node)
            index += 1
            continue
        if line.lstrip().startswith("|"):
            if index + 1 >= len(lines) or not table_separator(lines[index + 1]):
                raise ValueError(f"Missing table header separator: {line}")
            table = element("table")
            head = element("thead")
            row = element("tr")
            count = len(table_cells(line))
            for text in table_cells(line):
                cell = element("th", scope="col")
                inline(cell, text)
                row.append(cell)
            head.append(row)
            table.append(head)
            body = element("tbody")
            index += 2
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                cells = table_cells(lines[index])
                if len(cells) != count:
                    raise ValueError(f"Inconsistent table column count: {lines[index]}")
                row = element("tr")
                for text in cells:
                    cell = element("td")
                    inline(cell, text)
                    row.append(cell)
                body.append(row)
                index += 1
            table.append(body)
            article.append(table)
            continue
        ordered = re.match(r"^(\d+)\.\s+(.+)$", line)
        unordered = re.match(r"^[-*+]\s+(.+)$", line)
        if ordered or unordered:
            pattern = r"^(\d+)\.\s+(.+)$" if ordered else r"^[-*+]\s+(.+)$"
            node = element("ol" if ordered else "ul")
            expected = int(ordered[1]) if ordered else 1
            if ordered and expected != 1:
                node.set("start", str(expected))
            while index < len(lines):
                match = re.match(pattern, lines[index])
                if not match:
                    break
                item = element("li")
                if ordered and int(match[1]) != expected:
                    item.set("value", match[1])
                inline(item, match[2] if ordered else match[1])
                node.append(item)
                expected += 1
                index += 1
            article.append(node)
            continue
        if line.startswith("> "):
            node = element("blockquote")
            paragraph = element("p")
            inline(paragraph, line[2:])
            node.append(paragraph)
            article.append(node)
            index += 1
            continue
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not block(lines[index]):
            paragraph.append(lines[index])
            index += 1
        node = element("p")
        inline(node, " ".join(paragraph))
        article.append(node)
    return article, headings


def plain_document(title: str, body: ET.Element, **body_attrs: str) -> ET.Element:
    document = element("html", lang="zh-CN")
    document.set(f"{{{XML}}}lang", "zh-CN")
    head = element("head")
    head.append(element("title", title))
    head.append(element("meta", charset="utf-8"))
    head.append(element("link", rel="stylesheet", type="text/css", href="styles.css"))
    document.append(head)
    wrapper = element("body", **body_attrs)
    wrapper.append(body)
    document.append(wrapper)
    return document


def serialize(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def rewrite_links(article: ET.Element, heading_map: dict[str, list[tuple[int, str, str]]]) -> None:
    for anchor in article.iter(f"{{{XHTML}}}a"):
        href = anchor.get("href", "")
        target = urlsplit(href)
        if target.scheme or target.netloc:
            if target.scheme not in {"http", "https", "mailto"}:
                raise ValueError(f"Unsupported link: {href}")
            continue
        name = unquote(target.path)
        if name not in PATHS:
            raise ValueError(f"Unmapped local note link: {href}")
        fragment = target.fragment
        if fragment:
            matches = [h for h in heading_map[name] if h[1] == unquote(fragment)]
            if not matches:
                raise ValueError(f"Unmapped note fragment: {href}")
            fragment = matches[0][2]
        anchor.set("href", urlunsplit(("", "", PATHS[name], "", fragment)))


def make_cover() -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    canvas = Image.new("RGB", (1200, 1600), "#102d40")
    draw = ImageDraw.Draw(canvas)
    fonts = [
        os.environ.get("BOOK_NOTE_CJK_FONT", ""),
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    font_path = next((Path(p) for p in fonts if p and Path(p).is_file()), None)
    if font_path is None:
        raise FileNotFoundError("A CJK font is required for the ebook cover")
    font = lambda size: ImageFont.truetype(str(font_path), size)
    draw.rectangle((85, 100, 1115, 1500), outline="#678797", width=2)
    draw.rectangle((132, 158, 246, 172), fill="#d6a26d")
    draw.text((126, 257), "PROTOCOLS", font=font(106), fill="#f2eee7")
    draw.text((132, 429), "中文读书笔记", font=font(100), fill="#f2eee7")
    draw.text((135, 609), "七个主题 · 47 个方案", font=font(39), fill="#b3c8d0")
    for at, label in enumerate(["理解机制", "选择方法", "检验掌握"]):
        top = 861 + at * 129
        draw.text((137, top + 8), f"0{at + 1}", font=font(33), fill="#d6a26d")
        draw.text((232, top), label, font=font(53), fill="#f2eee7")
    draw.text((137, 1370), "睡眠 · 运动 · 压力 · 营养 · 光照 · 学习 · 成长", font=font(27), fill="#b3c8d0")
    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def navigation(sections: list[tuple[str, list[tuple[int, str, str]]]]) -> ET.Element:
    nav = element("nav", id="toc")
    nav.set(f"{{{EPUB}}}type", "toc")
    nav.append(element("h1", "目录"))
    outer = element("ol")
    for name, headings in sections:
        row = element("li")
        label = "阅读说明" if name == "README.md" else headings[0][1]
        row.append(element("a", label, href=PATHS[name] + "#" + headings[0][2]))
        stack: list[tuple[int, ET.Element, ET.Element | None]] = [(1, row, None)]
        for level, text, fragment in headings[1:]:
            while len(stack) > 1 and stack[-1][0] >= level:
                stack.pop()
            parent_level, parent_row, children = stack[-1]
            if children is None:
                children = element("ol")
                parent_row.append(children)
                stack[-1] = (parent_level, parent_row, children)
            child_row = element("li")
            child_row.append(element("a", text, href=PATHS[name] + "#" + fragment))
            children.append(child_row)
            stack.append((level, child_row, None))
        outer.append(row)
    nav.append(outer)
    landmarks = element("nav")
    landmarks.set(f"{{{EPUB}}}type", "landmarks")
    landmarks.append(element("h2", "阅读入口"))
    entries = element("ol")
    for title, path, kind in [("封面", "cover.xhtml", "cover"), ("导读", PATHS[FILES[1]], "bodymatter")]:
        item = element("li")
        link = element("a", title, href=path)
        link.set(f"{{{EPUB}}}type", kind)
        item.append(link)
        entries.append(item)
    landmarks.append(entries)
    wrapper = element("section")
    wrapper.extend([nav, landmarks])
    return plain_document("目录", wrapper)


def ncx(identifier: str, sections: list[tuple[str, list[tuple[int, str, str]]]]) -> bytes:
    root = ET.Element(f"{{{NCX}}}ncx", {"version": "2005-1", f"{{{XML}}}lang": "zh-CN"})
    head = ET.SubElement(root, f"{{{NCX}}}head")
    for name, value in [("dtb:uid", identifier), ("dtb:depth", "1"), ("dtb:totalPageCount", "0"), ("dtb:maxPageNumber", "0")]:
        ET.SubElement(head, f"{{{NCX}}}meta", name=name, content=value)
    title = ET.SubElement(root, f"{{{NCX}}}docTitle")
    ET.SubElement(title, f"{{{NCX}}}text").text = TITLE
    nav_map = ET.SubElement(root, f"{{{NCX}}}navMap")
    for index, (name, headings) in enumerate(sections, 1):
        point = ET.SubElement(nav_map, f"{{{NCX}}}navPoint", id=f"nav-{index}", playOrder=str(index))
        label = ET.SubElement(point, f"{{{NCX}}}navLabel")
        ET.SubElement(label, f"{{{NCX}}}text").text = "阅读说明" if name == "README.md" else headings[0][1]
        ET.SubElement(point, f"{{{NCX}}}content", src=PATHS[name] + "#" + headings[0][2])
    return serialize(root)


def validate(resources: dict[str, bytes]) -> None:
    documents = {name: ET.fromstring(data) for name, data in resources.items() if name.endswith((".xhtml", ".ncx"))}
    for name, document in list(documents.items()):
        ids = [node.get("id") for node in document.iter() if node.get("id")]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate ID in {name}")
        for node in document.iter():
            for attr in ("href", "src"):
                value = node.get(attr)
                if not value:
                    continue
                url = urlsplit(value)
                if url.scheme or url.netloc:
                    continue
                dest = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(url.path))) if url.path else name
                if dest not in resources:
                    raise ValueError(f"Broken link: {name} -> {value}")
                if url.fragment:
                    if dest not in documents or not any(n.get("id") == unquote(url.fragment) for n in documents[dest].iter()):
                        raise ValueError(f"Broken fragment: {name} -> {value}")


def main() -> None:
    parsed: dict[str, tuple[ET.Element, list[tuple[int, str, str]]]] = {}
    digest = hashlib.sha256()
    for name in FILES:
        source = (NOTES / name).read_text(encoding="utf-8")
        digest.update(name.encode())
        digest.update(source.encode())
        parsed[name] = markdown(source)
    heading_map = {name: parts[1] for name, parts in parsed.items()}
    identifier = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "protocols-chinese-notes:" + digest.hexdigest()))
    sections = [(name, heading_map[name]) for name in FILES]
    resources: dict[str, bytes] = {"EPUB/styles.css": CSS.encode(), "EPUB/cover.png": make_cover()}
    cover = element("section")
    cover.set(f"{{{EPUB}}}type", "cover")
    cover.append(element("img", src="cover.png", alt=TITLE + "：理解机制、选择方法、检验掌握"))
    resources["EPUB/cover.xhtml"] = serialize(plain_document(TITLE + "·封面", cover, **{"class": "cover"}))
    for index, name in enumerate(FILES):
        article, headings = parsed[name]
        rewrite_links(article, heading_map)
        footer = element("nav", **{"class": "chapter-links", "aria-label": "章节导航"})
        if index:
            footer.append(element("a", "上一章", href=PATHS[FILES[index - 1]]))
        footer.append(element("a", "目录", href="nav.xhtml#toc"))
        if index + 1 < len(FILES):
            footer.append(element("a", "下一章", href=PATHS[FILES[index + 1]]))
        article.append(footer)
        resources["EPUB/" + PATHS[name]] = serialize(plain_document(headings[0][1], article))
    resources["EPUB/nav.xhtml"] = serialize(navigation(sections))
    resources["EPUB/toc.ncx"] = ncx(identifier, sections)
    package = ET.Element(f"{{{OPF}}}package", version="3.0", **{"unique-identifier": "book-id"})
    metadata = ET.SubElement(package, f"{{{OPF}}}metadata")
    ET.SubElement(metadata, f"{{{DC}}}identifier", id="book-id").text = identifier
    ET.SubElement(metadata, f"{{{DC}}}title").text = TITLE
    ET.SubElement(metadata, f"{{{DC}}}language").text = "zh-CN"
    ET.SubElement(metadata, f"{{{DC}}}description").text = "七个主题、47 个方案，包含概念机制、实践方法、研究条件、57 道自测参考要点与全书速查。"
    ET.SubElement(metadata, f"{{{OPF}}}meta", property="dcterms:modified").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ET.SubElement(metadata, f"{{{OPF}}}meta", name="cover", content="cover-image")
    manifest = ET.SubElement(package, f"{{{OPF}}}manifest")
    ET.SubElement(manifest, f"{{{OPF}}}item", id="style", href="styles.css", **{"media-type": "text/css"})
    ET.SubElement(manifest, f"{{{OPF}}}item", id="cover-image", href="cover.png", properties="cover-image", **{"media-type": "image/png"})
    ET.SubElement(manifest, f"{{{OPF}}}item", id="cover", href="cover.xhtml", **{"media-type": "application/xhtml+xml"})
    ET.SubElement(manifest, f"{{{OPF}}}item", id="nav", href="nav.xhtml", properties="nav", **{"media-type": "application/xhtml+xml"})
    ET.SubElement(manifest, f"{{{OPF}}}item", id="ncx", href="toc.ncx", **{"media-type": "application/x-dtbncx+xml"})
    for index, name in enumerate(FILES):
        ET.SubElement(manifest, f"{{{OPF}}}item", id=f"text-{index}", href=PATHS[name], **{"media-type": "application/xhtml+xml"})
    spine = ET.SubElement(package, f"{{{OPF}}}spine", toc="ncx")
    ET.SubElement(spine, f"{{{OPF}}}itemref", idref="cover", linear="yes")
    ET.SubElement(spine, f"{{{OPF}}}itemref", idref="nav", linear="yes")
    for index in range(len(FILES)):
        ET.SubElement(spine, f"{{{OPF}}}itemref", idref=f"text-{index}", linear="yes")
    resources["EPUB/package.opf"] = serialize(package)
    container = ET.Element("container", version="1.0", xmlns="urn:oasis:names:tc:opendocument:xmlns:container")
    rootfiles = ET.SubElement(container, "rootfiles")
    ET.SubElement(rootfiles, "rootfile", **{"full-path": "EPUB/package.opf", "media-type": "application/oebps-package+xml"})
    resources["META-INF/container.xml"] = serialize(container)
    validate(resources)
    temporary = OUTPUT.with_suffix(".epub.tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            mime = ZipInfo("mimetype")
            mime.compress_type = ZIP_STORED
            archive.writestr(mime, b"application/epub+zip")
            for name, data in resources.items():
                archive.writestr(name, data)
        temporary.replace(OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Built {OUTPUT}")
    print(f"11 note documents, {sum(len(h) for h in heading_map.values())} heading targets; {OUTPUT.stat().st_size:,} bytes. No preview performed.")


if __name__ == "__main__":
    main()
