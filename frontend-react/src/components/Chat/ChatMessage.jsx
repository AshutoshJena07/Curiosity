import React, { useState, useRef, useEffect } from 'react';
import {
  Volume2Icon,
  SquareIcon,
  CopyIcon,
  CheckIcon,
  ImageIcon,
  FileTextIcon,
  PlayIcon,
  PauseIcon,
  DownloadIcon,
  MusicIcon
} from '../Common/Icons';
import MarkdownRenderer from '../Common/MarkdownRenderer';

function StudioAudioPlayer({ audioUrl, fileName }) {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoadedMetadata = () => setDuration(audio.duration || 0);
    const onEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('ended', onEnded);
    };
  }, [audioUrl]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
    }
  };

  const handleSeek = (e) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  };

  const formatTime = (secs) => {
    if (!secs || isNaN(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div 
      className="studio-audio-card" 
      style={{
        margin: '14px 0 10px 0',
        padding: '14px 18px',
        borderRadius: '16px',
        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.75), rgba(15, 23, 42, 0.85))',
        border: '1px solid rgba(255, 255, 255, 0.18)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.35), 0 0 15px rgba(255, 255, 255, 0.04)',
        backdropFilter: 'blur(12px)',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        maxWidth: '520px'
      }}
    >
      <audio ref={audioRef} src={audioUrl} preload="metadata" />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #ffffff, #e2e8f0)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#0f172a',
            boxShadow: '0 0 10px rgba(255, 255, 255, 0.25)',
            flexShrink: 0
          }}>
            <MusicIcon size={16} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.88rem', color: '#f8fafc' }}>
              Studio Audio Performance
            </div>
            <div style={{ fontSize: '0.74rem', color: 'rgba(255, 255, 255, 0.6)' }}>
              {fileName || 'Generated Master Recording (.mp3)'}
            </div>
          </div>
        </div>
        <a 
          href={audioUrl} 
          download={fileName || 'script_performance.mp3'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            padding: '5px 11px',
            borderRadius: '8px',
            fontSize: '0.74rem',
            fontWeight: 600,
            color: '#ffffff',
            background: 'rgba(255, 255, 255, 0.08)',
            border: '1px solid rgba(255, 255, 255, 0.22)',
            textDecoration: 'none',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
          title="Download Audio File"
        >
          <DownloadIcon size={13} />
          <span>Download</span>
        </a>
      </div>

      {/* Scrubber & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          type="button"
          onClick={togglePlay}
          style={{
            width: '38px',
            height: '38px',
            borderRadius: '50%',
            background: isPlaying ? '#ffffff' : 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.35)',
            color: isPlaying ? '#0f172a' : '#ffffff',
            boxShadow: isPlaying ? '0 0 14px rgba(255, 255, 255, 0.4)' : 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            flexShrink: 0
          }}
          aria-label={isPlaying ? "Pause audio" : "Play audio"}
        >
          {isPlaying ? <PauseIcon size={16} /> : <PlayIcon size={16} />}
        </button>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <input
            type="range"
            min={0}
            max={duration || 100}
            value={currentTime}
            onChange={handleSeek}
            style={{
              width: '100%',
              accentColor: '#ffffff',
              cursor: 'pointer'
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'rgba(255, 255, 255, 0.55)' }}>
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatFileSize(bytes) {
  if (!bytes || typeof bytes !== 'number') return '';
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

export default function ChatMessage({ message, onSpeak, isSpeakingThis }) {
  const { role, text, imageUrl, fileBadge, fileName, fileType, fileSize, error, typing, audio_url, audio_filename } = message;
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
            <div className="message-sender" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
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
          <>
            {text && (
              <div className={`message-text ${error ? 'error' : ''}`}>
                <MarkdownRenderer content={text} />
              </div>
            )}
            {audio_url && (
              <StudioAudioPlayer audioUrl={audio_url} fileName={audio_filename} />
            )}
          </>
        )}
      </div>
    </div>
  );
}
