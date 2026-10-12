"""HTML template generator for Curiosity AI Real-Time Model Evaluation Dashboard."""

def render_dashboard_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Curiosity AI — Real-Time Deep Learning Evaluation Dashboard</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #080b12;
            --bg-card: rgba(17, 24, 39, 0.75);
            --bg-card-border: rgba(56, 189, 248, 0.15);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-cyan: #38bdf8;
            --accent-green: #22c55e;
            --accent-amber: #f59e0b;
            --accent-purple: #c084fc;
            --accent-pink: #f472b6;
            --font-sans: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            --font-mono: 'JetBrains Mono', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-body);
            background-image: 
                radial-gradient(circle at 15% 20%, rgba(56, 189, 248, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 85% 80%, rgba(192, 132, 252, 0.06) 0%, transparent 40%);
            color: var(--text-main);
            font-family: var(--font-sans);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        /* Top Header */
        header {
            background: rgba(11, 15, 25, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            padding: 14px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .brand-box {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-badge {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #ffffff;
            font-weight: 800;
            font-size: 13px;
            padding: 6px 12px;
            border-radius: 8px;
            letter-spacing: 1px;
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.4);
        }

        .brand-title {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.3px;
            color: #ffffff;
        }

        .brand-subtitle {
            font-size: 12px;
            color: var(--text-muted);
            font-family: var(--font-mono);
        }

        .status-container {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .pulse-live {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(34, 197, 94, 0.12);
            border: 1px solid rgba(34, 197, 94, 0.3);
            color: #4ade80;
            font-size: 12px;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 20px;
            font-family: var(--font-mono);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            box-shadow: 0 0 8px #22c55e;
            animation: pulse-ring 1.8s infinite;
        }

        @keyframes pulse-ring {
            0% { transform: scale(0.95); opacity: 1; }
            50% { transform: scale(1.3); opacity: 0.6; }
            100% { transform: scale(0.95); opacity: 1; }
        }

        .clock-lbl {
            font-family: var(--font-mono);
            font-size: 13px;
            color: #94a3b8;
        }

        /* Container */
        .container {
            max-width: 1440px;
            width: 100%;
            margin: 0 auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            flex: 1;
        }

        /* Flash banner for new query update */
        #update-flash {
            display: none;
            background: linear-gradient(90deg, rgba(56, 189, 248, 0.2), rgba(34, 197, 94, 0.2));
            border: 1px solid rgba(56, 189, 248, 0.4);
            padding: 10px 18px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            color: #38bdf8;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* KPI Cards Grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
        }

        .kpi-card {
            background: var(--bg-card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--bg-card-border);
            border-radius: 12px;
            padding: 18px 20px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            transition: all 0.25s ease;
            position: relative;
            overflow: hidden;
        }

        .kpi-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-cyan), transparent);
            opacity: 0.6;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.35);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }

        .kpi-title {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
        }

        .kpi-value {
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
            font-family: var(--font-mono);
        }

        .val-cyan { color: var(--accent-cyan); text-shadow: 0 0 12px rgba(56, 189, 248, 0.3); }
        .val-green { color: var(--accent-green); text-shadow: 0 0 12px rgba(34, 197, 94, 0.3); }
        .val-amber { color: var(--accent-amber); text-shadow: 0 0 12px rgba(245, 158, 11, 0.3); }
        .val-purple { color: var(--accent-purple); text-shadow: 0 0 12px rgba(192, 132, 252, 0.3); }
        .val-pink { color: var(--accent-pink); text-shadow: 0 0 12px rgba(244, 114, 182, 0.3); }

        .kpi-desc {
            font-size: 11px;
            color: #64748b;
        }

        /* Action Toolbar */
        .action-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.06);
            padding: 10px 18px;
            border-radius: 12px;
        }

        .tab-btn-group {
            display: flex;
            gap: 8px;
        }

        .tab-btn {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #94a3b8;
            font-family: var(--font-sans);
            font-weight: 600;
            font-size: 13px;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .tab-btn.active {
            background: #0284c7;
            color: #ffffff;
            border-color: #0284c7;
            box-shadow: 0 0 14px rgba(2, 132, 199, 0.4);
        }

        .tab-btn:hover:not(.active) {
            background: rgba(255, 255, 255, 0.05);
            color: #ffffff;
        }

        .btn-group {
            display: flex;
            gap: 10px;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
            font-family: var(--font-sans);
        }

        .btn-primary {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #ffffff;
            border: none;
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 0 20px rgba(2, 132, 199, 0.6);
        }

        .btn-secondary {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: #e2e8f0;
        }

        .btn-secondary:hover {
            background: rgba(51, 65, 85, 0.8);
        }

        /* Tab Content Section */
        .tab-content {
            background: var(--bg-card);
            border: 1px solid var(--bg-card-border);
            border-radius: 14px;
            padding: 24px;
            display: none;
            flex-direction: column;
            gap: 18px;
        }

        .tab-content.active {
            display: flex;
        }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .section-title {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
        }

        .section-subtitle {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        .chart-display-frame {
            background: #000000;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 12px;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            min-height: 520px;
        }

        .chart-img {
            max-width: 100%;
            height: auto;
            border-radius: 6px;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
            transition: opacity 0.3s ease;
        }

        /* Live Table */
        .feed-table-container {
            overflow-x: auto;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            text-align: left;
        }

        th {
            background: rgba(30, 41, 59, 0.8);
            color: var(--accent-cyan);
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            padding: 12px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        }

        td {
            padding: 12px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: #cbd5e1;
            font-family: var(--font-mono);
            font-size: 12px;
        }

        tr:hover {
            background: rgba(56, 189, 248, 0.04);
        }

        .badge-cat {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            background: rgba(148, 163, 184, 0.15);
            color: #e2e8f0;
        }

        .badge-just-now {
            background: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.4);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            margin-left: 6px;
        }

        /* Footer */
        footer {
            margin-top: auto;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            padding: 16px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            color: #64748b;
        }

        footer a {
            color: var(--accent-cyan);
            text-decoration: none;
        }
    </style>
</head>
<body>

    <!-- Header -->
    <header>
        <div class="brand-box">
            <span class="brand-badge">RESEARCH DASHBOARD</span>
            <div>
                <div class="brand-title">CURIOSITY AI — Model Evaluation & Live Telemetry</div>
                <div class="brand-subtitle">8-Layer Cognitive Architecture | YOLOv11 & OCR Evaluation</div>
            </div>
        </div>
        <div class="status-container">
            <div class="pulse-live">
                <span class="pulse-dot"></span>
                <span>REAL-TIME PIPELINE ACTIVE</span>
            </div>
            <div class="clock-lbl" id="live-clock">--:--:--</div>
        </div>
    </header>

    <div class="container">
        <!-- Real-Time Update Flash Banner -->
        <div id="update-flash">
            ⚡ <span id="update-flash-msg">New query output processed & graphs refreshed!</span>
        </div>

        <!-- KPI Cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Total Inferences Audited</div>
                <div class="kpi-value val-cyan" id="kpi-total">195</div>
                <div class="kpi-desc">Total processed queries in database</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Pipeline Mean Accuracy</div>
                <div class="kpi-value val-green" id="kpi-mean-acc">74.3%</div>
                <div class="kpi-desc">Calculated ground-truth accuracy</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Latest Execution Latency</div>
                <div class="kpi-value val-amber" id="kpi-latency">2.45s</div>
                <div class="kpi-desc">End-to-end inference speed</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Latest Query Accuracy</div>
                <div class="kpi-value val-purple" id="kpi-latest-acc">88.5%</div>
                <div class="kpi-desc" id="kpi-latest-prompt">Waiting for query...</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">YOLOv11 mAP@0.5</div>
                <div class="kpi-value val-pink" id="kpi-map">0.902</div>
                <div class="kpi-desc">Mean Average Precision at IoU 0.5</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Optimum F1 Score</div>
                <div class="kpi-value val-cyan" id="kpi-f1">0.92 @ 0.45</div>
                <div class="kpi-desc">F1 Peak at Confidence 0.45</div>
            </div>
        </div>

        <!-- Action Bar & Tabs -->
        <div class="action-bar">
            <div class="tab-btn-group">
                <button class="tab-btn active" onclick="switchTab('curves', this)">📊 Deep Learning Curves (CVPR)</button>
                <button class="tab-btn" onclick="switchTab('telemetry', this)">📈 Pipeline Telemetry</button>
                <button class="tab-btn" onclick="switchTab('feed', this)">📜 Live Inferences Feed</button>
            </div>
            <div class="btn-group">
                <button class="btn btn-secondary" onclick="forceRefresh()">🔄 Refresh</button>
                <a class="btn btn-primary" id="btn-download-curves" href="/outputs/deep_learning_evaluation_report.png" download="Curiosity_Deep_Learning_Evaluation_Report.png">
                    📥 Download Curves for Report (300 DPI)
                </a>
                <a class="btn btn-secondary" id="btn-download-telem" href="/outputs/model_analytics_report.png" download="Curiosity_Model_Analytics_Report.png">
                    📥 Download Telemetry (PNG)
                </a>
            </div>
        </div>

        <!-- Tab 1: 4-Quadrant Deep Learning Curves -->
        <div class="tab-content active" id="tab-curves">
            <div class="section-header">
                <div>
                    <div class="section-title">Academic Model Evaluation Curves (Ultralytics / CVPR Format)</div>
                    <div class="section-subtitle">
                        Includes 4 standard research curves: (a) F1-Confidence Curve, (b) Precision-Recall Curve (mAP@0.5), (c) Precision-Confidence Curve, (d) Recall-Confidence Curve.
                    </div>
                </div>
                <div style="font-size: 11px; color: #94a3b8; font-family: var(--font-mono);">
                    Ready for direct inclusion in thesis / project report
                </div>
            </div>
            <div class="chart-display-frame">
                <img id="img-curves" class="chart-img" src="/outputs/deep_learning_evaluation_report.png" alt="Deep Learning Evaluation Report">
            </div>
        </div>

        <!-- Tab 2: Pipeline Telemetry -->
        <div class="tab-content" id="tab-telemetry">
            <div class="section-header">
                <div>
                    <div class="section-title">Production Inference Telemetry & Latency Diagnostics</div>
                    <div class="section-subtitle">
                        Tracking accuracy distribution, duration bar charts, processed media types, and confidence vs calculated accuracy correlation.
                    </div>
                </div>
            </div>
            <div class="chart-display-frame">
                <img id="img-telem" class="chart-img" src="/outputs/model_analytics_report.png" alt="Curiosity Model Analytics Report">
            </div>
        </div>

        <!-- Tab 3: Live Feed Table -->
        <div class="tab-content" id="tab-feed">
            <div class="section-header">
                <div>
                    <div class="section-title">Live Inference Audit Stream</div>
                    <div class="section-subtitle">Real-time database records logged from Curiosity Engine Layer 6.</div>
                </div>
            </div>
            <div class="feed-table-container">
                <table>
                    <thead>
                        <tr>
                            <th># ID</th>
                            <th>Timestamp</th>
                            <th>Category</th>
                            <th>Accuracy</th>
                            <th>Confidence</th>
                            <th>Duration (s)</th>
                            <th>Prompt / Query</th>
                        </tr>
                    </thead>
                    <tbody id="feed-tbody">
                        <tr><td colspan="7" style="text-align: center; color: #64748b;">Loading telemetry data...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer>
        <div>Curiosity AI Assistant &copy; 2026 | YOLOv11 Multi-Modal Perception & Grounded Reasoning Architecture</div>
        <div>
            Standalone Desktop Window: Run <code>python scripts/live_dashboard_gui.py</code>
        </div>
    </footer>

    <script>
        let lastMaxId = -1;
        let isFirstLoad = true;

        // Clock updater
        function updateClock() {
            const now = new Date();
            document.getElementById('live-clock').textContent = now.toLocaleTimeString();
        }
        setInterval(updateClock, 1000);
        updateClock();

        // Tab switcher
        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            document.getElementById('tab-' + tabId).classList.add('active');
            btn.classList.add('active');
        }

        // Live Poll Function
        async function fetchLiveTelemetry() {
            try {
                const res = await fetch('/api/telemetry/live');
                if (!res.ok) return;
                const data = await res.json();

                // Update KPI Cards
                document.getElementById('kpi-total').textContent = data.total_inferences || '0';
                document.getElementById('kpi-mean-acc').textContent = (data.average_accuracy || 0).toFixed(1) + '%';

                if (data.latest) {
                    document.getElementById('kpi-latency').textContent = (data.latest.duration_s || 0).toFixed(2) + 's';
                    document.getElementById('kpi-latest-acc').textContent = (data.latest.accuracy || 0).toFixed(1) + '%';
                    const p = data.latest.prompt || 'General query';
                    document.getElementById('kpi-latest-prompt').textContent = p.length > 35 ? p.substring(0, 32) + '...' : p;
                }

                // If new query detected
                if (data.max_id && data.max_id !== lastMaxId) {
                    if (!isFirstLoad) {
                        showFlashNotification(`New inference #${data.max_id} recorded! Graphs updated.`);
                    }
                    lastMaxId = data.max_id;
                    isFirstLoad = false;

                    // Refresh chart images with cache buster
                    const t = Date.now();
                    const imgCurves = document.getElementById('img-curves');
                    const imgTelem = document.getElementById('img-telem');
                    imgCurves.src = '/outputs/deep_learning_evaluation_report.png?v=' + t;
                    imgTelem.src = '/outputs/model_analytics_report.png?v=' + t;

                    // Update download button URLs
                    document.getElementById('btn-download-curves').href = '/outputs/deep_learning_evaluation_report.png?v=' + t;
                    document.getElementById('btn-download-telem').href = '/outputs/model_analytics_report.png?v=' + t;

                    // Populate feed table
                    renderFeedTable(data.recent_history);
                }
            } catch (err) {
                console.warn('Telemetry poll error:', err);
            }
        }

        function renderFeedTable(history) {
            if (!history || !history.length) return;
            const tbody = document.getElementById('feed-tbody');
            tbody.innerHTML = '';
            history.forEach((row, idx) => {
                const tr = document.createElement('tr');
                const isLatest = (idx === 0);
                const conf = (row.confidence <= 1.0 ? row.confidence * 100 : row.confidence).toFixed(1);
                tr.innerHTML = `
                    <td style="color: var(--accent-cyan); font-weight: bold;">
                        #${row.id} ${isLatest ? '<span class="badge-just-now">LATEST</span>' : ''}
                    </td>
                    <td>${row.created_at || '-'}</td>
                    <td><span class="badge-cat">${row.media_category || 'general'}</span></td>
                    <td style="color: #4ade80; font-weight: bold;">${(row.accuracy || 0).toFixed(1)}%</td>
                    <td>${conf}%</td>
                    <td style="color: #f59e0b;">${(row.duration_s || 0).toFixed(2)}s</td>
                    <td style="color: #e2e8f0; font-family: var(--font-sans);">${escapeHtml(row.prompt || '')}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        function escapeHtml(str) {
            return str.replace(/[&<>"']/g, function(m) {
                return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[m];
            });
        }

        function showFlashNotification(msg) {
            const flash = document.getElementById('update-flash');
            const flashMsg = document.getElementById('update-flash-msg');
            flashMsg.textContent = msg;
            flash.style.display = 'block';
            setTimeout(() => {
                flash.style.display = 'none';
            }, 4000);
        }

        async function forceRefresh() {
            try {
                await fetch('/api/telemetry/refresh', { method: 'POST' });
                await fetchLiveTelemetry();
                showFlashNotification('Charts and metrics forcibly regenerated!');
            } catch (e) {
                console.error(e);
            }
        }

        // Poll every 2 seconds
        setInterval(fetchLiveTelemetry, 2000);
        fetchLiveTelemetry();
    </script>
</body>
</html>
"""
