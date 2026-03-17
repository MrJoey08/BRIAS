// ===== BRIAS · WebGL Glow Background =====
// Shared between login.html and offline.html

var glowStarted = false;

function startAuthGlow() {
  if (glowStarted) return;
  var canvas = document.getElementById('authGlow');
  if (!canvas || canvas.offsetWidth === 0) { requestAnimationFrame(startAuthGlow); return; }
  glowStarted = true;

  var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  if (!gl) return;

  var vs = gl.createShader(gl.VERTEX_SHADER);
  gl.shaderSource(vs, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.0,1.0);}');
  gl.compileShader(vs);

  var fs = gl.createShader(gl.FRAGMENT_SHADER);
  gl.shaderSource(fs, 'precision mediump float;uniform float t;uniform vec2 res;void main(){vec2 uv=gl_FragCoord.xy/res;float x=uv.x,y=uv.y;float w1=sin(x*3.1+t*.5+sin(y*2.4+t*.35)*1.2)*.5+.5;float w2=sin(y*2.8-t*.6+sin(x*3.6-t*.4)*1.1)*.5+.5;float w3=sin((x+y)*2.5+t*.55+sin(x*1.8+t*.3)*.9)*.5+.5;float w4=sin((x-y)*3.2-t*.45+sin(y*2.1-t*.5)*1.)*.5+.5;float b=(w1*w2+w2*w3+w3*w4)/3.;vec3 og=vec3(.91,.388,.29);vec3 pk=vec3(.831,.353,.447);vec3 dk=vec3(.102,.067,.075);float ar=res.x/res.y;float ys=mix(ar<1.?.25:.3,ar<1.?.03:.1,y*y);float i=ys*mix(.5,1.,pow(b,1.4));gl_FragColor=vec4(mix(dk,mix(og,pk,w2),i),1.);}');
  gl.compileShader(fs);

  var prog = gl.createProgram();
  gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
  gl.useProgram(prog);

  var buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,1,-1,-1,1,1,1]), gl.STATIC_DRAW);
  var pLoc = gl.getAttribLocation(prog, 'p');
  gl.enableVertexAttribArray(pLoc);
  gl.vertexAttribPointer(pLoc, 2, gl.FLOAT, false, 0, 0);

  var tLoc = gl.getUniformLocation(prog, 't');
  var resLoc = gl.getUniformLocation(prog, 'res');
  var start = performance.now();

  function resize() {
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    gl.viewport(0, 0, canvas.width, canvas.height);
  }
  resize();
  window.addEventListener('resize', resize);

  (function tick() {
    gl.uniform1f(tLoc, (performance.now() - start) / 1000);
    gl.uniform2f(resLoc, canvas.width || 1, canvas.height || 1);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    requestAnimationFrame(tick);
  })();
}

// Auto-start when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  requestAnimationFrame(startAuthGlow);
});
