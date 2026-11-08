"""Build an offline HTML deck and embed the chapter notes. No third-party dependencies."""
from pathlib import Path
import base64
import json

HERE = Path(__file__).resolve().parent
NOTES = HERE.parents[1] / "Notes" / "Protocols"


def main():
    document = (HERE / "index.html").read_text(encoding="utf-8")
    document = document.replace('<link rel="stylesheet" href="theme.css">',
                                '<style>\n' + (HERE / "theme.css").read_text(encoding="utf-8") + '\n</style>')
    document = document.replace('<script defer src="presentation.js"></script>', '')
    for name in ["notes-cover.svg", "daylight.jpg", "training.jpg", "writing.jpg"]:
        data = base64.b64encode((HERE / "assets" / name).read_bytes()).decode()
        mime = "image/svg+xml" if name.endswith(".svg") else "image/jpeg"
        document = document.replace('src="assets/' + name + '"', 'src="data:' + mime + ';base64,' + data + '"')
    names = [
        "README.md", "00-导读与全书框架.md", "01-睡眠.md", "02-运动.md",
        "03-压力控制.md", "04-营养.md", "05-光照.md", "06-专注动机与学习.md",
        "07-个人成长.md", "08-全书速查与实践记录.md", "09-研究资料.md",
    ]
    notes = {name: (NOTES / name).read_text(encoding="utf-8") for name in names}
    payload = json.dumps(notes, ensure_ascii=False).replace('<', '\\u003c')
    document = document.replace('</body>',
        '<script id="embedded-notes" type="application/json">' + payload + '</script>\n'
        '<script>\n' + (HERE / "presentation.js").read_text(encoding="utf-8") + '\n</script>\n</body>')
    (HERE / "Protocols-读书分享.html").write_text(document, encoding="utf-8")
    print("Built", HERE / "Protocols-读书分享.html")


if __name__ == '__main__':
    main()
