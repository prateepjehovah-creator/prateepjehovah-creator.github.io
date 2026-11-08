#!/usr/bin/env python3
"""Publish the corrected original Tamil book from the editorial master.

Reads books/abraham-manal/source/master.json, which is the corrected chapters
file. It does not read the duplicated uncorrected manuscript.
"""

from __future__ import annotations

import asyncio
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[2]
SLUG = "abraham-manal"
BOOK = ROOT / "books" / SLUG
SOURCE = BOOK / "source" / "master.json"
MANUSCRIPT = BOOK / "source" / "edited-manuscript.md"
VOICE = "ta-IN-ValluvarNeural"
EXPECTED_SHA = "4d510026963265b26a9eb2666fa873c07840bc3d301988188605e0266dae6579"
TITLE = "ஆபிரகாம்: மணல் துகள்களின் பேரரசன்"
SUBTITLE = "விசுவாசம், போர் மற்றும் தெய்வீகத் தேடலின் காவியம்"
AUTHOR = "நீலம் பி.ஜே.பிரதீப் ஜேசுதாஸ்"
PUBLISHER = "ஜெய் பீம் எஜுகேஷனல் அண்ட் சேரிடபிள் டிரஸ்ட்"
PUBLISHER_EN = "Jai Bhim Educational Charitable Trust"

UPLOAD_JSON = Path("/home/ubuntu/.cursor/projects/agent-repos-prateepjehovah-creator-github-io/uploads/chapters_9620.json")
UPLOAD_MD = Path("/home/ubuntu/.cursor/projects/agent-repos-prateepjehovah-creator-github-io/uploads/edited-manuscript_045c.md")


def strip_md(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+)\*(?!\*)", r"\1", text)
    return text.strip()


def blocks_from_markdown(markdown: str) -> list[dict]:
    chunks = []
    for chunk in re.split(r"\n\s*\n", markdown.strip()):
        lines = [line.rstrip() for line in chunk.splitlines() if line.strip()]
        if sum(1 for line in lines if re.match(r"\d+\.\s", line.strip())) >= 2:
            buf: list[str] = []
            for line in lines:
                if re.match(r"\d+\.\s", line.strip()) and buf:
                    chunks.append(" ".join(buf))
                    buf = [line.strip()]
                else:
                    buf.append(line.strip())
            if buf:
                chunks.append(" ".join(buf))
        else:
            chunks.append(" ".join(lines))
    blocks = []
    for chunk in chunks:
        plain = strip_md(chunk)
        if not plain:
            continue
        if plain.startswith("### "):
            blocks.append({"type": "h", "text": strip_md(plain[4:])})
            continue
        if plain.startswith(("வசனத்தின் கருத்து", "ஹதீஸின் கருத்து")):
            blocks.append({"type": "quote", "text": plain})
            continue
        if plain.startswith(("கதைச் சூழல்:", "மரபுச் சூழல்:", "இடைநிலை வாசிப்பு:")):
            blocks.append({"type": "note", "text": plain})
            continue
        blocks.append({"type": "p", "text": plain})
    return blocks


def paragraphs_of(blocks: list[dict]) -> list[str]:
    return [block["text"] for block in blocks if block.get("text")]


def photo_records() -> list[dict]:
    return json.loads((BOOK / "img" / "credits.json").read_text(encoding="utf-8"))["images"]


def figure_from_photo(image: dict, after: int) -> dict:
    return {
        "after": after,
        "src": image["src"],
        "width": image["width"],
        "height": image["height"],
        "alt": "நவீன புகைப்படம். " + image["captionTa"],
        "caption": image["captionTa"],
        "credit": "%s · %s · %s" % (image["artist"], image["license"], image["sourceUrl"]),
        "modern": True,
    }


def place(blocks: list[dict], figures: list[dict], needle: str, image: dict) -> None:
    for index, block in enumerate(blocks):
        if needle in block["text"]:
            figures.append(figure_from_photo(image, index))
            return
    raise SystemExit("Could not place %s near %s" % (image["file"], needle))


def section(n: int, title: str, blocks: list[dict], figures: list[dict] | None = None, kind: str = "") -> dict:
    item = {"n": n, "title": title, "paragraphs": paragraphs_of(blocks), "blocks": blocks}
    if kind:
        item["kind"] = kind
    if figures:
        item["figures"] = figures
    return item


def build_sections(master: dict) -> list[dict]:
    photos = {item["file"]: item for item in photo_records()}
    imprint = [
        {"type": "h", "text": TITLE},
        {"type": "p", "text": SUBTITLE},
        {"type": "p", "text": "ஆசிரியர்: " + AUTHOR},
        {"type": "p", "text": "பதிப்பாளர்: " + PUBLISHER},
        {"type": "p", "text": PUBLISHER_EN},
        {"type": "p", "text": "வெளியீட்டு ஆண்டு: 2026"},
        {"type": "p", "text": "வகை: ஆசிரியரின் சொந்தப் படைப்பு — ஆன்மீகக் கதைநடையும் மரபுகளின் ஒப்பீடும். இது மொழிபெயர்ப்பு அல்ல."},
        {"type": "quote", "text": master["epigraph"]},
    ]
    contents_lines = [
        "முன்னுரை: விசுவாசத்தோடு ஒரு நேர்மையான தேடல்",
    ]
    for chapter in master["chapters"]:
        contents_lines.append(chapter["heading"])
    contents_lines.append(master["conclusion"]["heading"])
    contents_lines.append(master["bibliography"]["heading"])
    contents = [{"type": "p", "text": line} for line in contents_lines]
    preface_blocks = blocks_from_markdown(master["preface"]["markdown"])
    schematic = {
        "after": len(preface_blocks) - 1,
        "src": "/books/abraham-manal/accents/journey.png",
        "width": 880,
        "height": 420,
        "alt": "திசை காட்டும் வரைகலை. அளவீட்டு வரைபடம் அல்ல. ஆபிரகாமின் உருவப்படம் அல்ல.",
        "caption": "ஊர், ஹாரன், காணான், எகிப்து என்ற பெயர்களைக் காட்டும் வரைகலை. அளவீட்டு வரைபடம் அல்ல. நவீன புகைப்படம் அல்ல. ஆபிரகாமின் உருவப்படம் அல்ல.",
        "credit": "இந்தப் பதிப்பிற்கான வரைகலை",
        "modern": False,
    }
    sections = [
        section(1, "தலைப்பு மற்றும் பதிப்பு", imprint, kind="imprint"),
        section(2, "உள்ளடக்கம்", contents, kind="contents"),
        section(3, master["preface"]["heading"], preface_blocks, [schematic], kind="preface"),
    ]
    placements = {
        1: [("யூப்ரடீஸ்", "euphrates.jpg"), ("ஊர் நகரம்", "ur-facade.jpg"), ("ஆரானில்", "harran-houses.jpg")],
        2: [("நட்சத்திரமும்", "night-sky.jpg")],
        3: [("மாரி", "mari-palace.jpg")],
        10: [("மேற்குக் கரையில்", "hebron-shrine.jpg")],
    }
    for chapter in master["chapters"]:
        blocks = blocks_from_markdown(chapter["markdown"])
        figures = []
        for needle, filename in placements.get(chapter["number"], []):
            place(blocks, figures, needle, photos[filename])
        sections.append(section(len(sections) + 1, chapter["heading"], blocks, figures, kind="chapter"))
    sections.append(section(len(sections) + 1, master["conclusion"]["heading"], blocks_from_markdown(master["conclusion"]["markdown"]), kind="conclusion"))
    sections.append(section(len(sections) + 1, master["bibliography"]["heading"], blocks_from_markdown(master["bibliography"]["markdown"]), kind="bibliography"))
    credit_blocks = [{
        "type": "note",
        "text": "படக் குறிப்புகள் — இந்தப் பதிப்பு சேர்த்தது. இது ஆசிரியர் உரையின் பகுதி அல்ல. ஒவ்வொரு புகைப்படமும் நவீன புகைப்படம். ஆபிரகாமின் உருவப்படம் இல்லை.",
    }]
    credit_figures = []
    for filename in ("ur-ziggurat.jpg", "samawa-desert.jpg"):
        image = photos[filename]
        credit_blocks.append({"type": "p", "text": image["captionTa"] + " " + image["artist"] + ". " + image["license"] + ". " + image["sourceUrl"]})
        credit_figures.append(figure_from_photo(image, len(credit_blocks) - 1))
    for image in photo_records():
        if image["file"] in ("ur-ziggurat.jpg", "samawa-desert.jpg"):
            continue
        credit_blocks.append({"type": "p", "text": image["captionTa"] + " " + image["artist"] + ". " + image["license"] + ". " + image["sourceUrl"]})
    sections.append(section(len(sections) + 1, "படக் குறிப்புகள்", credit_blocks, credit_figures, kind="photo-credits"))
    return sections


def assert_complete(master: dict, sections: list[dict]) -> None:
    chapters = [item for item in sections if item.get("kind") == "chapter"]
    if len(chapters) != 10:
        raise SystemExit("expected 10 chapters")
    for chapter, section_item in zip(master["chapters"], chapters):
        if chapter["heading"] != section_item["title"]:
            raise SystemExit("heading mismatch " + chapter["heading"])
        source = re.sub(r"\s+", "", strip_md(chapter["markdown"]).replace("### ", ""))
        built = re.sub(r"\s+", "", "".join(section_item["paragraphs"]))
        if source != built:
            raise SystemExit("Chapter %s text does not match the master" % chapter["number"])
    for part in (master["preface"], master["conclusion"], master["bibliography"]):
        source = re.sub(r"\s+", "", strip_md(part["markdown"]).replace("### ", ""))
        match = next(item for item in sections if item["title"] == part["heading"])
        built = re.sub(r"\s+", "", "".join(match["paragraphs"]))
        if source != built:
            raise SystemExit("Section does not match the master: " + part["heading"])
    notes = " ".join(next(item["paragraphs"] for item in sections if item["kind"] == "bibliography"))
    for number in range(1, 24):
        if not re.search(r"(^|\s)%s\." % number, notes):
            raise SystemExit("missing source note %s" % number)
    joined = "\n".join("\n".join(item["paragraphs"]) for item in sections)
    if "മ" in joined:
        raise SystemExit("Malayalam corruption remains")


def spoken_text(section_item: dict) -> str:
    text = "\n".join(section_item["paragraphs"])
    if section_item.get("kind") == "bibliography":
        text = "ஆதாரக் குறிப்புகள். இணைய முகவரிகள் இந்த ஒலிப்பதிவில் வாசிக்கப்படவில்லை; அவை எழுத்து நூலில் உள்ளன.\n" + re.sub(r"https?://\S+", "", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
    return text


async def synthesize(sections: list[dict], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(3)

    async def one(section_item: dict) -> None:
        path = dest / ("%02d.mp3" % section_item["n"])
        if path.is_file() and path.stat().st_size > 20000:
            print("audio keep", path.name, flush=True)
            return
        async with sem:
            await edge_tts.Communicate(spoken_text(section_item), VOICE).save(str(path))
        print("audio", path.name, path.stat().st_size, flush=True)

    await asyncio.gather(*(one(item) for item in sections))


def duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], text=True)
    return float(out.strip())


def write_cover() -> None:
    import pipeline
    pipeline.write_cover(BOOK / "cover.jpg")


def write_pdf(sections: list[dict]) -> None:
    dest = BOOK / (SLUG + ".pdf")
    import pipeline
    book = {"sections": sections, "prefaceLead": ""}
    pipeline.write_pdf(book, dest)


def write_video(sections: list[dict]) -> None:
    work = BOOK / "_video_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    label = work / "label.mp3"
    asyncio.run(edge_tts.Communicate(
        "செயற்கைக் குரல். இது ஆசிரியரின் குரல் பதிவு அல்ல. படங்கள் நவீன புகைப்படங்கள். ஆபிரகாமின் உருவப்படம் அல்ல.",
        VOICE,
    ).save(str(label)))
    clips = []
    chapters = []
    cursor = 0.0

    def raster(image: Path) -> Path:
        if image.suffix.lower() != ".svg":
            return image
        png = image.with_suffix(".png")
        if not (png.is_file() and png.stat().st_size > 1000):
            import pipeline
            pipeline.chrome([
                "--screenshot=" + str(png), "--window-size=880,420", "--hide-scrollbars",
                image.resolve().as_uri(),
            ])
        return png

    def still(image: Path, audio: Path, start: float, length: float, out: Path) -> None:
        image = raster(image)
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(start), "-t", "%.3f" % length, "-i", str(audio),
            "-loop", "1", "-framerate", "1", "-t", "%.3f" % length, "-i", str(image),
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "33",
            "-c:a", "aac", "-b:a", "64k", "-shortest", "-movflags", "+faststart", str(out),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    label_len = duration(label)
    still(BOOK / "cover.jpg", label, 0, label_len, work / "c00.mp4")
    clips.append(work / "c00.mp4")
    chapters.append((0, int(label_len * 1000), "அறிமுகம் — செயற்கைக் குரல்"))
    cursor = label_len
    for section_item in sections:
        audio = BOOK / "audio" / ("%02d.mp3" % section_item["n"])
        total = duration(audio)
        images = []
        for figure in section_item.get("figures") or []:
            images.append(ROOT.joinpath(figure["src"].lstrip("/")))
        if not images:
            images = [BOOK / "cover.jpg"]
        span = total / len(images)
        for index, image in enumerate(images):
            start = span * index
            length = total - start if index == len(images) - 1 else span
            clip = work / ("s%02d-%d.mp4" % (section_item["n"], index))
            still(image, audio, start, length, clip)
            clips.append(clip)
        chapters.append((int(cursor * 1000), int((cursor + total) * 1000), section_item["title"]))
        cursor += total
        print("clip", section_item["n"], round(total, 1))
    listing = work / "list.txt"
    listing.write_text("".join("file '%s'\n" % clip for clip in clips), encoding="utf-8")
    silent = BOOK / "video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy", "-movflags", "+faststart", str(silent),
    ], check=True)
    meta = work / "chapters.txt"
    lines = [";FFMETADATA1"]
    for start, end, title in chapters:
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", "START=%s" % start, "END=%s" % end, "title=%s" % title]
    meta.write_text("\n".join(lines) + "\n", encoding="utf-8")
    final = work / "marked.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(silent), "-i", str(meta), "-map_metadata", "1",
        "-c", "copy", "-movflags", "+faststart", str(final),
    ], check=True)
    final.replace(silent)
    shutil.rmtree(work)
    print("video", silent.stat().st_size)


def html_page(desc_ta: str) -> str:
    photos = photo_records()
    figures = []
    for image in photos:
        figures.append(
            "<figure><img src=\"%s\" width=\"%s\" height=\"%s\" alt=\"%s\" loading=\"lazy\" decoding=\"async\">"
            "<figcaption><strong>நவீன புகைப்படம்.</strong> %s<br><small>%s · %s · <a href=\"%s\">ஆதாரம்</a></small></figcaption></figure>"
            % (image["src"], image["width"], image["height"], html.escape(image["captionTa"]),
               html.escape(image["captionTa"]), html.escape(image["artist"]), html.escape(image["license"]),
               html.escape(image["sourceUrl"]))
        )
    desc_en = (
        "An original Tamil book by Neelam P.J. Pradeep Jesudas, published in 2026 by Jai Bhim Educational Charitable Trust. "
        "Not a translation. The title’s “emperor” is the author’s metaphor for a legacy of faith."
    )
    return """<!DOCTYPE html>
<html lang="ta" data-lang="ta">
<head>
  <meta charset="utf-8">
  <script>
    try {
      var savedLang = localStorage.getItem("lang");
      if (savedLang === "en" || savedLang === "ta") {
        document.documentElement.setAttribute("data-lang", savedLang);
        document.documentElement.lang = savedLang;
      }
      var savedTheme = localStorage.getItem("theme");
      if (savedTheme === "light" || savedTheme === "dark") {
        document.documentElement.setAttribute("data-theme", savedTheme);
      }
    } catch (e) {}
  </script>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>%s · Abraham: Emperor of the Grains of Sand</title>
  <meta name="description" content="%s">
  <meta name="author" content="%s">
  <link rel="canonical" href="https://prateepjehovah-creator.github.io/books/%s/">
  <meta property="og:type" content="book">
  <meta property="og:title" content="%s">
  <meta property="og:image" content="https://prateepjehovah-creator.github.io/books/%s/cover.jpg">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="manifest" href="/manifest.json">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600&family=Noto+Serif+Tamil:wght@600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>
  <a class="skip" href="#main"><span class="only-ta" lang="ta">உள்ளடக்கத்திற்குச் செல்</span><span class="only-en" lang="en">Skip to content</span></a>
  <header class="site-header">
    <a class="brand" href="/"><span class="only-ta" lang="ta">நீலம்</span><span class="only-en" lang="en">Neelam</span></a>
    <div class="header-tools">
      <a class="nav-link" href="/about/"><span class="only-ta" lang="ta">பற்றி</span><span class="only-en" lang="en">About</span></a>
      <a class="nav-link" href="/contact/"><span class="only-ta" lang="ta">தொடர்பு</span><span class="only-en" lang="en">Contact</span></a>
      <button type="button" class="theme-btn" data-theme-toggle aria-pressed="false"><span class="only-ta" lang="ta">நிறம்</span><span class="only-en" lang="en">Theme</span></button>
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
        <h1 class="page-title"><span class="main-ta" lang="ta">%s</span><span class="sub" lang="en">Abraham: Emperor of the Grains of Sand</span></h1>
        <p class="byline"><span class="only-ta" lang="ta">%s<br>%s<br>2026 · மூல நூல்</span><span class="only-en" lang="en">Neelam P.J. Pradeep Jesudas</span></p>
        <p class="meta">%s</p>
        <nav class="modes" aria-label="படி, கேள், பார்">
          <a class="mode-btn" href="/read/?b=%s&amp;s=1"><span class="mode-ta" lang="ta">படி</span><span class="mode-en" lang="en">Read</span></a>
          <a class="mode-btn" href="#listen"><span class="mode-ta" lang="ta">கேள்</span><span class="mode-en" lang="en">Listen</span></a>
          <a class="mode-btn" href="#watch"><span class="mode-ta" lang="ta">பார்</span><span class="mode-en" lang="en">Watch</span></a>
        </nav>
        <p class="share-note"><span class="only-ta" lang="ta">இலவசம்: படிக்க, கேட்க, பார்க்க.</span><span class="only-en" lang="en">Read free, listen, watch.</span></p>
      </header>
      <figure class="plate cover-plate">
        <img fetchpriority="high" src="/books/%s/cover.jpg" width="1200" height="1700" alt="%s — அட்டைப்படம்">
      </figure>
      <div class="prose">
        <p class="only-ta" lang="ta">%s</p>
        <p class="only-en" lang="en">%s</p>
        <p class="actions pdf-download"><a class="button" href="/books/%s/%s.pdf"><span class="only-ta" lang="ta">PDF பதிவிறக்கம்</span><span class="only-en" lang="en">Download PDF</span></a></p>
      </div>
      <section class="block" id="listen" data-listen="%s">
        <h2><span class="only-ta" lang="ta">கேள்</span><span class="only-en" lang="en">Listen</span></h2>
        <p class="listen-status"><span class="only-ta" lang="ta">செயற்கைக் குரல் (Microsoft ta-IN-ValluvarNeural). இது ஆசிரியரின் குரல் பதிவு அல்ல. ஆதார இணைப்புகள் ஒலிப்பதிவில் வாசிக்கப்படவில்லை; அவை எழுத்து நூலில் உள்ளன.</span><span class="only-en" lang="en">Synthesized narration (Microsoft Tamil voice Valluvar). Not a recording of the author. Web addresses in the notes are not read aloud; they remain in the text.</span></p>
        <p class="actions"><button type="button" class="button" data-listen-start="%s"><span class="only-ta" lang="ta">கேட்கத் தொடங்கு</span><span class="only-en" lang="en">Start listening</span></button></p>
      </section>
      <section class="block" id="watch">
        <h2><span class="only-ta" lang="ta">பார்</span><span class="only-en" lang="en">Watch</span></h2>
        <p><span class="only-ta" lang="ta">அத்தியாயக் குறிப்புகளுடன் அமைந்த படக்காட்சி. குரல் செயற்கைக் குரல். இது பழைய காலத்தைப் படமாக்கிய காணொலி அல்ல. படங்கள் நவீன புகைப்படங்கள்.</span><span class="only-en" lang="en">A chaptered slideshow. The voice is synthesized. This is not filmed historical footage. The pictures are modern photographs.</span></p>
        <div class="watch-stage" data-watch-slug="%s">
          <div class="watch-frame"><video playsinline preload="metadata" controls controlsList="nodownload noremoteplayback" disablePictureInPicture aria-label="காணொளி / Video"></video></div>
        </div>
      </section>
      <section class="block book-credits" id="image-credits">
        <h2><span class="only-ta" lang="ta">படங்கள்</span><span class="only-en" lang="en">Photographs</span></h2>
        <p class="only-ta" lang="ta">இவை இன்றைய இடங்களின் புகைப்படங்கள். ஆபிரகாமின் உருவப்படமாக எதையும் காட்டவில்லை.</p>
        <p class="only-en" lang="en">These are photographs of places today. None is a portrait of Abraham.</p>
        <div class="book-gallery">
%s
        </div>
      </section>
    </div>
  </main>
  <footer class="site-footer"><div class="wrap">
    <p class="only-ta" lang="ta">இலவசம்: படிக்க, கேட்க, பார்க்க.</p>
    <p class="only-en" lang="en">Read free, listen, watch.</p>
  </div></footer>
  <script src="/js/site.js"></script>
  <script src="/js/player.js"></script>
</body>
</html>
""" % (
        html.escape(TITLE), html.escape(desc_ta), html.escape(AUTHOR), SLUG, html.escape(TITLE), SLUG,
        html.escape(TITLE), html.escape(AUTHOR), html.escape(PUBLISHER), html.escape(SUBTITLE),
        SLUG, SLUG, html.escape(TITLE), html.escape(desc_ta), html.escape(desc_en), SLUG, SLUG,
        SLUG, SLUG, SLUG, "\n".join(figures),
    )


def wire(desc_ta: str, desc_en: str) -> None:
    entry_raw = json.dumps({
        "slug": SLUG,
        "kind": "own_work",
        "titleTa": TITLE,
        "titleEn": "Abraham: Emperor of the Grains of Sand",
        "year": "2026",
        "originalAuthor": AUTHOR + " (Neelam P.J. Pradeep Jesudas)",
        "publisher": PUBLISHER,
        "descTa": desc_ta,
        "descEn": desc_en,
        "cover": "/books/%s/cover.jpg" % SLUG,
        "page": "/books/%s/" % SLUG,
        "pdf": "/books/%s/%s.pdf" % (SLUG, SLUG),
        "watch": True,
        "watchEn": False,
    }, ensure_ascii=False, indent=2)
    indented = "\n".join("    " + line for line in entry_raw.splitlines())
    catalog = ROOT / "books" / "catalog.json"
    text = catalog.read_text(encoding="utf-8")
    marker = '\n    {\n      "slug": "adiyogi",'
    if '"slug": "%s"' % SLUG not in text:
        if marker not in text:
            raise SystemExit("catalog marker missing")
        catalog.write_text(text.replace(marker, "\n" + indented + "," + marker, 1), encoding="utf-8")
    index = ROOT / "index.html"
    home = index.read_text(encoding="utf-8")
    if 'data-book="%s"' % SLUG not in home:
        card = """        <article class="book-card" data-book="%s">
          <figure class="plate">
            <a href="/books/%s/"><img src="/books/%s/cover.jpg" width="1200" height="1700" alt="%s — அட்டைப்படம்" loading="lazy" decoding="async"></a>
          </figure>
          <div class="card-body">
            <h3 class="book-title"><a href="/books/%s/"><span class="ta" lang="ta">%s</span><span class="en" lang="en">Abraham: Emperor of the Grains of Sand</span></a></h3>
            <p class="byline"><span class="only-ta" lang="ta"><strong>%s</strong><br>%s</span><span class="only-en" lang="en">Neelam P.J. Pradeep Jesudas</span></p>
            <p class="meta">2026 · மூல நூல்</p>
            <p class="only-ta" lang="ta">%s</p>
            <p class="only-en" lang="en">%s</p>
            <div class="actions"><a class="button" href="/books/%s/"><span class="only-ta" lang="ta">நூலைத் திற</span><span class="only-en" lang="en">Open the book</span></a></div>
            <p class="mode-badges" aria-label="படி, கேள், பார்">
              <a class="badge" href="/read/?b=%s&amp;s=1"><span class="mode-ta" lang="ta">படி</span><span class="mode-en" lang="en">Read</span></a>
              <a class="badge" href="/books/%s/#listen"><span class="mode-ta" lang="ta">கேள்</span><span class="mode-en" lang="en">Listen</span></a>
              <a class="badge" href="/books/%s/#watch"><span class="mode-ta" lang="ta">பார்</span><span class="mode-en" lang="en">Watch</span></a>
            </p>
          </div>
        </article>
""" % (SLUG, SLUG, SLUG, html.escape(TITLE), SLUG, html.escape(TITLE), html.escape(AUTHOR), html.escape(PUBLISHER), html.escape(desc_ta), html.escape(desc_en), SLUG, SLUG, SLUG, SLUG)
        idx = home.find('href="/books/adiyogi/"')
        own = home.find('id="my-books"')
        translations = home.find("மொழிபெயர்ப்புகள்")
        if not (own < idx < translations):
            raise SystemExit("home placement failed")
        start = home.rfind("<article", 0, idx)
        index.write_text(home[:start] + card + home[start:], encoding="utf-8")
    loc = "https://prateepjehovah-creator.github.io/books/%s/" % SLUG
    sitemap = ROOT / "sitemap.xml"
    sm = sitemap.read_text(encoding="utf-8")
    if loc not in sm:
        sitemap.write_text(sm.replace("</urlset>", "  <url><loc>%s</loc><lastmod>2026-11-08</lastmod></url>\n</urlset>" % loc), encoding="utf-8")
    feed = ROOT / "feed.xml"
    feed_text = feed.read_text(encoding="utf-8")
    if loc not in feed_text:
        item = """    <item>
      <title>%s · Abraham: Emperor of the Grains of Sand</title>
      <link>%s</link>
      <guid isPermaLink="true">%s</guid>
      <pubDate>Sun, 08 Nov 2026 00:00:00 GMT</pubDate>
      <description>%s</description>
    </item>
""" % (TITLE, loc, loc, html.escape(desc_ta))
        feed.write_text(feed_text.replace("<item>", item + "    <item>", 1), encoding="utf-8")
    sw = ROOT / "sw.js"
    sw_text = sw.read_text(encoding="utf-8")
    if "/books/%s/" % SLUG not in sw_text:
        sw_text = sw_text.replace("];", '  "/books/%s/",\n  "/books/%s/index.html",\n];' % (SLUG, SLUG), 1)
        match = re.search(r'var CACHE = "neelam-shell-v(\d+)";', sw_text)
        if match:
            sw_text = sw_text.replace(match.group(0), 'var CACHE = "neelam-shell-v%s";' % (int(match.group(1)) + 1), 1)
        sw.write_text(sw_text, encoding="utf-8")


def ensure_source() -> None:
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(UPLOAD_MD.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA:
        raise SystemExit("edited manuscript hash mismatch: " + digest)
    shutil.copy(UPLOAD_MD, MANUSCRIPT)
    shutil.copy(UPLOAD_JSON, SOURCE)


def main() -> None:
    ensure_source()
    master = json.loads(SOURCE.read_text(encoding="utf-8"))
    if master["metadata"]["title"] != TITLE or master["metadata"]["author"] != AUTHOR:
        raise SystemExit("master metadata mismatch")
    if master["metadata"]["is_translation"] or master["metadata"]["classification"] != "original":
        raise SystemExit("master is not marked original")
    sections = build_sections(master)
    assert_complete(master, sections)
    write_cover()
    audio = BOOK / "audio"
    asyncio.run(synthesize(sections, audio))
    for item in sections:
        item["duration_sec"] = int(round(duration(audio / ("%02d.mp3" % item["n"]))))
    document = {
        "slug": SLUG,
        "title_ta": TITLE,
        "artist": AUTHOR,
        "audioHost": "site",
        "sections": [{key: value for key, value in item.items() if key != "kind"} for item in sections],
    }
    data = ROOT / "data" / SLUG
    data.mkdir(parents=True, exist_ok=True)
    (data / "chapters.json").write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # PDF uses the same sections, including durations omitted from layout.
    write_pdf(sections)
    write_video(sections)
    preface = next(item for item in sections if item["kind"] == "preface")
    desc_ta = next(block["text"] for block in preface["blocks"] if block["text"].startswith("இந்த நூல் கிறிஸ்தவ"))
    desc_en = "An original Tamil book by Neelam P.J. Pradeep Jesudas, published in 2026 by Jai Bhim Educational Charitable Trust. Not a translation. The title’s “emperor” is the author’s metaphor for a legacy of faith."
    (BOOK / "index.html").write_text(html_page(desc_ta), encoding="utf-8")
    info = {
        "slug": SLUG,
        "title_ta": TITLE,
        "title_en": "Abraham: Emperor of the Grains of Sand",
        "original_author": AUTHOR,
        "publisher": PUBLISHER,
        "year": "2026",
        "kind": "own_work",
        "desc_ta": desc_ta,
        "desc_en": desc_en,
        "language": "ta",
    }
    (BOOK / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    wire(desc_ta, desc_en)
    print("built", len(sections), "sections")


if __name__ == "__main__":
    main()
