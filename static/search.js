(function () {
  "use strict";

  // --- State ---
  var searchIndex = window.SEARCH_INDEX || [];
  var activeIndex = -1;
  var debounceTimer = null;

  // --- DOM references ---
  var input = document.getElementById("search-input");
  var resultsContainer = document.getElementById("search-results");
  if (!input || !resultsContainer) return;

  // --- Search logic ---
  function search(query) {
    var q = query.toLowerCase().trim();
    if (q.length < 2 || !searchIndex.length) return [];

    var scored = [];
    for (var i = 0; i < searchIndex.length; i++) {
      var recipe = searchIndex[i];
      var score = 0;
      if (recipe.title.toLowerCase().indexOf(q) !== -1) score += 4;
      if (recipe.category.toLowerCase().indexOf(q) !== -1) score += 3;
      for (var t = 0; t < recipe.tags.length; t++) {
        if (recipe.tags[t].toLowerCase().indexOf(q) !== -1) { score += 2; break; }
      }
      if (recipe.description.toLowerCase().indexOf(q) !== -1) score += 1;
      if (score > 0) scored.push({ recipe: recipe, score: score });
    }

    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.recipe.title.localeCompare(b.recipe.title);
    });

    var results = [];
    var limit = Math.min(scored.length, 8);
    for (var j = 0; j < limit; j++) {
      results.push(scored[j].recipe);
    }
    return results;
  }

  // --- Rendering ---
  function renderResults(matches) {
    resultsContainer.innerHTML = "";

    if (matches.length === 0) {
      resultsContainer.innerHTML = '<div class="search-no-results">No recipes found</div>';
      showResults();
      return;
    }

    for (var i = 0; i < matches.length; i++) {
      var recipe = matches[i];
      var a = document.createElement("a");
      a.href = recipe.slug;
      a.className = "search-result";
      a.setAttribute("role", "option");
      a.dataset.index = i;

      var titleSpan = document.createElement("span");
      titleSpan.className = "search-result-title";
      titleSpan.textContent = recipe.title;

      var metaSpan = document.createElement("span");
      metaSpan.className = "search-result-meta";
      metaSpan.textContent = recipe.category;

      a.appendChild(titleSpan);
      a.appendChild(metaSpan);
      resultsContainer.appendChild(a);
    }

    activeIndex = -1;
    showResults();
  }

  function showResults() {
    resultsContainer.hidden = false;
  }

  function hideResults() {
    resultsContainer.hidden = true;
    activeIndex = -1;
  }

  function updateActive() {
    var results = resultsContainer.querySelectorAll(".search-result");
    for (var i = 0; i < results.length; i++) {
      if (i === activeIndex) {
        results[i].classList.add("active");
      } else {
        results[i].classList.remove("active");
      }
    }
  }

  // --- Event handlers ---
  input.addEventListener("input", function () {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      var query = input.value;
      if (query.trim().length < 2) {
        hideResults();
        return;
      }
      var matches = search(query);
      renderResults(matches);
    }, 200);
  });

  input.addEventListener("keydown", function (e) {
    var results = resultsContainer.querySelectorAll(".search-result");
    if (!results.length) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % results.length;
      updateActive();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + results.length) % results.length;
      updateActive();
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex >= 0 && results[activeIndex]) {
        window.location.href = results[activeIndex].href;
      }
    } else if (e.key === "Escape") {
      hideResults();
      input.blur();
    }
  });

  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search-wrapper")) {
      hideResults();
    }
  });
})();
