#!/usr/bin/env python3
"""Checks the published corrected book, not the uncorrected duplicate."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLUG = "abraham-manal"
TITLE = "ஆபிரகாம்: மணல் துகள்களின் பேரரசன்"
AUTHOR = "நீலம் பி.ஜே.பிரதீப் ஜேசுதாஸ்"
PUBLISHER = "ஜெய் பீம் எஜுகேஷனல் அண்ட் சேரிடபிள் டிரஸ்ட்"
CHAPTERS = [
    "அத்தியாயம் 1: ஊர் நகரின் கிளர்ச்சியாளன் — நெருப்பைக் கடந்த விசுவாசம்",
    "அத்தியாயம் 2: நட்சத்திரங்களும் எகிப்தியப் பயணமும்",
    "அத்தியாயம் 3: முந்நூற்றுப் பதினெட்டு பேர் — ஒரு குடும்பத்தின் தற்காப்பு",
    "அத்தியாயம் 4: நான்கு அரசர்களுக்கு எதிராக — இரவுத் தாக்குதலின் வியூகம்",
    "அத்தியாயம் 5: மெல்கிசேதேக்கு — வெற்றியின் நடுவே ஒரு சந்திப்பு",
    "அத்தியாயம் 6: சாராள் — காத்திருப்பின் கண்ணீரும் வாக்குத்தத்தத்தின் சிரிப்பும்",
    "அத்தியாயம் 7: மோரியா மலைப்பயணம் — பலிபீடத்தின் முன் ஒரு தந்தை",
    "அத்தியாயம் 8: ஸ்பார்ட்டா வரை நீண்ட ஒரு பெயர் — வரலாற்றில் ஆபிரகாமின் நினைவு",
    "அத்தியாயம் 9: கஅபா — இஸ்லாமிய மரபில் ஆபிரகாமின் சுவடுகள்",
    "அத்தியாயம் 10: இறுதிப் பயணம் — இரு மகன்கள் சந்திக்கும் இடம்",
]


def main() -> None:
    catalog = json.loads((ROOT / "books/catalog.json").read_text(encoding="utf-8"))
    books = catalog["books"]
    entry = next(item for item in books if item["slug"] == SLUG)
    assert books.count(entry) == 1 or sum(1 for item in books if item["slug"] == SLUG) == 1
    assert entry["kind"] == "own_work"
    assert entry["titleTa"] == TITLE
    assert "translator" not in entry
    assert entry["publisher"] == PUBLISHER
    assert entry["watch"] is True and entry["watchEn"] is False
    slugs = [item["slug"] for item in books]
    assert slugs.index(SLUG) < slugs.index("adiyogi")
    kinds = {item["slug"]: item.get("kind") for item in books}
    assert kinds["francisco"] == "public_domain"
    assert kinds["bible-to-quran"] == "own_work"

    home = (ROOT / "index.html").read_text(encoding="utf-8")
    assert home.find('data-book="%s"' % SLUG) < home.find("மொழிபெயர்ப்புகள்")
    assert 'href="/read/?b=%s&amp;s=1"' % SLUG in home
    assert 'href="/books/%s/#listen"' % SLUG in home
    assert 'href="/books/%s/#watch"' % SLUG in home

    page = (ROOT / "books" / SLUG / "index.html").read_text(encoding="utf-8")
    assert 'href="/read/?b=%s&amp;s=1"' % SLUG in page
    assert 'data-listen-start="%s"' % SLUG in page
    assert 'data-watch-slug="%s"' % SLUG in page
    assert "செயற்கைக் குரல்" in page
    assert "ஆசிரியரின் குரல் பதிவு அல்ல" in page
    assert "பழைய காலத்தைப் படமாக்கிய காணொலி அல்ல" in page
    assert "நவீன புகைப்படம்" in page
    assert 'href="/books/%s/%s.pdf"' % (SLUG, SLUG) in page
    assert 'name="viewport"' in page

    data = json.loads((ROOT / "data" / SLUG / "chapters.json").read_text(encoding="utf-8"))
    assert data["title_ta"] == TITLE
    assert data["artist"] == AUTHOR
    assert data["audioHost"] == "site"
    titles = [item["title"] for item in data["sections"]]
    for heading in CHAPTERS:
        assert heading in titles
    assert titles.count(CHAPTERS[0]) == 1
    assert any(item.startswith("முன்னுரை") for item in titles)
    assert any(item.startswith("முடிவுரை") for item in titles)
    assert any(item.startswith("ஆதார") for item in titles)
    joined = "\n".join("\n".join(item["paragraphs"]) for item in data["sections"])
    assert "മ" not in joined
    assert "முந்நூற்றுப் பதினெட்டு" in joined
    assert "நூற்றெழுபத்தைந்து" in joined
    bib = next(item for item in data["sections"] if item["title"].startswith("ஆதார"))
    bib_text = "\n".join(bib["paragraphs"])
    for number in range(1, 24):
        assert "%s." % number in bib_text
    for item in data["sections"]:
        audio = ROOT / "books" / SLUG / "audio" / ("%02d.mp3" % item["n"])
        assert audio.is_file() and audio.stat().st_size > 20000
        assert item["duration_sec"] > 10
        for figure in item.get("figures") or []:
            if figure.get("modern"):
                assert figure["src"].startswith("/books/%s/img/" % SLUG)
                assert "உருவப்படம் அல்ல" in figure["caption"]
                assert "நவீன புகைப்படம்" in figure["alt"]

    video = ROOT / "books" / SLUG / "video.mp4"
    assert video.is_file() and video.stat().st_size > 1000000
    pdf = ROOT / "books" / SLUG / (SLUG + ".pdf")
    assert pdf.is_file() and pdf.stat().st_size > 500000
    from pypdf import PdfReader
    reader = PdfReader(str(pdf))
    assert len(reader.pages) > 20

    def titles_of(nodes):
        found = []
        for node in nodes or []:
            if isinstance(node, list):
                found.extend(titles_of(node))
            elif isinstance(node, dict) and "/Title" in node:
                found.append(str(node["/Title"]))
                if isinstance(node.get("/Count"), int):
                    pass
        return found

    outline = "\n".join(titles_of(reader.outline))
    assert TITLE in outline
    assert "அத்தியாயம் 10:" in outline
    assert "பொருளடக்கம்" in outline
    info = json.loads((ROOT / "books" / SLUG / "info.json").read_text(encoding="utf-8"))
    assert info["kind"] == "own_work"
    print("published ok", len(data["sections"]), "sections", len(reader.pages), "pdf pages")


if __name__ == "__main__":
    main()
