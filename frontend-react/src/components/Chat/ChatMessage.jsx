import React, { useState } from 'react';
import {
  Volume2Icon,
  SquareIcon,
  CopyIcon,
  CheckIcon,
  ImageIcon,
  FileTextIcon
} from '../Common/Icons';
import MarkdownRenderer from '../Common/MarkdownRenderer';

function formatFileSize(bytes) {
  if (!bytes || typeof bytes !== 'number') return '';
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

export default function ChatMessage({ message, onSpeak, isSpeakingThis }) {
  const { role, text, imageUrl, fileBadge, fileName, fileType, fileSize, error, typing } = message;
  const isBot = role === 'bot';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  // Determine dynamic message timestamp
  const displayTime = message.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Has attachment (image or document)
  const isImageAttachment = Boolean(imageUrl || fileType === 'image');
  const isDocAttachment = Boolean(!imageUrl && (fileBadge || fileType === 'document' || fileName));
  const docDisplayName = fileName || fileBadge || 'Document';

  return (
    <div className={`message-row ${role}`}>
      {/* Bot Avatar: Only rendered for Curiosity bot */}
      {isBot && (
        <div className="message-avatar">
          <img 
            src="/favicon.svg" 
            alt="Curiosity" 
            className="chat-rabbit-avatar" 
          />
        </div>
      )}

      {/* Message Body Content */}
      <div className="message-body">
        {/* Bot Header: Curiosity + Actions (Never shown for user) */}
        {isBot && (
          <div className="message-header">
            <div className="message-sender">
              <span>Curiosity</span>
              <span className="message-meta message-timestamp">• {displayTime}</span>
            </div>

            {!typing && (
              <div className="message-actions">
                {/* Voice synthesis button */}
                <button 
                  className="message-btn"
                  type="button"
                  onClick={() => onSpeak && onSpeak(message.id, text)}
                  title={isSpeakingThis ? "Stop reading response" : "Read response aloud"}
                  style={{ color: isSpeakingThis ? 'var(--accent-primary)' : 'inherit', fontWeight: isSpeakingThis ? '700' : '600' }}
                >
                  {isSpeakingThis ? (
                    <>
                      <SquareIcon size={12} />
                      <span>Stop</span>
                    </>
                  ) : (
                    <>
                      <Volume2Icon size={12} />
                      <span>Read</span>
                    </>
                  )}
                </button>

                {/* Copy button */}
                <button 
                  className="message-btn"
                  type="button"
                  onClick={handleCopy}
                  title="Copy response text"
                >
                  {copied ? (
                    <>
                      <CheckIcon size={12} />
                      <span>Copied</span>
                    </>
                  ) : (
                    <>
                      <CopyIcon size={12} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Attachment Box: Rendered ABOVE the text message if image or document was provided */}
        {isImageAttachment && imageUrl && (
          <div className="message-attachment-box image-attachment-card">
            <div className="attachment-box-header">
              <div className="attachment-box-title">
                <ImageIcon size={13} />
                <span>Image Attachment</span>
              </div>
              {fileName && <span className="attachment-box-filename" title={fileName}>{fileName}</span>}
            </div>
            <div className="attachment-box-image-wrap">
              <img 
                src={imageUrl} 
                alt={fileName || "Image attachment"} 
                className="attachment-box-img"
              />
            </div>
          </div>
        )}

        {isDocAttachment && (
          <div className="message-attachment-box document-attachment-card">
            <div className="attachment-box-header">
              <div className="attachment-box-title">
                <FileTextIcon size={13} />
                <span>Document</span>
              </div>
            </div>
            <div className="attachment-doc-body">
              <div className="doc-icon-badge">
                <FileTextIcon size={18} />
              </div>
              <div className="doc-info">
                <span className="doc-name" title={docDisplayName}>
                  {docDisplayName}
                </span>
                <span className="doc-meta">
                  {docDisplayName.split('.').pop()?.toUpperCase() || 'DOCUMENT'}
                  {fileSize ? ` • ${formatFileSize(fileSize)}` : ''}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Render typing dots or text response */}
        {typing ? (
          <div className="typing">
            <span></span>
            <span></span>
            <span></span>
          </div>
        ) : (
          text && (
            <div className={`message-text ${error ? 'error' : ''}`}>
              <MarkdownRenderer content={text} />
            </div>
          )
        )}
      </div>
    </div>
  );
}
