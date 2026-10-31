// ==========================================
// 1. CONFIG & GLOBALS
// ==========================================
const API_BASE = ''; 
let currentUser = null;
let currentTranscript = '';
let otpTimer = null;
let otpCountdown = 600; // 10 minutes in seconds

// --- Helper Functions ---
window.showToast = function(message, type = 'info') {
    const toast = document.getElementById('toast');
    const icon = document.getElementById('toast-icon');
    const msg = document.getElementById('toast-message');
    if (!toast || !icon || !msg) {
        alert(message);
        return;
    }
    msg.textContent = message;
    icon.className = type === 'success' ? 'fas fa-check-circle' : (type === 'error' ? 'fas fa-exclamation-circle' : 'fas fa-info-circle');
    icon.style.color = type === 'success' ? '#16a34a' : (type === 'error' ? '#dc2626' : 'inherit');
    toast.style.display = 'flex';
    setTimeout(() => { toast.style.display = 'none'; }, 4000);
};

window.startOtpTimer = function() {
    const otpTimerDisplay = document.getElementById('timer-display');
    const resendOtpBtn = document.getElementById('resendOtpBtn'); // Assuming you have this ID
    
    if (otpTimer) clearInterval(otpTimer);
    otpCountdown = 600; 
    if (otpTimerDisplay) otpTimerDisplay.textContent = formatTime(otpCountdown);

    otpTimer = setInterval(() => {
        otpCountdown--;
        if (otpTimerDisplay) otpTimerDisplay.textContent = formatTime(otpCountdown);

        if (otpCountdown <= 0) {
            clearInterval(otpTimer);
            if (resendOtpBtn) {
                resendOtpBtn.disabled = false;
                resendOtpBtn.innerHTML = '<i class="fas fa-redo"></i> Resend OTP';
            }
            window.showToast('OTP expired. Please request a new one.', 'error');
        }
    }, 1000);
};

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

window.checkHealth = async function() {
    try {
        const res = await fetch(`${API_BASE}/api/health`);
        if (res.ok) console.log('Backend is healthy');
    } catch (err) {
        console.warn('Backend not reachable');
    }
};

// ==========================================
// 2. DOM ELEMENTS & INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const otpForm = document.getElementById('otp-form');
    const otpCodeInput = document.getElementById('otp-code');

    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (registerForm) registerForm.addEventListener('submit', handleRegister);
    if (otpForm) otpForm.addEventListener('submit', handleVerifyOtp);

    if (otpCodeInput) {
        otpCodeInput.addEventListener('focus', () => otpCodeInput.select());
        otpCodeInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '').slice(0, 6);
        });
    }

    const famEmail = document.getElementById('family-email');
    const famPhone = document.getElementById('family-phone');
    if (famEmail) famEmail.addEventListener('change', toggleFamilyContact);
    if (famPhone) famPhone.addEventListener('change', toggleFamilyContact);

    const regPass = document.getElementById('reg-password');
    if (regPass) regPass.addEventListener('input', updatePasswordStrength);

    const audioFile = document.getElementById('audio-file');
    if (audioFile) {
        audioFile.addEventListener('change', (e) => {
            const btn = document.getElementById('analyse-btn');
            if (btn) btn.disabled = !e.target.files.length;
        });
    }

    const includeTranscript = document.getElementById('include-transcript');
    if (includeTranscript) {
        includeTranscript.addEventListener('change', (e) => {
            const manualSec = document.getElementById('manual-transcript-section');
            if (manualSec) manualSec.style.display = e.target.checked ? 'block' : 'none';
        });
    }

    window.checkHealth();
});

function toggleFamilyContact() {
    const isEmail = document.getElementById('family-email').checked;
    const emailField = document.getElementById('reg-family-email');
    const phoneField = document.getElementById('reg-family-phone');
    if (emailField) emailField.closest('.field-wrapper').style.display = isEmail ? 'block' : 'none';
    if (phoneField) phoneField.closest('.field-wrapper').style.display = isEmail ? 'none' : 'block';
}

function updatePasswordStrength() {
    const password = document.getElementById('reg-password').value;
    const strengthFill = document.getElementById('strength-fill');
    if (!strengthFill) return;

    if (!password) {
        strengthFill.style.width = '0%';
        strengthFill.style.background = 'var(--text-dim)';
        return;
    }

    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.match(/[a-z]+/)) strength++;
    if (password.match(/[A-Z]+/)) strength++;
    if (password.match(/[0-9]+/)) strength++;
    if (password.match(/[!@#$%^&*(),.?\":{}|<>]+/)) strength++;

    const widths = ['0%', '25%', '50%', '75%', '100%'];
    const colors = ['var(--text-dim)', '#f59e0b', '#f59e0b', '#22d3ee', '#10b981'];

    strengthFill.style.width = widths[strength];
    strengthFill.style.background = colors[strength];
}

// ==========================================
// 3. NAVIGATION
// ==========================================
window.showPage = function(pageId) {
    let baseId = pageId.replace('-page', '');
    document.querySelectorAll('.page-section, .content-section, #auth-pages .page').forEach(section => {
        section.style.display = 'none';
    });

    let targetPage = document.getElementById(baseId + '-page') || document.getElementById(baseId);
    if (targetPage) {
        targetPage.style.display = 'block';
    } else {
        console.error("HTML section missing for:", baseId);
    }

    document.querySelectorAll('.nav-btn, .menu-item').forEach(btn => {
        btn.classList.remove('active');
    });
    
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }
    
    // Load data if hitting specific tabs
    if (baseId === 'dashboard' && typeof loadDashboard === 'function') loadDashboard();
    if (baseId === 'alerts' && typeof loadAlerts === 'function') loadAlerts();
};
window.showSection = window.showPage;

window.switchTab = function(tabId) {
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    
    const targetTab = document.getElementById(tabId);
    if (targetTab) targetTab.classList.add('active');
    
    const tabBtn = document.querySelector(`button[onclick="switchTab('${tabId}')"]`);
    if (tabBtn) tabBtn.classList.add('active');
};

// ==========================================
// 4. AUTH & OTP
// ==========================================
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const res = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok) {
            currentUser = data.user;
            const userEmailEl = document.getElementById('user-email');
            if (userEmailEl) userEmailEl.textContent = currentUser.email;
            
            document.getElementById('auth-pages').style.display = 'none';
            document.getElementById('main-app').style.display = 'flex';
            window.showPage('dashboard');
            window.showToast('Login successful', 'success');
        } else {
            window.showToast(data.error || 'Login failed', 'error');
        }
    } catch (err) {
        window.showToast('Connection error. Is the backend running?', 'error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const familyEmail = document.getElementById('reg-family-email').value.trim();
    const familyPhone = document.getElementById('reg-family-phone').value.trim();
    const tier = document.getElementById('reg-tier').value;

    if (!username || !email || !password || !tier) {
        window.showToast('Please fill out all required fields', 'error');
        return;
    }
    if (!familyEmail && !familyPhone) {
        window.showToast('Please enter either a family email or phone number', 'error');
        return;
    }

    try {
        const formData = {
            email, password, analyst_name: username, soc_tier: tier,
            family_email: familyEmail || null, family_phone: familyPhone || null
        };
        const res = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        const data = await res.json();

        if (res.ok) {
            window.showToast('Account created! Please verify your email.', 'success');
            const otpDisplay = document.getElementById('otp-email-display');
            if (otpDisplay) otpDisplay.textContent = email;
            window.startOtpTimer();
            window.showPage('otp-page');
            document.getElementById('register-form').reset();
        } else {
            window.showToast(data.error || 'Registration failed', 'error');
        }
    } catch (err) {
        window.showToast('Connection error. Is the backend running?', 'error');
    }
}

async function handleVerifyOtp(e) {
    e.preventDefault();
    const otpCodeInput = document.getElementById('otp-code');
    const otp = otpCodeInput.value.trim();
    const email = document.getElementById('otp-email-display').textContent;

    if (!otp || otp.length !== 6) {
        window.showToast('Please enter the 6-digit OTP', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/auth/verify-otp`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, otp })
        });
        const data = await res.json();

        if (res.ok) {
            window.showToast('Email verified successfully! Please sign in.', 'success');
            window.showPage('login-page');
        } else {
            window.showToast(data.error || 'Invalid OTP', 'error');
            otpCodeInput.value = '';
            otpCodeInput.focus();
        }
    } catch (err) {
        window.showToast('Connection error. Is the backend running?', 'error');
    }
}

window.resendOtp = function() {
    const email = document.getElementById('otp-email-display').textContent;
    if (!email) {
        window.showToast('No email to resend OTP to', 'error');
        return;
    }

    const btn = document.getElementById('resendOtpBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    }

    fetch(`${API_BASE}/api/auth/resend-otp`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
    })
    .then(async res => {
        const data = await res.json();
        if (res.ok) {
            window.showToast('OTP resent to your email', 'success');
            window.startOtpTimer();
        } else {
            window.showToast(data.error || 'Failed to resend OTP', 'error');
        }
    })
    .catch(err => window.showToast('Connection error', 'error'))
    .finally(() => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-redo"></i> Resend OTP';
        }
    });
};

function logout() {
    currentUser = null;
    document.getElementById('auth-pages').style.display = 'block';
    document.getElementById('main-app').style.display = 'none';
    window.showPage('login-page');
    document.getElementById('login-form').reset();
    document.getElementById('register-form').reset();
}

// ==========================================
// 5. DASHBOARD & ALERTS
// ==========================================
window.loadDashboard = async function() {
    try {
        const res = await fetch(`${API_BASE}/api/alerts`);
        const data = await res.json();
        updateStats(data.stats);
        updateRecentAlerts(data.alerts.slice(0, 5));
    } catch (err) {
        console.error('Failed to load dashboard:', err);
    }
};

function updateStats(stats) {
    if (!stats) return;
    const tAlerts = document.getElementById('stat-total-alerts');
    const hRisk = document.getElementById('stat-high-risk');
    const qPct = document.getElementById('stat-quarantined');
    const vClones = document.getElementById('stat-voice-clones');
    
    if (tAlerts) tAlerts.textContent = stats.totalAlerts;
    if (hRisk) hRisk.textContent = stats.highRisk;
    if (qPct) qPct.textContent = stats.quarantinedPercent + '%';
    if (vClones) vClones.textContent = stats.tabs ? stats.tabs.voiceClones : '0';
}

function updateRecentAlerts(alerts) {
    const tbody = document.querySelector('#recent-alerts-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4">No alerts yet</td></tr>';
        return;
    }
    alerts.forEach(a => {
        const riskClass = (a.risk_level || '').toLowerCase();
        tbody.innerHTML += `
            <tr>
                <td>${a.source || '-'}</td>
                <td>${a.type || '-'}</td>
                <td><span class="risk-badge ${riskClass}">${a.risk_level || '-'}</span></td>
                <td>${new Date(a.created_at).toLocaleDateString()}</td>
            </tr>
        `;
    });
}

window.loadAlerts = async function() {
    const type = document.getElementById('filter-type')?.value;
    const risk = document.getElementById('filter-risk')?.value;
    let url = `${API_BASE}/api/alerts`;
    const params = new URLSearchParams();
    if (type && type !== 'ALL') params.append('type', type);
    if (risk) params.append('risk_level', risk);
    if (params.toString()) url += '?' + params.toString();

    try {
        const res = await fetch(url);
        const data = await res.json();
        renderAlertsTable(data.alerts || []);
        updateStats(data.stats || {});
    } catch (err) {
        window.showToast('Failed to load alerts', 'error');
    }
};

function renderAlertsTable(alerts) {
    const tbody = document.querySelector('#alerts-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7">No alerts found</td></tr>';
        return;
    }
    alerts.forEach(a => {
        const riskClass = (a.risk_level || '').toLowerCase();
        tbody.innerHTML += `
            <tr>
                <td>${a.source || '-'}</td>
                <td>${a.type || '-'}</td>
                <td><span class="risk-badge ${riskClass}">${a.risk_level || '-'}</span></td>
                <td>${a.description || '-'}</td>
                <td>${(a.confidence || 0).toFixed(1)}%</td>
                <td>${new Date(a.created_at).toLocaleString()}</td>
                <td><button class="btn btn-outline" onclick="deleteAlert('${a.id}')" style="padding: 4px 8px; font-size: 12px;">Delete</button></td>
            </tr>
        `;
    });
}

window.deleteAlert = async function(id) {
    if (!confirm('Delete this alert?')) return;
    try {
        await fetch(`${API_BASE}/api/alerts/${id}`, { method: 'DELETE' });
        window.loadAlerts();
        window.showToast('Alert deleted', 'success');
    } catch (err) {
        window.showToast('Failed to delete alert', 'error');
    }
};

// ==========================================
// 6. AUDIO & TEXT ANALYSIS (STATIC)
// ==========================================
window.analyseAudio = async function() {
    const fileInput = document.getElementById('audio-file');
    if (!fileInput || !fileInput.files.length) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('delete_after', document.getElementById('delete-after')?.checked || false);
    formData.append('user_id', currentUser ? currentUser.id : '');

    const includeTranscript = document.getElementById('include-transcript')?.checked;
    if (includeTranscript) {
        const manualTranscript = document.getElementById('manual-transcript').value;
        if (manualTranscript.trim()) formData.append('transcript', manualTranscript);
    }

    const btn = document.getElementById('analyse-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analysing...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/api/analyse/audio`, { method: 'POST', body: formData });
        const result = await res.json();
        if (res.ok) {
            displayResults(result);
            window.showPage('results-section');
            window.showToast('Analysis complete', 'success');
        } else {
            window.showToast(result.error || 'Analysis failed', 'error');
        }
    } catch (err) {
        window.showToast('Connection error. Is the backend running?', 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
};

window.transcribeAudio = async function() {
    const fileInput = document.getElementById('transcribe-file');
    if (!fileInput || !fileInput.files.length) {
        window.showToast('Please select an audio file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('language', document.getElementById('transcribe-language')?.value || 'en-US');

    try {
        const res = await fetch(`${API_BASE}/api/transcribe`, { method: 'POST', body: formData });
        const result = await res.json();
        if (res.ok && result.Success) {
            document.getElementById('transcript-text').textContent = result.text;
            document.getElementById('transcribe-result').style.display = 'block';
            currentTranscript = result.text;
            window.showToast('Transcription complete', 'success');
        } else {
            window.showToast(result.error || 'Transcription failed', 'error');
        }
    } catch (err) {
        window.showToast('Connection error. Is the backend running?', 'error');
    }
};

window.useTranscript = function() {
    if (!currentTranscript) return;
    document.getElementById('text-transcript').value = currentTranscript;
    window.showPage('analyse');
    window.switchTab('text-tab');
    window.showToast('Transcript loaded for analysis', 'success');
};

function displayResults(result) {
    // (Logic left identical to your original code to handle the result cards)
    const risk = result.combined_risk || 'safe';
    const riskBadge = document.getElementById('risk-badge');
    const riskScore = document.getElementById('risk-score');
    if (riskBadge) {
        riskBadge.className = `risk-badge ${risk}`;
        riskBadge.textContent = risk.toUpperCase();
    }
    
    const vc = result.voice_clone || {};
    const sc = result.scam_script || {};
    const score = Math.max(vc.synthetic_probability || 0, sc.risk_score || 0);
    if (riskScore) riskScore.textContent = (score * 100).toFixed(1) + '%';
    
    const riskMessage = document.getElementById('risk-message');
    if (riskMessage) riskMessage.textContent = result.summary || 'Analysis completed.';

    const recBox = document.getElementById('recommendation-box');
    const recText = document.getElementById('recommendation-text');
    if (recText) recText.textContent = result.recommendation || 'No specific recommendation.';
    if (recBox) recBox.style.display = 'block';
}

// ==========================================
// 7. LIVE STT (FRAUD30 WASAPI)
// ==========================================
window.livePollInterval = null;

window.startLiveStt = async function() {
    try {
        const res = await fetch(API_BASE + "/api/stt/start", { method: "POST" });
        if (res.ok) {
            document.getElementById("stt-start-btn").style.display = "none";
            document.getElementById("stt-stop-btn").style.display = "inline-block";
            document.getElementById("live-transcript-feed").innerHTML = `<em style="color: #38bdf8;">Listening to system audio tap...</em><br><br>`;
            
            // Poll for text every 2 seconds
            window.livePollInterval = setInterval(window.fetchLatestTranscripts, 2000);
        } else {
            alert("Failed to connect to backend STT engine.");
        }
    } catch (err) {
        console.error("Failed to start STT:", err);
    }
};

window.stopLiveStt = async function() {
    try {
        await fetch(API_BASE + "/api/stt/stop", { method: "POST" });
        clearInterval(window.livePollInterval);
        
        document.getElementById("stt-start-btn").style.display = "inline-block";
        document.getElementById("stt-stop-btn").style.display = "none";
        document.getElementById("live-transcript-feed").innerHTML += `<br><br><em style="color: #ef4444;">Intercept stopped.</em>`;
    } catch (err) {
        console.error("Failed to stop STT:", err);
    }
};

window.fetchLatestTranscripts = async function() {
    try {
        const res = await fetch(API_BASE + "/api/transcriptions");
        if (!res.ok) return;
        
        const rows = await res.json();
        const feed = document.getElementById("live-transcript-feed");
        if (!feed) return; 
        
        feed.innerHTML = rows.map(t => {
            let color = t.risk_level === 'HIGH' ? '#ef4444' : (t.risk_level === 'MEDIUM' ? '#f59e0b' : '#22c55e');
            let badge = t.risk_level === 'HIGH' ? '🚨 HIGH RISK' : (t.risk_level === 'MEDIUM' ? '⚠️ MEDIUM RISK' : '✅ LOW RISK');
            
            return `
                <div style="margin-bottom: 15px; border-left: 4px solid ${color}; padding: 10px 15px; background: #1e293b; border-radius: 0 8px 8px 0;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong style="color: #94a3b8; font-size: 0.85em;">🕒 ${t.date_label || 'Now'} | Chunk ID: ${t.id || '-'}</strong>
                        <span style="background: ${color}20; color: ${color}; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: bold;">${badge}</span>
                    </div>
                    <span style="color: #f8fafc; font-size: 1.05em; line-height: 1.4;">"${t.transcript_text}"</span><br>
                    <div style="margin-top: 8px; font-size: 0.9em; color: ${color};">
                        <strong>AI Analysis:</strong> ${t.ai_summary || 'Analyzing...'}
                    </div>
                </div>
            `;
        }).join("");
        
        feed.scrollTop = feed.scrollHeight;
    } catch (err) {
        console.error("Error fetching live transcripts:", err);
    }
};
// --- DASHBOARD & ALERTS DATA SYNC ---

window.loadDashboard = async function() {
    try {
        const res = await fetch(API_BASE + "/api/transcriptions");
        if (!res.ok) return;
        const rows = await res.json();
        
        // Count the threats
        const totalAlerts = rows.filter(t => t.risk_level === 'HIGH' || t.risk_level === 'MEDIUM').length;
        const highRisk = rows.filter(t => t.risk_level === 'HIGH').length;
        
        // Update the dashboard numbers (make sure these IDs match your HTML)
        const totalElem = document.getElementById("total-alerts-count") || document.querySelector(".dashboard-card:nth-child(1) h2, .dashboard-card:nth-child(1) .text-4xl");
        const highElem = document.getElementById("high-risk-count") || document.querySelector(".dashboard-card:nth-child(2) h2, .dashboard-card:nth-child(2) .text-4xl");
        
        if (totalElem) totalElem.innerText = totalAlerts;
        if (highElem) highElem.innerText = highRisk;
        
    } catch (err) {
        console.error("Error loading dashboard data:", err);
    }
};

window.loadAlerts = async function() {
    try {
        const res = await fetch(API_BASE + "/api/transcriptions");
        if (!res.ok) return;
        const rows = await res.json();
        
        // Filter out safe conversations
        const alerts = rows.filter(t => t.risk_level === 'HIGH' || t.risk_level === 'MEDIUM');
        
        // Find the Alerts page container
        const alertsPage = document.getElementById("alerts-page") || document.getElementById("alerts");
        if (!alertsPage) return;
        
        // Create a dedicated list container if it doesn't exist
        let listContainer = alertsPage.querySelector('.alerts-feed-container');
        if (!listContainer) {
            listContainer = document.createElement('div');
            listContainer.className = 'alerts-feed-container';
            listContainer.style.marginTop = '20px';
            alertsPage.appendChild(listContainer);
        }
        
        // Draw the UI
        if (alerts.length === 0) {
            listContainer.innerHTML = `<h3 style="color: #22c55e;">✅ No active threats detected.</h3>`;
            return;
        }
        
        listContainer.innerHTML = alerts.map(t => {
            let color = t.risk_level === 'HIGH' ? '#ef4444' : '#f59e0b';
            return `
                <div style="margin-bottom: 15px; border-left: 4px solid ${color}; padding: 15px; background: #1e293b; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong style="color: ${color}; font-size: 1.1em;">🚨 ${t.risk_level} RISK DETECTED</strong>
                        <span style="color: #94a3b8; font-size: 0.9em;">🕒 ${t.date_label}</span>
                    </div>
                    <p style="color: #f8fafc; font-size: 1.05em; margin-bottom: 8px;">"${t.transcript_text}"</p>
                    <div style="color: ${color}; font-size: 0.9em; background: #0f172a; padding: 8px; border-radius: 4px;">
                        <strong>AI Breakdown:</strong> ${t.ai_summary}
                    </div>
                </div>
            `;
        }).reverse().join(""); // .reverse() shows the newest alerts at the top
        
    } catch (err) {
        console.error("Error loading alerts data:", err);
    }
};