/* BRIAS — Landingspagina */

// Netwerkactiviteit ophalen
async function loadState() {
  try {
    const s = await API.statePublic();
    document.getElementById('stat-activity').textContent =
      (s.activity * 100).toFixed(1) + '%';
    document.getElementById('stat-coherence').textContent =
      s.coherence.toFixed(3);
    document.getElementById('stat-uptime').textContent =
      s.uptime_human;
  } catch {
    document.getElementById('live-text').textContent = 'Verbinding...';
  }
}

loadState();
setInterval(loadState, 4000);

// Canvas achtergrond — gesimuleerde netwerkactiviteit
const canvas = document.getElementById('network-canvas');
const ctx = canvas.getContext('2d');

let nodes = [];
let W, H;

function resize() {
  W = canvas.width  = window.innerWidth;
  H = canvas.height = window.innerHeight;
}
resize();
window.addEventListener('resize', resize);

// Maak nodes aan
for (let i = 0; i < 80; i++) {
  nodes.push({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    vx: (Math.random() - 0.5) * 0.3,
    vy: (Math.random() - 0.5) * 0.3,
    r: Math.random() * 2 + 1,
    phase: Math.random() * Math.PI * 2,
    speed: Math.random() * 0.01 + 0.005,
  });
}

function draw(t) {
  ctx.clearRect(0, 0, W, H);

  // Verbindingen
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x;
      const dy = nodes[i].y - nodes[j].y;
      const d  = Math.sqrt(dx * dx + dy * dy);
      if (d < 120) {
        const alpha = (1 - d / 120) * 0.25;
        ctx.strokeStyle = `rgba(139,143,255,${alpha})`;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(nodes[i].x, nodes[i].y);
        ctx.lineTo(nodes[j].x, nodes[j].y);
        ctx.stroke();
      }
    }
  }

  // Nodes
  nodes.forEach(n => {
    const glow = 0.5 + 0.5 * Math.sin(t * n.speed + n.phase);
    ctx.fillStyle = `rgba(139,143,255,${0.3 + glow * 0.5})`;
    ctx.beginPath();
    ctx.arc(n.x, n.y, n.r + glow, 0, Math.PI * 2);
    ctx.fill();

    // Beweging
    n.x += n.vx;
    n.y += n.vy;
    if (n.x < 0 || n.x > W) n.vx *= -1;
    if (n.y < 0 || n.y > H) n.vy *= -1;
  });

  requestAnimationFrame(draw);
}
requestAnimationFrame(draw);

// Ingelogd? Stuur door naar /app
if (API.isLoggedIn()) {
  window.location.href = '/app';
}
