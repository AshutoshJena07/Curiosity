import React, { useState, useRef, useEffect } from 'react';
import gsap from 'gsap';
import {
  PlusIcon,
  FastSendIcon,
  MicIcon
} from '../Common/Icons';
import useSpeechRecognition from '../../hooks/useSpeechRecognition';

export default function WelcomeScreen({ 
  onSelectSuggestion,
  onSubmitMessage,
  activeFile,
  onAttachFile,
  onRemoveFile,
  isAnalyzing,
  conversationsList = [],
  navigate,
  userName = 'Ashutosh'
}) {
  const [welcomePrompt, setWelcomePrompt] = useState('');
  const fileInputRef = useRef(null);
  const welcomeTextareaRef = useRef(null);
  const welcomeRootRef = useRef(null);
  const heroContentRef = useRef(null);

  // Speech Recognition Hook for Voice Input ("Hey Curiosity")
  const { isListening, isSupported, toggleListening } = useSpeechRecognition({
    onTranscript: (liveText) => {
      setWelcomePrompt(liveText);
      if (welcomeTextareaRef.current) {
        welcomeTextareaRef.current.value = liveText;
        welcomeTextareaRef.current.style.height = 'auto';
        welcomeTextareaRef.current.style.height = `${Math.min(welcomeTextareaRef.current.scrollHeight, 140)}px`;
      }
    },
    onFinal: (finalText) => {
      const clean = (finalText || '').trim();
      setWelcomePrompt(clean);
      const lower = clean.toLowerCase();
      // If user said "Hey Curiosity" or similar greeting keyword, submit automatically
      if (
        lower.startsWith('hey curiosity') || 
        lower.startsWith('hi curiosity') || 
        lower.startsWith('hello curiosity') ||
        lower === 'curiosity'
      ) {
        if (!isAnalyzing && onSubmitMessage) {
          onSubmitMessage(clean, activeFile);
          setWelcomePrompt('');
          if (welcomeTextareaRef.current) {
            welcomeTextareaRef.current.value = '';
            welcomeTextareaRef.current.style.height = 'auto';
          }
        }
      }
    }
  });

  // Auto-resize welcome textarea as user types
  useEffect(() => {
    if (welcomeTextareaRef.current) {
      welcomeTextareaRef.current.style.height = 'auto';
      welcomeTextareaRef.current.style.height = `${Math.min(welcomeTextareaRef.current.scrollHeight, 140)}px`;
    }
  }, [welcomePrompt]);

  // Cinematic GSAP entrance timeline and cursor micro-parallax (matching HomePage)
  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        defaults: {
          ease: 'power4.out',
          force3D: true
        }
      });

      tl.fromTo(
        '.welcome-greeting-title',
        { opacity: 0, y: 36 },
        { opacity: 1, y: 0, duration: 1.15 }
      )
      .fromTo(
        '.welcome-capsule-composer',
        { opacity: 0, y: 24, scale: 0.96 },
        { opacity: 1, y: 0, scale: 1, duration: 0.95 },
        '-=0.75'
      );

      // Micro-parallax on mouse move (matching HomePage)
      if (heroContentRef.current) {
        const xTo = gsap.quickTo(heroContentRef.current, 'x', { duration: 0.9, ease: 'power3.out' });
        const yTo = gsap.quickTo(heroContentRef.current, 'y', { duration: 0.9, ease: 'power3.out' });

        const handleMouseMove = (e) => {
          const { innerWidth, innerHeight } = window;
          const xOffset = ((e.clientX / innerWidth) - 0.5) * 14;
          const yOffset = ((e.clientY / innerHeight) - 0.5) * 10;
          xTo(xOffset);
          yTo(yOffset);
        };

        window.addEventListener('mousemove', handleMouseMove, { passive: true });
        return () => window.removeEventListener('mousemove', handleMouseMove);
      }
    }, welcomeRootRef);

    return () => ctx.revert();
  }, []);

  // Dynamic greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour >= 5 && hour < 12) return 'Good Morning';
    if (hour >= 12 && hour < 17) return 'Good Afternoon';
    if (hour >= 17 && hour < 23) return 'Good Evening';
    return 'Good Night';
  };

  const greeting = getGreeting();

  const handleSend = (textOverride) => {
    const rawText = typeof textOverride === 'string' ? textOverride : (welcomeTextareaRef.current?.value ?? welcomePrompt);
    const trimmed = (rawText || '').trim();
    if ((!trimmed && !activeFile) || isAnalyzing) return;
    if (onSubmitMessage) {
      onSubmitMessage(trimmed, activeFile);
      setWelcomePrompt('');
      if (welcomeTextareaRef.current) {
        welcomeTextareaRef.current.value = '';
        welcomeTextareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if ((e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      if (!isAnalyzing) {
        handleSend();
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0] && onAttachFile) {
      onAttachFile(e.target.files[0]);
    }
  };

  return (
    <div className="welcome-screen-root" ref={welcomeRootRef}>
      {/* 1. Header: Elegant Serif Greeting with subtle micro-parallax */}
      <div className="welcome-hero-wrap" ref={heroContentRef}>
        <h1 className="welcome-greeting-title serif-heading">
          {greeting}, {userName}
        </h1>
      </div>

      {/* 2. Sleek Capsule Card Composer */}
      <div className="welcome-capsule-composer">
        {activeFile && (
          <div className="composer-attached-preview">
            <span className="file-badge">📎 {activeFile.name}</span>
            <button 
              type="button" 
              onClick={onRemoveFile}
              className="remove-file-btn"
              title="Remove attachment"
            >
              ×
            </button>
          </div>
        )}

        {/* Top Textarea: "How can I help you today?" */}
        <div className="composer-textarea-container">
          <textarea
            ref={welcomeTextareaRef}
            className="composer-text-area"
            placeholder={isAnalyzing ? "Analyzing file..." : "How can I help you today?"}
            rows={1}
            value={welcomePrompt}
            onChange={(e) => setWelcomePrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isAnalyzing}
            aria-label="User query input"
          />
        </div>

        {/* Bottom Controls Bar */}
        <div className="composer-bottom-bar">
          {/* Left: Circular + Button for file attachments */}
          <div className="composer-bottom-left">
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              style={{ display: 'none' }}
              accept="image/*,video/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.json,.md"
            />
            <button 
              type="button" 
              className="composer-circle-plus-btn"
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
              title="Attach File, Document or Image"
              aria-label="Attach File"
            >
              <PlusIcon size={16} />
            </button>
          </div>

          {/* Right: Circular Mic Voice Input & Fast Send Button */}
          <div className="composer-bottom-right" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isSupported && (
              <button
                type="button"
                className={`composer-mic-btn ${isListening ? 'listening' : ''}`}
                onClick={() => toggleListening()}
                disabled={isAnalyzing}
                title={isListening ? "Listening... (Click to stop)" : "Speak: Say 'Hey Curiosity'"}
                aria-label="Voice Input Microphone"
              >
                <MicIcon size={16} />
              </button>
            )}
            <button
              type="button"
              className={`composer-fast-send-btn ${(welcomePrompt.trim() || activeFile) && !isAnalyzing ? 'active' : ''}`}
              onClick={() => handleSend()}
              disabled={(!welcomePrompt.trim() && !activeFile) || isAnalyzing}
              title="Send message (Enter)"
              aria-label="Send message"
            >
              <FastSendIcon size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
