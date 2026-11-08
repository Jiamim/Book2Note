"""Generate the editable HTML presentation from book-sharing copy."""
from pathlib import Path
from html import escape
from deck_content import SLIDES

HERE = Path(__file__).resolve().parent
NOTE_FILES = {1: "01-睡眠.md", 2: "02-运动.md", 3: "03-压力控制.md", 4: "04-营养.md", 5: "05-光照.md", 6: "06-专注动机与学习.md", 7: "07-个人成长.md"}
GROUPS = {1: "睡眠", 2: "运动", 3: "压力控制", 4: "营养", 5: "光照", 6: "专注、动机与学习", 7: "个人成长"}
IMAGES = {
    "daylight.jpg": ("自然日光下的林地", "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8"),
    "training.jpg": ("力量训练场景", "https://images.unsplash.com/photo-1517836357463-d25dfeac3438"),
    "writing.jpg": ("钢笔书写场景", "https://images.unsplash.com/photo-1455390582262-044cdead277a"),
}


def render():
    source = (HERE / "template.html").read_text(encoding="utf-8")
    if source.count("{{SLIDES}}") != 1:
        raise ValueError("The presentation template must contain one {{SLIDES}} marker")
    blocks = []
    for i, s in enumerate(SLIDES, 1):
        chapter = s["chapter"]
        group = f"第 {chapter} 章 · {GROUPS[chapter]}" if chapter else s.get("group", "全书框架")
        title = s["title"]
        cls = "slide" + (" dark" if s.get("dark") else "") + (" photo-slide" if s.get("photo") else "") + (" cover" if i == 1 else "")
        citation = ""
        if chapter:
            citation += f'<a href="../../Notes/Protocols/{NOTE_FILES[chapter]}">完整分章笔记</a>。'
        else:
            citation += '<a href="../../Notes/Protocols/00-导读与全书框架.md">全书导读</a>。'
        photo = ""
        if s.get("photo"):
            name = s["photo"]
            alt, link = IMAGES[name]
            photo = f'<img class="hero-image {name.split(".")[0]}" src="assets/{name}" alt="{alt}">'
            citation += f' 场景图片：<a href="{link}">Unsplash 原图</a>。'
        citation += s.get("extra_refs", "")
        eyebrow = ("深入阅读　" if s.get("detail") else "") + ("读书分享" if i == 1 else group)
        header = "" if i == 1 else f"<h2>{title}</h2>"
        body = s["body"]
        footer = s.get("footer", "方法与数值需结合目标和适用条件")
        notes = "".join(f"<p>{escape(n)}</p>" for n in s["notes"])
        time = "按需展开" if s.get("detail") else "约 40–55 秒"
        if i == 1:
            time = "约 20 秒"
        if i == 35:
            time = "约 1–2 分钟讨论"
        blocks.append(f'''<section class="{cls}" data-id="slide-{i}" data-title="{escape(title)}" data-group="{escape(group)}" data-time="{time}" data-detail="{str(bool(s.get('detail'))).lower()}">
{photo}<header class="slide-header"><p class="eyebrow">{escape(eyebrow)}</p>{header}</header>
<div class="slide-body">{body}</div>
<footer class="slide-footer"><span>{footer}</span><span class="page-number"></span></footer>
<aside class="speaker-note" hidden><div class="notes-text">{notes}</div><div class="notes-citations">{citation}</div></aside>
</section>''')
    doc = source.replace("{{SLIDES}}", "\n\n".join(blocks))
    (HERE / "index.html").write_text(doc, encoding="utf-8")
    print(f"Generated {len(SLIDES)} pages, {sum(not s.get('detail') for s in SLIDES)} sharing pages.")


if __name__ == "__main__":
    render()
