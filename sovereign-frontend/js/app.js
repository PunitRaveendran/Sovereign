/* ============================================================
   SOVEREIGN — App Bootstrap
   app.js — session management, view routing, orchestration
   ============================================================ */

class SovereignApp {
  constructor() {
    this.session = { role: null, user: null };
    this.pendingAttachments = [];
    this.isStreaming = false;

    this.mock       = null;
    this.chat       = null;
    this.vramChart  = null;
    this.netMonitor = null;
    this.auditLog   = null;
    this.router     = null;
    this.fileManager= null;
  }

  async init() {
    this._bindLoginView();
    this._initComponents();
    this._bindDashboard();
    this._showView('login-view');
    if (window.UIMotion) window.UIMotion.animateLoginEntrance();
    if (window.UIMotion) window.UIMotion.bindHoverEffects();

    try {
      this.mock = new MockEngine();
      await this.mock.loadAll();
      this._startTelemetry();
    } catch (e) {
      console.error('Mock data failed to load:', e);
      showToast('Mock data failed to load — check console', 'error');
    }
  }

  // ── View Management ──
  _showView(id) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const el = document.getElementById(id);
    if (el) el.classList.add('active');
  }

  // ── Login ──
  _bindLoginView() {
    const tabs = document.querySelectorAll('.fluid-tab');
    const activePill = document.getElementById('role-active-pill');

    // Initialize pill position if a role is pre-selected (not typically the case on load)
    if (this.session.role && activePill) {
      const activeTab = document.querySelector(`.fluid-tab[data-role="${this.session.role}"]`);
      if (activeTab) {
        activeTab.classList.add('active');
        activePill.style.width = activeTab.offsetWidth + 'px';
        activePill.style.transform = `translateX(${activeTab.offsetLeft - 6}px)`;
        activePill.classList.add('visible');
      }
    }

    tabs.forEach(tab => {
      // Hover triggers the fluid animation and selects the role visually
      tab.addEventListener('mouseenter', () => {
        if (tab.classList.contains('active')) return;

        tabs.forEach(c => {
          c.classList.remove('active');
          c.classList.remove('animating');
        });
        
        tab.classList.add('active');
        
        // Trigger blur animation
        void tab.offsetWidth; 
        tab.classList.add('animating');

        this.session.role = tab.dataset.role;
        this.session.user = "Surya Balakrishnan";

        // Move the pill
        if (activePill) {
          activePill.style.width = tab.offsetWidth + 'px';
          activePill.style.transform = `translateX(${tab.offsetLeft - 6}px)`;
          activePill.classList.add('visible');
        }
      });

      // Click actually routes the user
      tab.addEventListener('click', () => {
        // Ensure role is set in case mouseenter fired late
        this.session.role = tab.dataset.role;
        this.session.user = "Surya Balakrishnan";
        this._updateTopbarRole();

        // Delay slightly for effect before routing
        setTimeout(() => {
          this._showView('auth-view');
        }, 150);
      });
    });

    // Auth screen logic
    const authBtn = document.getElementById('auth-login-btn');
    const authBackBtn = document.getElementById('auth-back-btn');
    const authPassword = document.getElementById('auth-password');

    authBtn?.addEventListener('click', () => {
      if (!this.session.role) return;
      
      const passwords = {
        'web_dev': 'dev2024',
        'department_lead': 'lead2024',
        'management': 'mgmt2024',
        'vp_ceo': 'ceo2024'
      };
      
      const expectedPassword = passwords[this.session.role];
      if (authPassword && authPassword.value !== expectedPassword) {
        showToast('Invalid credentials. Access Denied.', 'error');
        authPassword.value = '';
        return;
      }
      this._enterDashboard();
      if (authPassword) authPassword.value = ''; // clear password
    });

    authPassword?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        authBtn.click();
      }
    });

    authBackBtn?.addEventListener('click', () => {
      this._showView('login-view');
    });
  }

  // ── Dashboard Init ──
  _enterDashboard() {
    this._showView('dashboard-view');
    this._initComponents();
    this._bindDashboard();
    this._updateTopbarRole();
    if (window.UIMotion) {
      window.UIMotion.animateDashboardEntrance();
      setTimeout(() => window.UIMotion.bindHoverEffects(), 100);
    }
  }

  _initComponents() {
    if (this._componentsInitialized) return;
    this._componentsInitialized = true;

    try { this.chat = new Chat('chat-messages'); } catch (e) { console.error('Chat init:', e); }
    try { this.vramChart = new VRAMChart('vram-canvas'); } catch (e) { console.error('VRAMChart init:', e); }
    try { this.netMonitor = new NetworkMonitor('network-canvas'); } catch (e) { console.error('NetMonitor init:', e); }
    try { this.auditLog = new AuditLog('audit-log-list'); } catch (e) { console.error('AuditLog init:', e); }
    try { this.router = new RouterPanel(); this.router.init(); } catch (e) { console.error('Router init:', e); }
    try { this.fileManager = new FileManager(); } catch (e) { console.error('FileManager init:', e); }
  }

  _startTelemetry() {
    if (!this.mock) return;
    if (this.vramChart) {
      this.mock.on('vram', data => this.vramChart.update(data));
      this.mock.startVRAM();
    }
    if (this.netMonitor) {
      this.mock.on('network', data => this.netMonitor.update(data));
      this.mock.startNetwork();
    }
    if (CONFIG.MOCK_MODE) {
      if (this.auditLog) {
        this.mock.on('audit', data => this.auditLog.addEntry(data));
        this.mock.startAuditLog();
      }
    } else {
      this._startLiveAuditPolling();
    }
  }

  _startLiveAuditPolling() {
    setInterval(async () => {
      try {
        const res = await fetch(`${CONFIG.API_BASE}${CONFIG.ENDPOINTS.AUDIT}`);
        if (!res.ok) return;
        const logs = await res.json();
        if (this.auditLog) {
          this.auditLog.clear();
          logs.forEach(log => this.auditLog.addEntry(log));
        }
      } catch (e) {
        // fail silently for polling
      }
    }, 2000);
  }

  _bindDashboard() {
    const sendBtn = document.getElementById('send-btn');
    const input   = document.getElementById('chat-input');

    if (sendBtn && !sendBtn.dataset.bound) {
      sendBtn.dataset.bound = "true";
      sendBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this._sendMessage();
      });
    }

    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    if (sidebarToggleBtn && !sidebarToggleBtn.dataset.bound) {
      sidebarToggleBtn.dataset.bound = "true";
      sidebarToggleBtn.addEventListener('click', () => {
        const leftSidebar = document.getElementById('sidebar');
        const rightSidebar = document.getElementById('right-panel');
        if (leftSidebar) leftSidebar.classList.toggle('force-open');
        if (rightSidebar) rightSidebar.classList.toggle('force-open');
      });
    }

    if (input && !input.dataset.bound) {
      input.dataset.bound = "true";
      input.addEventListener('keydown', e => {
        if (e.key === 'Enter') {
          if (e.shiftKey) {
            // Shift+Enter: allow natural newline in textarea
            return;
          }
          // Enter alone: send message
          e.preventDefault();
          this._sendMessage();
        }
      });

      input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
      });
    }

    const attachBtn = document.getElementById('attach-btn');
    if (attachBtn && !attachBtn.dataset.bound) {
      attachBtn.dataset.bound = "true";
      attachBtn.addEventListener('click', () => {
        document.getElementById('file-input')?.click();
      });
    }

    document.querySelectorAll('.welcome-chip').forEach(chip => {
      if (!chip.dataset.bound) {
        chip.dataset.bound = "true";
        chip.addEventListener('click', () => {
          if (input) {
            input.value = chip.textContent.trim();
            input.focus();
          }
        });
      }
    });

    const clearBtn = document.getElementById('clear-chat-btn');
    if (clearBtn && !clearBtn.dataset.bound) {
      clearBtn.dataset.bound = "true";
      clearBtn.addEventListener('click', () => {
        const msgs = document.getElementById('chat-messages');
        if (msgs) msgs.innerHTML = '';
        if (this.chat) this.chat.showWelcome();
        showToast('Chat cleared', 'info');
      });
    }
  }

  // ── Send Message ──
  async _sendMessage() {
    if (this.isStreaming) return;
    const input = document.getElementById('chat-input');
    const text = input?.value?.trim();
    if (!text) return;

    if (!this.chat) {
      this.chat = new Chat('chat-messages');
    }

    input.value = '';
    input.style.height = 'auto';
    this.isStreaming = true;
    document.getElementById('send-btn')?.classList.add('loading');

    try {
      const attachments = [...this.pendingAttachments];
      this.pendingAttachments = [];

      this.chat.hideWelcome();
      this.chat.addUserMessage(text, attachments);

      if (CONFIG.MOCK_MODE) {
        await this._handleMockResponse(text);
      } else {
        await this._handleLiveResponse(text, attachments);
      }
    } catch (err) {
      console.error('Error in _sendMessage:', err);
    } finally {
      this.isStreaming = false;
      document.getElementById('send-btn')?.classList.remove('loading');
    }
  }

  // ── Mock Response ──
  async _handleMockResponse(text) {
    const scenario = this.mock.routeMessage(text);
    if (!scenario) return;

    const thinking = this.chat.addThinkingIndicator();

    let banner = null;
    let msgHandle = null;
    let fullText = '';

    await this.mock.streamScenario(scenario, {
      onRouter: async (content, modelName, taskType) => {
        this.chat.removeThinkingIndicator(thinking);
        banner = this.chat.addRouterBanner(content);
        this.router.setActiveModel(modelName);
        await mockDelay(CONFIG.MOCK.ROUTER_BANNER_MS);
      },

      onToolCall: (tool, args, result) => {
        this.chat.addToolCall(tool, args, result);
      },

      onToken: (buffer, char) => {
        if (!msgHandle) {
          if (banner) this.chat.removeRouterBanner(banner);
          msgHandle = this.chat.startAssistantMessage();
          fullText = '';
        }
        fullText = buffer;
        this.chat.updateStreamContent(fullText);
      },

      onCritique: (text) => {
        if (msgHandle) this.chat.finalizeMessage(fullText);
        this.chat.addCritiqueBadge(text);
        msgHandle = null;
      },

      onRbacBlock: (text) => {
        this.chat.removeThinkingIndicator(thinking);
        if (banner) this.chat.removeRouterBanner(banner);
        this.chat.addRbacBlock(text);
        this.auditLog.addEntry({
          action: 'RBAC_EVALUATION',
          role: this.session.role,
          tool: 'search_kb',
          kwargs_hash: '99b3ca12ff41',
          outcome: 'DENIED',
          prev_hash: 'fc180aa4231b',
          hash: 'e8bf4391bc4a',
          timestamp: Date.now(),
        });
      },

      onDone: (deliverable) => {
        if (msgHandle) this.chat.finalizeMessage(fullText);
        if (deliverable) this.chat.addDeliverable(deliverable);
        this.router.addRouteDecision(
          text,
          scenario.task_type,
          scenario.model,
          0.91,
          Math.floor(80 + Math.random() * 60),
        );
        msgHandle = null;
        banner = null;
      },
    });
  }

  // ── Live Response (called when MOCK_MODE = false) ──
  async _handleLiveResponse(text, attachments) {
    const thinking = this.chat.addThinkingIndicator();
    try {
      let res;

      if (attachments.length > 0 && attachments[0].file) {
        // Gap 3 Fix: Use FormData + multipart upload endpoint for file attachments
        const formData = new FormData();
        formData.append('file', attachments[0].file);
        formData.append('user_id', this.session.user || 'user');
        formData.append('role', this.session.role || 'web_dev');
        formData.append('prompt', text);

        res = await fetch(`${CONFIG.API_BASE}${CONFIG.ENDPOINTS.UPLOAD}`, {
          method: 'POST',
          body: formData,
        });
      } else {
        // Gap 1 Fix: Send correct field names matching backend TaskRequest
        const payload = {
          task_description: text,
          user_id: this.session.user || 'user',
          role: this.session.role || 'web_dev',
          context_files: attachments.map(a => a.name),
        };

        res = await fetch(`${CONFIG.API_BASE}${CONFIG.ENDPOINTS.TASK}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      this.chat.removeThinkingIndicator(thinking);

      if (!res.ok) {
        let errDetail = `HTTP ${res.status} ${res.statusText}`;
        try {
          const errJson = await res.json();
          errDetail = errJson.detail || JSON.stringify(errJson);
        } catch(e) {
          // ignore parsing error
        }
        console.error('Backend error:', errDetail);
        
        const { msg, content, cursor } = this.chat.startAssistantMessage();
        msg.classList.add('error-message'); // Optional styling
        const fallbackText = `**SYSTEM ERROR:** Agent execution failed.\n\n\`\`\`\n${errDetail}\n\`\`\`\n*Ensure the local LLM inference server (localhost:8080) is running.*`;
        this.chat.updateStreamContent(fallbackText);
        this.chat.finalizeMessage(fallbackText);
        return;
      }

      const data = await res.json();

      // Gap 2 Fix: Unwrap agent_output from backend response
      const agentOutput = data.agent_output || {};
      const plan = agentOutput.plan || '';
      const observations = agentOutput.observations || [];
      const finalOutput = agentOutput.final_output || '';
      const routedModel = data.routed_to_model || '';

      // Show router banner if we have model info
      if (routedModel) {
        const banner = this.chat.addRouterBanner(`Routed to ${routedModel}`);
        this.router.setActiveModel(routedModel);
        await new Promise(r => setTimeout(r, 600));
        this.chat.removeRouterBanner(banner);
      }

      // Show tool call cards from observations
      if (observations.length > 0) {
        for (const obs of observations) {
          // Backend observations are strings like "Executed generate_docx: ..."
          // Parse them into structured tool call cards
          const match = typeof obs === 'string' ? obs.match(/^Executed (\w+):\s*(.*)$/s) : null;
          if (match) {
            this.chat.addToolCall(match[1], {}, match[2].slice(0, 200));
          } else if (typeof obs === 'object' && obs.tool) {
            this.chat.addToolCall(obs.tool, obs.args || {}, obs.result || '');
          }
          await new Promise(r => setTimeout(r, 400));
        }
      }

      // Show final message
      const { msg, content, cursor } = this.chat.startAssistantMessage();
      const displayText = finalOutput || plan || 'Task completed.';
      this.chat.updateStreamContent(displayText);
      this.chat.finalizeMessage(displayText);

      // Check if a deliverable was generated (extract filename from observations)
      for (const obs of observations) {
        const obsStr = typeof obs === 'string' ? obs : JSON.stringify(obs);
        const fileMatch = obsStr.match(/Successfully generated (DOCX|PPTX|XLSX):\s*(\S+)/i);
        if (fileMatch) {
          const fileType = fileMatch[1].toLowerCase();
          const fileName = fileMatch[2];
          this.chat.addDeliverable({
            name: fileName,
            type: fileType,
            size: 'Generated',
            url: `${CONFIG.API_BASE}${CONFIG.ENDPOINTS.DOWNLOAD}/${fileName}`,
          });
        }
      }

      // Add route decision to history
      this.router.addRouteDecision(
        text,
        'live_task',
        routedModel,
        0.92,
        Math.floor(80 + Math.random() * 120),
      );

    } catch (e) {
      this.chat.removeThinkingIndicator(thinking);
      console.error('Connection failed:', e);
      const { msg } = this.chat.startAssistantMessage();
      msg.classList.add('error-message');
      const fallbackText = `**NETWORK ERROR:** Could not connect to the backend gateway.\n\n\`\`\`\n${e.message}\n\`\`\`\n*Ensure the FastAPI server is running on localhost:8000.*`;
      this.chat.updateStreamContent(fallbackText);
      this.chat.finalizeMessage(fallbackText);
    }
  }

  // ── Topbar ──
  _updateTopbarRole() {
    const role = CONFIG.ROLES[this.session.role];
    if (!role) return;

    const nameEl = document.getElementById('topbar-role-name');
    if (nameEl) nameEl.textContent = role.label;

    document.querySelectorAll('.role-option').forEach(opt => {
      opt.classList.toggle('selected', opt.dataset.role === this.session.role);
    });
  }
}

// ── Global Toast ──
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

window.showToast = showToast;

// ── Bootstrap ──
document.addEventListener('DOMContentLoaded', async () => {
  window.APP = new SovereignApp();
  await window.APP.init();
});