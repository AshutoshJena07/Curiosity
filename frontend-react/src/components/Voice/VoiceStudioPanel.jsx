import React, { useState, useRef, useEffect, useMemo } from 'react';
import {
  XIcon,
  PlayIcon,
  PauseIcon,
  SquareIcon,
  CheckIcon,
  ChevronDownIcon,
  SparklesIcon,
  Volume2Icon,
  SearchIcon,
  SlidersIcon
} from '../Common/Icons';

export default function VoiceStudioPanel({
  isOpen,
  onClose,
  selectedVoiceName,
  onSelectVoice,
  selectedEmotion = 'neutral',
  onSelectEmotion,
  emotionsList = [],
  emotionExpressiveness = 0.85,
  setEmotionExpressiveness,
  speechSpeed,
  setSpeechSpeed,
  speechPitch,
  setSpeechPitch,
  isCloudLoading,
  isCloudPlaying,
  isSpeaking,
  isPaused,
  ttsSupported,
  voices = [],
  sarvamVoiceList = [],
  onPlayPreview,
  onPlayResume,
  onPause,
  onStop,
  cloudAudioRef
}) {
  const panelRef = useRef(null);
  const dropdownRef = useRef(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Draggable positioning state
  const [position, setPosition] = useState(() => {
    if (typeof window !== 'undefined') {
      const initialX = Math.max(16, window.innerWidth - 360);
      return { x: initialX, y: 56 };
    }
    return { x: 100, y: 56 };
  });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ startX: 0, startY: 0, initialPosX: 0, initialPosY: 0, hasMoved: false });

  // Handle pointer down on draggable header
  const handleHeaderPointerDown = (e) => {
    if (e.target.closest('button') || e.target.closest('input') || e.target.closest('a')) {
      return;
    }
    e.preventDefault();
    setIsDragging(true);
    dragStartRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialPosX: position.x,
      initialPosY: position.y,
      hasMoved: false
    };
  };

  // Window pointer listeners for smooth dragging
  useEffect(() => {
    if (!isDragging) return;

    const handlePointerMove = (e) => {
      const dx = e.clientX - dragStartRef.current.startX;
      const dy = e.clientY - dragStartRef.current.startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
        dragStartRef.current.hasMoved = true;
      }

      const newX = dragStartRef.current.initialPosX + dx;
      const newY = dragStartRef.current.initialPosY + dy;

      const cardW = panelRef.current ? panelRef.current.offsetWidth : 335;
      const cardH = panelRef.current ? panelRef.current.offsetHeight : 520;
      const maxW = typeof window !== 'undefined' ? window.innerWidth : 1200;
      const maxH = typeof window !== 'undefined' ? window.innerHeight : 800;

      const clampedX = Math.max(8, Math.min(maxW - cardW - 8, newX));
      const clampedY = Math.max(8, Math.min(maxH - 60, newY));

      setPosition({ x: clampedX, y: clampedY });
    };

    const handlePointerUp = () => {
      setIsDragging(false);
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDragging]);

  // Ensure card is docked at top right when opened or window resizes (unless user dragged it)
  useEffect(() => {
    if (isOpen && !dragStartRef.current.hasMoved && typeof window !== 'undefined') {
      setPosition({
        x: Math.max(16, window.innerWidth - 360),
        y: 56
      });
    }

    const handleResize = () => {
      if (!dragStartRef.current.hasMoved && typeof window !== 'undefined') {
        setPosition({
          x: Math.max(16, window.innerWidth - 360),
          y: 56
        });
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isOpen]);

  // Keyboard accessibility and click outside listeners
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (isDropdownOpen) {
          setIsDropdownOpen(false);
        } else {
          onClose();
        }
      }
    };

    const handlePointerDown = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('touchstart', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('touchstart', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isDropdownOpen, isDragging, onClose]);

  // Click outside dropdown menu listener
  useEffect(() => {
    if (!isDropdownOpen) return;

    const handleClickOutsideDropdown = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutsideDropdown);
    return () => document.removeEventListener('mousedown', handleClickOutsideDropdown);
  }, [isDropdownOpen]);

  const currentVoiceMeta = useMemo(() => {
    const cleanId = selectedVoiceName.replace('sarvam-', '').toLowerCase();
    const predefined = sarvamVoiceList.find(v => v.id.toLowerCase() === cleanId);
    if (predefined) {
      return {
        id: `sarvam-${predefined.id}`,
        title: predefined.displayName,
        type: 'Neural Voice',
        accent: predefined.lang || 'hi-IN / en-IN'
      };
    }
    return {
      id: selectedVoiceName,
      title: cleanId === 'shubh' ? 'Shubh (Male)' : 'Ritu (Female)',
      type: 'Neural Voice',
      accent: 'hi-IN / en-IN'
    };
  }, [selectedVoiceName, sarvamVoiceList]);

  // Filtered Sarvam AI bulbul:v3 voices (Priya & Shubh) based on search query
  const filteredSarvam = useMemo(() => {
    if (!searchQuery.trim()) return sarvamVoiceList;
    const q = searchQuery.toLowerCase();
    return sarvamVoiceList.filter(v => 
      (v.displayName && v.displayName.toLowerCase().includes(q)) ||
      (v.id && v.id.toLowerCase().includes(q)) ||
      (v.description && v.description.toLowerCase().includes(q)) ||
      (v.lang && v.lang.toLowerCase().includes(q))
    );
  }, [sarvamVoiceList, searchQuery]);

  if (!isOpen) return null;

  const isAudioActive = Boolean(isCloudPlaying || isSpeaking);
  const isAudioPaused = Boolean(isPaused);

  // Gradient percentages for range slider visuals
  const speedPercent = ((speechSpeed - 0.5) / (2.0 - 0.5)) * 100;
  const pitchPercent = ((speechPitch - 0.5) / (1.5 - 0.5)) * 100;

  return (
    <div className="voice-studio-overlay" aria-label="Voice Studio Modal Background">
      <div
        ref={panelRef}
        className={`voice-studio-card open ${isDragging ? 'is-dragging' : ''}`}
        style={{
          left: `${position.x}px`,
          top: `${position.y}px`,
          right: 'auto',
          bottom: 'auto'
        }}
        role="dialog"
        aria-labelledby="vs-panel-heading"
        aria-modal="true"
      >
        {/* Draggable Header */}
        <div 
          className="vs-header"
          onPointerDown={handleHeaderPointerDown}
        >
          <div className="vs-header-title-wrap">
            <span className="vs-drag-grip">⋮⋮</span>
            <div className="vs-icon-badge">
              <SparklesIcon size={14} className="vs-spark-glow" />
            </div>
            <div>
              <h3 id="vs-panel-heading" className="vs-title">Voice Studio</h3>
              <p className="vs-subtitle">Neural Speech Synthesis</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="vs-close-btn"
            aria-label="Close Voice Studio"
          >
            <XIcon size={14} />
          </button>
        </div>

      <div className="vs-panel-body">
        {/* Section 1: Voice Selector Dropdown */}
        <div className="vs-section">
          <div className="vs-label-row">
            <span className="vs-label">Active Voice Model</span>
            <span className="vs-badge-live">Neural TTS</span>
          </div>

          <div className="vs-dropdown-wrapper" ref={dropdownRef}>
            <button
              type="button"
              className={`vs-dropdown-trigger ${isDropdownOpen ? 'active' : ''}`}
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              aria-haspopup="listbox"
              aria-expanded={isDropdownOpen}
            >
              <div className="vs-trigger-left">
                <div className="vs-voice-avatar">
                  {currentVoiceMeta.type.includes('Neural') || currentVoiceMeta.type.includes('Sarvam') ? (
                    <SparklesIcon size={13} className="vs-avatar-spark" />
                  ) : (
                    <Volume2Icon size={13} />
                  )}
                </div>
                <div className="vs-trigger-info">
                  <span className="vs-trigger-title">{currentVoiceMeta.title}</span>
                  <span className="vs-trigger-sub">{currentVoiceMeta.accent} • {currentVoiceMeta.type}</span>
                </div>
              </div>
              <ChevronDownIcon size={14} className={`vs-chevron ${isDropdownOpen ? 'open' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {isDropdownOpen && (
              <div className="vs-dropdown-menu" role="listbox">
                {/* Search input */}
                <div className="vs-search-box">
                  <SearchIcon size={13} className="vs-search-icon" />
                  <input
                    type="text"
                    placeholder="Search voices or accents..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="vs-search-input"
                    autoFocus
                  />
                  {searchQuery && (
                    <button 
                      type="button" 
                      onClick={() => setSearchQuery('')}
                      className="vs-search-clear"
                    >
                      <XIcon size={12} />
                    </button>
                  )}
                </div>

                <div className="vs-dropdown-scroll">
                  {/* Sarvam AI bulbul:v3 Voices (Priya & Shubh) */}
                  {filteredSarvam.length > 0 && (
                    <div className="vs-group">
                      <div className="vs-group-title">
                        <span>✨ Voices</span>
                        <span className="vs-group-count">{filteredSarvam.length}</span>
                      </div>
                      {filteredSarvam.map((voice) => {
                        const voiceKey = `sarvam-${voice.id}`;
                        const isSelected = selectedVoiceName === voiceKey || selectedVoiceName.replace('sarvam-', '').toLowerCase() === voice.id.toLowerCase();
                        return (
                          <div
                            key={voice.id}
                            className={`vs-item ${isSelected ? 'selected' : ''}`}
                            onClick={() => {
                              onSelectVoice(voiceKey);
                              setIsDropdownOpen(false);
                            }}
                            role="option"
                            aria-selected={isSelected}
                          >
                            <div className="vs-item-details">
                              <div className="vs-item-top">
                                <span className="vs-item-name">{voice.displayName}</span>
                                <span className="vs-item-lang-badge">{voice.lang}</span>
                              </div>
                              <span className="vs-item-desc">{voice.description}</span>
                            </div>
                            {isSelected && <CheckIcon size={14} className="vs-item-check" />}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {filteredSarvam.length === 0 && (
                    <div className="vs-empty-search">
                      <span>No voices matching "{searchQuery}"</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Sliders (Speaking Pace & Expressiveness) */}
        <div className="vs-sliders-wrap">
          {/* Speaking Pace Slider */}
          <div className="vs-slider-box">
            <div className="vs-slider-header">
              <span className="vs-label">Speaking Pace</span>
              <span className="vs-val-pill">{speechSpeed.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="2.0"
              step="0.1"
              value={speechSpeed}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                setSpeechSpeed(val);
                if (cloudAudioRef.current) {
                  cloudAudioRef.current.playbackRate = val;
                }
              }}
              style={{
                background: `linear-gradient(to right, rgba(255,255,255,0.7) 0%, rgba(255,255,255,0.95) ${speedPercent}%, rgba(255,255,255,0.08) ${speedPercent}%)`
              }}
              className="vs-range-slider"
            />
            <div className="vs-range-scale">
              <span>0.5x (Slow)</span>
              <span>1.0x (Normal)</span>
              <span>2.0x (Fast)</span>
            </div>
          </div>

          {/* Emotional Expressiveness Slider (Sarvam Temperature) */}
          <div className="vs-slider-box">
            <div className="vs-slider-header">
              <span className="vs-label">
                Emotion Dynamism
                <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', marginLeft: '6px', fontWeight: 500 }}>
                  (Temperature)
                </span>
              </span>
              <span className="vs-val-pill">{emotionExpressiveness.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="1.00"
              step="0.05"
              value={emotionExpressiveness}
              onChange={(e) => {
                if (setEmotionExpressiveness) {
                  setEmotionExpressiveness(parseFloat(e.target.value));
                }
              }}
              style={{
                background: `linear-gradient(to right, rgba(255,255,255,0.7) 0%, rgba(255,255,255,0.95) ${Math.min(100, Math.max(0, (emotionExpressiveness / 1.0) * 100))}%, rgba(255,255,255,0.08) ${Math.min(100, Math.max(0, (emotionExpressiveness / 1.0) * 100))}%)`
              }}
              className="vs-range-slider"
            />
            <div className="vs-range-scale">
              <span>0.1 (Subtle)</span>
              <span>0.6 (Balanced)</span>
              <span>1.0 (Intense)</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
  );
}
