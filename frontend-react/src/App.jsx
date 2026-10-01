import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import HomePage from './pages/HomePage';
import AuthPage from './pages/AuthPage';
import WorkspacePage from './pages/WorkspacePage';
import NotFoundPage from './pages/NotFoundPage';
import TubesBackground from './components/Common/TubesBackground';
import SiteLoader from './components/Common/SiteLoader';

function AppRouter() {
  const { token, user, loading, guestMode } = useAuth();
  const [currentHash, setCurrentHash] = useState(() => window.location.hash || '#/');
  
  // Dashboard dynamic launchers preloads
  const [preloadedFile, setPreloadedFile] = useState(null);
  const [preloadedPrompt, setPreloadedPrompt] = useState('');

  useEffect(() => {
    const handleHashChange = () => {
      setCurrentHash(window.location.hash || '#/');
    };
    window.addEventListener('hashchange', handleHashChange);
    window.addEventListener('popstate', handleHashChange);
    return () => {
      window.removeEventListener('hashchange', handleHashChange);
      window.removeEventListener('popstate', handleHashChange);
    };
  }, []);

  const navigate = (newHash) => {
    window.location.hash = newHash;
    setCurrentHash(newHash);
  };

  const handleNewSessionWithFile = (file) => {
    setPreloadedFile(file);
    navigate('#/workspace');
  };

  const handleNewSessionWithPrompt = (promptText) => {
    setPreloadedPrompt(promptText);
    navigate('#/workspace');
  };

  const actualHash = window.location.hash || currentHash || '#/';
  const isParsingOAuth = (actualHash.includes('access_token=') || actualHash.includes('refresh_token=')) && !token;

  if (isParsingOAuth) {
    return <SiteLoader text="LOADING" />;
  }

  const hash = actualHash;

  if (hash === '#/' || hash === '') {
    return <HomePage navigate={navigate} />;
  }

  if (hash === '#/login' || hash === '#/signup') {
    if (token) {
      navigate('#/workspace');
      return null;
    }
    return <AuthPage isSignUpDefault={hash === '#/signup'} navigate={navigate} />;
  }

  if (hash === '#/dashboard') {
    navigate('#/workspace');
    return null;
  }

  const isWorkspaceNew = hash === '#/workspace';
  const isWorkspaceSession = hash.startsWith('#/workspace/');

  if (isWorkspaceNew || isWorkspaceSession) {
    if (!token && !guestMode) {
      navigate('#/login');
      return null;
    }

    const conversationId = isWorkspaceSession ? hash.replace('#/workspace/', '') : null;

    return (
      <WorkspacePage 
        navigate={navigate} 
        conversationId={conversationId}
        preloadedFile={preloadedFile}
        clearPreloadedFile={() => setPreloadedFile(null)}
        preloadedPrompt={preloadedPrompt}
        clearPreloadedPrompt={() => setPreloadedPrompt('')}
      />
    );
  }

  // Render React Bits Pro 404-3 block for any invalid or unmapped routes
  return <NotFoundPage navigate={navigate} />;
}

function App() {
  const navigate = (hash) => {
    window.location.hash = hash;
  };

  return (
    <ThemeProvider>
      <AuthProvider navigate={navigate}>
        <TubesBackground>
          <AppRouter />
        </TubesBackground>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
