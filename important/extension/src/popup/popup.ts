import { browserAPI } from '../lib/browserPolyfill';

document.addEventListener('DOMContentLoaded', async () => {
  const badgeEl = document.getElementById('connection-badge') as HTMLElement;
  const viewAuth = document.getElementById('view-authenticated') as HTMLElement;
  const viewLogin = document.getElementById('view-login') as HTMLElement;

  const userNameEl = document.getElementById('user-name') as HTMLElement;
  const userEmailEl = document.getElementById('user-email') as HTMLElement;
  const userAvatarEl = document.getElementById('user-avatar') as HTMLElement;
  const resumeFilenameEl = document.getElementById('resume-filename') as HTMLElement;

  const loginForm = document.getElementById('login-form') as HTMLFormElement;
  const loginErrorEl = document.getElementById('login-error') as HTMLElement;
  const loginSubmitBtn = document.getElementById('btn-login-submit') as HTMLButtonElement;

  const btnLogout = document.getElementById('btn-logout') as HTMLButtonElement;
  const btnOptions = document.getElementById('btn-options') as HTMLButtonElement;
  const linkOptionsLoggedOut = document.getElementById('link-options-loggedout') as HTMLButtonElement;
  const linkKanban = document.getElementById('link-kanban') as HTMLButtonElement;
  const linkResumes = document.getElementById('link-resumes') as HTMLButtonElement;

  let backendUrl = 'http://localhost:8000';

  async function refreshStatus() {
    try {
      const res = await browserAPI.runtime.sendMessage({ type: 'CHECK_STATUS' });
      backendUrl = res.backendUrl || backendUrl;

      if (res.backendConnected) {
        badgeEl.textContent = 'Connected';
        badgeEl.className = 'badge badge-online';
      } else {
        badgeEl.textContent = 'Offline';
        badgeEl.className = 'badge badge-offline';
      }

      if (res.isLoggedIn && res.user) {
        viewLogin.classList.add('hidden');
        viewAuth.classList.remove('hidden');

        const name = [res.user.first_name, res.user.last_name].filter(Boolean).join(' ') || 'Candidate';
        userNameEl.textContent = name;
        userEmailEl.textContent = res.user.email;
        userAvatarEl.textContent = name.charAt(0).toUpperCase();

        if (res.activeResume) {
          resumeFilenameEl.textContent = res.activeResume.title || res.activeResume.filename || 'Active Resume';
        } else {
          resumeFilenameEl.textContent = 'No active resume set';
        }
      } else {
        viewAuth.classList.add('hidden');
        viewLogin.classList.remove('hidden');
      }
    } catch (err: any) {
      badgeEl.textContent = 'Error';
      badgeEl.className = 'badge badge-offline';
    }
  }

  // Handle Login Form
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginErrorEl.classList.add('hidden');
    loginSubmitBtn.disabled = true;
    loginSubmitBtn.textContent = 'Connecting...';

    const email = (document.getElementById('email') as HTMLInputElement).value.trim();
    const password = (document.getElementById('password') as HTMLInputElement).value;

    try {
      const res = await browserAPI.runtime.sendMessage({
        type: 'LOGIN',
        email,
        password,
      });

      if (!res.ok) {
        loginErrorEl.textContent = res.error || 'Invalid credentials or server unreachable.';
        loginErrorEl.classList.remove('hidden');
      } else {
        await refreshStatus();
      }
    } catch (err: any) {
      loginErrorEl.textContent = err.message || 'Connection failed';
      loginErrorEl.classList.remove('hidden');
    } finally {
      loginSubmitBtn.disabled = false;
      loginSubmitBtn.textContent = 'Log In';
    }
  });

  // Handle Logout
  btnLogout.addEventListener('click', async () => {
    await browserAPI.runtime.sendMessage({ type: 'LOGOUT' });
    await refreshStatus();
  });

  // Options page links
  const openOptions = () => browserAPI.runtime.openOptionsPage();
  btnOptions.addEventListener('click', openOptions);
  linkOptionsLoggedOut.addEventListener('click', openOptions);

  // Quick navigation links
  linkKanban.addEventListener('click', () => {
    browserAPI.tabs.create({ url: `${backendUrl}/#applications` });
  });

  linkResumes.addEventListener('click', () => {
    browserAPI.tabs.create({ url: `${backendUrl}/#resume-studio` });
  });

  const btnCaptureNow = document.getElementById('btn-capture-now') as HTMLButtonElement | null;
  if (btnCaptureNow) {
    btnCaptureNow.addEventListener('click', async () => {
      btnCaptureNow.disabled = true;
      btnCaptureNow.textContent = 'Activating...';
      try {
        await browserAPI.runtime.sendMessage({ type: 'ACTIVATE_CAPTURE_ON_TAB' });
      } finally {
        window.close();
      }
    });
  }

  await refreshStatus();
});
