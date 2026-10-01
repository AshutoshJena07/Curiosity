import React, { useState, useEffect, useRef } from 'react';
import './DeleteInteractionButton.css';

/**
 * DeleteInteractionButton
 * Inspired by Framer's award-winning Delete Interaction component
 * States:
 *   1. 'default'  - Pill button (Danger Red) -> "Delete"
 *   2. 'timer'    - Morphs into Cancel Countdown -> [Undo Icon] "Cancel deletion" [Live Number Badge]
 *   3. 'success'  - Morphs into Success confirmation -> [Checkmark Icon] "Deleted"
 */
export default function DeleteInteractionButton({
  label = 'Delete',
  cancelLabel = 'Cancel deletion',
  successLabel = 'Deleted',
  countdown = 5,
  onDelete,
  onCancel,
  size = 'md', // 'sm' | 'md' | 'lg'
  className = '',
  disabled = false,
}) {
  const [variant, setVariant] = useState('default'); // 'default' | 'timer' | 'success'
  const [timeLeft, setTimeLeft] = useState(countdown);
  const timerRef = useRef(null);
  const intervalRef = useRef(null);

  // Clear timers on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const startCountdown = () => {
    if (disabled || variant !== 'default') return;
    setVariant('timer');
    setTimeLeft(countdown);

    // Tick every second
    intervalRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(intervalRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    // Trigger success when countdown hits 0
    timerRef.current = setTimeout(async () => {
      clearInterval(intervalRef.current);
      setVariant('success');
      try {
        if (onDelete) {
          await onDelete();
        }
      } catch (err) {
        console.error('Delete action failed:', err);
        setVariant('default');
      }
    }, countdown * 1000);
  };

  const cancelDeletion = (e) => {
    e.stopPropagation();
    if (timerRef.current) clearTimeout(timerRef.current);
    if (intervalRef.current) clearInterval(intervalRef.current);
    setVariant('default');
    setTimeLeft(countdown);
    if (onCancel) onCancel();
  };

  const handleClick = (e) => {
    if (disabled) return;
    if (variant === 'default') {
      startCountdown();
    } else if (variant === 'timer') {
      cancelDeletion(e);
    }
  };

  return (
    <button
      type="button"
      className={`delete-interaction-btn ${size} ${variant} ${className}`.trim()}
      onClick={handleClick}
      disabled={disabled || variant === 'success'}
      aria-label={variant === 'timer' ? cancelLabel : variant === 'success' ? successLabel : label}
    >
      <div className="btn-content-inner">
        {/* Default State */}
        {variant === 'default' && (
          <div className="state-default">
            <svg
              className="delete-trash-icon"
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 6h18" />
              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
            </svg>
            <span className="btn-label-text">{label}</span>
          </div>
        )}

        {/* Timer State (Cancel Deletion with Countdown) */}
        {variant === 'timer' && (
          <div className="state-timer">
            {/* Undo Icon Circle */}
            <div className="undo-badge" title="Click to undo">
              <svg
                className="undo-icon"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M9 14 4 9l5-5" />
                <path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5v0a5.5 5.5 0 0 1-5.5 5.5H11" />
              </svg>
            </div>

            {/* Cancel Label */}
            <span className="btn-cancel-text">{cancelLabel}</span>

            {/* Countdown Badge */}
            <div className="countdown-pill" key={timeLeft}>
              <span className="countdown-number">{timeLeft}</span>
            </div>
          </div>
        )}

        {/* Success State */}
        {variant === 'success' && (
          <div className="state-success">
            <div className="success-icon-badge">
              <svg
                className="check-icon"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </div>
            <span className="btn-success-text">{successLabel}</span>
          </div>
        )}
      </div>
    </button>
  );
}
