import React, { useState, useRef, useEffect } from 'react';
import {
  PlusIcon,
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
  MessageSquareIcon,
  LogOutIcon,
  XIcon,
  SlidersIcon,
  Volume2Icon,
  VolumeXIcon,
  SparklesIcon,
  Trash2Icon
} from '../Common/Icons';
import CuriosityLogo from '../Common/CuriosityLogo';
import ThemeDropdown from '../Common/ThemeDropdown';

export default function Sidebar({
  isOpen,
  setIsOpen,
  isCollapsed,
  setIsCollapsed,
  isHidden,
  setIsHidden,
  onNewSession,
  conversationsList = [],
  activeSessionId,
  onDeleteConversation,
  navigate,
  user,
  guestMode,
  logout,
  autoSpeak,
  setAutoSpeak,
  isSettingsOpen,
  setIsSettingsOpen
}) {
  const [searchQuery, setSearchQuery] = useState('');

  // Only real saved conversations (No mock/demo chats)
  const displayList = conversationsList || [];

  const filteredHistory = displayList.filter(item =>
    item.title?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleToggleCollapse = () => {
    setIsCollapsed(prev => !prev);
  };

  const handleHideSidebar = () => {
    if (setIsHidden) {
      setIsHidden(true);
    }
  };

  const handleNewSessionClick = () => {
    if (onNewSession) onNewSession();
    if (isOpen) setIsOpen(false);
  };

  const handleNavClick = (hash) => {
    navigate(hash);
    if (isOpen) setIsOpen(false);
  };

  const rawName = guestMode 
    ? 'Guest Explorer' 
    : (user?.name?.trim()?.split(' ')[0] || (user?.email ? user.email.split('@')[0].replace(/[0-9_.-]+$/, '') : '') || 'Explorer');
  const displayName = rawName.charAt(0).toUpperCase() + rawName.slice(1);
  const avatarLetter = (displayName.charAt(0) || 'E').toUpperCase();
  const accountEmail = user?.email || (guestMode ? 'Guest Session' : 'Curiosity Member');

  return (
    <aside
      className={`sidebar ${isOpen ? 'open' : ''}`}
      aria-label="Main Navigation Sidebar"
    >
      {/* 1. Header / Logo + Close button */}
      <div className="sidebar-header">
        <div
          className="sidebar-brand"
          onClick={() => handleNavClick('#/')}
          title="Curiosity - Back to Home"
          role="button"
          tabIndex={0}
        >
          <CuriosityLogo size="md" />
        </div>

        <div className="sidebar-header-actions">
          <button
            className="icon-btn sidebar-close-btn"
            onClick={() => setIsOpen(false)}
            aria-label="Close navigation (Esc)"
            title="Close navigation (Esc)"
          >
            <XIcon size={16} />
          </button>
        </div>
      </div>

      {/* 2. Primary Action: + New Chat with [N] Shortcut Badge */}
      <div className="sidebar-actions-section">
        <button
          className="new-chat-btn"
          onClick={handleNewSessionClick}
          title="Start a new chat (Ctrl+N)"
          aria-label="New Chat"
        >
          <div className="new-chat-btn-left">
            <PlusIcon size={16} />
            <span className="btn-label">New Chat</span>
          </div>
          <span className="new-chat-shortcut">[N]</span>
        </button>
      </div>

      {/* 2.5 Quick System Controls: Voices, Auto-Speak & Theme */}
      <div className="sidebar-tools-section">
        {/* Voices (Voice Studio) */}
        <button
          className={`sidebar-tool-btn ${isSettingsOpen ? 'active' : ''}`}
          type="button"
          onClick={() => {
            if (setIsSettingsOpen) setIsSettingsOpen(true);
            if (setIsOpen) setIsOpen(false);
          }}
          title="Voice Studio (Voices)"
        >
          <div className="sidebar-tool-btn-left">
            <SlidersIcon size={15} />
            <span>Voices</span>
          </div>
          <span className="sidebar-tool-badge">Studio</span>
        </button>

        {/* Auto-Speak Toggle */}
        <button
          className={`sidebar-tool-btn ${autoSpeak ? 'active' : ''}`}
          type="button"
          onClick={() => setAutoSpeak && setAutoSpeak(!autoSpeak)}
          title={autoSpeak ? "Auto-Speak: Active (Click to mute)" : "Auto-Speak: Off (Click to enable)"}
        >
          <div className="sidebar-tool-btn-left">
            {autoSpeak ? <Volume2Icon size={15} /> : <VolumeXIcon size={15} />}
            <span>Auto-Speak</span>
          </div>
          <span className={`sidebar-tool-pill ${autoSpeak ? 'on' : 'off'}`}>
            {autoSpeak ? 'ON' : 'OFF'}
          </span>
        </button>

        {/* System Theme */}
        <div className="sidebar-tool-btn sidebar-theme-row">
          <div className="sidebar-tool-btn-left">
            <SparklesIcon size={15} />
            <span>System</span>
          </div>
          <ThemeDropdown />
        </div>
      </div>

      {/* 3. Recent Section Header */}
      <div className="sidebar-recent-header">
        <span>Recent</span>
      </div>

      {/* 4. Scrollable History List */}
      <div className="sidebar-scroll">
        {filteredHistory.map((item, idx) => (
          <SidebarHistoryItem
            key={item.id || idx}
            item={item}
            isActive={item.id === activeSessionId}
            onSelect={() => handleNavClick(`#/workspace/${item.id}`)}
            onDeleteConversation={onDeleteConversation}
          />
        ))}
        {filteredHistory.length === 0 && (
          <div className="sidebar-empty-state" style={{ padding: '16px 14px', fontSize: '12px', color: 'var(--text-muted)' }}>
            <span>No recent chats</span>
          </div>
        )}
      </div>

      {/* 5. Upgrade to Pro Card */}
      <div className="sidebar-pro-card">
        <div className="pro-card-title">Upgrade to Pro</div>
        <div className="pro-card-sub">Upgrade for unlimited use</div>
        <button 
          type="button" 
          className="pro-card-btn"
          onClick={() => alert('Curiosity Pro: Unlimited local VLM inference & multi-voice TTS included.')}
        >
          Upgrade
        </button>
      </div>

      {/* 6. Clean User Profile (Ashutosh) */}
      <div className="sidebar-footer">
        <div
          className="profile-info-wrap"
          title={displayName}
        >
          <div className="profile-avatar-clean">
            {avatarLetter}
          </div>
          <div className="profile-details">
            <span className="profile-name">{displayName}</span>
            <span className="profile-subtext" style={{ fontSize: '10px', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px', display: 'block' }}>{accountEmail}</span>
          </div>
        </div>

        <button
          className="icon-btn logout-btn"
          onClick={logout}
          title={guestMode ? "Exit Session" : "Sign Out"}
          aria-label="Sign Out"
        >
          <LogOutIcon size={15} />
        </button>
      </div>
    </aside>
  );
}

/**
 * SidebarHistoryItem
 * Seamless inline Framer-style undo countdown interaction:
 * When user clicks delete:
 * 1. Directly starts 3-second animated countdown inside the row (NO MODAL).
 * 2. User can either click "Cancel deletion" / press Esc to undo,
 *    or let it finish, which smoothly shows "Deleted", collapses, and permanently removes the chat.
 */
function SidebarHistoryItem({
  item,
  isActive,
  onSelect,
  onDeleteConversation
}) {
  const COUNTDOWN_SECONDS = 3;
  const [status, setStatus] = useState('idle'); // 'idle' | 'countdown' | 'success' | 'collapsing'
  const [timeLeft, setTimeLeft] = useState(COUNTDOWN_SECONDS);
  const timerRef = useRef(null);
  const intervalRef = useRef(null);

  // Clear timers on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // Listen for Escape key during countdown to cancel immediately
  useEffect(() => {
    if (status !== 'countdown') return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        handleCancel(e);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [status]);

  const handleStartDelete = (e) => {
    e.stopPropagation();
    setStatus('countdown');
    setTimeLeft(COUNTDOWN_SECONDS);

    // Tick every second
    intervalRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Trigger success when timer hits 0
    timerRef.current = setTimeout(() => {
      clearInterval(intervalRef.current);
      setStatus('success');

      // Hold success checkmark briefly, then trigger collapse exit
      setTimeout(() => {
        setStatus('collapsing');
        setTimeout(async () => {
          try {
            if (onDeleteConversation) {
              await onDeleteConversation(item.id);
            }
          } catch (err) {
            console.error('Delete conversation failed:', err);
            setStatus('idle');
          }
        }, 300);
      }, 450);
    }, COUNTDOWN_SECONDS * 1000);
  };

  const handleCancel = (e) => {
    if (e) e.stopPropagation();
    if (timerRef.current) clearTimeout(timerRef.current);
    if (intervalRef.current) clearInterval(intervalRef.current);
    setStatus('idle');
    setTimeLeft(COUNTDOWN_SECONDS);
  };

  // State 2: Countdown active ("Cancel deletion [3]")
  if (status === 'countdown') {
    return (
      <div
        className="history-item is-deleting"
        onClick={handleCancel}
        role="button"
        tabIndex={0}
        title="Click to cancel deletion (or press Esc)"
        aria-label={`Deleting ${item.title || 'conversation'}. Click to cancel.`}
      >
        <div className="history-item-delete-row">
          <div className="history-item-undo-left">
            <div className="history-item-undo-icon" title="Click to undo">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M9 14 4 9l5-5" />
                <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11" />
              </svg>
            </div>
            <span className="history-item-cancel-text">Cancel deletion</span>
          </div>

          <div className="history-item-countdown-badge" key={timeLeft}>
            <span>{timeLeft}</span>
          </div>
        </div>

        {/* Depleting timer progress bar */}
        <div
          className="history-item-progress-bar"
          style={{ animationDuration: `${COUNTDOWN_SECONDS}s` }}
        />
      </div>
    );
  }

  // State 3: Success checkmark & collapsing exit
  if (status === 'success' || status === 'collapsing') {
    return (
      <div
        className={`history-item is-deleted ${status === 'collapsing' ? 'is-collapsing' : ''}`}
        aria-label="Deleted"
      >
        <div className="history-item-success-row">
          <div className="history-item-success-icon">
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M20 6 9 17l-5-5" />
            </svg>
          </div>
          <span className="history-item-success-text">Deleted</span>
        </div>
      </div>
    );
  }

  // State 1: Default idle item
  return (
    <div
      className={`history-item ${isActive ? 'active' : ''}`}
      onClick={onSelect}
      title={item.title}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <span className="history-icon" aria-hidden="true">
        <MessageSquareIcon size={14} />
      </span>
      <div className="history-item-content">
        <span className="history-text">{item.title}</span>
        {item.time && <span className="history-time">{item.time}</span>}
      </div>
      <button
        type="button"
        className="history-item-delete-btn"
        onClick={handleStartDelete}
        title="Delete this conversation"
        aria-label={`Delete conversation ${item.title || ''}`}
      >
        <Trash2Icon size={13} />
      </button>
    </div>
  );
}
