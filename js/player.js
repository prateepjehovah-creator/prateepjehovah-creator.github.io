/* Read, listen, and watch. No download links are written into the page.
   Blocking the context menu, selection, and printing is deterrence only.
   A determined person can still copy text from the network response. */
(function () {
  /* Section n of book <slug> is served from this release pattern.
     NN is the section number, zero-padded to two digits. */
  var AUDIO_RELEASE = "https://github.com/prateepjehovah-creator/prateepjehovah-creator.github.io/releases/download/audio-";

  var speeds = [0.75, 1, 1.25, 1.5, 1.75, 2];
  var catalogPromise = null;
  var book = null;
  var sectionIndex = 0;
  var sleepTimer = null;
  var sleepEnds = 0;
  var saveTick = 0;

  function isLocal() {
    return location.hostname === "localhost" || location.hostname === "127.0.0.1";
  }

  function audioBase() {
    if (isLocal()) {
      var override = new URLSearchParams(location.search).get("audioBase");
      if (override) return override;
    }
    return AUDIO_RELEASE;
  }

  function pad2(n) {
    n = parseInt(n, 10) || 0;
    return (n < 10 ? "0" : "") + n;
  }

  function audioUrl(slug, n) {
    return audioBase() + slug + "/" + pad2(n) + ".mp3";
  }

  function videoUrl(slug, lang) {
    return "/books/" + slug + "/" + (lang === "en" ? "video_en.mp4" : "video.mp4");
  }

  function safeSlug(value) {
    return /^[a-z0-9-]{1,80}$/.test(value || "") ? value : "";
  }

  function lang() {
    return document.documentElement.getAttribute("data-lang") === "en" ? "en" : "ta";
  }

  function readJson(key) {
    try {
      var raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function writeJson(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {}
  }

  function clock(seconds) {
    seconds = Math.max(0, Math.floor(seconds || 0));
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    var s = seconds % 60;
    var mm = (m < 10 && h ? "0" : "") + m;
    var ss = (s < 10 ? "0" : "") + s;
    return h ? h + ":" + mm + ":" + ss : m + ":" + ss;
  }

  function loadCatalog() {
    if (!catalogPromise) {
      catalogPromise = fetch("/books/catalog.json").then(function (res) {
        if (!res.ok) throw new Error("catalog");
        return res.json();
      }).catch(function () {
        return { books: [] };
      });
    }
    return catalogPromise;
  }

  function catalogBook(slug) {
    return loadCatalog().then(function (data) {
      var books = data.books || [];
      for (var i = 0; i < books.length; i++) {
        if (books[i].slug === slug) return books[i];
      }
      return null;
    });
  }

  function loadChapters(slug) {
    return fetch("/data/" + slug + "/chapters.json", { cache: "no-store" }).then(function (res) {
      if (!res.ok) return null;
      return res.json();
    }).catch(function () {
      return null;
    });
  }

  function currentSection() {
    if (!book || !book.sections || !book.sections.length) return null;
    return book.sections[sectionIndex] || book.sections[0];
  }

  function ensurePlayer() {
    var existing = document.getElementById("listen-player");
    if (existing) return existing;
    var root = document.createElement("section");
    root.id = "listen-player";
    root.className = "player";
    root.hidden = true;
    root.setAttribute("aria-label", "கேட்பொலி / Audio");
    root.innerHTML = ''
      + '<audio id="listen-audio" preload="metadata" controlsList="nodownload"></audio>'
      + '<div class="player-section-list" id="player-sections" hidden></div>'
      + '<div class="player-row">'
      + '  <button type="button" class="player-btn" id="player-toggle" aria-pressed="false">'
      + '    <span class="when-paused"><span class="only-ta" lang="ta">இயக்கு</span><span class="only-en" lang="en">Play</span></span>'
      + '    <span class="when-playing" hidden><span class="only-ta" lang="ta">நிறுத்து</span><span class="only-en" lang="en">Pause</span></span>'
      + '  </button>'
      + '  <button type="button" class="player-btn" id="player-back" aria-label="15 வினாடி பின் / Back 15 seconds">−15</button>'
      + '  <button type="button" class="player-btn" id="player-forward" aria-label="15 வினாடி முன் / Forward 15 seconds">+15</button>'
      + '  <div class="player-meta">'
      + '    <p class="player-title" id="player-title"></p>'
      + '    <p class="player-sub" id="player-sub"></p>'
      + '    <label class="player-seek-label" for="player-seek">'
      + '      <span class="only-ta" lang="ta">நிலை</span><span class="only-en" lang="en">Position</span>'
      + '    </label>'
      + '    <input id="player-seek" class="player-seek" type="range" min="0" max="1000" value="0" step="1">'
      + '    <p class="player-time"><span id="player-now">0:00</span> / <span id="player-dur">0:00</span></p>'
      + '  </div>'
      + '  <label class="player-select" for="player-speed"><span class="only-ta" lang="ta">வேகம்</span><span class="only-en" lang="en">Speed</span>'
      + '    <select id="player-speed"></select>'
      + '  </label>'
      + '  <label class="player-select" for="player-sleep"><span class="only-ta" lang="ta">தூக்கம்</span><span class="only-en" lang="en">Sleep</span>'
      + '    <select id="player-sleep">'
      + '      <option value="0">Off</option>'
      + '      <option value="15">15</option>'
      + '      <option value="30">30</option>'
      + '      <option value="45">45</option>'
      + '      <option value="60">60</option>'
      + '    </select>'
      + '  </label>'
      + '  <button type="button" class="player-btn" id="player-list" aria-expanded="false" aria-controls="player-sections">'
      + '    <span class="only-ta" lang="ta">பகுதிகள்</span><span class="only-en" lang="en">Sections</span>'
      + '  </button>'
      + '</div>'
      + '<p class="player-status" id="player-status" role="status"></p>';
    document.body.appendChild(root);
    var speed = root.querySelector("#player-speed");
    for (var i = 0; i < speeds.length; i++) {
      var opt = document.createElement("option");
      opt.value = String(speeds[i]);
      opt.textContent = speeds[i] + "×";
      if (speeds[i] === 1) opt.selected = true;
      speed.appendChild(opt);
    }
    bindPlayer(root);
    return root;
  }

  function audioEl() {
    return document.getElementById("listen-audio");
  }

  function setPlayingFace(on) {
    var toggle = document.getElementById("player-toggle");
    if (!toggle) return;
    toggle.setAttribute("aria-pressed", on ? "true" : "false");
    var paused = toggle.querySelector(".when-paused");
    var playing = toggle.querySelector(".when-playing");
    if (paused) paused.hidden = on;
    if (playing) playing.hidden = !on;
  }

  function remember(time) {
    if (!book) return;
    var section = currentSection();
    if (!section) return;
    var point = {
      mode: "listen",
      slug: book.slug,
      n: section.n,
      t: Math.max(0, time || 0),
      titleTa: book.title_ta || book.titleTa || "",
      titleEn: book.titleEn || book.title_ta || "",
      at: Date.now()
    };
    writeJson("neelam-listen:" + book.slug, { n: point.n, t: point.t });
    writeJson("neelam-continue", point);
  }

  function status(ta, en) {
    var el = document.getElementById("player-status");
    if (!el) return;
    el.innerHTML = '<span class="only-ta" lang="ta"></span><span class="only-en" lang="en"></span>';
    el.querySelector(".only-ta").textContent = ta || "";
    el.querySelector(".only-en").textContent = en || "";
  }

  function renderSectionList() {
    var list = document.getElementById("player-sections");
    if (!list || !book) return;
    list.innerHTML = "";
    (book.sections || []).forEach(function (section, index) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "player-section";
      if (index === sectionIndex) button.setAttribute("aria-current", "true");
      button.innerHTML = '<span class="player-section-title"></span><span class="player-section-dur"></span>';
      button.querySelector(".player-section-title").textContent = section.n + ". " + (section.title || "");
      button.querySelector(".player-section-dur").textContent = clock(section.duration_sec);
      button.addEventListener("click", function () {
        playSection(index, 0);
      });
      list.appendChild(button);
    });
  }

  function updateMediaSession() {
    if (!("mediaSession" in navigator) || !book) return;
    var section = currentSection();
    if (!section) return;
    var cover = "/books/" + book.slug + "/cover.jpg";
    try {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: section.title || book.title_ta || "",
        artist: book.artist || "நீலம் பி.ஜே.பிரதீப் ஜேசுதாஸ்",
        album: book.title_ta || "",
        artwork: [{ src: cover, type: "image/jpeg" }]
      });
    } catch (e) {}
    function handler(name, fn) {
      try { navigator.mediaSession.setActionHandler(name, fn); } catch (err) {}
    }
    handler("play", function () { audioEl().play(); });
    handler("pause", function () { audioEl().pause(); });
    handler("previoustrack", function () { playSection(Math.max(0, sectionIndex - 1), 0); });
    handler("nexttrack", function () { playSection(sectionIndex + 1, 0); });
    handler("seekbackward", function () { seekBy(-15); });
    handler("seekforward", function () { seekBy(15); });
  }

  function showPlayer() {
    var root = ensurePlayer();
    root.hidden = false;
    document.body.classList.add("has-player");
  }

  function paintHead() {
    var section = currentSection();
    var title = document.getElementById("player-title");
    var sub = document.getElementById("player-sub");
    if (title) title.textContent = section ? (section.n + ". " + (section.title || "")) : "";
    if (sub) sub.textContent = book ? (book.title_ta || "") : "";
    var listed = document.querySelectorAll(".player-section");
    for (var i = 0; i < listed.length; i++) {
      if (i === sectionIndex) listed[i].setAttribute("aria-current", "true");
      else listed[i].removeAttribute("aria-current");
    }
  }

  function playSection(index, at) {
    if (!book || !book.sections || !book.sections.length) return;
    if (index < 0) index = 0;
    if (index >= book.sections.length) {
      audioEl().pause();
      setPlayingFace(false);
      status("முடிந்தது", "Finished");
      return;
    }
    sectionIndex = index;
    var section = book.sections[index];
    var audio = audioEl();
    showPlayer();
    paintHead();
    status("", "");
    /* The address is assigned here and is not placed in a visible link. */
    audio.src = audioUrl(book.slug, section.n);
    audio.playbackRate = parseFloat(document.getElementById("player-speed").value) || 1;
    var startAt = at || 0;
    var begin = function () {
      if (startAt > 0 && startAt < (audio.duration || Infinity) - 0.4) audio.currentTime = startAt;
      var pending = audio.play();
      if (pending && pending.catch) pending.catch(function () { setPlayingFace(false); });
    };
    if (audio.readyState >= 1) begin();
    else audio.addEventListener("loadedmetadata", begin, { once: true });
    updateMediaSession();
    remember(startAt);
  }

  function seekBy(delta) {
    var audio = audioEl();
    if (!audio || !audio.src) return;
    var next = (audio.currentTime || 0) + delta;
    if (next < 0) {
      if (sectionIndex > 0) playSection(sectionIndex - 1, Math.max(0, (currentSection() && 0)));
      else audio.currentTime = 0;
      return;
    }
    if (audio.duration && next > audio.duration - 0.3) {
      playSection(sectionIndex + 1, 0);
      return;
    }
    audio.currentTime = next;
  }

  function clearSleep() {
    if (sleepTimer) clearTimeout(sleepTimer);
    sleepTimer = null;
    sleepEnds = 0;
  }

  function armSleep(minutes) {
    clearSleep();
    var select = document.getElementById("player-sleep");
    if (!minutes) {
      if (select) select.value = "0";
      return;
    }
    sleepEnds = Date.now() + minutes * 60000;
    sleepTimer = setTimeout(function () {
      var audio = audioEl();
      if (audio) audio.pause();
      status("தூக்க நேரம் முடிந்தது", "Sleep timer finished");
      clearSleep();
      if (select) select.value = "0";
    }, minutes * 60000);
  }

  function bindPlayer(root) {
    var audio = root.querySelector("#listen-audio");
    root.querySelector("#player-toggle").addEventListener("click", function () {
      if (!audio.src && book) playSection(sectionIndex, 0);
      else if (audio.paused) audio.play();
      else audio.pause();
    });
    root.querySelector("#player-back").addEventListener("click", function () { seekBy(-15); });
    root.querySelector("#player-forward").addEventListener("click", function () { seekBy(15); });
    root.querySelector("#player-speed").addEventListener("change", function () {
      audio.playbackRate = parseFloat(this.value) || 1;
    });
    root.querySelector("#player-sleep").addEventListener("change", function () {
      armSleep(parseInt(this.value, 10) || 0);
    });
    root.querySelector("#player-list").addEventListener("click", function () {
      var list = document.getElementById("player-sections");
      var open = list.hidden;
      list.hidden = !open;
      this.setAttribute("aria-expanded", open ? "true" : "false");
    });
    var seek = root.querySelector("#player-seek");
    var seeking = false;
    seek.addEventListener("pointerdown", function () { seeking = true; });
    seek.addEventListener("input", function () {
      seeking = true;
      if (audio.duration) audio.currentTime = (this.value / 1000) * audio.duration;
    });
    seek.addEventListener("change", function () { seeking = false; });
    audio.addEventListener("timeupdate", function () {
      var dur = audio.duration || currentSection() && currentSection().duration_sec || 0;
      if (!seeking && dur) seek.value = String(Math.round((audio.currentTime / dur) * 1000));
      var now = document.getElementById("player-now");
      var total = document.getElementById("player-dur");
      if (now) now.textContent = clock(audio.currentTime);
      if (total) total.textContent = clock(dur);
      saveTick += 1;
      if (saveTick % 4 === 0) remember(audio.currentTime);
      if ("mediaSession" in navigator && audio.duration) {
        try {
          navigator.mediaSession.setPositionState({
            duration: audio.duration,
            playbackRate: audio.playbackRate || 1,
            position: Math.min(audio.currentTime, audio.duration)
          });
        } catch (e) {}
      }
    });
    audio.addEventListener("play", function () {
      setPlayingFace(true);
      var others = document.querySelectorAll("video");
      for (var i = 0; i < others.length; i++) others[i].pause();
    });
    audio.addEventListener("pause", function () {
      setPlayingFace(false);
      remember(audio.currentTime);
    });
    audio.addEventListener("ended", function () {
      remember(0);
      playSection(sectionIndex + 1, 0);
    });
    audio.addEventListener("error", function () {
      setPlayingFace(false);
      status("இந்தப் பகுதி இன்னும் வரவில்லை", "This section is not ready yet");
    });
    /* Deterrence only: the file can still be requested from the network panel. */
    audio.addEventListener("contextmenu", function (event) { event.preventDefault(); });
    root.addEventListener("contextmenu", function (event) { event.preventDefault(); });
  }

  function listen(slug, n, at) {
    slug = safeSlug(slug);
    if (!slug) return Promise.resolve();
    return loadChapters(slug).then(function (data) {
      var panel = document.querySelector("[data-listen=\"" + slug + "\"] .listen-status");
      if (!data || !data.sections || !data.sections.length) {
        if (panel) {
          panel.innerHTML = '<span class="only-ta" lang="ta">ஆடியோ விரைவில்</span><span class="only-en" lang="en">Audio coming soon</span>';
        }
        var start = document.querySelector("[data-listen-start=\"" + slug + "\"]");
        if (start) start.hidden = true;
        return;
      }
      return catalogBook(slug).then(function (meta) {
        book = data;
        book.slug = data.slug || slug;
        book.titleEn = meta && (meta.titleEn || meta.title_en) || data.title_ta;
        book.titleTa = meta && meta.titleTa || data.title_ta;
        renderSectionList();
        var index = 0;
        for (var i = 0; i < book.sections.length; i++) {
          if (book.sections[i].n === n) index = i;
        }
        playSection(index, at || 0);
      });
    });
  }

  function wireBookPages() {
    var panels = document.querySelectorAll("[data-listen]");
    for (var p = 0; p < panels.length; p++) {
      (function (panel) {
        var slug = panel.getAttribute("data-listen");
        loadChapters(slug).then(function (data) {
          if (data && data.sections && data.sections.length) return;
          var statusEl = panel.querySelector(".listen-status");
          if (statusEl) {
            statusEl.innerHTML = '<span class="only-ta" lang="ta">ஆடியோ விரைவில்</span><span class="only-en" lang="en">Audio coming soon</span>';
          }
          var start = panel.querySelector("[data-listen-start]");
          if (start) start.hidden = true;
        });
      })(panels[p]);
    }
    var starts = document.querySelectorAll("[data-listen-start]");
    for (var i = 0; i < starts.length; i++) {
      starts[i].addEventListener("click", function () {
        var slug = this.getAttribute("data-listen-start");
        var saved = readJson("neelam-listen:" + slug) || {};
        listen(slug, saved.n || 1, saved.t || 0);
      });
    }
    var watches = document.querySelectorAll("[data-watch-slug]");
    for (var w = 0; w < watches.length; w++) wireWatch(watches[w]);
  }

  function wireWatch(stage) {
    var slug = safeSlug(stage.getAttribute("data-watch-slug"));
    var video = stage.querySelector("video");
    if (!slug || !video) return;
    var langNow = "ta";
    function setLang(next) {
      langNow = next === "en" ? "en" : "ta";
      var buttons = stage.querySelectorAll("[data-vlang]");
      for (var i = 0; i < buttons.length; i++) {
        buttons[i].setAttribute("aria-pressed", buttons[i].getAttribute("data-vlang") === langNow ? "true" : "false");
      }
      /* Assigned in script so the page HTML has no visible media address. */
      video.src = videoUrl(slug, langNow);
      video.load();
    }
    setLang("ta");
    video.addEventListener("contextmenu", function (event) { event.preventDefault(); });
    video.addEventListener("dragstart", function (event) { event.preventDefault(); });
    video.addEventListener("play", function () {
      var audio = audioEl();
      if (audio && !audio.paused) audio.pause();
    });
    var buttons = stage.querySelectorAll("[data-vlang]");
    for (var b = 0; b < buttons.length; b++) {
      buttons[b].addEventListener("click", function () {
        var wasPlaying = !video.paused;
        setLang(this.getAttribute("data-vlang"));
        if (wasPlaying) video.play();
      });
    }
  }

  function renderContinue() {
    var slot = document.getElementById("continue-slot");
    if (!slot) return;
    var point = readJson("neelam-continue");
    if (!point || !safeSlug(point.slug)) {
      slot.hidden = true;
      return;
    }
    var listening = point.mode === "listen";
    var href = listening
      ? "/books/" + point.slug + "/#listen"
      : "/read/?b=" + encodeURIComponent(point.slug) + "&s=" + (point.n || 1);
    slot.hidden = false;
    slot.innerHTML = ''
      + '<article class="continue-card">'
      + '  <p class="kicker"><span class="only-ta" lang="ta">தொடருங்கள்</span><span class="only-en" lang="en">Continue</span></p>'
      + '  <h2 class="continue-title"></h2>'
      + '  <p class="continue-detail"></p>'
      + '  <p class="actions"><a class="button" id="continue-go" href=""></a></p>'
      + '</article>';
    var title = lang() === "en" ? (point.titleEn || point.titleTa || point.slug) : (point.titleTa || point.titleEn || point.slug);
    slot.querySelector(".continue-title").textContent = title;
    slot.querySelector(".continue-detail").innerHTML = listening
      ? '<span class="only-ta" lang="ta">தொடர்ந்து கேட்க</span><span class="only-en" lang="en">Continue listening</span>'
      : '<span class="only-ta" lang="ta">தொடர்ந்து படிக்க</span><span class="only-en" lang="en">Continue reading</span>';
    var go = slot.querySelector("#continue-go");
    go.href = href;
    go.innerHTML = slot.querySelector(".continue-detail").innerHTML;
    if (listening) {
      go.addEventListener("click", function (event) {
        if (location.pathname.indexOf("/books/" + point.slug + "/") === 0 || location.pathname === "/read/" || location.pathname === "/") {
          event.preventDefault();
          listen(point.slug, point.n || 1, point.t || 0);
        }
      });
    }
  }

  function rememberRead(slug, n, y) {
    var metaTitle = document.getElementById("reader-title");
    writeJson("neelam-read:" + slug, { n: n, y: y || 0 });
    writeJson("neelam-continue", {
      mode: "read",
      slug: slug,
      n: n,
      t: 0,
      titleTa: metaTitle ? metaTitle.getAttribute("data-ta") || metaTitle.textContent : "",
      titleEn: metaTitle ? metaTitle.getAttribute("data-en") || "" : "",
      at: Date.now()
    });
  }

  function setReaderTheme(theme) {
    if (theme !== "light" && theme !== "sepia" && theme !== "dark") theme = "light";
    document.documentElement.setAttribute("data-reader", theme);
    var buttons = document.querySelectorAll("[data-reader-theme]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute("aria-pressed", buttons[i].getAttribute("data-reader-theme") === theme ? "true" : "false");
    }
    try { localStorage.setItem("neelam-reader-theme", theme); } catch (e) {}
  }

  function applyFont(size) {
    size = Math.min(1.7, Math.max(1.02, size));
    document.documentElement.style.setProperty("--read-size", size + "rem");
    writeJson("neelam-font", size);
    return size;
  }

  function bootReader() {
    if (document.body.getAttribute("data-page") !== "reader") return;
    var params = new URLSearchParams(location.search);
    var slug = safeSlug(params.get("b"));
    var currentReaderSection = 1;
    var sheet = document.getElementById("reader-sheet");
    var missing = document.getElementById("reader-missing");
    var storedTheme = "";
    try { storedTheme = localStorage.getItem("neelam-reader-theme") || ""; } catch (e) {}
    var theme = params.get("readerTheme") || storedTheme || document.documentElement.getAttribute("data-reader") || "light";
    setReaderTheme(theme);
    var savedFont = readJson("neelam-font");
    var fontSize = typeof savedFont === "number" ? savedFont : 1.2;
    applyFont(fontSize);
    document.getElementById("font-down").addEventListener("click", function () { fontSize = applyFont(fontSize - 0.08); });
    document.getElementById("font-up").addEventListener("click", function () { fontSize = applyFont(fontSize + 0.08); });
    var themeButtons = document.querySelectorAll("[data-reader-theme]");
    for (var t = 0; t < themeButtons.length; t++) {
      themeButtons[t].addEventListener("click", function () { setReaderTheme(this.getAttribute("data-reader-theme")); });
    }
    if (!slug) {
      missing.hidden = false;
      if (sheet) sheet.hidden = true;
      return;
    }
    var back = document.getElementById("reader-back");
    if (back) back.href = "/books/" + slug + "/";
    var watch = document.getElementById("reader-watch");
    if (watch) watch.href = "/books/" + slug + "/#watch";
    document.getElementById("reader-listen").addEventListener("click", function () {
      var n = currentReaderSection || 1;
      listen(slug, n, (readJson("neelam-listen:" + slug) || {}).t || 0);
    });
    var text = document.getElementById("reader-text");
    /* Deterrence only. */
    text.addEventListener("contextmenu", function (event) { event.preventDefault(); });
    text.addEventListener("dragstart", function (event) { event.preventDefault(); });
    var chapters = null;
    var meta = null;

    function sectionByNumber(n) {
      for (var i = 0; i < chapters.sections.length; i++) {
        if (chapters.sections[i].n === n) return { section: chapters.sections[i], index: i };
      }
      return { section: chapters.sections[0], index: 0 };
    }

    function paintProgress() {
      var bar = document.getElementById("read-progress");
      if (!bar || !chapters) return;
      var rect = text.getBoundingClientRect();
      var span = Math.max(1, text.offsetHeight - window.innerHeight * 0.4);
      var scrolled = Math.min(1, Math.max(0, -rect.top / span));
      var found = sectionByNumber(currentReaderSection);
      var overall = (found.index + scrolled) / chapters.sections.length;
      var pct = Math.round(overall * 100);
      bar.setAttribute("aria-valuenow", String(pct));
      bar.querySelector("span").style.width = pct + "%";
    }

    function showSection(n, restoreY) {
      var found = sectionByNumber(n);
      var section = found.section;
      currentReaderSection = section.n;
      document.getElementById("reader-kicker").textContent = section.n + " / " + chapters.sections.length;
      document.getElementById("reader-section-title").textContent = section.title || "";
      text.innerHTML = "";
      var figures = section.figures || [];
      function addFigure(fig) {
        if (!fig || typeof fig.src !== "string" || fig.src.charAt(0) !== "/") return;
        var figure = document.createElement("figure");
        figure.className = "reader-figure";
        var img = document.createElement("img");
        img.src = fig.src;
        img.loading = "lazy";
        img.decoding = "async";
        if (fig.width) img.width = fig.width;
        if (fig.height) img.height = fig.height;
        img.alt = fig.caption || "";
        figure.appendChild(img);
        if (fig.caption || fig.credit) {
          var cap = document.createElement("figcaption");
          cap.textContent = fig.caption || "";
          if (fig.credit) {
            var small = document.createElement("small");
            small.textContent = fig.credit;
            cap.appendChild(small);
          }
          figure.appendChild(cap);
        }
        text.appendChild(figure);
      }
      (section.paragraphs || []).forEach(function (paragraph, i) {
        var p = document.createElement("p");
        p.textContent = paragraph;
        text.appendChild(p);
        figures.forEach(function (fig) { if (fig.after === i) addFigure(fig); });
      });
      var prev = document.getElementById("reader-prev");
      var next = document.getElementById("reader-next");
      prev.disabled = found.index === 0;
      next.disabled = found.index === chapters.sections.length - 1;
      var url = "/read/?b=" + encodeURIComponent(slug) + "&s=" + section.n;
      history.replaceState({ n: section.n }, "", url);
      if (restoreY) window.scrollTo(0, restoreY);
      else window.scrollTo(0, 0);
      paintProgress();
      rememberRead(slug, section.n, window.scrollY);
      var links = document.querySelectorAll("#reader-toc a");
      for (var i = 0; i < links.length; i++) {
        if (parseInt(links[i].getAttribute("data-n"), 10) === section.n) links[i].setAttribute("aria-current", "true");
        else links[i].removeAttribute("aria-current");
      }
    }

    loadChapters(slug).then(function (data) {
      if (!data || !data.sections || !data.sections.length) {
        missing.hidden = false;
        sheet.hidden = true;
        return;
      }
      chapters = data;
      return catalogBook(slug).then(function (found) {
        meta = found || {};
        var titleTa = data.title_ta || meta.titleTa || slug;
        var titleEn = meta.titleEn || meta.title_en || titleTa;
        var titleEl = document.getElementById("reader-title");
        titleEl.textContent = titleTa;
        titleEl.setAttribute("data-ta", titleTa);
        titleEl.setAttribute("data-en", titleEn);
        titleEl.setAttribute("lang", "ta");
        document.getElementById("reader-title-en").textContent = titleEn;
        document.getElementById("reader-artist").textContent = data.artist || "";
        var head = document.querySelector("title");
        if (head) {
          head.setAttribute("data-title-both", titleTa + " · " + titleEn);
          head.setAttribute("data-title-ta", titleTa);
          head.setAttribute("data-title-en", titleEn);
          head.textContent = lang() === "en" ? titleEn : titleTa + " · " + titleEn;
        }
        var credit = document.getElementById("reader-credit");
        var own = "Copyright: © நீலம் பி.ஜே.பிரதீப் ஜேசுதாஸ் — இந்த தளத்தில் மட்டும் படிக்கவும் கேட்கவும்";
        if (meta.kind === "public_domain") {
          var author = meta.originalAuthor || meta.original_author || "";
          credit.innerHTML = '<span class="only-ta" lang="ta"></span><span class="only-en" lang="en"></span>';
          credit.querySelector(".only-ta").textContent = "மூலம் பொதுவுடைமையில் உள்ளது. மூல ஆசிரியர்: " + author + ". " + own;
          credit.querySelector(".only-en").textContent = "The original is in the public domain. Original author: " + author + ". Tamil translation by Neelam P.J. Pradeep Jesudas — read and listen on this site only.";
        } else {
          credit.innerHTML = '<span lang="ta"></span>';
          credit.querySelector("span").textContent = own;
        }
        var toc = document.getElementById("reader-toc");
        data.sections.forEach(function (section) {
          var a = document.createElement("a");
          a.href = "/read/?b=" + encodeURIComponent(slug) + "&s=" + section.n;
          a.setAttribute("data-n", String(section.n));
          a.textContent = section.n + ". " + (section.title || "") + " · " + clock(section.duration_sec);
          a.addEventListener("click", function (event) {
            event.preventDefault();
            showSection(section.n, 0);
            document.getElementById("reader-toc").hidden = true;
            document.getElementById("toc-toggle").setAttribute("aria-expanded", "false");
          });
          toc.appendChild(a);
        });
        var saved = readJson("neelam-read:" + slug) || {};
        var requested = parseInt(params.get("s") || "", 10);
        var n = requested || saved.n || data.sections[0].n;
        var restore = !requested || saved.n === requested ? (saved.y || 0) : 0;
        if (!requested) restore = saved.y || 0;
        if (requested && saved.n !== requested) restore = 0;
        showSection(n, restore);
        document.getElementById("reader-prev").addEventListener("click", function () {
          var found = sectionByNumber(currentReaderSection);
          if (found.index > 0) showSection(chapters.sections[found.index - 1].n, 0);
        });
        document.getElementById("reader-next").addEventListener("click", function () {
          var found = sectionByNumber(currentReaderSection);
          if (found.index < chapters.sections.length - 1) showSection(chapters.sections[found.index + 1].n, 0);
        });
        var tocToggle = document.getElementById("toc-toggle");
        tocToggle.addEventListener("click", function () {
          var open = document.getElementById("reader-toc").hidden;
          document.getElementById("reader-toc").hidden = !open;
          this.setAttribute("aria-expanded", open ? "true" : "false");
        });
        window.addEventListener("scroll", function () {
          paintProgress();
          rememberRead(slug, currentReaderSection, window.scrollY);
        }, { passive: true });
      });
    });
  }

  function bootDemo() {
    if (!isLocal()) return;
    var params = new URLSearchParams(location.search);
    if (params.get("showPlayer") !== "1") return;
    var slug = safeSlug(params.get("b"));
    if (!slug) {
      var stage = document.querySelector("[data-listen]");
      slug = stage ? safeSlug(stage.getAttribute("data-listen")) : "";
    }
    if (!slug) return;
    loadChapters(slug).then(function (data) {
      if (!data || !data.sections) return;
      return catalogBook(slug).then(function (meta) {
        book = data;
        book.slug = data.slug || slug;
        book.titleEn = meta && (meta.titleEn || meta.title_en) || data.title_ta;
        book.titleTa = meta && meta.titleTa || data.title_ta;
        renderSectionList();
        sectionIndex = 0;
        showPlayer();
        paintHead();
        var total = document.getElementById("player-dur");
        if (total && currentSection()) total.textContent = clock(currentSection().duration_sec);
        var list = document.getElementById("player-sections");
        if (list) list.hidden = false;
        var listBtn = document.getElementById("player-list");
        if (listBtn) listBtn.setAttribute("aria-expanded", "true");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    ensurePlayer();
    wireBookPages();
    renderContinue();
    bootReader();
    bootDemo();
    document.addEventListener("contextmenu", function (event) {
      if (event.target.closest && event.target.closest(".reader-text, video, audio, .watch-frame")) event.preventDefault();
    });
    document.addEventListener("dragstart", function (event) {
      if (event.target.closest && event.target.closest(".reader-text, video, audio, .watch-frame")) event.preventDefault();
    });
  });

  window.NeelamLibrary = { listen: listen, audioUrl: audioUrl };
})();
