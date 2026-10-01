import React, { useState, useEffect, useRef } from 'react';
import gsap from 'gsap';
import Sidebar from './Sidebar';
import TopBar from './TopBar';

export default function MainLayout({
  children,
  isSidebarOpen,
  setIsSidebarOpen,
  autoSpeak,
  setAutoSpeak,
  isSettingsOpen,
  setIsSettingsOpen,
  serverStatus,
  onNewSession,
  conversationsList,
  activeSessionId,
  onSelectConversation,
  onDeleteConversation,
  navigate,
  user,
  guestMode,
  logout
}) {
  const layoutRef = useRef(null);

  // TopBar cinematic GSAP entrance
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.fromTo(
        '.topbar',
        { opacity: 0, y: -20 },
        { opacity: 1, y: 0, duration: 1.0, ease: 'power4.out', force3D: true }
      );
    }, layoutRef);

    return () => ctx.revert();
  }, []);

  // Sidebar collapsed state (State B: 58px) persisted in localStorage
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    return localStorage.getItem('sidebar_collapsed') === 'true';
  });

  // Sidebar hidden state (State C: 0px / completely hidden) persisted in localStorage
  const [isSidebarHidden, setIsSidebarHidden] = useState(() => {
    return localStorage.getItem('sidebar_hidden') === 'true';
  });

  // Sync states to localStorage
  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', String(isSidebarCollapsed));
  }, [isSidebarCollapsed]);

  useEffect(() => {
    localStorage.setItem('sidebar_hidden', String(isSidebarHidden));
  }, [isSidebarHidden]);

  // Global Keyboard shortcut: Ctrl+B / Cmd+B to toggle sidebar overlay, Esc to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        const activeTag = document.activeElement?.tagName?.toLowerCase();
        if (activeTag !== 'input' && activeTag !== 'textarea') {
          e.preventDefault();
          setIsSidebarOpen(prev => !prev);
        }
      }
      if (e.key === 'Escape' && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSidebarOpen, setIsSidebarOpen]);

  return (
    <div className="app-container" ref={layoutRef}>
      {/* 1. Smooth Overlay Backdrop for clicking outside to close */}
      <div
        className={`sidebar-overlay ${isSidebarOpen ? 'active' : ''}`}
        onClick={() => setIsSidebarOpen(false)}
        aria-hidden="true"
      />

      {/* 2. Left Sidebar Navigation Drawer (Smooth Overlay) with Quick Controls */}
      <Sidebar
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        onNewSession={onNewSession}
        conversationsList={conversationsList}
        activeSessionId={activeSessionId}
        onDeleteConversation={onDeleteConversation}
        navigate={navigate}
        user={user}
        guestMode={guestMode}
        logout={logout}
        autoSpeak={autoSpeak}
        setAutoSpeak={setAutoSpeak}
        isSettingsOpen={isSettingsOpen}
        setIsSettingsOpen={setIsSettingsOpen}
      />

      {/* 3. Primary Full-width Main Content (Chat UI is locked in dead center) */}
      <main className="main-content workspace-fade-in" id="main-workspace-content">
        <TopBar
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          navigate={navigate}
          guestMode={guestMode}
        />

        {/* Primary Full-width Workspace Body */}
        <div className="workspace-body-layout">
          <div className="workspace-center-stage">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
