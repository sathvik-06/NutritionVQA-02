/**
 * NutritionVQA-RAG — Frontend Application Logic
 */

const isLocalApp = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
window.API_BASE = isLocalApp ? 'http://127.0.0.1:8000' : 'https://sathvik-cs-nutritionvqa-backend.hf.space';
var API_BASE = window.API_BASE;

// ─── DOM Refs ────────────────────────────────────────────────────
const dropZone        = document.getElementById("drop-zone");
const fileInput       = document.getElementById("file-input");
const previewContainer= document.getElementById("preview-container");
const imagePreview    = document.getElementById("image-preview");
const removeImageBtn  = document.getElementById("remove-image");
const chatMessages    = document.getElementById("chat-messages");
const chatForm        = document.getElementById("chat-form");
const questionInput   = document.getElementById("question-input");
const sendBtn         = document.getElementById("send-btn");
const historyList     = document.getElementById("history-list");
const newChatBtn      = document.getElementById("new-chat-btn");

// Camera Modal Refs
const cameraModal     = document.getElementById("camera-modal");
const video           = document.getElementById("video");
const canvas          = document.getElementById("canvas");
const captureBtn      = document.getElementById("capture-frame");
const switchBtn       = document.getElementById("switch-camera");
const closeCameraBtn  = document.getElementById("close-camera");

// Chat Multi-Image Refs
const chatFileInput   = document.getElementById("chat-file-input");
const chatUploadBtn   = document.getElementById("chat-upload-btn");
const chatCameraBtn   = document.getElementById("chat-camera-btn");
const chatPreviews    = document.getElementById("chat-upload-previews");
const btnCameraAnalyzer = document.getElementById("btn-camera-analyzer");
const btnCameraA      = document.getElementById("btn-camera-a");
const btnCameraB      = document.getElementById("btn-camera-b");

let currentImageId = null; 
let currentConversationId = null;
let userProfile = null;

// Multi-image state for chat
let selectedChatImages = []; // Stores objects: { file, id, previewUrl }
let cameraTarget = "analyzer"; // "analyzer", "compare-a", "compare-b", "chat"
let currentFacingMode = "environment"; 
let stream = null;

// ── Comparator State ──
let compareImageA = null;
let compareImageB = null;

// ─── Auth Header Helper ─────────────────────────────────────────
function authHeaders(extra = {}) {
    return {
        "Authorization": `Bearer ${localStorage.getItem("token")}`,
        ...extra
    };
}

async function readApiResponse(res) {
    const text = await res.text();
    try {
        return JSON.parse(text);
    } catch {
        throw new Error(text || `Request failed (${res.status})`);
    }
}

function formatNutrientValue(val) {
    if (!val || val === "N/A" || val === "NA" || val === "-") return "—";
    return val;
}

function mediaUrl(path) {
    if (!path) return null;
    if (path.startsWith("http") || path.startsWith("data:")) return path;
    let p = path.startsWith("/") ? path : `/${path}`;
    if (/^\/[0-9a-f-]{36}\.(jpe?g|png|webp)$/i.test(p) && !p.startsWith("/uploads/")) p = `/uploads${p}`;
    else if (!p.startsWith("/uploads/") && !p.startsWith("/assets/")) p = `/uploads${p}`;
    return `${API_BASE}${p}`;
}

// ─── Theme Toggle ────────────────────────────────────────────────
const themeToggle = document.getElementById("theme-toggle");
if (themeToggle) {
    const savedTheme = localStorage.getItem("theme") || "dark";
    const knob = themeToggle.querySelector(".toggle-knob");
    
    if (savedTheme === "light") {
        document.body.classList.add("light-theme");
        if (knob) knob.textContent = "☀️";
    } else {
        document.body.setAttribute("data-theme", "dark");
        if (knob) knob.textContent = "🌙";
    }

    themeToggle.addEventListener("click", () => {
        const isLight = document.body.classList.toggle("light-theme");
        const currentTheme = isLight ? "light" : "dark";
        
        if (isLight) {
            document.body.removeAttribute("data-theme");
            if (knob) knob.textContent = "☀️";
        } else {
            document.body.setAttribute("data-theme", "dark");
            if (knob) knob.textContent = "🌙";
        }
        
        localStorage.setItem("theme", currentTheme);
    });
}


// ─── View Switching ──────────────────────────────────────────────
document.querySelectorAll('.nav-pill').forEach(pill => {
    pill.addEventListener('click', () => {
        const target = pill.getAttribute('data-target');
        
        // Update Pills
        document.querySelectorAll('.nav-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        
        // Update Views
        document.querySelectorAll('.app-view').forEach(view => {
            view.classList.remove('active');
            if (view.id === target) view.classList.add('active');
        });
    });
});
// ─── Profile & History ──────────────────────────────────────────
async function loadUserProfile() {
    try {
        const res = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() });
        if (res.ok) {
            userProfile = await res.json();
            document.getElementById("user-name").textContent = userProfile.name;
            const initials = userProfile.name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
            document.getElementById("user-initials").textContent = initials || "UN";
        }
    } catch (err) { console.error(err); }
}

async function loadChatHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/chat/history`, { headers: authHeaders() });
        if (!res.ok) return;
        const conversations = await res.json();
        renderHistoryList(conversations);
    } catch (err) { console.error(err); }
}

function renderHistoryList(conversations) {
    if (!conversations || conversations.length === 0) {
        historyList.innerHTML = '<div style="text-align:center; padding: 2rem; color:var(--text-muted); font-size:0.8rem;">No chat history yet</div>';
        return;
    }
    historyList.innerHTML = "";
    conversations.forEach(conv => {
        const item = document.createElement("div");
        item.className = `history-item-v2${conv._id === currentConversationId ? ' active' : ''}`;
        item.onclick = () => loadConversation(conv._id);
        
        const info = document.createElement("div");
        info.className = "history-info-v2";
        info.style = "flex:1; min-width:0;";

        const title = document.createElement("span");
        title.className = "history-title-v2";
        title.textContent = conv.title || "Untitled Chat";
        
        const time = document.createElement("span");
        time.className = "history-time-v2";
        // Mocking time for now as seen in Image 2
        const dateStr = conv.updated_at ? new Date(conv.updated_at).toLocaleDateString() : "Just now";
        time.textContent = dateStr;

        info.appendChild(title);
        info.appendChild(time);
        
        const deleteBtn = document.createElement("button");
        deleteBtn.innerHTML = "🗑️";
        deleteBtn.style = "background:transparent; border:none; color:var(--text-muted); cursor:pointer; padding:4px; font-size:0.8rem; opacity:0.5;";
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            if (confirm("Delete this conversation?")) deleteConversation(conv._id);
        };
        
        item.appendChild(info);
        item.appendChild(deleteBtn);
        historyList.appendChild(item);
    });
}

// ─── Analyzer & Comparator History ──────────────────────────────
async function loadAnalysesHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/features/history/analyses`, { headers: authHeaders() });
        if (!res.ok) return;
        const records = await res.json();
        renderAnalysesList(records);
    } catch (err) { console.error("Error loading analyses history:", err); }
}

async function loadComparisonsHistory() {
    try {
        const res = await fetch(`${API_BASE}/api/features/history/comparisons`, { headers: authHeaders() });
        if (!res.ok) return;
        const records = await res.json();
        renderComparisonsList(records);
    } catch (err) { console.error("Error loading comparisons history:", err); }
}

function renderAnalysesList(records) {
    const list = document.getElementById("recent-analyses-list");
    if (!list) return;
    if (!records || records.length === 0) {
        list.innerHTML = '<p class="no-recent-text">No recent analyses yet.</p>';
        return;
    }
    list.innerHTML = "";
    records.forEach(rec => {
        const card = document.createElement("div");
        card.className = "history-card";
        card.innerHTML = `
            <div class="history-thumb-icon" style="width:48px;height:48px;display:flex;align-items:center;justify-content:center;background:var(--bg-card,#f0f0f0);border-radius:8px;font-size:1.5rem;">🏷️</div>
            <div class="history-info">
                <div class="history-title">${rec.nutrition_data.product_name || 'Nutrition Label'}</div>
                <div class="history-date">${new Date(rec.created_at).toLocaleDateString()}</div>
            </div>
            <button class="history-delete-btn" onclick="deleteAnalysis('${rec._id}')">✕</button>
        `;
        card.onclick = () => {
            // Re-view this analysis
            showAnalyzerResult(rec);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };
        list.appendChild(card);
    });
}

function renderComparisonsList(records) {
    const list = document.getElementById("recent-comparisons-list");
    if (!list) return;
    if (!records || records.length === 0) {
        list.innerHTML = '<p class="no-recent-text">No recent comparisons yet.</p>';
        return;
    }
    list.innerHTML = "";
    records.forEach(rec => {
        const card = document.createElement("div");
        card.className = "history-card";
        card.innerHTML = `
            <div class="history-thumb-icon" style="width:48px;height:48px;display:flex;align-items:center;justify-content:center;background:var(--bg-card,#f0f0f0);border-radius:8px;font-size:1.5rem;">⚖️</div>
            <div class="history-info">
                <div class="history-title">Compare: Product A vs B</div>
                <div class="history-date">${new Date(rec.created_at).toLocaleDateString()} • Winner: Product ${rec.winner}</div>
            </div>
            <button class="history-delete-btn" onclick="deleteComparison('${rec._id}')">✕</button>
        `;
        card.onclick = () => {
            showComparisonResult(rec);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };
        list.appendChild(card);
    });
}

window.deleteAnalysis = async (id) => {
    if (!confirm("Delete this analysis record?")) return;
    try {
        const res = await fetch(`${API_BASE}/api/features/history/analyses/${id}`, {
            method: 'DELETE',
            headers: authHeaders()
        });
        if (res.ok) loadAnalysesHistory();
    } catch (err) { console.error(err); }
};

window.deleteComparison = async (id) => {
    if (!confirm("Delete this comparison record?")) return;
    try {
        const res = await fetch(`${API_BASE}/api/features/history/comparisons/${id}`, {
            method: 'DELETE',
            headers: authHeaders()
        });
        if (res.ok) loadComparisonsHistory();
    } catch (err) { console.error(err); }
};


async function deleteConversation(convId) {
    try {
        const res = await fetch(`${API_BASE}/api/chat/${convId}`, {
            method: "DELETE",
            headers: authHeaders()
        });
        if (res.ok) {
            if (currentConversationId === convId) {
                startNewChat();
            }
            loadChatHistory();
        }
    } catch (err) { console.error(err); }
}

async function loadConversation(convId) {
    try {
        const res = await fetch(`${API_BASE}/api/chat/${convId}`, { headers: authHeaders() });
        if (!res.ok) return;
        const conv = await res.json();
        currentConversationId = convId;
        chatMessages.innerHTML = "";
        if (conv.messages) {
            conv.messages.forEach(msg => {
                const isBot = msg.role === "bot" || msg.role === "assistant";
                addMessage(isBot ? "bot" : "user", msg.content, isBot, msg.nutrition_data, msg.health_score, msg.image_urls || []);
            });
        }
        loadChatHistory();
    } catch (err) { console.error(err); }
}

function startNewChat() {
    currentConversationId = null;
    chatMessages.innerHTML = `
        <div class="message bot">
            <div class="message-avatar-v2">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#28a745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
            </div>
            <div class="message-bubble-v2">
                <p><strong>Hello! 👋 I'm your AI Nutrition Expert.</strong></p>
                <p>Ask me anything about nutrition, ingredients, health, or your diet.</p>
            </div>
        </div>`;
    loadChatHistory();
}
newChatBtn?.addEventListener("click", startNewChat);

// ─── Camera Logic ───────────────────────────────────────────────
async function startCamera() {
    try {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: currentFacingMode }
        });
        video.srcObject = stream;
        cameraModal.classList.remove("hidden");
    } catch (err) {
        console.error("Camera error:", err);
        alert("Could not access camera. Please ensure permissions are granted.");
    }
}

window.stopCamera = function() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    cameraModal.classList.add("hidden");
}

switchBtn.addEventListener("click", () => {
    currentFacingMode = currentFacingMode === "user" ? "environment" : "user";
    startCamera();
});

closeCameraBtn.addEventListener("click", stopCamera);

captureBtn.addEventListener("click", async () => {
    const context = canvas.getContext("2d");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    canvas.toBlob(async (blob) => {
        const file = new File([blob], `capture_${Date.now()}.jpg`, { type: "image/jpeg" });
        stopCamera();
        
        if (cameraTarget === "analyzer") {
            handleFile(file);
        } else if (cameraTarget === "compare-a") {
            compareImageA = await uploadForCompare(file, "a");
        } else if (cameraTarget === "compare-b") {
            compareImageB = await uploadForCompare(file, "b");
        } else if (cameraTarget === "chat") {
            handleChatFiles([file]);
        }
    }, "image/jpeg");
});

// ─── Multi-Image Chat Logic ─────────────────────────────────────
chatUploadBtn?.addEventListener("click", () => chatFileInput.click());
chatCameraBtn?.addEventListener("click", () => {
    cameraTarget = "chat";
    startCamera();
});

// Redundant listener removed

btnCameraA?.addEventListener("click", () => {
    cameraTarget = "compare-a";
    startCamera();
});

btnCameraB?.addEventListener("click", () => {
    cameraTarget = "compare-b";
    startCamera();
});

chatFileInput?.addEventListener("change", () => {
    if (chatFileInput.files.length) {
        handleChatFiles(Array.from(chatFileInput.files));
    }
});

async function handleChatFiles(files) {
    for (const file of files) {
        if (selectedChatImages.length >= 3) {
            showToast("Maximum 3 labels allowed", "warning");
            break;
        }
        
        const previewUrl = URL.createObjectURL(file);
        const imgObj = { file, id: null, previewUrl };
        selectedChatImages.push(imgObj);
        renderChatPreviews();
        
        // Resize before upload
        const resizedBlob = await resizeImage(file);
        const formData = new FormData();
        formData.append("file", resizedBlob, file.name);
        
        try {
            const res = await fetch(`${API_BASE}/upload-image`, {
                method: "POST",
                headers: authHeaders(),
                body: formData
            });
            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Upload failed");
            }
            const data = await res.json();
            imgObj.id = data.image_id;
            // Use the server-provided URL (field: image_url from ImageUploadResponse)
            if (data.image_url) {
                imgObj.previewUrl = data.image_url;
            }
            renderChatPreviews(); // Refresh with official URL
        } catch (err) {
            console.error("Upload failed", err);
            showToast(err.message || "Upload failed", "error");
            // Remove the preview if it failed
            selectedChatImages = selectedChatImages.filter(i => i !== imgObj);
            renderChatPreviews();
        }
    }
    chatFileInput.value = "";
}

function renderChatPreviews() {
    chatPreviews.innerHTML = "";
    selectedChatImages.forEach((img, index) => {
        if (!img.previewUrl) return; // Skip undefined
        const div = document.createElement("div");
        div.className = "preview-item";
        div.innerHTML = `
            <img src="${img.previewUrl}" class="clickable-image" onclick="openLightbox('${img.previewUrl}')">
            <button class="remove-p" onclick="removeChatImage(${index})">&times;</button>
        `;
        chatPreviews.appendChild(div);
    });
}

window.removeChatImage = (index) => {
    selectedChatImages.splice(index, 1);
    renderChatPreviews();
};

// ─── Click Lock for File selection ───
let isSelectingFile = false;

// ─── Analyzer Upload ─────────────────────────────────────────────
document.getElementById("btn-analyzer-choose")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopImmediatePropagation();
    if (isSelectingFile) return;
    
    isSelectingFile = true;
    fileInput.value = ""; 
    fileInput.click();
    setTimeout(() => { isSelectingFile = false; }, 2000); 
});

dropZone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone?.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

dropZone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});

document.getElementById("btn-camera-analyzer")?.addEventListener("click", (e) => {
    e.stopPropagation();
    cameraTarget = "analyzer";
    startCamera();
});

fileInput?.addEventListener("change", () => {
    if (fileInput.files.length) {
        handleFile(fileInput.files[0]);
        fileInput.value = ""; // Reset to allow re-uploading
    }
});

window.resetAnalyzer = () => {
    currentImageId = null;
    imagePreview.src = "";
    previewContainer.classList.add("hidden");
    dropZone.classList.remove("hidden");
    document.getElementById("analyzer-result").classList.add("hidden");
};

async function handleFile(file) {
    const loader = document.getElementById("analyzer-loader");
    // Hide previous results immediately when a new file is uploaded
    document.getElementById("analyzer-result")?.classList.add("hidden");
    
    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        previewContainer.classList.remove("hidden");
        dropZone.classList.add("hidden");
        loader?.classList.remove("hidden");
    };
    reader.readAsDataURL(file);

    try {
        // Resize before upload
        const resizedBlob = await resizeImage(file);
        const formData = new FormData();
        formData.append("file", resizedBlob, file.name);
        
        const res = await fetch(`${API_BASE}/upload-image`, {
            method: "POST",
            headers: authHeaders(),
            body: formData,
        });

        const data = await readApiResponse(res);
        if (!res.ok) {
            throw new Error(data.detail || data.message || "Failed to analyze image");
        }

        currentImageId = data.image_id;
        if (data.image_url) imagePreview.src = mediaUrl(data.image_url) || imagePreview.src;
        
        // Build the result HTML but keep it hidden until analysis completes
        displayLabelExtraction(data, true); // pass true to keep hidden
        
        try {
            const vRes = await fetch(`${API_BASE}/api/features/analyze`, {
                method: "POST",
                headers: authHeaders({ "Content-Type": "application/json" }),
                body: JSON.stringify({ image_id: currentImageId })
            });
            if (vRes.ok) appendHealthInsights(await readApiResponse(vRes));
        } catch (e) { console.warn("Health insights skipped", e); }
        
        // Now reveal the results after everything is done
        loader?.classList.add("hidden");
        const resultCont = document.getElementById("analyzer-result");
        resultCont?.classList.remove("hidden");
        setTimeout(() => resultCont?.scrollIntoView({ behavior: "smooth" }), 100);
        
        loadAnalysesHistory();
    } catch (err) { 
        console.error(err); 
        showToast(err.message || "An error occurred during analysis.", "error");
    } finally {
        loader?.classList.add("hidden");
    }
}

// ─── Comparator Listeners ─────────────────────────────────────────
document.getElementById("upload-content-a")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopImmediatePropagation();
    if (isSelectingFile) return;
    isSelectingFile = true;
    const inpA = document.getElementById("compare-file-a");
    if (inpA) inpA.value = "";
    inpA?.click();
    setTimeout(() => { isSelectingFile = false; }, 2000);
});
document.getElementById("upload-content-b")?.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopImmediatePropagation();
    if (isSelectingFile) return;
    isSelectingFile = true;
    const inpB = document.getElementById("compare-file-b");
    if (inpB) inpB.value = "";
    inpB?.click();
    setTimeout(() => { isSelectingFile = false; }, 2000);
});

document.getElementById("btn-camera-a")?.addEventListener("click", (e) => {
    e.stopPropagation();
    cameraTarget = "compare-a";
    startCamera();
});
document.getElementById("btn-camera-b")?.addEventListener("click", (e) => {
    e.stopPropagation();
    cameraTarget = "compare-b";
    startCamera();
});

document.getElementById("compare-file-a").addEventListener("change", async (e) => {
    if (e.target.files.length) {
        const id = await uploadForCompare(e.target.files[0], "a");
        compareImageA = id;
        updateCompareBtn();
        e.target.value = "";
    }
});
document.getElementById("compare-file-b").addEventListener("change", async (e) => {
    if (e.target.files.length) {
        const id = await uploadForCompare(e.target.files[0], "b");
        compareImageB = id;
        updateCompareBtn();
        e.target.value = "";
    }
});

async function uploadForCompare(file, slot) {
    const loader = document.getElementById(`loader-compare-${slot}`);
    const reader = new FileReader();
    
    // Show preview and loader immediately
    reader.onload = (e) => {
        document.getElementById(`compare-img-${slot}`).src = e.target.result;
        document.getElementById(`compare-preview-${slot}`).classList.remove("hidden");
        document.getElementById(`upload-content-${slot}`)?.classList.add("hidden");
        loader?.classList.remove("hidden");
    };
    reader.readAsDataURL(file);

    try {
        // Resize before upload
        const resizedBlob = await resizeImage(file);
        const formData = new FormData();
        formData.append("file", resizedBlob, file.name);

        const res = await fetch(`${API_BASE}/upload-image`, {
            method: "POST",
            headers: authHeaders(),
            body: formData
        });
        if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Upload failed");
        }
        const data = await res.json();
        return data.image_id;
    } catch (err) { 
        showToast(err.message || "Upload failed", "error");
        resetCompare(slot);
        return null; 
    } finally {
        loader?.classList.add("hidden");
    }
}

window.resetCompare = (slot) => {
    if (slot === 'a') compareImageA = null;
    else compareImageB = null;
    document.getElementById(`compare-preview-${slot}`).classList.add("hidden");
    document.getElementById(`upload-content-${slot}`)?.classList.remove("hidden");
    updateCompareBtn();
};

function updateCompareBtn() {
    document.getElementById("compare-btn").disabled = !(compareImageA && compareImageB);
}

document.getElementById("compare-btn").addEventListener("click", async () => {
    const btn = document.getElementById("compare-btn");
    btn.disabled = true;
    btn.innerHTML = "⚡ Comparing...";
    
    try {
        const res = await fetch(`${API_BASE}/api/features/compare`, {
            method: "POST",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ image_id_a: compareImageA, image_id_b: compareImageB })
        });
        const data = await res.json();
        displayCompareResult(data);
        document.getElementById("btn-discuss-compare")?.classList.remove("hidden");
        loadComparisonsHistory();
    } catch (err) {
        console.error(err);
    } finally {
        btn.disabled = false;
        btn.innerHTML = "⚡ Run Comparison";
    }
});

// ─── Chat Logic ──────────────────────────────────────────────────
chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    let question = questionInput.value.trim();
    const imageIds = selectedChatImages.map(img => img.id).filter(id => id !== null);

    if (!question) {
        if (imageIds.length > 0) {
            question = "Please analyze these nutrition labels and provide insights.";
        } else {
            return;
        }
    }

    const currentPreviews = selectedChatImages.map(img => img.previewUrl);
    addMessage("user", question, false, null, null, currentPreviews);
    saveChatMessage("user", question, currentPreviews);
    
    questionInput.value = "";
    questionInput.style.height = 'auto'; // Reset height
    
    selectedChatImages = [];
    renderChatPreviews();

    const loaderId = addLoader();
    try {
        const res = await fetch(`${API_BASE}/ask`, {
            method: "POST",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ 
                question, 
                image_id: imageIds[0] || null, 
                image_ids: imageIds,
                conversation_id: currentConversationId,
            })
        });
        const data = await res.json();
        removeLoader(loaderId);
        
        const answer = data.answer || data.explanation || "I couldn't process that. Please try again.";
        const score = data.health_score || 85;
        // PASS PREVIEWS TO BOT MESSAGE SO IT CAN SHOW THEM IN THE ANALYSIS CARD
        addMessage("bot", marked.parse(answer), true, data.ocr_data, score, currentPreviews);
        
        await saveChatMessage("bot", answer, [], data.ocr_data, score);
    } catch (err) {
        removeLoader(loaderId);
        addMessage("bot", "❌ Error processing request. Check connection.");
    }
});

// ─── Helpers ─────────────────────────────────────────────────────
function addMessage(role, text, isHtml = false, nutritionData = null, score = null, imageUrls = []) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    
    let avatarHtml = "";
    if (role === "bot") {
        avatarHtml = `<div class="message-avatar-v2">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#28a745" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
        </div>`;
    } else {
        const initials = userProfile ? userProfile.name[0] : "👤";
        avatarHtml = `<div class="message-avatar-v2" style="background:#4f46e5; color:white; font-weight:700; font-size:0.8rem;">${initials}</div>`;
    }
    
    let imagesContent = "";
    if (imageUrls && imageUrls.length > 0) {
        imagesContent = `<div class="message-images" style="display: flex; gap: 0.5rem; margin-bottom: 0.75rem; overflow-x: auto; padding-bottom: 5px;">`;
        imageUrls.forEach(url => {
            if (!url) return;
            const fullUrl = (url.startsWith('http') || url.startsWith('data:')) ? url : `${API_BASE}${url}`;
            imagesContent += `<img src="${fullUrl}" class="clickable-image" onclick="openLightbox('${fullUrl}')" style="height: 100px; max-width: 200px; border-radius: 8px; border: 1px solid var(--border-subtle); object-fit: cover; background: #000; cursor: pointer;">`;
        });
        imagesContent += `</div>`;
    }

    let richContent = "";
    if (nutritionData && role === "bot") {
        const ratingClass = score >= 80 ? "badge-healthy" : score >= 50 ? "badge-caution" : "badge-unhealthy";
        const ratingLabel = score >= 80 ? "Healthy" : score >= 50 ? "Caution" : "Unhealthy";
        
        let nutritionHtml = "";
        const coreNutrients = [
            { key: 'calories', label: 'Calories' },
            { key: 'protein', label: 'Protein' },
            { key: 'carbohydrates', label: 'Carbs' },
            { key: 'total_fat', label: 'Fat' },
            { key: 'sugar', label: 'Sugar' },
            { key: 'vitamin_a', label: 'Vit A' },
            { key: 'vitamin_c', label: 'Vit C' },
            { key: 'vitamin_d', label: 'Vit D' },
            { key: 'calcium', label: 'Calcium' },
            { key: 'iron', label: 'Iron' }
        ];

        // Find max value to scale the bars relative to each other
        const maxVal = Math.max(...coreNutrients.map(n => {
            const val = nutritionData[n.key] || "N/A";
            const match = typeof val === 'string' ? val.match(/[\d.]+/) : null;
            return match ? parseFloat(match[0]) : 0;
        }));

        coreNutrients.forEach(n => {
            const val = nutritionData[n.key] || "N/A";
            const numMatch = typeof val === 'string' ? val.match(/[\d.]+/) : null;
            const numVal = numMatch ? parseFloat(numMatch[0]) : 0;
            let percent = maxVal > 0 ? (numVal / maxVal) * 100 : 0;
            if (percent > 100) percent = 100;
            if (isNaN(percent)) percent = 0;

            if (val === "N/A" && (n.key.startsWith("vitamin") || n.key === "calcium" || n.key === "iron")) return; // skip missing optional nutrients

            nutritionHtml += `
                <div class="nutrient-stat-card" style="padding: 0.5rem; border-radius: 8px; background: rgba(255,255,255,0.03); text-align:center;">
                    <div style="font-size: 0.6rem; color: var(--text-muted); text-transform: uppercase;">${n.label}</div>
                    <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-main);">${val}</div>
                    <div class="progress-bar-container" style="width: 100%; background: rgba(255,255,255,0.1); height: 4px; border-radius: 2px; margin-top: 4px; overflow: hidden;">
                        <div class="progress-bar-fill" style="width: ${percent}%; background: var(--accent-primary, #28a745); height: 100%; transition: width 0.3s ease;"></div>
                    </div>
                </div>
            `;
        });

        richContent = `
            <div class="analysis-card" style="margin-bottom: 1rem; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 1rem;">
                <div style="flex: 1; margin-bottom: 0.75rem;">
                    <div style="font-weight: 600; font-size: 0.9rem;">Product Analysis</div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: 0.5rem;">
                    ${nutritionHtml}
                </div>
                <div class="nutrition-legend" style="display: flex; gap: 0.75rem; justify-content: center; margin-top: 0.75rem; font-size: 0.65rem; color: var(--text-muted);">
                    <div style="display: flex; align-items: center; gap: 3px;">
                        <div style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-primary, #28a745);"></div>
                        <span>Optimal</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 3px;">
                        <div style="width: 8px; height: 8px; border-radius: 50%; background: #ffc107;"></div>
                        <span>Moderate</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 3px;">
                        <div style="width: 8px; height: 8px; border-radius: 50%; background: #dc3545;"></div>
                        <span>High</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    const finalContent = (text && text.length > 0) ? `
        <div class="markdown-body">${isHtml ? text : escapeHtml(text)}</div>
    ` : "";

    div.innerHTML = `
        ${avatarHtml}
        <div class="message-bubble-v2">
            ${imagesContent}
            ${richContent}
            ${finalContent}
        </div>
    `;
    
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoader() {
    const id = "loader-" + Date.now();
    const div = document.createElement("div");
    div.className = "message bot";
    div.id = id;
    div.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-bubble">Thinking...</div>
    `;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return id;
}

function removeLoader(id) { document.getElementById(id)?.remove(); }



function displayLabelExtraction(uploadData, keepHidden) {
    const cont = document.getElementById("analyzer-result");
    const rawOcr = uploadData.ocr_text || "No text detected.";
    const cleanedOcr = uploadData.cleaned_ocr_text || "";
    const nut = uploadData.nutrition_data || {};
    
    let nutritionHtml = "";
    if (Object.keys(nut).length > 0 && !nut.error) {
        const coreNutrients = [
            { key: 'calories', label: 'Calories' },
            { key: 'protein', label: 'Protein' },
            { key: 'carbohydrates', label: 'Carbs' },
            { key: 'total_fat', label: 'Total Fat' },
            { key: 'sugar', label: 'Sugar' },
            { key: 'sodium', label: 'Sodium' },
            { key: 'vitamin_a', label: 'Vit A' },
            { key: 'vitamin_c', label: 'Vit C' },
            { key: 'vitamin_d', label: 'Vit D' },
            { key: 'calcium', label: 'Calcium' },
            { key: 'iron', label: 'Iron' }
        ];

        // Find max value
        const maxVal = Math.max(...coreNutrients.map(n => {
            const val = formatNutrientValue(nut[n.key]);
            const match = typeof val === 'string' ? val.match(/[\d.]+/) : null;
            return match ? parseFloat(match[0]) : (typeof val === 'number' ? val : 0);
        }));

        coreNutrients.forEach(n => {
            const val = formatNutrientValue(nut[n.key]);
            if ((val === "—" || val === "N/A") && (n.key.startsWith("vitamin") || n.key === "calcium" || n.key === "iron")) return;

            const numMatch = typeof val === 'string' ? val.match(/[\d.]+/) : null;
            const numVal = numMatch ? parseFloat(numMatch[0]) : (typeof val === 'number' ? val : 0);
            let percent = maxVal > 0 ? (numVal / maxVal) * 100 : 0;
            if (percent > 100) percent = 100;
            if (isNaN(percent)) percent = 0;

            let barColor = "var(--accent-primary, #28a745)";
            // Check original values for color coding (high sugar/sodium)
            let absPercent = 0;
            if (n.key === 'sugar') absPercent = (numVal / 50) * 100;
            else if (n.key === 'sodium') absPercent = (numVal / 2300) * 100;
            else if (n.key === 'total_fat') absPercent = (numVal / 78) * 100;

            if ((n.key === 'sugar' || n.key === 'sodium' || n.key === 'total_fat') && absPercent > 20) {
                barColor = absPercent > 50 ? "#dc3545" : "#ffc107";
            }

            nutritionHtml += `
                <div class="nutrient-stat-card" style="display: flex; flex-direction: column; justify-content: center; padding: 10px; border-radius: 8px; background: var(--bg-card); border: 1px solid var(--border-subtle); text-align: center;">
                    <div class="nutrient-label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">${n.label}</div>
                    <div class="nutrient-value" style="font-size: 1.1rem; font-weight: 700; margin-bottom: 4px; color: var(--text-main);">${val}</div>
                    <div class="progress-bar-container" style="width: 100%; background: var(--border-subtle, #e0e0e0); height: 6px; border-radius: 3px; overflow: hidden; margin-top: auto;">
                        <div class="progress-bar-fill" style="width: ${percent}%; background: ${barColor}; height: 100%; transition: width 0.3s ease;"></div>
                    </div>
                </div>
            `;
        });
        if (nutritionHtml) {
            nutritionHtml = `
                <hr class="section-divider">
                <h3 class="section-heading">📊 Nutrition Analysis</h3>
                <div class="nutrition-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 1rem; margin-bottom: 0.5rem;">
                    ${nutritionHtml}
                </div>
                <div class="nutrition-legend" style="display: flex; gap: 1rem; justify-content: center; margin-bottom: 1.5rem; font-size: 0.75rem; color: var(--text-muted);">
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: var(--accent-primary, #28a745);"></div>
                        <span>Optimal</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: #ffc107;"></div>
                        <span>Moderate</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: #dc3545;"></div>
                        <span>High (Limit)</span>
                    </div>
                </div>
            `;
        }
    }
    
    // Format OCR text as a paragraph with preserved line breaks but wrapping like text
    const formatAsParagraph = (text) => {
        return `<p class="ocr-paragraph" style="white-space: pre-wrap; font-family: var(--font-main); line-height: 1.6; color: var(--text-main); background: var(--bg-main); padding: 1rem; border-radius: 8px; border: 1px solid var(--border-subtle);">${escapeHtml(text)}</p>`;
    };
    
    cont.innerHTML = `
        <div class="label-extraction-result card">
            <h3 class="section-heading">Extracted OCR Text</h3>
            ${formatAsParagraph(rawOcr)}
            ${cleanedOcr && cleanedOcr !== rawOcr ? `<h4 class="section-subheading" style="margin-top: 1rem;">Cleaned OCR</h4>${formatAsParagraph(cleanedOcr)}` : ""}
            ${nutritionHtml}
            <hr class="section-divider">
            <div id="health-insights-slot"></div>
            <button class="btn-compare" style="margin-top:1.5rem;width:100%" onclick="switchToChat('analyze')">💬 Ask Follow-up Questions</button>
        </div>`;
    cont.classList.remove("hidden");
    if (!keepHidden) {
        setTimeout(() => cont.scrollIntoView({ behavior: "smooth" }), 100);
    } else {
        // Keep hidden - caller will reveal after full analysis
        cont.classList.add("hidden");
    }
}

function appendHealthInsights(vData) {
    const slot = document.getElementById("health-insights-slot");
    if (!slot || !vData?.verdict) return;
    const t = typeof vData.verdict === "string" ? vData.verdict : vData.verdict.verdict || "";
    if (!t) return;
    slot.innerHTML = `<hr class="section-divider"><h3 class="section-heading">💡 Health Insights</h3><div class="markdown-body">${marked.parse(t)}</div>`;
}

function displayVerdict(verdict) {
    const cont = document.getElementById("verdict-result");
    document.getElementById("verdict-content").innerHTML = marked.parse(verdict);
    cont.classList.remove("hidden");
    document.getElementById("verdict-placeholder")?.classList.add("hidden");
    cont.scrollIntoView({ behavior: 'smooth' });
}

function displayAnalysisReport(data, vData) {
    const cont = document.getElementById("analyzer-result");
    const nut = data.nutrition_data || {};
    const verdict = vData?.verdict || {};
    
    const score = data.health_score || 85; 
    const ratingClass = score >= 80 ? "badge-healthy" : score >= 50 ? "badge-caution" : "badge-unhealthy";
    const ratingLabel = score >= 80 ? "Healthy" : score >= 50 ? "Caution" : "Unhealthy";

    let nutritionHtml = "";
    const coreNutrients = [
        { key: 'calories', label: 'Calories', max: 2000 },
        { key: 'protein', label: 'Protein', max: 50 },
        { key: 'carbohydrates', label: 'Carbs', max: 275 },
        { key: 'total_fat', label: 'Total Fat', max: 78 },
        { key: 'sugar', label: 'Sugar', max: 50 },
        { key: 'sodium', label: 'Sodium', max: 2300 },
        { key: 'vitamin_a', label: 'Vit A', max: 900 },
        { key: 'vitamin_c', label: 'Vit C', max: 90 },
        { key: 'vitamin_d', label: 'Vit D', max: 20 },
        { key: 'calcium', label: 'Calcium', max: 1300 },
        { key: 'iron', label: 'Iron', max: 18 }
    ];

    coreNutrients.forEach(n => {
        const val = formatNutrientValue(nut[n.key]);
        if ((val === "—" || val === "N/A") && (n.key.startsWith("vitamin") || n.key === "calcium" || n.key === "iron")) return; // Hide missing vitamins

        const numMatch = typeof val === 'string' ? val.match(/[\d.]+/) : null;
        const numVal = numMatch ? parseFloat(numMatch[0]) : (typeof val === 'number' ? val : 0);
        let percent = n.max ? (numVal / n.max) * 100 : 0;
        if (percent > 100) percent = 100;
        if (isNaN(percent)) percent = 0;

        let barColor = "var(--accent-primary, #28a745)";
        if ((n.key === 'sugar' || n.key === 'sodium' || n.key === 'total_fat') && percent > 20) {
            barColor = percent > 50 ? "#dc3545" : "#ffc107"; // red or yellow
        }

        nutritionHtml += `
            <div class="nutrient-stat-card" style="display: flex; flex-direction: column; justify-content: center;">
                <div class="nutrient-label">${n.label}</div>
                <div class="nutrient-value" style="margin-bottom: 4px;">${val}</div>
                <div style="display: flex; align-items: center; gap: 6px; margin-top: auto;">
                    <div class="progress-bar-container" style="flex: 1; background: var(--border-subtle, #e0e0e0); height: 6px; border-radius: 3px; overflow: hidden;">
                        <div class="progress-bar-fill" style="width: ${percent}%; background: ${barColor}; height: 100%; transition: width 0.3s ease;"></div>
                    </div>
                    <span style="font-size: 0.65rem; color: var(--text-muted); font-weight: 600;">${Math.round(percent)}% DV</span>
                </div>
            </div>
        `;
    });

    const explanation = typeof verdict === 'string' ? verdict : (verdict.explanation || verdict.verdict || "No detailed analysis available.");

    cont.innerHTML = `
        <div class="analyzer-grid-container">
            <!-- Left: Analysis Report -->
            <div class="report-section">
                <div class="verdict-header" style="margin-bottom: 1.5rem; border:none; padding:0;">
                    <div>
                        <h4 style="margin: 0; font-size: 1.2rem;">Analysis Report</h4>
                    </div>
                </div>
                <div class="nutrition-grid" style="margin-bottom: 1rem;">
                    ${nutritionHtml}
                </div>
                <div class="nutrition-legend" style="display: flex; gap: 1rem; justify-content: center; font-size: 0.75rem; color: var(--text-muted); margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: var(--accent-primary, #28a745);"></div>
                        <span>Optimal</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: #ffc107;"></div>
                        <span>Moderate</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <div style="width: 10px; height: 10px; border-radius: 50%; background: #dc3545;"></div>
                        <span>High (Limit)</span>
                    </div>
                </div>
            </div>

            <!-- Right: AI Insights -->
            <div class="insights-section">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-main); display: flex; align-items: center; gap: 0.5rem;">
                    <span>💡</span> AI Insights & Recommendations
                </h4>
                <div class="markdown-body" style="font-size: 0.95rem; color: var(--text-muted); line-height: 1.6; flex: 1;">
                    ${marked.parse(explanation)}
                </div>
                <button class="btn-compare" style="margin-top: 1.5rem; width: 100%;" onclick="switchToChat('analyze')">
                    💬 Ask Follow-up Questions
                </button>
            </div>
        </div>
    `;
    cont.classList.remove("hidden");
    setTimeout(() => {
        cont.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

function displayCompareResult(data) {
    const cont = document.getElementById("compare-result");
    const a = data.product_a || {};
    const b = data.product_b || {};

    let tableHtml = `
        <div class="comparison-table-wrapper" style="margin-bottom: 2rem; overflow-x: auto;">
            <table class="nutrition-table" style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: var(--bg-card); border-bottom: 2px solid var(--accent-primary);">
                        <th style="padding: 12px; text-align: left; color: var(--accent-primary);">Nutrient</th>
                        <th style="padding: 12px; text-align: center; color: var(--badge-a);">Product A</th>
                        <th style="padding: 12px; text-align: center; color: var(--badge-b);">Product B</th>
                    </tr>
                </thead>
                <tbody>
    `;

    (data.comparison_table || []).forEach(row => {
        const styleA = row.winner === 'A' ? "color: #10b981; font-weight: 600;" : "";
        const styleB = row.winner === 'B' ? "color: #10b981; font-weight: 600;" : "";
        
        tableHtml += `
            <tr style="border-bottom: 1px solid var(--border-subtle);">
                <td style="padding: 10px; font-weight: 500;">${row.nutrient}</td>
                <td style="padding: 10px; text-align: center; ${styleA}">${row.product_a}</td>
                <td style="padding: 10px; text-align: center; ${styleB}">${row.product_b}</td>
            </tr>
        `;
    });

    tableHtml += `</tbody></table></div>`;

    cont.innerHTML = `
        <div class="verdict-card">
            <h3 class="section-title">📊 Side-by-Side Comparison</h3>
            ${tableHtml}
            <h3 class="section-title">✨ AI Analysis</h3>
            <div class="markdown-body">${marked.parse(data.ai_verdict || "Analysis unavailable.")}</div>
            <button class="btn-compare" style="margin-top: 1.5rem; width: 100%;" onclick="switchToChat('compare')">
                💬 Ask Follow-up Questions
            </button>
        </div>
    `;
    cont.classList.remove("hidden");
    cont.scrollIntoView({ behavior: 'smooth' });
}

function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
}

async function saveChatMessage(role, content, imageUrls = [], nutritionData = null, healthScore = null) {
    try {
        const cleanUrls = (imageUrls || []).filter(url => !!url);
        const urlParams = currentConversationId ? `?conv_id=${currentConversationId}` : "";
        const res = await fetch(`${API_BASE}/api/chat/save${urlParams}`, {
            method: "POST",
            headers: authHeaders({ "Content-Type": "application/json" }),
            body: JSON.stringify({ 
                role, 
                content,
                image_urls: cleanUrls,
                nutrition_data: nutritionData,
                health_score: healthScore
            })
        });
        if (res.ok) {
            const data = await res.json();
            if (!currentConversationId) {
                currentConversationId = data.conversation_id;
                loadChatHistory();
            }
        }
    } catch (err) {}
}

function showToast(msg, type = "info") {
    // Simple alert for now, can be improved to a real toast
    alert(msg);
}

function logout() { localStorage.removeItem("token"); window.location.href = "signin.html"; }

// ─── Image Resizing Utility ──────────────────────────────────────
async function resizeImage(file, maxWidth = 1200, maxHeight = 1200) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target.result;
            img.onload = () => {
                const canvas = document.createElement('canvas');
                let width = img.width;
                let height = img.height;

                if (width > height) {
                    if (width > maxWidth) {
                        height *= maxWidth / width;
                        width = maxWidth;
                    }
                } else {
                    if (height > maxHeight) {
                        width *= maxHeight / height;
                        height = maxHeight;
                    }
                }

                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                canvas.toBlob((blob) => {
                    resolve(blob || file);
                }, file.type, 0.85); // 0.85 quality
            };
        };
    });
}

// ─── Lightbox Logic ──────────────────────────────────────────────
window.openLightbox = (src) => {
    const lightbox = document.getElementById("lightbox");
    const lightboxImg = document.getElementById("lightbox-img");
    if (lightbox && lightboxImg) {
        lightboxImg.src = src;
        lightbox.classList.add("active");
        document.body.style.overflow = "hidden"; // Prevent scrolling
    }
};

window.closeLightbox = () => {
    const lightbox = document.getElementById("lightbox");
    if (lightbox) {
        lightbox.classList.remove("active");
        document.body.style.overflow = ""; // Restore scrolling
    }
};

// ─── Navigation Helper ───────────────────────────────────────────
async function switchToChat(source = 'general') {
    const chatPill = document.querySelector('.nav-pill[data-target="chat-app"]');
    if (chatPill) {
        // Clear existing context if switching for a new reason
        selectedChatImages = [];
        
        if (source === 'analyze' && currentImageId) {
            // Find the image source from the preview
            const previewSrc = document.getElementById("image-preview").src;
            selectedChatImages.push({ id: currentImageId, previewUrl: previewSrc });
        } else if (source === 'compare' && compareImageA && compareImageB) {
            const srcA = document.getElementById("compare-img-a").src;
            const srcB = document.getElementById("compare-img-b").src;
            selectedChatImages.push({ id: compareImageA, previewUrl: srcA });
            selectedChatImages.push({ id: compareImageB, previewUrl: srcB });
        }
        
        renderChatPreviews();
        chatPill.click();
        
        // Update title manually if needed (since pill click might overwrite it)
        setTimeout(() => {
            const title = document.getElementById('chat-title');
            if (title) {
                if (source === 'analyze') title.textContent = '🔬 Analysis Expert';
                else if (source === 'compare') title.textContent = '⚖️ Comparison Expert';
            }
        }, 50);

        // No auto-submit as per user request
    }
}

// ─── Initialization ──────────────────────────────────────────────
async function init() {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "signin.html";
        return;
    }

    try {
        await loadUserProfile();
        await loadChatHistory();
        await loadAnalysesHistory();
        await loadComparisonsHistory();
    } catch (err) {
        console.error("Initialization failed:", err);
    }
}

// Start the app
init();

async function showAnalyzerResult(record) {
    // Switch to analyzer tab if not active
    document.querySelector('[data-target="analyze-app"]').click();
    
    // Set preview image
    imagePreview.src = `${API_BASE}${record.image_url}`;
    previewContainer.classList.remove("hidden");
    dropZone.classList.add("hidden");
    
    // Mocking the 'data' structure expected by displayAnalysisReport
    const data = {
        nutrition_data: record.nutrition_data,
        health_score: record.health_score,
        verdict: record.health_verdict
    };
    displayAnalysisReport(data, data);
}

async function showComparisonResult(record) {
    // Switch to comparator tab
    document.querySelector('[data-target="compare-app"]').click();
    
    // Set previews
    document.getElementById('compare-img-a').src = `${API_BASE}${record.image_url_a}`;
    document.getElementById('compare-img-b').src = `${API_BASE}${record.image_url_b}`;
    document.getElementById('compare-preview-a').classList.remove("hidden");
    document.getElementById('compare-preview-b').classList.remove("hidden");
    document.getElementById('upload-content-a').classList.add("hidden");
    document.getElementById('upload-content-b').classList.add("hidden");
    
    const data = {
        product_a: record.data_a,
        product_b: record.data_b,
        comparison_table: record.comparison_table,
        ai_verdict: record.ai_verdict,
        winner: record.winner
    };
    displayCompareResult(data);
}
