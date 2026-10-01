import React from 'react';

/**
 * Brand Logo component featuring the iconic Rabbit SVG logo and 'curiosity' wordmark.
 */
export default function CuriosityLogo({ 
  size = 'md', // 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  showSparkle = true,
  showRabbit = true,
  className = '',
  onClick = null
}) {
  const displayRabbit = showRabbit && showSparkle;

  return (
    <span 
      className={`curiosity-brand-logo size-${size} ${className}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {displayRabbit && (
        <span className="curiosity-rabbit-logo-wrap" aria-hidden="true">
          <img 
            src="/favicon.svg" 
            alt="Curiosity Rabbit" 
            className="curiosity-rabbit-logo-img" 
          />
        </span>
      )}
      <span className="curiosity-brand-text">curiosity</span>
    </span>
  );
}
