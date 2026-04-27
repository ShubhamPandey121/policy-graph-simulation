import React from 'react';
import { Sparkles, Plus, History, Trash2, Moon, Sun, Settings } from 'lucide-react';

const formatTimeAgo = (dateStr) => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`;
  return `${Math.floor(diffDays / 30)} month${Math.floor(diffDays / 30) > 1 ? 's' : ''} ago`;
};

export default function Sidebar({ 
  theme, 
  setTheme, 
  isOpen, 
  conversations, 
  currentConversationId, 
  onNewChat, 
  onSelectConversation, 
  onDeleteConversation 
}) {
  return (
    <aside id="sidebar" className={`sidebar ${isOpen ? 'active' : ''}`}>
      <div className="sidebar-header">
        <div className="brand">
          <div className="brand-icon-wrapper">
            <Sparkles className="brand-icon" />
            <div className="brand-glow"></div>
          </div>
          <div>
            <h1 className="brand-title">Policy AI</h1>
            <p className="brand-subtitle">Intelligent Analysis</p>
          </div>
        </div>

        <button onClick={onNewChat} className="new-chat-btn">
          <Plus size={18} />
          <span>New Simulation</span>
        </button>
      </div>

      <div className="sidebar-content">
        <div className="conversations-header">
          <History size={14} />
          <span>Recent Simulations</span>
        </div>
        <div className="conversations-list">
          {conversations.length === 0 ? (
            <div className="empty-state">
              <MessageSquare className="icon mx-auto" size={48} />
              <p style={{ fontSize: '0.875rem', color: 'var(--muted-foreground)' }}>No simulations yet</p>
              <p style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)', opacity: 0.6, marginTop: '0.25rem' }}>Start a new simulation to begin</p>
            </div>
          ) : (
            conversations.map((conv, index) => (
              <div 
                key={conv.id}
                className={`conversation-item ${conv.id === currentConversationId ? 'active' : ''}`}
                onClick={() => onSelectConversation(conv.id)}
                style={{ animationDelay: `${index * 0.03}s` }}
              >
                <div className="conversation-info">
                  <div className="conversation-title">{conv.title}</div>
                  <div className="conversation-time">{formatTimeAgo(conv.updatedAt)}</div>
                </div>
                <button className="delete-btn" onClick={(e) => onDeleteConversation(conv.id, e)}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="sidebar-footer">
        <button 
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')} 
          className="sidebar-footer-btn"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
        </button>
        <button className="sidebar-footer-btn">
          <Settings size={18} />
          <span>Settings</span>
        </button>
      </div>
    </aside>
  );
}
