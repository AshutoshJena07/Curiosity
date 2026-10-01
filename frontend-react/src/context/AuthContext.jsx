import React, { createContext, useContext, useState, useEffect } from 'react';
import { getMe, loginUser, registerUser, logoutUser, supabaseLogin } from '../services/api';

export function formatUserDisplayName(user) {
  if (!user) return 'Explorer';
  if (user.name && user.name.trim()) {
    const firstWord = user.name.trim().split(' ')[0];
    return firstWord.charAt(0).toUpperCase() + firstWord.slice(1);
  }
  if (user.email) {
    const raw = user.email.split('@')[0];
    const lettersOnly = raw.replace(/[0-9_.-]+$/, '');
    const clean = lettersOnly.length >= 2 ? lettersOnly : raw;
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  }
  return 'Explorer';
}

const AuthContext = createContext(null);

export function AuthProvider({ children, navigate }) {
  const [token, setToken] = useState(() => localStorage.getItem('auth_token'));
  const [user, setUser] = useState(() => {
    const savedEmail = localStorage.getItem('user_email');
    const savedName = localStorage.getItem('user_name');
    return savedEmail ? { email: savedEmail, name: savedName } : null;
  });
  const [loading, setLoading] = useState(false);
  const [guestMode, setGuestModeState] = useState(() => {
    return localStorage.getItem('guest_mode') === 'true';
  });

  const setGuestMode = (val) => {
    setGuestModeState(val);
    if (val) {
      localStorage.setItem('guest_mode', 'true');
    } else {
      localStorage.removeItem('guest_mode');
    }
  };

  // Handle Supabase OAuth callback (Google, GitHub, etc.)
  useEffect(() => {
    let active = true;

    const handleOAuthCallback = async () => {
      const fullHash = window.location.hash || '';
      const searchStr = window.location.search || '';

      let accessToken = null;
      let errorMsg = null;

      if (fullHash.includes('access_token=') || fullHash.includes('error=')) {
        const raw = fullHash.replace(/^#\/?/, '');
        const tokenPart = raw.includes('access_token=') ? raw.slice(raw.indexOf('access_token=')) : raw;
        const params = new URLSearchParams(tokenPart);
        accessToken = params.get('access_token');
        errorMsg = params.get('error_description') || params.get('error');
      } else if (searchStr.includes('access_token=') || searchStr.includes('error=')) {
        const params = new URLSearchParams(searchStr);
        accessToken = params.get('access_token');
        errorMsg = params.get('error_description') || params.get('error');
      }

      if (errorMsg) {
        console.error('Supabase OAuth error:', errorMsg);
        window.history.replaceState(null, '', window.location.pathname + '#/login');
        if (navigate) navigate('#/login');
        return;
      }

      if (accessToken) {
        setLoading(true);
        try {
          const data = await supabaseLogin(accessToken);
          if (!active) return;
          localStorage.setItem('auth_token', data.token);
          localStorage.setItem('user_email', data.email);
          if (data.name) {
            localStorage.setItem('user_name', data.name);
          }
          localStorage.removeItem('guest_mode');
          setToken(data.token);
          setUser({ email: data.email, name: data.name });
          setGuestModeState(false);
          setLoading(false);
          window.location.hash = '#/workspace';
          if (navigate) navigate('#/workspace');
        } catch (err) {
          console.error('Supabase OAuth token exchange failed:', err);
          window.location.hash = '#/login';
          if (navigate) navigate('#/login');
        } finally {
          if (active) setLoading(false);
        }
      }
    };

    handleOAuthCallback();
    window.addEventListener('hashchange', handleOAuthCallback);
    return () => {
      active = false;
      window.removeEventListener('hashchange', handleOAuthCallback);
    };
  }, [navigate]);

  // Sync token to API validation
  useEffect(() => {
    let isMounted = true;

    async function validateToken() {
      if (!token) {
        if (isMounted) {
          setUser(null);
        }
        return;
      }
      try {
        const profile = await getMe(token);
        if (isMounted) {
          const savedName = localStorage.getItem('user_name');
          setUser({ ...profile, name: profile?.name || savedName });
          if (profile?.email) {
            localStorage.setItem('user_email', profile.email);
          }
        }
      } catch (err) {
        console.warn("Token validation issue:", err);
        // Only clear token if server explicitly rejected with 401 or 403 or 404
        if (err.status === 401 || err.status === 403 || err.status === 404) {
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_email');
          if (isMounted) {
            setToken(null);
            setUser(null);
          }
        }
      }
    }
    validateToken();

    return () => {
      isMounted = false;
    };
  }, [token]);

  const handleLogin = async (email, password) => {
    try {
      const data = await loginUser(email, password);
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('user_email', data.email || email);
      localStorage.removeItem('guest_mode');
      const savedName = localStorage.getItem('user_name');
      setToken(data.token);
      setUser({ email: data.email || email, name: data.name || savedName });
      setGuestMode(false);
      navigate('#/workspace');
    } catch (err) {
      throw err;
    }
  };

  const handleRegister = async (email, password) => {
    try {
      await registerUser(email, password);
    } catch (err) {
      throw err;
    }
  };

  const handleLogout = async () => {
    if (token) {
      try {
        await logoutUser(token);
      } catch (err) {
        console.warn("Server logout failed, proceeding to clear client session.", err);
      }
    }
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_email');
    localStorage.removeItem('guest_mode');
    setToken(null);
    setUser(null);
    setGuestMode(false);
    navigate('#/');
  };

  const enterGuestMode = () => {
    setGuestMode(true);
    setToken(null);
    setUser(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_email');
    navigate('#/workspace');
  };

  const displayName = formatUserDisplayName(user);

  const value = {
    token,
    user,
    displayName,
    loading,
    guestMode,
    login: handleLogin,
    register: handleRegister,
    logout: handleLogout,
    enterGuestMode
  };


  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
