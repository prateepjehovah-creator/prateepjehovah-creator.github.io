#!/usr/bin/env python3
"""Download a small set of modern photographs and record the licence Wikimedia returns.

Captions are factual labels for those photographs. They are not text from the
manuscript. The script refuses a file whose Commons licence is outside spec.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "books" / "abraham-manal" / "img"
SPEC = json.loads((Path(__file__).resolve().parent / "spec.json").read_text(encoding="utf-8"))
UA = {"User-Agent": "AbrahamBookScaffold/1.0 (educational book design; license verification)"}

CHOICES = [
    {
        "file": "ur-ziggurat.jpg",
        "commons": "File:Great Ziggurat of Ur.JPG",
        "captionTa": "இன்றைய நாசிரிய்யா அருகே உள்ள ஊர் நகரத்தின் பெரிய சீகுராத். நவீன புகைப்படம். ஆபிரகாமின் உருவப்படம் அல்ல; அவர் இங்கு நின்றதற்கான ஆதாரமும் அல்ல.",
        "captionEn": "The Great Ziggurat at Ur, near present-day Nasiriyah. A modern photograph, not a portrait of Abraham and not evidence that he stood here.",
        "slot": "ur",
    },
    {
        "file": "ur-facade.jpg",
        "commons": "File:Ziggarat of Ur 001.jpg",
        "captionTa": "ஊர் சீகுராத்தின் முகப்பு, 2006-இல் எடுக்கப்பட்ட நவீன புகைப்படம். மீட்கப்பட்ட செங்கல் அமைப்பு. ஆபிரகாமின் உருவப்படம் அல்ல.",
        "captionEn": "Facade of the ziggurat at Ur, photographed in 2006. The restored brick structure. Not a portrait of Abraham.",
        "slot": "ur-facade",
    },
    {
        "file": "euphrates.jpg",
        "commons": "File:Euphrates River.jpg",
        "captionTa": "யூப்ரடீஸ் நதிப் பகுதியின் நவீன புகைப்படம். ஆபிரகாமின் உருவப்படம் அல்ல; ஒரு குறிப்பிட்ட பயண நாளைக் காட்டும் படமும் அல்ல.",
        "captionEn": "A modern photograph of the Euphrates river country. Not a portrait of Abraham and not a picture of one dated journey.",
        "slot": "river",
    },
    {
        "file": "samawa-desert.jpg",
        "commons": "File:20160104-Lake in Samawa desert Iraq 0356.jpg",
        "captionTa": "தெற்கு ஈராக்கின் சமாவா பாலைவனத்தில் 2016-இல் எடுக்கப்பட்ட நவீன புகைப்படம். இது ஊர் நகரத்தின் தொல்பதிவுக் காட்சி அல்ல. ஆபிரகாமின் உருவப்படம் அல்ல.",
        "captionEn": "The Samawah desert in southern Iraq, photographed in 2016. Not the Ur excavation and not a portrait of Abraham.",
        "slot": "desert",
    },
    {
        "file": "mari-palace.jpg",
        "commons": "File:Mari (Tell Hariri), Palast des Zimri-Lim, 18 Jhdt.v.Chr. (24834101698).jpg",
        "captionTa": "சிரியாவின் டெல் ஹரிரியில், பண்டைய மாரியின் சிம்ரி-லிம் அரண்மனை இடிபாடுகளின் நவீன புகைப்படம். ஒப்பீட்டுத் தொல்பொருள் பின்னணி. ஆபிரகாமின் சொந்தப் படையையோ வாழ்க்கையையோ நிரூபிக்கும் சான்று அல்ல. ஆபிரகாமின் உருவப்படம் அல்ல.",
        "captionEn": "Modern photograph of the Zimri-Lim palace ruins at Mari (Tell Hariri), Syria. Comparative archaeology, not proof of Abraham's household or army, and not his portrait.",
        "slot": "mari",
    },
    {
        "file": "hebron-shrine.jpg",
        "commons": "File:Cave of the Patriarchs, Hebron 2007.jpg",
        "captionTa": "மேற்குக் கரையில் உள்ள எபிரோன் / அல்-கலீலில் பின்னாளில் கட்டப்பட்ட மூதாதையர் குகை வளாகத்தின் நவீன புகைப்படம் (2007). ஆபிரகாமின் உருவப்படம் அல்ல. உடல் அடையாளம் காணப்பட்ட அகழ்வாய்வுச் சான்றும் அல்ல. எபிரோன் நாட்டு எல்லையில் அல்ல; மேற்குக் கரையில் உள்ளது.",
        "captionEn": "The later shrine over the Cave of the Patriarchs in Hebron / Al-Khalil, in the West Bank, photographed in 2007. Not a portrait of Abraham, not an identification of his remains, and not a picture of an international border.",
        "slot": "hebron",
    },
    {
        "file": "night-sky.jpg",
        "commons": "File:Milky Way Night Sky Black Rock Desert Nevada.jpg",
        "captionTa": "நெவாடாவின் பிளாக் ராக் பாலைவனத்துக்கு மேல் பால்வீதி, 2007. நவீன புகைப்படம். இது ஊர் நகரத்தின் வானம் அல்ல. ஆபிரகாமின் உருவப்படம் அல்ல.",
        "captionEn": "The Milky Way over Black Rock Desert, Nevada, in 2007. A modern night-sky photograph, not the sky over Ur and not a portrait of Abraham.",
        "slot": "stars",
    },
    {
        "file": "harran-houses.jpg",
        "commons": "File:Harran Beehive houses 193.jpg",
        "captionTa": "இன்றைய ஹாரன் பகுதியின் தேன்கூடு வீடுகள், 1997-இல் எடுக்கப்பட்ட நவீன புகைப்படம். பண்டைய ஹாரானின் அரண்மனை அல்ல. ஆபிரகாமின் உருவப்படம் அல்ல.",
        "captionEn": "Beehive houses at present-day Harran, photographed in 1997. Not an ancient palace and not a portrait of Abraham.",
        "slot": "harran",
    },
]


def strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = text.replace("&amp;", "&").replace("&nbsp;", " ").replace("&#039;", "'")
    return re.sub(r"\s+", " ", text).strip()


def commons_info(titles: list[str]) -> dict:
    api = "https://commons.wikimedia.org/w/api.php?"
    params = {
        "action": "query",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "format": "json",
    }
    req = urllib.request.Request(api + urllib.parse.urlencode(params), headers=UA)
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.load(response)
    found = {}
    for page in data["query"]["pages"].values():
        info = page["imageinfo"][0]
        meta = info.get("extmetadata") or {}

        def field(key: str) -> str:
            return strip_html((meta.get(key) or {}).get("value") or "")

        found[page["title"]] = {
            "mime": info.get("mime"),
            "sourceUrl": info.get("descriptionurl"),
            "fileUrl": info.get("url"),
            "license": field("LicenseShortName"),
            "licenseUrl": (meta.get("LicenseUrl") or {}).get("value") or "",
            "artist": field("Artist"),
            "credit": field("Credit"),
            "description": field("ImageDescription"),
        }
    return found


def main() -> None:
    allowed = set(SPEC["photos"]["allowedLicenses"])
    info = commons_info([item["commons"] for item in CHOICES])
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for item in CHOICES:
        meta = info.get(item["commons"])
        if not meta:
            raise SystemExit("Commons returned no record for " + item["commons"])
        if meta["license"] not in allowed:
            raise SystemExit("Licence not allowed for %s: %s" % (item["commons"], meta["license"]))
        if not meta["sourceUrl"].startswith("https://commons.wikimedia.org/"):
            raise SystemExit("Unexpected source URL for " + item["commons"])
        raw = b""
        for attempt in range(5):
            try:
                req = urllib.request.Request(meta["fileUrl"], headers=UA)
                with urllib.request.urlopen(req, timeout=180) as response:
                    raw = response.read()
                break
            except urllib.error.HTTPError as error:
                if error.code != 429 or attempt == 4:
                    raise
                time.sleep(8 * (attempt + 1))
        time.sleep(2)
        image = Image.open(BytesIO(raw))
        image = image.convert("RGB")
        image.thumbnail((1600, 1600))
        dest = OUT / item["file"]
        image.save(dest, "JPEG", quality=82, optimize=True)
        records.append({
            "file": item["file"],
            "src": "/books/abraham-manal/img/" + item["file"],
            "slot": item["slot"],
            "commonsTitle": item["commons"],
            "sourceUrl": meta["sourceUrl"],
            "license": meta["license"],
            "licenseUrl": meta["licenseUrl"],
            "artist": meta["artist"],
            "creditLine": meta["credit"],
            "sourceDescription": meta["description"],
            "captionTa": item["captionTa"],
            "captionEn": item["captionEn"],
            "modernPhotograph": True,
            "portraitOfAbraham": False,
            "width": image.width,
            "height": image.height,
            "bytes": dest.stat().st_size,
        })
        print(item["file"], meta["license"], image.size, dest.stat().st_size)
    payload = {
        "retrieved": "2026-11-08",
        "source": "Wikimedia Commons imageinfo API. Licences below are the values that API returned.",
        "rule": SPEC["photos"]["rule"],
        "images": records,
    }
    (OUT / "credits.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
