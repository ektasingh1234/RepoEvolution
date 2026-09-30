MAIN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --primary-color: #2563eb !important;
    }

    /* CSS Reset & Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #e2e8f0;
    }

    code, pre, .stCodeBlock, [class*="stCode"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Overall Application Dark Theme */
    .stApp {
        background-color: #080c14 !important;
        background-image: radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.12) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(124, 58, 237, 0.10) 0px, transparent 50%);
        background-attachment: fixed;
        color: #e2e8f0;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
        z-index: 1;
    }

    .main .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 3rem !important;
        max-width: 1400px;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0b0f1a !important;
        border-right: 1px solid #1e293b !important;
    }

    .sidebar-brand {
        padding: 12px 0 16px 0;
    }

    .brand-title {
        font-size: 1.45rem;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.4px;
        margin-bottom: 2px;
        background: linear-gradient(90deg, #ffffff 0%, #60a5fa 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .brand-subtitle {
        font-size: 0.74rem;
        color: #64748b;
        font-weight: 500;
        letter-spacing: 0.2px;
    }

    .sidebar-section-title {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.1px;
        color: #475569;
        margin: 16px 0 8px 0;
    }

    .sidebar-divider {
        height: 1px;
        background: #1e293b;
        margin: 16px 0;
    }

    /* Status Cards */
    .status-card, .quick-info-card {
        background: rgba(15, 22, 38, 0.85);
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 12px;
        backdrop-filter: blur(8px);
    }

    .status-row, .info-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        color: #94a3b8;
        padding: 6px 0;
        border-bottom: 1px dashed rgba(30, 41, 59, 0.6);
    }

    .status-row:last-child, .info-row:last-child {
        border-bottom: none;
    }

    .status-val, .info-val {
        color: #cbd5e1;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        font-weight: 500;
    }

    /* Pulse Status Dots */
    .status-dot {
        display: inline-block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        margin-right: 6px;
    }

    .status-dot.green {
        background-color: #22c55e;
        box-shadow: 0 0 8px rgba(34, 197, 94, 0.7);
    }

    .status-dot.blue {
        background-color: #3b82f6;
        box-shadow: 0 0 8px rgba(59, 130, 246, 0.7);
    }

    .status-dot.gray {
        background-color: #475569;
    }

    .status-text-active {
        color: #4ade80;
        font-weight: 600;
        font-size: 0.78rem;
    }

    .status-text-offline {
        color: #64748b;
        font-size: 0.78rem;
    }

    /* Auth Card Layout */
    .auth-container {
        max-width: 440px;
        margin: 40px auto;
        background: rgba(15, 22, 38, 0.9);
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 32px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(12px);
    }

    .auth-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #ffffff;
        text-align: center;
        margin-bottom: 4px;
        background: linear-gradient(90deg, #ffffff 0%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .auth-subtitle {
        font-size: 0.84rem;
        color: #64748b;
        text-align: center;
        margin-bottom: 24px;
    }

    /* Hero Banner with SVG Architecture Visual */
    .hero-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(135deg, #0d1425 0%, #111a30 45%, #181640 100%);
        border: 1px solid #1e293b;
        border-radius: 14px;
        padding: 28px 32px;
        margin-bottom: 24px;
        box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
        position: relative;
        overflow: hidden;
    }

    .hero-left {
        max-width: 55%;
        z-index: 2;
    }

    .hero-brand-tag {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: #38bdf8;
        margin-bottom: 6px;
    }

    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 10px 0;
        letter-spacing: -0.6px;
        line-height: 1.2;
    }

    .hero-description {
        font-size: 0.88rem;
        color: #94a3b8;
        line-height: 1.55;
        margin-bottom: 18px;
    }

    .hero-pills {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }

    .hero-pill {
        display: inline-flex;
        align-items: center;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(59, 130, 246, 0.35);
        color: #93c5fd;
        font-size: 0.76rem;
        font-weight: 500;
        padding: 5px 12px;
        border-radius: 16px;
        transition: all 0.2s ease;
    }

    .hero-pill:hover {
        border-color: #60a5fa;
        color: #ffffff;
        transform: translateY(-1px);
    }

    .pill-dot {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        margin-right: 7px;
    }
    .pill-dot.blue { background-color: #3b82f6; }
    .pill-dot.cyan { background-color: #06b6d4; }
    .pill-dot.purple { background-color: #a855f7; }

    /* SVG Architecture Visual Right */
    .hero-right {
        z-index: 2;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    .arch-svg-container {
        width: 290px;
        height: 180px;
        background: #0b0f19;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }

    .arch-node {
        animation: nodePulse 3s ease-in-out infinite alternate;
    }

    @keyframes nodePulse {
        0% { r: 5; opacity: 0.8; }
        100% { r: 7; opacity: 1; filter: drop-shadow(0 0 6px #38bdf8); }
    }

    /* Navigation Tabs Polish */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #0b0f19;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid #1e293b;
        margin-bottom: 22px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: 7px;
        color: #8b949e;
        font-size: 0.85rem;
        font-weight: 500;
        padding: 0 16px;
        background-color: transparent;
        border: none !important;
        transition: all 0.2s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #f1f5f9;
        background-color: rgba(30, 41, 59, 0.5);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #162036 0%, #1e1b4b 100%) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        border: 1px solid rgba(59, 130, 246, 0.45) !important;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.35);
    }

    /* Standard Primary & Action Button Styling - Unified Blue Accent */
    .stButton button[kind="primary"],
    .stButton button[data-testid="baseButton-primary"],
    div[data-testid="stButton"] > button[kind="primary"],
    div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
    button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: 1px solid #3b82f6 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 8px 18px !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
        transition: all 0.2s ease !important;
    }

    .stButton button[kind="primary"]:hover,
    .stButton button[data-testid="baseButton-primary"]:hover,
    div[data-testid="stButton"] > button[kind="primary"]:hover,
    div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover,
    button[kind="primary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;
        background-color: #3b82f6 !important;
        border-color: #60a5fa !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5) !important;
    }

    .stButton button[kind="primary"]:focus,
    .stButton button[data-testid="baseButton-primary"]:focus,
    button[kind="primary"]:focus,
    button[data-testid="baseButton-primary"]:focus,
    .stButton button[kind="primary"]:active,
    .stButton button[data-testid="baseButton-primary"]:active,
    button[kind="primary"]:active,
    button[data-testid="baseButton-primary"]:active {
        background: #1d4ed8 !important;
        background-color: #1d4ed8 !important;
        border-color: #3b82f6 !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.6) !important;
    }

    .stButton button[kind="secondary"], .stButton button:not([kind="primary"]) {
        background-color: #0f1524 !important;
        border: 1px solid #1e293b !important;
        color: #cbd5e1 !important;
        border-radius: 8px !important;
        font-size: 0.84rem !important;
        transition: all 0.2s ease !important;
    }

    .stButton button:not([kind="primary"]):hover {
        border-color: #3b82f6 !important;
        color: #ffffff !important;
    }

    /* Dashboard Metrics Cards (Native + HTML Container) */
    .metric-card-box {
        background: #0f1524;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px;
        transition: all 0.25s ease;
    }

    .metric-card-box:hover {
        border-color: rgba(59, 130, 246, 0.5);
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.35);
    }

    .metric-card-title {
        font-size: 0.72rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 700;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .metric-card-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #38bdf8;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.1;
    }

    .metric-card-sub {
        font-size: 0.72rem;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* Dashboard Composition Cards */
    .dash-card {
        background: #0f1524;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }

    .dash-card-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #f1f5f9;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .bar-row {
        margin-bottom: 12px;
    }

    .bar-label-group {
        display: flex;
        justify-content: space-between;
        font-size: 0.78rem;
        color: #94a3b8;
        margin-bottom: 4px;
    }

    .bar-track {
        height: 7px;
        background: #1e293b;
        border-radius: 4px;
        overflow: hidden;
    }

    .bar-fill {
        height: 100%;
        border-radius: 4px;
        background: linear-gradient(90deg, #3b82f6 0%, #6366f1 100%);
    }

    /* AST Explanation Card */
    .ast-explain-card {
        background: linear-gradient(135deg, #0d1425 0%, #111827 100%);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 24px;
    }

    .ast-workflow {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #0b0f19;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px 20px;
        margin: 16px 0;
    }

    .ast-step {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #38bdf8;
        font-weight: 600;
    }

    .ast-arrow {
        color: #475569;
        font-weight: 700;
    }

    /* NLP Pipeline Stage Card */
    .nlp-pipeline-card {
        background: #0b0f19;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 18px;
    }

    .nlp-pipeline-steps {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.76rem;
        color: #94a3b8;
    }

    .nlp-step-pill {
        font-family: 'JetBrains Mono', monospace;
        background: #111827;
        border: 1px solid #1e293b;
        color: #38bdf8;
        padding: 4px 10px;
        border-radius: 12px;
    }

    /* NLP Intent Explanation Box */
    .nlp-intent-box {
        background: #0b0f19;
        border: 1px solid #1e293b;
        border-left: 3px solid #3b82f6;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 16px;
    }

    .nlp-intent-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        font-size: 0.78rem;
    }

    .nlp-intent-item {
        display: flex;
        flex-direction: column;
    }

    .nlp-intent-lbl {
        color: #64748b;
        font-size: 0.7rem;
        text-transform: uppercase;
        margin-bottom: 2px;
    }

    .nlp-intent-val {
        color: #cbd5e1;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
    }

    /* Chat Bubbles for Copilot History */
    .chat-bubble-user {
        background: #162036;
        border: 1px solid #23304a;
        border-radius: 10px 10px 2px 10px;
        padding: 12px 16px;
        margin: 10px 0 10px auto;
        max-width: 85%;
        color: #f1f5f9;
        font-size: 0.88rem;
    }

    .chat-bubble-ai {
        background: #0f1524;
        border: 1px solid #1e293b;
        border-radius: 10px 10px 10px 2px;
        padding: 18px;
        margin: 10px auto 16px 0;
        max-width: 95%;
        color: #cbd5e1;
        font-size: 0.88rem;
        line-height: 1.6;
    }

    /* ChangeGraph Node Visualization */
    .graph-visual-card {
        background: #0b0f19;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 24px;
        margin-top: 16px;
    }

    .graph-network-view {
        display: flex;
        justify-content: space-around;
        align-items: center;
        padding: 30px 10px;
        background: #080c14;
        border: 1px solid #1e293b;
        border-radius: 10px;
        margin: 16px 0;
    }

    .node-column {
        display: flex;
        flex-direction: column;
        gap: 12px;
        align-items: center;
    }

    .graph-node-box {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        color: #cbd5e1;
        transition: all 0.2s ease;
    }

    .graph-node-box.central {
        background: linear-gradient(135deg, #1e293b 0%, #1e1b4b 100%);
        border: 1px solid #3b82f6;
        color: #ffffff;
        font-weight: 700;
        box-shadow: 0 0 18px rgba(59, 130, 246, 0.35);
    }

    .graph-node-box.incoming {
        border-color: rgba(56, 189, 248, 0.5);
        color: #38bdf8;
    }

    .graph-node-box.outgoing {
        border-color: rgba(168, 85, 247, 0.5);
        color: #c084fc;
    }

    /* Quota / 429 Graceful Error Card */
    .quota-warning-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(245, 158, 11, 0.4);
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }

    .quota-title {
        font-size: 0.9rem;
        font-weight: 700;
        color: #fbbf24;
        margin-bottom: 4px;
    }

    .quota-desc {
        font-size: 0.82rem;
        color: #cbd5e1;
        line-height: 1.45;
    }

    /* Copilot Evidence Cards */
    .citation-card {
        background-color: #0b0f19;
        border-left: 3px solid #3b82f6;
        border-top: 1px solid #1e293b;
        border-right: 1px solid #1e293b;
        border-bottom: 1px solid #1e293b;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }

    .citation-ref {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        font-weight: 600;
        color: #38bdf8;
        margin-bottom: 4px;
    }

    .citation-snippet {
        font-size: 0.82rem;
        color: #94a3b8;
    }

    /* Typography & Section Titles */
    .section-heading {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0 0 4px 0;
        letter-spacing: -0.3px;
    }

    .section-subheading {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 20px;
    }

    .subsection-title {
        font-size: 1rem;
        font-weight: 600;
        color: #cbd5e1;
        margin: 20px 0 12px 0;
    }
</style>
"""
