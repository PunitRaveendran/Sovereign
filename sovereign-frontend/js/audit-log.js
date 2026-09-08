/* ============================================================
   SOVEREIGN — Audit Log
   audit-log.js — real-time access event feed
   ============================================================ */

class AuditLog {
  constructor(listId) {
    this.list = document.getElementById(listId);
    this.count = { granted: 0, denied: 0 };
  }

  addEntry(entry) {
    const _animate = window.Motion?.animate;
    const { role, action, tool, kwargs_hash, outcome, prev_hash, hash, timestamp } = entry;
    const isGranted = outcome === 'GRANTED';
    this.count[isGranted ? 'granted' : 'denied']++;

    const item = document.createElement('div');
    item.className = `audit-entry ${isGranted ? 'granted' : 'denied'}`;

    const time = new Date(typeof timestamp === 'number' ? timestamp * 1000 : timestamp);
    const timeStr = time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
    const roleLabel = CONFIG.ROLES[role]?.label || role;

    item.innerHTML = `
      <div class="audit-icon">${isGranted ? '✅' : '❌'}</div>
      <div class="audit-content">
        <div class="audit-resource truncate" title="${action} · ${tool}">${action} · ${tool}</div>
        <div class="audit-detail">${roleLabel} · <span class="badge badge-dot ${isGranted ? 'badge-success' : 'badge-danger'}" style="display:inline-flex;padding:1px 6px;font-size:10px;">${outcome}</span> · <span class="monospace" style="font-size:10px;color:var(--text-muted);" title="Hash: ${hash}">#${(hash || '').slice(0, 8)}</span></div>
      </div>
      <div class="audit-time">${timeStr}</div>
    `;

    // set the starting state BEFORE it's in the DOM so there's no flash of the final state
    item.style.opacity = 0;
    item.style.transform = 'translateY(-10px)';

    this.list.prepend(item);

    if (_animate) {
      // animate it into place
      _animate(item,
        { opacity: [0, 1], transform: ['translateY(-10px)', 'translateY(0px)'] },
        { duration: 0.28, easing: 'ease-out' }
      );

      // quick highlight flash on the row itself — denied entries flash red, granted flash green
      _animate(item,
        { backgroundColor: [isGranted ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)', 'rgba(0,0,0,0)'] },
        { duration: 0.8, easing: 'ease-out' }
      );
    }

    this._updateCounters(isGranted);
    this._trimList(50);
  }

  _updateCounters(isGranted) {
    const _animate = window.Motion?.animate;
    const gEl = document.getElementById('audit-granted-count');
    const dEl = document.getElementById('audit-denied-count');
    if (gEl) {
      gEl.textContent = this.count.granted;
      if (isGranted && _animate) _animate(gEl, { scale: [1.4, 1] }, { duration: 0.3, easing: 'ease-out' });
    }
    if (dEl) {
      dEl.textContent = this.count.denied;
      if (!isGranted && _animate) _animate(dEl, { scale: [1.4, 1] }, { duration: 0.3, easing: 'ease-out' });
    }
  }

  _trimList(max) {
    while (this.list.children.length > max) {
      this.list.removeChild(this.list.lastChild);
    }
  }

  clear() {
    this.list.innerHTML = '';
    this.count = { granted: 0, denied: 0 };
    this._updateCounters();
  }
}

window.AuditLog = AuditLog;