/**
 * Acoustic Clap Detection Engine
 * Ported & adapted from J.A.R.V.I.S. (jarvis-main) clap.ts
 *
 * Distinguishes a true physical clap from doors, coughs, or dropped items by shape:
 * - Quiet before: silence in room immediately prior to strike.
 * - Sharp rise: climbs to peak within milliseconds (<10ms).
 * - Fast collapse: decays below 35% of peak within 130ms.
 */

(function (window) {
  const PEAK_OVER_FLOOR = 6.5;
  const MIN_PEAK = 0.050;
  const QUIET_BEFORE = 0.18;
  const HISTORY_SIZE = 20;
  const LOOKBACK = 5;
  const DECAY_TO = 0.35;
  const DECAY_MS = 130;
  const GIVE_UP_MS = 260;
  const COOLDOWN_MS = 1200;

  let stream = null;
  let audioCtx = null;
  let analyser = null;
  let rafId = 0;
  let isListening = false;

  async function startClapDetection(onClap) {
    if (isListening) return;

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.log('[Clap] MediaDevices not available in current context.');
        return;
      }
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false
        }
      });
    } catch (e) {
      console.log('[Clap] Microphone access declined or unavailable:', e);
      return;
    }

    const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
    audioCtx = new AudioCtxClass();
    if (audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {});
    }

    const source = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 512;
    analyser.smoothingTimeConstant = 0;
    source.connect(analyser);

    const buf = new Float32Array(analyser.fftSize);
    const history = [];
    let floor = 0.01;
    let lastClap = 0;
    let candidate = null;

    const computeRms = () => {
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) {
        sum += buf[i] * buf[i];
      }
      return Math.sqrt(sum / buf.length);
    };

    const tick = () => {
      if (!isListening) return;
      rafId = requestAnimationFrame(tick);

      const now = performance.now();
      const level = computeRms();
      history.push(level);
      if (history.length > HISTORY_SIZE) history.shift();

      if (!candidate && level < floor * 3) {
        floor += (level - floor) * 0.05;
        floor = Math.max(floor, 0.002);
      }

      if (candidate) {
        if (level < candidate.peak * DECAY_TO && now - candidate.at < DECAY_MS) {
          // Sharp transient confirmed: quiet -> instant attack -> fast collapse
          candidate = null;
          lastClap = now;
          console.log('[Clap] Acoustic clap detected.');
          if (typeof onClap === 'function') {
            onClap();
          }
        } else if (now - candidate.at > GIVE_UP_MS) {
          candidate = null;
        } else {
          candidate.peak = Math.max(candidate.peak, level);
        }
        return;
      }

      if (now - lastClap < COOLDOWN_MS) return;
      if (level < MIN_PEAK || level < floor * PEAK_OVER_FLOOR) return;

      const before = history[history.length - 1 - LOOKBACK];
      if (before === undefined || before > level * QUIET_BEFORE) {
        return;
      }

      candidate = { at: now, peak: level };
    };

    isListening = true;
    tick();
    console.log('[Clap] Acoustic clap listener operational.');
  }

  function stopClapDetection() {
    isListening = false;
    if (rafId) cancelAnimationFrame(rafId);
    if (stream) {
      stream.getTracks().forEach(t => t.stop());
      stream = null;
    }
    if (audioCtx) {
      audioCtx.close().catch(() => {});
      audioCtx = null;
    }
  }

  window.AetherClap = {
    start: startClapDetection,
    stop: stopClapDetection
  };
})(window);
