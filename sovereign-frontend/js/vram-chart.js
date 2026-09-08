
/* ============================================================
   SOVEREIGN — VRAM Chart
   vram-chart.js — live Canvas 2D chart with model swap markers
   ============================================================ */

class VRAMChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.history = [];          // { mb, ts, model }
    this.events = [];           // { index, label, color } model swap markers
    this.maxPoints = 40;
    this.totalMB = 8192;
    this.currentModel = null;
    this.currentUsed = 0;
    this.prevModel = null;

    // Smoothed value shown in the label — animates toward currentUsed instead of snapping
    this.displayedUsed = 0;
    this._labelAnimation = null;

    this.modelColors = {
      'Nemotron-9B': '#a78bfa',
      'Granite-4.1-8B': '#38bdf8',
      'Qwen2.5-VL-7B': '#fb923c',
      'router/Nemotron-4B': '#a3e635',
      'unloading...': '#ff4757',
    };

    this._resize();
    window.addEventListener('resize', () => this._resize());
  }

  _resize() {
    const parent = this.canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const w = parent.clientWidth;
    const h = 80;
    this.canvas.width = w * dpr;
    this.canvas.height = h * dpr;
    this.canvas.style.width = w + 'px';
    this.canvas.style.height = h + 'px';
    this.ctx.scale(dpr, dpr);
    this.logicalWidth = w;
    this.logicalHeight = h;
    this.draw();
  }

  update(data) {
    const { vram_used_mb, model_loaded, total_mb } = data;
    this.totalMB = total_mb || 8192;
    this.currentUsed = vram_used_mb;

    // Detect model swap events
    let swapped = false;
    if (model_loaded !== this.currentModel && model_loaded !== 'unloading...') {
      if (this.currentModel && this.currentModel !== 'unloading...') {
        this.events.push({
          index: this.history.length,
          label: model_loaded,
          color: this.modelColors[model_loaded] || '#4f8ef7',
        });
        swapped = true;
      }
      this.currentModel = model_loaded;
    }

    this.history.push({ mb: vram_used_mb, model: model_loaded });
    if (this.history.length > this.maxPoints) {
      this.history.shift();
      this.events = this.events
        .map(e => ({ ...e, index: e.index - 1 }))
        .filter(e => e.index >= 0);
    }

    this.draw();
    this._animateLabelTo(vram_used_mb);

    if (swapped) this._flashSwap();
  }

  // Smoothly counts the label from its current displayed value to the new one,
  // instead of the text just snapping on every update() call.
  _animateLabelTo(target) {
    const _animate = window.Motion?.animate;
    if (!_animate) {
      this.displayedUsed = target;
      this._updateStats();
      return;
    }
    if (this._labelAnimation) this._labelAnimation.stop();
    const from = this.displayedUsed;
    this._labelAnimation = _animate(from, target, {
      duration: 0.4,
      easing: 'ease-out',
      onUpdate: (latest) => {
        this.displayedUsed = latest;
        this._updateStats();
      },
    });
  }

  // Border-flash on the chart's card when a model swap happens — makes the
  // swap moment (the thing you're actually demoing) visible at a glance,
  // not just inferred from the dashed line appearing on the graph.
  _flashSwap() {
    const _animate = window.Motion?.animate;
    if (!_animate) return;
    const container = this.canvas.closest('.card') || this.canvas.parentElement;
    if (!container) return;
    const color = this.modelColors[this.currentModel] || '#4f8ef7';
    _animate(container,
      {
        boxShadow: [
          `inset 0 0 0px ${color}00`,
          `inset 0 0 24px ${color}55`,
          `inset 0 0 0px ${color}00`
        ]
      },
      { duration: 1.0, easing: 'ease-out' }
    );
  }

  draw() {
    const ctx = this.ctx;
    const W = this.logicalWidth || this.canvas.width;
    const H = this.logicalHeight || this.canvas.height;

    ctx.clearRect(0, 0, W, H);

    if (this.history.length < 2) return;

    const pad = { top: 6, right: 8, bottom: 2, left: 8 };
    const chartW = W - pad.left - pad.right;
    const chartH = H - pad.top - pad.bottom;

    const xScale = chartW / (this.maxPoints - 1);
    const yScale = chartH / this.totalMB;

    const getX = (i) => pad.left + (i + (this.maxPoints - this.history.length)) * xScale;
    const getY = (mb) => pad.top + chartH - mb * yScale;

    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75, 1.0].forEach(pct => {
      const y = getY(this.totalMB * pct);
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(W - pad.right, y);
      ctx.stroke();
    });

    const usedPct = this.currentUsed / this.totalMB;
    let lineColor = '#4f8ef7';
    if (usedPct > 0.85) lineColor = '#ff4757';
    else if (usedPct > 0.65) lineColor = '#ffa502';
    else if (this.currentModel) lineColor = this.modelColors[this.currentModel] || '#4f8ef7';

    const grad = ctx.createLinearGradient(0, pad.top, 0, H);
    grad.addColorStop(0, lineColor + '55');
    grad.addColorStop(1, lineColor + '05');

    ctx.beginPath();
    ctx.moveTo(getX(0), getY(this.history[0].mb));
    for (let i = 1; i < this.history.length; i++) {
      const x0 = getX(i - 1), y0 = getY(this.history[i - 1].mb);
      const x1 = getX(i), y1 = getY(this.history[i].mb);
      const cpx = (x0 + x1) / 2;
      ctx.bezierCurveTo(cpx, y0, cpx, y1, x1, y1);
    }
    const lastX = getX(this.history.length - 1);
    ctx.lineTo(lastX, H);
    ctx.lineTo(pad.left, H);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(getX(0), getY(this.history[0].mb));
    for (let i = 1; i < this.history.length; i++) {
      const x0 = getX(i - 1), y0 = getY(this.history[i - 1].mb);
      const x1 = getX(i), y1 = getY(this.history[i].mb);
      const cpx = (x0 + x1) / 2;
      ctx.bezierCurveTo(cpx, y0, cpx, y1, x1, y1);
    }
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    ctx.shadowColor = lineColor;
    ctx.shadowBlur = 8;
    ctx.stroke();
    ctx.shadowBlur = 0;

    this.events.forEach(evt => {
      const x = getX(evt.index);
      ctx.strokeStyle = evt.color + 'aa';
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(x, pad.top);
      ctx.lineTo(x, H - pad.bottom);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    const dotX = getX(this.history.length - 1);
    const dotY = getY(this.history[this.history.length - 1].mb);
    ctx.beginPath();
    ctx.arc(dotX, dotY, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = lineColor;
    ctx.shadowColor = lineColor;
    ctx.shadowBlur = 10;
    ctx.fill();
    ctx.shadowBlur = 0;
  }

  _updateStats() {
    // Uses the smoothed displayedUsed value, not the raw currentUsed jump
    const usedGB = (this.displayedUsed / 1024).toFixed(1);
    const totalGB = (this.totalMB / 1024).toFixed(0);
    const pct = Math.round((this.displayedUsed / this.totalMB) * 100);

    const usedEl = document.getElementById('vram-used-label');
    const modelEl = document.getElementById('vram-model-label');
    const pctEl = document.getElementById('vram-pct-badge');
    if (usedEl) usedEl.textContent = `${usedGB} / ${totalGB} GB`;
    if (modelEl) modelEl.textContent = this.currentModel || '—';
    if (pctEl) {
      pctEl.textContent = `${pct}%`;
      pctEl.className = 'badge badge-dot monospace ' + (
        pct > 85 ? 'badge-danger' :
          pct > 65 ? 'badge-warning' : 'badge-blue'
      );
    }
  }
}

window.VRAMChart = VRAMChart;