/**
 * NutritionVQA-RAG — Frontend Application Logic
 * Handles image upload, chat, API communication, chat history,
 * daily intake, product comparison, health verdict, and gamification.
 */

var API_BASE = window.location.origin;

// ─── DOM refs ───────────────────────────────────────────────────
const dropZone        = document.getElementById("drop-zone");
const fileInput       = document.getElementById("file-input");
const previewContainer= document.getElementById("preview-container");
const imagePreview    = document.getElementById("image-preview");
const removeImageBtn  = document.getElementById("remove-image");
const ocrResult       = document.getElementById("ocr-result");
const ocrText         = document.getElementById("ocr-text");
const chatMessages    = document.getElementById("chat-messages");
const chatForm        = document.getElementById("chat-form");
const questionInput   = document.getElementById("question-input");
const sendBtn         = document.getElementById("send-btn");
const historyList     = document.getElementById("history-list");
const newChatBtn      = document.getElementById("new-chat-btn");
const chatTitle       = document.getElementById("chat-title");

let currentImageId = null;  // Stores the uploaded image reference
let currentConversationId = null;
let userProfile = null;

// ── Compare State ──
let compareImageA = null;
let compareImageB = null;

// ─── Initialization ──────────────────────────────────────────────
console.log("🚀 app.js loading...");

async function init() {
    console.log("🏁 init() starting...");
    const token = localStorage.getItem("token");
    console.log("🔑 Token found:", !!token);
    
    if (!token) {
        console.warn("🚫 No token, redirecting to signin...");
        window.location.href = "signin.html";
        return;
    }

    try {
        console.log("👤 Loading profile...");
        await loadUserProfile();
        console.log("💬 Loading history...");
        await loadChatHistory();
        console.log("✅ Initialization complete!");
    } catch (err) {
        console.error("❌ Initialization failed:", err);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}

async function loadUserProfile() {
    console.log("📡 Fetching /api/auth/me...");
    try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });
        console.log("📥 Profile response status:", res.status);
        if (res.ok) {
            userProfile = await res.json();
            console.log("👤 Profile loaded:", userProfile.name);
            document.getElementById("user-name").textContent = userProfile.name;
            const initials = userProfile.name.split(" ").map(n => n[0]).join("").toUpperCase();
            document.getElementById("user-initials").textContent = initials;
        } else {
            console.error("🚫 Profile load failed (not OK). Logging out.");
            logout();
        }
    } catch (err) {
        console.error("❌ Profile fetch error:", err);
    }
}

async function loadChatHistory() {
    console.log("📡 Fetching /api/chat/history...");
    try {
        const res = await fetch(`${API_BASE}/api/chat/history`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });
        console.log("📥 History response status:", res.status);
        if (res.ok) {
            const history = await res.json();
            console.log("📜 History items:", history.length);
            renderHistoryList(history);
        }
    } catch (err) {
        console.error("❌ History fetch error:", err);
    }
}

function renderHistoryList(history) {
    historyList.innerHTML = "";
    if (history.length === 0) {
        historyList.innerHTML = '<p class="empty-history">No past chats found.</p>';
        return;
    }

    history.forEach(conv => {
        const item = document.createElement("div");
        item.className = "history-item";
        if (conv._id === currentConversationId) item.classList.add("active");
        
        const titleSpan = document.createElement("span");
        titleSpan.className = "history-title";
        titleSpan.textContent = conv.title || "Untitled Chat";
        titleSpan.onclick = () => loadConversation(conv._id);
        
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "btn-delete-conv";
        deleteBtn.innerHTML = "🗑️";
        deleteBtn.title = "Delete Chat";
        deleteBtn.onclick = (e) => {
            e.stopPropagation();
            deleteConversation(conv._id);
        };
        
        item.appendChild(titleSpan);
        item.appendChild(deleteBtn);
        historyList.appendChild(item);
    });
}

async function deleteConversation(id) {
    if (!confirm("Are you sure you want to delete this chat?")) return;
    try {
        const res = await fetch(`${API_BASE}/api/chat/${id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });
        if (res.ok) {
            if (currentConversationId === id) {
                newChatBtn.click(); // Reset UI if current chat deleted
            }
            loadChatHistory(); // Refresh sidebar
        }
    } catch (err) {
        console.error("Delete failed", err);
    }
}

async function loadConversation(id) {
    currentConversationId = id;
    try {
        const res = await fetch(`${API_BASE}/api/chat/${id}`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });
        if (res.ok) {
            const conv = await res.json();
            chatMessages.innerHTML = "";
            conv.messages.forEach(msg => {
                // If message has image_id or metadata with image_url, show it
                const imgUrl = msg.metadata ? msg.metadata.image_url : null;
                addMessage(msg.role, msg.content, msg.role === "bot", imgUrl);
            });
            chatTitle.textContent = `💬 ${conv.title}`;
            // Update active states in sidebar
            document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
            loadChatHistory(); // Refresh list to set active
        }
    } catch (err) {
        console.error("Failed to load conversation", err);
    }
}

newChatBtn.onclick = () => {
    currentConversationId = null;
    currentImageId = null;
    chatMessages.innerHTML = `
        <div class="message bot">
            <div class="message-bubble">
                <p>Hello! 👋 Upload a nutrition label or ask me any nutrition question to give you an
                    accurate, step-by-step answer.</p>
            </div>
        </div>
    `;
    chatTitle.textContent = "💬 Ask About Nutrition";
    ocrResult.classList.add("hidden");
    previewContainer.classList.add("hidden");
    dropZone.classList.remove("hidden");
    // Hide verdict and language
    document.getElementById("verdict-result").classList.add("hidden");
    document.getElementById("language-badge").classList.add("hidden");
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
};

// ─── Drop Zone ───────────────────────────────────────────────────
dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => {
    if (fileInput.files.length) handleFile(fileInput.files[0]);
});

removeImageBtn.addEventListener("click", () => {
    currentImageId = null;
    previewContainer.classList.add("hidden");
    ocrResult.classList.add("hidden");
    document.getElementById("serving-size-container").classList.add("hidden");
    document.getElementById("serving-size-container").innerHTML = "";
    document.getElementById("verdict-result").classList.add("hidden");
    document.getElementById("language-badge").classList.add("hidden");
    dropZone.classList.remove("hidden");
    fileInput.value = "";
});

// ─── File Handling (Enhanced with new features) ──────────────────
async function handleFile(file) {
    const allowed = ["image/png", "image/jpeg", "image/jpg", "image/webp"];
    if (!allowed.includes(file.type)) {
        addMessage("bot", "⚠️ Please upload a valid image (PNG, JPG, or WEBP).");
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        addMessage("bot", "⚠️ File is too large. Maximum size is 10 MB.");
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        imagePreview.src = e.target.result;
        previewContainer.classList.remove("hidden");
        dropZone.classList.add("hidden");
    };
    reader.readAsDataURL(file);

    addMessage("bot", "🔄 Processing your image…");

    try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await fetch(`${API_BASE}/upload-image`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` },
            body: formData,
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Upload failed");
        }
        const data = await res.json();
        currentImageId = data.image_id;
        const imageUrl = data.image_url;

        displayNutritionData(data.nutrition_data);
        ocrText.textContent = data.ocr_text;
        ocrResult.classList.remove("hidden");
        
        // Show detected language
        if (data.detected_language) {
            document.getElementById("detected-lang").textContent = data.detected_language;
            document.getElementById("language-badge").classList.remove("hidden");
        }

        // Show health verdict
        if (data.health_verdict) {
            displayVerdict(data.health_verdict);
        }
        
        // Add image to chat as a user message
        addMessage("user", "📷 Uploaded nutrition label", false, imageUrl);
        
        // Save the image message to history
        const imgMsg = { 
            role: "user", 
            content: "📷 Uploaded nutrition label", 
            timestamp: new Date().toISOString(), 
            image_id: currentImageId,
            metadata: { image_url: imageUrl }
        };
        await saveToHistory(imgMsg);

        addMessage("bot", `✅ Image processed! I extracted the nutrition data. Go ahead and ask me a question about it.`);
    } catch (err) {
        console.error(err);
        addMessage("bot", `❌ Could not process the image: ${err.message}`);
    }
}

function displayVerdict(verdict) {
    const container = document.getElementById("verdict-result");
    const content = document.getElementById("verdict-content");
    
    if (typeof verdict === "object") {
        const text = verdict.verdict || verdict.message || JSON.stringify(verdict);
        content.innerHTML = marked.parse(text);
    } else {
        content.innerHTML = marked.parse(verdict);
    }
    container.classList.remove("hidden");
}



function displayNutritionData(nutrition) {
    const grid = document.getElementById("nutrition-grid");
    const servingContainer = document.getElementById("serving-size-container");
    grid.innerHTML = "";
    servingContainer.innerHTML = "";
    
    const items = Object.entries(nutrition).filter(([k]) => k !== "raw_text" && k !== "serving_size");
    const servingSize = nutrition.serving_size;
    
    if (items.length === 0 && !servingSize) {
        grid.innerHTML = "<p class='card-desc'>No clear nutrition metrics identified by regex, but I've kept the raw text for AI analysis.</p>";
        servingContainer.classList.add("hidden");
        return;
    }

    items.forEach(([key, value]) => {
        const item = document.createElement("div");
        item.className = "nutrition-item";
        const labelText = key.replace(/_/g, " ");
        item.innerHTML = `
            <span class="nutrition-label">${labelText}</span>
            <span class="nutrition-value">${value}</span>
        `;
        grid.appendChild(item);
    });

    if (servingSize) {
        servingContainer.innerHTML = `
            <details class="raw-data">
                <summary>View Serving Size Details</summary>
                <div class="serving-size-card" style="display:block; text-align:left;">
                    <span class="nutrition-label">Serving Size Info</span>
                    <p class="serving-value" style="text-align:left; margin-top:var(--sp-2);">${servingSize}</p>
                </div>
            </details>
        `;
        servingContainer.classList.remove("hidden");
    } else {
        servingContainer.classList.add("hidden");
    }
}








// ─── Product Comparator ─────────────────────────────────────────
const compareDropA = document.getElementById("compare-drop-a");
const compareDropB = document.getElementById("compare-drop-b");
const compareFileA = document.getElementById("compare-file-a");
const compareFileB = document.getElementById("compare-file-b");
const compareBtn   = document.getElementById("compare-btn");

compareDropA.addEventListener("click", () => compareFileA.click());
compareDropB.addEventListener("click", () => compareFileB.click());

compareFileA.addEventListener("change", async () => {
    if (compareFileA.files.length) {
        compareImageA = await uploadForCompare(compareFileA.files[0], "a");
    }
    updateCompareBtn();
});

compareFileB.addEventListener("change", async () => {
    if (compareFileB.files.length) {
        compareImageB = await uploadForCompare(compareFileB.files[0], "b");
    }
    updateCompareBtn();
});

async function uploadForCompare(file, slot) {
    const formData = new FormData();
    formData.append("file", file);
    
    try {
        const res = await fetch(`${API_BASE}/upload-image`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` },
            body: formData,
        });
        if (!res.ok) throw new Error("Upload failed");
        const data = await res.json();
        
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById(`compare-img-${slot}`).src = e.target.result;
            document.getElementById(`compare-preview-${slot}`).classList.remove("hidden");
            document.getElementById(`compare-drop-${slot}`).classList.add("hidden");
        };
        reader.readAsDataURL(file);
        
        return data.image_id;
    } catch (err) {
        console.error("Compare upload failed:", err);
        addMessage("bot", `❌ Failed to upload product ${slot.toUpperCase()}: ${err.message}`);
        return null;
    }
}

function updateCompareBtn() {
    compareBtn.disabled = !(compareImageA && compareImageB);
}

compareBtn.addEventListener("click", async () => {
    if (!compareImageA || !compareImageB) return;
    
    compareBtn.disabled = true;
    compareBtn.innerHTML = "<span>⏳ Comparing...</span>";
    
    try {
        const res = await fetch(`${API_BASE}/api/features/compare`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify({
                image_id_a: compareImageA,
                image_id_b: compareImageB
            })
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Compare failed");
        }
        
        const data = await res.json();
        displayCompareResult(data);
    } catch (err) {
        console.error("Compare failed:", err);
        addMessage("bot", `❌ Comparison failed: ${err.message}`);
    } finally {
        compareBtn.disabled = false;
        compareBtn.innerHTML = "<span>⚡ Compare Products</span>";
    }
});

function displayCompareResult(data) {
    const container = document.getElementById("compare-result");
    container.classList.remove("hidden");
    
    let html = `<div class="compare-winner">🏆 Winner: <strong>Product ${data.winner}</strong></div>`;
    
    // Comparison table
    html += `<table class="compare-table">
        <thead>
            <tr><th>Nutrient</th><th>Product A</th><th>Product B</th><th>Better</th></tr>
        </thead>
        <tbody>`;
    
    (data.comparison_table || []).forEach(row => {
        const winnerIcon = row.winner === "A" ? "🅰️" : row.winner === "B" ? "🅱️" : "🤝";
        html += `<tr class="${row.winner !== 'tie' ? 'has-winner' : ''}">
            <td>${row.nutrient}</td>
            <td class="${row.winner === 'A' ? 'winner-cell' : ''}">${row.product_a}</td>
            <td class="${row.winner === 'B' ? 'winner-cell' : ''}">${row.product_b}</td>
            <td>${winnerIcon}</td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    
    // AI Verdict
    if (data.ai_verdict) {
        html += `<div class="compare-ai-verdict">
            <h3>🤖 AI Verdict</h3>
            <div class="markdown-body">${marked.parse(data.ai_verdict)}</div>
        </div>`;
    }
    
    container.innerHTML = html;
}


// ─── Chat ────────────────────────────────────────────────────────
chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;

    addMessage("user", question);
    const userMsg = { role: "user", content: question, timestamp: new Date().toISOString(), image_id: currentImageId };
    
    questionInput.value = "";
    sendBtn.disabled = true;

    const loaderId = addLoader();

    try {
        const body = {
            question,
            image_id: currentImageId,
            use_rag: true,
            use_ocr: !!currentImageId,
        };
        const res = await fetch(`${API_BASE}/ask`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify(body),
        });
        removeLoader(loaderId);
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Request failed");
        }
        const data = await res.json();
        const answerHtml = formatAnswer(data);
        addMessage("bot", answerHtml, true);
        
        // Save BOTH to history (sequential to prevent duplicate conversations)
        const userSaved = await saveToHistory(userMsg);
        if (userSaved) {
            const botMsg = { role: "bot", content: answerHtml, timestamp: new Date().toISOString() };
            await saveToHistory(botMsg);
        }
        
    } catch (err) {
        removeLoader(loaderId);
        addMessage("bot", `❌ ${err.message}`);
    } finally {
        sendBtn.disabled = false;
        questionInput.focus();
    }
});

async function saveToHistory(msg) {
    try {
        const res = await fetch(`${API_BASE}/api/chat/save?conv_id=${currentConversationId || ""}`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify(msg)
        });
        if (res.ok) {
            const data = await res.json();
            currentConversationId = data.conversation_id;
            loadChatHistory(); // Refresh history list
            return true;
        }
    } catch (err) {
        console.error("Save failed", err);
    }
    return false;
}

// ─── Helpers ─────────────────────────────────────────────────────
function addMessage(role, text, isHtml = false, imageUrl = null) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    
    if (imageUrl) {
        const img = document.createElement("img");
        img.src = imageUrl.startsWith("http") ? imageUrl : API_BASE + imageUrl;
        img.className = "chat-image-bubble";
        img.onclick = () => window.open(img.src, "_blank");
        bubble.appendChild(img);
        if (text) {
            const p = document.createElement("p");
            p.textContent = text;
            p.style.marginTop = "10px";
            bubble.appendChild(p);
        }
    } else if (isHtml) {
        bubble.innerHTML = text;
    } else {
        bubble.textContent = text;
    }
    
    wrapper.appendChild(bubble);
    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoader() {
    const id = "loader-" + Date.now();
    const wrapper = document.createElement("div");
    wrapper.className = "message bot";
    wrapper.id = id;
    wrapper.innerHTML = `
        <div class="message-bubble">
            <div class="loader"><span></span><span></span><span></span></div>
        </div>`;
    chatMessages.appendChild(wrapper);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return id;
}

function removeLoader(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function formatAnswer(data) {
    let html = "";
    if (data.explanation) {
        let explText = data.explanation.replace(/^[#\s]*Explanation:\s*/i, "").trim();
        if (explText) {
            html += `
                <div class="answer-section explanation">
                    <h3 class="section-title">🔍 Detailed Explanation</h3>
                    <div class="markdown-body">${marked.parse(explText)}</div>
                </div>`;
        }
    }
    if (data.answer) {
        let ansText = data.answer.replace(/^[#\s]*Final Answer:\s*/i, "").trim();
        if (ansText && ansText !== "Direct answer provided.") {
            html += `
                <div class="answer-section final-answer">
                    <h3 class="section-title">💡 Final Expert Answer</h3>
                    <div class="markdown-body">${marked.parse(ansText)}</div>
                </div>`;
        }
    }
    if (!html && data.raw_response) {
        html = `<div class="markdown-body">${marked.parse(data.raw_response)}</div>`;
    }
    if (data.sources && data.sources.length) {
        html += `<p class="sources"><em>📚 Context: ${data.sources.length} knowledge chunks used</em></p>`;
    }
    return html || "<p>No answer generated.</p>";
}
