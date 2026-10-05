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

  // Handle Auto-Discover
  const btnDiscover = document.getElementById('btn-discover') as HTMLButtonElement | null;
  const instancesListEl = document.getElementById('instances-list') as HTMLElement | null;

  if (btnDiscover && instancesListEl) {
    btnDiscover.addEventListener('click', async () => {
      instancesListEl.classList.remove('hidden');
      instancesListEl.innerHTML = '<p style="color: #94a3b8; margin: 4px 0;">Probing ports 8000–8010 for active Compust instances...</p>';

      try {
        const res = await browserAPI.runtime.sendMessage({ type: 'DISCOVER_INSTANCES' });
        const instances: any[] = res.instances || [];

        if (instances.length === 0) {
          instancesListEl.innerHTML = '<p style="color: #f87171; margin: 4px 0;">No active Compust instances found on ports 8000–8010.</p>';
          return;
        }

        instancesListEl.innerHTML = `<p style="font-weight: 600; color: #38bdf8; margin: 4px 0 8px 0;">Found ${instances.length} active Compust instance(s):</p>`;

        instances.forEach((inst) => {
          const item = document.createElement('div');
          item.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 6px 8px; margin-bottom: 6px; background: rgba(15, 23, 42, 0.6); border-radius: 6px; border: 1px solid rgba(255,255,255,0.06); font-size: 0.85rem;';

          const info = document.createElement('div');
          info.innerHTML = `<strong>${inst.url}</strong> <span style="color: #a78bfa; margin-left: 6px;">[${inst.mode.toUpperCase()}]</span> <span style="color: #64748b; margin-left: 6px;">v${inst.version} (PID ${inst.pid || '?'})</span>`;

          const selectBtn = document.createElement('button');
          selectBtn.className = 'btn btn-secondary';
          selectBtn.style.cssText = 'padding: 4px 10px; font-size: 0.8rem;';
          selectBtn.textContent = 'Select';
          selectBtn.addEventListener('click', async () => {
            backendUrlInput.value = inst.url;
            await browserAPI.runtime.sendMessage({
              type: 'SAVE_SETTINGS',
              settings: { backendUrl: inst.url },
            });
            saveFeedbackEl.classList.remove('hidden');
            setTimeout(() => saveFeedbackEl.classList.add('hidden'), 3000);
            instancesListEl.classList.add('hidden');
          });

          item.appendChild(info);
          item.appendChild(selectBtn);
          instancesListEl.appendChild(item);
        });

        // If only 1 instance, automatically adopt it
        if (instances.length === 1) {
          backendUrlInput.value = instances[0].url;
          await browserAPI.runtime.sendMessage({
            type: 'SAVE_SETTINGS',
            settings: { backendUrl: instances[0].url },
          });
          saveFeedbackEl.classList.remove('hidden');
          setTimeout(() => saveFeedbackEl.classList.add('hidden'), 3000);
        }
      } catch (err: any) {
        instancesListEl.innerHTML = `<p style="color: #f87171; margin: 4px 0;">Discovery failed: ${err.message}</p>`;
      }
    });
  }

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
