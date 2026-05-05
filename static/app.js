/* =========================================================
   app.js — Creative Campaign Agent
   ========================================================= */

// ── Brand Voice Options ──────────────────────────────────
const VOICE_OPTIONS = [
    { value: "Authentic",    label: "Authentic",    color: "#4f7bff" },
    { value: "Refreshing",   label: "Refreshing",   color: "#2dd4a0" },
    { value: "Youthful",     label: "Youthful",     color: "#f5a623" },
    { value: "Fun",          label: "Fun",           color: "#ff6b6b" },
    { value: "Natural",      label: "Natural",       color: "#6bcb77" },
    { value: "Bold",         label: "Bold",          color: "#c77dff" },
    { value: "Luxurious",    label: "Luxurious",     color: "#ffd700" },
    { value: "Minimalist",   label: "Minimalist",    color: "#8b92a5" },
    { value: "Playful",      label: "Playful",       color: "#ff9f1c" },
    { value: "Sophisticated",label: "Sophisticated", color: "#b8c0cc" },
    { value: "Energetic",    label: "Energetic",     color: "#ff4d6d" },
    { value: "Trustworthy",  label: "Trustworthy",   color: "#4361ee" },
    { value: "Warm",         label: "Warm",          color: "#e07a5f" },
    { value: "Inspiring",    label: "Inspiring",     color: "#81b29a" },
    { value: "Cultural",     label: "Cultural",      color: "#f2cc8f" },
];

// ── State ─────────────────────────────────────────────────
const selectedVoices = new Set();

// ── DOM refs ──────────────────────────────────────────────
const form           = document.getElementById('campaignForm');
const generateBtn    = document.getElementById('generateBtn');
const outputCard     = document.getElementById('outputCard');
const outputIdle     = document.getElementById('outputIdle');
const outputActive   = document.getElementById('outputActive');
const stepsList      = document.getElementById('stepsList');
const narrativeBlock = document.getElementById('narrativeBlock');
const narrativeText  = document.getElementById('narrativeText');
const errorBlock     = document.getElementById('errorBlock');
const errorText      = document.getElementById('errorText');
const copyBtn        = document.getElementById('copyBtn');

const msContainer  = document.getElementById('brandVoiceSelect');
const msTrigger    = document.getElementById('brandVoiceTrigger');
const msTags       = document.getElementById('brandVoiceTags');
const msDropdown   = document.getElementById('brandVoiceDropdown');
const voiceSearch  = document.getElementById('voiceSearch');
const voiceList    = document.getElementById('voiceList');
const brandVoiceHidden = document.getElementById('brand_voice');

// ── Build Multiselect ─────────────────────────────────────
function buildDropdownList(filter = '') {
    voiceList.innerHTML = '';
    const lower = filter.toLowerCase();
    let visible = 0;

    VOICE_OPTIONS.forEach(opt => {
        if (lower && !opt.label.toLowerCase().includes(lower)) return;
        visible++;

        const li = document.createElement('li');
        li.dataset.value = opt.value;
        if (selectedVoices.has(opt.value)) li.classList.add('selected');

        li.innerHTML = `
            <div class="option-check">
                <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                    <path d="M1 4l3 3 5-6" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            </div>
            <div class="option-dot" style="background:${opt.color}"></div>
            <span>${opt.label}</span>
        `;

        li.addEventListener('click', () => toggleVoice(opt.value, li));
        voiceList.appendChild(li);
    });

    if (visible === 0) {
        const no = document.createElement('div');
        no.className = 'no-results';
        no.textContent = 'No tones found';
        voiceList.appendChild(no);
    }
}

function toggleVoice(value, liEl) {
    if (selectedVoices.has(value)) {
        selectedVoices.delete(value);
        liEl.classList.remove('selected');
    } else {
        selectedVoices.add(value);
        liEl.classList.add('selected');
    }
    renderTags();
    syncHiddenInput();
}

function renderTags() {
    msTags.innerHTML = '';
    if (selectedVoices.size === 0) {
        msTags.innerHTML = '<span class="multiselect-placeholder">Select brand tones...</span>';
        return;
    }
    selectedVoices.forEach(val => {
        const opt = VOICE_OPTIONS.find(o => o.value === val);
        if (!opt) return;
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.innerHTML = `
            ${opt.label}
            <span class="tag-remove" data-value="${val}" tabindex="-1">×</span>
        `;
        tag.querySelector('.tag-remove').addEventListener('click', (e) => {
            e.stopPropagation();
            selectedVoices.delete(val);
            renderTags();
            syncHiddenInput();
            // update list item
            const li = voiceList.querySelector(`[data-value="${val}"]`);
            if (li) li.classList.remove('selected');
        });
        msTags.appendChild(tag);
    });
}

function syncHiddenInput() {
    brandVoiceHidden.value = [...selectedVoices].join(', ');
}

// Open / close
function openDropdown() {
    msContainer.classList.add('open');
    msTrigger.setAttribute('aria-expanded', 'true');
    voiceSearch.focus();
}
function closeDropdown() {
    msContainer.classList.remove('open');
    msTrigger.setAttribute('aria-expanded', 'false');
    voiceSearch.value = '';
    buildDropdownList('');
}

msTrigger.addEventListener('click', () => {
    msContainer.classList.contains('open') ? closeDropdown() : openDropdown();
});
msTrigger.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openDropdown(); }
    if (e.key === 'Escape') closeDropdown();
});

voiceSearch.addEventListener('input', () => buildDropdownList(voiceSearch.value));

document.addEventListener('click', (e) => {
    if (!msContainer.contains(e.target)) closeDropdown();
});

// Init
buildDropdownList();

// ── Validation ────────────────────────────────────────────
function setError(fieldId, msg) {
    const el = document.getElementById(fieldId);
    const err = document.getElementById('err_' + fieldId);
    if (el) el.classList.toggle('is-error', !!msg);
    if (err) err.textContent = msg || '';
}

function validateForm(data) {
    let valid = true;
    if (!data.product_name.trim()) {
        setError('product_name', 'Product name is required');
        valid = false;
    } else { setError('product_name', ''); }

    if (!data.product_desc.trim()) {
        setError('product_desc', 'Product description is required');
        valid = false;
    } else { setError('product_desc', ''); }

    if (!data.target_audience.trim()) {
        setError('target_audience', 'Target audience is required');
        valid = false;
    } else { setError('target_audience', ''); }

    return valid;
}

// ── Output helpers ────────────────────────────────────────
function showOutput() {
    outputIdle.style.display = 'none';
    outputActive.style.display = 'flex';
    narrativeBlock.style.display = 'none';
    errorBlock.style.display = 'none';
    stepsList.innerHTML = '';
    narrativeText.innerHTML = '';
    outputCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function getStepClass(content) {
    const c = content.toLowerCase();
    if (c.includes('strategy') || c.includes('attempt')) return 'step-strategy';
    if (c.includes('copy') || c.includes('copywriter'))   return 'step-copy';
    if (c.includes('score'))                               return 'step-score';
    return 'step-memory';
}

function addStep(content) {
    const item = document.createElement('div');
    item.className = `step-item ${getStepClass(content)}`;
    item.innerHTML = `<div class="step-dot"></div><span>${escapeHtml(content)}</span>`;
    stepsList.appendChild(item);
    item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showNarrative(html) {
    narrativeText.innerHTML = html;
    narrativeBlock.style.display = 'block';
    narrativeBlock.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showError(msg) {
    errorText.textContent = msg;
    errorBlock.style.display = 'flex';
}

function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Copy button ───────────────────────────────────────────
copyBtn.addEventListener('click', () => {
    const text = narrativeText.innerText;
    navigator.clipboard.writeText(text).then(() => {
        copyBtn.classList.add('copied');
        copyBtn.querySelector('span') && (copyBtn.querySelector('span').textContent = 'Copied!');
        setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyBtn.innerHTML = `
                <svg viewBox="0 0 16 16" fill="none">
                    <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="currentColor" stroke-width="1.2"/>
                    <path d="M3 11V3a1 1 0 011-1h8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
                </svg>
                Copy`;
        }, 2000);
    });
});

// ── Form submit ───────────────────────────────────────────
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const data = {
        product_name:    document.getElementById('product_name').value,
        product_desc:    document.getElementById('product_desc').value,
        target_audience: document.getElementById('target_audience').value,
        brand_voice:     brandVoiceHidden.value || 'Authentic, Refreshing',
        output_language: document.getElementById('output_language').value,
    };

    if (!validateForm(data)) return;

    // UI: loading state
    generateBtn.disabled = true;
    generateBtn.classList.add('loading');
    generateBtn.querySelector('.btn-text').textContent = 'Generating...';

    showOutput();

    try {
        const resp = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        if (!resp.ok) throw new Error(`Server error: ${resp.status}`);

        const reader  = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer    = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE lines
            const lines = buffer.split('\n');
            buffer = lines.pop(); // keep incomplete last line

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed.startsWith('data: ')) continue;
                const payload = trimmed.slice(6).trim();
                if (!payload || payload === '[DONE]') continue;

                try {
                    const msg = JSON.parse(payload);
                    if (msg.type === 'step')      addStep(msg.content);
                    if (msg.type === 'narrative') showNarrative(msg.content);
                    if (msg.type === 'error')     showError(msg.content);
                } catch (_) { /* ignore parse errors */ }
            }
        }

    } catch (err) {
        showError(err.message || 'Connection error. Please try again.');
    } finally {
        generateBtn.disabled = false;
        generateBtn.classList.remove('loading');
        generateBtn.querySelector('.btn-text').textContent = 'Generate Campaign';
    }
});
