/**
 * NutritionVQA-RAG — Auth Logic
 * Handles Signup, Signin, OTP, and JWT management.
 */

// Global API configuration shared across scripts
const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
window.API_BASE = isLocal ? 'http://127.0.0.1:8000' : 'https://sathvik-cs-nutrition-vqa-backend.hf.space';
var API_BASE = window.API_BASE;

// ─── Auto-cleanup corrupted tokens ─────────────────────────────
(function() {
    const token = localStorage.getItem('token');
    if (token && (token.startsWith("b'") || token.startsWith('b"') || token.includes("\\n") || token.includes("\n"))) {
        console.warn('[Auth] Detected corrupted token, clearing it automatically.');
        localStorage.removeItem('token');
    }
})();

// ─── Global Fetch Interceptor (401 → auto-redirect to login) ────
(function() {
    const _origFetch = window.fetch;
    window.fetch = async function(...args) {
        const response = await _origFetch.apply(this, args);
        if (response.status === 401) {
            const url = typeof args[0] === 'string' ? args[0] : (args[0]?.url || '');
            const isProtectedRoute = url.includes('/api/') || url.includes('/ask') || url.includes('/upload-image');
            const isAuthPage = window.location.pathname.includes('signin.html') || window.location.pathname.includes('signup.html');
            if (isProtectedRoute && !isAuthPage) {
                console.warn('[Auth] Session expired — redirecting to login.');
                localStorage.removeItem('token');
                window.location.href = 'signin.html';
                return response;
            }
        }
        return response;
    };
})();


// ─── DOM Elements ───────────────────────────────────────────────
const signupForm = document.getElementById("signup-form");
const signinForm = document.getElementById("signin-form");
const forgotPasswordLink = document.getElementById("forgot-password-link");
const forgotPasswordSection = document.getElementById("forgot-password-section");
const sendOtpBtn = document.getElementById("send-otp-btn");
const otpVerifySection = document.getElementById("otp-verify-section");
const resetFinalBtn = document.getElementById("reset-final-btn");
const backToSignin = document.getElementById("back-to-signin");

function isGmail(email) {
    const gmailRegex = /^[a-zA-Z0-9._%+-]+@gmail\.com$/;
    return gmailRegex.test(email);
}

function isPasswordSecure(password) {
    const hasCapital = /[A-Z]/.test(password);
    const hasDigit = /\d/.test(password);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    if (!hasCapital || !hasDigit || !hasSpecial) {
        return {
            valid: false,
            msg: "Password must contain at least 1 capital letter, 1 digit, and 1 special character."
        };
    }
    return { valid: true };
}

// ─── Event Listeners ──────────────────────────────────────────────

if (signupForm) {
    signupForm.addEventListener("submit", handleSignup);
}

if (signinForm) {
    signinForm.addEventListener("submit", handleSignin);
}

if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener("click", (e) => {
        e.preventDefault();
        signinForm.classList.add("hidden");
        document.querySelector(".sn-welcome")?.classList.add("hidden");
        document.querySelector(".sn-signup-prompt")?.classList.add("hidden");
        forgotPasswordSection.classList.remove("hidden");
    });
}

if (backToSignin) {
    backToSignin.addEventListener("click", () => {
        signinForm.classList.remove("hidden");
        document.querySelector(".sn-welcome")?.classList.remove("hidden");
        document.querySelector(".sn-signup-prompt")?.classList.remove("hidden");
        forgotPasswordSection.classList.add("hidden");
        otpVerifySection?.classList.add("hidden");
        if (sendOtpBtn) sendOtpBtn.style.display = "";
    });
}

if (sendOtpBtn) {
    sendOtpBtn.addEventListener("click", async () => {
        const mobile = document.getElementById("reset-mobile").value;
        if (!mobile) return alert("Please enter your mobile number");
        
        try {
            const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mobile })
            });
            const data = await res.json();
            if (res.ok) {
                let msg = data.message;
                if (data.dev_otp) console.log(`Dev OTP: ${data.dev_otp}`);
                alert(msg);
                sendOtpBtn.style.display = "none";
                otpVerifySection.classList.remove("hidden");
            } else {
                alert(data.detail);
            }
        } catch (err) {
            console.error(err);
            alert("Error sending OTP");
        }
    });
}

if (resetFinalBtn) {
    resetFinalBtn.addEventListener("click", async () => {
        const mobile = document.getElementById("reset-mobile").value;
        const otp = document.getElementById("otp-code").value;
        const newPassword = document.getElementById("new-password").value;
        
        if (!otp || !newPassword) return alert("Please fill all fields");
        
        const check = isPasswordSecure(newPassword);
        if (!check.valid) return alert(check.msg);
        
        try {
            const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ mobile, otp, new_password: newPassword })
            });
            const data = await res.json();
            if (res.ok) {
                alert("Password reset successful! Please log in.");
                window.location.reload();
            } else {
                alert(data.detail);
            }
        } catch (err) {
            console.error(err);
        }
    });
}

// ─── 2FA Handlers (Signin & Signup) ──────────────────────────────
window.signupDataTemp = null;
window.signinLoginTemp = null;

const verifySigninOtpBtn = document.getElementById("verify-signin-otp-btn");
const verifySignupOtpBtn = document.getElementById("verify-signup-otp-btn");
const backToSigninFromOtp = document.getElementById("back-to-signin-from-otp");
const backToSignupFromOtp = document.getElementById("back-to-signup-from-otp");

if (backToSigninFromOtp) {
    backToSigninFromOtp.addEventListener("click", () => {
        document.getElementById("signin-otp-section").classList.add("hidden");
        signinForm.classList.remove("hidden");
        document.querySelector(".sn-welcome")?.classList.remove("hidden");
        document.querySelector(".sn-signup-prompt")?.classList.remove("hidden");
    });
}

if (backToSignupFromOtp) {
    backToSignupFromOtp.addEventListener("click", () => {
        document.getElementById("signup-otp-section").classList.add("hidden");
        signupForm.classList.remove("hidden");
        document.querySelector(".sn-welcome")?.classList.remove("hidden");
        document.querySelector(".sn-signup-prompt")?.classList.remove("hidden");
    });
}

if (verifySigninOtpBtn) {
    verifySigninOtpBtn.addEventListener("click", async () => {
        const otp = document.getElementById("signin-otp-code").value;
        if (!otp || otp.length < 4) return alert("Please enter a valid OTP");
        
        try {
            const res = await fetch(`${API_BASE}/api/auth/verify-signin-otp`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ login: window.signinLoginTemp, otp })
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem("token", data.access_token);
                window.location.href = "index.html";
            } else {
                alert(data.detail || "Invalid OTP");
            }
        } catch (err) {
            console.error(err);
            alert("Error verifying OTP");
        }
    });
}

if (verifySignupOtpBtn) {
    verifySignupOtpBtn.addEventListener("click", async () => {
        const otp = document.getElementById("signup-otp-code").value;
        if (!otp || otp.length < 4) return alert("Please enter a valid OTP");
        
        const payload = { ...window.signupDataTemp, otp };
        
        try {
            const res = await fetch(`${API_BASE}/api/auth/verify-signup-otp`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (res.ok) {
                alert("Account created successfully! Please log in.");
                window.location.href = "signin.html";
            } else {
                alert(data.detail || "Invalid OTP");
            }
        } catch (err) {
            console.error(err);
            alert("Error verifying OTP");
        }
    });
}

// ─── Handlers ───────────────────────────────────────────────────

async function handleSignup(e) {
    e.preventDefault();
    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const mobile = document.getElementById("mobile").value;
    const weight = document.getElementById("weight").value;
    const age = document.getElementById("age").value;
    const password = document.getElementById("password").value;

    if (!isGmail(email)) return alert("Please use a valid @gmail.com address.");
    const check = isPasswordSecure(password);
    if (!check.valid) return alert(check.msg);

    const body = { name, email, mobile, weight: parseFloat(weight), age: parseInt(age), password };

    try {
        const res = await fetch(`${API_BASE}/api/auth/signup`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });
        const data = await res.json();

        if (res.ok) {
            alert("Signup successful! Please log in.");
            window.location.href = "signin.html";
        } else {
            const errorMsg = data.detail || "Signup failed";
            alert(errorMsg);
        }
    } catch (err) {
        console.error(err);
        alert("Error during signup");
    }
}

async function handleSignin(e) {
    e.preventDefault();
    const login = document.getElementById("login").value;
    const password = document.getElementById("password").value;

    if (!isGmail(login) && !/^\d+$/.test(login)) {
        return alert("Please use a valid @gmail.com address or registered mobile number.");
    }
    try {
        const res = await fetch(`${API_BASE}/api/auth/signin`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ login, password })
        });
        const data = await res.json();

        if (res.ok) {
            localStorage.setItem("token", data.access_token);
            window.location.href = "index.html"; 
        } else {
            alert(data.detail || "Signin failed");
        }
    } catch (err) {
        console.error(err);
        alert("Error during signin");
    }
}

// Check for redirect if not logged in
window.addEventListener("load", () => {
    const token = localStorage.getItem("token");
    const path = window.location.pathname;
    const isMainPage = path === "/" || path === "/index.html" || path.endsWith("/index.html");
    const isProtectedPage = isMainPage || path.includes("dashboard.html") || path.includes("analytics.html");
    const isAuthPage = path.includes("signin.html") || path.includes("signup.html");
    
    if (!token && isProtectedPage) {
        window.location.href = "signin.html";
    }
    
    if (token && isAuthPage) {
        window.location.href = "index.html";
    }
});

// ─── Password Visibility Toggle (SVG Icons) ──────────────────────
const EYE_ICON = `<svg viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>`;
const EYE_OFF_ICON = `<svg viewBox="0 0 24 24"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.82l2.92 2.92c1.51-1.26 2.7-2.89 3.44-4.74-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.34-1.2l1.53 1.53c-.34-.13-.7-.13-1.07 0zm-2.07 2.07c.13.37.13.73 0 1.07L8.27 10.67z"/></svg>`;

function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const btn = input.nextElementSibling;
    if (input.type === "password") {
        input.type = "text";
        btn.innerHTML = EYE_OFF_ICON;
    } else {
        input.type = "password";
        btn.innerHTML = EYE_ICON;
    }
}


// ─── Google Auth (Mock Flow) ───────────────────────────

const googleSigninBtn = document.getElementById("google-signin");
if (googleSigninBtn) {
    googleSigninBtn.onclick = () => {
        document.getElementById("google-modal").classList.remove("hidden");
        document.getElementById("google-step-password").classList.add("hidden");
        document.getElementById("google-step-email").classList.add("hidden");
        document.getElementById("google-step-otp").classList.add("hidden");
        document.getElementById("google-step-chooser").classList.remove("hidden");
    };
}

function closeGoogleModal() {
    document.getElementById("google-modal").classList.add("hidden");
}

let selectedMockEmail = "";
let selectedMockName = "";

function selectMockGoogleAccount(email, name) {
    selectedMockEmail = email;
    selectedMockName = name;
    document.getElementById("google-user-display").innerText = email;
    document.getElementById("google-step-chooser").classList.add("hidden");
    document.getElementById("google-step-password").classList.remove("hidden");
}

function handleMockGoogleEmail() {
    const email = document.getElementById("google-email-input").value;
    if (!email) return alert("Please enter your email or phone");
    selectedMockEmail = email;
    selectedMockName = email.split("@")[0];
    document.getElementById("google-user-display").innerText = email;
    document.getElementById("google-step-email").classList.add("hidden");
    document.getElementById("google-step-password").classList.remove("hidden");
}

async function verifyMockGooglePassword() {
    const pass = document.getElementById("google-pass-input").value;
    const mobile = document.getElementById("google-mobile-input") ? document.getElementById("google-mobile-input").value : "N/A";
    
    if (!pass) return alert("Please enter your password");
    
    const btn = document.querySelector("#google-step-password .gm-btn");
    const origText = btn.innerText;
    btn.innerText = "Authenticating...";
    btn.disabled = true;
    
    const payload = {
        email: selectedMockEmail,
        name: selectedMockName,
        password: pass,
        mobile: mobile
    };
    let encodedPayload = btoa(JSON.stringify(payload)).replace(/\+/g, '-').replace(/\//g, '_');
    const fakeJwt = `dummyHeader.${encodedPayload}.dummySignature`;

    try {
        const res = await fetch(`${API_BASE}/api/auth/google`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: fakeJwt })
        });
        const data = await res.json();
        
        if (res.ok) {
            const isSignupPage = window.location.pathname.includes('signup.html');
            
            if (data.is_new_user) {
                alert(data.message || "Account created successfully! Please log in.");
                window.location.href = "signin.html";
            } else if (isSignupPage && !data.is_new_user) {
                alert("Account already exists! Please log in.");
                window.location.href = "signin.html";
            } else {
                localStorage.setItem("token", data.access_token);
                window.location.href = "index.html";
            }
        } else {
            let errorMsg = data.detail || "Google Auth failed on server";
            if (typeof errorMsg === 'object') errorMsg = JSON.stringify(errorMsg);
            alert(errorMsg);
        }
    } catch (err) {
        console.error(err);
        alert("Error connecting to server");
    } finally {
        btn.innerText = origText;
        btn.disabled = false;
        closeGoogleModal();
    }
}

// Logout Functionality (Global)
function logout() {
    localStorage.removeItem("token");
    window.location.href = "signin.html";
}
