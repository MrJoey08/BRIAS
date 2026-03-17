/* ═══════════════════════════════════════════════
   BRIAS — helpers.js
   DOM utilities: escape, scroll, auto-resize
   ═══════════════════════════════════════════════ */

/**
 * HTML-escape a string to prevent XSS
 */
function esc(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Scroll the message container to the bottom
 */
function scrollBottom() {
  const container = document.getElementById('msgContainer');
  if (container) {
    setTimeout(() => container.scrollTop = container.scrollHeight, 30);
  }
}

/**
 * Auto-resize a textarea to fit content
 */
function autoResize(el) {
  el.style.height = '24px';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

/**
 * Shuffle an array in-place (Fisher-Yates)
 */
function shuffleArray(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export { esc, scrollBottom, autoResize, shuffleArray };
