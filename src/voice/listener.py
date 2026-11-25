import time
import json
import threading
import collections
import locale
import numpy as np
import sounddevice as sd
import speech_recognition as sr

class VoiceListener:
    def __init__(self, on_speech_detected=None, on_rms_update=None, on_state_change=None, on_barge_in=None, language: str = None):
        self.on_speech_detected = on_speech_detected
        self.on_rms_update = on_rms_update
        self.on_state_change = on_state_change
        self.on_barge_in = on_barge_in

        # Locale-aware regional English acoustic mapping
        if language:
            self.language = language
        else:
            try:
                sys_loc = locale.getlocale()[0] or ""
                self.language = "en-IN" if ("India" in sys_loc or "IN" in sys_loc) else "en-US"
            except Exception:
                self.language = "en-IN"

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = False

        self.is_running = False
        self.is_speaking = False
        self.is_enabled = True

        self.sample_rate = 16000
        self.block_size = 1024

        # Pre-roll rolling ring buffer (keeps last ~380ms of audio so initial consonants aren't cut)
        self.pre_buffer = collections.deque(maxlen=6)

        # Dynamic VAD & Noise Rejection State
        self.is_user_speaking = False
        self.speech_buffer = []
        self.silence_blocks = 0
        self.consecutive_speech_blocks = 0
        self.barge_in_consecutive_blocks = 0

        # ~0.70s of silence after speech to trigger instant processing (prevents premature cutoffs)
        self.silence_limit = int(0.70 * (self.sample_rate / self.block_size))
        # At least ~0.40s of speech to ignore brief clicks and background thumps
        self.min_speech_blocks = int(0.40 * (self.sample_rate / self.block_size))

        self.ambient_rms = 260.0
        self.speech_threshold = 520.0

        self.thread = None
        self.stream = None
        self.speech_safety_timer = None

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass

    def set_speaking(self, speaking: bool):
        """Set True when TTS is talking to prevent acoustic feedback loop"""
        self.is_speaking = speaking
        self.barge_in_consecutive_blocks = 0
        self.consecutive_speech_blocks = 0
        if speaking:
            self.speech_buffer = []
            self.is_user_speaking = False

            # Safety watchdog: automatically restore listening after 8 seconds in case TTS event is dropped
            if self.speech_safety_timer:
                self.speech_safety_timer.cancel()
            self.speech_safety_timer = threading.Timer(8.0, self._auto_release_speaking)
            self.speech_safety_timer.daemon = True
            self.speech_safety_timer.start()
        else:
            if self.speech_safety_timer:
                self.speech_safety_timer.cancel()

    def _auto_release_speaking(self):
        if self.is_speaking:
            print("[VoiceListener] ⚠️ Safety watchdog: auto-restoring mic listening state.")
            self.is_speaking = False
            self.barge_in_consecutive_blocks = 0
            if self.on_state_change:
                self.on_state_change("idle")

    def toggle(self):
        self.is_enabled = not self.is_enabled
        print(f"[VoiceListener] Voice intercept {'resumed' if self.is_enabled else 'suspended'}.")
        return self.is_enabled

    def set_enabled(self, enabled: bool) -> bool:
        self.is_enabled = bool(enabled)
        print(f"[VoiceListener] Voice intercept {'enabled' if self.is_enabled else 'disabled'}.")
        return self.is_enabled

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_running or not self.is_enabled:
            return

        data_int16 = indata[:, 0]

        # Calculate current block RMS energy
        rms = float(np.sqrt(np.mean(data_int16.astype(float) ** 2)))

        # Push normalized RMS to visualizer (0.0 to 1.0)
        norm_rms = min(1.0, max(0.0, (rms - self.ambient_rms) / 800.0))
        if self.on_rms_update:
            self.on_rms_update(norm_rms)

        # ─── Case 1: Assistant is Speaking (TTS Active) ───────────────────────
        # The speakers are playing audio into the room.
        # Normal room noise, keyboard clicks, or speaker audio must NEVER interrupt.
        # Only a deliberate, sustained, loud user command ("STOP!", "WAIT!") can barge in.
        if self.is_speaking:
            barge_in_threshold = max(900.0, self.ambient_rms * 3.2 + 250.0)
            if rms > barge_in_threshold:
                self.barge_in_consecutive_blocks += 1
                if self.barge_in_consecutive_blocks >= 3:
                    print(f"[VoiceListener] ⚡ FLUID BARGE-IN DETECTED (RMS {rms:.1f} > {barge_in_threshold:.1f})! Halting TTS...")
                    self.is_speaking = False
                    self.barge_in_consecutive_blocks = 0
                    if self.on_barge_in:
                        try:
                            self.on_barge_in()
                        except Exception as e:
                            print(f"[VoiceListener] on_barge_in callback error: {e}")
            else:
                self.barge_in_consecutive_blocks = 0
            return

        # ─── Case 2: Assistant is Idle (Listening for User Commands) ──────────
        if rms > self.speech_threshold:
            self.consecutive_speech_blocks += 1
            # Require at least 2 consecutive high-energy blocks (~130ms) to reject single-block clicks
            if self.consecutive_speech_blocks >= 2:
                if not self.is_user_speaking:
                    self.is_user_speaking = True
                    # Include pre-roll buffer to preserve the first syllable
                    self.speech_buffer = list(self.pre_buffer) + [data_int16.copy()]
                    print(f"[VoiceListener] 🎙️ Speech locked (RMS: {rms:.1f} > {self.speech_threshold:.1f})...")
                    if self.on_state_change:
                        self.on_state_change("listening")
                else:
                    self.speech_buffer.append(data_int16.copy())
                self.silence_blocks = 0
            else:
                self.pre_buffer.append(data_int16.copy())
        else:
            self.consecutive_speech_blocks = 0
            if self.is_user_speaking:
                self.speech_buffer.append(data_int16.copy())
                self.silence_blocks += 1

                # If silence duration reached, finish capture and transcribe
                if self.silence_blocks > self.silence_limit:
                    self.is_user_speaking = False
                    self.silence_blocks = 0
                    if len(self.speech_buffer) >= self.min_speech_blocks:
                        captured_audio = np.concatenate(self.speech_buffer)
                        self.speech_buffer = []
                        print(f"[VoiceListener] ⏹️ Speech phrase captured ({len(captured_audio)/self.sample_rate:.2f}s). Transcribing...")
                        threading.Thread(target=self._transcribe, args=(captured_audio,), daemon=True).start()
                    else:
                        self.speech_buffer = []
                        if self.on_state_change:
                            self.on_state_change("idle")
            else:
                # User is quiet: update pre-buffer and continuously adapt ambient noise floor
                self.pre_buffer.append(data_int16.copy())
                self.ambient_rms = 0.99 * self.ambient_rms + 0.01 * rms
                self.speech_threshold = max(480.0, min(1200.0, self.ambient_rms * 2.2 + 160.0))

    def _calibrate_noise(self):
        """Calibrates microphone ambient noise floor for 1 second"""
        print("[VoiceListener] Calibrating microphone acoustics...")
        try:
            samples = sd.rec(int(1.0 * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype='int16')
            sd.wait()
            calib_rms = float(np.sqrt(np.mean(samples.astype(float) ** 2)))
            self.ambient_rms = max(180.0, min(600.0, calib_rms))
            self.speech_threshold = max(480.0, min(1200.0, self.ambient_rms * 2.2 + 160.0))
            print(f"[VoiceListener] ✓ Calibration complete: Ambient RMS={self.ambient_rms:.1f}, Speech Threshold={self.speech_threshold:.1f}")
        except Exception as e:
            print(f"[VoiceListener] Calibration fallback: {e}")
            self.ambient_rms = 260.0
            self.speech_threshold = 520.0
            print(f"[VoiceListener] ✓ Calibration complete: Ambient RMS={self.ambient_rms:.1f}, Speech Threshold={self.speech_threshold:.1f}")
        except Exception as e:
            print(f"[VoiceListener] Calibration fallback: {e}")
            self.ambient_rms = 260.0
            self.speech_threshold = 380.0

    def _run_loop(self):
        self._calibrate_noise()
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16',
                blocksize=self.block_size,
                callback=self._audio_callback
            )
            with self.stream:
                print("[VoiceListener] ✓ Microphone stream active and listening.")
                while self.is_running:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[VoiceListener] Stream error: {e}")

    def _transcribe(self, audio_data_int16):
        if self.on_state_change:
            self.on_state_change("thinking")

        raw_bytes = audio_data_int16.tobytes()
        audio_data = sr.AudioData(raw_bytes, self.sample_rate, 2)

        text = None
        primary_lang = self.language or "en-IN"
        fallback_lang = "en-US" if "IN" in primary_lang else "en-IN"

        # Multi-dialect resilient speech recognition
        try:
            text = self.recognizer.recognize_google(audio_data, language=primary_lang)
        except sr.UnknownValueError:
            # Try alternate English dialect before giving up
            try:
                text = self.recognizer.recognize_google(audio_data, language=fallback_lang)
            except Exception:
                text = None
        except Exception as e:
            print(f"[VoiceListener] STT network error ({primary_lang}): {e}")
            try:
                text = self.recognizer.recognize_google(audio_data, language=fallback_lang)
            except Exception:
                text = None

        if text and text.strip():
            print(f"[VoiceListener] 💬 Intercepted voice: '{text}'")
            if self.on_speech_detected:
                self.on_speech_detected(text.strip())
        else:
            if self.on_state_change:
                self.on_state_change("idle")
