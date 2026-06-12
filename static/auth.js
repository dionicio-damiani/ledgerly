/* ================================================
   Ledgerly — auth.js
   Token storage helpers + login/register form wiring
================================================ */

const TOKEN_KEY = "ledgerly_token";

window.Auth = {
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  },
  isAuthenticated() {
    return !!window.Auth.getToken();
  },
  authHeader() {
    const token = window.Auth.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },
  logout() {
    window.Auth.clearToken();
    window.location.href = "/login";
  },
  requireAuth() {
    if (!window.Auth.isAuthenticated()) {
      window.location.href = "/login";
    }
  },
};

// Spanish translations for fastapi-users error codes.
const ERROR_MESSAGES = {
  LOGIN_BAD_CREDENTIALS: "Email o contraseña incorrectos.",
  REGISTER_USER_ALREADY_EXISTS: "Ya existe una cuenta con ese email.",
  REGISTER_INVALID_PASSWORD: "La contraseña no cumple los requisitos.",
};

function describeError(detail) {
  if (typeof detail === "string") {
    return ERROR_MESSAGES[detail] || detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  if (detail && typeof detail === "object") {
    if (detail.code) {
      return ERROR_MESSAGES[detail.code] || detail.reason || JSON.stringify(detail);
    }
    if (detail.reason) return detail.reason;
  }
  return "Ocurrió un error inesperado. Intentá de nuevo.";
}

function showAuthError(message) {
  const el = document.getElementById("auth-error");
  if (!el) return;
  el.textContent = message;
  el.style.display = "block";
}

function hideAuthError() {
  const el = document.getElementById("auth-error");
  if (!el) return;
  el.textContent = "";
  el.style.display = "none";
}

function setButtonLoading(button, loading) {
  if (!button) return;
  button.disabled = loading;
  button.classList.toggle("loading", loading);
}

async function performLogin(email, password) {
  const res = await fetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(describeError(body.detail));
  }

  const data = await res.json();
  return data.access_token;
}

async function performRegister(email, password) {
  const res = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(describeError(body.detail));
  }

  return res.json();
}

document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideAuthError();

      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;

      if (!email) {
        showAuthError("Ingresá tu email.");
        return;
      }
      if (password.length < 8) {
        showAuthError("La contraseña debe tener al menos 8 caracteres.");
        return;
      }

      const button = document.getElementById("btn-login");
      setButtonLoading(button, true);

      try {
        const token = await performLogin(email, password);
        window.Auth.setToken(token);
        window.location.href = "/app";
      } catch (err) {
        showAuthError(err.message);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideAuthError();

      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;
      const confirmPassword = document.getElementById("confirm_password").value;

      if (!email) {
        showAuthError("Ingresá tu email.");
        return;
      }
      if (password.length < 8) {
        showAuthError("La contraseña debe tener al menos 8 caracteres.");
        return;
      }
      if (password !== confirmPassword) {
        showAuthError("Las contraseñas no coinciden.");
        return;
      }

      const button = document.getElementById("btn-register");
      setButtonLoading(button, true);

      try {
        await performRegister(email, password);
        const token = await performLogin(email, password);
        window.Auth.setToken(token);
        window.location.href = "/app";
      } catch (err) {
        showAuthError(err.message);
      } finally {
        setButtonLoading(button, false);
      }
    });
  }
});
