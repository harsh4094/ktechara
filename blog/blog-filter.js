/* blog-filter.js — Static client-side filter for K Techara blog
 * Replaces the non-functional WordPress Search & Filter Pro plugin.
 * Works on blog/index.html and blog/page/N/index.html.
 */
(function () {
  "use strict";

  /* ── Label maps ─────────────────────────────────────────────────────────── */
  var INSIGHT_LABELS = {
    blog: "Blog",
  };

  var BUSINESS_LABELS = {
    agility: "Agility",
    compliance: "Compliance",
    efficiency: "Efficiency",
    "employee-experience": "Employee experience",
    "future-readiness": "Future readiness",
    infrastructure: "Infrastructure",
    security: "Security",
    sustainability: "Sustainability",
  };

  var SERVICE_LABELS = {
    "ai-automation": "AI & automation",
    "azure-cloud": "Azure & cloud",
    "business-applications": "Business applications",
    data: "Data",
    "managed-it-services": "Managed IT services",
    "modern-work": "Modern work",
    strategy: "Strategy",
    "unified-communications": "Unified communications",
  };

  function toLabel(map, slug) {
    return (
      map[slug] ||
      slug.replace(/-/g, " ").replace(/\b\w/g, function (c) {
        return c.toUpperCase();
      })
    );
  }

  /* ── Path detection ──────────────────────────────────────────────────────── */
  var onPageN = /\/blog\/page\//.test(window.location.pathname);
  var JSON_URL = onPageN ? "../../blog-posts.json" : "blog-posts.json";

  /* ── State ───────────────────────────────────────────────────────────────── */
  var allPosts = [];
  var mainLoop = null;
  var loadMoreWrapper = null;
  var resultsEl = null;
  var countEl = null;
  var shownCount = 0;
  var LOAD_MORE_BATCH = 12;

  /* ── CSS injection ───────────────────────────────────────────────────────── */
  function injectStyles() {
    var s = document.createElement("style");
    s.textContent = [
      /* Reset plugin containers */
      ".search-filter-field--id-4,.search-filter-field--id-5,.search-filter-field--id-6,.search-filter-field--id-7{display:block!important;min-height:0!important;}",

      /* Label above each dropdown — matches Advania "Insight type:" style */
      ".ktm-label{display:block;font-size:13px;color:#555;font-weight:400;margin-bottom:8px;line-height:1.4;}",

      /* Dropdown — data URI on single line to avoid CSS parse break */
      '.ktm-select{display:block;width:100%;height:52px;box-sizing:border-box;padding:0 48px 0 16px;border:1px solid #d0d0d0;border-radius:4px;background:#fff url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2712%27 height=%278%27 viewBox=%270 0 12 8%27%3E%3Cpath d=%27M1 1l5 5 5-5%27 stroke=%27%23888%27 stroke-width=%271.8%27 fill=%27none%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27/%3E%3C/svg%3E") no-repeat right 16px center;-webkit-appearance:none;appearance:none;font-size:15px;color:#333;cursor:pointer;transition:border-color .15s;}',
      ".ktm-select:focus{outline:none;border-color:#9B59B6;box-shadow:0 0 0 3px rgba(155,89,182,.12);}",
      ".ktm-select option{color:#333;}",

      /* Search bar — underline style matching Advania */
      ".ktm-search-wrap{position:relative;display:flex;align-items:center;border-bottom:1.5px solid #d0d0d0;padding:6px 0;margin-top:4px;}",
      ".ktm-search-wrap svg{position:absolute;left:2px;width:18px;height:18px;color:#888;flex-shrink:0;pointer-events:none;}",
      ".ktm-search-input{width:100%;padding:10px 10px 10px 30px;border:none;background:transparent;font-size:15px;color:#333;box-sizing:border-box;}",
      ".ktm-search-input:focus{outline:none;}",
      ".ktm-search-input::placeholder{color:#aaa;}",

      /* Result count */
      ".ktm-count{padding:8px 0 16px;font-size:14px;color:#666;display:none;}",

      /* No-results */
      ".ktm-no-results{grid-column:1/-1;padding:40px 24px;text-align:center;color:#666;font-size:15px;}",
    ].join("\n");
    document.head.appendChild(s);
  }

  /* ── Suppress plugin combobox elements via MutationObserver ──────────────── */
  function suppressPluginUI() {
    var fieldClasses = [
      "search-filter-field--id-4",
      "search-filter-field--id-5",
      "search-filter-field--id-6",
      "search-filter-field--id-7",
    ];

    function hidePluginNode(node) {
      if (node.nodeType !== 1) return;
      var cls = node.className || "";
      if (
        cls.indexOf("search-filter-component") !== -1 ||
        cls.indexOf("search-filter-label") !== -1
      ) {
        node.style.setProperty("display", "none", "important");
      }
    }

    var observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        m.addedNodes.forEach(hidePluginNode);
      });
    });

    fieldClasses.forEach(function (cls) {
      var el = document.querySelector("." + cls);
      if (!el) return;
      /* Hide any plugin elements already present */
      Array.from(el.children).forEach(hidePluginNode);
      /* Watch for future additions */
      observer.observe(el, { childList: true });
    });
  }

  /* ── Inject real UI into the plugin placeholder divs ─────────────────────── */
  function injectFilterUI() {
    var searchIcon = [
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"',
      ' aria-hidden="true">',
      '<circle cx="11" cy="11" r="8"/>',
      '<line x1="21" y1="21" x2="16.65" y2="16.65"/>',
      "</svg>",
    ].join("");

    var fieldMap = {
      "search-filter-field--id-5":
        '<label class="ktm-label">Insight type:</label><select id="ktm-insight"  class="ktm-select"><option value="">All insight types</option></select>',
      "search-filter-field--id-6":
        '<label class="ktm-label">Business needs:</label><select id="ktm-business" class="ktm-select"><option value="">All Business Needs</option></select>',
      "search-filter-field--id-7":
        '<label class="ktm-label">Solutions:</label><select id="ktm-service"  class="ktm-select"><option value="">All solutions</option></select>',
      "search-filter-field--id-4":
        '<div class="ktm-search-wrap">' +
        searchIcon +
        '<input type="text" id="ktm-search" class="ktm-search-input" placeholder="Search" autocomplete="off"></div>',
    };

    Object.keys(fieldMap).forEach(function (cls) {
      var el = document.querySelector("." + cls);
      if (el) el.innerHTML = fieldMap[cls];
    });
  }

  /* ── Populate dropdown <option>s from post data ──────────────────────────── */
  function populateDropdowns(posts) {
    function countValues(key) {
      var counts = {};
      posts.forEach(function (p) {
        (p[key] || []).forEach(function (v) {
          counts[v] = (counts[v] || 0) + 1;
        });
      });
      return counts;
    }

    function fill(id, counts, labelMap) {
      var sel = document.getElementById(id);
      if (!sel) return;
      var sorted = Object.keys(counts).sort(function (a, b) {
        return (labelMap[a] || a).localeCompare(labelMap[b] || b);
      });
      sorted.forEach(function (val) {
        var opt = document.createElement("option");
        opt.value = val;
        opt.textContent = toLabel(labelMap, val) + " (" + counts[val] + ")";
        sel.appendChild(opt);
      });
    }

    fill("ktm-insight", countValues("insightTypes"), INSIGHT_LABELS);
    fill("ktm-business", countValues("businessNeeds"), BUSINESS_LABELS);
    fill("ktm-service", countValues("services"), SERVICE_LABELS);
  }

  /* ── Event listeners ─────────────────────────────────────────────────────── */
  function attachEvents() {
    ["ktm-insight", "ktm-business", "ktm-service"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("change", applyFilter);
    });

    var searchEl = document.getElementById("ktm-search");
    var timer;
    if (searchEl) {
      searchEl.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(applyFilter, 280);
      });
    }
  }

  /* ── Core filter logic ───────────────────────────────────────────────────── */
  function applyFilter() {
    var insight = val("ktm-insight");
    var business = val("ktm-business");
    var service = val("ktm-service");
    var term = (val("ktm-search") || "").toLowerCase().trim();
    var active = insight || business || service || term;

    if (!active) {
      resetView();
      return;
    }

    var filtered = allPosts.filter(function (p) {
      if (insight && (p.insightTypes || []).indexOf(insight) === -1)
        return false;
      if (business && (p.businessNeeds || []).indexOf(business) === -1)
        return false;
      if (service && (p.services || []).indexOf(service) === -1) return false;
      if (term && p.title.toLowerCase().indexOf(term) === -1) return false;
      return true;
    });

    showResults(filtered);
  }

  function val(id) {
    var el = document.getElementById(id);
    return el ? el.value.trim() : "";
  }

  /* ── Show filtered results ───────────────────────────────────────────────── */
  function showResults(posts) {
    if (mainLoop) mainLoop.style.display = "none";
    if (loadMoreWrapper) loadMoreWrapper.style.display = "none";

    countEl.textContent =
      posts.length + (posts.length === 1 ? " result found" : " results found");
    countEl.style.display = "block";

    resultsEl.innerHTML = posts.length
      ? posts.map(buildCard).join("")
      : '<p class="ktm-no-results">No results found. Try adjusting your filters.</p>';
    resultsEl.style.display = "";
  }

  /* ── Reset to original page cards ───────────────────────────────────────── */
  function resetView() {
    if (mainLoop) mainLoop.style.display = "";
    if (loadMoreWrapper) loadMoreWrapper.style.display = "";
    countEl.style.display = "none";
    resultsEl.style.display = "none";
    resultsEl.innerHTML = "";
  }

  /* ── Card HTML builder ───────────────────────────────────────────────────── */
  function buildCard(post) {
    var insightSlug = (post.insightTypes || ["blog"])[0];
    var insightLabel = toLabel(INSIGHT_LABELS, insightSlug);

    var taxClasses = [
      (post.insightTypes || [])
        .map(function (t) {
          return "insights-type-" + t;
        })
        .join(" "),
      (post.businessNeeds || [])
        .map(function (b) {
          return "business-need-" + b;
        })
        .join(" "),
      (post.services || [])
        .map(function (s) {
          return "service-" + s;
        })
        .join(" "),
    ]
      .filter(Boolean)
      .join(" ");

    var imgHtml = post.image
      ? '<div class="elementor-element elementor-element-6734958 e-flex e-con-boxed e-con e-child">' +
        '<div class="e-con-inner">' +
        '<div class="elementor-element elementor-element-dba0396 elementor-widget elementor-widget-image">' +
        '<a href="' +
        post.url +
        '">' +
        '<img loading="lazy" src="' +
        post.image +
        '" class="elementor-animation-grow attachment-large size-large" alt="">' +
        "</a></div></div></div>"
      : "";

    return (
      '<div class="elementor elementor-31500 e-loop-item insights type-insights ' +
      taxClasses +
      '">' +
      '<div class="elementor-element elementor-element-7c8d0cd e-con-full e-flex e-con e-parent">' +
      '<div class="elementor-element elementor-element-0807fac e-con-full e-flex e-con e-child">' +
      '<div class="elementor-element elementor-element-54386c4 e-con-full e-flex e-con e-child">' +
      '<div class="elementor-element elementor-element-a97b6de type-title elementor-widget elementor-widget-post-info">' +
      '<ul class="elementor-inline-items elementor-icon-list-items elementor-post-info">' +
      '<li class="elementor-icon-list-item elementor-repeater-item-7166291 elementor-inline-item" itemprop="about">' +
      '<span class="elementor-icon-list-text elementor-post-info__item elementor-post-info__item--type-terms">' +
      '<span class="elementor-post-info__terms-list">' +
      '<a href="/blog/" class="elementor-post-info__terms-list-item">' +
      insightLabel +
      "</a>" +
      "</span></span></li></ul></div>" +
      '<div class="elementor-element elementor-element-0a452fe rltcase elementor-widget elementor-widget-heading">' +
      '<h4 class="elementor-heading-title elementor-size-default">' +
      '<a href="' +
      post.url +
      '">' +
      post.title +
      "</a>" +
      "</h4></div></div>" +
      imgHtml +
      "</div></div></div>"
    );
  }

  /* ── Load more ───────────────────────────────────────────────────────────── */
  function initLoadMore() {
    /* allPosts is the full, globally-ordered post list starting at index 0,
     * which only lines up with what's already on screen on the main listing
     * page. The /blog/page/N/ fallback pages each render their own slice out
     * of sequence, so appending via allPosts there would replay/skip posts. */
    if (onPageN) return;
    if (!mainLoop || !loadMoreWrapper) return;

    var button = loadMoreWrapper.querySelector("a.elementor-button");
    var widget = mainLoop.closest(".elementor-widget-loop-grid");
    if (!button || !widget) return;

    shownCount = mainLoop.querySelectorAll(":scope > .e-loop-item").length;

    function updateEndState() {
      if (shownCount >= allPosts.length) {
        widget.classList.add("e-load-more-pagination-end");
      }
    }

    updateEndState();

    /* Capture phase + stopPropagation so this runs before, and blocks,
     * Elementor Pro's own document-level delegated click handler for
     * .e-loop__load-more (load-more.bundle.min.js), which still tries an
     * admin-ajax.php request that 404s on this static export. */
    button.addEventListener(
      "click",
      function (event) {
        event.preventDefault();
        event.stopPropagation();
        var next = allPosts.slice(shownCount, shownCount + LOAD_MORE_BATCH);
        if (!next.length) return;
        mainLoop.insertAdjacentHTML("beforeend", next.map(buildCard).join(""));
        shownCount += next.length;
        updateEndState();
      },
      true,
    );
  }

  /* ── Bootstrap ───────────────────────────────────────────────────────────── */
  function init() {
    injectStyles();
    injectFilterUI();
    suppressPluginUI();

    /* Find the main loop container and the load-more section */
    mainLoop = document.querySelector(
      ".elementor-widget-loop-grid .elementor-loop-container",
    );
    loadMoreWrapper = document.querySelector(".e-loop__load-more");

    /* Insert count label before the main loop */
    countEl = document.createElement("div");
    countEl.className = "ktm-count";
    if (mainLoop) mainLoop.parentNode.insertBefore(countEl, mainLoop);

    /* Insert results container after the main loop */
    resultsEl = document.createElement("div");
    resultsEl.id = "ktm-filter-results";
    resultsEl.className = "elementor-loop-container elementor-grid";
    resultsEl.setAttribute("role", "list");
    resultsEl.style.display = "none";
    if (mainLoop)
      mainLoop.parentNode.insertBefore(resultsEl, mainLoop.nextSibling);

    /* Fetch post data then wire up everything.
     * Re-call injectFilterUI() here so we overwrite any plugin combobox UI
     * that the Search Filter Pro plugin may have appended asynchronously. */
    fetch(JSON_URL)
      .then(function (r) {
        return r.json();
      })
      .then(function (posts) {
        allPosts = posts;
        injectFilterUI();
        suppressPluginUI();
        populateDropdowns(posts);
        attachEvents();
        initLoadMore();
      })
      .catch(function (err) {
        console.warn("[blog-filter] Could not load posts JSON:", err);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
