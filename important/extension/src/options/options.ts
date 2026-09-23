import { browserAPI } from '../lib/browserPolyfill';

document.addEventListener('DOMContentLoaded', async () => {
  const backendUrlInput = document.getElementById('backend-url') as HTMLInputElement;
  const btnTest = document.getElementById('btn-test') as HTMLButtonElement;
  const btnSave = document.getElementById('btn-save') as HTMLButtonElement;
  const testResultEl = document.getElementById('test-result') as HTMLElement;
  const saveFeedbackEl = document.getElementById('save-feedback') as HTMLElement;

  // Load existing settings
  try {
    const res = await browserAPI.runtime.sendMessage({ type: 'GET_SETTINGS' });
    if (res.ok && res.settings) {
      backendUrlInput.value = res.settings.backendUrl || 'http://localhost:8000';
    }
  } catch {
    backendUrlInput.value = 'http://localhost:8000';
  }

  // Handle Test Connection
  btnTest.addEventListener('click', async () => {
    const url = backendUrlInput.value.trim().replace(/\/+$/, '');
    testResultEl.className = 'test-box';
    testResultEl.textContent = 'Testing connection...';
    testResultEl.classList.remove('hidden');

    try {
      const res = await browserAPI.runtime.sendMessage({
        type: 'TEST_CONNECTION',
        url,
      });

      if (res.ok) {
        testResultEl.className = 'test-box test-success';
        testResultEl.textContent = `✓ Connected successfully to Compust! Database engine: ${res.database || 'SQLite/MySQL'}`;
      } else {
        testResultEl.className = 'test-box test-error';
        testResultEl.textContent = `✗ ${res.error || 'Could not reach Compust backend'}`;
      }
    } catch (err: any) {
      testResultEl.className = 'test-box test-error';
      testResultEl.textContent = `✗ ${err.message || 'Connection failed'}`;
    }
  });

  // Handle Save Settings
  btnSave.addEventListener('click', async () => {
    const backendUrl = backendUrlInput.value.trim().replace(/\/+$/, '');
    saveFeedbackEl.classList.add('hidden');

    try {
      await browserAPI.runtime.sendMessage({
        type: 'SAVE_SETTINGS',
        settings: { backendUrl },
      });

      saveFeedbackEl.classList.remove('hidden');
      setTimeout(() => {
        saveFeedbackEl.classList.add('hidden');
      }, 3000);
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
    }
  });
});
