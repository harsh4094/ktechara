/* related-blogs.js — Fix broken images in the "Related blogs" section
 * Each individual blog page (at blog/[category]/[post-slug]/index.html)
 * includes this script as  ../../related-blogs.js
 *
 * Root cause: some related-blog card <img> elements reference old/renamed
 * image files that no longer exist on disk.  The blog-posts.json file holds
 * the correct, up-to-date image path for every post.
 *
 * Strategy:
 *   1. Fetch blog-posts.json (two levels up from this script's location,
 *      i.e. at /blog/blog-posts.json).
 *   2. Build a map of  post-url → image-path  from the JSON.
 *   3. Walk every <img> inside the "Related blogs" loop grid.
 *   4. For each <img>, find the closest ancestor <a> whose href points to a
 *      blog post.  Look that URL up in the map.
 *   5. If the JSON has a different (and presumably correct) image for that
 *      post, replace the element's src (and clear srcset so the browser
 *      always uses the corrected src).
 */
(function () {
  "use strict";

  /* ── Helpers ──────────────────────────────────────────────────────────────── */

  /**
   * Normalise a URL to a canonical path string so we can compare URLs that
   * may differ in protocol, host, or relative-vs-absolute form.
   */
  function normalisePath(href, base) {
    try {
      return new URL(href, base || window.location.href).pathname;
    } catch (e) {
      return href;
    }
  }

  /**
   * Convert a JSON image path (absolute, e.g. "/wp-content/uploads/…") to a
   * path that can be used as a relative src from the current page.
   */
  function absoluteToRelative(absPath) {
    return "../../.." + absPath;
  }

  /**
   * Given an <img> element, walk up the DOM to find the closest <a> that
   * links to a blog post.  Returns the href string or null.
   */
  function findLinkHref(img) {
    var el = img.parentElement;
    while (el && el !== document.body) {
      if (el.tagName === "A" && el.href) {
        return el.getAttribute("href");
      }
      el = el.parentElement;
    }
    return null;
  }

  /* ── Main ─────────────────────────────────────────────────────────────────── */

  function init() {
    var relatedSection = null;

    /* The section heading says "Related blogs"; grab the nearest grid. */
    var headings = document.querySelectorAll(
      ".elementor-heading-title, h2, h3, h4"
    );
    for (var i = 0; i < headings.length; i++) {
      if (/related blogs/i.test(headings[i].textContent)) {
        var parent = headings[i].closest(
          ".elementor-widget-container, .elementor-element, .e-con-inner, .e-con"
        );
        while (parent) {
          var grid = parent.querySelector(".elementor-loop-container");
          if (grid) {
            relatedSection = grid;
            break;
          }
          parent = parent.parentElement;
        }
        break;
      }
    }

    if (!relatedSection) {
      var allGrids = document.querySelectorAll(".elementor-loop-container");
      if (allGrids.length > 0) {
        relatedSection = allGrids[allGrids.length - 1];
      }
    }

    if (!relatedSection) {
      return;
    }

    var jsonUrl = "../../blog-posts.json";

    fetch(jsonUrl)
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.json();
      })
      .then(function (posts) {
        var imageMap = {};
        posts.forEach(function (post) {
          if (post.url && post.image) {
            var normUrl = normalisePath(post.url, window.location.origin);
            imageMap[normUrl] = post.image;
          }
        });

        var imgs = relatedSection.querySelectorAll("img");
        imgs.forEach(function (img) {
          var href = findLinkHref(img);
          if (!href) return;

          var normHref = normalisePath(href);
          var correctAbsImage = imageMap[normHref];
          if (!correctAbsImage) return;

          var correctRelImage = absoluteToRelative(correctAbsImage);
          var currentAbsSrc = img.src;
          var correctAbsSrc;
          try {
            correctAbsSrc = new URL(
              correctRelImage,
              window.location.href
            ).href;
          } catch (e) {
            return;
          }

          if (currentAbsSrc !== correctAbsSrc) {
            img.src = correctRelImage;
            img.removeAttribute("srcset");
            img.removeAttribute("sizes");
          }
        });
      })
      .catch(function (err) {
        console.warn("[related-blogs] Could not load blog-posts.json:", err);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
