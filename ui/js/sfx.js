/**
 * Aether Sound Design & Procedural Web Audio Synthesizer
 * Ported & adapted from J.A.R.V.I.S. (jarvis-main) sfx.ts
 *
 * Every sound cue is synthesized in code using the Web Audio API without
 * needing external audio files:
 *  - 'boot': Reactor spin-up with stacked harmonic fifths and rising confirmation third.
 *  - 'wake': Ascending tactical pips (1046Hz -> 1568Hz).
 *  - 'listen': Soft acoustic focus blip (660Hz).
 *  - 'tool': High-tech mechanical tick & transient noise sweep (2200Hz).
 *  - 'done': Harmonic descending resolution pair (1320Hz -> 880Hz).
 *  - 'error': Dissonant warning square wave blips (320Hz -> 226Hz).
 *  - 'duck': Audio ducking (45% attenuation) during assistant speech to prevent collisions.
 */

(function (window) {
  let ctx = null;
  let master = null;
  let volume = 0.55;
  let ducked = false;
  const DUCK_FACTOR = 0.45;

  function getAudioCtx() {
    if (!ctx) {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (AudioCtxClass) {
        ctx = new AudioCtxClass();
        master = ctx.createGain();
        master.gain.value = volume;
        master.connect(ctx.destination);
      }
    }
    return ctx;
  }

  function rampTo(param, targetVal, seconds) {
    if (!ctx) return;
    const now = ctx.currentTime;
    param.cancelScheduledValues(now);
    param.setValueAtTime(param.value, now);
    param.linearRampToValueAtTime(Math.max(0.0001, targetVal), now + seconds);
  }

  function blip(freq, opts) {
    const c = getAudioCtx();
    if (!c) return;
    const at = (opts && opts.at) || 0;
    const dur = (opts && opts.dur) || 0.12;
    const type = (opts && opts.type) || 'sine';
    const gain = (opts && opts.gain) || 0.25;
    const sweepTo = (opts && opts.sweepTo) || 0;

    const t = c.currentTime + at;
    const osc = c.createOscillator();
    const env = c.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq, t);
    if (sweepTo) {
      osc.frequency.exponentialRampToValueAtTime(sweepTo, t + dur);
    }

    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(gain, t + 0.008);
    env.gain.exponentialRampToValueAtTime(0.0001, t + dur);

    osc.connect(env);
    env.connect(master);
    osc.start(t);
    osc.stop(t + dur + 0.02);
  }

  function noise(opts) {
    const c = getAudioCtx();
    if (!c) return;
    const at = (opts && opts.at) || 0;
    const dur = (opts && opts.dur) || 0.4;
    const gain = (opts && opts.gain) || 0.1;
    const from = (opts && opts.from) || 200;
    const to = (opts && opts.to) || 800;

    const t = c.currentTime + at;
    const sampleRate = c.sampleRate;
    const buffer = c.createBuffer(1, Math.floor(sampleRate * dur), sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const src = c.createBufferSource();
    src.buffer = buffer;

    const filter = c.createBiquadFilter();
    filter.type = 'bandpass';
    filter.Q.value = 3.0;
    filter.frequency.setValueAtTime(from, t);
    filter.frequency.exponentialRampToValueAtTime(to, t + dur);

    const env = c.createGain();
    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(gain, t + dur * 0.25);
    env.gain.exponentialRampToValueAtTime(0.0001, t + dur);

    src.connect(filter);
    filter.connect(env);
    env.connect(master);
    src.start(t);
  }

  const synth = {
    boot: function () {
      noise({ dur: 1.8, gain: 0.08, from: 120, to: 4800 });
      blip(110, { dur: 2.0, type: 'sawtooth', gain: 0.08, sweepTo: 880 });
      blip(220, { at: 0.1, dur: 1.8, type: 'sine', gain: 0.08, sweepTo: 1320 });
      blip(880, { at: 1.6, dur: 0.25, gain: 0.15 });
      blip(1320, { at: 1.75, dur: 0.35, gain: 0.18 });
    },

    wake: function () {
      blip(1046, { dur: 0.09, gain: 0.20 });
      blip(1568, { at: 0.07, dur: 0.14, gain: 0.18 });
    },

    listen: function () {
      blip(660, { dur: 0.09, gain: 0.12 });
    },

    tool: function () {
      blip(2200, { dur: 0.05, type: 'square', gain: 0.06 });
      noise({ dur: 0.08, gain: 0.04, from: 3000, to: 900 });
    },

    done: function () {
      blip(1320, { dur: 0.10, gain: 0.14 });
      blip(880, { at: 0.08, dur: 0.18, gain: 0.12 });
    },

    error: function () {
      blip(320, { dur: 0.16, type: 'square', gain: 0.14 });
      blip(226, { at: 0.12, dur: 0.25, type: 'square', gain: 0.12 });
    }
  };

  async function unlockAudio() {
    const c = getAudioCtx();
    if (c && c.state === 'suspended') {
      try {
        await c.resume();
      } catch (e) {
        // Ignored for non-interactive init
      }
    }
  }

  function play(cue) {
    try {
      unlockAudio();
      if (synth[cue]) {
        synth[cue]();
      }
    } catch (e) {
      console.warn('[SFX] Synthesis notice:', e);
    }
  }

  function duck(on) {
    if (ducked === on || !master) return;
    ducked = on;
    rampTo(master.gain, on ? volume * DUCK_FACTOR : volume, on ? 0.1 : 0.4);
  }

  function setMasterVolume(v) {
    volume = Math.max(0, Math.min(1, v));
    if (master) {
      rampTo(master.gain, ducked ? volume * DUCK_FACTOR : volume, 0.05);
    }
  }

  // Global exports
  window.AetherSfx = {
    play: play,
    duck: duck,
    unlock: unlockAudio,
    setVolume: setMasterVolume
  };

  window.playSfx = play;
  window.duckSfx = duck;

  // Auto-unlock on first document interaction
  const unlockEvents = ['click', 'keydown', 'touchstart'];
  function onFirstUserGesture() {
    unlockAudio();
    unlockEvents.forEach(evt => document.removeEventListener(evt, onFirstUserGesture));
  }
  unlockEvents.forEach(evt => document.addEventListener(evt, onFirstUserGesture, { once: true }));
})(window);
