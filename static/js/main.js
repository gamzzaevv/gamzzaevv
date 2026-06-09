"use strict";

// Cookie consent
function acceptCookies() {
  localStorage.setItem("cookies_accepted", "1");
  document.getElementById("cookie-notice").style.display = "none";
}

document.addEventListener("DOMContentLoaded", function () {
  const notice = document.getElementById("cookie-notice");
  if (notice && !localStorage.getItem("cookies_accepted")) {
    notice.style.display = "flex";
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener("click", function (e) {
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
});
