/* ═══════════════════════════════════════════════
   BRIAS — glow.js
   WebGL ambient glow background for auth screen
   ═══════════════════════════════════════════════ */

const VERTEX_SHADER = `
  attribute vec2 p;
  void main() {
    gl_Position = vec4(p, 0.0, 1.0);
  }
`;

const FRAGMENT_SHADER = `
  precision mediump float;
  uniform float t;
  uniform vec2 res;

  void main() {
    vec2 uv = gl_FragCoord.xy / res;
    float x = uv.x, y = uv.y;

    float w1 = sin(x * 3.1 + t * 0.5 + sin(y * 2.4 + t * 0.35) * 1.2) * 0.5 + 0.5;
    float w2 = sin(y * 2.8 - t * 0.6 + sin(x * 3.6 - t * 0.4) * 1.1) * 0.5 + 0.5;
    float w3 = sin((x + y) * 2.5 + t * 0.55 + sin(x * 1.8 + t * 0.3) * 0.9) * 0.5 + 0.5;
    float w4 = sin((x - y) * 3.2 - t * 0.45 + sin(y * 2.1 - t * 0.5) * 1.0) * 0.5 + 0.5;

    float blend = (w1 * w2 + w2 * w3 + w3 * w4) / 3.0;

    vec3 orange = vec3(0.91, 0.388, 0.29);
    vec3 pink   = vec3(0.831, 0.353, 0.447);
    vec3 dark   = vec3(0.102, 0.067, 0.075);

    float ar = res.x / res.y;
    float ys = mix(ar < 1.0 ? 0.25 : 0.3, ar < 1.0 ? 0.03 : 0.1, y * y);
    float intensity = ys * mix(0.5, 1.0, pow(blend, 1.4));

    gl_FragColor = vec4(mix(dark, mix(orange, pink, w2), intensity), 1.0);
  }
`;

class GlowBackground {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.started = false;
    this.animId = null;
  }

  start() {
    if (this.started) return;

    if (!this.canvas || this.canvas.offsetWidth === 0) {
      requestAnimationFrame(() => this.start());
      return;
    }

    this.started = true;
    const gl = this.canvas.getContext('webgl') || this.canvas.getContext('experimental-webgl');
    if (!gl) return;

    // Compile shaders
    const vs = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vs, VERTEX_SHADER);
    gl.compileShader(vs);

    const fs = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fs, FRAGMENT_SHADER);
    gl.compileShader(fs);

    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);

    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
    gl.useProgram(prog);

    // Fullscreen quad
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);

    const pLoc = gl.getAttribLocation(prog, 'p');
    gl.enableVertexAttribArray(pLoc);
    gl.vertexAttribPointer(pLoc, 2, gl.FLOAT, false, 0, 0);

    const tLoc = gl.getUniformLocation(prog, 't');
    const resLoc = gl.getUniformLocation(prog, 'res');
    const startTime = performance.now();

    const resize = () => {
      this.canvas.width = this.canvas.offsetWidth;
      this.canvas.height = this.canvas.offsetHeight;
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    };

    resize();
    window.addEventListener('resize', resize);

    const tick = () => {
      gl.uniform1f(tLoc, (performance.now() - startTime) / 1000);
      gl.uniform2f(resLoc, this.canvas.width || 1, this.canvas.height || 1);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      this.animId = requestAnimationFrame(tick);
    };

    tick();
  }

  stop() {
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }
  }
}

export { GlowBackground };
