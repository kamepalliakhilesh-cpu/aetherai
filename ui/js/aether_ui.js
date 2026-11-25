/**
 * Aether / Piko UI Controller
 * Connected with Native Python Hardware Voice Intercept Loop
 */
function escapeHtml(value) {
  const text = document.createElement('span');
  text.textContent = String(value ?? '');
  return text.innerHTML;
}

class AetherUI {
  constructor() {
    this.config = {};
    this.state = 'idle'; // idle, listening, thinking, speaking
    this.synth = window.speechSynthesis;
    this.history = [];
    this.voices = [];
    this.isMicActive = true;
    this.rmsInterval = null;
    this.safetyTimer = null;

    this.initElements();
    this.initTtsVoices();
    this.initPywebview();
    this.bindEvents();

    if (window.initSingularity) {
      window.initSingularity();
    }
  }

  initElements() {
    this.statusEl = document.getElementById('whisperStatus');
    this.headlineEl = document.getElementById('whisperHeadline');
    this.actionBadge = document.getElementById('actionBadge');
    this.proactiveBanner = document.getElementById('proactiveBanner');
    this.voiceOrbWrapper = document.getElementById('voiceOrbWrapper');
    this.voiceOrbBtn = document.getElementById('voiceOrbBtn');
    this.typingInput = document.getElementById('typingInput');
    this.sendBtn = document.getElementById('sendBtn');
    this.visionBtn = document.getElementById('visionBtn');

    this.brandName = document.getElementById('brandName');

    // Drawers & Modals
    this.historyDrawer = document.getElementById('historyDrawer');
    this.historyFeed = document.getElementById('historyFeed');
    this.historyBtn = document.getElementById('historyBtn');
    this.closeHistoryBtn = document.getElementById('closeHistoryBtn');
    this.clearHistoryBtn = document.getElementById('clearHistoryBtn');

    this.telemetryModal = document.getElementById('telemetryModal');
    this.telemetryBtn = document.getElementById('telemetryBtn');
    this.closeTelemetryBtn = document.getElementById('closeTelemetryBtn');

    // Memory Elements
    this.memoryModal = document.getElementById('memoryModal');
    this.closeMemoryBtn = document.getElementById('closeMemoryBtn');
    this.reindexBtn = document.getElementById('reindexBtn');
    this.memFactsCount = document.getElementById('memFactsCount');
    this.memConvsCount = document.getElementById('memConvsCount');
    this.memFilesCount = document.getElementById('memFilesCount');
    this.memChunksCount = document.getElementById('memChunksCount');
    this.memoryFactsList = document.getElementById('memoryFactsList');

    // Environment & Orchestration Elements
    this.environmentModal = document.getElementById('environmentModal');
    this.closeEnvironmentBtn = document.getElementById('closeEnvironmentBtn');
    this.presetCodingBtn = document.getElementById('presetCodingBtn');
    this.presetCinemaBtn = document.getElementById('presetCinemaBtn');
    this.presetDaylightBtn = document.getElementById('presetDaylightBtn');
    this.presetAlertBtn = document.getElementById('presetAlertBtn');
    this.dispExtendBtn = document.getElementById('dispExtendBtn');
    this.dispCloneBtn = document.getElementById('dispCloneBtn');
    this.dispInternalBtn = document.getElementById('dispInternalBtn');
    this.envDisplayInfo = document.getElementById('envDisplayInfo');
    this.envAudioInfo = document.getElementById('envAudioInfo');
    this.envAudioSub = document.getElementById('envAudioSub');
    this.envWifiSsid = document.getElementById('envWifiSsid');
    this.envWifiDetails = document.getElementById('envWifiDetails');
    this.toggleLampBtn = document.getElementById('toggleLampBtn');
    this.envLampStatus = document.getElementById('envLampStatus');
    this.envLightColorLabel = document.getElementById('envLightColorLabel');
    this.envBrightnessSlider = document.getElementById('envBrightnessSlider');
    this.runCodeDiagBtn = document.getElementById('runCodeDiagBtn');
    this.pairDiagOutput = document.getElementById('pairDiagOutput');

    this.settingsModal = document.getElementById('settingsModal');
    this.settingsBtn = document.getElementById('settingsBtn');
    this.closeSettingsBtn = document.getElementById('closeSettingsBtn');
    this.saveSettingsBtn = document.getElementById('saveSettingsBtn');

    // Live API Key Status Header Elements
    this.apiStatusPill = document.getElementById('apiStatusPill');
    this.apiStatusDot = document.getElementById('apiStatusDot');
    this.apiStatusLabel = document.getElementById('apiStatusLabel');

    // Settings Provider & Keys
    this.settingProvider = document.getElementById('settingProvider');
    this.geminiConfigBlock = document.getElementById('geminiConfigBlock');
    this.openrouterConfigBlock = document.getElementById('openrouterConfigBlock');
    this.settingApiKey = document.getElementById('settingApiKey');
    this.settingOpenRouterKey = document.getElementById('settingOpenRouterKey');
    this.settingModelName = document.getElementById('settingModelName');
    this.settingCustomGeminiModel = document.getElementById('settingCustomGeminiModel');
    this.settingOpenRouterModel = document.getElementById('settingOpenRouterModel');
    this.settingCustomOpenRouterModel = document.getElementById('settingCustomOpenRouterModel');
    this.testGeminiBtn = document.getElementById('testGeminiBtn');
    this.testOpenRouterBtn = document.getElementById('testOpenRouterBtn');

    // Test Feedback Card
    this.apiTestCard = document.getElementById('apiTestCard');
    this.apiTestIcon = document.getElementById('apiTestIcon');
    this.apiTestTitle = document.getElementById('apiTestTitle');
    this.apiTestMsg = document.getElementById('apiTestMsg');

    // Telemetry fields
    this.telemCpu = document.getElementById('telemCpu');
    this.telemRam = document.getElementById('telemRam');
    this.telemBat = document.getElementById('telemBat');
    this.telemUptime = document.getElementById('telemUptime');

    // Aether Mobile Link
    this.mobileLinkBtn = document.getElementById('mobileLinkBtn');
    this.mobileChipBtn = document.getElementById('mobileChipBtn');
    this.mobileChipLabel = document.getElementById('mobileChipLabel');
    this.mobileLinkModal = document.getElementById('mobileLinkModal');
    this.closeMobileLinkBtn = document.getElementById('closeMobileLinkBtn');
    this.mobileModalBadge = document.getElementById('mobileModalBadge');
    this.bridgeHostDisplay = document.getElementById('bridgeHostDisplay');
    this.bridgeCodeDisplay = document.getElementById('bridgeCodeDisplay');
    this.bridgeQrImage = document.getElementById('bridgeQrImage');
    this.bridgeTlsBadge = document.getElementById('bridgeTlsBadge');
    this.btnRotateBridgeCode = document.getElementById('btnRotateBridgeCode');
    this.bridgeFpDisplay = document.getElementById('bridgeFpDisplay');
    this.mobileDeviceInfo = document.getElementById('mobileDeviceInfo');
    this.btnRingPhone = document.getElementById('btnRingPhone');
    this.btnSyncClipboard = document.getElementById('btnSyncClipboard');
    this.btnPhoneTorch = document.getElementById('btnPhoneTorch');
    this.btnRefreshMobile = document.getElementById('btnRefreshMobile');

    // Window controls
    this.minimizeBtn = document.getElementById('minimizeBtn');
    this.closeBtn = document.getElementById('closeBtn');

    // Security Confirmation Modal
    this.confirmModal = document.getElementById('confirmModal');
    this.confirmTitle = document.getElementById('confirmTitle');
    this.confirmDetail = document.getElementById('confirmDetail');
    this.confirmAcceptBtn = document.getElementById('confirmAcceptBtn');
    this.confirmCancelBtn = document.getElementById('confirmCancelBtn');
    this.confirmCancelXBtn = document.getElementById('confirmCancelXBtn');
  }

  initTtsVoices() {
    const loadVoices = () => {
      this.voices = this.synth.getVoices();
      const select = document.getElementById('settingVoice');
      if (select && this.voices.length > 0) {
        select.replaceChildren();
        this.voices.forEach(v => {
          const opt = document.createElement('option');
          opt.value = v.name;
          opt.textContent = `${v.name} (${v.lang})`;
          if (this.config.voice_name && v.name.includes(this.config.voice_name)) {
            opt.selected = true;
          }
          select.appendChild(opt);
        });
      }
    };
    loadVoices();
    if (this.synth.onvoiceschanged !== undefined) {
      this.synth.onvoiceschanged = loadVoices;
    }
  }

  initPywebview() {
    window.addEventListener('pywebviewready', async () => {
      // Boot cue
      setTimeout(() => {
        if (window.playSfx) window.playSfx('boot');
      }, 350);

      // Acoustic Clap Detection Engine
      if (window.AetherClap && window.AetherClap.start) {
        window.AetherClap.start(() => this.triggerClapWake());
      }

      if (window.pywebview && window.pywebview.api) {
        try {
          this.config = await window.pywebview.api.get_config();
          this.applyConfig();
          const telem = await window.pywebview.api.get_telemetry();
          this.updateTelemetry(telem);
        } catch (e) {
          console.warn('[AetherUI] Bridge fetch error:', e);
        }
      }
    });

    if (!window.pywebview) {
      setTimeout(() => {
        this.updateTelemetry({
          cpu_percent: 24.5,
          ram_percent: 61.2,
          ram_used_gb: 9.8,
          ram_total_gb: 16.0,
          battery_percent: 82,
          battery_plugged: true,
          battery_time: 'Plugged in',
          uptime: '4h 20m'
        });
      }, 500);
    }
  }

  applyConfig() {
    const name = this.config.assistant_name || 'Aether';
    if (this.brandName) {
      this.brandName.textContent = name;
    }

    const provider = (this.config.provider || 'gemini').toLowerCase();
    if (this.settingProvider) this.settingProvider.value = provider;

    if (this.settingApiKey) this.settingApiKey.value = this.config.gemini_api_key || '';
    if (this.settingOpenRouterKey) this.settingOpenRouterKey.value = this.config.openrouter_api_key || '';

    // Model setups
    const geminiModel = this.config.model_name || 'gemini-2.0-flash';
    if (this.settingModelName) {
      const options = Array.from(this.settingModelName.options).map(o => o.value);
      if (options.includes(geminiModel)) {
        this.settingModelName.value = geminiModel;
        if (this.settingCustomGeminiModel) this.settingCustomGeminiModel.style.display = 'none';
      } else {
        this.settingModelName.value = 'custom';
        if (this.settingCustomGeminiModel) {
          this.settingCustomGeminiModel.value = geminiModel;
          this.settingCustomGeminiModel.style.display = 'block';
        }
      }
    }

    const orModel = this.config.openrouter_model || 'google/gemini-2.0-flash-001';
    if (this.settingOpenRouterModel) {
      const orOptions = Array.from(this.settingOpenRouterModel.options).map(o => o.value);
      if (orOptions.includes(orModel)) {
        this.settingOpenRouterModel.value = orModel;
        if (this.settingCustomOpenRouterModel) this.settingCustomOpenRouterModel.style.display = 'none';
      } else {
        this.settingOpenRouterModel.value = 'custom';
        if (this.settingCustomOpenRouterModel) {
          this.settingCustomOpenRouterModel.value = orModel;
          this.settingCustomOpenRouterModel.style.display = 'block';
        }
      }
    }

    // Toggle provider view
    if (this.geminiConfigBlock && this.openrouterConfigBlock) {
      if (provider === 'openrouter') {
        this.geminiConfigBlock.style.display = 'none';
        this.openrouterConfigBlock.style.display = 'block';
      } else {
        this.geminiConfigBlock.style.display = 'block';
        this.openrouterConfigBlock.style.display = 'none';
      }
    }

    const nameEl = document.getElementById('settingAssistantName');
    if (nameEl) nameEl.value = name;

    const autoListenEl = document.getElementById('settingAutoListen');
    if (autoListenEl) autoListenEl.checked = !!this.config.auto_listen;

    // Check & reflect live API key status
    this.refreshApiStatus();
  }

  async refreshApiStatus() {
    if (!window.pywebview || !window.pywebview.api || !window.pywebview.api.check_api_status) return;

    try {
      const res = await window.pywebview.api.check_api_status();
      const status = (res.status || 'offline').toLowerCase();
      const model = res.model || '';

      if (this.apiStatusDot && this.apiStatusLabel) {
        if (res.valid === true && status === 'active') {
          this.apiStatusDot.className = 'api-status-dot active';
          const shortModel = model.replace('google/', '').replace('anthropic/', '').replace('openai/', '');
          this.apiStatusLabel.textContent = `${(res.provider || 'AI')} · ${shortModel}`;
          this.apiStatusPill.title = `Active: ${res.message || model}`;
        } else if (status === 'error' || res.valid === false) {
          this.apiStatusDot.className = 'api-status-dot error';
          this.apiStatusLabel.textContent = 'Connection error';
          this.apiStatusPill.title = `Error: ${res.message || 'Model or key verification failed'}`;
        } else {
          this.apiStatusDot.className = 'api-status-dot offline';
          this.apiStatusLabel.textContent = 'Local engine';
          this.apiStatusPill.title = 'Offline: Local deterministic intent parser active.';
        }
      }
    } catch (e) {
      console.warn('[AetherUI] refreshApiStatus error:', e);
    }
  }

  async testKey(provider, key, model) {
    if (!this.apiTestCard) return;

    this.apiTestCard.style.display = 'flex';
    this.apiTestCard.className = 'api-test-card';
    this.apiTestTitle.textContent = `Testing ${provider}...`;
    this.apiTestMsg.textContent = 'Verifying API key & selected model connectivity...';

    try {
      let res = null;
      if (window.pywebview && window.pywebview.api && window.pywebview.api.test_key) {
        res = await window.pywebview.api.test_key(provider, key, model);
      } else {
        res = { valid: false, status: 'error', message: 'Bridge unavailable in preview mode.' };
      }

      if (res.valid === true && res.status === 'active') {
        this.apiTestCard.className = 'api-test-card active';
        this.apiTestTitle.textContent = 'Connected';
        this.apiTestMsg.textContent = res.message || 'Key authenticated and selected model operational.';
      } else {
        this.apiTestCard.className = 'api-test-card error';
        const msg = (res.message || '').toLowerCase();
        if (msg.includes('network') || msg.includes('timeout')) {
          this.apiTestTitle.textContent = 'Network timeout';
        } else if (msg.includes('invalid') || msg.includes('format')) {
          this.apiTestTitle.textContent = 'Invalid key format';
        } else if (msg.includes('permission') || msg.includes('403')) {
          this.apiTestTitle.textContent = 'Permission denied (403)';
        } else if (msg.includes('not found') || msg.includes('404') || msg.includes('not supported') || msg.includes('not available')) {
          this.apiTestTitle.textContent = 'Model not found (404)';
        } else if (msg.includes('quota') || msg.includes('429')) {
          this.apiTestTitle.textContent = 'Quota exceeded (429)';
        } else {
          this.apiTestTitle.textContent = 'Authentication failed';
        }
        this.apiTestMsg.textContent = res.message || 'Unable to authenticate key or model.';
      }
    } catch (e) {
      this.apiTestCard.className = 'api-test-card error';
      this.apiTestTitle.textContent = 'Error';
      this.apiTestMsg.textContent = e.message || 'Validation request failed.';
    }
  }

  setAssistantState(newState) {
    this.state = newState;
    if (window.setSingularityState) {
      window.setSingularityState(newState);
    }

    if (this.voiceOrbWrapper) {
      this.voiceOrbWrapper.className = `voice-orb-wrapper ${newState}`;
    }

    const orbSvgIdle = `<svg class="orb-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>`;
    const orbSvgListen = `<svg class="orb-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8"/></svg>`;
    const orbSvgThinking = `<svg class="orb-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg>`;
    const orbSvgSpeaking = `<svg class="orb-icon" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>`;

    if (newState === 'idle') {
      this.statusEl.textContent = 'Ready';
      this.voiceOrbBtn.innerHTML = orbSvgIdle;
      if (window.duckSfx) window.duckSfx(false);
    } else if (newState === 'listening') {
      this.statusEl.textContent = 'Listening...';
      this.headlineEl.textContent = '"Listening..."';
      this.voiceOrbBtn.innerHTML = orbSvgListen;
      if (window.playSfx) window.playSfx('listen');
      if (window.duckSfx) window.duckSfx(false);
    } else if (newState === 'thinking') {
      this.statusEl.textContent = 'Processing...';
      this.headlineEl.textContent = '"Processing..."';
      this.voiceOrbBtn.innerHTML = orbSvgThinking;
      if (window.playSfx) window.playSfx('tool');
    } else if (newState === 'speaking') {
      this.statusEl.textContent = 'Speaking...';
      this.voiceOrbBtn.innerHTML = orbSvgSpeaking;
      if (window.duckSfx) window.duckSfx(true);
    } else if (newState === 'error') {
      this.statusEl.textContent = 'Error';
      this.headlineEl.textContent = '"An error occurred"';
      this.voiceOrbBtn.innerHTML = orbSvgIdle;
      if (window.playSfx) window.playSfx('error');
    }
  }

  onFiller(text) {
    if (!text) return;
    console.log('[AetherUI] Conversational latency filler:', text);
    this.headlineEl.textContent = `"${text}"`;
    if (this.synth && !this.synth.speaking) {
      try {
        const utt = new SpeechSynthesisUtterance(text);
        utt.rate = 1.15;
        const voice = this.voices.find(v => v.name.includes(this.config.voice_name || 'David')) || this.voices[0];
        if (voice) utt.voice = voice;
        this.synth.speak(utt);
      } catch (err) {
        console.warn('[AetherUI] Filler speech notice:', err);
      }
    }
  }

  triggerClapWake() {
    console.log('[AetherUI] Wake signal detected.');
    if (window.playSfx) window.playSfx('wake');
    this.setAssistantState('listening');
    this.headlineEl.textContent = '"Listening..."';
    if (window.pywebview && window.pywebview.api) {
      if (window.pywebview.api.set_voice_listen) {
        window.pywebview.api.set_voice_listen(true);
      } else if (window.pywebview.api.toggle_voice_listen && !this.isMicActive) {
        window.pywebview.api.toggle_voice_listen();
      }
      this.isMicActive = true;
    }
  }

  showConfirmation(title, detail) {
    if (!this.confirmModal) return;
    if (this.confirmTitle) this.confirmTitle.textContent = title || 'Confirm action';
    if (this.confirmDetail) this.confirmDetail.textContent = detail || 'Do you want to authorize this operation?';
    this.confirmModal.style.display = 'flex';
    if (window.playSfx) window.playSfx('wake');
    if (this.confirmAcceptBtn) {
      setTimeout(() => this.confirmAcceptBtn.focus(), 50);
    }
  }

  hideConfirmation() {
    if (this.confirmModal) {
      this.confirmModal.style.display = 'none';
    }
  }

  async resolveConfirmation(accepted) {
    this.hideConfirmation();
    if (window.pywebview && window.pywebview.api && window.pywebview.api.confirm_action) {
      try {
        await window.pywebview.api.confirm_action(!!accepted);
      } catch (e) {
        console.warn('[Confirm] Resolve dispatch error:', e);
      }
    }
  }

  bindEvents() {
    // Confirmation Modal handlers
    if (this.confirmAcceptBtn) {
      this.confirmAcceptBtn.addEventListener('click', () => this.resolveConfirmation(true));
    }
    if (this.confirmCancelBtn) {
      this.confirmCancelBtn.addEventListener('click', () => this.resolveConfirmation(false));
    }
    if (this.confirmCancelXBtn) {
      this.confirmCancelXBtn.addEventListener('click', () => this.resolveConfirmation(false));
    }
    if (this.confirmModal) {
      this.confirmModal.addEventListener('click', (e) => {
        if (e.target === this.confirmModal) {
          this.resolveConfirmation(false);
        }
      });
    }

    // Global Keyboard Navigation: Escape dismisses open modals & drawers
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (this.confirmModal && this.confirmModal.style.display === 'flex') {
          e.preventDefault();
          this.resolveConfirmation(false);
          return;
        }
        const modals = [
          this.historyDrawer,
          this.telemetryModal,
          this.memoryModal,
          this.environmentModal,
          this.settingsModal,
          this.mobileLinkModal
        ];
        let closedAny = false;
        for (const el of modals) {
          if (el && el.style.display && el.style.display !== 'none') {
            el.style.display = 'none';
            closedAny = true;
          }
        }
        if (closedAny) {
          e.preventDefault();
          if (this.typingInput) this.typingInput.focus();
        }
      }
    });

    // Backdrop dismissal for modal dialogs
    [this.memoryModal, this.environmentModal, this.telemetryModal, this.settingsModal, this.mobileLinkModal].forEach(modal => {
      if (modal) {
        modal.addEventListener('click', (e) => {
          if (e.target === modal) {
            modal.style.display = 'none';
          }
        });
      }
    });

    // Voice Orb Click
    this.voiceOrbBtn.addEventListener('click', async () => {
      if (this.state === 'speaking') {
        this.stopSpeech();
        return;
      }
      if (window.pywebview && window.pywebview.api) {
        this.isMicActive = await window.pywebview.api.toggle_voice_listen();
        if (!this.isMicActive) {
          this.headlineEl.textContent = '"Voice input paused."';
          this.setAssistantState('idle');
        } else {
          this.headlineEl.textContent = '"Voice input active."';
        }
      }
    });

    // Send button
    this.sendBtn.addEventListener('click', () => {
      const q = this.typingInput.value.trim();
      if (q) {
        this.handleQuery(q);
        this.typingInput.value = '';
      }
    });

    this.typingInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        if (e.isComposing || e.keyCode === 229) {
          return;
        }
        e.preventDefault();
        const q = this.typingInput.value.trim();
        if (q) {
          this.handleQuery(q);
          this.typingInput.value = '';
        }
      }
    });

    // Vision Scan
    this.visionBtn.addEventListener('click', () => {
      this.handleVision();
    });

    // Quick chips
    document.querySelectorAll('.chip-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const act = btn.dataset.action;
        if (act) {
          this.handleChipAction(act);
        }
      });
    });

    // History Drawer
    this.historyBtn.addEventListener('click', () => {
      this.historyDrawer.style.display = 'flex';
    });
    this.closeHistoryBtn.addEventListener('click', () => {
      this.historyDrawer.style.display = 'none';
    });
    this.clearHistoryBtn.addEventListener('click', () => {
      this.history = [];
      this.historyFeed.replaceChildren();
      this.historyDrawer.style.display = 'none';
      this.headlineEl.textContent = '"History cleared."';
    });

    // Telemetry Modal
    this.telemetryBtn.addEventListener('click', () => {
      this.telemetryModal.style.display = 'flex';
    });
    this.closeTelemetryBtn.addEventListener('click', () => {
      this.telemetryModal.style.display = 'none';
    });

    // Aether Mobile Link Modal
    if (this.mobileLinkBtn) {
      this.mobileLinkBtn.addEventListener('click', () => {
        this.openMobileLinkModal();
      });
    }
    if (this.closeMobileLinkBtn) {
      this.closeMobileLinkBtn.addEventListener('click', () => {
        if (this.mobileLinkModal) this.mobileLinkModal.style.display = 'none';
      });
    }

    if (this.btnRingPhone) {
      this.btnRingPhone.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.send_phone_command) {
          const res = await window.pywebview.api.send_phone_command('ring_phone');
          this.headlineEl.textContent = res.success ? '"Ringing mobile phone at max volume..."' : '"Mobile device is offline."';
        }
      });
    }

    if (this.btnSyncClipboard) {
      this.btnSyncClipboard.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.send_phone_command) {
          const res = await window.pywebview.api.send_phone_command('sync_clipboard');
          this.headlineEl.textContent = res.success ? '"Windows clipboard synced to mobile."' : '"Mobile device is offline."';
        }
      });
    }

    if (this.btnPhoneTorch) {
      this.btnPhoneTorch.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.send_phone_command) {
          const res = await window.pywebview.api.send_phone_command('toggle_flashlight');
          this.headlineEl.textContent = res.success ? '"Toggled mobile flashlight."' : '"Mobile device is offline."';
        }
      });
    }

    if (this.btnRefreshMobile) {
      this.btnRefreshMobile.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.send_phone_command) {
          await window.pywebview.api.send_phone_command('get_battery');
          await this.openMobileLinkModal();
        }
      });
    }

    if (this.btnRotateBridgeCode) {
      this.btnRotateBridgeCode.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.rotate_pairing_code) {
          try {
            const info = await window.pywebview.api.rotate_pairing_code();
            this.renderBridgeInfo(info);
          } catch (e) {
            console.warn('[AetherUI] Rotate pairing code error:', e);
          }
        }
      });
    }

    // Memory Modal
    if (this.closeMemoryBtn) {
      this.closeMemoryBtn.addEventListener('click', () => {
        if (this.memoryModal) this.memoryModal.style.display = 'none';
      });
    }
    if (this.reindexBtn) {
      this.reindexBtn.addEventListener('click', async () => {
        this.reindexBtn.innerHTML = `<span>Indexing...</span>`;
        if (window.pywebview && window.pywebview.api && window.pywebview.api.index_codebase) {
          await window.pywebview.api.index_codebase();
          this.reindexBtn.innerHTML = `<span>Indexed</span>`;
          await this.openMemoryModal();
          setTimeout(() => {
            if (this.reindexBtn) {
              this.reindexBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg><span>Re-index codebase</span>`;
            }
          }, 3000);
        }
      });
    }

    // Environment Modal Listeners
    if (this.closeEnvironmentBtn) {
      this.closeEnvironmentBtn.addEventListener('click', () => {
        if (this.environmentModal) this.environmentModal.style.display = 'none';
      });
    }

    const applyPreset = async (presetName, btnEl) => {
      if (btnEl) btnEl.innerHTML = `<span>...</span>`;
      if (window.pywebview && window.pywebview.api && window.pywebview.api.set_environment_preset) {
        const res = await window.pywebview.api.set_environment_preset(presetName);
        this.headlineEl.textContent = `"${res.message || presetName + ' applied'}"`;
        this.speak(res.message || `${presetName} applied.`);
        await this.openEnvironmentModal();
      }
      if (btnEl) {
        if (presetName === 'coding_focus') {
          btnEl.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg><span>Focus</span>`;
        } else if (presetName === 'cinematic') {
          btnEl.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg><span>Cinema</span>`;
        } else if (presetName === 'daylight') {
          btnEl.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg><span>Daylight</span>`;
        } else if (presetName === 'alert') {
          btnEl.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg><span>Alert</span>`;
        }
      }
    };

    if (this.presetCodingBtn) this.presetCodingBtn.addEventListener('click', () => applyPreset('coding_focus', this.presetCodingBtn));
    if (this.presetCinemaBtn) this.presetCinemaBtn.addEventListener('click', () => applyPreset('cinematic', this.presetCinemaBtn));
    if (this.presetDaylightBtn) this.presetDaylightBtn.addEventListener('click', () => applyPreset('daylight', this.presetDaylightBtn));
    if (this.presetAlertBtn) this.presetAlertBtn.addEventListener('click', () => applyPreset('alert', this.presetAlertBtn));

    // Display switches
    if (this.dispExtendBtn) {
      this.dispExtendBtn.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.switch_display_mode) {
          await window.pywebview.api.switch_display_mode('extend');
          this.headlineEl.textContent = '"Display extended."';
        }
      });
    }
    if (this.dispCloneBtn) {
      this.dispCloneBtn.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.switch_display_mode) {
          await window.pywebview.api.switch_display_mode('clone');
          this.headlineEl.textContent = '"Display duplicated across monitors."';
        }
      });
    }
    if (this.dispInternalBtn) {
      this.dispInternalBtn.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.switch_display_mode) {
          await window.pywebview.api.switch_display_mode('internal');
          this.headlineEl.textContent = '"Laptop display only."';
        }
      });
    }

    // Desk lamp toggle
    if (this.toggleLampBtn) {
      this.toggleLampBtn.addEventListener('click', async () => {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.toggle_desk_lamp) {
          const res = await window.pywebview.api.toggle_desk_lamp();
          const isOn = res.desk_lamp !== false;
          if (this.envLampStatus) {
            this.envLampStatus.textContent = isOn ? 'Illuminated (On)' : 'Off';
            this.envLampStatus.style.color = isOn ? 'var(--accent-amber)' : 'var(--text-muted)';
          }
          this.headlineEl.textContent = isOn ? '"Desk lamp turned on."' : '"Desk lamp turned off."';
        }
      });
    }

    // Ambient light color dots
    document.querySelectorAll('.color-dot-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        document.querySelectorAll('.color-dot-btn').forEach(b => {
          b.classList.remove('active');
          b.style.borderColor = 'transparent';
        });
        btn.classList.add('active');
        btn.style.borderColor = 'rgba(255,255,255,0.85)';
        const color = btn.getAttribute('data-color');
        const brightness = this.envBrightnessSlider ? parseInt(this.envBrightnessSlider.value) : 85;
        if (window.pywebview && window.pywebview.api && window.pywebview.api.set_ambient_lighting) {
          const res = await window.pywebview.api.set_ambient_lighting(color, brightness, 'on');
          const cName = res.light ? res.light.color_name : color;
          if (this.envLightColorLabel) {
            this.envLightColorLabel.textContent = `${cName} (${brightness}%)`;
          }
          this.headlineEl.textContent = `"${res.message || 'Ambient lights calibrated'}"`;
        }
      });
    });

    // Brightness slider
    if (this.envBrightnessSlider) {
      this.envBrightnessSlider.addEventListener('change', async () => {
        const b = parseInt(this.envBrightnessSlider.value);
        if (window.pywebview && window.pywebview.api && window.pywebview.api.set_ambient_lighting) {
          await window.pywebview.api.set_ambient_lighting(null, b, 'on');
          if (this.envLightColorLabel) {
            const curTxt = this.envLightColorLabel.textContent.split('(')[0].trim();
            this.envLightColorLabel.textContent = `${curTxt} (${b}%)`;
          }
        }
      });
    }

    // Pair Programmer Live Diagnostics
    if (this.runCodeDiagBtn) {
      this.runCodeDiagBtn.addEventListener('click', async () => {
        this.runCodeDiagBtn.innerHTML = `<span>Checking...</span>`;
        if (this.pairDiagOutput) this.pairDiagOutput.textContent = 'Running diagnostics...';
        if (window.pywebview && window.pywebview.api && window.pywebview.api.run_code_diagnostics) {
          const res = await window.pywebview.api.run_code_diagnostics('src/app.py');
          if (this.pairDiagOutput) {
            const safeSummary = escapeHtml(res.summary || 'Diagnostics finished.');
            if (res.success) {
              this.pairDiagOutput.innerHTML = `<span style="color: var(--status-positive); font-weight: 600;">[Pass]</span> ${safeSummary}`;
            } else {
              this.pairDiagOutput.innerHTML = `<span style="color: var(--status-negative); font-weight: 600;">[Fail]</span> ${safeSummary}`;
            }
          }
          this.headlineEl.textContent = `"${res.summary}"`;
          this.speak(res.summary);
          this.runCodeDiagBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg><span>Run diagnostic</span>`;
        }
      });
    }

    // API Status Pill Header Click
    if (this.apiStatusPill) {
      this.apiStatusPill.addEventListener('click', () => {
        this.settingsModal.style.display = 'flex';
      });
    }

    // Provider Selector Toggle
    if (this.settingProvider) {
      this.settingProvider.addEventListener('change', () => {
        const val = this.settingProvider.value;
        if (val === 'openrouter') {
          if (this.geminiConfigBlock) this.geminiConfigBlock.style.display = 'none';
          if (this.openrouterConfigBlock) this.openrouterConfigBlock.style.display = 'block';
        } else {
          if (this.geminiConfigBlock) this.geminiConfigBlock.style.display = 'block';
          if (this.openrouterConfigBlock) this.openrouterConfigBlock.style.display = 'none';
        }
      });
    }

    // Custom Model Input Toggles
    if (this.settingModelName) {
      this.settingModelName.addEventListener('change', () => {
        if (this.settingCustomGeminiModel) {
          this.settingCustomGeminiModel.style.display = (this.settingModelName.value === 'custom') ? 'block' : 'none';
        }
      });
    }

    if (this.settingOpenRouterModel) {
      this.settingOpenRouterModel.addEventListener('change', () => {
        if (this.settingCustomOpenRouterModel) {
          this.settingCustomOpenRouterModel.style.display = (this.settingOpenRouterModel.value === 'custom') ? 'block' : 'none';
        }
      });
    }

    // Test Gemini Key
    if (this.testGeminiBtn) {
      this.testGeminiBtn.addEventListener('click', () => {
        const key = this.settingApiKey ? this.settingApiKey.value.trim() : '';
        let model = this.settingModelName ? this.settingModelName.value : 'gemini-2.0-flash';
        if (model === 'custom' && this.settingCustomGeminiModel) {
          model = this.settingCustomGeminiModel.value.trim() || 'gemini-2.0-flash';
        }
        this.testKey('gemini', key, model);
      });
    }

    // Test OpenRouter Key
    if (this.testOpenRouterBtn) {
      this.testOpenRouterBtn.addEventListener('click', () => {
        const key = this.settingOpenRouterKey ? this.settingOpenRouterKey.value.trim() : '';
        let model = this.settingOpenRouterModel ? this.settingOpenRouterModel.value : 'google/gemini-2.0-flash-001';
        if (model === 'custom' && this.settingCustomOpenRouterModel) {
          model = this.settingCustomOpenRouterModel.value.trim() || 'google/gemini-2.0-flash-001';
        }
        this.testKey('openrouter', key, model);
      });
    }

    // Settings Modal
    this.settingsBtn.addEventListener('click', () => {
      this.settingsModal.style.display = 'flex';
      if (this.apiTestCard) this.apiTestCard.style.display = 'none';
    });
    this.closeSettingsBtn.addEventListener('click', () => {
      this.settingsModal.style.display = 'none';
    });
    this.saveSettingsBtn.addEventListener('click', async () => {
      const provider = this.settingProvider ? this.settingProvider.value : 'gemini';

      let geminiModel = this.settingModelName ? this.settingModelName.value : 'gemini-2.0-flash';
      if (geminiModel === 'custom' && this.settingCustomGeminiModel) {
        geminiModel = this.settingCustomGeminiModel.value.trim() || 'gemini-2.0-flash';
      }

      let orModel = this.settingOpenRouterModel ? this.settingOpenRouterModel.value : 'google/gemini-2.0-flash-001';
      if (orModel === 'custom' && this.settingCustomOpenRouterModel) {
        orModel = this.settingCustomOpenRouterModel.value.trim() || 'google/gemini-2.0-flash-001';
      }

      const newCfg = {
        provider: provider,
        gemini_api_key: this.settingApiKey ? this.settingApiKey.value.trim() : '',
        openrouter_api_key: this.settingOpenRouterKey ? this.settingOpenRouterKey.value.trim() : '',
        assistant_name: document.getElementById('settingAssistantName').value.trim() || 'Aether',
        model_name: geminiModel,
        openrouter_model: orModel,
        voice_name: document.getElementById('settingVoice').value,
        auto_listen: document.getElementById('settingAutoListen').checked
      };

      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.save_settings(newCfg);
      }
      this.config = Object.assign(this.config, newCfg);
      this.applyConfig();
      await this.refreshApiStatus();
      this.settingsModal.style.display = 'none';
      this.headlineEl.textContent = `"${this.config.assistant_name} settings saved."`;
    });

    // Window controls
    if (this.minimizeBtn) {
      this.minimizeBtn.addEventListener('click', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.minimize_window();
        }
      });
    }
    if (this.closeBtn) {
      this.closeBtn.addEventListener('click', () => {
        if (window.pywebview && window.pywebview.api) {
          window.pywebview.api.close_window();
        }
      });
    }
  }

  notifySpeakingState(isSpeaking) {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.set_speaking_state(isSpeaking);
    }
  }

  triggerBargeIn() {
    console.log('[Voice] Vocal barge-in detected. Stopping TTS output.');
    if (this.safetyTimer) clearTimeout(this.safetyTimer);
    if (this.rmsInterval) clearInterval(this.rmsInterval);
    if (this.synth) this.synth.cancel();
    window._activeUtterance = null;
    this.notifySpeakingState(false);
    this.setAssistantState('listening');
    this.statusEl.textContent = 'Listening...';
    this.headlineEl.textContent = '"Listening..."';
  }

  stopSpeech() {
    if (this.safetyTimer) clearTimeout(this.safetyTimer);
    if (this.rmsInterval) clearInterval(this.rmsInterval);
    if (this.synth) this.synth.cancel();
    window._activeUtterance = null;
    if (window.setAudioRms) window.setAudioRms(0);
    this.notifySpeakingState(false);
    this.setAssistantState('idle');
  }

  speak(text) {
    if (!this.synth) return;
    this.stopSpeech();

    const clean = text.replace(/[*#_`~]/g, '').trim();
    if (!clean) return;

    const utterance = new SpeechSynthesisUtterance(clean);
    window._activeUtterance = utterance;

    const voice = this.voices.find(v => v.name.includes(this.config.voice_name || 'David')) || this.voices[0];
    if (voice) utterance.voice = voice;

    const telem = this.latestTelemetry || {};
    const cpu = telem.cpu_percent || 0;
    const bat = telem.battery_percent || 100;
    const curHour = new Date().getHours();

    if (cpu > 75 || bat < 15) {
      utterance.rate = 1.15;
      utterance.pitch = 0.98;
    } else if (curHour >= 22 || curHour < 6) {
      utterance.rate = 0.98;
      utterance.pitch = 0.96;
    } else {
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
    }

    const maxDurationMs = Math.max(3500, clean.length * 85);
    this.safetyTimer = setTimeout(() => {
      this.stopSpeech();
    }, maxDurationMs);

    utterance.onstart = () => {
      this.notifySpeakingState(true);
      this.setAssistantState('speaking');
      this.rmsInterval = setInterval(() => {
        if (window.setAudioRms) {
          window.setAudioRms(0.35 + Math.random() * 0.45);
        }
      }, 100);
    };

    utterance.onend = () => {
      this.stopSpeech();
    };

    utterance.onerror = (e) => {
      console.warn('[TTS] Synthesis error:', e);
      this.stopSpeech();
    };

    try {
      this.synth.speak(utterance);
    } catch (err) {
      console.error('[TTS] speak() exception:', err);
      this.stopSpeech();
    }
  }

  async handleQuery(userText) {
    if (!userText || !userText.trim()) return;

    this.stopSpeech();
    this.addHistoryMessage('user', userText);
    this.setAssistantState('thinking');
    if (window.playSfx) window.playSfx('wake');
    if (this.actionBadge) this.actionBadge.style.display = 'none';
    this.headlineEl.textContent = `"${userText}"`;

    try {
      let res = null;
      if (window.pywebview && window.pywebview.api) {
        res = await window.pywebview.api.send_message(userText);
      } else {
        res = { text: `Acknowledged: "${userText}". All systems operational.`, action: null };
      }

      const replyText = (res && res.text) ? res.text : (res && res.reply ? res.reply : 'Command executed.');
      const actionName = res ? res.action : null;
      const steps = res ? (res.steps || []) : [];

      if (window.playSfx) window.playSfx('done');
      this.headlineEl.textContent = `"${replyText}"`;
      if (actionName && this.actionBadge) {
        const cleanName = actionName.replace(/_/g, ' ');
        this.actionBadge.textContent = cleanName.charAt(0).toUpperCase() + cleanName.slice(1);
        this.actionBadge.style.display = 'inline-flex';
      }
      this.addHistoryMessage('assistant', replyText, actionName, steps);
      this.speak(replyText);
    } catch (e) {
      console.error('[AetherUI] Query error:', e);
      if (window.playSfx) window.playSfx('error');
      this.setAssistantState('idle');
      this.headlineEl.textContent = `"${e.message || 'Execution error'}"`;
    }
  }

  async handleVision() {
    this.stopSpeech();
    this.headlineEl.textContent = '"Analyzing active screen..."';
    this.setAssistantState('thinking');

    try {
      let res = null;
      if (window.pywebview && window.pywebview.api) {
        res = await window.pywebview.api.scan_screen('Analyze what is on the screen right now and summarize key information.');
      } else {
        res = { text: 'Optical sensor offline in browser preview.', action: null };
      }

      const replyText = (res && res.text) ? res.text : 'Screen analysis complete.';
      this.headlineEl.textContent = `"${replyText}"`;
      if (this.actionBadge) {
        this.actionBadge.textContent = 'Screen scan';
        this.actionBadge.style.display = 'inline-flex';
      }
      this.addHistoryMessage('assistant', replyText, 'capture_screen');
      this.speak(replyText);
    } catch (e) {
      this.setAssistantState('idle');
      this.headlineEl.textContent = `"${e.message || 'Screen capture error'}"`;
    }
  }

  handleProactiveEvent(eventData) {
    if (!eventData || !eventData.text) return;

    const alertType = (eventData.type || 'info').toLowerCase();
    const priority = (eventData.priority || 'normal').toLowerCase();
    const text = eventData.text;

    console.log(`[AetherUI] Proactive alert (${alertType}/${priority}):`, text);

    if (this.proactiveBanner) {
      this.proactiveBanner.textContent = `${alertType.charAt(0).toUpperCase() + alertType.slice(1)} notification`;
      this.proactiveBanner.className = `proactive-banner ${alertType} ${priority}`;
      this.proactiveBanner.style.display = 'inline-flex';

      if (this.bannerTimeout) clearTimeout(this.bannerTimeout);
      this.bannerTimeout = setTimeout(() => {
        if (this.proactiveBanner) this.proactiveBanner.style.display = 'none';
      }, 14000);
    }

    this.headlineEl.textContent = `"${text}"`;
    this.addHistoryMessage('assistant', text, `proactive_${alertType}`);

    if (eventData.speak !== false) {
      this.speak(text);
    }
  }

  async openMemoryModal() {
    if (!this.memoryModal) return;
    this.memoryModal.style.display = 'flex';
    if (window.pywebview && window.pywebview.api && window.pywebview.api.get_memory_overview) {
      try {
        const res = await window.pywebview.api.get_memory_overview();
        const stats = res.stats || {};
        const facts = res.facts || [];

        if (this.memFactsCount) this.memFactsCount.textContent = stats.facts || 0;
        if (this.memConvsCount) this.memConvsCount.textContent = stats.conversations || 0;
        if (this.memFilesCount) this.memFilesCount.textContent = stats.indexed_files || 0;
        if (this.memChunksCount) this.memChunksCount.textContent = stats.indexed_chunks || 0;

        if (this.memoryFactsList) {
          this.memoryFactsList.replaceChildren();
          facts.forEach(f => {
            const fEl = document.createElement('div');
            fEl.className = 'form-control';
            fEl.style.fontSize = '12px';
            fEl.style.lineHeight = '1.4';
            fEl.innerHTML = `<span style="color: var(--accent-amber); font-weight: 500;">[${escapeHtml(f.category)}]</span> <span style="color: var(--text-primary);">${escapeHtml(f.content)}</span>`;
            this.memoryFactsList.appendChild(fEl);
          });
        }
      } catch (e) {
        console.warn('[AetherUI] Memory overview fetch error:', e);
      }
    }
  }

  async openEnvironmentModal() {
    if (!this.environmentModal) return;
    this.environmentModal.style.display = 'flex';
    if (window.pywebview && window.pywebview.api && window.pywebview.api.get_environment_snapshot) {
      try {
        const snap = await window.pywebview.api.get_environment_snapshot();
        const p = snap.peripherals || {};
        const iot = snap.iot || {};

        // Displays
        if (this.envDisplayInfo) {
          const dCount = p.display_count || 1;
          const dDesc = (p.displays && p.displays.length > 0) ? p.displays[0].resolution : '1920x1080';
          this.envDisplayInfo.textContent = `${dCount} Display active (${dDesc})`;
        }

        // Audio
        if (this.envAudioInfo && p.audio) {
          const isHp = p.audio.is_headphones;
          this.envAudioInfo.textContent = isHp ? `Headphones (${p.audio.device_name})` : `Speakers (${p.audio.device_name})`;
        }

        // Network / Wi-Fi
        if (this.envWifiSsid && p.network) {
          if (p.network.is_connected) {
            this.envWifiSsid.textContent = p.network.ssid;
            if (this.envWifiDetails) {
              this.envWifiDetails.textContent = `Signal: ${p.network.signal_percent}% // ${p.network.band} (${p.network.phy_rate_mbps || 0} Mbps)`;
            }
          } else {
            this.envWifiSsid.textContent = 'Disconnected';
          }
        }

        // Desk Lamp
        if (this.envLampStatus) {
          const lampOn = iot.desk_lamp !== false;
          this.envLampStatus.textContent = lampOn ? 'Illuminated (On)' : 'Off';
          this.envLampStatus.style.color = lampOn ? 'var(--accent-amber)' : 'var(--text-muted)';
        }

        // Ambient Light
        if (iot.ambient_light) {
          if (this.envLightColorLabel) {
            this.envLightColorLabel.textContent = `${iot.ambient_light.color_name || 'Amber'} (${iot.ambient_light.brightness || 85}%)`;
          }
          if (this.envBrightnessSlider) {
            this.envBrightnessSlider.value = iot.ambient_light.brightness || 85;
          }
        }
      } catch (e) {
        console.warn('[AetherUI] Environment snapshot fetch error:', e);
      }
    }
  }

  async handleChipAction(action) {
    if (action === 'briefing') {
      this.handleQuery('Give me a full situational briefing.');
    } else if (action === 'auto_task') {
      this.handleQuery('Find the research paper on neural networks I downloaded yesterday, extract the conclusions, and draft a summary in Notepad.');
    } else if (action === 'memory') {
      this.openMemoryModal();
    } else if (action === 'environment') {
      this.openEnvironmentModal();
    } else if (action === 'mobile_link') {
      this.openMobileLinkModal();
    } else if (action === 'scan_screen') {
      this.handleVision();
    } else if (action === 'diagnostics') {
      this.handleQuery('Run diagnostics and report system status.');
    } else if (action === 'vol_up') {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.trigger_quick_action('set_volume', { action: 'up' });
      }
      this.headlineEl.textContent = '"Master volume increased."';
    } else if (action === 'vol_down') {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.trigger_quick_action('set_volume', { action: 'down' });
      }
      this.headlineEl.textContent = '"Master volume decreased."';
    } else if (action === 'mute') {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.trigger_quick_action('set_volume', { action: 'mute' });
      }
      this.headlineEl.textContent = '"Audio muted / unmuted."';
    } else if (action === 'media') {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.trigger_quick_action('control_media', { command: 'toggle' });
      }
      this.headlineEl.textContent = '"Media playback toggled."';
    } else if (action === 'lock') {
      if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.trigger_quick_action('lock_workstation', {});
      }
      this.headlineEl.textContent = '"Workstation locked."';
    }
  }

  addHistoryMessage(sender, text, action = null, steps = []) {
    this.history.push({ sender, text, action, steps, time: new Date() });
    const item = document.createElement('div');
    item.className = `msg-item ${sender}`;

    const speaker = document.createElement('div');
    speaker.className = 'msg-speaker';
    speaker.textContent = sender === 'user' ? 'You' : (this.config.assistant_name || 'Aether');

    const bubble = document.createElement('div');
    bubble.className = 'msg-text';
    bubble.textContent = text;

    // Structured HUD Cards Formatter
    if (text.includes('\n') && (text.includes(': ') || text.includes(' - ') || text.includes(' | '))) {
      const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
      if (lines.length >= 2 && lines.some(l => l.includes(':'))) {
        const hudRows = document.createElement('div');
        hudRows.className = 'hud-rows';
        let structuredFound = false;

        lines.forEach((l, idx) => {
          if (l.includes(':')) {
            const colonIdx = l.indexOf(':');
            const k = l.substring(0, colonIdx).replace(/^[-*•\s]+/, '').trim();
            const v = l.substring(colonIdx + 1).trim();
            if (k && v && k.length < 32) {
              structuredFound = true;
              const row = document.createElement('div');
              row.className = 'hud-row';
              row.innerHTML = `
                <span class="hud-idx">${idx + 1 < 10 ? '0' + (idx + 1) : idx + 1}</span>
                <div class="hud-main">
                  <span class="hud-label">${escapeHtml(k)}</span>
                  <span class="hud-sub">${escapeHtml(v)}</span>
                </div>
                <span class="hud-tag gold">Data</span>
              `;
              hudRows.appendChild(row);
            }
          }
        });

        if (structuredFound) {
          bubble.replaceChildren(hudRows);
        }
      }
    }

    if (steps && steps.length > 0) {
      const stepsContainer = document.createElement('div');
      stepsContainer.className = 'workflow-steps-container';
      steps.forEach((st, idx) => {
        const stepEl = document.createElement('div');
        stepEl.className = 'workflow-step-item';
        stepEl.innerHTML = `<span class="step-num">${idx + 1}</span> <span>${escapeHtml(st)}</span>`;
        stepsContainer.appendChild(stepEl);
      });
      bubble.appendChild(stepsContainer);
    }

    if (action) {
      const act = document.createElement('div');
      act.className = 'action-badge';
      const cleanAction = action.replace(/_/g, ' ');
      act.textContent = cleanAction.charAt(0).toUpperCase() + cleanAction.slice(1);
      bubble.appendChild(act);
    }

    item.appendChild(speaker);
    item.appendChild(bubble);
    this.historyFeed.appendChild(item);
    this.historyFeed.scrollTop = this.historyFeed.scrollHeight;
  }

  updateTelemetry(telem) {
    if (!telem) return;
    this.latestTelemetry = telem;
    if (this.telemCpu) this.telemCpu.textContent = `${telem.cpu_percent}%`;
    if (this.telemRam) this.telemRam.textContent = `${telem.ram_used_gb} / ${telem.ram_total_gb} GB (${telem.ram_percent}%)`;
    if (this.telemBat) this.telemBat.textContent = `${telem.battery_percent}% (${telem.battery_time})`;
    if (this.telemUptime) this.telemUptime.textContent = telem.uptime || 'Active';
  }

  async openMobileLinkModal() {
    if (this.mobileLinkModal) {
      this.mobileLinkModal.style.display = 'flex';
      if (window.pywebview && window.pywebview.api && window.pywebview.api.get_bridge_info) {
        try {
          const info = await window.pywebview.api.get_bridge_info();
          this.renderBridgeInfo(info);
        } catch (e) {
          console.warn('[AetherUI] Bridge info fetch error:', e);
        }
      }
    }
  }

  renderBridgeInfo(info) {
    if (!info) return;
    if (this.bridgeHostDisplay) this.bridgeHostDisplay.textContent = `${info.ip}:${info.port}`;
    if (this.bridgeCodeDisplay) this.bridgeCodeDisplay.textContent = info.pairing_code || '------';
    if (this.bridgeQrImage && info.qr_data_url) {
      this.bridgeQrImage.src = info.qr_data_url;
    }
    if (this.bridgeFpDisplay && info.cert_fingerprint) {
      this.bridgeFpDisplay.textContent = info.cert_fingerprint.slice(0, 24) + '...';
      this.bridgeFpDisplay.title = info.cert_fingerprint;
    }
    if (this.bridgeTlsBadge) {
      this.bridgeTlsBadge.textContent = info.use_tls ? 'WSS / TLS' : 'WS Plain';
      this.bridgeTlsBadge.style.color = info.use_tls ? '#10b981' : 'var(--text-tertiary)';
    }
    this.updateMobileStatusUI(info.mobile_telemetry);
  }

  updateMobileStatusUI(telem) {
    if (!telem) return;
    if (telem.connected) {
      if (this.mobileModalBadge) {
        this.mobileModalBadge.textContent = 'Linked';
        this.mobileModalBadge.style.color = 'var(--status-positive)';
        this.mobileModalBadge.style.borderColor = 'var(--status-positive)';
      }
      if (this.mobileChipLabel) {
        const charging = telem.is_charging ? ' ⚡' : '';
        this.mobileChipLabel.textContent = `Mobile: ${telem.battery ?? '--'}%${charging}`;
      }
      if (this.mobileDeviceInfo) {
        const devName = escapeHtml(telem.device_name || 'Aether Android');
        const charging = telem.is_charging ? ' (Charging)' : '';
        const battery = escapeHtml(telem.battery ?? '--');
        const network = escapeHtml(telem.wifi_ssid || 'Wi-Fi');
        this.mobileDeviceInfo.innerHTML = `
          <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 4px;">${devName}</div>
          <div style="display: flex; gap: 12px; font-size: 11px; color: var(--text-secondary);">
            <span>Battery: <b style="color: var(--status-positive);">${battery}%${charging}</b></span>
            <span>Network: <b>${network}</b></span>
            <span>Status: <b style="color: var(--status-positive);">Active Synaptic Link</b></span>
          </div>
        `;
      }
    } else {
      if (this.mobileModalBadge) {
        this.mobileModalBadge.textContent = 'Disconnected';
        this.mobileModalBadge.style.color = 'var(--text-tertiary)';
        this.mobileModalBadge.style.borderColor = 'var(--border-hairline)';
      }
      if (this.mobileChipLabel) {
        this.mobileChipLabel.textContent = 'Mobile link';
      }
      if (this.mobileDeviceInfo) {
        this.mobileDeviceInfo.textContent = 'No mobile companion currently connected. Pair with the code above.';
      }
    }
  }

  onMobileTelemetry(telem) {
    this.updateMobileStatusUI(telem);
  }

  onMobileNotification(notif) {
    if (this.headlineEl) {
      this.headlineEl.textContent = `"[${notif.app_name || 'Mobile'}] ${notif.title}: ${notif.text}"`;
    }
    if (window.playSfx) window.playSfx('chime');
  }

  onMobileStatus(status) {
    this.updateMobileStatusUI(status);
  }
}

window.onTelemetryUpdate = function(telem) {
  if (window.aetherApp) {
    window.aetherApp.updateTelemetry(telem);
  }
};

window.addEventListener('DOMContentLoaded', () => {
  window.aetherApp = new AetherUI();
});
