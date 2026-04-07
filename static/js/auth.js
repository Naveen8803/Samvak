// static/js/auth.js

const API_BASE = "/api";

// Toast message helper
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  // Trigger animation
  setTimeout(() => toast.classList.add("show"), 100);
  
  // Remove after 3 seconds
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Password validation
function validatePassword(pwd) {
  return pwd && pwd.length >= 6;
}

// ---------- LOGIN ----------
const loginForm = document.getElementById("loginForm");

if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = loginForm.loginEmail.value.trim();
    const password = loginForm.loginPassword.value;
    const errorDiv = document.getElementById("loginError");

    if (errorDiv) errorDiv.textContent = "";

    if (!email || !password) {
      if (errorDiv) errorDiv.textContent = "All fields are required";
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Invalid login credentials");
      }

      showToast("Login successful", "success");
      // Redirect to dashboard after success
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 500);

    } catch (err) {
      if (errorDiv) errorDiv.textContent = err.message;
    }
  });
}

// ---------- REGISTER ----------
const registerForm = document.getElementById("registerForm");

if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = registerForm.regName.value.trim();
    const email = registerForm.regEmail.value.trim();
    const password = registerForm.regPassword.value;
    const errorDiv = document.getElementById("registerError");

    if (errorDiv) errorDiv.textContent = "";

    if (!name || !email || !password) {
      if (errorDiv) errorDiv.textContent = "All fields are required";
      return;
    }

    if (!validatePassword(password)) {
      if (errorDiv) errorDiv.textContent = "Password must be at least 6 characters";
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "Registration failed");
      }

      showToast("Account created successfully", "success");
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 500);

    } catch (err) {
      if (errorDiv) errorDiv.textContent = err.message;
    }
  });
}