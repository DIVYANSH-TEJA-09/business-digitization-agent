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
    if (viewName === 'data' && state.currentJobId) {
        // Auto-load last job if viewing data tab
        loadJobData();
    }
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
// CONNECTION STATUS
// ═══════════════════════════════════════════════════════════

function updateConnectionStatus(isConnected) {
    let indicator = $('connection-status');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'connection-status';
        const headerInner = document.querySelector('.header-inner');
        if (headerInner) headerInner.appendChild(indicator);
    }
    indicator.className = `connection-status ${isConnected ? 'connected' : 'disconnected'}`;
    indicator.innerHTML = isConnected
        ? '<span class="status-dot"></span> Backend Connected'
        : '<span class="status-dot"></span> Backend Disconnected';
}

// ═══════════════════════════════════════════════════════════
// HEALTH CHECK
// ═══════════════════════════════════════════════════════════

async function checkHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (!res.ok) throw new Error('Health check failed');

        const health = await res.json();
        updateConnectionStatus(true);

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
        updateConnectionStatus(false);
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

// ═══════════════════════════════════════════════════════════
// DATA VIEWER
// ═══════════════════════════════════════════════════════════

let currentJobData = null;

// Data viewer event listeners
$('btn-load-job')?.addEventListener('click', loadJobData);
$('job-id-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loadJobData();
});

// Tab switching for data viewer
$$('.data-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        switchDataTab(tab);
    });
});

async function loadJobData() {
    const jobId = $('job-id-input').value.trim();
    if (!jobId) {
        alert('Please enter a Job ID');
        return;
    }

    try {
        $('btn-load-job').disabled = true;
        $('btn-load-job').textContent = 'Loading...';

        const res = await fetch(`${API_BASE}/api/job-data/${jobId}`);
        if (!res.ok) {
            throw new Error('Job data not found. Make sure the job has completed processing.');
        }

        currentJobData = await res.json();
        state.currentJobId = jobId;

        // Show tabs and content, hide empty state
        $('data-tabs').style.display = 'flex';
        $('tab-content-container').style.display = 'block';
        $('data-empty').style.display = 'none';

        // Render all sections
        renderOverview(currentJobData);
        renderPdfDocs(currentJobData);  // New: Render PDF-wise data
        renderDocuments(currentJobData);
        renderTables(currentJobData);
        renderMedia(currentJobData);
        renderProfileView(currentJobData);
        renderValidation(currentJobData);

    } catch (err) {
        alert(err.message);
        $('data-tabs').style.display = 'none';
        $('tab-content-container').style.display = 'none';
        $('data-empty').style.display = 'block';
    } finally {
        $('btn-load-job').disabled = false;
        $('btn-load-job').textContent = 'Load Data';
    }
}

function switchDataTab(tabName) {
    // Update tab buttons
    $$('.data-tabs .tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update tab content
    $$('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

function renderOverview(data) {
    // Count stats
    const docCount = data.parsed_documents?.length || 0;
    const tableCount = data.extracted_tables?.length || 0;
    const imageCount = data.media_collection?.images?.length || 0;
    const completeness = data.validation?.completeness_score || 0;

    $('stat-docs').textContent = docCount;
    $('stat-tables').textContent = tableCount;
    $('stat-images').textContent = imageCount;
    $('stat-completeness').textContent = `${Math.round(completeness * 100)}%`;

    // File collection
    const fc = data.file_collection;
    if (fc) {
        let html = `<div class="overview-grid" style="margin-bottom:1rem">`;
        html += `<div class="stat-card"><div class="stat-value">${fc.total_files || 0}</div><div class="stat-label">Total Files</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${fc.documents?.length || 0}</div><div class="stat-label">Documents</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${fc.spreadsheets?.length || 0}</div><div class="stat-label">Spreadsheets</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${fc.images?.length || 0}</div><div class="stat-label">Images</div></div>`;
        html += `</div>`;

        if (fc.directory_structure) {
            html += `<h4 style="margin:1rem 0 0.5rem">Directory Structure</h4>`;
            html += `<pre style="background:var(--bg-primary);padding:1rem;border-radius:8px;overflow-x:auto;font-size:0.875rem">${JSON.stringify(fc.directory_structure, null, 2)}</pre>`;
        }

        $('file-collection-content').innerHTML = html;
    }
}

async function renderPdfDocs(data) {
    // Fetch PDF-wise data
    const jobId = state.currentJobId;
    try {
        const res = await fetch(`${API_BASE}/api/job-data/${jobId}/pdf-wise`);
        if (!res.ok) {
            $('pdf-docs-content').innerHTML = '<p style="color:var(--text-secondary)">PDF-wise data not available. Processing may still be in progress.</p>';
            return;
        }
        
        const pdfData = await res.json();
        
        if (!pdfData.pdfs || Object.keys(pdfData.pdfs).length === 0) {
            $('pdf-docs-content').innerHTML = '<p style="color:var(--text-secondary)">No PDF documents with images found</p>';
            return;
        }
        
        // Summary
        let html = `<div class="overview-grid" style="margin-bottom:1.5rem">`;
        html += `<div class="stat-card"><div class="stat-value">${pdfData.summary?.total_pdfs || 0}</div><div class="stat-label">PDFs Processed</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${pdfData.summary?.total_images_extracted || 0}</div><div class="stat-label">Images Extracted</div></div>`;
        html += `<div class="stat-card"><div class="stat-value">${pdfData.summary?.total_yolo_detections || 0}</div><div class="stat-label">YOLO Detections</div></div>`;
        html += `</div>`;
        
        // PDF-wise sections
        Object.entries(pdfData.pdfs).forEach(([pdfId, pdf]) => {
            const pdfName = pdf.pdf_name || 'Unknown PDF';
            const totalPages = pdf.total_pages || 0;
            const totalImages = pdf.total_images || 0;
            
            html += `<div class="data-section-card" style="margin-top:1.5rem">`;
            html += `<h3>📕 ${escapeHtml(pdfName)}</h3>`;
            html += `<div style="display:flex;gap:1rem;margin-bottom:1rem;font-size:0.875rem;color:var(--text-secondary)">`;
            html += `<span>📄 ${totalPages} pages</span>`;
            html += `<span>🖼️ ${totalImages} images</span>`;
            if (pdf.document_metadata?.title) {
                html += `<span>📝 ${escapeHtml(pdf.document_metadata.title)}</span>`;
            }
            html += `</div>`;
            
            // Pages with images
            if (pdf.pages && Object.keys(pdf.pages).length > 0) {
                html += `<h4 style="margin:1rem 0">Pages with Images</h4>`;
                
                Object.entries(pdf.pages).forEach(([pageNum, pageData]) => {
                    html += `<div class="document-item">`;
                    html += `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem">`;
                    html += `<strong style="color:var(--accent-primary)">Page ${pageData.page_number}</strong>`;
                    html += `<span style="font-size:0.875rem;color:var(--text-secondary)">${pageData.images?.length || 0} image(s)</span>`;
                    html += `</div>`;
                    
                    // Images grid for this page
                    if (pageData.images && pageData.images.length > 0) {
                        html += `<div class="media-grid">`;
                        pageData.images.forEach((img, imgIdx) => {
                            const filePath = img.file_path || '';
                            const fileName = filePath.split('/').pop() || `Image ${imgIdx + 1}`;
                            const fileUrl = filePath.startsWith('http') ? filePath : `/${filePath}`;
                            
                            html += `<div class="media-item">`;
                            
                            // Image preview
                            if (filePath && filePath !== '') {
                                html += `<img src="${fileUrl}" alt="${escapeHtml(fileName)}" class="media-preview" onerror="this.style.display='none';this.parentElement.querySelector('.no-image').style.display='flex'" />`;
                                html += `<div class="no-image" style="display:none;height:150px;align-items:center;justify-content:center;background:var(--bg-primary);border-radius:8px;margin-bottom:0.75rem;color:var(--text-secondary)">Image not available</div>`;
                            } else {
                                html += `<div class="no-image" style="height:150px;display:flex;align-items:center;justify-content:center;background:var(--bg-primary);border-radius:8px;margin-bottom:0.75rem;color:var(--text-secondary)">No image file</div>`;
                            }
                            
                            html += `<div class="media-info">`;
                            html += `<h4 style="font-size:0.875rem">${escapeHtml(fileName)}</h4>`;
                            html += `<p style="font-size:0.75rem">${img.width || 0} × ${img.height || 0} • ${formatSize(img.file_size || 0)}</p>`;
                            
                            // YOLO detections
                            if (img.yolo_detections && img.yolo_detections.length > 0) {
                                html += `<div style="margin-top:0.5rem">`;
                                html += `<span style="font-size:0.75rem;color:var(--accent-primary)">🎯 YOLO Detections (${img.yolo_detections.length}):</span>`;
                                html += `<div style="display:flex;flex-wrap:wrap;gap:0.25rem;margin-top:0.25rem">`;
                                img.yolo_detections.slice(0, 5).forEach(det => {
                                    html += `<span class="tag">${escapeHtml(det.class)} ${(det.confidence * 100).toFixed(0)}%</span>`;
                                });
                                if (img.yolo_detections.length > 5) {
                                    html += `<span class="tag">+${img.yolo_detections.length - 5} more</span>`;
                                }
                                html += `</div>`;
                                html += `</div>`;
                            }
                            
                            // Vision description
                            if (img.vision_description && img.vision_description.description) {
                                html += `<div style="margin-top:0.5rem">`;
                                html += `<span style="font-size:0.75rem;color:var(--accent-primary)">👁️ AI Description:</span>`;
                                html += `<p style="font-size:0.75rem;margin-top:0.25rem;color:var(--text-secondary)">${escapeHtml(img.vision_description.description)}</p>`;
                                
                                if (img.vision_description.tags && img.vision_description.tags.length > 0) {
                                    html += `<div style="display:flex;flex-wrap:wrap;gap:0.25rem;margin-top:0.25rem">`;
                                    img.vision_description.tags.slice(0, 5).forEach(tag => {
                                        html += `<span class="tag">${escapeHtml(tag)}</span>`;
                                    });
                                    html += `</div>`;
                                }
                                
                                if (img.vision_description.category) {
                                    html += `<p style="font-size:0.75rem;margin-top:0.25rem;color:var(--text-secondary)">Category: ${escapeHtml(img.vision_description.category)}</p>`;
                                }
                                html += `</div>`;
                            }
                            
                            html += `</div>`;  // media-info
                            html += `</div>`;  // media-item
                        });
                        html += `</div>`;  // media-grid
                    }
                    
                    html += `</div>`;  // document-item
                });
            }
            
            html += `</div>`;  // data-section-card
        });
        
        $('pdf-docs-content').innerHTML = html;
        
    } catch (err) {
        console.error('Failed to load PDF-wise data:', err);
        $('pdf-docs-content').innerHTML = `<p style="color:var(--color-error)">Failed to load PDF data: ${escapeHtml(err.message)}</p>`;
    }
}

function renderDocuments(data) {
    const docs = data.parsed_documents || [];
    if (docs.length === 0) {
        $('documents-content').innerHTML = '<p style="color:var(--text-secondary)">No documents found</p>';
        return;
    }

    let html = '';
    docs.forEach((doc, idx) => {
        const fileName = doc.source_file.split('/').pop() || doc.source_file;
        html += `<div class="document-item">`;
        html += `<div class="document-header">`;
        html += `<span class="document-name">📄 ${fileName}</span>`;
        html += `<span class="document-meta">${doc.file_type} • ${doc.total_pages} pages</span>`;
        html += `</div>`;
        html += `<div class="document-meta" style="margin-bottom:0.75rem">Size: ${formatSize(doc.metadata?.file_size || 0)}</div>`;
        html += `<details>`;
        html += `<summary style="cursor:pointer;color:var(--accent-primary);margin-bottom:0.5rem">View Extracted Text</summary>`;
        html += `<div class="document-text">${escapeHtml(doc.full_text || 'No text extracted')}</div>`;
        html += `</details>`;
        html += `</div>`;
    });

    $('documents-content').innerHTML = html;
}

function renderTables(data) {
    const tables = data.extracted_tables || [];
    if (tables.length === 0) {
        $('tables-content').innerHTML = '<p style="color:var(--text-secondary)">No tables extracted</p>';
        return;
    }

    let html = '';
    tables.forEach((table, idx) => {
        const typeClass = `table-type-${table.table_type?.toLowerCase() || 'general'}`;
        html += `<div class="table-item">`;
        html += `<div class="table-header">`;
        html += `<span><strong>Table ${idx + 1}</strong> - ${table.source_doc?.split('/').pop()}</span>`;
        html += `<span class="table-type-badge ${typeClass}">${table.table_type || 'UNKNOWN'}</span>`;
        html += `</div>`;
        html += `<div style="margin-bottom:0.75rem;font-size:0.875rem;color:var(--text-secondary)">Page ${table.source_page} • ${table.rows?.length || 0} rows • Confidence: ${Math.round((table.confidence || 0) * 100)}%</div>`;

        if (table.headers && table.headers.length > 0) {
            html += `<table class="data-table">`;
            html += `<thead><tr>`;
            table.headers.forEach(h => html += `<th>${escapeHtml(h)}</th>`);
            html += `</tr></thead>`;
            html += `<tbody>`;
            (table.rows || []).forEach((row, ri) => {
                html += `<tr>`;
                row.forEach(cell => html += `<td>${escapeHtml(cell || '')}</td>`);
                html += `</tr>`;
            });
            html += `</tbody></table>`;
        }

        html += `</div>`;
    });

    $('tables-content').innerHTML = html;
}

function renderMedia(data) {
    // Media collection
    const mc = data.media_collection;
    if (mc && mc.images && mc.images.length > 0) {
        let html = `<div class="media-grid">`;
        mc.images.forEach((img, idx) => {
            const filePath = img.file_path || '';
            const fileName = filePath.split('/').pop() || `Image ${idx + 1}`;
            const fileUrl = filePath.startsWith('http') ? filePath : `/${filePath}`;

            html += `<div class="media-item">`;
            if (filePath && filePath !== '') {
                html += `<img src="${fileUrl}" alt="${fileName}" class="media-preview" onerror="this.style.display='none'" />`;
            }
            html += `<div class="media-info">`;
            html += `<h4>${escapeHtml(fileName)}</h4>`;
            html += `<p>Size: ${formatSize(img.file_size || 0)}</p>`;
            html += `<p>Method: ${img.extraction_method || 'unknown'}</p>`;
            html += `</div>`;
            html += `</div>`;
        });
        html += `</div>`;
        $('media-content').innerHTML = html;
    } else {
        $('media-content').innerHTML = '<p style="color:var(--text-secondary)">No media extracted</p>';
    }

    // Image analyses
    const analyses = data.image_analyses || [];
    if (analyses.length > 0) {
        let html = `<div class="media-grid">`;
        analyses.forEach((analysis, idx) => {
            html += `<div class="media-item">`;
            html += `<div class="media-info">`;
            html += `<h4>Image ${idx + 1}</h4>`;
            html += `<p><strong>Category:</strong> ${analysis.category || 'unknown'}</p>`;
            html += `<p><strong>Description:</strong> ${escapeHtml(analysis.description || 'No description')}</p>`;
            if (analysis.tags && analysis.tags.length > 0) {
                html += `<div style="margin-top:0.5rem">`;
                analysis.tags.forEach(tag => html += `<span class="tag">${escapeHtml(tag)}</span>`);
                html += `</div>`;
            }
            html += `<p style="margin-top:0.5rem"><strong>Product:</strong> ${analysis.is_product ? 'Yes' : 'No'} • <strong>Service:</strong> ${analysis.is_service_related ? 'Yes' : 'No'}</p>`;
            html += `<p><strong>Confidence:</strong> ${Math.round((analysis.confidence || 0) * 100)}%</p>`;
            html += `</div>`;
            html += `</div>`;
        });
        html += `</div>`;
        $('image-analysis-content').innerHTML = html;
    } else {
        $('image-analysis-content').innerHTML = '<p style="color:var(--text-secondary)">No image analyses available</p>';
    }
}

function renderProfileView(data) {
    const profile = data.business_profile;
    if (!profile) {
        $('profile-view-content').innerHTML = '<p style="color:var(--text-secondary)">No business profile generated</p>';
        return;
    }

    const info = profile.business_info || {};
    let html = '';

    // Business header
    html += `<div class="data-section-card">`;
    html += `<h3>🏢 Business Information</h3>`;
    html += `<div style="display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(250px,1fr))">`;

    if (info.name) html += `<div><strong>Name:</strong> ${escapeHtml(info.name)}</div>`;
    if (info.description) html += `<div><strong>Description:</strong> ${escapeHtml(info.description)}</div>`;
    if (info.category) html += `<div><strong>Category:</strong> ${escapeHtml(info.category)}</div>`;

    if (info.contact) {
        if (info.contact.phone) html += `<div><strong>Phone:</strong> ${escapeHtml(info.contact.phone)}</div>`;
        if (info.contact.email) html += `<div><strong>Email:</strong> ${escapeHtml(info.contact.email)}</div>`;
        if (info.contact.website) html += `<div><strong>Website:</strong> ${escapeHtml(info.contact.website)}</div>`;
    }

    if (info.location) {
        const loc = info.location;
        const addr = [loc.address, loc.city, loc.state, loc.country].filter(Boolean).join(', ');
        if (addr) html += `<div><strong>Location:</strong> ${escapeHtml(addr)}</div>`;
    }

    html += `</div></div>`;

    // Products
    if (profile.products && profile.products.length > 0) {
        html += `<div class="data-section-card">`;
        html += `<h3>🛍️ Products (${profile.products.length})</h3>`;
        profile.products.forEach((p, idx) => {
            html += `<div class="document-item">`;
            html += `<strong>${escapeHtml(p.name || 'Unnamed Product')}</strong>`;
            if (p.pricing?.base_price) html += ` - ${p.pricing.currency || 'INR'} ${p.pricing.base_price.toLocaleString()}`;
            if (p.description) html += `<p style="margin-top:0.5rem;color:var(--text-secondary)">${escapeHtml(p.description)}</p>`;
            html += `</div>`;
        });
        html += `</div>`;
    }

    // Services
    if (profile.services && profile.services.length > 0) {
        html += `<div class="data-section-card">`;
        html += `<h3>🎯 Services (${profile.services.length})</h3>`;
        profile.services.forEach((p, idx) => {
            html += `<div class="document-item">`;
            html += `<strong>${escapeHtml(p.name || 'Unnamed Service')}</strong>`;
            if (p.pricing?.base_price) html += ` - ${p.pricing.currency || 'INR'} ${p.pricing.base_price.toLocaleString()}`;
            if (p.description) html += `<p style="margin-top:0.5rem;color:var(--text-secondary)">${escapeHtml(p.description)}</p>`;
            html += `</div>`;
        });
        html += `</div>`;
    }

    $('profile-view-content').innerHTML = html;
}

function renderValidation(data) {
    const validation = data.validation;
    if (!validation) {
        $('validation-content').innerHTML = '<p style="color:var(--text-secondary)">No validation data available</p>';
        return;
    }

    let html = `<div class="validation-summary">`;
    html += `<div class="validation-item ${validation.is_valid ? 'success' : 'error'}">`;
    html += `<div class="validation-label">Status</div>`;
    html += `<div class="validation-count">${validation.is_valid ? 'Valid ✓' : 'Invalid ✗'}</div>`;
    html += `</div>`;

    html += `<div class="validation-item success">`;
    html += `<div class="validation-label">Completeness</div>`;
    html += `<div class="validation-count">${Math.round((validation.completeness_score || 0) * 100)}%</div>`;
    html += `</div>`;

    html += `<div class="validation-item warning">`;
    html += `<div class="validation-label">Warnings</div>`;
    html += `<div class="validation-count">${validation.warnings?.length || 0}</div>`;
    html += `</div>`;

    html += `<div class="validation-item error">`;
    html += `<div class="validation-label">Errors</div>`;
    html += `<div class="validation-count">${validation.errors?.length || 0}</div>`;
    html += `</div>`;
    html += `</div>`;

    // Field scores
    if (validation.field_scores) {
        html += `<h4 style="margin:1.5rem 0 1rem">Field Scores</h4>`;
        html += `<div class="overview-grid">`;
        Object.entries(validation.field_scores).forEach(([key, score]) => {
            html += `<div class="stat-card">`;
            html += `<div class="stat-value" style="font-size:1.5rem">${Math.round((score.score || 0) * 100)}%</div>`;
            html += `<div class="stat-label">${key.replace('_', ' ').toUpperCase()}</div>`;
            html += `<div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.25rem">${score.populated_fields}/${score.total_fields} fields</div>`;
            html += `</div>`;
        });
        html += `</div>`;
    }

    // Errors
    if (validation.errors && validation.errors.length > 0) {
        html += `<h4 style="margin:1.5rem 0 1rem">Errors</h4>`;
        html += `<div class="error-list">`;
        validation.errors.forEach(err => {
            html += `<div class="error-item"><strong>${err.field}:</strong> ${escapeHtml(err.message)}</div>`;
        });
        html += `</div>`;
    }

    // Warnings
    if (validation.warnings && validation.warnings.length > 0) {
        html += `<h4 style="margin:1.5rem 0 1rem">Warnings</h4>`;
        html += `<div class="warning-list">`;
        validation.warnings.forEach(warn => {
            html += `<div class="warning-item"><strong>${warn.field}:</strong> ${escapeHtml(warn.message)}</div>`;
        });
        html += `</div>`;
    }

    $('validation-content').innerHTML = html;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
