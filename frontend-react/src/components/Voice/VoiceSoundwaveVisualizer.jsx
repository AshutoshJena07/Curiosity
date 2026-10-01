import React from 'react';
import './VoiceSoundwaveVisualizer.css';

export default function VoiceSoundwaveVisualizer({ isActive, onStop }) {
  return (
    <div 
      className={`voice-soundwave-backdrop ${isActive ? 'active' : ''}`}
      aria-hidden={!isActive}
    >
      {/* Ambient Radial Core Glow */}
      <div className="soundwave-ambient-glow" />

      {/* Acoustic Spherical Sonic Rings SVG */}
      <svg 
        className="voice-soundwave-svg" 
        viewBox="0 0 1000 500" 
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          {/* Ethereal Glow Filters */}
          <filter id="intenseGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur1" />
            <feGaussianBlur in="SourceGraphic" stdDeviation="12" result="blur2" />
            <feMerge>
              <feMergeNode in="blur2" />
              <feMergeNode in="blur1" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Gradients tailored to highlight the left & right rim arcs for each concentric ellipse */}
          <linearGradient id="centerRimGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="34%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="35.5%" stopColor="#ffffff" stopOpacity="0.98" />
            <stop offset="37%" stopColor="#93c5fd" stopOpacity="0.8" />
            <stop offset="41%" stopColor="#60a5fa" stopOpacity="0" />
            <stop offset="59%" stopColor="#60a5fa" stopOpacity="0" />
            <stop offset="63%" stopColor="#93c5fd" stopOpacity="0.8" />
            <stop offset="64.5%" stopColor="#ffffff" stopOpacity="0.98" />
            <stop offset="66%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="100%" stopColor="#93c5fd" stopOpacity="0" />
          </linearGradient>

          <linearGradient id="ring1Grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="26%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="27.5%" stopColor="#ffffff" stopOpacity="0.9" />
            <stop offset="29%" stopColor="#93c5fd" stopOpacity="0.75" />
            <stop offset="33%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="67%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="71%" stopColor="#93c5fd" stopOpacity="0.75" />
            <stop offset="72.5%" stopColor="#ffffff" stopOpacity="0.9" />
            <stop offset="74%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="100%" stopColor="#93c5fd" stopOpacity="0" />
          </linearGradient>

          <linearGradient id="ring2Grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="17%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="18.5%" stopColor="#ffffff" stopOpacity="0.82" />
            <stop offset="20%" stopColor="#93c5fd" stopOpacity="0.65" />
            <stop offset="24%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="76%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="80%" stopColor="#93c5fd" stopOpacity="0.65" />
            <stop offset="81.5%" stopColor="#ffffff" stopOpacity="0.82" />
            <stop offset="83%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="100%" stopColor="#93c5fd" stopOpacity="0" />
          </linearGradient>

          <linearGradient id="ring3Grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="8%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="9.5%" stopColor="#ffffff" stopOpacity="0.7" />
            <stop offset="11%" stopColor="#93c5fd" stopOpacity="0.5" />
            <stop offset="15%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="85%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="89%" stopColor="#93c5fd" stopOpacity="0.5" />
            <stop offset="90.5%" stopColor="#ffffff" stopOpacity="0.7" />
            <stop offset="92%" stopColor="#93c5fd" stopOpacity="0" />
            <stop offset="100%" stopColor="#93c5fd" stopOpacity="0" />
          </linearGradient>

          <linearGradient id="ring4Grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.5" />
            <stop offset="1.5%" stopColor="#ffffff" stopOpacity="0.6" />
            <stop offset="3%" stopColor="#93c5fd" stopOpacity="0.4" />
            <stop offset="7%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="93%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="97%" stopColor="#93c5fd" stopOpacity="0.4" />
            <stop offset="98.5%" stopColor="#ffffff" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0.5" />
          </linearGradient>
        </defs>

        {/* 1. Outermost Ring 4 */}
        <g className="soundwave-ring-4" filter="url(#softGlow)">
          <ellipse 
            cx="500" 
            cy="250" 
            rx="480" 
            ry="220" 
            fill="none" 
            stroke="url(#ring4Grad)" 
            strokeWidth="1.5" 
          />
        </g>

        {/* 2. Outer Ring 3 */}
        <g className="soundwave-ring-3" filter="url(#softGlow)">
          <ellipse 
            cx="500" 
            cy="250" 
            rx="395" 
            ry="200" 
            fill="none" 
            stroke="url(#ring3Grad)" 
            strokeWidth="1.8" 
          />
        </g>

        {/* 3. Middle Ring 2 */}
        <g className="soundwave-ring-2" filter="url(#softGlow)">
          <ellipse 
            cx="500" 
            cy="250" 
            rx="310" 
            ry="180" 
            fill="none" 
            stroke="url(#ring2Grad)" 
            strokeWidth="2.2" 
          />
        </g>

        {/* 4. Inner Ring 1 */}
        <g className="soundwave-ring-1" filter="url(#intenseGlow)">
          <ellipse 
            cx="500" 
            cy="250" 
            rx="225" 
            ry="160" 
            fill="none" 
            stroke="url(#ring1Grad)" 
            strokeWidth="2.6" 
          />
        </g>

        {/* 5. Core Primary Luminous Sphere */}
        <g className="soundwave-ring-center" filter="url(#intenseGlow)">
          <ellipse 
            cx="500" 
            cy="250" 
            rx="145" 
            ry="145" 
            fill="none" 
            stroke="url(#centerRimGrad)" 
            strokeWidth="3.2" 
          />
        </g>
      </svg>

      {/* Floating Audio Playing Status Pill */}
      {isActive && (
        <div className="soundwave-status-pill">
          <div className="soundwave-bars">
            <span className="soundwave-bar" />
            <span className="soundwave-bar" />
            <span className="soundwave-bar" />
            <span className="soundwave-bar" />
          </div>
          <span className="soundwave-status-text">Playing Voice Response</span>
        </div>
      )}
    </div>
  );
}
