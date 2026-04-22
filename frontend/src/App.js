import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

const API = 'http://127.0.0.1:8000';

function formatTime(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleTimeString('en-NG', { hour: '2-digit', minute: '2-digit' });
}

function getInitials(name) {
  return name ? name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2) : 'OJ';
}

function ReportCard({ analysis }) {
  if (!analysis) return null;
  const score = analysis.health_score ?? '—';
  const scoreColor = score >= 70 ? '#25d366' : score >= 40 ? '#f0b429' : '#e53e3e';
  return (
    <div className="report-card">
      <div className="report-title">📊 Weekly Business Report</div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 4 }}>
        <span className="health-score" style={{ color: scoreColor }}>{score}</span>
        <span style={{ color: '#8696a0', fontSize: 13 }}>/100 health score</span>
      </div>
      <div style={{ fontSize: 12, color: '#8696a0', marginBottom: 10 }}>
        {analysis.overall_health}
      </div>

      {analysis.weekly_narrative && (
        <>
          <div className="section-label">This Week's Story</div>
          <div className="narrative-text">{analysis.weekly_narrative}</div>
        </>
      )}

      {analysis.weekly_narrative_pidgin && (
        <>
          <div className="section-label" style={{ marginTop: 10 }}>In Pidgin</div>
          <div className="narrative-text" style={{ fontStyle: 'italic' }}>
            {analysis.weekly_narrative_pidgin}
          </div>
        </>
      )}

      {(analysis.key_finding_1 || analysis.key_finding_2 || analysis.key_finding_3) && (
        <>
          <div className="section-label">Key Findings</div>
          {analysis.key_finding_1 && <div className="finding-item">• {analysis.key_finding_1}</div>}
          {analysis.key_finding_2 && <div className="finding-item">• {analysis.key_finding_2}</div>}
          {analysis.key_finding_3 && <div className="finding-item">• {analysis.key_finding_3}</div>}
        </>
      )}

      {(analysis.action_1 || analysis.action_2) && (
        <>
          <div className="section-label">Actions To Take</div>
          {analysis.action_1 && <div className="action-item">✅ {analysis.action_1}</div>}
          {analysis.action_2 && <div className="action-item">✅ {analysis.action_2}</div>}
        </>
      )}

      {analysis.warning && (
        <div style={{
          marginTop: 10, background: '#2d1b1b', border: '1px solid #7b2d2d',
          borderRadius: 8, padding: '8px 10px', fontSize: 13, color: '#fc8181'
        }}>
          ⚠️ {analysis.warning}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ msg }) {
  const isTrader = msg.sender === 'trader';
  const isReport = msg.type === 'report';

  return (
    <div className={`message-row ${isTrader ? 'trader' : 'ojamoni'}`}>
      {isReport ? (
        <ReportCard analysis={msg.analysis} />
      ) : (
        <div className="bubble">
          <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
          <div className="bubble-time">
            {formatTime(msg.timestamp)}
            {isTrader && ' ✓✓'}
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [traders, setTraders] = useState([]);
  const [selectedTrader, setSelectedTrader] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const audioInputRef = useRef(null);

  // Load traders on mount
  useEffect(() => {
    axios.get(`${API}/traders`)
      .then(res => {
        setTraders(res.data.traders);
        // Auto-select first trader (Amaka) for demo
        if (res.data.traders.length > 0) {
          selectTrader(res.data.traders[0]);
        }
      })
      .catch(() => console.error('Backend not reachable — is uvicorn running?'));
  }, []);

  // Auto-refresh chat every 5 seconds
  useEffect(() => {
    if (!selectedTrader) return;
    const interval = setInterval(() => {
      loadChat(selectedTrader.id, false);
    }, 5000);
    return () => clearInterval(interval);
  }, [selectedTrader]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  function loadChat(traderId, showLoading = true) {
    axios.get(`${API}/chat-history/${traderId}`)
      .then(res => {
        const raw = res.data.messages || [];
        const formatted = raw.map(m => ({
          id: m.id,
          sender: m.sender,
          text: m.message,
          timestamp: m.timestamp,
          type: 'text',
        }));
        setMessages(formatted);
      })
      .catch(err => console.error('Failed to load chat', err));
  }

  function selectTrader(trader) {
    setSelectedTrader(trader);
    loadChat(trader.id);
  }

  async function sendMessage() {
    if (!inputText.trim() || !selectedTrader || isLoading) return;
    const text = inputText.trim();
    setInputText('');

    // Optimistically add trader message to UI
    const traderMsg = {
      id: Date.now(),
      sender: 'trader',
      text,
      timestamp: new Date().toISOString(),
      type: 'text',
    };
    setMessages(prev => [...prev, traderMsg]);
    setIsTyping(true);
    setIsLoading(true);

    try {
      const form = new FormData();
      form.append('trader_id', selectedTrader.id);
      form.append('text', text);
      const res = await axios.post(`${API}/message`, form);
      const reply = {
        id: Date.now() + 1,
        sender: 'ojamoni',
        text: res.data.reply,
        timestamp: new Date().toISOString(),
        type: 'text',
      };
      setIsTyping(false);
      setMessages(prev => [...prev, reply]);
    } catch (err) {
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ojamoni',
        text: '❌ Could not reach OjaMoni backend. Make sure uvicorn is running!',
        timestamp: new Date().toISOString(),
        type: 'text',
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function sendImage(e) {
    const file = e.target.files[0];
    if (!file || !selectedTrader) return;
    e.target.value = '';

    const traderMsg = {
      id: Date.now(),
      sender: 'trader',
      text: `📷 Sent image: ${file.name}`,
      timestamp: new Date().toISOString(),
      type: 'text',
    };
    setMessages(prev => [...prev, traderMsg]);
    setIsTyping(true);
    setIsLoading(true);

    try {
      const form = new FormData();
      form.append('trader_id', selectedTrader.id);
      form.append('file', file);
      const res = await axios.post(`${API}/upload-image`, form);
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ojamoni',
        text: res.data.reply,
        timestamp: new Date().toISOString(),
        type: 'text',
      }]);
    } catch {
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ojamoni',
        text: '❌ Image upload failed.',
        timestamp: new Date().toISOString(),
        type: 'text',
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function sendVoice(e) {
    const file = e.target.files[0];
    if (!file || !selectedTrader) return;
    e.target.value = '';

    const traderMsg = {
      id: Date.now(),
      sender: 'trader',
      text: `🎤 Sent voice note: ${file.name}`,
      timestamp: new Date().toISOString(),
      type: 'text',
    };
    setMessages(prev => [...prev, traderMsg]);
    setIsTyping(true);
    setIsLoading(true);

    try {
      const form = new FormData();
      form.append('trader_id', selectedTrader.id);
      form.append('file', file);
      const res = await axios.post(`${API}/voice-note`, form);
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ojamoni',
        text: res.data.reply,
        timestamp: new Date().toISOString(),
        type: 'text',
      }]);
    } catch {
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ojamoni',
        text: '❌ Voice note upload failed.',
        timestamp: new Date().toISOString(),
        type: 'text',
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function fetchWeeklyReport() {
    if (!selectedTrader || isLoading) return;
    setIsTyping(true);
    setIsLoading(true);

    // Add a "requested" message from trader side
    setMessages(prev => [...prev, {
      id: Date.now(),
      sender: 'trader',
      text: '📊 Send me my weekly report',
      timestamp: new Date().toISOString(),
      type: 'text',
    }]);

    try {
      const res = await axios.get(`${API}/weekly-report/${selectedTrader.id}`);
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ojamoni',
        text: res.data.report,
        timestamp: new Date().toISOString(),
        type: 'report',
        analysis: res.data.analysis,
      }]);
    } catch {
      setIsTyping(false);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        sender: 'ojamoni',
        text: '❌ Could not generate weekly report.',
        timestamp: new Date().toISOString(),
        type: 'text',
      }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function triggerNudge() {
    if (!selectedTrader) return;
    try {
      const res = await axios.post(`${API}/trigger-nudge/${selectedTrader.id}`);
      setMessages(prev => [...prev, {
        id: Date.now(),
        sender: 'ojamoni',
        text: res.data.nudge,
        timestamp: new Date().toISOString(),
        type: 'text',
      }]);
    } catch {
      console.error('Nudge failed');
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const lastMessage = messages[messages.length - 1];
  const previewText = lastMessage?.text?.slice(0, 40) || 'No messages yet';

  return (
    <div className="app">
      {/* ── SIDEBAR ── */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="logo-circle">OJ</div>
          <h2>OjaMoni</h2>
        </div>
        <div className="sidebar-search">
          <input type="text" placeholder="🔍  Search traders" readOnly />
        </div>
        <div className="trader-list">
          {traders.map(trader => (
            <div
              key={trader.id}
              className={`trader-item ${selectedTrader?.id === trader.id ? 'active' : ''}`}
              onClick={() => selectTrader(trader)}
            >
              <div className="avatar">{getInitials(trader.name)}</div>
              <div className="trader-info">
                <div className="trader-name">{trader.name}</div>
                <div className="trader-preview">{previewText}</div>
              </div>
              <div className="trader-time">
                {lastMessage ? formatTime(lastMessage.timestamp) : ''}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── CHAT PANEL ── */}
      {selectedTrader ? (
        <div className="chat-panel">
          {/* Header */}
          <div className="chat-header">
            <div className="chat-header-left">
              <div className="avatar" style={{ width: 38, height: 38, fontSize: 13 }}>
                {getInitials(selectedTrader.name)}
              </div>
              <div className="chat-header-info">
                <div className="name">{selectedTrader.name}</div>
                <div className="status">● online</div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="nudge-btn" onClick={triggerNudge} disabled={isLoading}>
                Send Nudge
              </button>
              <button className="weekly-report-btn" onClick={fetchWeeklyReport} disabled={isLoading}>
                📊 Weekly Report
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="messages-area">
            {messages.map(msg => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {isTyping && (
              <div className="message-row ojamoni">
                <div className="typing-indicator">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input bar */}
          <div className="input-bar">
            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              onChange={sendImage}
            />
            <input
              type="file"
              ref={audioInputRef}
              accept="audio/*"
              onChange={sendVoice}
            />
            <button className="icon-btn" title="Send image" onClick={() => fileInputRef.current.click()}>
              📷
            </button>
            <button className="icon-btn" title="Send voice note" onClick={() => audioInputRef.current.click()}>
              🎤
            </button>
            <input
              type="text"
              placeholder="Type a message..."
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button className="send-btn" onClick={sendMessage} disabled={isLoading || !inputText.trim()}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="white">
                <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </div>
      ) : (
        <div className="empty-state">
          <div className="big-logo">OJ</div>
          <h3>Welcome to OjaMoni</h3>
          <p>Select a trader from the left to view their chat history</p>
        </div>
      )}
    </div>
  );
}