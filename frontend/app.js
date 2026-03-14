/**
 * BizDigit — Frontend Application Logic
 *
 * Handles:
 *   - File upload via drag-and-drop or button
 *   - Pipeline progress polling
 *   - Business profile rendering
 *   - System health checks
 */

const API_BASE = window.location.port === '5500' || window.location.protocol === 'file:'
    ? 'http://localhost:8000'
    : '';

// ═══════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════

const state = {
    selectedFile: null,
    currentJobId: null,
    pollInterval: null,
    currentView: 'upload',
    profile: null,
};

// ═══════════════════════════════════════════════════════════
// DOM REFERENCES
// ═══════════════════════════════════════════════════════════

const $ = (id) => document.getElementById(id);
const $$ = (sel) => document.querySelectorAll(sel);

// ═══════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Nav buttons
    $$('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
        });
    });

    // Upload zone — drag and drop
    const zone = $('upload-zone');
    const fileInput = $('file-input');

    zone.addEventListener('click', () => fileInput.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) selectFile(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) selectFile(e.target.files[0]);
    });

    // Buttons
    $('btn-upload').addEventListener('click', startUpload);
    $('btn-remove').addEventListener('click', clearFile);
    $('btn-view-profile').addEventListener('click', () => switchView('profile'));
    $('btn-retry').addEventListener('click', resetUpload);
    $('btn-toggle-json').addEventListener('click', toggleJson);
    $('btn-refresh-health').addEventListener('click', checkHealth);

    // Check health on load
    checkHealth();
});

function switchView(viewName) {
    state.currentView = viewName;

    $$('.view').forEach(v => v.classList.remove('active'));
    $(`view-${viewName}`).classList.add('active');

    $$('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    if (viewName === 'health') checkHealth();
}

// ═══════════════════════════════════════════════════════════
// FILE SELECTION
// ═══════════════════════════════════════════════════════════

function selectFile(file) {
    if (!file.name.toLowerCase().endsWith('.zip')) {
        alert('Please select a ZIP file.');
        return;
    }

    state.selectedFile = file;
    $('upload-content').style.display = 'none';
    $('upload-preview').style.display = 'flex';
    $('file-name').textContent = file.name;
    $('file-size').textContent = formatSize(file.size);
    $('btn-upload').disabled = false;
}

function clearFile() {
    state.selectedFile = null;
    $('upload-content').style.display = 'block';
    $('upload-preview').style.display = 'none';
    $('file-input').value = '';
    $('btn-upload').disabled = true;
}

function resetUpload() {
    clearFile();
    $('progress-section').style.display = 'none';
    $('result-card').style.display = 'none';
    $('error-card').style.display = 'none';
    $('btn-upload').style.display = 'flex';
    // Reset pipeline steps
    $$('.step').forEach(s => {
        s.classList.remove('active', 'complete');
    });
}

// ═══════════════════════════════════════════════════════════
// UPLOAD & PROCESSING
// ═══════════════════════════════════════════════════════════

async function startUpload() {
    if (!state.selectedFile) return;

    $('btn-upload').disabled = true;
    $('btn-upload').style.display = 'none';
    $('progress-section').style.display = 'block';
    $('result-card').style.display = 'none';
    $('error-card').style.display = 'none';

    const formData = new FormData();
    formData.append('file', state.selectedFile);

    try {
        updateProgress(0, 'Uploading ZIP file...');

        const response = await fetch(`${API_BASE}/api/upload-and-process`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Upload failed');
        }

        const data = await response.json();
        state.currentJobId = data.job_id;

        updateProgress(5, 'Pipeline started...');
        startPolling();

    } catch (err) {
        showError(err.message);
    }
}

function startPolling() {
    if (state.pollInterval) clearInterval(state.pollInterval);

    state.pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/status/${state.currentJobId}`);
            if (!res.ok) throw new Error('Status check failed');

            const status = await res.json();

            updateProgress(status.progress, status.message);
            updatePipelineSteps(status.current_phase, status.progress);

            if (status.status === 'completed') {
                clearInterval(state.pollInterval);
                await loadProfile();
                showResult(status.message);
            } else if (status.status === 'failed') {
                clearInterval(state.pollInterval);
                showError(status.error_message || status.message);
            }
        } catch (err) {
            console.error('Poll error:', err);
        }
    }, 2000); // Poll every 2 seconds
}

function updateProgress(percent, message) {
    $('progress-fill').style.width = `${percent}%`;
    $('progress-percent').textContent = `${Math.round(percent)}%`;
    $('progress-message').textContent = message;
}

function updatePipelineSteps(currentPhase, progress) {
    const phases = [
        'file_discovery', 'parsing', 'pageindex',
        'table_extraction', 'media_extraction', 'vision_analysis',
        'schema_mapping', 'validation'
    ];

    const currentIdx = phases.indexOf(currentPhase);

    $$('.step').forEach(step => {
        const phase = step.dataset.phase;
        const idx = phases.indexOf(phase);

        if (idx < currentIdx) {
            step.classList.remove('active');
            step.classList.add('complete');
        } else if (idx === currentIdx) {
            step.classList.add('active');
            step.classList.remove('complete');
        } else {
            step.classList.remove('active', 'complete');
        }
    });

    // If complete, mark all as complete
    if (progress >= 100) {
        $$('.step').forEach(s => {
            s.classList.remove('active');
            s.classList.add('complete');
        });
    }
}

function showResult(message) {
    $('progress-section').style.display = 'none';
    $('result-card').style.display = 'block';
    $('result-message').textContent = message;
}

function showError(message) {
    $('progress-section').style.display = 'none';
    $('error-card').style.display = 'block';
    $('error-message').textContent = message;
    $('btn-upload').style.display = 'flex';
    $('btn-upload').disabled = false;
}

// ═══════════════════════════════════════════════════════════
// PROFILE RENDERING
// ═══════════════════════════════════════════════════════════

async function loadProfile() {
    if (!state.currentJobId) return;

    try {
        const res = await fetch(`${API_BASE}/api/profile/${state.currentJobId}`);
        if (!res.ok) throw new Error('Profile not ready');

        state.profile = await res.json();
        renderProfile(state.profile);
    } catch (err) {
        console.error('Profile load error:', err);
    }
}

function renderProfile(profile) {
    $('profile-empty').style.display = 'none';
    $('profile-header').style.display = 'block';
    $('profile-grid').style.display = 'grid';
    $('json-section').style.display = 'block';

    // Header
    const info = profile.business_info || {};
    $('profile-badge').textContent = (profile.business_type || 'UNKNOWN').toUpperCase();
    $('profile-name').textContent = info.name || 'Untitled Business';
    $('profile-description').textContent = info.description || '';

    // Tags
    const tagsHtml = (info.tags || []).map(t => `<span class="tag">${t}</span>`).join('');
    $('profile-tags').innerHTML = tagsHtml;

    // Contact
    renderContact(info);

    // Hours
    renderHours(info);

    // Score
    renderScore(profile);

    // Products
    if (profile.products && profile.products.length > 0) {
        $('section-products').style.display = 'block';
        renderItems('products-grid', profile.products, 'product');
    }

    // Services
    if (profile.services && profile.services.length > 0) {
        $('section-services').style.display = 'block';
        renderItems('services-grid', profile.services, 'service');
    }

    // JSON
    $('json-view').textContent = JSON.stringify(profile, null, 2);
}

function renderContact(info) {
    const contact = info.contact || {};
    const location = info.location || {};

    let html = '';
    if (contact.phone) html += `<div><span class="label">Phone</span><br><span class="value">${contact.phone}</span></div>`;
    if (contact.email) html += `<div><span class="label">Email</span><br><span class="value">${contact.email}</span></div>`;
    if (contact.website) html += `<div><span class="label">Website</span><br><span class="value">${contact.website}</span></div>`;
    if (location.city || location.state) {
        const loc = [location.city, location.state, location.country].filter(Boolean).join(', ');
        html += `<div><span class="label">Location</span><br><span class="value">${loc}</span></div>`;
    }
    if (location.address) html += `<div><span class="label">Address</span><br><span class="value">${location.address}</span></div>`;

    $('contact-content').innerHTML = html || '<span class="label">No contact info found</span>';
}

function renderHours(info) {
    const hours = info.working_hours || {};
    const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
    let html = '';

    for (const day of days) {
        if (hours[day]) {
            html += `<div><span class="label">${day.charAt(0).toUpperCase() + day.slice(1)}</span>: <span class="value">${hours[day]}</span></div>`;
        }
    }

    $('hours-content').innerHTML = html || '<span class="label">Not specified</span>';
}

function renderScore(profile) {
    const meta = profile.extraction_metadata || {};
    const score = meta.confidence_score || 0;
    const percent = Math.round(score * 100);

    $('score-value').textContent = `${percent}%`;

    // Animate the ring
    const circumference = 2 * Math.PI * 42;
    const offset = circumference - (score * circumference);

    // Add SVG gradient
    const svg = $('score-ring').querySelector('svg');
    if (!svg.querySelector('defs')) {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const grad = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        grad.setAttribute('id', 'grad');
        const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop1.setAttribute('offset', '0%');
        stop1.setAttribute('style', 'stop-color:#6366f1');
        const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop2.setAttribute('offset', '100%');
        stop2.setAttribute('style', 'stop-color:#ec4899');
        grad.appendChild(stop1);
        grad.appendChild(stop2);
        defs.appendChild(grad);
        svg.prepend(defs);
    }

    setTimeout(() => {
        $('ring-fill').style.strokeDashoffset = offset;
    }, 300);
}

function renderItems(containerId, items, type) {
    const container = $(containerId);
    container.innerHTML = '';

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'item-card animate-in';

        let priceHtml = '';
        if (item.pricing) {
            const price = item.pricing.base_price;
            const currency = item.pricing.currency || 'INR';
            if (price) {
                priceHtml = `<div class="item-price">${currency} ${price.toLocaleString()}</div>`;
            }
        }

        let tagsHtml = '';
        if (item.tags && item.tags.length > 0) {
            tagsHtml = `<div class="item-tags">${item.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>`;
        }

        let detailsHtml = '';
        if (type === 'service' && item.details) {
            const d = item.details;
            if (d.duration) detailsHtml += `<span class="tag">⏱️ ${d.duration}</span>`;
            if (d.group_size) detailsHtml += `<span class="tag">👥 ${d.group_size}</span>`;
        }

        card.innerHTML = `
            <h5>${item.name || 'Unnamed'}</h5>
            <p>${item.description || ''}</p>
            ${priceHtml}
            ${detailsHtml ? `<div class="item-tags">${detailsHtml}</div>` : ''}
            ${tagsHtml}
        `;

        container.appendChild(card);
    });
}

function toggleJson() {
    const view = $('json-view');
    const btn = $('btn-toggle-json');

    if (view.style.display === 'none') {
        view.style.display = 'block';
        btn.textContent = 'Hide Raw JSON';
    } else {
        view.style.display = 'none';
        btn.textContent = 'View Raw JSON';
    }
}

// ═══════════════════════════════════════════════════════════
// HEALTH CHECK
// ═══════════════════════════════════════════════════════════

async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (!res.ok) throw new Error('Health check failed');

        const health = await res.json();

        // Ollama
        const ollamaOk = health.ollama?.status === 'ok';
        $('ind-ollama').className = `health-indicator ${ollamaOk ? 'ok' : 'error'}`;
        $('status-ollama').textContent = health.ollama?.status || 'Unknown';

        // Groq
        const groqOk = health.groq?.status === 'ok';
        $('ind-groq').className = `health-indicator ${groqOk ? 'ok' : 'error'}`;
        $('status-groq').textContent = health.groq?.status || 'Unknown';

        // Storage
        $('ind-storage').className = 'health-indicator ok';
        const storage = health.storage || {};
        const totalMb = Object.values(storage).reduce((sum, s) => sum + (s.size_mb || 0), 0);
        $('status-storage').textContent = `${totalMb.toFixed(1)} MB used`;

    } catch (err) {
        $('ind-ollama').className = 'health-indicator error';
        $('ind-groq').className = 'health-indicator error';
        $('ind-storage').className = 'health-indicator error';
        $('status-ollama').textContent = 'Offline';
        $('status-groq').textContent = 'Offline';
        $('status-storage').textContent = 'Server unreachable';
    }
}

// ═══════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
