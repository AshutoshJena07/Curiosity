import React from 'react';

/**
 * React Bits Pro: Block 404-3
 * "Centered 404 page with blurred large numerals and a compact CTA"
 * 
 * Adapted to project design tokens and theme tokens (--bg-app, --accent-gradient, Outfit font).
 */
export function NotFoundBlock({
  errorCode = '404',
  badgeText = '404 • Resource Not Found',
  title = 'Page Lost in the Latent Space',
  description = 'The path, conversation, or multimodal asset you requested cannot be located in this neural workspace.',
  primaryAction = { label: 'Return to Safety', hash: '#/' },
  secondaryAction = { label: 'Launch Workspace', hash: '#/workspace' },
  onNavigate
}) {
  const handleNav = (hash) => {
    if (onNavigate) {
      onNavigate(hash);
    } else {
      window.location.hash = hash;
    }
  };

  return (
    <section 
      className="reactbits-404-3-root"
      style={{
        position: 'relative',
        minHeight: '100vh',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        overflow: 'hidden',
        background: 'transparent',
        textAlign: 'center',
        fontFamily: "'Inter', sans-serif"
      }}
    >
      {/* Ambient Radial Gradient Mesh */}
      <div 
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 'min(700px, 90vw)',
          height: 'min(500px, 70vh)',
          background: 'radial-gradient(ellipse at center, rgba(124, 58, 237, 0.18) 0%, rgba(99, 102, 241, 0.08) 45%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0,
          borderRadius: '50%',
          filter: 'blur(40px)'
        }}
      />

      {/* ── BLURRED LARGE NUMERALS (REACT BITS PRO 404-3 SIGNATURE) ── */}
      <div 
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -52%)',
          userSelect: 'none',
          pointerEvents: 'none',
          zIndex: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        {/* Deep blurred glow shadow layer */}
        <span 
          style={{
            position: 'absolute',
            fontFamily: "'Outfit', sans-serif",
            fontSize: 'clamp(10rem, 26vw, 22rem)',
            fontWeight: 900,
            lineHeight: 0.8,
            letterSpacing: '-0.06em',
            background: 'linear-gradient(135deg, #a855f7 0%, #6366f1 40%, #06b6d4 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'blur(54px)',
            opacity: 0.45,
            transform: 'scale(1.05)'
          }}
        >
          {errorCode}
        </span>

        {/* Medium diffused halo layer */}
        <span 
          style={{
            position: 'absolute',
            fontFamily: "'Outfit', sans-serif",
            fontSize: 'clamp(10rem, 26vw, 22rem)',
            fontWeight: 900,
            lineHeight: 0.8,
            letterSpacing: '-0.06em',
            background: 'linear-gradient(180deg, rgba(255,255,255,0.2) 0%, rgba(139,92,246,0.3) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'blur(16px)',
            opacity: 0.6
          }}
        >
          {errorCode}
        </span>

        {/* Crisp foreground translucent numerals */}
        <span 
          style={{
            position: 'relative',
            fontFamily: "'Outfit', sans-serif",
            fontSize: 'clamp(10rem, 26vw, 22rem)',
            fontWeight: 900,
            lineHeight: 0.8,
            letterSpacing: '-0.06em',
            color: 'transparent',
            WebkitTextStroke: '1.5px rgba(255, 255, 255, 0.14)',
            opacity: 0.85
          }}
        >
          {errorCode}
        </span>
      </div>

      {/* ── CENTERED COMPACT CONTENT & CTA ── */}
      <div 
        style={{
          position: 'relative',
          zIndex: 1,
          maxWidth: '540px',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          background: 'rgba(20, 23, 34, 0.55)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '24px',
          padding: 'clamp(28px, 5vw, 42px) clamp(20px, 4vw, 36px)',
          boxShadow: '0 24px 60px -12px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(124, 58, 237, 0.12)'
        }}
      >
        {/* Compact Pill Badge */}
        <div 
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '5px 14px',
            borderRadius: '9999px',
            background: 'rgba(124, 58, 237, 0.15)',
            border: '1px solid rgba(139, 92, 246, 0.35)',
            color: '#c4b5fd',
            fontSize: '11px',
            fontWeight: 600,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            marginBottom: '18px'
          }}
        >
          <span 
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: '#a855f7',
              boxShadow: '0 0 8px #a855f7'
            }} 
          />
          {badgeText}
        </div>

        {/* Heading */}
        <h1 
          style={{
            fontFamily: "'Outfit', sans-serif",
            fontSize: 'clamp(1.75rem, 3.5vw, 2.35rem)',
            fontWeight: 800,
            letterSpacing: '-0.03em',
            color: 'var(--text-primary, #f8fafc)',
            margin: '0 0 12px 0',
            lineHeight: 1.2
          }}
        >
          {title}
        </h1>

        {/* Description */}
        <p 
          style={{
            fontSize: '14px',
            lineHeight: 1.6,
            color: 'var(--text-secondary, #94a3b8)',
            margin: '0 0 28px 0',
            maxWidth: '440px'
          }}
        >
          {description}
        </p>

        {/* ── COMPACT CALL-TO-ACTION BUTTONS ── */}
        <div 
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            width: '100%',
            flexWrap: 'wrap'
          }}
        >
          {/* Primary CTA */}
          <button
            type="button"
            onClick={() => handleNav(primaryAction.hash)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '11px 22px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #7c3aed 0%, #6366f1 100%)',
              color: '#ffffff',
              fontSize: '13px',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 4px 18px rgba(124, 58, 237, 0.45)',
              transition: 'all 0.2s ease',
              minWidth: '150px'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 8px 24px rgba(124, 58, 237, 0.6)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 18px rgba(124, 58, 237, 0.45)';
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m12 19-7-7 7-7"/>
              <path d="M19 12H5"/>
            </svg>
            <span>{primaryAction.label}</span>
          </button>

          {/* Secondary CTA */}
          <button
            type="button"
            onClick={() => handleNav(secondaryAction.hash)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '11px 20px',
              borderRadius: '12px',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'var(--text-primary, #f8fafc)',
              fontSize: '13px',
              fontWeight: 500,
              border: '1px solid rgba(255, 255, 255, 0.12)',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              minWidth: '150px'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.25)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
              e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.12)';
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2"/>
              <polyline points="2 17 12 22 22 17"/>
              <polyline points="2 12 12 17 22 12"/>
            </svg>
            <span>{secondaryAction.label}</span>
          </button>
        </div>

        {/* Bottom subtle metadata */}
        <div 
          style={{
            marginTop: '24px',
            fontSize: '11px',
            color: 'var(--text-muted, #64748b)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <span>Need help?</span>
          <span style={{ opacity: 0.4 }}>•</span>
          <a 
            href="#/workspace" 
            onClick={(e) => { e.preventDefault(); handleNav('#/workspace'); }}
            style={{ color: 'var(--accent-text, #a78bfa)', textDecoration: 'none' }}
          >
            Open Workspace
          </a>
        </div>
      </div>
    </section>
  );
}

export default NotFoundBlock;
