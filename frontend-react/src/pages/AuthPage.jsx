import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  ArrowLeftIcon,
  AlertTriangleIcon,
  CheckCircleIcon
} from '../components/Common/Icons';

export default function AuthPage({ isSignUpDefault = true, navigate }) {
  const { login, register } = useAuth();
  const [isSignUp, setIsSignUp] = useState(isSignUpDefault);

  // Form states
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    const cleanEmail = email.trim();
    if (!cleanEmail || !password) {
      setErrorMsg('Please fill in all required fields.');
      return;
    }

    if (isSignUp) {
      if (!firstName.trim() || !lastName.trim()) {
        setErrorMsg('Please enter your first and last name.');
        return;
      }
      if (password.length < 8) {
        setErrorMsg('Password must be at least 8 characters long.');
        return;
      }
    }

    setLoading(true);
    try {
      if (isSignUp) {
        await register(cleanEmail, password);
        const fullName = `${firstName.trim()} ${lastName.trim()}`;
        if (fullName) {
          localStorage.setItem('user_name', fullName);
        }
        setSuccessMsg('Account created successfully! You can now log in.');
        setIsSignUp(false);
        setPassword('');
      } else {
        await login(cleanEmail, password);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Authentication failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSocialAuth = (provider) => {
    setErrorMsg('');
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://ilzaltvxvtyyfphbtyyj.supabase.co';
    const redirectUrl = window.location.origin + window.location.pathname;
    const providerParam = provider.toLowerCase();
    const targetUrl = `${supabaseUrl}/auth/v1/authorize?provider=${providerParam}&redirect_to=${encodeURIComponent(redirectUrl)}`;
    window.location.href = targetUrl;
  };

  return (
    <div className="auth-page-container">
      {/* ── FLOATING TOP BACK BUTTON ── */}
      <button 
        type="button"
        className="auth-back-btn" 
        onClick={() => navigate('#/')}
        title="Back to Landing Page"
      >
        <ArrowLeftIcon size={14} />
        <span>Back to Home</span>
      </button>

      {/* ── DUAL-PANE AUTH CARD ── */}
      <div className="auth-split-card">
        
        {/* ── LEFT SHOWCASE PANE (PURPLE GLOWING GRADIENT & STEPPER) ── */}
        <div className="auth-showcase-pane">
          
          {/* Brand Logo & Name */}
          <div className="auth-brand-pill">
            <span className="brand-dot-ring" aria-hidden="true" />
            <span className="auth-brand-name">Curiosity</span>
          </div>

          {/* Heading & Subtitle */}
          <h1 className="auth-showcase-title">
            {isSignUp ? 'Get Started with Us' : 'Welcome Back to Us'}
          </h1>
          <p className="auth-showcase-desc">
            {isSignUp 
              ? 'Complete these easy steps to register your account.' 
              : 'Authenticate your credentials to access your workspace.'}
          </p>

          {/* Stepper Checklist Stack */}
          <div className="auth-steps-stack">
            {/* Step 1: Active Card */}
            <div className="auth-step-card active">
              <span className="step-num-badge">1</span>
              <span className="step-card-text">
                {isSignUp ? 'Sign up your account' : 'Sign in to account'}
              </span>
            </div>

            {/* Step 2: Inactive Card */}
            <div className="auth-step-card inactive">
              <span className="step-num-badge">2</span>
              <span className="step-card-text">
                {isSignUp ? 'Set up your workspace' : 'Resume workspace'}
              </span>
            </div>

            {/* Step 3: Inactive Card */}
            <div className="auth-step-card inactive">
              <span className="step-num-badge">3</span>
              <span className="step-card-text">
                {isSignUp ? 'Set up your profile' : 'Access Curiosity'}
              </span>
            </div>
          </div>

        </div>

        {/* ── RIGHT FORM PANE (SLEEK PITCH BLACK) ── */}
        <div className="auth-form-pane">
          
          {/* Header */}
          <div className="auth-form-header">
            <h2 className="auth-form-title">
              {isSignUp ? 'Sign Up Account' : 'Sign In Account'}
            </h2>
            <p className="auth-form-subtitle">
              {isSignUp 
                ? 'Enter your personal data to create your account.' 
                : 'Enter your credentials to access your private workspace.'}
            </p>
          </div>

          {/* Notification Alerts */}
          {errorMsg && (
            <div className="auth-notification-banner error">
              <AlertTriangleIcon size={14} />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="auth-notification-banner success">
              <CheckCircleIcon size={14} />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Social Auth Buttons Row */}
          <div className="auth-social-row">
            {/* Google Button */}
            <button 
              type="button" 
              className="auth-social-btn" 
              onClick={() => handleSocialAuth('Google')}
              disabled={loading}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
              </svg>
              <span>Google</span>
            </button>

            {/* GitHub Button */}
            <button 
              type="button" 
              className="auth-social-btn" 
              onClick={() => handleSocialAuth('GitHub')}
              disabled={loading}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
              </svg>
              <span>Github</span>
            </button>
          </div>

          {/* Divider */}
          <div className="auth-divider-wrap">
            <span className="auth-divider-line" />
            <span>Or</span>
            <span className="auth-divider-line" />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="auth-form-body">
            
            {/* First Name & Last Name (Only in Sign Up Mode) */}
            {isSignUp && (
              <div className="auth-input-row">
                <div className="auth-field-group">
                  <label className="auth-field-label">First Name</label>
                  <input 
                    type="text" 
                    className="auth-input-field" 
                    placeholder="eg. John"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>

                <div className="auth-field-group">
                  <label className="auth-field-label">Last Name</label>
                  <input 
                    type="text" 
                    className="auth-input-field" 
                    placeholder="eg. Francisco"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
              </div>
            )}

            {/* Email Address */}
            <div className="auth-field-group">
              <label className="auth-field-label">Email</label>
              <input 
                type="email" 
                className="auth-input-field" 
                placeholder="eg. johnfrans@gmail.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
              />
            </div>

            {/* Password Field with Eye Toggle */}
            <div className="auth-field-group">
              <label className="auth-field-label">Password</label>
              <div className="auth-input-wrapper">
                <input 
                  type={showPassword ? 'text' : 'password'} 
                  className="auth-input-field" 
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                />
                <button 
                  type="button" 
                  className="auth-pw-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  title={showPassword ? "Hide password" : "Show password"}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
              {isSignUp && (
                <span className="auth-field-hint">Must be at least 8 characters.</span>
              )}
            </div>

            {/* Primary Submit Button */}
            <button 
              type="submit" 
              className="auth-primary-action-btn" 
              disabled={loading}
            >
              <span className="auth-btn-label">
                {loading 
                  ? 'Processing...' 
                  : isSignUp 
                    ? 'Sign Up' 
                    : 'Sign In'}
              </span>
            </button>
          </form>

          {/* Switch Sign Up / Log In Toggle */}
          <div className="auth-footer-toggle">
            {isSignUp ? (
              <span>
                Already have an account?{' '}
                <button 
                  type="button"
                  className="auth-switch-link"
                  onClick={() => {
                    setIsSignUp(false);
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  disabled={loading}
                >
                  Log in
                </button>
              </span>
            ) : (
              <span>
                Don't have an account?{' '}
                <button 
                  type="button"
                  className="auth-switch-link"
                  onClick={() => {
                    setIsSignUp(true);
                    setErrorMsg('');
                    setSuccessMsg('');
                  }}
                  disabled={loading}
                >
                  Sign up
                </button>
              </span>
            )}
          </div>

        </div>

      </div>

    </div>
  );
}
