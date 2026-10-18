/* Language toggle and one-at-a-time playback. No build step. */
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

  var media = document.querySelectorAll("audio, video");
  for (var m = 0; m < media.length; m++) {
    media[m].addEventListener("play", function () {
      for (var j = 0; j < media.length; j++) {
        if (media[j] !== this && !media[j].paused) media[j].pause();
      }
    });
  }
})();
