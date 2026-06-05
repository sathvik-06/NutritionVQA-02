/**
 * NutritionVQA-RAG — Analytics Page Logic
 * Chart.js powered nutrition trend analytics with weekly/monthly views.
 */

const isLocalAnal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
window.API_BASE = isLocalAnal ? 'http://127.0.0.1:8000' : 'https://sathvik-cs-nutrition-vqa-backend.hf.space';
var API_BASE = window.API_BASE;
let calorieChart = null;
let macroChart = null;
let scoreChart = null;

// ─── Initialization ──────────────────────────────────────────────
async function init() {
    const token = localStorage.getItem("token");
    if (!token) { window.location.href = "signin.html"; return; }

    try {
        await loadUserProfile();
        setupPeriodButtons();
        await loadAnalytics("weekly");
    } catch (err) {
        console.error("Analytics init failed:", err);
    }
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}

async function loadUserProfile() {
    try {
        const res = await fetch(`${API_BASE}/api/auth/me`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });
        if (res.ok) {
            const user = await res.json();
            document.getElementById("user-name").textContent = user.name;
            const initials = user.name.split(" ").map(n => n[0]).join("").toUpperCase();
            document.getElementById("user-initials").textContent = initials;
        } else {
            logout();
        }
    } catch (err) {
        console.error("Profile error:", err);
    }
}

// ─── Period Buttons ──────────────────────────────────────────────
function setupPeriodButtons() {
    document.querySelectorAll(".period-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
            document.querySelectorAll(".period-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            await loadAnalytics(btn.dataset.period);
        });
    });
}

// ─── Load Analytics Data ─────────────────────────────────────────
async function loadAnalytics(period) {
    try {
        const res = await fetch(`${API_BASE}/api/features/analytics/${period}`, {
            headers: { "Authorization": `Bearer ${localStorage.getItem("token")}` }
        });
        if (!res.ok) {
            console.error("Analytics fetch failed:", res.status);
            showEmptyState();
            return;
        }
        const data = await res.json();
        
        // Summary cards
        document.getElementById("analytics-products").textContent = data.total_products_scanned || 0;
        document.getElementById("analytics-days").textContent = data.days_tracked || 0;
        document.getElementById("analytics-avg-cal").textContent = 
            data.averages && data.averages.calories ? Math.round(data.averages.calories) : "--";
        document.getElementById("analytics-avg-protein").textContent = 
            data.averages && data.averages.protein ? Math.round(data.averages.protein) + "g" : "--";
        
        if (!data.daily_data || data.daily_data.length === 0) {
            showEmptyState();
            return;
        }
        
        // Render Charts
        renderCalorieChart(data.daily_data);
        renderMacroChart(data.averages || {});
        renderNutrientBars(data.averages || {}, data.recommended || {});
        renderScoreChart(data.score_data || []);
        
        // AI Summary
        const summaryDiv = document.getElementById("ai-analytics-summary");
        if (data.ai_summary) {
            summaryDiv.innerHTML = marked.parse(data.ai_summary);
        } else {
            summaryDiv.innerHTML = '<p class="card-desc">Not enough data for AI analysis. Keep scanning!</p>';
        }
    } catch (err) {
        console.error("Analytics load failed:", err);
        showEmptyState();
    }
}

function showEmptyState() {
    document.getElementById("ai-analytics-summary").innerHTML = 
        '<p class="card-desc">📭 No nutrition data yet. Start scanning food labels to see your trends here!</p>';
}

// ─── Calorie Trend Line Chart ────────────────────────────────────
function renderCalorieChart(dailyData) {
    const ctx = document.getElementById("calorie-chart").getContext("2d");
    
    if (calorieChart) calorieChart.destroy();
    
    const labels = dailyData.map(d => d.date ? d.date.slice(5) : "");
    const calories = dailyData.map(d => d.calories || 0);
    const proteins = dailyData.map(d => d.protein || 0);
    
    calorieChart = new Chart(ctx, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: "Calories (kcal)",
                    data: calories,
                    borderColor: "#f87171",
                    backgroundColor: "rgba(248, 113, 113, 0.1)",
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: "#f87171",
                    pointRadius: 5,
                    pointHoverRadius: 8,
                },
                {
                    label: "Protein (g)",
                    data: proteins,
                    borderColor: "#38bdf8",
                    backgroundColor: "rgba(56, 189, 248, 0.1)",
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: "#38bdf8",
                    pointRadius: 5,
                    pointHoverRadius: 8,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: "#e2e8f0", font: { family: "'Inter', sans-serif" } }
                }
            },
            scales: {
                x: {
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255,255,255,0.05)" }
                },
                y: {
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255,255,255,0.05)" }
                }
            }
        }
    });
}

// ─── Macro Distribution Pie Chart ────────────────────────────────
function renderMacroChart(averages) {
    const ctx = document.getElementById("macro-chart").getContext("2d");
    
    if (macroChart) macroChart.destroy();
    
    const protein = averages.protein || 0;
    const fat = averages.fat || 0;
    const carbs = averages.carbohydrates || 0;
    const total = protein + fat + carbs;
    
    if (total === 0) {
        document.getElementById("macro-legend").innerHTML = '<p class="card-desc">No macro data available.</p>';
        return;
    }
    
    macroChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Protein", "Fat", "Carbs"],
            datasets: [{
                data: [protein, fat, carbs],
                backgroundColor: ["#38bdf8", "#fbbf24", "#a78bfa"],
                borderColor: ["#38bdf8", "#fbbf24", "#a78bfa"],
                borderWidth: 2,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "60%",
            plugins: {
                legend: { display: false }
            }
        }
    });
    
    // Custom legend
    const legendDiv = document.getElementById("macro-legend");
    const proteinPct = Math.round((protein / total) * 100);
    const fatPct = Math.round((fat / total) * 100);
    const carbsPct = Math.round((carbs / total) * 100);
    
    legendDiv.innerHTML = `
        <div class="macro-legend-item">
            <span class="macro-dot" style="background:#38bdf8"></span>
            <div>
                <span class="macro-name">Protein</span>
                <span class="macro-val">${Math.round(protein)}g (${proteinPct}%)</span>
            </div>
        </div>
        <div class="macro-legend-item">
            <span class="macro-dot" style="background:#fbbf24"></span>
            <div>
                <span class="macro-name">Fat</span>
                <span class="macro-val">${Math.round(fat)}g (${fatPct}%)</span>
            </div>
        </div>
        <div class="macro-legend-item">
            <span class="macro-dot" style="background:#a78bfa"></span>
            <div>
                <span class="macro-name">Carbs</span>
                <span class="macro-val">${Math.round(carbs)}g (${carbsPct}%)</span>
            </div>
        </div>
    `;
}

// ─── Nutrient vs Recommended Bars ────────────────────────────────
function renderNutrientBars(averages, recommended) {
    const container = document.getElementById("nutrient-compare-bars");
    container.innerHTML = "";
    
    const nutrients = ["calories", "protein", "fat", "sugar", "sodium", "fiber", "carbohydrates", "saturated_fat"];
    
    let hasData = false;
    nutrients.forEach(nutrient => {
        const avg = averages[nutrient] || 0;
        const rec = recommended[nutrient] || 100;
        if (avg === 0) return;
        
        hasData = true;
        const pct = Math.min(Math.round((avg / rec) * 100), 200);
        const unit = nutrient === "calories" ? "kcal" : (nutrient === "sodium" ? "mg" : "g");
        const isOver = pct > 100;
        
        const bar = document.createElement("div");
        bar.className = "intake-bar-row";
        bar.innerHTML = `
            <div class="intake-bar-label">
                <span>${nutrient.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}</span>
                <span class="intake-bar-values ${isOver ? 'over' : ''}">${Math.round(avg)}${unit} / ${rec}${unit}</span>
            </div>
            <div class="intake-bar-track">
                <div class="intake-bar-fill ${isOver ? 'over' : ''}" style="width: ${Math.min(pct, 100)}%"></div>
            </div>
            <span class="intake-bar-pct ${isOver ? 'over' : ''}">${pct}%</span>
        `;
        container.appendChild(bar);
    });
    
    if (!hasData) {
        container.innerHTML = '<p class="card-desc">No nutrient data available for this period.</p>';
    }
}

// ─── Health Score Trend Line Chart ───────────────────────────────
function renderScoreChart(scoreData) {
    const ctx = document.getElementById("score-chart").getContext("2d");
    
    if (scoreChart) scoreChart.destroy();
    
    if (!scoreData || scoreData.length === 0) {
        return;
    }
    
    const labels = scoreData.map(d => d.date ? d.date.slice(5) : "");
    const scores = scoreData.map(d => d.score || 0);
    
    // Generate gradient colors based on scores
    const colors = scores.map(s => {
        if (s >= 80) return "#34d399";
        if (s >= 60) return "#38bdf8";
        if (s >= 40) return "#fbbf24";
        return "#f87171";
    });
    
    scoreChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Health Score",
                data: scores,
                backgroundColor: colors.map(c => c + "99"),
                borderColor: colors,
                borderWidth: 2,
                borderRadius: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: "#e2e8f0", font: { family: "'Inter', sans-serif" } }
                }
            },
            scales: {
                x: {
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255,255,255,0.05)" }
                },
                y: {
                    min: 0,
                    max: 100,
                    ticks: { color: "#94a3b8" },
                    grid: { color: "rgba(255,255,255,0.05)" }
                }
            }
        }
    });
}
