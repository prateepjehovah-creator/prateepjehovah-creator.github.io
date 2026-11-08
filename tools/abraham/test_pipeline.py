#!/usr/bin/env python3
"""Checks for the Abraham book scaffold. The live site must not gain chapter text here."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "abraham"))
import pipeline  # noqa: E402

SPEC = pipeline.SPEC
TITLE = SPEC["titleTa"]


def fixture(extra=""):
    chapters = []
    for number in range(1, 11):
        body = "சோதனை அத்தியாயம் %s தனி வாக்கியம் இங்கே நிற்கிறது." % number
        if number == 1:
            body = "படம்: ur-facade\n\n" + body
        chapters.append("## அத்தியாயம் %s — சோதனை %s\n\n%s" % (number, number, body))
    return """# %s

status: approved
வகை: மூலநூல்
ஆசிரியர்: %s
வெளியீடு: %s
ஆண்டு: 2026

## முன்னுரை

சோதனை முன்னுரை வாக்கியம். இது வெளியீட்டு நூல் அல்ல.

> விண்மீன்களைப் போலவும் மணலைப் போலவும்.
>
> ஆதாரம்: சோதனைச் சுட்டு · கருத்துச் சுருக்கம்

%s

## முடிவுரை

சோதனை முடிவுரை வாக்கியம் இங்கே நிற்கிறது.

## நூற்பட்டியல்

சோதனை நூற்பட்டியல் வரி இங்கே நிற்கிறது.
%s
""" % (TITLE, SPEC["authorTa"], SPEC["publisherTa"], "\n\n".join(chapters), extra)


def test_other_books_unchanged_in_kind():
    kinds = {item["slug"]: item.get("kind") for item in json.loads((ROOT / "books/catalog.json").read_text(encoding="utf-8"))["books"]}
    assert kinds["adiyogi"] == "own_work"
    assert kinds["francisco"] == "public_domain"
    assert kinds.get(SPEC["slug"]) in (None, "own_work")


def test_parser_gates():
    book = pipeline.parse_manuscript(fixture())
    numbers = [section["title"] for section in book["sections"] if section["key"].startswith("chapter-")]
    assert len(numbers) == 10
    assert book["sections"][2]["figures"][0]["modern"] is True
    assert book["sections"][2]["figures"][0]["src"].endswith("ur-facade.jpg")
    try:
        pipeline.parse_manuscript(fixture().replace("status: approved", "status: draft"))
    except pipeline.ManuscriptError as error:
        assert any("approval" in item for item in error.errors)
    else:
        raise AssertionError("draft was accepted")
    try:
        pipeline.parse_manuscript(fixture().replace("வகை: மூலநூல்", "வகை: மொழிபெயர்ப்பு"))
    except pipeline.ManuscriptError:
        pass
    else:
        raise AssertionError("translation marker was accepted")
    duplicated = fixture() + "\n# " + TITLE + "\n"
    try:
        pipeline.parse_manuscript(duplicated)
    except pipeline.ManuscriptError as error:
        assert any("more than once" in item for item in error.errors)
    else:
        raise AssertionError("duplicate title was accepted")
    try:
        pipeline.parse_manuscript(fixture("\nമുന്നൂற்று\n"))
    except pipeline.ManuscriptError as error:
        assert any("Malayalam" in item for item in error.errors)
    else:
        raise AssertionError("Malayalam corruption was accepted")
    missing = fixture().replace("## அத்தியாயம் 7 — சோதனை 7", "## குறிப்பு 7")
    try:
        pipeline.parse_manuscript(missing)
    except pipeline.ManuscriptError as error:
        assert any("Chapter 7" in item for item in error.errors)
    else:
        raise AssertionError("missing chapter was accepted")


def test_photos_and_cover_art():
    data = pipeline.credits()
    allowed = set(SPEC["photos"]["allowedLicenses"])
    assert len(data["images"]) >= 6
    for image in data["images"]:
        path = ROOT / "books" / SPEC["slug"] / "img" / image["file"]
        assert path.is_file() and path.stat().st_size > 20000
        assert image["license"] in allowed
        assert image["sourceUrl"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert image["modernPhotograph"] is True
        assert image["portraitOfAbraham"] is False
        assert "நவீன புகைப்படம்" in image["captionTa"]
        assert "உருவப்படம் அல்ல" in image["captionTa"]
        assert image["artist"]
        assert "உண்மையான புகைப்படம்" not in image["captionTa"]
    art = (ROOT / "books" / SPEC["slug"] / "accents" / "journey.svg").read_text(encoding="utf-8")
    assert "அளவீட்டு வரைபடம் அல்ல" in art
    assert "உருவப்படம் அல்ல" in art
    cover = (ROOT / "tools/abraham/cover.html").read_text(encoding="utf-8")
    assert TITLE in cover
    assert SPEC["authorTa"] in cover
    assert SPEC["publisherTa"] in cover
    assert "<img" not in cover


def test_apply_on_copy_and_pdf():
    book = pipeline.parse_manuscript(fixture())
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relative in ("books/catalog.json", "index.html", "sitemap.xml", "feed.xml", "sw.js"):
            dest = root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, dest)
        catalog_text = (root / "books/catalog.json").read_text(encoding="utf-8")
        catalog_data = json.loads(catalog_text)
        catalog_data["books"] = [item for item in catalog_data["books"] if item.get("slug") != SPEC["slug"]]
        (root / "books/catalog.json").write_text(json.dumps(catalog_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        home = (root / "index.html").read_text(encoding="utf-8")
        home = re.sub(r'\s*<article class="book-card" data-book="%s">.*?</article>\n' % SPEC["slug"], "\n", home, count=1, flags=re.S)
        (root / "index.html").write_text(home, encoding="utf-8")
        pipeline.apply_publication(root, book, listen=False, watch=False)
        page = (root / "books" / SPEC["slug"] / "index.html").read_text(encoding="utf-8")
        home = (root / "index.html").read_text(encoding="utf-8")
        catalog = json.loads((root / "books/catalog.json").read_text(encoding="utf-8"))
        entry = next(item for item in catalog["books"] if item["slug"] == SPEC["slug"])
        assert entry["kind"] == "own_work"
        assert entry["titleTa"] == TITLE
        assert "translator" not in entry
        assert home.find('data-book="%s"' % SPEC["slug"]) < home.find("மொழிபெயர்ப்புகள்")
        assert 'href="/read/?b=%s&amp;s=1"' % SPEC["slug"] in page
        assert "data-listen-start" not in page
        assert "<video" not in page
        assert "செயற்கை" not in page or "இன்னும் இல்லை" in page
        assert "நவீன புகைப்படம்" in page
        chapters = json.loads((root / "data" / SPEC["slug"] / "chapters.json").read_text(encoding="utf-8"))
        chapter_keys = [item["title"] for item in chapters["sections"] if item["title"].startswith("அத்தியாயம்")]
        assert len(chapter_keys) == 10
        assert "audioHost" not in chapters
        pdf = root / "books" / SPEC["slug"] / ("%s.pdf" % SPEC["slug"])
        assert pdf.is_file() and pdf.stat().st_size > 5000
        from pypdf import PdfReader
        reader = PdfReader(str(pdf))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "Charitable Trust" in text
        assert len(reader.pages) >= 2
        outline = json.dumps(reader.outline, ensure_ascii=False, default=str)
        assert "சோதனை" in outline or "அத்தியாயம்" in outline
        info = json.loads((root / "books" / SPEC["slug"] / "info.json").read_text(encoding="utf-8"))
        assert info["kind"] == "own_work"


def test_reader_and_existing_book():
    import os
    os.chdir(ROOT)

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        dump = "/tmp/reader-blocks-dump.html"
        subprocess.run(
            "timeout 15 %s --headless=new --disable-gpu --no-sandbox --user-data-dir=/tmp/chrome-abraham-test --virtual-time-budget=4000 --dump-dom %s > %s"
            % (CHROME(), "http://127.0.0.1:%s/tools/abraham/fixtures/reader-blocks.html" % port, dump),
            shell=True, cwd=ROOT,
        )
        rich = Path(dump).read_text(encoding="utf-8", errors="replace")
        assert 'class="scripture"' in rich
        assert 'class="modern-photo"' in rich
        assert 'class="source-note"' in rich
        assert rich.count("<blockquote") == 1
        assert 'id="plain"' in rich
        adiyogi = (ROOT / "data/adiyogi/chapters.json").read_text(encoding="utf-8")
        assert "கைலாய மலை" in adiyogi
        assert "மணல் துகள்களின் பேரரசன்" not in adiyogi
    finally:
        server.shutdown()


def CHROME():
    return "/usr/local/bin/google-chrome"


def main():
    test_other_books_unchanged_in_kind()
    test_parser_gates()
    test_photos_and_cover_art()
    test_apply_on_copy_and_pdf()
    test_reader_and_existing_book()
    print("ok")


if __name__ == "__main__":
    main()
