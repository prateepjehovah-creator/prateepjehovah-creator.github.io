/* Language, theme, search, sharing, and the offline shell.
   No trackers. Tamil is the default language. */
(function () {
  var root = document.documentElement;

  function apply(lang) {
    if (lang !== "ta" && lang !== "en") lang = "ta";
    root.setAttribute("data-lang", lang);
    root.lang = lang;
    var buttons = document.querySelectorAll("[data-set-lang]");
    for (var i = 0; i < buttons.length; i++) {
      var on = buttons[i].getAttribute("data-set-lang") === lang;
      buttons[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
    var titleEl = document.querySelector("title");
    if (titleEl) {
      var titleKey = lang === "en" ? "data-title-en" : "data-title-both";
      var nextTitle = titleEl.getAttribute(titleKey);
      if (nextTitle) document.title = nextTitle;
    }
    var desc = document.querySelector('meta[name="description"]');
    if (desc) {
      var descKey = lang === "en" ? "data-desc-en" : "data-desc-both";
      var nextDesc = desc.getAttribute(descKey);
      if (nextDesc) desc.setAttribute("content", nextDesc);
    }
  }

  var switches = document.querySelectorAll("[data-set-lang]");
  for (var s = 0; s < switches.length; s++) {
    switches[s].addEventListener("click", function () {
      var lang = this.getAttribute("data-set-lang");
      apply(lang);
      try {
        localStorage.setItem("lang", lang);
      } catch (e) {}
    });
  }

  apply(root.getAttribute("data-lang") || "ta");

  function systemDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function applyTheme(theme) {
    if (theme === "light" || theme === "dark") {
      root.setAttribute("data-theme", theme);
    } else {
      theme = "system";
      root.removeAttribute("data-theme");
    }
    var btn = document.querySelector("[data-theme-toggle]");
    if (btn) {
      var dark = theme === "dark" || (theme === "system" && systemDark());
      btn.setAttribute("aria-pressed", dark ? "true" : "false");
    }
  }

  var themeBtn = document.querySelector("[data-theme-toggle]");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var order = ["system", "light", "dark"];
      var current = root.getAttribute("data-theme") || "system";
      var next = order[(order.indexOf(current) + 1) % order.length];
      applyTheme(next);
      try {
        if (next === "system") localStorage.removeItem("theme");
        else localStorage.setItem("theme", next);
      } catch (e) {}
    });
  }
  applyTheme(root.getAttribute("data-theme") || "system");

  var navLinks = document.querySelectorAll(".nav-link");
  for (var n = 0; n < navLinks.length; n++) {
    var href = navLinks[n].getAttribute("href");
    if (href && href !== "/" && location.pathname.indexOf(href) === 0) {
      navLinks[n].setAttribute("aria-current", "page");
    }
  }

  var user = ["prateep", "jehovah"].join("");
  var host = ["gmail", "com"].join(".");
  var addr = user + "@" + host;
  var emailLinks = document.querySelectorAll("[data-email-link]");
  for (var e = 0; e < emailLinks.length; e++) {
    emailLinks[e].setAttribute("href", "mailto:" + addr);
    emailLinks[e].textContent = addr;
  }

  var search = document.getElementById("book-search");
  if (search) {
    var empty = document.getElementById("search-empty");
    if (search.form) {
      search.form.addEventListener("submit", function (event) {
        event.preventDefault();
      });
    }
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      var shelves = document.querySelectorAll(".shelf");
      var shown = 0;
      for (var i = 0; i < shelves.length; i++) {
        var cards = shelves[i].querySelectorAll(".book-card");
        var shelfShown = 0;
        for (var c = 0; c < cards.length; c++) {
          var ok = !q || cards[c].textContent.toLowerCase().indexOf(q) !== -1;
          cards[c].hidden = !ok;
          if (ok) shelfShown += 1;
        }
        shelves[i].hidden = shelfShown === 0;
        shown += shelfShown;
      }
      if (empty) empty.hidden = shown !== 0;
    });
  }

  var copyButtons = document.querySelectorAll("[data-copy-link]");
  for (var b = 0; b < copyButtons.length; b++) {
    copyButtons[b].addEventListener("click", function () {
      var url = this.getAttribute("data-url") || location.href;
      var status = this.parentNode.parentNode.querySelector(".copy-status");
      var lang = root.getAttribute("data-lang") === "en" ? "en" : "ta";
      var done = function () {
        if (status) status.textContent = lang === "en" ? "Link copied" : "இணைப்பு நகலெடுக்கப்பட்டது";
      };
      var fallback = function () {
        var input = document.createElement("input");
        input.value = url;
        document.body.appendChild(input);
        input.select();
        try {
          document.execCommand("copy");
          done();
        } catch (err) {}
        document.body.removeChild(input);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(done).catch(fallback);
      } else {
        fallback();
      }
    });
  }

  var media = document.querySelectorAll("audio, video");
  for (var m = 0; m < media.length; m++) {
    media[m].addEventListener("play", function () {
      for (var j = 0; j < media.length; j++) {
        if (media[j] !== this && !media[j].paused) media[j].pause();
      }
    });
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js");
    });
  }

  var installBar = document.getElementById("install-bar");
  var installBtn = document.getElementById("install-app");
  var installIos = document.getElementById("install-ios");
  var standalone = (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) || window.navigator.standalone === true;

  function hideInstall() {
    if (installBar) installBar.hidden = true;
    if (installBtn) installBtn.hidden = true;
    if (installIos) installIos.hidden = true;
  }

  if (standalone) {
    hideInstall();
  } else if (installBar && installBtn) {
    var ios = /iphone|ipad|ipod/i.test(window.navigator.userAgent);
    if (ios && installIos) {
      installBar.hidden = false;
      installIos.hidden = false;
    }
    window.addEventListener("beforeinstallprompt", function (event) {
      event.preventDefault();
      installBar.hidden = false;
      installBtn.hidden = false;
      if (installIos) installIos.hidden = true;
      installBtn.onclick = function () {
        event.prompt();
        event.userChoice.then(function (choice) {
          if (choice && choice.outcome === "accepted") hideInstall();
          else installBtn.hidden = false;
        });
      };
    });
    window.addEventListener("appinstalled", hideInstall);
  }
})();
