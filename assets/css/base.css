@import url('https://fonts.googleapis.com/css2?family=Bitter:wght@300;400;500&family=Lora:ital,wght@0,500;1,500&family=Noto+Serif+Display:wght@600&family=DM+Sans:wght@300;400;500;600&display=swap');

*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}

:root{
  --bg:#2a2a2a;--sidebar:#232323;--sidebar-hover:#2c2c2c;--sidebar-active:#343434;
  --border:#353535;--surface:#333;--text:#e8e8e8;--text-sub:#9a9a9a;
  --text-muted:#636363;--text-dim:#4e4e4e;--input-bg:#252525;
  --input-border:#393939;--input-focus:#4a4a4a;
  --orange:#e8764a;--pink:#d44a7a;
  --grad:linear-gradient(135deg,#e8764a,#d44a7a);
  --auth-bg:#1a1118;
  --font:'DM Sans',-apple-system,BlinkMacSystemFont,sans-serif;
  --font-display:'Noto Serif Display',Georgia,serif;
  --font-logo:'Lora',Georgia,serif;
  --font-body:'Bitter',Georgia,serif;
  --ease-smooth:cubic-bezier(.16,1,.3,1);
  --ease-bounce:cubic-bezier(.34,1.4,.64,1);
}

body{font-family:var(--font);background:var(--bg);color:var(--text);height:100vh;overflow:hidden;-webkit-font-smoothing:antialiased;}
::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px;}
textarea::placeholder,input::placeholder{color:var(--text-dim);}

@keyframes fadeUp{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:translateY(0);}}
@keyframes fadeIn{from{opacity:0;}to{opacity:1;}}
@keyframes blink{0%,100%{opacity:1;}50%{opacity:0;}}
@keyframes bDot{0%,60%,100%{opacity:.25;transform:scale(.8);}30%{opacity:1;transform:scale(1.15);}}

.hidden{display:none!important;}

/* Shared background layers (used by auth + offline) */
.auth-glow-canvas{position:absolute;inset:0;z-index:0;width:100%;height:100%;}
.auth-grain{position:absolute;inset:0;z-index:1;opacity:.03;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");background-size:200px;pointer-events:none;}
.auth-vignette{position:absolute;inset:0;z-index:1;background:radial-gradient(ellipse at center,transparent 40%,rgba(10,6,8,.5) 100%);pointer-events:none;}
