MAIN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main Container & Dark Theme Overrides */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }

    /* Top Banner / Header Card */
    .hero-banner {
        background: linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(33, 38, 45, 0.95) 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }

    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #58a6ff 0%, #bc8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 8px 0;
    }

    .hero-subtitle {
        font-size: 0.95rem;
        color: #8b949e;
        margin: 0;
    }

    /* Metric Cards */
    .stat-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }

    .stat-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #58a6ff;
    }

    .stat-lbl {
        font-size: 0.8rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Entity Badges */
    .badge-class {
        background-color: rgba(56, 139, 253, 0.15);
        color: #58a6ff;
        border: 1px solid rgba(56, 139, 253, 0.4);
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-func {
        background-color: rgba(46, 160, 67, 0.15);
        color: #3fb950;
        border: 1px solid rgba(46, 160, 67, 0.4);
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .badge-method {
        background-color: rgba(187, 128, 255, 0.15);
        color: #bc8cff;
        border: 1px solid rgba(187, 128, 255, 0.4);
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Search Result Card */
    .result-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }

    .result-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }

    .result-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #f0f6fc;
    }
</style>
"""
