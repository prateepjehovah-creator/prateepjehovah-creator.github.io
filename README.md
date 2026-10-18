# நீலம் பி.ஜே. பிரதீப் ஜேசுதாஸ்

Personal site for Neelam P.J. Pradeep Jesudas (நீலம் பி.ஜே. பிரதீப் ஜேசுதாஸ்), published with GitHub Pages at [https://prateepjehovah-creator.github.io/](https://prateepjehovah-creator.github.io/).

Plain HTML and CSS. There is no build step. Tamil is the default language; English is on the same pages behind the language switch.

The books on this site are offered free to read, watch, listen to, and download.

## Add a book

1. Create `books/<slug>/` with `index.html`, `cover.jpg`, and the files (`book.pdf`, and `video.mp4` when there is one). Keep each file under 100 MB.
2. On the home page, add a card under என் நூல்கள் / My Books or மொழிபெயர்ப்புகள் / Translations.
3. Add the book to `books/catalog.json` and `sitemap.xml`.
4. Commit to `main`. GitHub Pages serves this repository from the root of `main`.

`books/catalog.json` is the list of books. The pages themselves are written in HTML so they can be read with or without JavaScript.

## உப்புப் பெட்டி / The Salt Box

- PDF: `books/uppu-petti/uppu-petti.pdf`
- Video: `books/uppu-petti/video.mp4`
- Tamil audiobook chapters: `books/uppu-petti/audio/ch01.mp3` … `ch12.mp3`
- Full Tamil audiobook (chapters 1–12 in one file): GitHub Release `uppu-petti-audiobook`, asset `Uppu-Petti-Tamil-audiobook.mp3`. That file is about 105 MB, so it is not stored in the repository.
