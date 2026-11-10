document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const node = document.getElementById(button.getAttribute("data-copy"));
    if (!node) return;
    const text = "value" in node ? node.value : node.innerText;
    try {
      await navigator.clipboard.writeText(text);
      const previous = button.textContent;
      button.textContent = "Copied";
      setTimeout(() => {
        button.textContent = previous;
      }, 1400);
    } catch (_err) {
      button.textContent = "Copy failed";
    }
  });
});
