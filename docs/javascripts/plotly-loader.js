(function () {
  function loadPlotlyFigure(card) {
    const target = card.querySelector(".plotly-lazy-target");
    const button = card.querySelector(".plotly-load-button");
    if (!target || target.querySelector("iframe")) {
      return;
    }

    const iframe = document.createElement("iframe");
    iframe.className = "plotly-embed";
    iframe.src = card.dataset.plotlySrc;
    iframe.title = card.dataset.plotlyTitle || "Interactive Plotly figure";
    iframe.loading = "lazy";

    target.appendChild(iframe);
    card.classList.add("is-loaded");
    if (button) {
      button.disabled = true;
      button.textContent = "Interactive Figure Loaded";
    }
  }

  document.addEventListener("click", function (event) {
    const button = event.target.closest(".plotly-load-button");
    if (!button) {
      return;
    }
    const card = button.closest(".plotly-lazy-card");
    if (card) {
      loadPlotlyFigure(card);
    }
  });
}());
