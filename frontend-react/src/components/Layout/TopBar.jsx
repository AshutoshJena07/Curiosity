import React from 'react';
import { MenuIcon, LayoutDashboardIcon } from '../Common/Icons';
import CuriosityLogo from '../Common/CuriosityLogo';

export default function TopBar({
  isSidebarOpen,
  setIsSidebarOpen,
  navigate,
  guestMode
}) {
  return (
    <header className="topbar transparent-topbar" aria-label="Application Header">
      {/* 1. Left Cluster: 3-line Menu Toggle & Clean Brand */}
      <div className="topbar-left">
        <button
          className="icon-btn topbar-sidebar-toggle-btn"
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          aria-label="Toggle navigation sidebar (Ctrl+B)"
          title="Toggle Navigation Menu (Ctrl+B)"
        >
          <MenuIcon size={18} />
        </button>

        {/* Clean Brand Title */}
        <div className="topbar-breadcrumb">
          <CuriosityLogo 
            size="md" 
            onClick={() => navigate('#/')} 
          />
        </div>
      </div>

      {/* 2. Right Cluster: Clean Minimal */}
      <div className="topbar-right">
      </div>
    </header>
  );
}
