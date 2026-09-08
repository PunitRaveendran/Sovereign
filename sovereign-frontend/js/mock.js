/* ============================================================
   SOVEREIGN — Mock Engine
   mock.js — fixture loader + playback for all panels
   ============================================================ */

class MockEngine {
  constructor() {
    this.fixtures = {};
    this.vramIndex = 0;
    this.auditIndex = 0;
    this.vramTimer = null;
    this.auditTimer = null;
    this.networkTimer = null;
    this.listeners = {};
  }

  async loadAll() {
    const files = ['vram_stream', 'audit_log', 'router_decisions', 'chat_responses'];
    await Promise.all(files.map(async (name) => {
      const res = await fetch(`mock/${name}.json`);
      this.fixtures[name] = await res.json();
    }));
  }

  // ── Event bus ──
  on(event, fn) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(fn);
  }
  emit(event, data) {
    (this.listeners[event] || []).forEach(fn => fn(data));
  }

  // ── VRAM Telemetry ──
  startVRAM() {
    const data = this.fixtures['vram_stream'];
    let idx = 0;
    const tick = () => {
      if (idx >= data.length) idx = 0;
      this.emit('vram', data[idx]);
      idx++;
    };
    tick();
    this.vramTimer = setInterval(tick, CONFIG.MOCK.VRAM_INTERVAL);
  }

  stopVRAM() { clearInterval(this.vramTimer); }

  // ── Audit Log ──
  startAuditLog() {
    const data = this.fixtures['audit_log'];
    let idx = 0;
    const tick = () => {
      if (idx >= data.length) {
        clearInterval(this.auditTimer);
        return;
      }
      this.emit('audit', data[idx]);
      idx++;
    };
    // Replay historical entries quickly, then slow down
    data.slice(0, 3).forEach((entry, i) => {
      setTimeout(() => this.emit('audit', entry), i * 300);
    });
    idx = 3;
    this.auditTimer = setInterval(tick, CONFIG.MOCK.AUDIT_INTERVAL);
  }

  stopAuditLog() { clearInterval(this.auditTimer); }

  // ── Network Monitor ──
  startNetwork() {
    const tick = () => {
      this.emit('network', { egress_packets: 0, egress_bytes: 0, timestamp: Date.now() });
    };
    tick();
    this.networkTimer = setInterval(tick, CONFIG.MOCK.NETWORK_INTERVAL);
  }

  stopNetwork() { clearInterval(this.networkTimer); }

  // ── Route a message and return scenario ──
  routeMessage(text) {
    const scenarios = this.fixtures['chat_responses'];
    const lower = text.toLowerCase();

    // RBAC check first based on session role
    const role = window.APP?.session?.role;
    const rbacTrigger = ['vendor negotiation', 'q3 strategy', 'board', 'executive', 'confidential'];
    const isRbacQuery = rbacTrigger.some(kw => lower.includes(kw));
    if (isRbacQuery && role === 'web_dev') {
      return scenarios.find(s => s.scenario === 'rbac_denied');
    }

    // Keyword routing
    for (const scenario of scenarios) {
      if (scenario.scenario === 'rbac_denied') continue;
      if (scenario.trigger_keywords.some(kw => lower.includes(kw))) {
        return scenario;
      }
    }

    // Default: document reasoning
    return scenarios.find(s => s.scenario === 'document_reasoning');
  }

  // ── Stream scenario steps ──
  async streamScenario(scenario, callbacks) {
    const { onRouter, onToolCall, onToken, onCritique, onRbacBlock, onDone } = callbacks;

    for (const step of scenario.steps) {
      await delay(step.delay || 0);

      switch (step.type) {
        case 'router':
          onRouter?.(step.content, scenario.model, scenario.task_type);
          break;

        case 'tool_call':
          onToolCall?.(step.tool, step.args, step.result);
          await delay(CONFIG.MOCK.TOOL_CALL_GAP_MS);
          break;

        case 'token_stream':
          await streamText(step.content, onToken, CONFIG.MOCK.TYPING_SPEED);
          break;

        case 'critique':
          onCritique?.(step.content);
          break;

        case 'rbac_block':
          onRbacBlock?.(step.content);
          break;

        case 'done':
          onDone?.(step.deliverable);
          break;
      }
    }
  }
}

// ── Helpers ──
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function streamText(text, onChunk, speedMs = 18) {
  let buffer = '';
  for (let i = 0; i < text.length; i++) {
    buffer += text[i];
    onChunk?.(buffer, text[i]);
    if (text[i] !== ' ') {
      await delay(speedMs);
    }
  }
}

window.MockEngine = MockEngine;
window.mockDelay = delay;
