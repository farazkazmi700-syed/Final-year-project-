/**
 * frontend/static/js/app.js
 * ==========================
 * All frontend logic for the LLaMA 3 chatbot.
 * FR2: Chat UI, Feedback Panel | FR5: API connectivity
 *
 * Organized into modules:
 *   api       — fetch wrappers for backend calls
 *   ui        — DOM rendering helpers
 *   feedback  — feedback panel logic
 *   analytics — load and render stats + charts
 *   app       — main controller (init, event listeners)
 */

'use strict';

/* ════════════════════════════════════════════════════════════════════════
   API MODULE — backend communication
   ═══════════════════════════════════════════════════════════════════════ */
const api = {
  /**
   * Send a message to the backend and get the AI response.
   * POST /chat/send
   */
  async sendMessage(content, sessionId) {
    const res = await fetch('/chat/send', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ content, session_id: sessionId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    return res.json();
  },

  /** GET /chat/sessions — list all sessions for the current user */
  async getSessions() {
    const res = await fetch('/chat/sessions', { credentials: 'include' });
    if (!res.ok) throw new Error('Failed to load sessions');
    return res.json();
  },

  /** GET /chat/history/:id — get all messages in a session */
  async getHistory(sessionId) {
    const res = await fetch(`/chat/history/${sessionId}`, { credentials: 'include' });
    if (!res.ok) throw new Error('Failed to load history');
    return res.json();
  },

  /** DELETE /chat/session/:id — delete a session */
  async deleteSession(sessionId) {
    const res = await fetch(`/chat/session/${sessionId}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    if (!res.ok) throw new Error('Failed to delete session');
    return res.json();
  },

  /** POST /feedback/submit — save user feedback */
  async submitFeedback(payload) {
    const res = await fetch('/feedback/submit', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Feedback submission failed');
    }
    return res.json();
  },

  /** GET /analytics/stats — aggregated usage statistics */
  async getStats() {
    const res = await fetch('/analytics/stats', { credentials: 'include' });
    if (!res.ok) throw new Error('Failed to load stats');
    return res.json();
  },

  /** GET /analytics/graphs — base64 chart images */
  async getGraphs() {
    const res = await fetch('/analytics/graphs', { credentials: 'include' });
    if (!res.ok) throw new Error('Failed to load charts');
    return res.json();
  },

  /** GET /analytics/health — Groq connection check */
  async checkHealth() {
    const res = await fetch('/analytics/health', { credentials: 'include' });
    return res.json();
  },
};

/* ════════════════════════════════════════════════════════════════════════
   UI MODULE — DOM helpers
   ═══════════════════════════════════════════════════════════════════════ */
const ui = {
  /** Move analytics/feedback into separate left-side sidebar panels. */
  prepareSidebarPanels() {
    const tabs = document.querySelector('.sidebar-tabs');
    const analyticsPanel = document.getElementById('tab-analytics');
    const existingFeedback = document.getElementById('feedback-panel');

    if (tabs && !tabs.querySelector('[data-tab="feedback"]')) {
      const btn = document.createElement('button');
      btn.className = 'tab-btn';
      btn.dataset.tab = 'feedback';
      btn.textContent = 'Feedback';
      tabs.appendChild(btn);
    }

    if (analyticsPanel && existingFeedback && !document.getElementById('tab-feedback')) {
      const feedbackTab = document.createElement('div');
      feedbackTab.className = 'tab-panel';
      feedbackTab.id = 'tab-feedback';
      analyticsPanel.insertAdjacentElement('afterend', feedbackTab);

      existingFeedback.removeAttribute('style');
      existingFeedback.classList.add('sidebar-feedback-panel', 'feedback-empty');
      feedbackTab.appendChild(existingFeedback);

      const headerText = existingFeedback.querySelector('.feedback-header span');
      if (headerText) headerText.textContent = 'Rate response';

      const emptyState = document.createElement('div');
      emptyState.className = 'feedback-empty-state';
      emptyState.id = 'feedback-empty-state';
      emptyState.textContent = 'Select Rate under an assistant message.';
      existingFeedback.insertBefore(emptyState, existingFeedback.children[1] || null);

      const form = document.createElement('div');
      form.className = 'feedback-form';
      while (emptyState.nextSibling) {
        form.appendChild(emptyState.nextSibling);
      }
      existingFeedback.appendChild(form);
    }
  },

  /** Activate one sidebar panel by name. */
  switchSidebarTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
      panel.classList.toggle('active', panel.id === `tab-${tabName}`);
    });
    if (tabName === 'analytics') analytics.load();
  },

  /** Format an ISO timestamp to HH:MM */
  formatTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  },

  /** Escape HTML to prevent XSS in message content */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },

  /**
   * Convert plain text with code blocks (``` ... ```) to HTML.
   * Handles inline `code`, **bold**, and newlines.
   */
  formatMessage(text) {
    // Code blocks
    text = text.replace(/```([\s\S]*?)```/g, (_, code) => {
      return `<pre><code>${ui.escapeHtml(code.trim())}</code></pre>`;
    });
    // Inline code
    text = text.replace(/`([^`]+)`/g, (_, code) => {
      return `<code>${ui.escapeHtml(code)}</code>`;
    });
    // Bold
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Newlines to <br> (but not inside pre blocks)
    text = text.replace(/\n/g, '<br>');
    return text;
  },

  /** Build a message bubble element */
  createMessageEl(role, content, msgId, timestamp) {
    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.dataset.msgId = msgId || '';

    const avatar = role === 'user' ? '👤' : '🤖';
    const timeStr = ui.formatTime(timestamp);
    const formattedContent = role === 'assistant'
      ? ui.formatMessage(content)
      : ui.escapeHtml(content);

    const feedbackBtn = role === 'assistant' && msgId
      ? `<button class="btn-feedback-trigger" onclick="feedback.open('${msgId}')">★ Rate</button>`
      : '';

    div.innerHTML = `
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-content">
        <div class="msg-bubble">${formattedContent}</div>
        <div class="msg-meta">
          <span>${timeStr}</span>
          ${feedbackBtn}
        </div>
      </div>
    `;
    return div;
  },

  /** Add a message to the chat window and scroll to bottom */
  appendMessage(role, content, msgId, timestamp) {
    const container = document.getElementById('messages-container');

    // Hide welcome screen on first message
    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.remove();

    const el = ui.createMessageEl(role, content, msgId, timestamp);
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
  },

  /** Show an animated typing indicator while waiting for response */
  showTyping() {
    const container = document.getElementById('messages-container');
    const welcome = document.getElementById('welcome-message');
    if (welcome) welcome.remove();

    const div = document.createElement('div');
    div.className = 'message assistant typing-indicator';
    div.id = 'typing-indicator';
    div.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-content">
        <div class="msg-bubble">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  },

  /** Remove typing indicator */
  hideTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
  },

  /** Render the session list in the sidebar */
  renderSessions(sessions) {
    const list = document.getElementById('session-list');
    if (!sessions || sessions.length === 0) {
      list.innerHTML = '<div class="empty-sessions">No chats yet. Start a new one!</div>';
      return;
    }
    list.innerHTML = sessions.map(s => `
      <div class="session-item ${s.session_id === app.currentSessionId ? 'active' : ''}"
           data-id="${s.session_id}"
           onclick="app.loadSession('${s.session_id}')">
        <div class="session-info">
          <div class="session-title">${ui.escapeHtml(s.title || 'New Chat')}</div>
          <div class="session-meta">${s.message_count} messages</div>
        </div>
        <button class="session-delete"
                onclick="event.stopPropagation(); app.deleteSession('${s.session_id}')"
                title="Delete">🗑</button>
      </div>
    `).join('');
  },

  /** Update the chat header title */
  setTitle(title) {
    document.getElementById('current-session-title').textContent = title || 'New Chat';
  },

  /** Update connection status indicator */
  setConnectionStatus(online, text) {
    const dot  = document.querySelector('.status-dot');
    const span = document.querySelector('.status-text');
    dot.className = `status-dot ${online ? 'online' : 'offline'}`;
    span.textContent = text;
  },
};

/* ════════════════════════════════════════════════════════════════════════
   FEEDBACK MODULE
   FR2: Feedback panel (rating, correctness, length type)
   ═══════════════════════════════════════════════════════════════════════ */
const feedback = {
  currentMessageId: null,
  selectedRating:      0,
  selectedCorrectness: null,
  selectedLength:      null,

  /** Open the feedback panel for a specific AI message */
  open(messageId) {
    feedback.currentMessageId = messageId;
    feedback.selectedRating      = 0;
    feedback.selectedCorrectness = null;
    feedback.selectedLength      = null;

    // Reset UI
    document.querySelectorAll('.star').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('selected'));
    document.getElementById('feedback-comment').value = '';
    document.getElementById('feedback-status').textContent = '';
    document.getElementById('feedback-status').className = 'feedback-status';

    document.getElementById('feedback-panel').classList.remove('feedback-empty');
    ui.switchSidebarTab('feedback');
  },

  /** Close the feedback panel */
  close() {
    document.getElementById('feedback-panel').classList.add('feedback-empty');
    feedback.currentMessageId = null;
  },

  /** Set the star rating (1–5) */
  setRating(value) {
    feedback.selectedRating = value;
    document.querySelectorAll('.star').forEach(s => {
      s.classList.toggle('active', parseInt(s.dataset.value) <= value);
    });
  },

  /** Submit feedback to the backend */
  async submit() {
    const statusEl = document.getElementById('feedback-status');

    // Validate
    if (!feedback.selectedRating) {
      statusEl.textContent = 'Please select a star rating.';
      statusEl.className = 'feedback-status error';
      return;
    }
    if (!feedback.selectedCorrectness) {
      statusEl.textContent = 'Please select a correctness rating.';
      statusEl.className = 'feedback-status error';
      return;
    }
    if (!feedback.selectedLength) {
      statusEl.textContent = 'Please select a length rating.';
      statusEl.className = 'feedback-status error';
      return;
    }

    const payload = {
      message_id:    feedback.currentMessageId,
      session_id:    app.currentSessionId,
      rating:        feedback.selectedRating,
      correctness:   feedback.selectedCorrectness,
      length_rating: feedback.selectedLength,
      comment:       document.getElementById('feedback-comment').value.trim() || null,
    };

    try {
      await api.submitFeedback(payload);
      statusEl.textContent = '✅ Feedback saved. Thank you!';
      statusEl.className = 'feedback-status';
      setTimeout(feedback.close, 1500);
    } catch (err) {
      statusEl.textContent = `❌ ${err.message}`;
      statusEl.className = 'feedback-status error';
    }
  },
};

/* ════════════════════════════════════════════════════════════════════════
   ANALYTICS MODULE — load and render stats + charts
   ═══════════════════════════════════════════════════════════════════════ */
const analytics = {
  loaded: false,

  /** Load stats and charts from backend, render in sidebar */
  async load() {
    if (analytics.loaded) return;
    const panel = document.getElementById('analytics-panel');
    panel.innerHTML = '<div class="loading-spinner">Loading analytics...</div>';

    try {
      const [stats, graphs] = await Promise.all([api.getStats(), api.getGraphs()]);
      analytics.render(panel, stats, graphs);
      analytics.loaded = true;
    } catch (err) {
      panel.innerHTML = `<div class="loading-spinner">❌ ${err.message}</div>`;
    }
  },

  /** Render stats cards and chart images */
  render(panel, stats, graphs) {
    panel.innerHTML = `
      <!-- Stats Cards -->
      <div class="stat-card">
        <h4>Total Messages</h4>
        <div class="stat-value">${stats.total_messages || 0}</div>
        <div class="stat-sub">${stats.user_messages || 0} sent · ${stats.assistant_messages || 0} received</div>
      </div>
      <div class="stat-card">
        <h4>Sessions</h4>
        <div class="stat-value">${stats.total_sessions || 0}</div>
        <div class="stat-sub">${stats.messages_last_7_days || 0} messages this week</div>
      </div>
      <div class="stat-card">
        <h4>Avg. Rating</h4>
        <div class="stat-value">${stats.avg_rating || '—'} ⭐</div>
        <div class="stat-sub">${stats.total_feedback || 0} ratings submitted</div>
      </div>

      <!-- Charts -->
      <div class="analytics-charts">
        <p style="font-size:12px;color:var(--text-muted);margin-bottom:4px;">Daily Activity</p>
        <img class="chart-img" src="${graphs.daily_activity}" alt="Daily Activity" />

        <p style="font-size:12px;color:var(--text-muted);margin:8px 0 4px;">Response Quality</p>
        <img class="chart-img" src="${graphs.correctness_pie}" alt="Correctness" />

        <p style="font-size:12px;color:var(--text-muted);margin:8px 0 4px;">Rating Distribution</p>
        <img class="chart-img" src="${graphs.rating_dist}" alt="Ratings" />
      </div>
    `;
  },

  /** Force reload (call after new feedback is submitted) */
  reload() {
    analytics.loaded = false;
  },
};

/* ════════════════════════════════════════════════════════════════════════
   APP CONTROLLER — main logic
   ═══════════════════════════════════════════════════════════════════════ */
const app = {
  currentSessionId: null,
  isLoading:        false,

  /** Called on page load — wire up all events and load initial data */
  async init() {
    ui.prepareSidebarPanels();
    app.bindEvents();
    await app.loadSessions();
    await app.checkConnection();
    // Auto-resize textarea as user types
    app.autoResizeInput();
  },

  /** Attach all DOM event listeners */
  bindEvents() {
    // Send button click
    document.getElementById('btn-send').addEventListener('click', app.handleSend);

    // Enter key in textarea (Shift+Enter = newline)
    document.getElementById('message-input').addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        app.handleSend();
      }
    });

    // New chat button
    document.getElementById('btn-new-chat').addEventListener('click', app.startNewChat);

    // Sidebar toggle
    document.getElementById('btn-sidebar-toggle').addEventListener('click', () => {
      document.getElementById('sidebar').classList.toggle('collapsed');
    });

    // Tab switching (Chats / Analytics)
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        ui.switchSidebarTab(btn.dataset.tab);
      });
    });

    // Star rating clicks
    document.querySelectorAll('.star').forEach(star => {
      star.addEventListener('click', () => feedback.setRating(parseInt(star.dataset.value)));
    });

    // Toggle buttons (correctness + length)
    document.querySelectorAll('#correctness-group .toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#correctness-group .toggle-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        feedback.selectedCorrectness = btn.dataset.value;
      });
    });
    document.querySelectorAll('#length-group .toggle-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#length-group .toggle-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        feedback.selectedLength = btn.dataset.value;
      });
    });

    // Feedback submit / close
    document.getElementById('btn-submit-feedback').addEventListener('click', async () => {
      await feedback.submit();
      analytics.reload(); // refresh charts after feedback
    });
    document.getElementById('btn-close-feedback').addEventListener('click', feedback.close);
  },

  /** Auto-grow textarea as user types */
  autoResizeInput() {
    const input = document.getElementById('message-input');
    input.addEventListener('input', () => {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 160) + 'px';
    });
  },

  /** Send a message (triggered by button or Enter key) */
  async handleSend() {
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    if (!content || app.isLoading) return;

    // Disable input while waiting
    app.isLoading = true;
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('btn-send').disabled = true;

    // Show user message immediately (optimistic UI)
    ui.appendMessage('user', content, null, new Date().toISOString());

    // Show typing indicator
    ui.showTyping();

    try {
      const result = await api.sendMessage(content, app.currentSessionId);

      ui.hideTyping();

      // Set session ID from response (for new sessions)
      app.currentSessionId = result.session_id;

      // Render AI response
      ui.appendMessage('assistant', result.response, result.message_id, result.timestamp);

      // Refresh session list (title may have been updated)
      await app.loadSessions();

    } catch (err) {
      ui.hideTyping();
      ui.appendMessage('assistant',
        `⚠️ Error: ${err.message}. Please try again.`,
        null,
        new Date().toISOString()
      );
    } finally {
      app.isLoading = false;
      document.getElementById('btn-send').disabled = false;
      input.focus();
    }
  },

  /** Load all sessions from backend and render sidebar list */
  async loadSessions() {
    try {
      const data = await api.getSessions();
      ui.renderSessions(data.sessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  },

  /** Load a specific session's messages into the chat window */
  async loadSession(sessionId) {
    if (sessionId === app.currentSessionId) return;

    try {
      const data = await api.getHistory(sessionId);
      app.currentSessionId = sessionId;

      // Clear chat window
      const container = document.getElementById('messages-container');
      container.innerHTML = '';

      // Render all messages
      data.messages.forEach(msg => {
        ui.appendMessage(msg.role, msg.content, msg.id, msg.timestamp);
      });

      // Find and display session title
      const sessionData = await api.getSessions();
      const session = sessionData.sessions.find(s => s.session_id === sessionId);
      ui.setTitle(session?.title || 'Chat');

      // Update active state in sidebar
      document.querySelectorAll('.session-item').forEach(el => {
        el.classList.toggle('active', el.dataset.id === sessionId);
      });

    } catch (err) {
      console.error('Failed to load session:', err);
    }
  },

  /** Start a fresh chat session */
  startNewChat() {
    app.currentSessionId = null;
    const container = document.getElementById('messages-container');
    container.innerHTML = `
      <div class="welcome-message" id="welcome-message">
        <div class="welcome-icon">🤖</div>
        <h2>New Chat</h2>
        <p>Ask me anything — I'll remember the conversation.</p>
        <div class="suggestion-chips">
          <button class="chip" onclick="app.sendSuggestion('Explain machine learning in simple terms')">Machine learning</button>
          <button class="chip" onclick="app.sendSuggestion('Write a Python hello world program')">Python code</button>
          <button class="chip" onclick="app.sendSuggestion('Give me 3 tips for better writing')">Writing tips</button>
        </div>
      </div>
    `;
    ui.setTitle('New Chat');
    feedback.close();
    document.getElementById('message-input').focus();
    document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
  },

  /** Delete a session (with confirmation) */
  async deleteSession(sessionId) {
    if (!confirm('Delete this conversation? This cannot be undone.')) return;
    try {
      await api.deleteSession(sessionId);
      if (app.currentSessionId === sessionId) app.startNewChat();
      await app.loadSessions();
    } catch (err) {
      alert(`Failed to delete: ${err.message}`);
    }
  },

  /** Send a suggestion chip message */
  sendSuggestion(text) {
    document.getElementById('message-input').value = text;
    app.handleSend();
  },

  /** Check Groq API connection and update status indicator */
  async checkConnection() {
    try {
      const result = await api.checkHealth();
      if (result.status === 'ok') {
        ui.setConnectionStatus(true, 'Connected');
      } else {
        ui.setConnectionStatus(false, 'AI Offline');
        console.warn('Groq health check failed:', result.message);
      }
    } catch {
      ui.setConnectionStatus(false, 'No Connection');
    }
  },
};

// ── Bootstrap ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => app.init());
