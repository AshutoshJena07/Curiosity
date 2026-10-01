import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

/**
 * Cinematic 404 Depth-of-Field Page
 * Recreates the iconic focal lens depth design with giant crimson red typography,
 * optical blur, handwritten scribble accent, and mouse parallax.
 */
export default function NotFoundPage({ navigate }) {
  const { token } = useAuth();
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const handleMouseMove = (e) => {
      const { innerWidth, innerHeight } = window;
      const x = ((e.clientX / innerWidth) - 0.5) * 2;
      const y = ((e.clientY / innerHeight) - 0.5) * 2;
      setMousePos({ x, y });
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const handleGoBack = () => {
    if (token) {
      if (navigate) navigate('#/workspace');
      else window.location.hash = '#/workspace';
    } else {
      if (window.history.length > 1) {
        window.history.back();
      } else {
        if (navigate) navigate('#/');
        else window.location.hash = '#/';
      }
    }
  };

  // Subtle parallax translation calculation
  const parallaxX = mousePos.x * 12;
  const parallaxY = mousePos.y * 8;

  return (
    <main className="focal-404-wrapper" role="main" aria-label="Page Not Found">
      
      {/* ── 1. TOP HEADER ── */}
      <header className="focal-top-header">
        <span className="focal-top-badge">404</span>
        <span className="focal-top-subtitle">ERROR PAGE</span>
      </header>

      {/* ── 2. GIANT BACKGROUND "404" NUMBERS WITH DEPTH-OF-FIELD ── */}
      <div 
        className="focal-numbers-row"
        aria-hidden="true"
        style={{
          transform: `translate3d(${parallaxX * 0.5}px, ${parallaxY * 0.5}px, 0)`
        }}
      >
        {/* Left '4' (Lens Focal Blurred) */}
        <span 
          className="focal-digit blurred"
          style={{
            transform: `translate3d(${-parallaxX * 0.4}px, 0, 0)`
          }}
        >
          4
        </span>

        {/* Center '0' (Sharp & In-Focus) */}
        <span className="focal-digit sharp">
          0
        </span>

        {/* Right '4' (Lens Focal Blurred) */}
        <span 
          className="focal-digit blurred"
          style={{
            transform: `translate3d(${parallaxX * 0.4}px, 0, 0)`
          }}
        >
          4
        </span>
      </div>

      {/* ── 3. DEAD-CENTER CONTENT (INSIDE THE HOLLOW OF THE '0') ── */}
      <section 
        className="focal-center-overlay"
        style={{
          transform: `translate3d(calc(-50% + ${-parallaxX * 0.8}px), calc(-50% + ${-parallaxY * 0.8}px), 0)`
        }}
      >
        <span className="focal-center-mini-tag">404</span>
        
        <h1 className="focal-center-main-text">
          SORRY, WE COULDN'T FIND THIS PAGE
        </h1>

        {/* Interactive "GO BACK" with Scribble Accent Underline */}
        <button 
          type="button"
          className="focal-goback-wrap"
          onClick={handleGoBack}
          title="Go back to previous page"
          aria-label="Go back to previous page"
        >
          <span className="focal-goback-text">GO BACK</span>
          
          {/* Authentic Hand-drawn Loop Scribble SVG */}
          <svg 
            className="focal-scribble-svg" 
            viewBox="0 0 260 42" 
            fill="none" 
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            {/* Loose whimsical signature scribble loops */}
            <path 
              d="M 12 24 C 38 15, 68 32, 98 18 C 128 4, 158 30, 192 16 C 218 5, 238 22, 252 16" 
              stroke="rgba(255, 255, 255, 0.45)" 
              strokeWidth="2.4" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
            />
            <path 
              d="M 28 32 C 14 26, 18 14, 38 18 C 58 22, 36 36, 52 30 C 68 24, 98 22, 138 20 C 178 18, 222 17, 255 14" 
              stroke="rgba(255, 255, 255, 0.65)" 
              strokeWidth="2.2" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
            />
            <path 
              d="M 22 28 C 44 38, 76 16, 108 26 C 140 36, 172 18, 206 22 C 228 25, 244 18, 254 18" 
              stroke="rgba(255, 255, 255, 0.3)" 
              strokeWidth="1.6" 
              strokeLinecap="round" 
            />
          </svg>
        </button>
      </section>

      {/* ── 4. BOTTOM FOOTER ── */}
      <footer className="focal-bottom-footer">
        <p className="focal-bottom-disclaimer">
          THE PAGE YOU ARE LOOKING FOR DOESN'T EXIST OR AN OTHER ERROR OCCURRED.
        </p>
      </footer>

    </main>
  );
}
