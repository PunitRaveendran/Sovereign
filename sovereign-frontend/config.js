/* ============================================================
   SOVEREIGN — App Config
   config.js — single toggle between mock and live backend
   ============================================================ */

const CONFIG = {
  // ── Toggle this to false when connecting to Punit's backend ──
  MOCK_MODE: false,

  // ── Backend endpoints (used when MOCK_MODE = false) ──
  API_BASE: 'http://localhost:8000',
  WS_BASE:  'ws://localhost:8000',

  ENDPOINTS: {
    TASK:       '/api/v1/task',
    UPLOAD:     '/api/v1/task/upload',
    DOWNLOAD:   '/api/v1/download',
    AUDIT:      '/api/v1/audit',
    WS_METRICS: '/ws/metrics',
    WS_NETWORK: '/ws/network',
  },

  // ── Mock playback speeds (ms) ──
  MOCK: {
    TYPING_SPEED:       18,    // ms per character for token streaming
    VRAM_INTERVAL:      1500,  // ms between VRAM telemetry ticks
    AUDIT_INTERVAL:     4000,  // ms between audit log entries
    NETWORK_INTERVAL:   800,   // ms between network monitor ticks
    ROUTER_BANNER_MS:   900,   // how long the router banner shows before typing
    TOOL_CALL_GAP_MS:   600,   // gap between consecutive tool call cards
  },

  // ── Role definitions ──
  ROLES: {
    web_dev: {
      label: 'Web Dev',
      icon: '👨‍💻',
      levels: ['public'],
      color: '#4f8ef7',
    },
    department_lead: {
      label: 'Dept. Lead',
      icon: '📋',
      levels: ['public', 'department'],
      color: '#00d4aa',
    },
    management: {
      label: 'Management',
      icon: '🏢',
      levels: ['public', 'department', 'management'],
      color: '#ffa502',
    },
    vp_ceo: {
      label: 'VP / CEO',
      icon: '👔',
      levels: ['public', 'department', 'management', 'executive'],
      color: '#a78bfa',
    },
  },

  // ── Models ──
  MODELS: [
    {
      id: 'nemotron-9b',
      name: 'Nemotron-9B',
      shortName: 'Nemotron',
      task: 'Reasoning & Documents',
      vram: '~5.6 GB',
      quant: 'Q4_K_M',
      color: '#a78bfa',
      icon: '🧠',
    },
    {
      id: 'granite-4-8b',
      name: 'Granite 4.1 8B',
      shortName: 'Granite',
      task: 'Code Generation',
      vram: '~5.1 GB',
      quant: 'Q4_K_M',
      color: '#38bdf8',
      icon: '⚙️',
    },
    {
      id: 'qwen-vl-7b',
      name: 'Qwen2.5-VL-7B',
      shortName: 'Qwen-VL',
      task: 'Vision & OCR',
      vram: '~6.2 GB',
      quant: 'Q4/AWQ',
      color: '#fb923c',
      icon: '👁️',
    },
  ],
};

window.CONFIG = CONFIG;
