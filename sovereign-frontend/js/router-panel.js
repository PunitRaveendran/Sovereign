/* ============================================================
   SOVEREIGN — Router Panel
   router-panel.js — model card switching + routing history
   ============================================================ */

class RouterPanel {
  constructor() {
    this.activeModelId = null;
    this.routeHistory = [];
    this.maxHistory = 5;
    this._pulseAnimation = null; // tracks the currently running glow so we can stop it on switch
  }

  init() {
    this._renderModelCards();
  }

  _renderModelCards() {
    const container = document.getElementById('model-cards');
    if (!container) return;
    container.innerHTML = '';
    CONFIG.MODELS.forEach(model => {
      const card = document.createElement('div');
      card.className = 'model-card';
      card.id = `model-card-${model.id}`;
      card.style.setProperty('--model-color', model.color);
      card.innerHTML = `
        <div class="model-dot"></div>
        <div class="model-info">
          <div class="model-name">${model.icon} ${model.name}</div>
          <div class="model-task">${model.task}</div>
        </div>
        <div class="model-vram-badge">${model.vram}</div>
      `;
      container.appendChild(card);
    });
  }

  setActiveModel(modelName) {
    const _animate = window.Motion?.animate;
    if (!_animate) return;

    // Stop any glow animation currently running on the previously active card
    if (this._pulseAnimation) {
      this._pulseAnimation.stop();
      this._pulseAnimation = null;
    }

    // Deactivate all, and clear any leftover inline box-shadow from the glow
    document.querySelectorAll('.model-card').forEach(card => {
      card.classList.remove('active');
      card.style.boxShadow = '';
    });

    // Find matching model
    const model = CONFIG.MODELS.find(m =>
      modelName.toLowerCase().includes(m.shortName.toLowerCase()) ||
      m.name.toLowerCase().includes(modelName.toLowerCase().split('-')[0])
    );

    if (model) {
      this.activeModelId = model.id;
      const card = document.getElementById(`model-card-${model.id}`);
      if (card) {
        card.classList.add('active');
        card.style.setProperty('--model-color', model.color);

        // Quick pop-in on selection (replaces the old CSS-only flash)
        _animate(card, { scale: [0.97, 1] }, { duration: 0.25, easing: 'ease-out' });

        // Continuous glow pulse for as long as this card stays active
        this._pulseAnimation = _animate(card,
          {
            boxShadow: [
              `0 0 0px ${model.color}00`,
              `0 0 18px ${model.color}99`,
              `0 0 0px ${model.color}00`
            ]
          },
          { duration: 1.6, repeat: Infinity, easing: 'ease-in-out' }
        );
      }
    }
  }

  addRouteDecision(query, taskType, modelName, confidence, latencyMs) {
    this.routeHistory.unshift({ query, taskType, modelName, confidence, latencyMs, ts: Date.now() });
    if (this.routeHistory.length > this.maxHistory) this.routeHistory.pop();
    this._renderHistory();
    this._updateRoutingBanner(taskType, modelName, confidence, latencyMs);
  }

  _renderHistory() {
    const _animate = window.Motion?.animate;
    const container = document.getElementById('route-history');
    if (!container) return;
    container.innerHTML = '';
    this.routeHistory.forEach((item, index) => {
      const model = CONFIG.MODELS.find(m => m.name.includes(item.modelName.split('-')[0]));
      const color = model?.color || '#4f8ef7';
      const div = document.createElement('div');
      div.className = 'route-history-item';
      div.innerHTML = `
        <div class="route-history-query" title="${item.query}">${item.query.slice(0, 38)}${item.query.length > 38 ? '…' : ''}</div>
        <div class="route-history-model" style="color:${color};">${item.modelName.split('/')[1] || item.modelName}</div>
      `;
      container.appendChild(div);

      // Only the newest entry (top of the list) needs an entrance animation —
      // the rest are just being re-rendered in their already-settled state.
      if (index === 0 && _animate) {
        div.style.opacity = 0;
        div.style.transform = 'translateX(-8px)';
        _animate(div,
          { opacity: [0, 1], transform: ['translateX(-8px)', 'translateX(0px)'] },
          { duration: 0.25, easing: 'ease-out' }
        );
      }
    });
  }

  _updateRoutingBanner(taskType, modelName, confidence, latencyMs) {
    const _animate = window.Motion?.animate;
    const banner = document.getElementById('routing-banner');
    if (!banner) return;
    const taskLabel = {
      'code_generation': 'Code Generation',
      'document_reasoning': 'Document Reasoning',
      'vision_ocr': 'Vision / OCR',
    }[taskType] || taskType;
    banner.textContent = '';
    banner.style.display = 'flex';
    const pct = Math.round((confidence || 0.9) * 100);
    const ms = latencyMs || 95;
    banner.innerHTML = `
      <span style="font-size:12px">⚡</span>
      <span>Last routed to <strong>${modelName}</strong> · <em>${taskLabel}</em> · ${pct}% confidence · <span class="monospace">${ms}ms</span></span>
    `;

    // Brief highlight sweep whenever the banner text changes, so a repeat
    // route to the same model still visibly registers as "new"
    if (_animate) {
      _animate(banner,
        { backgroundColor: ['rgba(79,142,247,0.18)', 'rgba(0,0,0,0)'] },
        { duration: 0.9, easing: 'ease-out' }
      );
    }
  }
}

window.RouterPanel = RouterPanel;