/* ============================================================
   SOVEREIGN — Chat
   chat.js — message rendering, streaming, tool call trace
   ============================================================ */

class Chat {
  constructor(messagesId) {
    this.container = document.getElementById(messagesId);
    this.isStreaming = false;
    this.currentBubble = null;
    this.currentBubbleContent = null;
  }

  showWelcome() {
    const el = document.getElementById('chat-welcome');
    if (el) el.style.display = '';
  }

  hideWelcome() {
    const el = document.getElementById('chat-welcome');
    if (el) el.style.display = 'none';
  }

  addUserMessage(text, attachments = []) {
    const msg = document.createElement('div');
    msg.className = 'message message-user';
    let attachHTML = '';
    if (attachments.length > 0) {
      attachHTML = `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;justify-content:flex-end;">
        ${attachments.map(a => `<div class="badge badge-muted">${fileIcon(a.type)} ${a.name}</div>`).join('')}
      </div>`;
    }
    msg.innerHTML = `
      ${attachHTML}
      <div class="message-bubble">${escapeHtml(text)}</div>
      <div class="message-meta">${timeNow()}</div>
    `;
    this.container.appendChild(msg);
    if (window.UIMotion) window.UIMotion.animateChatMessage(msg);
    this._scrollToBottom();
    return msg;
  }

  addThinkingIndicator() {
    const el = document.createElement('div');
    el.className = 'thinking-indicator';
    el.innerHTML = `<span class="think-dot"></span><span class="think-dot"></span><span class="think-dot"></span>`;
    this.container.appendChild(el);
    if (window.UIMotion) window.UIMotion.animateChatMessage(el);
    this._scrollToBottom();
    return el;
  }

  removeThinkingIndicator(el) {
    if (el && el.parentNode) {
      el.style.opacity = '0';
      el.style.transition = 'opacity 0.2s';
      setTimeout(() => el.remove(), 200);
    }
  }

  addRouterBanner(text) {
    const banner = document.createElement('div');
    banner.className = 'router-banner';
    banner.innerHTML = `<span class="spinner">⟳</span><span>${text}</span>`;
    this.container.appendChild(banner);
    this._scrollToBottom();
    return banner;
  }

  removeRouterBanner(banner) {
    if (banner && banner.parentNode) {
      banner.style.opacity = '0';
      banner.style.transition = 'opacity 0.3s';
      setTimeout(() => banner.remove(), 300);
    }
  }

  addToolCall(tool, args, result) {
    const icons = {
      kb_search: '🔍', file_read: '📄', code_sandbox: '⚙️',
      doc_gen: '📝', ocr_preprocess: '🖼️', file_write: '💾',
    };
    const card = document.createElement('div');
    card.className = 'tool-call-card';
    card.innerHTML = `
      <div class="tool-call-header" onclick="this.parentElement.classList.toggle('expanded')">
        <span class="tool-call-icon">${icons[tool] || '🔧'}</span>
        <span class="tool-call-name">${tool}()</span>
        <span class="tool-call-status"><span class="badge badge-blue">done</span></span>
        <span class="tool-call-chevron">▶</span>
      </div>
      <div class="tool-call-body">
        <div class="tool-call-args-label">Arguments</div>
        <div class="tool-call-args">${JSON.stringify(args, null, 2)}</div>
        <div class="tool-call-result-label" style="margin-top:8px">Result</div>
        <div class="tool-call-result">${result}</div>
      </div>
    `;
    this.container.appendChild(card);
    if (window.UIMotion) window.UIMotion.animateCard(card);
    if (window.UIMotion) setTimeout(() => window.UIMotion.bindHoverEffects(), 50);
    this._scrollToBottom();
    return card;
  }

  startAssistantMessage() {
    const msg = document.createElement('div');
    msg.className = 'message message-assistant';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    const content = document.createElement('div');
    content.className = 'md-content';

    const cursor = document.createElement('span');
    cursor.className = 'cursor-blink';

    bubble.appendChild(content);
    bubble.appendChild(cursor);

    const meta = document.createElement('div');
    meta.className = 'message-meta';
    meta.textContent = timeNow();

    msg.appendChild(bubble);
    msg.appendChild(meta);
    this.container.appendChild(msg);
    if (window.UIMotion) window.UIMotion.animateChatMessage(msg);

    this.currentBubble = cursor;
    this.currentBubbleContent = content;
    this._scrollToBottom();
    return { msg, content, cursor };
  }

  updateStreamContent(fullText) {
    if (this.currentBubbleContent) {
      this.currentBubbleContent.innerHTML = renderMarkdown(fullText);
      this._scrollToBottom();
    }
  }

  finalizeMessage(fullText) {
    if (this.currentBubbleContent) {
      this.currentBubbleContent.innerHTML = renderMarkdown(fullText);
    }
    if (this.currentBubble) {
      this.currentBubble.remove();
      this.currentBubble = null;
      this.currentBubbleContent = null;
    }
  }

  addCritiqueBadge(text) {
    const badge = document.createElement('div');
    badge.className = 'critique-badge';
    badge.innerHTML = `<span>✓</span><span>${text}</span>`;
    this.container.appendChild(badge);
    if (window.UIMotion) window.UIMotion.animateCard(badge);
    this._scrollToBottom();
  }

  addRbacBlock(text) {
    const card = document.createElement('div');
    card.className = 'rbac-block-card';
    card.innerHTML = `
      <div class="rbac-title">🔒 Access Denied</div>
      <p>The knowledge base contains documents matching your query, but they are classified above your current role level. This attempt has been logged.</p>
    `;
    this.container.appendChild(card);
    if (window.UIMotion) window.UIMotion.animateCard(card);
    this._scrollToBottom();
  }

  addDeliverable(deliverable) {
    if (!deliverable) return;
    const item = document.createElement('div');
    item.className = 'deliverable-item';
    item.innerHTML = `
      <span class="deliverable-icon">${fileIcon(deliverable.type || 'docx')}</span>
      <div class="deliverable-info">
        <div class="deliverable-name">${deliverable.name}</div>
        <div class="deliverable-size">${deliverable.size} · Generated</div>
      </div>
      <span class="deliverable-dl">⬇</span>
    `;
    const downloadAction = () => {
      showToast(`Downloading ${deliverable.name}…`, 'info');
      if (deliverable.url) {
        const a = document.createElement('a');
        a.href = deliverable.url;
        a.download = deliverable.name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
    };

    item.addEventListener('click', downloadAction);

    // Also add to sidebar
    const sidebarList = document.getElementById('deliverables-list');
    if (sidebarList) {
      const emptyState = sidebarList.querySelector('.empty-state');
      if (emptyState) emptyState.remove();
      
      const clone = item.cloneNode(true);
      clone.addEventListener('click', downloadAction);
      sidebarList.insertBefore(clone, sidebarList.firstChild);
    }

    this.container.appendChild(item);
    if (window.UIMotion) window.UIMotion.animateCard(item);
    if (window.UIMotion) setTimeout(() => window.UIMotion.bindHoverEffects(), 50);
    this._scrollToBottom();
  }

  showWelcome() {
    const w = document.getElementById('chat-welcome');
    if (w) {
      w.style.display = 'flex';
      w.style.opacity = '0.7';
    }
  }

  hideWelcome() {
    const w = document.getElementById('chat-welcome');
    if (w) {
      w.style.opacity = '0';
      w.style.transition = 'opacity 0.3s';
      setTimeout(() => w.style.display = 'none', 300);
    }
  }

  _scrollToBottom() {
    this.container.scrollTop = this.container.scrollHeight;
  }
}

// ── Minimal Markdown renderer ──
function renderMarkdown(text) {
  if (!text) return '';
  let clean = text
    .replace(/<think>[\s\S]*?<\/think>/g, '')
    .replace(/<think>[\s\S]*/g, '')
    .replace(/<?\|?im_(?:start|end)\|?>?(?:\w+)?/g, '')
    .trim();

  let html = clean
    // Code blocks (must be before inline code)
    .replace(/```(\w+)?\n([\s\S]*?)```/g, (_, lang, code) =>
      `<pre><code class="language-${lang || ''}">${escapeHtml(code.trim())}</code></pre>`)
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    // Headers
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    // Blockquote
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // HR
    .replace(/^---$/gm, '<hr>')
    // Tables (simple)
    .replace(/\|(.+)\|\n\|[-| :]+\|\n((?:\|.+\|\n?)+)/g, (_, header, rows) => {
      const headers = header.split('|').map(h => h.trim()).filter(Boolean);
      const rowLines = rows.trim().split('\n');
      const thHtml = headers.map(h => `<th>${h}</th>`).join('');
      const tbHtml = rowLines.map(row => {
        const cells = row.split('|').map(c => c.trim()).filter(Boolean);
        return `<tr>${cells.map(c => `<td>${c}</td>`).join('')}</tr>`;
      }).join('');
      return `<table><thead><tr>${thHtml}</tr></thead><tbody>${tbHtml}</tbody></table>`;
    })
    // Unordered list items
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    // Ordered list items
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Wrap consecutive <li> in <ul>
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    // Paragraphs (blank line separated blocks)
    .replace(/\n\n([^<])/g, '\n\n<p>$1')
    .replace(/([^>])\n\n/g, '$1</p>\n\n')
    // Line breaks
    .replace(/\n/g, '<br>');

  return html;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fileIcon(type) {
  const icons = { docx: '📄', pdf: '📋', xlsx: '📊', pptx: '📑', png: '🖼️', jpg: '🖼️', jpeg: '🖼️', csv: '📈' };
  return icons[type?.toLowerCase()] || '📎';
}

function timeNow() {
  return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

window.Chat = Chat;
window.renderMarkdown = renderMarkdown;
window.escapeHtml = escapeHtml;
window.fileIcon = fileIcon;
