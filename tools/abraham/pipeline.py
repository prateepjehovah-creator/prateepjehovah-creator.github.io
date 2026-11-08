#!/usr/bin/env python3
"""Build path for the original Tamil book ஆபிரகாம்: மணல் துகள்களின் பேரரசன்.

Nothing in this tool copies the uncorrected source manuscript. `publish` and
`pdf` refuse to run until an approved edited-manuscript.md is present.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "spec.json").read_text(encoding="utf-8"))
CREDITS_PATH = ROOT / "books" / SPEC["slug"] / "img" / "credits.json"
CHROME = "/usr/local/bin/google-chrome"
CHAPTER_RE = re.compile(r"^அத்தியாயம்[ \t]+(10|[1-9])\b[ \t]*[:.।—–\-]*[ \t]*(.*)$")
HEADING_RE = re.compile(r"^(#{1,3})[ \t]+(.+?)[ \t]*$", re.M)
MALAYALAM_RE = re.compile(r"[\u0D00-\u0D7F]")


class ManuscriptError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def credits() -> dict:
    return json.loads(CREDITS_PATH.read_text(encoding="utf-8"))


def find_manuscript() -> Path | None:
    names = SPEC["manuscript"]["paths"]
    for name in names:
        path = ROOT / name
        if path.is_file():
            return path
    uploads = Path("/home/ubuntu/.cursor/projects")
    if uploads.is_dir():
        found = sorted(uploads.glob("**/edited-manuscript.md"))
        if found:
            return found[0]
    return None


def _sections(text: str) -> list[dict]:
    matches = list(HEADING_RE.finditer(text))
    sections = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append({
            "level": len(match.group(1)),
            "heading": match.group(2).strip(),
            "body": text[start:end].strip(),
        })
    return sections


def _blocks(body: str) -> tuple[list[dict], list[str]]:
    blocks = []
    figures = []
    if not body.strip():
        return blocks, figures
    for part in re.split(r"\n\s*\n", body.strip()):
        lines = [line.rstrip() for line in part.splitlines() if line.strip()]
        if not lines:
            continue
        if all(line.lstrip().startswith(">") for line in lines):
            quote = []
            cite = ""
            for line in lines:
                content = line.lstrip()[1:].strip()
                if content.startswith(("ஆதாரம்:", "சுட்டு:")):
                    cite = content
                elif content:
                    quote.append(content)
            blocks.append({"type": "quote", "text": " ".join(quote), "cite": cite})
            continue
        paragraph = " ".join(line.strip() for line in lines)
        if paragraph.startswith("படம்:"):
            figures.append(paragraph.split(":", 1)[1].strip())
            continue
        if paragraph.startswith("குறிப்பு:"):
            blocks.append({"type": "note", "text": paragraph})
            continue
        if paragraph.startswith("### "):
            blocks.append({"type": "h", "text": paragraph[4:].strip()})
            continue
        blocks.append({"type": "p", "text": paragraph})
    return blocks, figures


def _photo(token: str) -> dict | None:
    token = token.strip()
    for image in credits()["images"]:
        if token in (image["file"], image["slot"], Path(image["file"]).stem):
            return image
    return None


def _figure(image: dict, after: int) -> dict:
    credit = "%s · %s · %s" % (image["artist"], image["license"], image["sourceUrl"])
    return {
        "after": after,
        "src": image["src"],
        "width": image["width"],
        "height": image["height"],
        "alt": "நவீன புகைப்படம். " + image["captionTa"],
        "caption": image["captionTa"],
        "credit": credit,
        "modern": True,
    }


def parse_manuscript(text: str) -> dict:
    errors = []
    if MALAYALAM_RE.search(text):
        errors.append("Malayalam letters are present; the known corrupted duplicate used them.")
    if text.count("\n# ") > 1 or len(re.findall(r"(?m)^# ", text)) > 1:
        errors.append("The title heading appears more than once.")
    sections = _sections(text)
    if not sections or sections[0]["level"] != 1:
        errors.append("The file must open with one # title heading.")
        raise ManuscriptError(errors)
    if sections[0]["heading"] != SPEC["titleTa"]:
        errors.append("Title must be exactly " + SPEC["titleTa"])
    preamble = sections[0]["body"]
    head = "\n".join(text.splitlines()[:40])
    if not any(marker in head or marker in preamble for marker in SPEC["manuscript"]["statusMarkers"]):
        errors.append("Missing approval marker in the first lines (status: approved).")
    if not any(marker in head or marker in preamble for marker in SPEC["manuscript"]["kindMarkers"]):
        errors.append("Missing original-work marker (வகை: மூலநூல்).")
    if "மொழிபெயர்ப்பு" in preamble and "மூலநூல்" not in preamble:
        errors.append("Preamble classifies the book as a translation.")
    if SPEC["authorTa"] not in text:
        errors.append("Author name is missing.")
    if SPEC["publisherTa"] not in text:
        errors.append("Publisher name is missing.")
    chapters = {}
    apparatus = {}
    for section in sections[1:]:
        chapter = CHAPTER_RE.match(section["heading"])
        if chapter:
            number = int(chapter.group(1))
            if number in chapters:
                errors.append("Chapter %s is duplicated." % number)
            chapters[number] = {
                "title": chapter.group(2).strip() or section["heading"],
                "heading": section["heading"],
                "body": section["body"],
            }
            continue
        for name in SPEC["apparatus"]:
            if section["heading"] == name or section["heading"].startswith(name):
                apparatus[name] = section
    for number in range(1, SPEC["chapterCount"] + 1):
        if number not in chapters:
            errors.append("Chapter %s is missing." % number)
        elif len(chapters[number]["body"].strip()) < 20:
            errors.append("Chapter %s has no body." % number)
    for name in SPEC["apparatus"]:
        if name not in apparatus:
            errors.append("Missing section " + name)
        elif len(apparatus[name]["body"].strip()) < 10:
            errors.append("Section %s is empty." % name)
    bodies = [item["body"].strip() for item in chapters.values()]
    for index, body in enumerate(bodies):
        if body and bodies.count(body) > 1:
            errors.append("Chapter body %s is repeated verbatim." % (index + 1))
    if errors:
        raise ManuscriptError(errors)

    ordered = []
    ordered.append(("பதிப்பு", "தலைப்பு மற்றும் பதிப்பு", _imprint_blocks(), []))
    for name in ("முன்னுரை",):
        blocks, figures = _blocks(apparatus[name]["body"])
        ordered.append((name, apparatus[name]["heading"], blocks, figures))
    for number in range(1, 11):
        item = chapters[number]
        blocks, figures = _blocks(item["body"])
        ordered.append(("chapter-%s" % number, "அத்தியாயம் %s — %s" % (number, item["title"]), blocks, figures))
    for name in ("முடிவுரை", "நூற்பட்டியல்"):
        blocks, figures = _blocks(apparatus[name]["body"])
        ordered.append((name, apparatus[name]["heading"], blocks, figures))

    reader_sections = []
    for index, (key, title, blocks, figure_tokens) in enumerate(ordered, start=1):
        content = [block for block in blocks if block["type"] != "figure-request"]
        figures = []
        for token in figure_tokens:
            image = _photo(token)
            if not image:
                raise ManuscriptError(["Unknown picture token: " + token])
            figures.append(_figure(image, max(0, len(content) - 1)))
        paragraphs = []
        for block in content:
            if block.get("text"):
                paragraphs.append(block["text"])
            if block.get("cite"):
                paragraphs.append(block["cite"])
        reader_sections.append({
            "n": index,
            "key": key,
            "title": title,
            "paragraphs": paragraphs,
            "blocks": content,
            "figures": figures,
        })
    gallery = {
        "n": len(reader_sections) + 1,
        "key": "credits",
        "title": "படக் குறிப்புகள்",
        "paragraphs": [
            "இங்குள்ள படங்கள் அனைத்தும் நவீன புகைப்படங்கள் அல்லது இந்தப் பதிப்புக்கான வரைகலை. ஆபிரகாமின் உருவப்படம் எதுவும் இல்லை."
        ],
        "blocks": [{
            "type": "p",
            "text": "இங்குள்ள படங்கள் அனைத்தும் நவீன புகைப்படங்கள் அல்லது இந்தப் பதிப்புக்கான வரைகலை. ஆபிரகாமின் உருவப்படம் எதுவும் இல்லை.",
        }],
        "figures": [_figure(image, 0) for image in credits()["images"]],
    }
    reader_sections.append(gallery)
    preface = apparatus["முன்னுரை"]["body"].strip().split("\n\n")[0].strip()
    return {
        "spec": SPEC,
        "prefaceLead": preface,
        "sections": reader_sections,
    }


def _imprint_blocks() -> list[dict]:
    return [
        {"type": "h", "text": SPEC["titleTa"]},
        {"type": "p", "text": SPEC["authorTa"]},
        {"type": "p", "text": "வெளியீடு: " + SPEC["publisherTa"] + " (" + SPEC["publisherEn"] + ")"},
        {"type": "p", "text": SPEC["year"] + " · மூல நூல். இது மொழிபெயர்ப்பு அல்ல."},
        {"type": "note", "text": "குறிப்பு: படங்கள் நவீன புகைப்படங்கள். ஆபிரகாமின் முகத்தை இந்தப் பதிப்பு காட்டவில்லை."},
    ]


def chapters_document(book: dict, audio_host: str | None) -> dict:
    document = {
        "slug": SPEC["slug"],
        "title_ta": SPEC["titleTa"],
        "artist": SPEC["authorTa"],
        "sections": [],
    }
    if audio_host:
        document["audioHost"] = audio_host
    for section in book["sections"]:
        item = {
            "n": section["n"],
            "title": section["title"],
            "paragraphs": section["paragraphs"],
            "blocks": section["blocks"],
        }
        if section["figures"]:
            item["figures"] = section["figures"]
        document["sections"].append(item)
    return document


def catalog_entry(book: dict, watch: bool) -> dict:
    return {
        "slug": SPEC["slug"],
        "kind": "own_work",
        "titleTa": SPEC["titleTa"],
        "titleEn": SPEC["titleEn"],
        "year": SPEC["year"],
        "originalAuthor": SPEC["authorTa"] + " (" + SPEC["authorEn"] + ")",
        "publisher": SPEC["publisherTa"],
        "descTa": book["prefaceLead"],
        "descEn": "An original Tamil book by %s, published in %s by %s. Ten chapters. This English line names the Tamil work; the book is not a translation." % (SPEC["authorEn"], SPEC["year"], SPEC["publisherEn"]),
        "cover": "/books/%s/cover.jpg" % SPEC["slug"],
        "page": "/books/%s/" % SPEC["slug"],
        "pdf": "/books/%s/%s.pdf" % (SPEC["slug"], SPEC["slug"]),
        "watch": watch,
        "watchEn": False,
    }


def _card(entry: dict, listen: bool, watch: bool) -> str:
    badges = [
        '<a class="badge" href="/read/?b=%s&amp;s=1"><span class="mode-ta" lang="ta">படி</span><span class="mode-en" lang="en">Read</span></a>' % SPEC["slug"]
    ]
    if listen:
        badges.append('<a class="badge" href="/books/%s/#listen"><span class="mode-ta" lang="ta">கேள்</span><span class="mode-en" lang="en">Listen</span></a>' % SPEC["slug"])
    if watch:
        badges.append('<a class="badge" href="/books/%s/#watch"><span class="mode-ta" lang="ta">பார்</span><span class="mode-en" lang="en">Watch</span></a>' % SPEC["slug"])
    return """        <article class="book-card" data-book="%s">
          <figure class="plate">
            <a href="/books/%s/">
              <img src="/books/%s/cover.jpg" width="1200" height="1700" alt="%s — அட்டைப்படம்" loading="lazy" decoding="async">
            </a>
          </figure>
          <div class="card-body">
            <h3 class="book-title">
              <a href="/books/%s/">
                <span class="ta" lang="ta">%s</span>
                <span class="en" lang="en">%s</span>
              </a>
            </h3>
            <p class="byline"><span class="only-ta" lang="ta"><strong>🔵 நீலக்குரல் — உரிமை இழந்த மக்களுக்கான பத்திரிகை</strong><br><small>ஒடுக்கப்பட்டோர் குரல் ★ சமூகநீதிக்கான சமரசமற்ற களப்போராளி ★ சமூகநீதி எழுத்தாளர் ★ மனித உரிமைச் செயற்பாட்டாளர்</small><br><strong>தோழர் நீலம் பி.ஜே.பிரதீப் ஜேசுதாஸ், B.Th.</strong><br><small>&quot;நீலக்குரல்&quot; இணையதளப் பத்திரிகையின் நிறுவனர்</small></span><span class="only-en" lang="en">%s</span></p>
            <p class="meta">%s · மூல நூல்</p>
            <p class="only-ta" lang="ta">%s</p>
            <p class="only-en" lang="en">%s</p>
            <div class="actions">
              <a class="button" href="/books/%s/">
                <span class="only-ta" lang="ta">நூலைத் திற</span>
                <span class="only-en" lang="en">Open the book</span>
              </a>
            </div>
            <p class="mode-badges" aria-label="படி, கேள், பார்">
              %s
            </p>
          </div>
        </article>
""" % (
        SPEC["slug"], SPEC["slug"], SPEC["slug"], html.escape(SPEC["titleTa"]),
        SPEC["slug"], html.escape(SPEC["titleTa"]), html.escape(SPEC["titleEn"]),
        html.escape(SPEC["authorEn"]), SPEC["year"], html.escape(entry["descTa"]),
        html.escape(entry["descEn"]), SPEC["slug"], "\n              ".join(badges),
    )


def book_page(entry: dict, listen: bool, watch: bool) -> str:
    listen_block = """      <section class="block" id="listen">
        <h2><span class="only-ta" lang="ta">கேள்</span><span class="only-en" lang="en">Listen</span></h2>
        <p class="listen-status"><span class="only-ta" lang="ta">அத்தியாய ஒலி இன்னும் இல்லை. உலாவியின் வாசிப்பைப் பதிவு என்று சொல்ல மாட்டோம்.</span><span class="only-en" lang="en">Chapter audio is not ready. Browser speech is not a recording.</span></p>
      </section>"""
    if listen:
        listen_block = """      <section class="block" id="listen" data-listen="%s">
        <h2><span class="only-ta" lang="ta">கேள்</span><span class="only-en" lang="en">Listen</span></h2>
        <p class="listen-status"><span class="only-ta" lang="ta">%s</span><span class="only-en" lang="en">%s</span></p>
        <p class="actions"><button type="button" class="button" data-listen-start="%s"><span class="only-ta" lang="ta">கேட்கத் தொடங்கு</span><span class="only-en" lang="en">Start listening</span></button></p>
      </section>""" % (SPEC["slug"], html.escape(SPEC["media"]["voiceLabelTa"]), html.escape(SPEC["media"]["voiceLabelEn"]), SPEC["slug"])
    watch_block = """      <section class="block" id="watch">
        <h2><span class="only-ta" lang="ta">பார்</span><span class="only-en" lang="en">Watch</span></h2>
        <p><span class="only-ta" lang="ta">காணொலி இன்னும் இல்லை.</span><span class="only-en" lang="en">The video is not ready.</span></p>
      </section>"""
    if watch:
        watch_block = """      <section class="block" id="watch">
        <h2><span class="only-ta" lang="ta">பார்</span><span class="only-en" lang="en">Watch</span></h2>
        <p><span class="only-ta" lang="ta">அத்தியாயக் குறிப்புகளுடன் அமைந்த படக்காட்சி. குரல் செயற்கைக் குரல்.</span><span class="only-en" lang="en">A chaptered slideshow. The voice is synthesized.</span></p>
        <div class="watch-stage" data-watch-slug="%s">
          <div class="watch-frame"><video playsinline preload="metadata" controls controlsList="nodownload noremoteplayback" disablePictureInPicture aria-label="காணொளி / Video"></video></div>
        </div>
      </section>""" % SPEC["slug"]
    figures = []
    for image in credits()["images"]:
        figures.append("""        <figure>
          <img src="%s" width="%s" height="%s" alt="%s" loading="lazy" decoding="async">
          <figcaption><strong>நவீன புகைப்படம்.</strong> %s<br><small>%s · %s · <a href="%s">ஆதாரம்</a></small></figcaption>
        </figure>""" % (
            image["src"], image["width"], image["height"], html.escape(image["captionTa"]),
            html.escape(image["captionTa"]), html.escape(image["artist"]), html.escape(image["license"]),
            html.escape(image["sourceUrl"]),
        ))
    return """<!DOCTYPE html>
<html lang="ta" data-lang="ta">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>%s · %s</title>
  <meta name="description" content="%s">
  <meta name="author" content="%s">
  <link rel="canonical" href="https://prateepjehovah-creator.github.io/books/%s/">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
  <a class="skip" href="#main"><span class="only-ta" lang="ta">உள்ளடக்கத்திற்குச் செல்</span><span class="only-en" lang="en">Skip to content</span></a>
  <header class="site-header">
    <a class="brand" href="/"><span class="only-ta" lang="ta">நீலம்</span><span class="only-en" lang="en">Neelam</span></a>
    <div class="header-tools">
      <a class="nav-link" href="/about/"><span class="only-ta" lang="ta">பற்றி</span><span class="only-en" lang="en">About</span></a>
      <a class="nav-link" href="/contact/"><span class="only-ta" lang="ta">தொடர்பு</span><span class="only-en" lang="en">Contact</span></a>
      <div class="lang-switch" role="group" aria-label="மொழி / Language">
        <button type="button" data-set-lang="ta" aria-pressed="true">தமிழ்</button>
        <button type="button" data-set-lang="en" aria-pressed="false">English</button>
      </div>
    </div>
  </header>
  <main id="main" class="book-layout">
    <div class="wrap">
      <header class="page-hero">
        <a class="back" href="/#books"><span class="only-ta" lang="ta">← நூல்கள்</span><span class="only-en" lang="en">← Books</span></a>
        <h1 class="page-title"><span class="main-ta" lang="ta">%s</span><span class="sub" lang="en">%s</span></h1>
        <p class="byline"><span class="only-ta" lang="ta">%s<br>%s<br>%s</span><span class="only-en" lang="en">%s</span></p>
        <p class="meta">%s · மூல நூல்</p>
        <nav class="modes" aria-label="படி, கேள், பார்">
          <a class="mode-btn" href="/read/?b=%s&amp;s=1"><span class="mode-ta" lang="ta">படி</span><span class="mode-en" lang="en">Read</span></a>
          <a class="mode-btn" href="#listen"><span class="mode-ta" lang="ta">கேள்</span><span class="mode-en" lang="en">Listen</span></a>
          <a class="mode-btn" href="#watch"><span class="mode-ta" lang="ta">பார்</span><span class="mode-en" lang="en">Watch</span></a>
        </nav>
      </header>
      <figure class="plate cover-plate">
        <img src="/books/%s/cover.jpg" width="1200" height="1700" alt="%s — அட்டைப்படம்">
      </figure>
      <div class="prose">
        <p class="only-ta" lang="ta">%s</p>
        <p class="only-en" lang="en">%s</p>
        <p class="actions pdf-download"><a class="button" href="/books/%s/%s.pdf"><span class="only-ta" lang="ta">PDF பதிவிறக்கம்</span><span class="only-en" lang="en">Download PDF</span></a></p>
      </div>
%s
%s
      <section class="block book-credits" id="image-credits">
        <h2><span class="only-ta" lang="ta">படங்கள்</span><span class="only-en" lang="en">Photographs</span></h2>
        <p class="only-ta" lang="ta">இவை இன்றைய இடங்களின் புகைப்படங்கள். ஆபிரகாமின் உருவப்படமாக எதையும் காட்டவில்லை.</p>
        <div class="book-gallery">
%s
        </div>
      </section>
    </div>
  </main>
  <script src="/js/site.js"></script>
  <script src="/js/player.js"></script>
</body>
</html>
""" % (
        html.escape(SPEC["titleTa"]), html.escape(SPEC["titleEn"]), html.escape(entry["descTa"]),
        html.escape(SPEC["authorTa"]), SPEC["slug"], html.escape(SPEC["titleTa"]), html.escape(SPEC["titleEn"]),
        html.escape(SPEC["authorTa"]), html.escape(SPEC["publisherTa"]), SPEC["year"],
        html.escape(SPEC["authorEn"]), SPEC["year"], SPEC["slug"], SPEC["slug"],
        html.escape(SPEC["titleTa"]), html.escape(entry["descTa"]), html.escape(entry["descEn"]),
        SPEC["slug"], SPEC["slug"], listen_block, watch_block, "\n".join(figures),
    )


def pdf_html(book: dict) -> str:
    parts = []
    toc = []
    for section in book["sections"]:
        anchor = "s%s" % section["n"]
        toc.append('<li><a href="#%s">%s</a></li>' % (anchor, html.escape(section["title"])))
        body = []
        for block in section["blocks"]:
            if block["type"] == "h":
                body.append("<h3>%s</h3>" % html.escape(block["text"]))
            elif block["type"] == "quote":
                body.append("<blockquote>%s</blockquote>" % html.escape(block["text"]))
                if block.get("cite"):
                    body.append("<p class='cite'>%s</p>" % html.escape(block["cite"]))
            elif block["type"] == "note":
                body.append("<p class='note'>%s</p>" % html.escape(block["text"]))
            else:
                body.append("<p>%s</p>" % html.escape(block["text"]))
        for figure in section.get("figures") or []:
            src = ROOT.joinpath(figure["src"].lstrip("/")).resolve().as_uri()
            flag = "<strong>நவீன புகைப்படம்.</strong> " if figure.get("modern") else ""
            body.append("<figure><img src='%s' alt='%s'><figcaption>%s%s<br><small>%s</small></figcaption></figure>" % (
                src, html.escape(figure["alt"]), flag, html.escape(figure["caption"]), html.escape(figure["credit"]),
            ))
        parts.append("<section id='%s'><h2>%s</h2>%s</section>" % (anchor, html.escape(section["title"]), "\n".join(body)))
    return """<!DOCTYPE html>
<html lang="ta">
<head>
<meta charset="utf-8">
<title>%s</title>
<style>
@font-face { font-family: "Noto Serif Tamil"; src: url("file:///usr/share/fonts/truetype/noto/NotoSerifTamil-Regular.ttf") format("truetype"); font-weight: 400; }
@font-face { font-family: "Noto Serif Tamil"; src: url("file:///usr/share/fonts/truetype/noto/NotoSerifTamil-Bold.ttf") format("truetype"); font-weight: 700; }
@font-face { font-family: "Noto Sans Tamil"; src: url("file:///usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf") format("truetype"); font-weight: 400; }
@page { size: A5; margin: 14mm 13mm 16mm; }
html { font-family: "Noto Sans Tamil", sans-serif; font-size: 11.5pt; line-height: 1.7; color: #1a2030; }
h1, h2, h3, blockquote { font-family: "Noto Serif Tamil", serif; }
h1 { font-size: 22pt; line-height: 1.25; color: #12224a; }
h2 { font-size: 15pt; line-height: 1.35; color: #12224a; break-after: avoid; }
blockquote { margin: 0.6em 0; padding: 0.4em 0.7em; border-left: 3px solid #a86b3c; background: #f7f1e6; }
.cite, .note, figcaption { font-size: 9.5pt; color: #3c4454; }
img { max-width: 100%%; height: auto; }
figure { break-inside: avoid; margin: 0.8em 0; }
nav a { color: #1a3d78; }
</style>
</head>
<body>
<header>
<p>மூல நூல் · %s</p>
<h1>%s</h1>
<p>%s</p>
<p>%s<br>%s</p>
</header>
<nav id="contents"><h2>பொருளடக்கம்</h2><ol>%s</ol></nav>
%s
</body>
</html>
""" % (
        html.escape(SPEC["titleTa"]), SPEC["year"], html.escape(SPEC["titleTa"]),
        html.escape(SPEC["authorTa"]), html.escape(SPEC["publisherTa"]),
        html.escape(SPEC["publisherEn"]), "".join(toc), "\n".join(parts),
    )


def chrome(args: list[str]) -> None:
    profile = "/tmp/chrome-abraham-profile"
    shutil.rmtree(profile, ignore_errors=True)
    command = [
        CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
        "--user-data-dir=" + profile, "--allow-file-access-from-files", *args,
    ]
    try:
        subprocess.run(command, check=True, timeout=40)
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-f", "chrome-abraham-profile"], check=False)


def write_pdf(book: dict, dest: Path) -> None:
    from weasyprint import HTML
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(".html")
    temp.write_text(pdf_html(book), encoding="utf-8")
    HTML(filename=str(temp)).write_pdf(str(dest))
    temp.unlink(missing_ok=True)


def write_cover(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    png = dest.with_suffix(".png")
    chrome(["--screenshot=" + str(png), "--window-size=1200,1700", "--hide-scrollbars", (HERE / "cover.html").resolve().as_uri()])
    from PIL import Image
    image = Image.open(png).convert("RGB")
    image = image.crop((0, 0, 1200, 1700)) if image.width >= 1200 and image.height >= 1700 else image
    image.save(dest, "JPEG", quality=86, optimize=True)
    png.unlink(missing_ok=True)


def synthesize_sections(book: dict, dest_dir: Path) -> list[Path]:
    import asyncio
    import edge_tts

    dest_dir.mkdir(parents=True, exist_ok=True)
    voice = SPEC["media"]["voice"]
    written = []

    async def one(section: dict) -> None:
        text = "\n".join(section["paragraphs"])
        path = dest_dir / ("%02d.mp3" % section["n"])
        await edge_tts.Communicate(text, voice).save(str(path))
        written.append(path)

    async def run() -> None:
        for section in book["sections"]:
            await one(section)

    asyncio.run(run())
    return written


def write_slideshow(book: dict, audio_dir: Path, dest: Path) -> None:
    """Still-image slideshow with the synthesized narration. Requires real mp3 files."""
    clips = []
    work = dest.parent / "_video_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for section in book["sections"]:
        audio = audio_dir / ("%02d.mp3" % section["n"])
        if not audio.is_file():
            raise ManuscriptError(["Missing audio for section %s" % section["n"]])
        image = None
        for figure in section.get("figures") or []:
            image = ROOT.joinpath(figure["src"].lstrip("/"))
            break
        if image is None:
            image = ROOT / "books" / SPEC["slug"] / "cover.jpg"
        clip = work / ("c%02d.mp4" % section["n"])
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(image), "-i", str(audio),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:v", "libx264", "-tune", "stillimage", "-crf", "30", "-c:a", "aac", "-b:a", "64k",
            "-shortest", "-movflags", "+faststart", str(clip),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        clips.append(clip)
    listing = work / "list.txt"
    listing.write_text("".join("file '%s'\n" % clip for clip in clips), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(dest)], check=True)
    shutil.rmtree(work)


def _insert_catalog(text: str, entry: dict) -> str:
    if '"slug": "%s"' % SPEC["slug"] in text:
        raise ManuscriptError(["Catalog already contains this book."])
    raw = json.dumps(entry, ensure_ascii=False, indent=2)
    indented = "\n".join("    " + line for line in raw.splitlines())
    marker = '\n    {\n      "slug": "adiyogi",'
    if marker not in text:
        raise ManuscriptError(["Could not find the adiyogi catalog entry."])
    return text.replace(marker, "\n" + indented + "," + marker, 1)


def _insert_card(text: str, card: str) -> str:
    if 'data-book="%s"' % SPEC["slug"] in text:
        raise ManuscriptError(["Home page already contains this book."])
    own = text.find('id="my-books"')
    translations = text.find("மொழிபெயர்ப்புகள்")
    idx = text.find('href="/books/adiyogi/"')
    if own < 0 or translations < 0 or not (own < idx < translations):
        raise ManuscriptError(["Could not place the card inside My Books."])
    start = text.rfind("<article", 0, idx)
    return text[:start] + card + text[start:]


def apply_publication(root: Path, book: dict, listen: bool, watch: bool) -> None:
    entry = catalog_entry(book, watch)
    book_dir = root / "books" / SPEC["slug"]
    data_dir = root / "data" / SPEC["slug"]
    book_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "chapters.json").write_text(
        json.dumps(chapters_document(book, "site" if listen else None), ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    (book_dir / "index.html").write_text(book_page(entry, listen, watch), encoding="utf-8")
    info = {
        "slug": SPEC["slug"],
        "title_ta": SPEC["titleTa"],
        "title_en": SPEC["titleEn"],
        "original_author": entry["originalAuthor"],
        "publisher": SPEC["publisherTa"],
        "year": SPEC["year"],
        "kind": "own_work",
        "desc_ta": entry["descTa"],
        "desc_en": entry["descEn"],
        "language": "ta",
    }
    (book_dir / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    catalog_path = root / "books" / "catalog.json"
    catalog_path.write_text(_insert_catalog(catalog_path.read_text(encoding="utf-8"), entry), encoding="utf-8")
    index_path = root / "index.html"
    index_path.write_text(_insert_card(index_path.read_text(encoding="utf-8"), _card(entry, listen, watch)), encoding="utf-8")
    sitemap = root / "sitemap.xml"
    sitemap_text = sitemap.read_text(encoding="utf-8")
    loc = "https://prateepjehovah-creator.github.io/books/%s/" % SPEC["slug"]
    if loc not in sitemap_text:
        sitemap_text = sitemap_text.replace(
            "</urlset>",
            "  <url><loc>%s</loc><lastmod>2026-11-08</lastmod></url>\n</urlset>" % loc,
        )
        sitemap.write_text(sitemap_text, encoding="utf-8")
    feed = root / "feed.xml"
    feed_text = feed.read_text(encoding="utf-8")
    if loc not in feed_text:
        item = """    <item>
      <title>%s · %s</title>
      <link>%s</link>
      <guid isPermaLink="true">%s</guid>
      <pubDate>Sun, 08 Nov 2026 00:00:00 GMT</pubDate>
      <description>%s</description>
    </item>
""" % (SPEC["titleTa"], SPEC["titleEn"], loc, loc, html.escape(entry["descTa"]))
        feed_text = feed_text.replace("<item>", item + "    <item>", 1)
        feed.write_text(feed_text, encoding="utf-8")
    sw = root / "sw.js"
    sw_text = sw.read_text(encoding="utf-8")
    if "/books/%s/" % SPEC["slug"] not in sw_text:
        sw_text = sw_text.replace(
            "];",
            '  "/books/%s/",\n  "/books/%s/index.html",\n];' % (SPEC["slug"], SPEC["slug"]),
            1,
        )
        match = re.search(r'var CACHE = "neelam-shell-v(\d+)";', sw_text)
        if match:
            sw_text = sw_text.replace(match.group(0), 'var CACHE = "neelam-shell-v%s";' % (int(match.group(1)) + 1))
        sw.write_text(sw_text, encoding="utf-8")
    write_pdf(book, book_dir / ("%s.pdf" % SPEC["slug"]))


def require_book() -> dict:
    path = find_manuscript()
    if path is None:
        raise ManuscriptError(["Approved manuscript not found. Refusing to publish."])
    return parse_manuscript(path.read_text(encoding="utf-8"))


def status() -> dict:
    path = find_manuscript()
    report = {
        "slug": SPEC["slug"],
        "titleTa": SPEC["titleTa"],
        "awaitingManuscript": path is None,
        "manuscript": str(path) if path else None,
        "published": (ROOT / "data" / SPEC["slug"] / "chapters.json").exists(),
        "photos": len(credits()["images"]),
    }
    if path is not None:
        try:
            parse_manuscript(path.read_text(encoding="utf-8"))
            report["approved"] = True
        except ManuscriptError as error:
            report["approved"] = False
            report["errors"] = error.errors
    return report


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "status"
    if command == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0 if status()["awaitingManuscript"] or status().get("approved") else 2
    if command == "cover":
        write_cover(ROOT / "books" / SPEC["slug"] / "cover.jpg")
        return 0
    if command == "check":
        text = argv[2] if len(argv) > 2 else ""
        if not text:
            path = find_manuscript()
            if path is None:
                print("waiting")
                return 2
            text = path.read_text(encoding="utf-8")
        parse_manuscript(text if isinstance(text, str) and "\n" in text else Path(text).read_text(encoding="utf-8"))
        print("approved")
        return 0
    if command == "publish":
        book = require_book()
        audio = ROOT / "books" / SPEC["slug"] / "audio"
        video = ROOT / "books" / SPEC["slug"] / "video.mp4"
        listen = audio.is_dir() and any(audio.glob("*.mp3"))
        watch = video.is_file() and video.stat().st_size > 1000
        apply_publication(ROOT, book, listen, watch)
        print("published")
        return 0
    print("Unknown command", command, file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ManuscriptError as error:
        print(error, file=sys.stderr)
        raise SystemExit(2)
