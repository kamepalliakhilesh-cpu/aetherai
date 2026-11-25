/**
 * PIKO / AETHER Singularity — Solaris WebGL Particle Core
 * Extracted directly from aether.ai assets
 */
(function() {
  const S = {
    state: 'idle',
    palette: 'solar',
    tier: 'high',
    reducedMotion: false,
    time: 0,
    impulse: 0,
    rotX: 0.15,
    rotY: 0.0,
    targetRotX: 0.15,
    targetRotY: 0.0,
    isDrag: false,
    prevX: 0,
    prevY: 0
  };

  let isPaused = false;
  let animId = null;

  const palettes = {
    solar: {
      core: [1.00, 0.72, 0.28],  // Warm Gold
      mid: [0.96, 0.32, 0.45],   // Rose Nebula
      outer: [1.00, 0.95, 0.88]  // Champagne Silk
    }
  };

  const VS = `
    uniform float uTime;
    uniform float uPixelRatio;
    uniform float uListening;
    uniform float uThinking;
    uniform float uSpeaking;
    uniform float uImpulse;
    uniform vec3  uColorCore;
    uniform vec3  uColorMid;
    uniform vec3  uColorOuter;

    attribute float aRandom;
    attribute float aShell;
    attribute vec3  aOrbitAxis;

    varying vec3  vColor;
    varying float vAlpha;
    varying float vShell;

    vec3 mod289(vec3 x){ return x-floor(x*(1.0/289.0))*289.0; }
    vec4 mod289(vec4 x){ return x-floor(x*(1.0/289.0))*289.0; }
    vec4 permute(vec4 x){ return mod289(((x*34.0)+1.0)*x); }
    vec4 taylorInvSqrt(vec4 r){ return 1.79284291400159 - 0.85373472095314*r; }

    float snoise(vec3 v){
        const vec2 C = vec2(1.0/6.0, 1.0/3.0);
        const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
        vec3 i  = floor(v + dot(v, C.yyy));
        vec3 x0 = v - i + dot(i, C.xxx);
        vec3 g = step(x0.yzx, x0.xyz);
        vec3 l = 1.0 - g;
        vec3 i1 = min(g.xyz, l.zxy);
        vec3 i2 = max(g.xyz, l.zxy);
        vec3 x1 = x0 - i1 + C.xxx;
        vec3 x2 = x0 - i2 + C.yyy;
        vec3 x3 = x0 - D.yyy;
        i = mod289(i);
        vec4 p = permute(permute(permute(
                    i.z + vec4(0.0, i1.z, i2.z, 1.0))
                + i.y + vec4(0.0, i1.y, i2.y, 1.0))
                + i.x + vec4(0.0, i1.x, i2.x, 1.0));
        float n_ = 0.142857142857;
        vec3 ns = n_ * D.wyz - D.xzx;
        vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
        vec4 x_ = floor(j * ns.z);
        vec4 y_ = floor(j - 7.0 * x_);
        vec4 x = x_ *ns.x + ns.yyyy;
        vec4 y = y_ *ns.x + ns.yyyy;
        vec4 h = 1.0 - abs(x) - abs(y);
        vec4 b0 = vec4(x.xy, y.xy);
        vec4 b1 = vec4(x.zw, y.zw);
        vec4 s0 = floor(b0)*2.0 + 1.0;
        vec4 s1 = floor(b1)*2.0 + 1.0;
        vec4 sh = -step(h, vec4(0.0));
        vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
        vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
        vec3 p0 = vec3(a0.xy, h.x);
        vec3 p1 = vec3(a0.zw, h.y);
        vec3 p2 = vec3(a1.xy, h.z);
        vec3 p3 = vec3(a1.zw, h.w);
        vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
        p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
        vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
        m = m * m;
        return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
    }

    vec3 curlNoise(vec3 p){
        const float e = 0.005;
        float n1 = snoise(vec3(p.x, p.y + e, p.z));
        float n2 = snoise(vec3(p.x, p.y - e, p.z));
        float n3 = snoise(vec3(p.x, p.y, p.z + e));
        float n4 = snoise(vec3(p.x, p.y, p.z - e));
        float n5 = snoise(vec3(p.x + e, p.y, p.z));
        float n6 = snoise(vec3(p.x - e, p.y, p.z));
        return vec3((n1 - n2) - (n3 - n4), (n3 - n4) - (n5 - n6), (n5 - n6) - (n1 - n2)) / (2.0 * e);
    }

    vec3 rotateOnAxis(vec3 v, vec3 axis, float angle) {
        return v * cos(angle) + cross(axis, v) * sin(angle) + axis * dot(axis, v) * (1.0 - cos(angle));
    }

    void main(){
        vShell = aShell;
        float orbitSpeed = (1.0 + aRandom * 0.4) * (0.18 + uThinking * 0.45 + uSpeaking * 0.25);
        vec3 pos = rotateOnAxis(position, aOrbitAxis, uTime * orbitSpeed);

        vec3 curl = curlNoise(pos * 0.72 + vec3(uTime * 0.12));
        float dispAmp = 0.08 + uListening * 0.18 + uThinking * 0.35 + uSpeaking * 0.22 + uImpulse * 0.4;
        pos += curl * dispAmp;

        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
        gl_Position = projectionMatrix * mvPosition;

        float baseSize = mix(2.6, 6.0, aRandom);
        if(aShell > 1.5) baseSize *= 1.4;
        baseSize *= (1.0 + uImpulse * 0.6 + uSpeaking * 0.35);
        gl_PointSize = (baseSize * uPixelRatio) * (2.8 / -mvPosition.z);

        vec3 col = mix(uColorCore, uColorMid, smoothstep(0.0, 1.2, aShell));
        col = mix(col, uColorOuter, smoothstep(1.0, 2.0, aShell) * 0.6);
        col += vec3(uImpulse * 0.35);

        vColor = col;
        float alpha = mix(0.55, 0.95, aRandom);
        alpha *= (1.0 - aShell * 0.18);
        vAlpha = alpha;
    }
  `;

  const FS = `
    varying vec3  vColor;
    varying float vAlpha;
    varying float vShell;

    void main(){
        vec2 c = gl_PointCoord - vec2(0.5);
        float d = length(c);
        if(d > 0.5) discard;

        float core = 1.0 - smoothstep(0.0, 0.22, d);
        float halo = 1.0 - smoothstep(0.15, 0.5, d);
        float alpha = (core * 0.8 + halo * 0.4) * vAlpha;
        vec3 col = vColor + vec3(core * 0.5);
        gl_FragColor = vec4(col * 1.35, clamp(alpha, 0.0, 1.0));
    }
  `;

  let scene, camera, renderer, group, cloud, halo, uniforms;

  function initSingularity() {
    const container = document.getElementById('webglCanvas');
    if (!container) return;

    const W = window.innerWidth, H = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    try {
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(38, W / H, 0.1, 100);
      camera.position.z = 4.6;

      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'default' });
      renderer.setSize(W, H);
      renderer.setPixelRatio(dpr);
      container.replaceChildren();
      container.appendChild(renderer.domElement);

      group = new THREE.Group();
      group.position.y = 0.12;
      scene.add(group);

      const pal = palettes.solar;
      uniforms = {
        uTime:       { value: 0 },
        uPixelRatio: { value: dpr },
        uListening:  { value: 0 },
        uThinking:   { value: 0 },
        uSpeaking:   { value: 0 },
        uImpulse:    { value: 0 },
        uColorCore:  { value: new THREE.Color(...pal.core) },
        uColorMid:   { value: new THREE.Color(...pal.mid) },
        uColorOuter: { value: new THREE.Color(...pal.outer) }
      };

      // Inner halo
      const hg = new THREE.SphereGeometry(0.95, 32, 32);
      const hm = new THREE.ShaderMaterial({
        uniforms: { uColorCore: uniforms.uColorCore, uColorMid: uniforms.uColorMid, uTime: uniforms.uTime },
        vertexShader: `
          varying vec3 vNormal, vView;
          void main(){
            vNormal=normalize(normalMatrix*normal);
            vec4 mv=modelViewMatrix*vec4(position,1.0);
            vView=-mv.xyz;
            gl_Position=projectionMatrix*mv;
          }
        `,
        fragmentShader: `
          uniform vec3 uColorCore, uColorMid;
          uniform float uTime;
          varying vec3 vNormal, vView;
          void main(){
            vec3 n=normalize(vNormal);
            vec3 v=normalize(vView);
            float rim=dot(n,v);
            float glow=pow(clamp(rim,0.0,1.0),2.2)*(0.28+0.06*sin(uTime*2.5));
            vec3 col=mix(uColorMid,uColorCore,rim);
            gl_FragColor=vec4(col,glow);
          }
        `,
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      });
      halo = new THREE.Mesh(hg, hm);
      group.add(halo);

      // Particle count for high fidelity desktop
      const count = 22000;
      const pos = new Float32Array(count * 3);
      const rnd = new Float32Array(count);
      const shl = new Float32Array(count);
      const orb = new Float32Array(count * 3);
      const gr = (1 + Math.sqrt(5)) / 2;

      for (let i = 0; i < count; i++) {
        let r, sh;
        if (i < count * 0.5) { r = 0.88 + (Math.random() - 0.5) * 0.22; sh = 0; }
        else if (i < count * 0.85) { r = 1.15 + (Math.random() - 0.5) * 0.28; sh = 1; }
        else { r = 1.44 + (Math.random() - 0.5) * 0.44; sh = 2; }

        const idx = i + 0.5;
        const phi = Math.acos(1 - 2 * (idx / count));
        const theta = 2 * Math.PI * idx / gr;
        pos[i*3]   = r * Math.sin(phi) * Math.cos(theta);
        pos[i*3+1] = r * Math.sin(phi) * Math.sin(theta);
        pos[i*3+2] = r * Math.cos(phi);
        rnd[i] = Math.random();
        shl[i] = sh;
        const ax = Math.random() - 0.5, ay = Math.random() - 0.5, az = Math.random() - 0.5;
        const len = Math.sqrt(ax * ax + ay * ay + az * az) || 1;
        orb[i*3] = ax / len; orb[i*3+1] = ay / len; orb[i*3+2] = az / len;
      }

      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      geo.setAttribute('aRandom', new THREE.BufferAttribute(rnd, 1));
      geo.setAttribute('aShell', new THREE.BufferAttribute(shl, 1));
      geo.setAttribute('aOrbitAxis', new THREE.BufferAttribute(orb, 3));

      const mat = new THREE.ShaderMaterial({
        vertexShader: VS, fragmentShader: FS, uniforms,
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending
      });
      cloud = new THREE.Points(geo, mat);
      group.add(cloud);

      bindInteraction();
      animId = requestAnimationFrame(animate);
    } catch (e) {
      console.warn('[Singularity] Init error:', e);
    }
  }

  function animate(now) {
    if (isPaused) return;

    const tL = S.state === 'listening' ? 1 : 0;
    const tT = S.state === 'thinking' ? 1 : 0;
    const tS = S.state === 'speaking' ? 1 : 0;
    let spd = 1.0;
    if (S.state === 'listening') spd = 1.35;
    else if (S.state === 'thinking') spd = 2.1;
    else if (S.state === 'speaking') spd = 1.75;

    S.time += 0.008 * spd;
    S.impulse *= 0.92;

    if (uniforms) {
      uniforms.uTime.value = S.time;
      uniforms.uListening.value += (tL - uniforms.uListening.value) * 0.07;
      uniforms.uThinking.value += (tT - uniforms.uThinking.value) * 0.07;
      uniforms.uSpeaking.value += (tS - uniforms.uSpeaking.value) * 0.07;
      uniforms.uImpulse.value = S.impulse;
    }

    if (group && cloud && renderer) {
      if (!S.isDrag) {
        S.targetRotY += 0.0022 * spd;
        S.rotY += (S.targetRotY - S.rotY) * 0.06;
        S.rotX += (S.targetRotX - S.rotX) * 0.06;
      }
      group.position.y = 0.12 + Math.sin(now * 0.0014) * 0.05;
      cloud.rotation.y = S.rotY;
      cloud.rotation.x = S.rotX;
      cloud.rotation.z = Math.sin(S.time * 0.3) * 0.08;
      renderer.render(scene, camera);
    }
    animId = requestAnimationFrame(animate);
  }

  function bindInteraction() {
    const c = document.getElementById('webglCanvas');
    const down = (x, y) => {
      S.isDrag = true;
      S.prevX = x;
      S.prevY = y;
      S.impulse = Math.min(1, S.impulse + 0.35);
    };
    const move = (x, y) => {
      if (!S.isDrag) return;
      S.rotY += (x - S.prevX) * 0.007;
      S.rotX += (y - S.prevY) * 0.007;
      S.targetRotY = S.rotY;
      S.targetRotX = S.rotX;
      S.prevX = x;
      S.prevY = y;
    };
    const up = () => { S.isDrag = false; };

    c.addEventListener('mousedown', e => down(e.clientX, e.clientY));
    window.addEventListener('mousemove', e => move(e.clientX, e.clientY));
    window.addEventListener('mouseup', up);

    window.addEventListener('resize', () => {
      if (!renderer || !camera) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.setPixelRatio(dpr);
      if (uniforms) uniforms.uPixelRatio.value = dpr;
    });

    // Zero-Watt Battery Optimization: Halt WebGL rendering when minimized or hidden
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        isPaused = true;
        if (animId) {
          cancelAnimationFrame(animId);
          animId = null;
        }
      } else {
        if (isPaused) {
          isPaused = false;
          animId = requestAnimationFrame(animate);
        }
      }
    });
  }

  // Public Interface
  window.setSingularityState = function(newState) {
    S.state = newState.toLowerCase();
    S.impulse = 0.85;
  };

  window.setAudioRms = function(rms) {
    if (typeof rms === 'number' && !isNaN(rms)) {
      if (uniforms) {
        uniforms.uImpulse.value = Math.max(uniforms.uImpulse.value, Math.min(1.0, rms * 1.5));
      }
    }
  };

  window.initSingularity = initSingularity;
})();
