# நீலம் பி.ஜே. பிரதீப் ஜேசுதாஸ்

Personal site for Neelam P.J. Pradeep Jesudas (நீலம் பி.ஜே. பிரதீப் ஜேசுதாஸ்), published with GitHub Pages at [https://prateepjehovah-creator.github.io/](https://prateepjehovah-creator.github.io/).

Plain HTML and CSS. There is no build step. Tamil is the default language; English is on the same pages behind the language switch.

இலவசம்: படிக்க, கேட்க, பார்க்க. Read free, listen, watch — no downloads. The site does not offer PDF or audio download links.

## Add a book

1. Create `books/<slug>/` with `index.html`, `cover.jpg`, and `video.mp4` when a video exists (`video_en.mp4` as well when there is an English cut).
2. On the home page, add a card under என் நூல்கள் / My Books or மொழிபெயர்ப்புகள் / Translations, with read / listen / watch badges.
3. Add the book to `books/catalog.json` and `sitemap.xml`. Do not add `/read/` to the sitemap.
4. Commit the book text as `/data/<slug>/chapters.json` (see the schema below). Section audio is not stored in the repository.

`books/catalog.json` is the list of books. The pages themselves are written in HTML so they can be read with or without JavaScript.

## Book text

`/data/<slug>/chapters.json` is what the reader and the player need:

```json
{
  "slug": "example",
  "title_ta": "தலைப்பு",
  "artist": "நீலம் பி.ஜே.பிரதீப் ஜேசுதாஸ்",
  "sections": [
    {"n": 1, "title": "பகுதி", "duration_sec": 1234, "paragraphs": ["..."]}
  ]
}
```

Titles in English, the public-domain note, and the cover come from `books/catalog.json`. Section audio, when the chapters file exists, is loaded from `releases/download/audio-<slug>/<NN>.mp3` (NN is the section number, two digits). That address is not shown as a link.
