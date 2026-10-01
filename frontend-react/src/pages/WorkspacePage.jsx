import React, { useState, useEffect, useCallback, useRef } from 'react';
import MainLayout from '../components/Layout/MainLayout';
import ChatArea from '../components/Chat/ChatArea';
import ChatComposer from '../components/Chat/ChatComposer';
import { checkHealth, analyzeFile, fetchConversationDetail, saveConversation, fetchConversations, deleteConversation } from '../services/api';
import { validateFileExtension } from '../utils/fileValidation';
import useSpeechSynthesis from '../hooks/useSpeechSynthesis';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { PlayIcon, PauseIcon, SquareIcon, XIcon } from '../components/Common/Icons';
import VoiceStudioPanel from '../components/Voice/VoiceStudioPanel';
import SideRays from '../components/Common/SideRays';
import VoiceSoundwaveVisualizer from '../components/Voice/VoiceSoundwaveVisualizer';


export default function WorkspacePage({ 
  navigate, 
  conversationId, 
  preloadedFile, 
  clearPreloadedFile,
  preloadedPrompt,
  clearPreloadedPrompt
}) {
  const { token, user, displayName, guestMode, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  // UI States
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(() => localStorage.getItem('auto_speak') === 'true');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [serverStatus, setServerStatus] = useState('checking');

  // Busy lock state to prevent duplicate submissions
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState('');

  // Active loaded session identifier (for SQLite syncing)
  const [currentSessionId, setCurrentSessionId] = useState(() => Date.now().toString());
  const [conversationsList, setConversationsList] = useState([]);

  // Chat Data States (Unique IDs and dynamic timestamps)
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState('');
  const [activeFile, setActiveFile] = useState(null);

  // Speech Hook Integration
  const {
    supported: ttsSupported,
    voices,
    isSpeaking,
    isPaused,
    speak,
    pause,
    resume,
    stop: stopSpeech
  } = useSpeechSynthesis();

  // Voice configurations states
  const [selectedVoiceName, setSelectedVoiceName] = useState(() => {
    return localStorage.getItem('active_voice_model') || 'inworld-Sarah';
  });
  const [speechSpeed, setSpeechSpeed] = useState(1.0);
  const [speechPitch, setSpeechPitch] = useState(1.0);
  const [speakingMessageId, setSpeakingMessageId] = useState(null);

  // Inworld AI Voice catalog & custom voice management
  const [inworldVoiceList, setInworldVoiceList] = useState([
    { id: 'Sarah', displayName: 'Sarah (Inworld Studio Female)', lang: 'en-US' },
    { id: 'Anjali', displayName: 'Anjali (Inworld Indian Female)', lang: 'en-IN' },
    { id: 'Vincent', displayName: 'Vincent (Inworld Classy Male)', lang: 'en-US' },
    { id: 'Ashley', displayName: 'Ashley (Inworld Warm Female)', lang: 'en-US' },
    { id: 'Carter', displayName: 'Carter (Inworld Announcer Male)', lang: 'en-US' },
  ]);
  const [customVoices, setCustomVoices] = useState(() => {
    try {
      const saved = localStorage.getItem('inworld_custom_voices');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [newVoiceInput, setNewVoiceInput] = useState('');

  // Fetch registered voices from backend on mount
  useEffect(() => {
    fetch('/tts/voices')
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && Array.isArray(data.voices) && data.voices.length > 0) {
          setInworldVoiceList(data.voices);
        }
      })
      .catch(() => {});
  }, []);

  // Cloud AI TTS Audio reference & playback state
  const cloudAudioRef = useRef(null);
  const [isCloudPlaying, setIsCloudPlaying] = useState(false);
  const [isCloudLoading, setIsCloudLoading] = useState(false);

  // Active acoustic speech state (used to trigger visualizer only when speech/read is active)
  const isVoiceActive = Boolean(speakingMessageId || isSpeaking || isCloudPlaying || isCloudLoading);

  const initialLoadRef = useRef(false);

  // Clean up audio playback on unmount
  useEffect(() => {
    return () => {
      if (cloudAudioRef.current) {
        try {
          cloudAudioRef.current.pause();
        } catch (e) {}
        cloudAudioRef.current = null;
      }
    };
  }, []);

  // Load past conversation if ID is provided in URL path
  useEffect(() => {
    async function loadPastSession() {
      if (!conversationId) return;

      // 1. Try server fetch if user is logged in
      if (token && !guestMode) {
        try {
          setAnalysisStatus('Loading conversation history...');
          setIsAnalyzing(true);
          const detail = await fetchConversationDetail(conversationId, token);
          if (detail && detail.messages) {
            setCurrentSessionId(detail.id);
            const formattedMessages = (detail.messages || [])
              .filter(m => m.id !== 'greeting' && !m.content?.startsWith('Hello! I am Curiosity. Upload any image'))
              .map(m => ({
                id: m.id || Math.random().toString(),
                role: m.role === 'assistant' ? 'bot' : 'user',
                text: m.content || '',
                imageUrl: m.imageUrl || null,
                fileName: m.fileName || m.fileBadge || null,
                fileType: m.fileType || (m.imageUrl ? 'image' : (m.fileBadge ? 'document' : null)),
                fileBadge: m.fileBadge || null,
                fileSize: m.fileSize || null,
                timestamp: m.timestamp || ''
              }));
            setMessages(formattedMessages);
            return;
          }
        } catch (err) {
          console.warn('Could not load session from server, falling back to local:', err);
        } finally {
          setIsAnalyzing(false);
          setAnalysisStatus('');
        }
      }

      // 2. Fallback to local storage
      try {
        const stored = localStorage.getItem('curiosity_local_conversations');
        if (stored) {
          const list = JSON.parse(stored);
          const match = list.find(c => c.id === conversationId);
          if (match && match.messages && match.messages.length > 0) {
            setCurrentSessionId(match.id);
            setMessages(
              (match.messages || [])
                .filter(m => m.id !== 'greeting' && !m.content?.startsWith('Hello! I am Curiosity. Upload any image'))
                .map(m => ({
                  id: m.id || Math.random().toString(),
                  role: m.role === 'assistant' ? 'bot' : 'user',
                  text: m.content || '',
                  imageUrl: m.imageUrl || null,
                  fileName: m.fileName || m.fileBadge || null,
                  fileType: m.fileType || (m.imageUrl ? 'image' : (m.fileBadge ? 'document' : null)),
                  fileBadge: m.fileBadge || null,
                  fileSize: m.fileSize || null,
                  timestamp: m.timestamp || ''
                }))
            );
          }
        }
      } catch (err) {
        console.warn('Failed to load session from local cache:', err);
      }
    }

    loadPastSession();
  }, [conversationId, token, guestMode]);

  // Load conversions sidebar list
  const refreshSidebar = useCallback(async () => {
    if (token && !guestMode) {
      try {
        const list = await fetchConversations(token);
        if (Array.isArray(list)) {
          setConversationsList(list);
          return;
        }
      } catch (err) {
        console.warn('Failed to load dynamic sidebar history from server:', err);
      }
    }

    // Local real-time cache fallback
    try {
      const stored = localStorage.getItem('curiosity_local_conversations');
      if (stored) {
        setConversationsList(JSON.parse(stored));
      } else {
        setConversationsList([]);
      }
    } catch {
      setConversationsList([]);
    }
  }, [token, guestMode]);

  useEffect(() => {
    refreshSidebar();
  }, [refreshSidebar, messages]);

  // Process dashboard launch parameters (quick files or prompts)
  useEffect(() => {
    if (preloadedFile) {
      handleAttachFile(preloadedFile);
      clearPreloadedFile();
    }
    if (preloadedPrompt) {
      setPrompt(preloadedPrompt);
      clearPreloadedPrompt();
    }
  }, [preloadedFile, preloadedPrompt]);

  // Sync active conversation back to backend Supabase + local cache
  const syncToDatabase = useCallback(async (updatedMessages) => {
    const firstUserQuery = updatedMessages.find(m => m.role === 'user')?.text || 'Untitled Session';
    const cleanTitle = firstUserQuery.length > 32 ? `${firstUserQuery.slice(0, 30)}...` : firstUserQuery;

    const payload = {
      id: currentSessionId,
      title: cleanTitle,
      messages: updatedMessages.map(m => ({
        id: m.id,
        role: m.role === 'bot' ? 'assistant' : 'user',
        content: m.text,
        imageUrl: m.imageUrl || '',
        fileName: m.fileName || '',
        fileType: m.fileType || '',
        fileBadge: m.fileBadge || '',
        fileSize: m.fileSize || 0,
        timestamp: m.timestamp
      })),
      attachments: activeFile ? [{ name: activeFile.name, type: activeFile.type }] : [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    // 1. Sync to backend (which automatically syncs to Supabase Cloud) if authenticated
    if (token && !guestMode) {
      try {
        await saveConversation(payload, token);
      } catch (err) {
        console.error('Cloud auto-save sync failed:', err);
      }
    }

    // 2. Always sync to local cache so history updates instantly in UI
    try {
      const existingStr = localStorage.getItem('curiosity_local_conversations');
      let existing = existingStr ? JSON.parse(existingStr) : [];
      const idx = existing.findIndex(c => c.id === currentSessionId);
      if (idx >= 0) {
        existing[idx] = payload;
      } else {
        existing.unshift(payload);
      }
      const trimmed = existing.slice(0, 30);
      localStorage.setItem('curiosity_local_conversations', JSON.stringify(trimmed));
      setConversationsList(trimmed);
    } catch (err) {
      console.warn('Local cache sync failed:', err);
    }
  }, [token, guestMode, currentSessionId, activeFile]);

  // Auto-initialize first English voice or fallback voice on mount/load
  useEffect(() => {
    if (voices.length > 0 && !selectedVoiceName) {
      setSelectedVoiceName('inworld-Sarah');
    }
  }, [voices, selectedVoiceName]);

  const activeVoiceObj = voices.find(v => v.name === selectedVoiceName) || null;

  // Clear speaking message ID if synthesis stops externally
  useEffect(() => {
    if (!isSpeaking && !isCloudPlaying && !isCloudLoading) {
      setSpeakingMessageId(null);
    }
  }, [isSpeaking, isCloudPlaying, isCloudLoading]);

  // Sync auto-speak preference
  useEffect(() => {
    localStorage.setItem('auto_speak', String(autoSpeak));
  }, [autoSpeak]);

  // Poll backend health status
  useEffect(() => {
    let active = true;
    const runCheck = async () => {
      const isOnline = await checkHealth();
      if (active) {
        setServerStatus(isOnline ? 'online' : 'offline');
      }
    };
    runCheck();
    const interval = setInterval(runCheck, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Centralized File Validation and Attachment Setter
  const handleAttachFile = useCallback((file) => {
    if (!validateFileExtension(file.name)) {
      alert(`Unsupported file format: "${file.name}".\n\nAllowed formats:\n• Images: png, jpg, jpeg, webp, bmp, gif, svg\n• Videos: mp4, avi, mov, mkv, webm\n• Documents: pdf, docx, doc, pptx, ppt\n• Data: xlsx, xls, csv\n• Text/Code: txt, json, md, py, js, ts`);
      return;
    }
    
    if (activeFile?.previewUrl) {
      URL.revokeObjectURL(activeFile.previewUrl);
    }

    const previewUrl = file.type.startsWith('image/') ? URL.createObjectURL(file) : '';
    setActiveFile({
      fileObj: file,
      name: file.name,
      type: file.type,
      previewUrl: previewUrl
    });
  }, [activeFile]);

  const handleRemoveFile = useCallback(() => {
    if (activeFile?.previewUrl) {
      URL.revokeObjectURL(activeFile.previewUrl);
    }
    setActiveFile(null);
  }, [activeFile]);

  // Drag and Drop global listeners
  useEffect(() => {
    const handleDragOver = (e) => {
      e.preventDefault();
      e.stopPropagation();
    };

    const handleDrop = (e) => {
      e.preventDefault();
      e.stopPropagation();
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        handleAttachFile(files[0]);
      }
    };

    window.addEventListener('dragover', handleDragOver);
    window.addEventListener('drop', handleDrop);
    return () => {
      window.removeEventListener('dragover', handleDragOver);
      window.removeEventListener('drop', handleDrop);
    };
  }, [handleAttachFile]);

  // Paste handler listener (Ctrl+V)
  useEffect(() => {
    const handlePaste = (e) => {
      const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
      if (!items) return;
      for (const item of items) {
        if (item.kind === 'file') {
          const file = item.getAsFile();
          if (file) {
            e.preventDefault();
            handleAttachFile(file);
            break;
          }
        }
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, [handleAttachFile]);

  // Stop all active audio playback across both Web Speech API and Cloud Audio
  const stopAllAudio = useCallback(() => {
    stopSpeech();
    if (cloudAudioRef.current) {
      try {
        cloudAudioRef.current.pause();
        cloudAudioRef.current.currentTime = 0;
      } catch (e) {}
      cloudAudioRef.current = null;
    }
    setIsCloudPlaying(false);
    setIsCloudLoading(false);
    setSpeakingMessageId(null);
  }, [stopSpeech]);

  // Synthesize and play audio using Inworld AI or Ultra-Realistic Cloud Voice Model
  const playCloudTTS = async (text, msgId = null, overrideVoice = null) => {
    stopAllAudio();
    if (msgId) setSpeakingMessageId(msgId);
    setIsCloudLoading(true);

    const isLegacyHinglish = selectedVoiceName === 'ultra-realistic-hinglish';
    let voiceId = 'Sarah';
    let provider = 'inworld';

    if (overrideVoice) {
      voiceId = overrideVoice;
    } else if (selectedVoiceName.startsWith('inworld-')) {
      voiceId = selectedVoiceName.replace('inworld-', '');
      provider = 'inworld';
    } else if (isLegacyHinglish) {
      provider = 'cartesia';
    }

    // --- Step 1: Fetch audio from backend (network errors caught separately) ---
    let res;
    try {
      res = await fetch('/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          text, 
          voice_id: voiceId,
          provider: provider,
          model: isLegacyHinglish ? 'ultra-realistic-hinglish' : 'inworld-tts-2' 
        })
      });
    } catch (networkErr) {
      console.error('TTS network error:', networkErr);
      alert('Could not connect to TTS service. Make sure backend is running.');
      setIsCloudLoading(false);
      setSpeakingMessageId(null);
      return;
    }

    if (!res.ok) {
      let errDetail = 'Failed to synthesize audio.';
      try {
        const errData = await res.json();
        errDetail = errData.detail || errDetail;
      } catch (e) {}
      alert(`Voice Studio Notice:\n\n${errDetail}`);
      setIsCloudLoading(false);
      setSpeakingMessageId(null);
      return;
    }

    // --- Step 2: Play the audio blob (autoplay block caught separately) ---
    try {
      const blob = await res.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      cloudAudioRef.current = audio;
      audio.playbackRate = speechSpeed;

      audio.onplay = () => {
        setIsCloudPlaying(true);
        setIsCloudLoading(false);
      };

      audio.onended = () => {
        setIsCloudPlaying(false);
        setIsCloudLoading(false);
        setSpeakingMessageId(null);
        URL.revokeObjectURL(audioUrl);
        cloudAudioRef.current = null;
      };

      audio.onerror = () => {
        setIsCloudPlaying(false);
        setIsCloudLoading(false);
        setSpeakingMessageId(null);
        URL.revokeObjectURL(audioUrl);
        cloudAudioRef.current = null;
      };

      await audio.play();
    } catch (playErr) {
      // Browser autoplay policy blocked — not a backend connectivity issue
      console.warn('Audio playback blocked or failed:', playErr.message);
      setIsCloudLoading(false);
      setSpeakingMessageId(null);
    }
  };


  // Reset conversation to fresh session (New Analysis)
  const handleNewSession = () => {
    if (activeFile?.previewUrl) {
      URL.revokeObjectURL(activeFile.previewUrl);
    }
    stopAllAudio();
    setActiveFile(null);
    setPrompt('');
    setCurrentSessionId(Date.now().toString());
    setMessages([]);
    
    // Redirect URL to a clean new workspace hash
    navigate('#/workspace');
  };

  // Speaks specific text response from active message
  const handleSpeakMessage = (msgId, text) => {
    // If clicking on active speaking message, toggle stop
    if (speakingMessageId === msgId && (isSpeaking || isCloudPlaying || isCloudLoading)) {
      stopAllAudio();
      return;
    }

    // Inworld & Ultra-Realistic Cloud routing
    if (selectedVoiceName.startsWith('inworld-') || selectedVoiceName === 'ultra-realistic-hinglish') {
      playCloudTTS(text, msgId);
      return;
    }

    if (!ttsSupported) {
      alert("Text-to-speech is not supported in this browser.");
      return;
    }

    stopAllAudio();
    setSpeakingMessageId(msgId);
    speak(text, {
      voice: activeVoiceObj,
      rate: speechSpeed,
      pitch: speechPitch
    });
  };

  // Speaks last bot message from active panel
  const handlePlayActiveResponse = () => {
    if (cloudAudioRef.current && cloudAudioRef.current.paused) {
      cloudAudioRef.current.play();
      setIsCloudPlaying(true);
      return;
    }
    if (isPaused) {
      resume();
      return;
    }
    const lastBotMessage = [...messages].reverse().find(msg => msg.role === 'bot' && !msg.typing && !msg.error);
    if (lastBotMessage) {
      handleSpeakMessage(lastBotMessage.id, lastBotMessage.text);
    }
  };

  // Handle suggestion click on Welcome screen
  const handleSelectSuggestion = (selectedPrompt) => {
    setPrompt(selectedPrompt);
  };

  // Handle message submission with real API calls and attachments
  const handleSubmitMessage = async (submittedPrompt, attachedFile) => {
    if (isAnalyzing) return;
    
    const trimmedPrompt = (submittedPrompt || '').trim();
    if (!trimmedPrompt && !attachedFile) {
      alert("Please provide a prompt message or attach a supported file to run the analysis.");
      return;
    }

    setIsAnalyzing(true);
    setAnalysisStatus(attachedFile ? `Analyzing file "${attachedFile.name}"...` : "Generating response...");
    stopAllAudio();
    setPrompt('');
    const userMsgId = Date.now().toString();
    const isImage = attachedFile ? (attachedFile.type?.startsWith('image/') || Boolean(attachedFile.previewUrl)) : false;
    const userMessage = {
      id: userMsgId,
      role: 'user',
      text: trimmedPrompt,
      imageUrl: attachedFile?.previewUrl || null,
      fileName: attachedFile ? attachedFile.name : null,
      fileType: attachedFile ? (isImage ? 'image' : 'document') : null,
      fileBadge: attachedFile && !isImage ? attachedFile.name : null,
      fileSize: attachedFile?.fileObj?.size || null,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const currentMessages = [...messages, userMessage];
    setMessages(currentMessages);
    
    // Clear attachment state
    setActiveFile(null);

    // Add temporary typing indicator bot message
    const typingMsgId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: typingMsgId, role: 'bot', typing: true }]);

    try {
      const fileObj = attachedFile ? attachedFile.fileObj : null;
      const result = await analyzeFile(trimmedPrompt, fileObj, messages, displayName);
      
      const botMsgId = (Date.now() + 2).toString();
      const botReply = {
        id: botMsgId,
        role: 'bot',
        text: result.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      const finalMessages = currentMessages.concat(botReply);
      setMessages(finalMessages);
      setServerStatus('online');

      // Sync updated conversation details back to SQLite database asynchronously
      syncToDatabase(finalMessages);

      if (autoSpeak) {
        if (selectedVoiceName.startsWith('inworld-') || selectedVoiceName === 'ultra-realistic-hinglish') {
          playCloudTTS(result.answer, botMsgId);
        } else if (ttsSupported) {
          setSpeakingMessageId(botMsgId);
          speak(result.answer, {
            voice: activeVoiceObj,
            rate: speechSpeed,
            pitch: speechPitch
          });
        }
      }
    } catch (error) {
      console.error('API submission error:', error);
      
      let friendlyError = error.message || 'Failed to communicate with FastAPI backend server.';
      if (error.name === 'TypeError' || error.message.includes('fetch') || error.message.includes('NetworkError')) {
        friendlyError = 'Backend Server Unreachable. Please make sure the local FastAPI backend is running (run_backend.bat) and port 8000 is open.';
      }

      setMessages(prev => prev.filter(msg => msg.id !== typingMsgId).concat({
        id: (Date.now() + 3).toString(),
        role: 'bot',
        text: friendlyError,
        error: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }));

      setServerStatus('offline');
    } finally {
      setIsAnalyzing(false);
      setAnalysisStatus('');
    }
  };

  // Delete conversation from database, localStorage, and state
  const handleDeletePastConversation = useCallback(async (conversationIdToDelete) => {
    if (!conversationIdToDelete) return;
    
    // 1. Immediately delete from local storage cache
    try {
      const stored = localStorage.getItem('curiosity_local_conversations');
      if (stored) {
        const list = JSON.parse(stored);
        const filtered = list.filter(c => String(c.id) !== String(conversationIdToDelete));
        localStorage.setItem('curiosity_local_conversations', JSON.stringify(filtered));
      }
    } catch (e) {
      console.warn('Failed to delete from localStorage cache:', e);
    }

    // 2. Immediately delete from React state
    setConversationsList(prev => prev.filter(c => String(c.id) !== String(conversationIdToDelete)));

    // 3. If currently viewing the deleted conversation, reset to new session
    if (String(currentSessionId) === String(conversationIdToDelete) || window.location.hash.includes(conversationIdToDelete)) {
      handleNewSession();
      if (navigate) {
        navigate('#/workspace');
      }
    }

    // 4. If logged in with token, sync deletion with backend
    if (token && !guestMode) {
      try {
        await deleteConversation(conversationIdToDelete, token);
      } catch (err) {
        console.warn('Backend delete sync failed (offline or guest):', err);
      }
    }
  }, [token, guestMode, currentSessionId, handleNewSession, navigate]);

  return (
    <MainLayout
      theme={theme}
      setTheme={setTheme}
      isSidebarOpen={isSidebarOpen}
      setIsSidebarOpen={setIsSidebarOpen}
      autoSpeak={autoSpeak}
      setAutoSpeak={setAutoSpeak}
      isSettingsOpen={isSettingsOpen}
      setIsSettingsOpen={setIsSettingsOpen}
      serverStatus={serverStatus}
      onNewSession={handleNewSession}
      conversationsList={conversationsList}
      activeSessionId={currentSessionId}
      onSelectConversation={(id) => navigate(`#/workspace/${id}`)}
      onDeleteConversation={handleDeletePastConversation}
      navigate={navigate}
      user={user}
      guestMode={guestMode}
      logout={logout}
    >
      {/* Configured WebGL SideRays Ambient Effect */}
      <div 
        style={{ 
          width: '100%', 
          height: '600px', 
          position: 'absolute', 
          top: 0, 
          left: 0, 
          pointerEvents: 'none', 
          zIndex: 0, 
          overflow: 'hidden' 
        }}
      >
        <SideRays
          speed={2.5}
          rayColor1="#EAB308"
          rayColor2="#96c8ff"
          intensity={2.2}
          spread={2.2}
          origin="top-right"
          tilt={0}
          saturation={1.5}
          blend={0.825}
          falloff={1.76}
          opacity={1.0}
        />
      </div>

      {/* Acoustic Spherical Sonic Wave Visualizer (Active ONLY when user clicks Read) */}
      <VoiceSoundwaveVisualizer
        isActive={isVoiceActive}
        onStop={stopAllAudio}
      />

      {/* Scrollable messages container */}
      <ChatArea 
        messages={messages} 
        onSelectSuggestion={handleSelectSuggestion}
        onSpeak={handleSpeakMessage}
        speakingMessageId={speakingMessageId}
        onSubmitMessage={handleSubmitMessage}
        activeFile={activeFile}
        onAttachFile={handleAttachFile}
        onRemoveFile={handleRemoveFile}
        isAnalyzing={isAnalyzing}
        conversationsList={conversationsList}
        navigate={navigate}
        userName={displayName}
      />

      {/* Floating Voice Studio Modal Panel */}
      <VoiceStudioPanel
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        selectedVoiceName={selectedVoiceName}
        onSelectVoice={(val) => {
          setSelectedVoiceName(val);
          localStorage.setItem('active_voice_model', val);
        }}
        speechSpeed={speechSpeed}
        setSpeechSpeed={setSpeechSpeed}
        speechPitch={speechPitch}
        setSpeechPitch={setSpeechPitch}
        isCloudLoading={isCloudLoading}
        isCloudPlaying={isCloudPlaying}
        isSpeaking={isSpeaking}
        isPaused={isPaused}
        ttsSupported={ttsSupported}
        voices={voices}
        inworldVoiceList={inworldVoiceList}
        customVoices={customVoices}
        setCustomVoices={setCustomVoices}
        newVoiceInput={newVoiceInput}
        setNewVoiceInput={setNewVoiceInput}
        onPlayPreview={() => {
          if (selectedVoiceName.startsWith('inworld-') || selectedVoiceName === 'ultra-realistic-hinglish') {
            const cleanName = selectedVoiceName.replace('inworld-', '');
            let previewText = `Hello! This is ${cleanName} from Inworld AI. Voice synthesis is working smoothly in your project!`;
            if (cleanName === 'Anjali') {
              previewText = "Namaste! This is Anjali from Inworld AI. Voice synthesis is working smoothly in your project!";
            } else if (selectedVoiceName === 'ultra-realistic-hinglish') {
              previewText = "नमस्ते! यह अल्ट्रा-रियलिस्टिक हिंग्लिश वॉइस मॉडल का टेस्ट प्रिव्यू है। Voice Studio is working smoothly!";
            }
            playCloudTTS(previewText);
          } else if (ttsSupported) {
            speak("Hello! This is a voice studio test preview.", {
              voice: activeVoiceObj,
              rate: speechSpeed,
              pitch: speechPitch
            });
          }
        }}
        onPlayResume={handlePlayActiveResponse}
        onPause={() => {
          if (cloudAudioRef.current && !cloudAudioRef.current.paused) {
            cloudAudioRef.current.pause();
            setIsCloudPlaying(false);
          } else {
            pause();
          }
        }}
        onStop={stopAllAudio}
        cloudAudioRef={cloudAudioRef}
      />

      {/* Footer input text box composer (only when active conversation thread has started) */}
      {messages.filter(m => m.id !== 'greeting').length > 0 && (
        <ChatComposer 
          prompt={prompt}
          setPrompt={setPrompt}
          activeFile={activeFile}
          onAttachFile={handleAttachFile}
          onRemoveFile={handleRemoveFile}
          onSubmit={handleSubmitMessage}
          isAnalyzing={isAnalyzing}
          analysisStatus={analysisStatus}
        />
      )}
    </MainLayout>
  );
}
