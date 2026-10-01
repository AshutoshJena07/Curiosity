import React, { useEffect, useRef } from 'react';
import { XIcon, MessageSquareIcon, ArrowRightIcon, CopyIcon, CheckIcon } from '../Common/Icons';

export default function FloatingHistoryModal({ 
  session, 
  onClose, 
  onOpenInWorkspace 
}) {
  const modalRef = useRef(null);
  const [copied, setCopied] = React.useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };

    const handlePointerDown = (e) => {
      if (modalRef.current && !modalRef.current.contains(e.target)) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handlePointerDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handlePointerDown);
    };
  }, [onClose]);

  if (!session) return null;

  const handleCopy = () => {
    const textToCopy = session.assistantOutput || session.summary || '';
    if (!textToCopy) return;
    navigator.clipboard.writeText(textToCopy).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="floating-modal-backdrop" aria-label="History Detail Modal Overlay">
      <div 
        ref={modalRef} 
        className="floating-modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-history-title"
      >
        {/* Header */}
        <div className="floating-modal-header">
          <div className="floating-modal-header-left">
            <div className="floating-modal-icon-wrap">
              <MessageSquareIcon size={16} />
            </div>
            <div>
              <h3 id="modal-history-title" className="floating-modal-title">
                {session.title || 'Untitled Session'}
              </h3>
              <div className="floating-modal-meta">
                {session.tag && <span className="floating-modal-tag">{session.tag}</span>}
                {session.time && <span className="floating-modal-time">• {session.time}</span>}
              </div>
            </div>
          </div>
          <button 
            type="button" 
            className="floating-modal-close"
            onClick={onClose}
            title="Close (Esc)"
          >
            <XIcon size={16} />
          </button>
        </div>

        {/* Content Body: User Input + Assistant Output */}
        <div className="floating-modal-body">
          {/* User Input Section */}
          <div className="floating-turn user-turn">
            <div className="floating-turn-header">
              <span className="floating-turn-badge user">User Input</span>
              {session.imageUrl && <span className="floating-media-pill">Attached Image</span>}
            </div>
            <div className="floating-turn-content">
              {session.userInput || session.prompt || 'No user prompt recorded.'}
            </div>
          </div>

          {/* Assistant Output Section */}
          <div className="floating-turn assistant-turn">
            <div className="floating-turn-header">
              <span className="floating-turn-badge assistant">Curiosity Output</span>
              <button 
                type="button" 
                className="floating-copy-btn"
                onClick={handleCopy}
                title="Copy response"
              >
                {copied ? <CheckIcon size={13} /> : <CopyIcon size={13} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <div className="floating-turn-content output-text">
              {session.assistantOutput || session.output || session.response || 'No response recorded.'}
            </div>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="floating-modal-footer">
          <button
            type="button"
            className="floating-modal-btn secondary"
            onClick={onClose}
          >
            Close
          </button>
          <button
            type="button"
            className="floating-modal-btn primary"
            onClick={() => {
              if (onOpenInWorkspace) onOpenInWorkspace(session);
              onClose();
            }}
          >
            <span>Open in Workspace</span>
            <ArrowRightIcon size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
