import React from 'react';

/**
 * Custom blur-wave loading animation component
 * Implements the blur-text keyframe animation with Quattrocento Sans typography.
 */
export default function SiteLoader({ text = 'LOADING', fullScreen = true }) {
  const letters = Array.from(text);

  return (
    <div className={fullScreen ? "loading" : "loading-inline"}>
      <div className="loading-text">
        {letters.map((char, index) => (
          <span 
            key={index} 
            className="loading-text-words"
            style={{
              animationDelay: `${index * 0.2}s`
            }}
          >
            {char === ' ' ? '\u00A0' : char}
          </span>
        ))}
      </div>
    </div>
  );
}
