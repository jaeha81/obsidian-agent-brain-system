(function () {
  function getCookie(name) {
    var parts = document.cookie.split(";");
    for (var i = 0; i < parts.length; i += 1) {
      var part = parts[i].trim();
      if (part.indexOf(name + "=") === 0) return part.slice(name.length + 1);
    }
    return "";
  }

  function isLoginHref(href) {
    return /(^|\/)login\.html(\?|$)/.test(href) || /(^|\/)login(\?|$)/.test(href);
  }

  function isLogoutHref(href) {
    return href.indexOf("/api/logout") === 0 || href.indexOf("api/logout") >= 0;
  }

  function syncAuthLinks() {
    var loggedIn = Boolean(getCookie("bucky_auth"));
    document.querySelectorAll("a[href]").forEach(function (link) {
      var href = link.getAttribute("href") || "";
      if (isLoginHref(href)) {
        link.hidden = loggedIn;
        link.setAttribute("aria-hidden", loggedIn ? "true" : "false");
      }
      if (isLogoutHref(href)) {
        link.hidden = !loggedIn;
        link.setAttribute("aria-hidden", loggedIn ? "false" : "true");
      }
    });
    document.documentElement.dataset.authenticated = loggedIn ? "true" : "false";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", syncAuthLinks);
  } else {
    syncAuthLinks();
  }
})();
