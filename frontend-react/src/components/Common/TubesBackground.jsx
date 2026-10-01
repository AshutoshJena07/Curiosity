import React, { useEffect, useRef, useState } from 'react';

// Helper for generating dynamic neon / cyberpunk colors
const randomColors = (count) => {
  return new Array(count)
    .fill(0)
    .map(() => "#" + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0'));
};

export function TubesBackground({ 
  children, 
  className = "",
  enableClickInteraction = true 
}) {
  const canvasRef = useRef(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const tubesRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    let cleanup;

    const initTubes = async () => {
      if (!canvasRef.current) return;

      try {
        // Load offline local vendor script first; fallback to CDN if needed
        let module;
        try {
          module = await import('../../vendor/tubes1.min.js');
        } catch (localErr) {
          console.warn("Local tubes script failed, falling back to CDN:", localErr);
          module = await import(/* @vite-ignore */ 'https://cdn.jsdelivr.net/npm/threejs-components@0.0.19/build/cursors/tubes1.min.js');
        }
        const TubesCursor = module.default;

        if (!mounted || !canvasRef.current) return;

        const app = TubesCursor(canvasRef.current, {
          bloom: {
            threshold: 0.05,
            strength: 1.63,   // +10% blur & glow intensity boost
            radius: 0.55      // +10% glow blur radius
          },
          sleepRadiusX: 230,
          sleepRadiusY: 130,
          sleepTimeScale1: 0.75,
          sleepTimeScale2: 1.4,
          tubes: {
            count: 10,
            minRadius: 0.005,
            maxRadius: 0.034,
            minTubularSegments: 24,
            maxTubularSegments: 55,
            colors: ["#38bdf8", "#818cf8", "#c084fc"],
            lights: {
              intensity: 200, // Refined ~2% light intensity
              colors: ["#00f0ff", "#7000ff", "#ff007b", "#00ff88"]
            },
            lerp: 0.48,
            noise: 0.06
          }
        });

        // Medium camera distance for a balanced, proportional perspective
        if (app && app.three) {
          if (app.three.renderer) {
            // Cap pixel ratio at 1.5 to eliminate heavy 4K/Retina GPU fillrate choke on laptops
            app.three.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
          }
          if (app.three.camera) {
            app.three.camera.position.z = 4.4;
            app.three.camera.updateProjectionMatrix();
          }
          if (typeof app.three.updateWorldSize === 'function') {
            app.three.updateWorldSize();
          }
        }

        tubesRef.current = app;

        // Smooth cinematic fade-in once WebGL renders initial frame
        requestAnimationFrame(() => {
          setTimeout(() => {
            if (mounted) setIsLoaded(true);
          }, 60);
        });

        const handleResize = () => {
          // Three.js cursor updates on resize automatically
        };

        window.addEventListener('resize', handleResize);
        
        cleanup = () => {
          window.removeEventListener('resize', handleResize);
          if (app && typeof app.dispose === 'function') {
            try {
              app.dispose();
            } catch (e) {
              // Ignore dispose error
            }
          }
        };

      } catch (error) {
        console.warn("TubesCursor not loaded (WebGL unavailable):", error);
      }
    };

    initTubes();

    return () => {
      mounted = false;
      if (cleanup) cleanup();
    };
  }, []);

  const handleClick = (e) => {
    if (!enableClickInteraction || !tubesRef.current) return;
    
    // Don't randomize colors if clicking inside an interactive element (button, input, textarea, a)
    const targetTag = e.target?.tagName?.toLowerCase();
    if (['button', 'input', 'textarea', 'a', 'select'].includes(targetTag) || e.target?.closest('button, input, textarea, a')) {
      return;
    }

    try {
      const colors = randomColors(3);
      const lightsColors = randomColors(4);
      tubesRef.current.tubes.setColors(colors);
      tubesRef.current.tubes.setLightsColors(lightsColors);
    } catch (err) {
      // Ignore if setColors method unavailable
    }
  };

  return (
    <div 
      className={`tubes-bg-container ${className}`}
      onClick={handleClick}
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '100vh',
        overflowX: 'clip',
        background: '#000000'
      }}
    >
      {/* 3D WebGL Canvas for interactive cursor tubes with smooth cinematic fade-in */}
      <canvas 
        ref={canvasRef} 
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          display: 'block',
          pointerEvents: 'none',
          zIndex: 0,
          touchAction: 'none',
          opacity: isLoaded ? 1 : 0,
          transform: isLoaded ? 'scale(1)' : 'scale(0.92)',
          transition: 'opacity 1.6s cubic-bezier(0.16, 1, 0.3, 1), transform 1.6s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
      />
      
      {/* Foreground Content with normal interaction */}
      <div 
        style={{
          position: 'relative',
          zIndex: 1,
          width: '100%',
          minHeight: '100vh'
        }}
      >
        {children}
      </div>
    </div>
  );
}

export default TubesBackground;
