import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Custom React hook for Speech-to-Text using native Web Speech Recognition API.
 * Provides voice input capability for speech prompts like "Hey Curiosity".
 */
export default function useSpeechRecognition({ onTranscript, onFinal } = {}) {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const recognitionRef = useRef(null);

  const isSupported = typeof window !== 'undefined' && 
    Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.warn('SpeechRecognition stop error:', err);
      }
      setIsListening(false);
    }
  }, []);

  const startListening = useCallback((lang = 'en-US') => {
    if (!isSupported) {
      alert('Speech Recognition is not supported in this browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch {}
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;

    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = lang; // 'en-US', 'hi-IN', or browser default

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript('');
    };

    recognition.onresult = (event) => {
      let currentInterim = '';
      let currentFinal = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const item = event.results[i];
        if (item.isFinal) {
          currentFinal += item[0].transcript;
        } else {
          currentInterim += item[0].transcript;
        }
      }

      const text = currentFinal || currentInterim;
      setTranscript(text);
      if (onTranscript) {
        onTranscript(text);
      }

      if (currentFinal && onFinal) {
        onFinal(currentFinal.trim());
      }
    };

    recognition.onerror = (event) => {
      if (event.error !== 'no-speech') {
        console.warn('Speech recognition error:', event.error);
      }
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    try {
      recognition.start();
    } catch (err) {
      console.warn('Speech recognition start failed:', err);
      setIsListening(false);
    }
  }, [isSupported, onTranscript, onFinal]);

  const toggleListening = useCallback((lang) => {
    if (isListening) {
      stopListening();
    } else {
      startListening(lang);
    }
  }, [isListening, startListening, stopListening]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {}
      }
    };
  }, []);

  return {
    isListening,
    transcript,
    isSupported,
    startListening,
    stopListening,
    toggleListening,
    resetTranscript: () => setTranscript('')
  };
}
