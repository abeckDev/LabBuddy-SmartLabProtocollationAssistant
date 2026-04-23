/**
 * LabBuddy — Frontend application.
 * Handles WebSocket, mic capture, audio playback, transcript display, and field updates.
 * Supports Low Tech and Medium Tech Preview modes.
 */

// ── State ──────────────────────────────────────────────────────────────
let ws = null;
let audioContext = null;
let captureNode = null;
let playbackNode = null;
let mediaStream = null;
let cameraStream = null;
let sessionActive = false;
let isMuted = false;
let currentLang = 'de'; // 'de' or 'en'
let currentMode = 'low'; // 'low' or 'medium'
let currentConfigName = null; // selected demo config name
let currentConfig = null; // loaded config data from backend

// ── DOM Elements ───────────────────────────────────────────────────────
const startBtn = document.getElementById('start-btn');
const exportBtn = document.getElementById('export-btn');
const statusText = document.getElementById('status-text');
const voiceOrb = document.getElementById('voice-orb');
const connectionDot = document.getElementById('connection-status');
const transcriptContainer = document.getElementById('transcript-container');
const fieldsContainer = document.getElementById('fields-container');
const completionFill = null;
const completionText = null;
const downloadLinks = document.getElementById('download-links');
const muteBtn = document.getElementById('mute-btn');

let lastSessionId = null;
let lastExtractedFields = {};

// ── Config-driven fields (loaded from backend, with fallback defaults) ──
let REQUIRED_FIELDS = [
    'researcherName', 'experimentTitle', 'experimentType', 'experimentDate',
    'rawMaterials', 'procedureSteps', 'result'
];

let LIMS_SECTIONS = {
    header: ['researcherName', 'researcherId', 'projectName', 'projectCode', 'experimentTitle', 'experimentType', 'experimentDate', 'laboratory'],
    materials: ['rawMaterials', 'rawMaterialSource', 'sampleId', 'batchNumber', 'targetFormulation', 'equipment'],
    procedure: ['procedureSteps', 'duration', 'temperatureCelsius', 'humidityPercent'],
    measurements: ['phValue', 'viscosity', 'observations'],
    results: ['result', 'deviations', 'safetyNotes', 'nextSteps', 'comments'],
};

let FIELD_LABELS = {
    de: {
        researcherName: 'Forscher/in',
        researcherId: 'Mitarbeiter-ID',
        projectName: 'Projektname',
        projectCode: 'Projektcode',
        experimentTitle: 'Experimenttitel',
        experimentType: 'Experimenttyp',
        experimentDate: 'Datum',
        laboratory: 'Labor',
        equipment: 'Geräte',
        rawMaterials: 'Rohstoffe/Chemikalien',
        rawMaterialSource: 'Rohstoffquelle',
        sampleId: 'Proben-ID',
        batchNumber: 'Chargennummer',
        targetFormulation: 'Zielformulierung',
        procedureSteps: 'Durchführung',
        temperatureCelsius: 'Temperatur (°C)',
        humidityPercent: 'Luftfeuchtigkeit (%)',
        phValue: 'pH-Wert',
        viscosity: 'Viskosität',
        duration: 'Dauer',
        observations: 'Beobachtungen',
        result: 'Ergebnis',
        deviations: 'Abweichungen',
        safetyNotes: 'Sicherheitshinweise',
        nextSteps: 'Nächste Schritte',
        comments: 'Anmerkungen',
    },
    en: {
        researcherName: 'Researcher',
        researcherId: 'Employee ID',
        projectName: 'Project Name',
        projectCode: 'Project Code',
        experimentTitle: 'Experiment Title',
        experimentType: 'Experiment Type',
        experimentDate: 'Date',
        laboratory: 'Laboratory',
        equipment: 'Equipment',
        rawMaterials: 'Raw Materials',
        rawMaterialSource: 'Material Source',
        sampleId: 'Sample ID',
        batchNumber: 'Batch Number',
        targetFormulation: 'Target Formulation',
        procedureSteps: 'Procedure',
        temperatureCelsius: 'Temperature (°C)',
        humidityPercent: 'Humidity (%)',
        phValue: 'pH Value',
        viscosity: 'Viscosity',
        duration: 'Duration',
        observations: 'Observations',
        result: 'Result',
        deviations: 'Deviations',
        safetyNotes: 'Safety Notes',
        nextSteps: 'Next Steps',
        comments: 'Comments',
    },
};

// Bilingual UI strings
const UI_STRINGS = {
    de: {
        tagline: 'Smart Lab Protocol Assistant',
        welcome: 'Willkommen bei LabBuddy!',
        welcomeSub: 'Klicken Sie auf Start, um Ihr Versuchsprotokoll zu starten.',
        clickMic: 'Klicken Sie auf das Mikrofon, um zu beginnen',
        connecting: 'Verbindung wird hergestellt...',
        listening: 'Zuhören...',
        thinking: 'Verarbeitung...',
        speaking: 'Antwort...',
        sessionComplete: 'Protokoll abgeschlossen! ✅',
        sessionEnded: 'Sitzung beendet',
        connectionError: 'Verbindungsfehler',
        exportBtn: 'Export',
        exporting: 'Exportiert...',
        profileTitle: 'Versuchsprotokoll',
        you: 'Sie',
        transcript: 'Transkript (.txt)',
        audio: 'Aufnahme (.wav)',
        json: 'Felder (.json)',
        xlsx: 'Felder (.xlsx)',
    },
    en: {
        tagline: 'Smart Lab Protocol Assistant',
        welcome: 'Welcome to LabBuddy!',
        welcomeSub: 'Click Start to begin documenting your experiment.',
        clickMic: 'Click the microphone to start',
        connecting: 'Connecting...',
        listening: 'Listening...',
        thinking: 'Processing...',
        speaking: 'Responding...',
        sessionComplete: 'Protocol complete! ✅',
        sessionEnded: 'Session ended',
        connectionError: 'Connection error',
        exportBtn: 'Export',
        exporting: 'Exporting...',
        profileTitle: 'Experiment Protocol',
        you: 'You',
        transcript: 'Transcript (.txt)',
        audio: 'Recording (.wav)',
        json: 'Fields (.json)',
        xlsx: 'Fields (.xlsx)',
    },
}

// ── Language toggle ─────────────────────────────────────────────────────
const langDeBtn = document.getElementById('lang-de');
const langEnBtn = document.getElementById('lang-en');

function setLanguage(lang) {
    currentLang = lang;
    langDeBtn.classList.toggle('active', lang === 'de');
    langEnBtn.classList.toggle('active', lang === 'en');
    document.documentElement.lang = lang;
    applyUIStrings();
    initFieldCards();
}

function applyUIStrings() {
    const s = UI_STRINGS[currentLang];
    document.querySelector('.tagline').textContent = s.tagline;
    document.querySelector('.fields-header h2').textContent = s.profileTitle;
    // Update welcome message if visible
    const welcomeH2 = document.querySelector('.welcome-message h2');
    const welcomeP = document.querySelector('.welcome-message p');
    if (welcomeH2) welcomeH2.textContent = s.welcome;
    if (welcomeP) welcomeP.textContent = s.welcomeSub;
    // Update status text if not in session
    if (!sessionActive) statusText.textContent = s.clickMic;
    // Update export button text (if not exporting)
    if (!exportBtn.disabled || exportBtn.textContent.trim() === UI_STRINGS.de.exportBtn || exportBtn.textContent.trim() === UI_STRINGS.en.exportBtn) {
        exportBtn.innerHTML = `
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
            </svg>
            ${s.exportBtn}
        `;
    }
}

langDeBtn.addEventListener('click', () => setLanguage('de'));
langEnBtn.addEventListener('click', () => setLanguage('en'));

// ── Mode toggle ─────────────────────────────────────────────────────────
const modeLowBtn = document.getElementById('mode-low');
const modeMediumBtn = document.getElementById('mode-medium');

function setMode(mode) {
    currentMode = mode;
    modeLowBtn.classList.toggle('active', mode === 'low');
    modeMediumBtn.classList.toggle('active', mode === 'medium');
    applyModeUI();
    if (mode === 'medium') {
        showMediumTechToast();
    }
}

function applyModeUI() {
    const isMedium = currentMode === 'medium';
    document.querySelectorAll('.medium-tech-panel').forEach(el => {
        el.style.display = isMedium ? '' : 'none';
    });
    if (isMedium) {
        startCamera();
    } else {
        stopCamera();
    }
}

function showMediumTechToast() {
    const toast = document.getElementById('medium-tech-toast');
    toast.style.display = 'flex';
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => {
            toast.style.display = 'none';
            toast.style.opacity = '1';
        }, 600);
    }, 3500);
}

modeLowBtn.addEventListener('click', () => setMode('low'));
modeMediumBtn.addEventListener('click', () => setMode('medium'));

// ── Camera (Medium Tech) ───────────────────────────────────────────────
const cameraVideo = document.getElementById('camera-video');
const cameraCanvas = document.getElementById('camera-canvas');
const captureBtn = document.getElementById('capture-btn');

async function startCamera() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
        cameraVideo.srcObject = cameraStream;
        captureBtn.disabled = false;
    } catch (err) {
        console.warn('Camera not available:', err.message);
        captureBtn.disabled = true;
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(t => t.stop());
        cameraStream = null;
    }
    cameraVideo.srcObject = null;
    captureBtn.disabled = true;
}

captureBtn.addEventListener('click', () => {
    if (!cameraStream || !cameraVideo.videoWidth) return;
    cameraCanvas.width = cameraVideo.videoWidth;
    cameraCanvas.height = cameraVideo.videoHeight;
    cameraCanvas.getContext('2d').drawImage(cameraVideo, 0, 0);
    const imageData = cameraCanvas.toDataURL('image/jpeg', 0.7);
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'vision_capture', image: imageData }));
        addSystemMessage('📷 Capturing frame — Vision Agent analysing lab setup...');
    }
});

// ── LIMS Preview (Medium Tech) ──────────────────────────────────────────
const limsSubmitBtn = document.getElementById('lims-submit-btn');
const limsPanelToggle = document.getElementById('lims-panel-toggle');
const limsPanelBody = document.getElementById('lims-panel-body');
let limsPanelOpen = true;

limsPanelToggle.addEventListener('click', () => {
    limsPanelOpen = !limsPanelOpen;
    limsPanelBody.style.display = limsPanelOpen ? '' : 'none';
    document.querySelector('.lims-chevron').textContent = limsPanelOpen ? '▼' : '▶';
});

function updateLimsPreview(fields) {
    const labels = FIELD_LABELS[currentLang];
    let filledCount = 0;

    for (const [sectionId, fieldKeys] of Object.entries(LIMS_SECTIONS)) {
        const container = document.getElementById('lims-' + sectionId + '-fields');
        if (!container) continue;
        container.innerHTML = '';
        for (const key of fieldKeys) {
            const value = fields[key];
            if (value !== null && value !== undefined && value !== '') {
                filledCount++;
                const row = document.createElement('div');
                row.className = 'lims-field-row';
                row.innerHTML = '<span class="lims-field-key">' + escapeHtml(labels[key] || key) + '</span><span class="lims-field-val">' + escapeHtml(String(value)) + '</span>';
                container.appendChild(row);
            } else {
                const row = document.createElement('div');
                row.className = 'lims-field-row empty';
                row.innerHTML = '<span class="lims-field-key">' + escapeHtml(labels[key] || key) + '</span><span class="lims-field-val lims-empty">—</span>';
                container.appendChild(row);
            }
        }
    }
    limsSubmitBtn.disabled = filledCount < REQUIRED_FIELDS.length;
}

limsSubmitBtn.addEventListener('click', showLimsConfirmDialog);

function showLimsConfirmDialog() {
    const labels = FIELD_LABELS[currentLang];
    const overlay = document.getElementById('lims-confirm-overlay');
    const confirmFields = document.getElementById('lims-confirm-fields');
    confirmFields.innerHTML = '';
    for (const [key, value] of Object.entries(lastExtractedFields)) {
        if (value === null || value === '' || value === undefined) continue;
        const row = document.createElement('div');
        row.className = 'lims-confirm-row';
        row.innerHTML = '<b>' + escapeHtml(labels[key] || key) + ':</b> ' + escapeHtml(String(value));
        confirmFields.appendChild(row);
    }
    overlay.style.display = 'flex';
}

document.getElementById('lims-confirm-yes').addEventListener('click', async () => {
    document.getElementById('lims-confirm-overlay').style.display = 'none';
    limsSubmitBtn.disabled = true;
    limsSubmitBtn.textContent = 'Submitting...';
    try {
        const resp = await fetch('/api/lims/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...lastExtractedFields, _config_name: currentConfigName }),
        });
        const data = await resp.json();
        if (data.status === 'success') {
            addSystemMessage('✅ ' + data.message);
            limsSubmitBtn.textContent = '✅ Submitted: ' + data.protocol_id;
        } else {
            addSystemMessage('❌ LIMS submission failed.');
            limsSubmitBtn.disabled = false;
            limsSubmitBtn.textContent = 'Submit to LIMS';
        }
    } catch (err) {
        addSystemMessage('❌ LIMS submission error: ' + err.message);
        limsSubmitBtn.disabled = false;
        limsSubmitBtn.textContent = 'Submit to LIMS';
    }
});

document.getElementById('lims-confirm-no').addEventListener('click', () => {
    document.getElementById('lims-confirm-overlay').style.display = 'none';
});

// ── Config selector ────────────────────────────────────────────────────
const configSelect = document.getElementById('config-select');
let limsName = 'Albert'; // current LIMS name

async function loadAvailableConfigs() {
    try {
        const resp = await fetch('/api/configs');
        const data = await resp.json();
        const configs = data.configs || [];
        const defaultName = data.default || '';
        configSelect.innerHTML = '';
        for (const cfg of configs) {
            const opt = document.createElement('option');
            opt.value = cfg.name;
            const label = cfg.profile_name[currentLang] || cfg.profile_name['en'] || cfg.name;
            opt.textContent = label;
            if (cfg.name === defaultName) opt.selected = true;
            configSelect.appendChild(opt);
        }
        // Load the default config details
        const selected = configSelect.value || defaultName || (configs[0] && configs[0].name);
        if (selected) await applyConfig(selected);
    } catch (err) {
        console.warn('Failed to load configs:', err);
    }
}

async function applyConfig(configName) {
    try {
        const resp = await fetch(`/api/configs/${encodeURIComponent(configName)}`);
        const cfg = await resp.json();
        if (cfg.error) { console.warn(cfg.error); return; }

        currentConfigName = configName;
        currentConfig = cfg;

        // Update config-driven state
        REQUIRED_FIELDS = cfg.required_fields || REQUIRED_FIELDS;
        LIMS_SECTIONS = cfg.lims_sections || LIMS_SECTIONS;
        if (cfg.field_labels) FIELD_LABELS = cfg.field_labels;
        limsName = (cfg.lims && cfg.lims.name) || 'Albert';

        // Update LIMS panel title and confirmation dialog
        const limsPanelTitle = document.getElementById('lims-panel-title');
        if (limsPanelTitle) limsPanelTitle.textContent = `📊 LIMS Preview (${limsName})`;
        const limsConfirmName = document.getElementById('lims-confirm-name');
        if (limsConfirmName) limsConfirmName.textContent = limsName;

        // Re-render fields sidebar
        initFieldCards();
    } catch (err) {
        console.warn('Failed to apply config:', err);
    }
}

configSelect.addEventListener('change', async () => {
    if (sessionActive) return; // Don't switch mid-session
    await applyConfig(configSelect.value);
});

// ── Settings panel ─────────────────────────────────────────────────────
const SETTINGS_KEYS = {
    endpoint: 'labbuddy_azure_endpoint',
    openaiEndpoint: 'labbuddy_openai_endpoint',
    openaiDeployment: 'labbuddy_openai_deployment',
};
// API key is stored only in sessionStorage (not persisted across browser sessions)
const API_KEY_SESSION_KEY = 'labbuddy_azure_api_key';

function loadSettingsFromStorage() {
    return {
        endpoint: localStorage.getItem(SETTINGS_KEYS.endpoint) || '',
        // Read API key from sessionStorage only (clears when browser tab/session ends)
        apiKey: sessionStorage.getItem(API_KEY_SESSION_KEY) || '',
        openaiEndpoint: localStorage.getItem(SETTINGS_KEYS.openaiEndpoint) || '',
        openaiDeployment: localStorage.getItem(SETTINGS_KEYS.openaiDeployment) || '',
    };
}

function saveSettingsToStorage(s) {
    if (s.endpoint) localStorage.setItem(SETTINGS_KEYS.endpoint, s.endpoint);
    else localStorage.removeItem(SETTINGS_KEYS.endpoint);
    // API key stored in sessionStorage only — not persisted to localStorage
    if (s.apiKey) sessionStorage.setItem(API_KEY_SESSION_KEY, s.apiKey);
    else sessionStorage.removeItem(API_KEY_SESSION_KEY);
    if (s.openaiEndpoint) localStorage.setItem(SETTINGS_KEYS.openaiEndpoint, s.openaiEndpoint);
    else localStorage.removeItem(SETTINGS_KEYS.openaiEndpoint);
    if (s.openaiDeployment) localStorage.setItem(SETTINGS_KEYS.openaiDeployment, s.openaiDeployment);
    else localStorage.removeItem(SETTINGS_KEYS.openaiDeployment);
}

function clearSettingsFromStorage() {
    Object.values(SETTINGS_KEYS).forEach(k => localStorage.removeItem(k));
    sessionStorage.removeItem(API_KEY_SESSION_KEY);
}

function openSettingsModal(showBanner) {
    const s = loadSettingsFromStorage();
    document.getElementById('settings-endpoint').value = s.endpoint;
    document.getElementById('settings-api-key').value = s.apiKey;
    document.getElementById('settings-openai-endpoint').value = s.openaiEndpoint;
    document.getElementById('settings-openai-deployment').value = s.openaiDeployment;
    const banner = document.getElementById('settings-setup-banner');
    if (banner) banner.style.display = showBanner ? '' : 'none';
    document.getElementById('settings-overlay').style.display = 'flex';
}

function closeSettingsModal() {
    document.getElementById('settings-overlay').style.display = 'none';
}

document.getElementById('settings-btn').addEventListener('click', () => openSettingsModal(false));
document.getElementById('settings-close').addEventListener('click', closeSettingsModal);
document.getElementById('settings-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('settings-overlay')) closeSettingsModal();
});

document.getElementById('settings-save').addEventListener('click', () => {
    saveSettingsToStorage({
        endpoint: document.getElementById('settings-endpoint').value.trim(),
        apiKey: document.getElementById('settings-api-key').value.trim(),
        openaiEndpoint: document.getElementById('settings-openai-endpoint').value.trim(),
        openaiDeployment: document.getElementById('settings-openai-deployment').value.trim(),
    });
    closeSettingsModal();
    checkSetupStatus();
});

document.getElementById('settings-clear').addEventListener('click', () => {
    clearSettingsFromStorage();
    document.getElementById('settings-endpoint').value = '';
    document.getElementById('settings-api-key').value = '';
    document.getElementById('settings-openai-endpoint').value = '';
    document.getElementById('settings-openai-deployment').value = '';
    checkSetupStatus();
});

const setupBanner = document.getElementById('setup-required-banner');
const setupLink = document.getElementById('setup-required-link');
if (setupLink) setupLink.addEventListener('click', () => openSettingsModal(true));

async function checkSetupStatus() {
    try {
        const resp = await fetch('/api/setup-status');
        const data = await resp.json();
        const localSettings = loadSettingsFromStorage();
        // Show banner only when backend has no endpoint AND nothing saved locally
        const needsSetup = !data.configured && !localSettings.endpoint;
        if (setupBanner) setupBanner.style.display = needsSetup ? '' : 'none';
    } catch (err) {
        // ignore
    }
}

// ── Init ───────────────────────────────────────────────────────────────
checkSetupStatus();
loadAvailableConfigs();
initFieldCards();
startBtn.addEventListener('click', toggleSession);
exportBtn.addEventListener('click', exportSession);
muteBtn.addEventListener('click', toggleMute);

function toggleMute() {
    isMuted = !isMuted;
    muteBtn.classList.toggle('muted', isMuted);
    document.getElementById('mute-icon-on').style.display = isMuted ? 'none' : 'block';
    document.getElementById('mute-icon-off').style.display = isMuted ? 'block' : 'none';
    muteBtn.title = isMuted
        ? (currentLang === 'de' ? 'Mikrofon einschalten' : 'Unmute microphone')
        : (currentLang === 'de' ? 'Mikrofon stummschalten' : 'Mute microphone');
    // Mute/unmute the mic track
    if (mediaStream) {
        mediaStream.getAudioTracks().forEach(t => t.enabled = !isMuted);
    }
}

function initFieldCards() {
    const labels = FIELD_LABELS[currentLang];
    fieldsContainer.innerHTML = '';
    for (const [key, label] of Object.entries(labels)) {
        const card = document.createElement('div');
        card.className = 'field-card' + (REQUIRED_FIELDS.includes(key) ? ' required' : '');
        card.id = `field-${key}`;
        card.innerHTML = `
            <div class="field-name">${label}${REQUIRED_FIELDS.includes(key) ? ' *' : ''}</div>
            <div class="field-value empty">—</div>
        `;
        fieldsContainer.appendChild(card);
    }
}

// ── Session toggle ─────────────────────────────────────────────────────
async function toggleSession() {
    if (sessionActive) {
        stopSession();
    } else {
        await startSession();
    }
}

async function startSession() {
    try {
        // Set up audio context
        audioContext = new AudioContext({ sampleRate: 48000 });

        // Load audio worklets
        await audioContext.audioWorklet.addModule('audio-capture-worklet.js');
        await audioContext.audioWorklet.addModule('audio-playback-worklet.js');

        // Get microphone
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: false, noiseSuppression: false, sampleRate: 48000 }
        });

        // Set up capture pipeline: mic → worklet → WebSocket
        const source = audioContext.createMediaStreamSource(mediaStream);
        captureNode = new AudioWorkletNode(audioContext, 'audio-capture-processor');
        captureNode.port.onmessage = (e) => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                const b64 = arrayBufferToBase64(e.data);
                ws.send(JSON.stringify({ type: 'audio_chunk', data: b64 }));
            }
        };
        source.connect(captureNode);
        // Don't connect to destination — capture only

        // Set up playback pipeline: WebSocket → worklet → speakers
        playbackNode = new AudioWorkletNode(audioContext, 'audio-playback-processor');
        playbackNode.connect(audioContext.destination);

        // Connect WebSocket
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const clientId = crypto.randomUUID().slice(0, 8);
        ws = new WebSocket(`${protocol}//${location.host}/ws/${clientId}`);

        ws.onopen = () => {
            connectionDot.className = 'status-dot online';
            const localSettings = loadSettingsFromStorage();
            ws.send(JSON.stringify({
                type: 'start_session',
                language: currentLang,
                mode: currentMode,
                config_name: currentConfigName,
                // User-provided credentials (passed when env vars are not set)
                ...(localSettings.endpoint && { endpoint: localSettings.endpoint }),
                ...(localSettings.apiKey && { api_key: localSettings.apiKey }),
                ...(localSettings.openaiEndpoint && { openai_endpoint: localSettings.openaiEndpoint }),
                ...(localSettings.openaiDeployment && { openai_deployment: localSettings.openaiDeployment }),
            }));
        };

        ws.onmessage = (e) => handleMessage(JSON.parse(e.data));

        ws.onclose = () => {
            connectionDot.className = 'status-dot offline';
            if (sessionActive) stopSession();
        };

        ws.onerror = (err) => {
            console.error('WebSocket error:', err);
            setStatus(UI_STRINGS[currentLang].connectionError, 'idle');
        };

        sessionActive = true;
        isMuted = false;
        muteBtn.style.display = 'flex';
        muteBtn.classList.remove('muted');
        document.getElementById('mute-icon-on').style.display = 'block';
        document.getElementById('mute-icon-off').style.display = 'none';
        startBtn.textContent = currentLang === 'de' ? 'Beenden' : 'End';
        startBtn.title = currentLang === 'de' ? 'Gespräch beenden' : 'End conversation';
        // Disable language switch during session
        langDeBtn.disabled = true;
        langEnBtn.disabled = true;
        modeLowBtn.disabled = true;
        modeMediumBtn.disabled = true;
        configSelect.disabled = true;
        // Clear welcome message
        transcriptContainer.innerHTML = '';
        setStatus(UI_STRINGS[currentLang].connecting, 'idle');
        exportBtn.disabled = true;
        downloadLinks.style.display = 'none';

        // Reset agent activity feed for medium mode
        if (currentMode === 'medium') {
            clearAgentFeed();
        }

    } catch (err) {
        console.error('Failed to start session:', err);
        setStatus(`Fehler: ${err.message}`, 'idle');
        stopSession();
    }
}

function stopSession() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'stop_session' }));
        ws.close();
    }
    ws = null;

    if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop());
        mediaStream = null;
    }

    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }

    captureNode = null;
    playbackNode = null;
    sessionActive = false;
    isMuted = false;
    muteBtn.style.display = 'none';
    startBtn.textContent = 'Start';
    startBtn.title = currentLang === 'de' ? 'Gespräch starten' : 'Start conversation';
    langDeBtn.disabled = false;
    langEnBtn.disabled = false;
    modeLowBtn.disabled = false;
    modeMediumBtn.disabled = false;
    configSelect.disabled = false;
    connectionDot.className = 'status-dot offline';
    setStatus(UI_STRINGS[currentLang].sessionEnded, 'idle');
    if (lastSessionId) exportBtn.disabled = false;
}

// ── WebSocket message handler ──────────────────────────────────────────
function handleMessage(msg) {
    switch (msg.type) {
        case 'session_started':
            setStatus('Zuhören...', 'listening');
            if (msg.sessionId) lastSessionId = msg.sessionId;
            break;

        case 'status': {
            const s = UI_STRINGS[currentLang];
            const stateLabels = {
                listening: s.listening,
                thinking: s.thinking,
                speaking: s.speaking,
            };
            setStatus(stateLabels[msg.state] || msg.state, msg.state);
            break;
        }

        case 'transcript':
            updateTranscript(msg.role, msg.text, msg.isFinal);
            break;

        case 'audio_data':
            playAudio(msg.data);
            break;

        case 'stop_playback':
            if (playbackNode) {
                playbackNode.port.postMessage('clear');
            }
            break;

        case 'fields_update':
            updateFields(msg.fields, msg.completion, msg.missingRequired);
            break;

        case 'session_complete':
            setStatus(UI_STRINGS[currentLang].sessionComplete, 'idle');
            break;

        case 'export_ready':
            showDownloadLinks(msg.files);
            break;

        case 'session_stopped':
            setStatus(UI_STRINGS[currentLang].sessionEnded, 'idle');
            if (msg.sessionId) lastSessionId = msg.sessionId;
            exportBtn.disabled = false;
            break;

        case 'error':
            console.error('Server error:', msg.message);
            setStatus(`${currentLang === 'de' ? 'Fehler' : 'Error'}: ${msg.message}`, 'idle');
            break;

        // ── Medium Tech message types ─────────────────────────────────
        case 'sop_suggestion':
            if (currentMode === 'medium') showSopCard(msg.data);
            break;

        case 'material_lookup':
            if (currentMode === 'medium') showMaterialCard(msg.data);
            break;

        case 'agent_activity':
            if (currentMode === 'medium') addAgentActivity(msg.icon, msg.agent, msg.message);
            break;

        case 'vision_result':
            if (currentMode === 'medium') showVisionResult(msg.text);
            break;
    }
}

// ── Audio playback ─────────────────────────────────────────────────────
function playAudio(base64Data) {
    if (!playbackNode) return;
    const bytes = base64ToArrayBuffer(base64Data);
    playbackNode.port.postMessage(bytes, [bytes]);
}

// ── Transcript display ─────────────────────────────────────────────────
let currentStreamingEl = null;
let currentStreamingRole = null;

function updateTranscript(role, text, isFinal) {
    // If a different role is speaking, finalize the previous streaming bubble first
    if (currentStreamingEl && currentStreamingRole !== role) {
        currentStreamingEl.classList.remove('streaming');
        currentStreamingEl = null;
        currentStreamingRole = null;
    }

    if (!isFinal) {
        if (currentStreamingRole !== role || !currentStreamingEl) {
            currentStreamingEl = createMessageBubble(role, text, true);
            currentStreamingRole = role;
        } else {
            currentStreamingEl.querySelector('.message-text').textContent = text;
        }
    } else {
        if (currentStreamingEl && currentStreamingRole === role) {
            currentStreamingEl.querySelector('.message-text').textContent = text;
            currentStreamingEl.classList.remove('streaming');
            currentStreamingEl = null;
            currentStreamingRole = null;
        } else {
            createMessageBubble(role, text, false);
        }
    }

    // Auto-scroll
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
}

function createMessageBubble(role, text, isStreaming) {
    const div = document.createElement('div');
    div.className = `message ${role}${isStreaming ? ' streaming' : ''}`;
    if (role === 'assistant') {
        div.innerHTML = `
            <div class="bubble-content">
                <div class="message-role">LabBuddy</div>
                <div class="message-text">${escapeHtml(text)}</div>
            </div>
        `;
    } else {
        div.innerHTML = `
            <div class="message-role">${UI_STRINGS[currentLang].you}</div>
            <div class="message-text">${escapeHtml(text)}</div>
        `;
    }
    transcriptContainer.appendChild(div);
    return div;
}

function addSystemMessage(text) {
    const div = document.createElement('div');
    div.className = 'message system-msg';
    div.innerHTML = '<div class="message-text">' + escapeHtml(text) + '</div>';
    transcriptContainer.appendChild(div);
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
}

// ── SOP suggestion card ────────────────────────────────────────────────
function showSopCard(data) {
    const div = document.createElement('div');
    div.className = 'message sop-card';
    div.innerHTML =
        '<div class="card-icon">📋</div>' +
        '<div class="card-body">' +
            '<div class="card-label">Related SOP found <span class="preview-badge">PREVIEW</span></div>' +
            '<div class="card-title">' + escapeHtml(data.sop_id) + ' — ' + escapeHtml(data.title) + '</div>' +
            '<div class="card-detail">' + escapeHtml(data.description) + '</div>' +
            '<div class="card-meta">v' + escapeHtml(data.version) + ' · ' + escapeHtml(data.department) + '</div>' +
        '</div>';
    transcriptContainer.appendChild(div);
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
}

// ── Material lookup card ───────────────────────────────────────────────
function showMaterialCard(data) {
    const div = document.createElement('div');
    div.className = 'message material-card';
    div.innerHTML =
        '<div class="card-icon">📦</div>' +
        '<div class="card-body">' +
            '<div class="card-label">Material found in RMH <span class="preview-badge">PREVIEW</span></div>' +
            '<div class="card-title">' + escapeHtml(data.name) + ', Lot# ' + escapeHtml(data.lot) + '</div>' +
            '<div class="card-detail">Supplier: ' + escapeHtml(data.supplier) + ' · Grade: ' + escapeHtml(data.grade) + '</div>' +
            '<div class="card-meta">' + escapeHtml(data.spec_status) + ' · TDS/SDS: ' + escapeHtml(data.tds_sds) + ' · ' + escapeHtml(data.location) + '</div>' +
        '</div>';
    transcriptContainer.appendChild(div);
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
}

// ── Vision result card ─────────────────────────────────────────────────
function showVisionResult(text) {
    const div = document.createElement('div');
    div.className = 'message vision-card';
    div.innerHTML =
        '<div class="card-icon">👁️</div>' +
        '<div class="card-body">' +
            '<div class="card-label">Vision Analysis <span class="preview-badge">PREVIEW</span></div>' +
            '<div class="card-title">' + escapeHtml(text) + '</div>' +
        '</div>';
    transcriptContainer.appendChild(div);
    transcriptContainer.scrollTop = transcriptContainer.scrollHeight;
}

// ── Agent activity feed ────────────────────────────────────────────────
const agentFeed = document.getElementById('agent-activity-feed');

function clearAgentFeed() {
    agentFeed.innerHTML = '<div class="agent-idle">Waiting for session activity...</div>';
}

function addAgentActivity(icon, agent, message) {
    const idle = agentFeed.querySelector('.agent-idle');
    if (idle) idle.remove();
    const line = document.createElement('div');
    line.className = 'agent-line';
    line.innerHTML = '<span class="agent-icon">' + escapeHtml(icon) + '</span><span class="agent-name">' + escapeHtml(agent) + ':</span> ' + escapeHtml(message);
    agentFeed.appendChild(line);
    agentFeed.scrollTop = agentFeed.scrollHeight;
    // Keep only last 20 lines
    const lines = agentFeed.querySelectorAll('.agent-line');
    if (lines.length > 20) lines[0].remove();
}

// ── Fields display ─────────────────────────────────────────────────────
function updateFields(fields, completion, missingRequired) {
    lastExtractedFields = fields;

    for (const [key, value] of Object.entries(fields)) {
        const card = document.getElementById(`field-${key}`);
        if (!card) continue;

        const valueEl = card.querySelector('.field-value');
        if (value !== null && value !== '' && value !== undefined) {
            valueEl.textContent = String(value);
            valueEl.classList.remove('empty');
            card.classList.add('filled');
        }
    }

    // Update LIMS preview in Medium Tech mode
    if (currentMode === 'medium') {
        updateLimsPreview(fields);
    }
}

// ── Export ──────────────────────────────────────────────────────────────
function exportSession() {
    if (!lastSessionId) return;
    exportBtn.disabled = true;
    exportBtn.textContent = UI_STRINGS[currentLang].exporting;
    fetch(`/api/export/${lastSessionId}`)
        .then(res => res.json())
        .then(data => {
            if (data.type === 'export_ready') {
                showDownloadLinks(data.files);
            } else {
                console.error('Export error:', data.message);
                exportBtn.disabled = false;
                exportBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                        <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
                    </svg>
                    Export
                `;
            }
        })
        .catch(err => {
            console.error('Export fetch error:', err);
            exportBtn.disabled = false;
        });
}

function showDownloadLinks(files) {
    exportBtn.disabled = false;
    exportBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
        </svg>
        Export
    `;

    const icons = {
        transcript: '📄',
        audio: '🔊',
        json: '📋',
        xlsx: '📊',
    };
    const s = UI_STRINGS[currentLang];
    const labels = {
        transcript: s.transcript,
        audio: s.audio,
        json: s.json,
        xlsx: s.xlsx,
    };

    downloadLinks.innerHTML = '';
    for (const [key, url] of Object.entries(files)) {
        const a = document.createElement('a');
        a.href = url;
        a.download = '';
        a.className = 'download-link';
        a.innerHTML = `${icons[key] || '📁'} ${labels[key] || key}`;
        downloadLinks.appendChild(a);
    }
    downloadLinks.style.display = 'flex';
}

// ── UI helpers ─────────────────────────────────────────────────────────
const avatarContainer = document.getElementById('avatar-container');

function setStatus(text, state) {
    statusText.textContent = text;
    voiceOrb.className = `voice-orb ${state || 'idle'}`;
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

function base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}
