import React, { useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import WelcomeScreen from './WelcomeScreen';

export default function ChatArea({ 
  messages, 
  onSelectSuggestion, 
  onSpeak, 
  speakingMessageId,
  onSubmitMessage,
  activeFile,
  onAttachFile,
  onRemoveFile,
  isAnalyzing,
  conversationsList = [],
  navigate,
  userName = 'Explorer'
}) {
  const bottomRef = useRef(null);

  // Filter out any default greeting messages from chat history
  const visibleMessages = messages.filter(
    msg => msg && msg.id !== 'greeting' && !msg.text?.startsWith('Hello! I am Curiosity. Upload any image')
  );

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    if (bottomRef.current && visibleMessages.length > 0) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [visibleMessages]);

  return (
    <div className="chat-container">
      <div className="chat-inner">
        {visibleMessages.length === 0 ? (
          <WelcomeScreen 
            onSelectSuggestion={onSelectSuggestion} 
            onSubmitMessage={onSubmitMessage}
            activeFile={activeFile}
            onAttachFile={onAttachFile}
            onRemoveFile={onRemoveFile}
            isAnalyzing={isAnalyzing}
            conversationsList={conversationsList}
            navigate={navigate}
            userName={userName}
          />
        ) : (
          visibleMessages.map((msg, idx) => (
            <ChatMessage 
              key={msg.id || idx} 
              message={msg} 
              onSpeak={onSpeak}
              isSpeakingThis={speakingMessageId === msg.id}
            />
          ))
        )}
        
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
