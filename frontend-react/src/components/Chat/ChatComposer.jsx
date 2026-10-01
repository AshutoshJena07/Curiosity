import React, { useRef, useEffect } from 'react';
import FileUploaderUI from './FileUploaderUI';
import {
  PlusIcon,
  FastSendIcon,
  MicIcon
} from '../Common/Icons';
import useSpeechRecognition from '../../hooks/useSpeechRecognition';

export default function ChatComposer({ 
  prompt, 
  setPrompt, 
  activeFile, 
  onAttachFile, 
  onRemoveFile, 
  onSubmit, 
  isAnalyzing,
  analysisStatus
}) {
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  // Native Speech-to-Text Recognition Hook
  const { isListening, isSupported, toggleListening } = useSpeechRecognition({
    onTranscript: (liveText) => {
      setPrompt(liveText);
      if (textareaRef.current) {
        textareaRef.current.value = liveText;
        textareaRef.current.style.height = 'auto';
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
      }
    },
    onFinal: (finalText) => {
      const clean = (finalText || '').trim();
      setPrompt(clean);
      const lower = clean.toLowerCase();
      // Auto-submit if user greeted Curiosity by voice (e.g. "Hey curiosity", "Hi curiosity")
      if (
        lower.startsWith('hey curiosity') || 
        lower.startsWith('hi curiosity') || 
        lower.startsWith('hello curiosity') ||
        lower === 'curiosity'
      ) {
        if (!isAnalyzing) {
          onSubmit(clean, activeFile);
          setPrompt('');
          if (textareaRef.current) {
            textareaRef.current.value = '';
            textareaRef.current.style.height = 'auto';
          }
        }
      }
    }
  });

  // Resize textarea on content change
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [prompt]);

  const handleAttachClick = () => {
    if (isAnalyzing) return;
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onAttachFile(e.target.files[0]);
    }
  };

  const handleSend = (overrideText) => {
    const rawText = typeof overrideText === 'string' ? overrideText : (textareaRef.current?.value ?? prompt);
    const trimmedPrompt = (rawText || '').trim();
    if ((trimmedPrompt || activeFile) && !isAnalyzing) {
      onSubmit(trimmedPrompt, activeFile);
      setPrompt('');
      if (textareaRef.current) {
        textareaRef.current.value = '';
        textareaRef.current.style.height = 'auto';
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

  const isSendDisabled = (!prompt.trim() && !activeFile) || isAnalyzing;

  return (
    <div className="composer-wrap">
      <div className="composer-capsule-card">
        {/* Render file attachments wrapper */}
        <FileUploaderUI 
          activeFile={activeFile} 
          onRemove={onRemoveFile} 
        />

        {/* Hidden File Input */}
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileChange} 
          style={{ display: 'none' }}
          disabled={isAnalyzing}
          accept="image/*,video/*,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.txt,.json,.md"
        />

        {/* Top Textarea: "How can I help you today?" */}
        <div className="composer-textarea-container">
          <textarea
            ref={textareaRef}
            className="composer-text-area"
            placeholder={isAnalyzing ? (analysisStatus || "Analyzing file...") : "How can I help you today?"}
            rows={1}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isAnalyzing}
            aria-label="User message query input"
          />
        </div>

        {/* Bottom Controls Bar */}
        <div className="composer-bottom-bar">
          {/* Left: Circular + Button */}
          <div className="composer-bottom-left">
            <button 
              type="button" 
              className="composer-circle-plus-btn"
              onClick={handleAttachClick}
              disabled={isAnalyzing}
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
              className={`composer-fast-send-btn ${!isSendDisabled ? 'active' : ''}`}
              onClick={() => handleSend()}
              disabled={isSendDisabled}
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
