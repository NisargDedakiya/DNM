const state = {
  mode: 'login',
  token: localStorage.getItem('nh_token') || '',
};

const usernameField = document.getElementById('username-field');
const usernameInput = document.getElementById('username');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submit-btn');
const statusEl = document.getElementById('status');
const outputEl = document.getElementById('output');
const tabs = document.querySelectorAll('.tab');
const checkMeBtn = document.getElementById('check-me');

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.style.color = isError ? 'var(--danger)' : 'rgba(255,255,255,0.7)';
}

function renderMode() {
  tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.mode === state.mode));
  const isRegister = state.mode === 'register';
  usernameField.classList.toggle('field-hidden', !isRegister);
  submitBtn.textContent = isRegister ? 'Create account' : 'Sign in';
}

function pretty(obj) {
  return JSON.stringify(obj, null, 2);
}

async function requestJSON(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const detail = data.detail || data.message || res.statusText;
    throw new Error(detail);
  }
  return data;
}

tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    state.mode = tab.dataset.mode;
    setStatus(state.mode === 'register' ? 'Ready to create your account' : 'Ready to sign in');
    renderMode();
  });
});

submitBtn.addEventListener('click', async (e) => {
  e.preventDefault();
  try {
    if (state.mode === 'register') {
      const payload = {
        username: usernameInput.value.trim(),
        email: emailInput.value.trim(),
        password: passwordInput.value,
      };
      setStatus('Creating secure account...');
      const data = await requestJSON('/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      outputEl.textContent = pretty(data);
      setStatus('Account created successfully');
    } else {
      const payload = {
        email: emailInput.value.trim(),
        password: passwordInput.value,
      };
      setStatus('Signing in securely...');
      const data = await requestJSON('/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      state.token = data.access_token;
      localStorage.setItem('nh_token', state.token);
      outputEl.textContent = pretty(data);
      setStatus('Signed in successfully');
    }
  } catch (error) {
    outputEl.textContent = pretty({ error: error.message });
    setStatus(error.message, true);
  }
});

checkMeBtn.addEventListener('click', async () => {
  if (!state.token) {
    setStatus('Login first to check current user', true);
    outputEl.textContent = pretty({ error: 'No token found. Please login first.' });
    return;
  }

  try {
    setStatus('Checking your profile...');
    const data = await requestJSON('/auth/me', {
      method: 'GET',
      headers: { Authorization: `Bearer ${state.token}` },
    });
    outputEl.textContent = pretty(data);
    setStatus('Profile loaded');
  } catch (error) {
    outputEl.textContent = pretty({ error: error.message });
    setStatus(error.message, true);
  }
});

renderMode();
setStatus('Ready to authenticate');
