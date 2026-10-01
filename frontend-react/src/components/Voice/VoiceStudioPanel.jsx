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
  PlusIcon,
  SearchIcon,
  SlidersIcon
} from '../Common/Icons';

export default function VoiceStudioPanel({
  isOpen,
  onClose,
  selectedVoiceName,
  onSelectVoice,
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
  inworldVoiceList = [],
  customVoices = [],
  setCustomVoices,
  newVoiceInput,
  setNewVoiceInput,
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
      setTimeout(() => {
        dragStartRef.current.hasMoved = false;
      }, 60);
    };

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
    };
  }, [isDragging]);

  // 1. Click outside panel listener to auto-dismiss (respects dragging)
  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (event) => {
      if (isDragging || dragStartRef.current.hasMoved) return;
      // If clicking inside panel, do not close
      if (panelRef.current && panelRef.current.contains(event.target)) {
        return;
      }
      // If clicking TopBar's Voice Studio trigger button, let TopBar handle toggle
      const topbarTrigger = document.querySelector('[title*="Voice Studio"]');
      if (topbarTrigger && topbarTrigger.contains(event.target)) {
        return;
      }
      const sidebarTrigger = document.querySelector('.sidebar-tool-btn');
      if (sidebarTrigger && sidebarTrigger.contains(event.target)) {
        return;
      }
      onClose();
    };

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        if (isDropdownOpen) {
          setIsDropdownOpen(false);
        } else {
          onClose();
        }
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

  // 2. Click outside dropdown menu listener
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

  // Resolve current active voice details
  const currentVoiceMeta = useMemo(() => {
    if (selectedVoiceName.startsWith('inworld-')) {
      const cleanId = selectedVoiceName.replace('inworld-', '');
      const predefined = inworldVoiceList.find(v => v.id.toLowerCase() === cleanId.toLowerCase());
      if (predefined) {
        return {
          id: selectedVoiceName,
          title: predefined.displayName || predefined.name || cleanId,
          type: 'Inworld AI',
          accent: predefined.lang || 'en-US',
          isCustom: false
        };
      }
      const custom = customVoices.find(v => v.id.toLowerCase() === cleanId.toLowerCase());
      return {
        id: selectedVoiceName,
        title: custom?.displayName || `${cleanId} (Custom Inworld)`,
        type: 'Inworld Custom',
        accent: 'Inworld',
        isCustom: true
      };
    }

    if (selectedVoiceName === 'ultra-realistic-hinglish') {
      return {
        id: 'ultra-realistic-hinglish',
        title: 'Cartesia Hinglish Voice Model',
        type: 'Neural Cloud',
        accent: 'hi-IN',
        isCustom: false
      };
    }

    const browserVoice = voices.find(v => v.name === selectedVoiceName);
    return {
      id: selectedVoiceName,
      title: browserVoice?.name || selectedVoiceName,
      type: 'Browser Voice',
      accent: browserVoice?.lang || 'Local',
      isCustom: false
    };
  }, [selectedVoiceName, inworldVoiceList, customVoices, voices]);

  // Filtered voice options based on search query
  const filteredInworld = useMemo(() => {
    if (!searchQuery.trim()) return inworldVoiceList;
    const q = searchQuery.toLowerCase();
    return inworldVoiceList.filter(v => 
      (v.displayName && v.displayName.toLowerCase().includes(q)) ||
      (v.id && v.id.toLowerCase().includes(q)) ||
      (v.lang && v.lang.toLowerCase().includes(q))
    );
  }, [inworldVoiceList, searchQuery]);

  const filteredCustom = useMemo(() => {
    if (!searchQuery.trim()) return customVoices;
    const q = searchQuery.toLowerCase();
    return customVoices.filter(v => v.id.toLowerCase().includes(q));
  }, [customVoices, searchQuery]);

  const filteredBrowser = useMemo(() => {
    if (!searchQuery.trim()) return voices;
    const q = searchQuery.toLowerCase();
    return voices.filter(v => 
      v.name.toLowerCase().includes(q) || 
      (v.lang && v.lang.toLowerCase().includes(q))
    );
  }, [voices, searchQuery]);

  // Handle adding custom voice ID
  const handleAddCustomVoice = () => {
    const trimmed = newVoiceInput.trim();
    if (!trimmed) return;

    if (!customVoices.some(v => v.id.toLowerCase() === trimmed.toLowerCase()) &&
        !inworldVoiceList.some(v => v.id.toLowerCase() === trimmed.toLowerCase())) {
      const updated = [...customVoices, { id: trimmed, displayName: `${trimmed} (Inworld AI)` }];
      setCustomVoices(updated);
      try {
        localStorage.setItem('inworld_custom_voices', JSON.stringify(updated));
      } catch (e) {}
    }

    const fullKey = `inworld-${trimmed}`;
    onSelectVoice(fullKey);
    setNewVoiceInput('');
  };

  const handleRemoveCustomVoice = (voiceIdToRemove, e) => {
    e.stopPropagation();
    const updated = customVoices.filter(v => v.id !== voiceIdToRemove);
    setCustomVoices(updated);
    try {
      localStorage.setItem('inworld_custom_voices', JSON.stringify(updated));
    } catch (e) {}

    if (selectedVoiceName === `inworld-${voiceIdToRemove}`) {
      onSelectVoice('inworld-Sarah');
    }
  };

  if (!isOpen) return null;

  const isAudioActive = isCloudPlaying || isSpeaking;
  const isAudioBusy = isCloudLoading || isAudioActive;

  // Percentage calculations for gradient slider tracks
  const speedPercent = ((speechSpeed - 0.5) / (2.0 - 0.5)) * 100;
  const pitchPercent = ((speechPitch - 0.5) / (1.5 - 0.5)) * 100;

  return (
    <div 
      className="voice-studio-overlay"
      aria-label="Voice Studio Modal Background"
    >
      <div 
        ref={panelRef}
        className={`voice-studio-card open ${isDragging ? 'is-dragging' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="voice-studio-title"
        style={{
          left: `${position.x}px`,
          top: `${position.y}px`,
          right: 'auto',
          bottom: 'auto'
        }}
      >
        {/* Draggable Header */}
        <div 
          className="vs-header"
          onPointerDown={handleHeaderPointerDown}
          title="Click and drag anywhere to move Voice Studio"
        >
          <div className="vs-header-title-wrap">
            <span className="vs-drag-grip" aria-hidden="true" title="Drag to move">⠿</span>
            <div className="vs-icon-badge">
              <SlidersIcon size={14} />
            </div>
            <div>
              <h3 id="voice-studio-title" className="vs-title">Voice Studio</h3>
              <p className="vs-subtitle">High-Fidelity AI Speech Synthesis</p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            {isAudioActive && (
              <div className="vs-equalizer" title="Audio playing">
                <span className="eq-bar eq-bar-1" />
                <span className="eq-bar eq-bar-2" />
                <span className="eq-bar eq-bar-3" />
              </div>
            )}
            <button 
              onClick={onClose}
              className="vs-close-btn"
              title="Close Voice Studio (Esc)"
              aria-label="Close Voice Studio"
            >
              <XIcon size={15} />
            </button>
          </div>
        </div>

        {/* Section 1: Fluid Active Voice Selector */}
        <div className="vs-section">
          <div className="vs-label-row">
            <span className="vs-label">Active Voice Model</span>
            <span className="vs-pill-tag">{currentVoiceMeta.type}</span>
          </div>

          <div className="vs-dropdown-wrapper" ref={dropdownRef}>
            {/* Custom High-Hz Animated Trigger */}
            <button
              type="button"
              className={`vs-dropdown-trigger ${isDropdownOpen ? 'active' : ''}`}
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              aria-haspopup="listbox"
              aria-expanded={isDropdownOpen}
            >
              <div className="vs-trigger-left">
                <div className="vs-voice-avatar">
                  {currentVoiceMeta.type.includes('Inworld') ? (
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

            {/* Smooth Spring Dropdown Menu */}
            {isDropdownOpen && (
              <div className="vs-dropdown-menu" role="listbox">
                {/* Search input if multiple voices */}
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
                  {/* Category A: Inworld AI Studio Voices */}
                  {filteredInworld.length > 0 && (
                    <div className="vs-group">
                      <div className="vs-group-title">
                        <span>✨ Inworld AI Studio Voices</span>
                        <span className="vs-group-count">{filteredInworld.length}</span>
                      </div>
                      {filteredInworld.map((voice) => {
                        const voiceKey = `inworld-${voice.id}`;
                        const isSelected = selectedVoiceName === voiceKey;
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
                                <span className="vs-item-name">{voice.displayName || voice.name || voice.id}</span>
                                <span className="vs-item-lang-badge">{voice.lang || 'en-US'}</span>
                              </div>
                              <span className="vs-item-desc">{voice.description || 'Expressive studio voice model'}</span>
                            </div>
                            {isSelected && <CheckIcon size={14} className="vs-item-check" />}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Category B: Custom Added Inworld Voices */}
                  {filteredCustom.length > 0 && (
                    <div className="vs-group">
                      <div className="vs-group-title">
                        <span>⭐ Custom Inworld Voices</span>
                        <span className="vs-group-count">{filteredCustom.length}</span>
                      </div>
                      {filteredCustom.map((voice) => {
                        const voiceKey = `inworld-${voice.id}`;
                        const isSelected = selectedVoiceName === voiceKey;
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
                                <span className="vs-item-name">{voice.displayName || `${voice.id} (Custom)`}</span>
                                <span className="vs-item-lang-badge">Custom ID</span>
                              </div>
                              <span className="vs-item-desc">User configured Inworld voice ID</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              {isSelected && <CheckIcon size={14} className="vs-item-check" />}
                              <button
                                type="button"
                                className="vs-chip-del"
                                onClick={(e) => handleRemoveCustomVoice(voice.id, e)}
                                title="Remove custom voice"
                              >
                                <XIcon size={12} />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Category C: Cloud Neural Hinglish */}
                  {(!searchQuery || 'cartesia hinglish ultra-realistic'.includes(searchQuery.toLowerCase())) && (
                    <div className="vs-group">
                      <div className="vs-group-title">
                        <span>🌐 Cloud Neural Voices</span>
                      </div>
                      <div
                        className={`vs-item ${selectedVoiceName === 'ultra-realistic-hinglish' ? 'selected' : ''}`}
                        onClick={() => {
                          onSelectVoice('ultra-realistic-hinglish');
                          setIsDropdownOpen(false);
                        }}
                        role="option"
                        aria-selected={selectedVoiceName === 'ultra-realistic-hinglish'}
                      >
                        <div className="vs-item-details">
                          <div className="vs-item-top">
                            <span className="vs-item-name">Cartesia Hinglish Voice Model</span>
                            <span className="vs-item-lang-badge">hi-IN</span>
                          </div>
                          <span className="vs-item-desc">High-clarity Indian Hinglish model</span>
                        </div>
                        {selectedVoiceName === 'ultra-realistic-hinglish' && <CheckIcon size={14} className="vs-item-check" />}
                      </div>
                    </div>
                  )}

                  {/* Category D: Browser / Local Voices */}
                  {filteredBrowser.length > 0 && (
                    <div className="vs-group">
                      <div className="vs-group-title">
                        <span>💻 Local Browser Voices</span>
                        <span className="vs-group-count">{filteredBrowser.length}</span>
                      </div>
                      {filteredBrowser.map((voice, idx) => {
                        const isSelected = selectedVoiceName === voice.name;
                        return (
                          <div
                            key={idx}
                            className={`vs-item ${isSelected ? 'selected' : ''}`}
                            onClick={() => {
                              onSelectVoice(voice.name);
                              setIsDropdownOpen(false);
                            }}
                            role="option"
                            aria-selected={isSelected}
                          >
                            <div className="vs-item-details">
                              <div className="vs-item-top">
                                <span className="vs-item-name">{voice.name}</span>
                                <span className="vs-item-lang-badge">{voice.lang}</span>
                              </div>
                              <span className="vs-item-desc">Operating System Native Speech</span>
                            </div>
                            {isSelected && <CheckIcon size={14} className="vs-item-check" />}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Quick Add Inworld Voice ID */}
        <div className="vs-section vs-add-section">
          <div className="vs-label-row">
            <span className="vs-label">Add Custom Inworld Voice ID</span>
            {customVoices.length > 0 && (
              <button
                type="button"
                className="vs-clear-all-btn"
                onClick={() => {
                  setCustomVoices([]);
                  try {
                    localStorage.removeItem('inworld_custom_voices');
                  } catch (e) {}
                  if (selectedVoiceName.startsWith('inworld-') && !inworldVoiceList.some(v => `inworld-${v.id}` === selectedVoiceName)) {
                    onSelectVoice('inworld-Sarah');
                  }
                }}
              >
                Clear Added
              </button>
            )}
          </div>
          <div className="vs-input-group">
            <input
              type="text"
              placeholder="e.g. Lauren, Bianca, Ren, Haruto"
              value={newVoiceInput}
              onChange={(e) => setNewVoiceInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddCustomVoice();
                }
              }}
              className="vs-text-input"
            />
            <button
              type="button"
              className="vs-add-btn"
              onClick={handleAddCustomVoice}
              disabled={!newVoiceInput.trim()}
              title="Add Voice ID to Studio"
            >
              <PlusIcon size={13} />
              <span>Add</span>
            </button>
          </div>

          {/* Quick Active Chips */}
          {customVoices.length > 0 && (
            <div className="vs-chips-cloud">
              {customVoices.map((cv) => (
                <div 
                  key={cv.id} 
                  className={`vs-chip ${selectedVoiceName === `inworld-${cv.id}` ? 'active' : ''}`}
                  onClick={() => onSelectVoice(`inworld-${cv.id}`)}
                >
                  <span className="vs-chip-name">{cv.id}</span>
                  <button
                    type="button"
                    className="vs-chip-close"
                    onClick={(e) => handleRemoveCustomVoice(cv.id, e)}
                    title={`Delete ${cv.id}`}
                  >
                    <XIcon size={10} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section 3: Sliders (Speed & Pitch) */}
        <div className="vs-sliders-wrap">
          {/* Speed Slider */}
          <div className="vs-slider-box">
            <div className="vs-slider-header">
              <span className="vs-label">Speech Speed</span>
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
              <span>0.5x</span>
              <span>1.0x</span>
              <span>2.0x</span>
            </div>
          </div>

          {/* Pitch Slider (Browser voices only) */}
          <div className={`vs-slider-box ${(!ttsSupported || selectedVoiceName.startsWith('inworld-') || selectedVoiceName === 'ultra-realistic-hinglish') ? 'disabled' : ''}`}>
            <div className="vs-slider-header">
              <span className="vs-label">
                Speech Pitch
                {(selectedVoiceName.startsWith('inworld-') || selectedVoiceName === 'ultra-realistic-hinglish') && (
                  <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', marginLeft: '6px', fontWeight: 500 }}>
                    (Cloud Native)
                  </span>
                )}
              </span>
              <span className="vs-val-pill">{speechPitch.toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="1.5"
              step="0.1"
              value={speechPitch}
              onChange={(e) => setSpeechPitch(parseFloat(e.target.value))}
              disabled={!ttsSupported || selectedVoiceName.startsWith('inworld-') || selectedVoiceName === 'ultra-realistic-hinglish'}
              style={{
                background: `linear-gradient(to right, rgba(255,255,255,0.7) 0%, rgba(255,255,255,0.95) ${pitchPercent}%, rgba(255,255,255,0.08) ${pitchPercent}%)`
              }}
              className="vs-range-slider"
            />
            <div className="vs-range-scale">
              <span>0.5</span>
              <span>1.0</span>
              <span>1.5</span>
            </div>
          </div>
        </div>

        {/* Section 4: Action & Preview Button */}
        <div className="vs-action-block">
          <button
            type="button"
            className={`vs-preview-btn ${isCloudLoading ? 'loading' : ''} ${isAudioActive ? 'playing' : ''}`}
            onClick={onPlayPreview}
            disabled={isCloudLoading}
          >
            {isCloudLoading ? (
              <>
                <span className="vs-spinner" />
                <span>Synthesizing Audio...</span>
              </>
            ) : isAudioActive ? (
              <>
                <div className="vs-equalizer mini">
                  <span className="eq-bar eq-bar-1" />
                  <span className="eq-bar eq-bar-2" />
                  <span className="eq-bar eq-bar-3" />
                </div>
                <span>Playing Voice Preview...</span>
              </>
            ) : (
              <>
                <PlayIcon size={14} />
                <span>Play Voice Preview</span>
              </>
            )}
          </button>

          {/* Quick Playback Bar */}
          <div className="vs-controls-row">
            <button
              type="button"
              className="vs-control-btn"
              onClick={onPlayResume}
              title="Play/Resume Audio"
            >
              <PlayIcon size={12} />
              <span>{isPaused || (cloudAudioRef.current && cloudAudioRef.current.paused) ? 'Resume' : 'Play'}</span>
            </button>
            <button
              type="button"
              className="vs-control-btn"
              onClick={onPause}
              disabled={(!isSpeaking && !isCloudPlaying) || isPaused}
              title="Pause Audio"
            >
              <PauseIcon size={12} />
              <span>Pause</span>
            </button>
            <button
              type="button"
              className="vs-control-btn vs-stop-btn"
              onClick={onStop}
              disabled={!isSpeaking && !isCloudPlaying && !isCloudLoading}
              title="Stop Speech"
            >
              <SquareIcon size={11} />
              <span>Stop</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
