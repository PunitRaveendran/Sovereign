/* ============================================================
   SOVEREIGN — Network Monitor
   network-monitor.js — egress counter + flatline canvas graph
   ============================================================ */

class NetworkMonitor {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      console.warn(`NetworkMonitor: Canvas element '${canvasId}' not found. Flatline graph disabled.`);
      this.ctx = null;
      return;
    }
    this.ctx = this.canvas.getContext('2d');
    this.totalPackets = 0;
    this.history = [];      // always 0 in mock
    this.maxPoints = 60;
    this._motion = window.Motion || null; // guarded, same pattern as your other files
    this._proofInterval = null;

    this._resize();
    window.addEventListener('resize', () => this._resize());
    this._startSovereigntyProof();
  }

  _resize() {
    if (!this.canvas) return;
    const parent = this.canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const w = parent.clientWidth - 32; // account for panel padding
    const h = 36;
    this.canvas.width  = w * dpr;
    this.canvas.height = h * dpr;
    this.canvas.style.width  = w + 'px';
    this.canvas.style.height = h + 'px';
    this.ctx.scale(dpr, dpr);
    this.logicalW = w;
    this.logicalH = h;
    this.draw();
  }

  update(data) {
    const { egress_packets } = data;
    this.totalPackets += egress_packets;
    this.history.push(egress_packets);
    if (this.history.length > this.maxPoints) this.history.shift();

    this.draw();
    this._updateCounter();
  }

  draw() {
    if (!this.ctx) return;
    const ctx  = this.ctx;
    const W = this.logicalW || 260;
    const H = this.logicalH || 36;

    ctx.clearRect(0, 0, W, H);

    const points = this.history.length;
    if (points < 2) {
      this._drawFlatline(ctx, W, H);
      return;
    }

    const maxVal = Math.max(...this.history, 1);
    const xStep  = W / (this.maxPoints - 1);
    const offset = this.maxPoints - points;

    const allZero = this.history.every(v => v === 0);
    if (allZero) {
      this._drawFlatline(ctx, W, H);
      return;
    }

    const getX = (i) => (i + offset) * xStep;
    const getY = (v) => H - 4 - (v / maxVal) * (H - 8);

    ctx.beginPath();
    ctx.moveTo(getX(0), getY(this.history[0]));
    for (let i = 1; i < points; i++) {
      ctx.lineTo(getX(i), getY(this.history[i]));
    }
    ctx.strokeStyle = '#ff4757';
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }

  _drawFlatline(ctx, W, H) {
    const y = H - 10;

    ctx.strokeStyle = 'rgba(255,255,255,0.03)';
    ctx.lineWidth = 1;
    for (let yy = H * 0.25; yy < H; yy += H * 0.25) {
      ctx.beginPath();
      ctx.moveTo(0, yy);
      ctx.lineTo(W, yy);
      ctx.stroke();
    }

    const grad = ctx.createLinearGradient(0, 0, W, 0);
    grad.addColorStop(0,   'rgba(46,213,115,0.1)');
    grad.addColorStop(0.5, 'rgba(46,213,115,0.5)');
    grad.addColorStop(1,   'rgba(46,213,115,0.1)');

    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(W, y);
    ctx.strokeStyle = grad;
    ctx.lineWidth = 1.5;
    ctx.shadowColor = '#2ed573';
    ctx.shadowBlur = 6;
    ctx.stroke();
    ctx.shadowBlur = 0;

    const now = Date.now() / 1000;
    for (let i = 0; i < 8; i++) {
      const phase = (now * 0.3 + i / 8) % 1;
      const x = phase * W;
      const alpha = Math.sin(Math.PI * phase) * 0.6;
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(46,213,115,${alpha})`;
      ctx.fill();
    }

    requestAnimationFrame(() => {
      if (this.history.every(v => v === 0)) this.draw();
    });
  }

  _updateCounter() {
    const el = document.getElementById('egress-packets');
    if (!el) return;
    const prev = this.totalPackets - (this.history[this.history.length - 1] || 0);
    el.textContent = this.totalPackets.toLocaleString();

    if (this._motion && this.totalPackets !== prev) {
      this._motion.animate(
        el,
        { scale: [1.3, 1], color: ['#ff4757', 'var(--text-primary, #fff)'] },
        { duration: 0.4, easing: 'ease-out' }
      );
    }
  }

  // Periodically re-confirms "still 0 packets" with the sovereignty-proved
  // glow from animations.css — reinforces the air-gap claim as an ongoing
  // fact rather than a one-time badge, without you touching anything during
  // the live demo.
  _startSovereigntyProof() {
    this._proofInterval = setInterval(() => {
      if (!this.history.every(v => v === 0)) return; // never flash if real traffic showed up
      this.pulseSovereigntyProof();
    }, 8000);
  }

  // Call this manually too — e.g. wire it to a button, or trigger it right
  // when you switch to the air-gapped laptop in step 5 of your demo script.
  pulseSovereigntyProof() {
    const panel = this.canvas.closest('.right-panel-section');
    if (!panel) return;
    panel.classList.remove('sovereignty-active'); // restart if already mid-animation
    void panel.offsetWidth; // force reflow so the animation replays
    panel.classList.add('sovereignty-active');
    setTimeout(() => panel.classList.remove('sovereignty-active'), 1500);
  }

  destroy() {
    if (this._proofInterval) clearInterval(this._proofInterval);
  }
}

window.NetworkMonitor = NetworkMonitor;