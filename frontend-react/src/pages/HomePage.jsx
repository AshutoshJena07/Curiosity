import React, { useEffect, useRef } from 'react';
import gsap from 'gsap';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';
import { useAuth } from '../context/AuthContext';
import CuriosityLogo from '../components/Common/CuriosityLogo';

export default function HomePage({ navigate }) {
  const { token, enterGuestMode } = useAuth();
  const containerRef = useRef(null);
  const heroContentRef = useRef(null);

  useEffect(() => {
    // 1. Lenis Smooth Scrolling Engine synchronized with GSAP Ticker
    const lenis = new Lenis({
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      touchMultiplier: 1.5
    });

    const rafHandler = (time) => lenis.raf(time * 1000);
    gsap.ticker.add(rafHandler);
    gsap.ticker.lagSmoothing(500, 33);

    // 2. High-performance cinematic GSAP Entrance Timeline
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({
        defaults: {
          ease: 'power4.out',
          force3D: true
        }
      });

      tl.fromTo(
        '.landing-nav',
        { opacity: 0, y: -24 },
        { opacity: 1, y: 0, duration: 1.1 }
      )
      .fromTo(
        '.editorial-waitlist-dot',
        { opacity: 0, scale: 0 },
        { opacity: 1, scale: 1, duration: 0.6 },
        '-=0.7'
      )
      .fromTo(
        '.editorial-waitlist-badge',
        { opacity: 0, y: 18, scale: 0.96 },
        { opacity: 1, y: 0, scale: 1, duration: 0.8 },
        '-=0.55'
      )
      .fromTo(
        '.editorial-hero-title',
        { opacity: 0, y: 32 },
        { opacity: 1, y: 0, duration: 1.15 },
        '-=0.65'
      )
      .fromTo(
        '.editorial-hero-subtext',
        { opacity: 0, y: 18 },
        { opacity: 1, y: 0, duration: 0.9 },
        '-=0.75'
      )
      .fromTo(
        '.editorial-cta-btn',
        { opacity: 0, y: 14, scale: 0.92 },
        { opacity: 1, y: 0, scale: 1, duration: 0.8 },
        '-=0.65'
      )
      .fromTo(
        '.editorial-outer-footer',
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, duration: 0.9 },
        '-=0.5'
      );

      // 3. Smooth, zero-lag micro-parallax on cursor movement using gsap.quickTo
      if (heroContentRef.current) {
        const xTo = gsap.quickTo(heroContentRef.current, 'x', { duration: 0.9, ease: 'power3.out' });
        const yTo = gsap.quickTo(heroContentRef.current, 'y', { duration: 0.9, ease: 'power3.out' });

        const handleMouseMove = (e) => {
          const { innerWidth, innerHeight } = window;
          const xOffset = ((e.clientX / innerWidth) - 0.5) * 16;
          const yOffset = ((e.clientY / innerHeight) - 0.5) * 12;
          xTo(xOffset);
          yTo(yOffset);
        };

        window.addEventListener('mousemove', handleMouseMove, { passive: true });
        
        return () => {
          window.removeEventListener('mousemove', handleMouseMove);
        };
      }
    }, containerRef);

    return () => {
      ctx.revert();
      gsap.ticker.remove(rafHandler);
      lenis.destroy();
    };
  }, []);

  const handleGetStarted = () => {
    if (token) {
      navigate('#/workspace');
    } else {
      navigate('#/signup');
    }
  };

  return (
    <div className="editorial-landing-wrapper" ref={containerRef}>
      
      {/* ── TOP NAVIGATION: CURIOSITY LOGO (LEFT) & SIGN IN BUTTON (RIGHT) ── */}
      <header className="landing-nav">
        <div 
          className="landing-nav-brand" 
          onClick={() => navigate('#/')} 
          style={{ cursor: 'pointer' }}
          title="Curiosity"
        >
          <CuriosityLogo size="md" />
        </div>

        <div className="landing-nav-actions" style={{ marginLeft: 'auto' }}>
          <button 
            type="button" 
            className="landing-nav-signin-btn" 
            onClick={() => navigate(token ? '#/workspace' : '#/login')}
          >
            {token ? 'Workspace' : 'Sign In'}
          </button>
        </div>
      </header>

      {/* ── HERO CONTENT: EXACT TEXT PLACEMENTS & TYPOGRAPHY (VERTICALLY CENTERED) ── */}
      <main className="editorial-hero-content" ref={heroContentRef}>
        
        {/* Subtle Pin Dot */}
        <div className="editorial-waitlist-dot" aria-hidden="true" />

        {/* Status Badge */}
        <div className="editorial-waitlist-badge">
          <span>Product is now live!</span>
        </div>

        {/* Main Headline */}
        <h1 className="editorial-hero-title">
          <span className="editorial-title-clarity">Clarity in</span>
          <span className="editorial-title-complexity">Complexity</span>
        </h1>

        {/* Editorial Subtitle */}
        <p className="editorial-hero-subtext">
          We help you decode the noise. One insight at a time.<br />
          Transform chaos into clarity with intelligent solutions built for scale.
        </p>

        {/* Call To Action Pill Button */}
        <button 
          type="button"
          className="editorial-cta-btn" 
          onClick={handleGetStarted}
        >
          <span>Get Started</span>
          <svg className="cta-btn-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>

      </main>

      {/* ── OUTER METADATA FOOTER (EDGE-TO-EDGE AT BOTTOM) ── */}
      <footer className="editorial-outer-footer">
        <span className="footer-meta-left">PRODUCT LAUNCH</span>
        <span 
          className="footer-meta-center" 
          onClick={() => navigate('#/404')} 
          style={{ cursor: 'pointer' }}
          title="ASHUTOSH J."
        >
          ASHUTOSH J.
        </span>
        <span className="footer-meta-right">2026</span>
      </footer>

    </div>
  );
}
