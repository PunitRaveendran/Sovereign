/* ============================================================
   SOVEREIGN — File Manager
   file-manager.js — upload zone, file tree, deliverable list
   ============================================================ */

class FileManager {
  constructor() {
    this.uploadedFiles = [];
    this.deliverables = [];
    this._initDropZone();
  }

  _initDropZone() {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('file-input');
    if (!zone) return;

    zone.addEventListener('click', () => input?.click());

    zone.addEventListener('dragover', e => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      if (window.UIMotion && window.Motion) {
    window.Motion.animate(zone, { scale: [1, 1.02, 1] }, { duration: 0.3, easing: 'ease-out' });
    }
      const files = Array.from(e.dataTransfer.files);
      files.forEach(f => this._handleFile(f));
    });

    input?.addEventListener('change', e => {
      Array.from(e.target.files).forEach(f => this._handleFile(f));
      input.value = '';
    });
  }

  _handleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    const entry = {
      id: Date.now() + '_' + file.name,
      name: file.name,
      size: formatBytes(file.size),
      type: ext,
      file,
    };
    this.uploadedFiles.unshift(entry);
    this._renderFiles();
    showToast(`Uploaded: ${file.name}`, 'success');

    // Notify chat input
    if (window.APP) window.APP.pendingAttachments.push(entry);
  }

  _renderFiles() {
    const list = document.getElementById('uploaded-files-list');
    if (!list) return;
    list.innerHTML = '';
    if (this.uploadedFiles.length === 0) {
      list.innerHTML = `<div style="font-size:var(--text-xs);color:var(--text-muted);padding:8px 0;">No files uploaded yet</div>`;
      return;
    }
    this.uploadedFiles.forEach((f, i) => {
      const item = document.createElement('div');
      item.className = 'file-item';
      item.innerHTML = `
        <span class="file-icon">${fileIcon(f.type)}</span>
        <span class="file-name" title="${f.name}">${f.name}</span>
        <span class="file-size">${f.size}</span>
      `;
      list.appendChild(item);

      if (i === 0 && window.UIMotion) window.UIMotion.animateCard(item);
    });
  }
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

window.FileManager = FileManager;
window.formatBytes = formatBytes;
