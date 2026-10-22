"""
Compust User-Facing Diagnostics and Error Views.

Renders polished, self-contained HTML pages for:
1. Missing or stale frontend build (instead of raw 404/500)
2. Friendly server error page with Request ID (instead of raw 500 stack traces)
"""

import html


def render_missing_frontend_page(
    port: int,
    mode: str,
    logs_path: str,
    db_status: str,
    version: str = "1.0.4",
) -> str:
    """Render friendly HTML diagnostic page when frontend dist is missing or stale."""
    safe_logs_path = html.escape(logs_path)
    safe_mode = html.escape(mode.upper())
    safe_db = html.escape(db_status.upper())
    safe_port = int(port)

    dev_hints = """
      <div class="card instruction-card">
        <h3>Developer Quick Start</h3>
        <p>You are running in <strong>DEV mode</strong>. The pre-compiled production frontend (<code>dist</code>) is not present. Choose one of the following:</p>
        <ol>
          <li><strong>Start Vite Dev Server (Recommended for development):</strong>
            <pre><code>cd important/frontend
npm run dev</code></pre>
            Then open <a href="http://127.0.0.1:5173" class="highlight-link">http://127.0.0.1:5173</a>.
          </li>
          <li><strong>Build Static Frontend:</strong>
            <pre><code>cd important/frontend
npm run build</code></pre>
            Then refresh this page.
          </li>
        </ol>
      </div>
    """

    installed_hints = """
      <div class="card instruction-card">
        <h3>Standalone Installation Recovery</h3>
        <p>You are running in <strong>INSTALLED mode</strong>, but the user interface bundle is missing or incomplete.</p>
        <ul>
          <li><strong>Tray Menu:</strong> Right-click the Compust tray icon near your clock and select <strong>Check &amp; Repair</strong>.</li>
          <li><strong>Re-install:</strong> Run the installer again over this installation to restore damaged files (your user data will be preserved).</li>
        </ul>
      </div>
    """

    hints = dev_hints if mode.lower() == "dev" else installed_hints

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Compust - Frontend Service Diagnostics</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --card-bg: #111827;
      --border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --success: #10b981;
      --warn: #f59e0b;
      --code-bg: #1f2937;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    body {{
      background: var(--bg);
      color: var(--text);
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 24px;
    }}
    .container {{
      max-width: 680px;
      width: 100%;
    }}
    .header {{
      text-align: center;
      margin-bottom: 24px;
    }}
    .logo-badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: rgba(59, 130, 246, 0.1);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #60a5fa;
      padding: 6px 14px;
      border-radius: 9999px;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 12px;
    }}
    h1 {{
      font-size: 26px;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .subtitle {{
      color: var(--text-muted);
      font-size: 15px;
      line-height: 1.5;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
    }}
    .status-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .status-item {{
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      text-align: center;
    }}
    .status-label {{
      font-size: 12px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }}
    .status-value {{
      font-size: 15px;
      font-weight: 600;
    }}
    .status-value.ok {{ color: var(--success); }}
    .status-value.mode {{ color: #60a5fa; }}
    .instruction-card h3 {{
      font-size: 16px;
      margin-bottom: 10px;
      color: #93c5fd;
    }}
    .instruction-card p, .instruction-card li {{
      font-size: 14px;
      color: var(--text-muted);
      line-height: 1.6;
    }}
    .instruction-card ol, .instruction-card ul {{
      padding-left: 20px;
      margin-top: 8px;
    }}
    .instruction-card li {{
      margin-bottom: 8px;
    }}
    pre {{
      background: var(--code-bg);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 13px;
      margin: 6px 0;
      color: #e5e7eb;
      overflow-x: auto;
    }}
    .highlight-link {{
      color: #60a5fa;
      text-decoration: underline;
    }}
    .actions {{
      display: flex;
      gap: 12px;
      justify-content: center;
      margin-top: 24px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s;
    }}
    .btn-primary {{
      background: var(--primary);
      color: #ffffff;
      border: 1px solid var(--primary);
    }}
    .btn-primary:hover {{
      background: var(--primary-hover);
    }}
    .btn-secondary {{
      background: transparent;
      color: var(--text);
      border: 1px solid var(--border);
    }}
    .btn-secondary:hover {{
      background: rgba(255, 255, 255, 0.05);
    }}
    .footer-note {{
      text-align: center;
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 20px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo-badge">Compust Core Engine v{version}</div>
      <h1>Backend Running — Frontend Build Needed</h1>
      <p class="subtitle">The Compust FastAPI backend is online and healthy, but the user interface bundle was not found.</p>
    </div>

    <div class="status-grid">
      <div class="status-item">
        <div class="status-label">Backend Status</div>
        <div class="status-value ok">ONLINE (Port {safe_port})</div>
      </div>
      <div class="status-item">
        <div class="status-label">Database</div>
        <div class="status-value ok">{safe_db}</div>
      </div>
      <div class="status-item">
        <div class="status-label">Runtime Mode</div>
        <div class="status-value mode">{safe_mode}</div>
      </div>
    </div>

    {hints}

    <div class="card">
      <div class="status-label">Diagnostic Logs Path</div>
      <pre style="margin-top: 6px;"><code>{safe_logs_path}</code></pre>
    </div>

    <div class="actions">
      <button class="btn btn-primary" onclick="window.location.reload()">Refresh Page</button>
      <a href="/docs" class="btn btn-secondary">API Docs (/docs)</a>
      <a href="/health/deep" class="btn btn-secondary">Deep Health (/health/deep)</a>
    </div>

    <div class="footer-note">
      Compust Local-First Intelligence Platform • Port {safe_port}
    </div>
  </div>
</body>
</html>
"""


def render_friendly_error_page(
    request_id: str,
    path: str,
    logs_path: str,
    error_summary: str = "An unexpected server error occurred.",
) -> str:
    """Render friendly HTML error page when an unhandled exception occurs."""
    safe_req_id = html.escape(request_id)
    safe_path = html.escape(path)
    safe_logs_path = html.escape(logs_path)
    safe_summary = html.escape(error_summary)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Compust - Server Error</title>
  <style>
    :root {{
      --bg: #0b0f19;
      --card-bg: #111827;
      --border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --danger: #ef4444;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    body {{
      background: var(--bg);
      color: var(--text);
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 24px;
    }}
    .container {{
      max-width: 580px;
      width: 100%;
      text-align: center;
    }}
    .error-icon {{
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: rgba(239, 68, 68, 0.15);
      color: var(--danger);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      margin: 0 auto 16px auto;
      border: 1px solid rgba(239, 68, 68, 0.3);
    }}
    h1 {{
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    .subtitle {{
      color: var(--text-muted);
      font-size: 15px;
      margin-bottom: 24px;
      line-height: 1.5;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      text-align: left;
      margin-bottom: 20px;
    }}
    .row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 14px;
    }}
    .row:last-child {{ border-bottom: none; }}
    .label {{ color: var(--text-muted); }}
    .value {{ font-family: monospace; font-weight: 600; color: #60a5fa; }}
    pre {{
      background: #1f2937;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      margin-top: 6px;
      overflow-x: auto;
      color: #e5e7eb;
    }}
    .hint-box {{
      background: rgba(59, 130, 246, 0.06);
      border: 1px solid rgba(59, 130, 246, 0.2);
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 13px;
      color: #93c5fd;
      text-align: left;
      margin-bottom: 24px;
      line-height: 1.5;
    }}
    .actions {{
      display: flex;
      gap: 12px;
      justify-content: center;
    }}
    .btn {{
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s;
    }}
    .btn-primary {{
      background: var(--primary);
      color: #ffffff;
      border: 1px solid var(--primary);
    }}
    .btn-primary:hover {{ background: var(--primary-hover); }}
    .btn-secondary {{
      background: transparent;
      color: var(--text);
      border: 1px solid var(--border);
    }}
    .btn-secondary:hover {{ background: rgba(255, 255, 255, 0.05); }}
  </style>
</head>
<body>
  <div class="container">
    <div class="error-icon">!</div>
    <h1>Something went wrong on the server</h1>
    <p class="subtitle">{safe_summary}</p>

    <div class="card">
      <div class="row">
        <span class="label">Request ID</span>
        <span class="value">{safe_req_id}</span>
      </div>
      <div class="row">
        <span class="label">Endpoint</span>
        <span class="value">{safe_path}</span>
      </div>
      <div style="margin-top: 10px;">
        <span class="label">Diagnostic Logs File</span>
        <pre><code>{safe_logs_path}</code></pre>
      </div>
    </div>

    <div class="hint-box">
      <strong>Self-Healing Hint:</strong> This error has been logged to the file above with Request ID <code>{safe_req_id}</code>. If using the Windows installed launcher, right-click the system tray icon and select <strong>Check &amp; Repair</strong>.
    </div>

    <div class="actions">
      <button class="btn btn-primary" onclick="window.location.reload()">Retry Request</button>
      <a href="/" class="btn btn-secondary">Go to Home</a>
    </div>
  </div>
</body>
</html>
"""
