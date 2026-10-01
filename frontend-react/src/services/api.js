/**
 * Frontend API Service for Local Image Assistant
 */

export async function checkHealth() {
  try {
    const response = await fetch('/health');
    if (!response.ok) return false;
    const data = await response.json();
    return data.status === 'ok';
  } catch (err) {
    console.warn('Backend health check failed:', err);
    return false;
  }
}

export async function analyzeFile(prompt, fileObj, history = [], userName = '') {
  const data = new FormData();
  
  if (fileObj) {
    // Both file and image keys are appended for compatibility
    data.append('file', fileObj);
    data.append('image', fileObj);
  }
  
  data.append('prompt', prompt || 'Analyze this file and summarize its key content and details.');
  
  // Forward preferred user display name for personalized interactions
  const savedName = localStorage.getItem('user_name') || '';
  const effectiveName = (userName || savedName || '').trim();
  if (effectiveName) {
    data.append('user_name', effectiveName);
  }

  // Clean up history turns: filter out system greetings, active typing indicators, errors, and empty strings
  const cleanHistory = history
    .filter(turn => !turn.typing && !turn.error && turn.text && !turn.text.startsWith('Hello! I am your local'))
    .map(turn => ({
      role: turn.role === 'bot' ? 'assistant' : 'user',
      content: turn.text
    }));
  
  data.append('history', JSON.stringify(cleanHistory.slice(-8)));

  const headers = {};
  const token = localStorage.getItem('auth_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch('/analyze', {
    method: 'POST',
    headers,
    body: data
  });

  let result = null;
  try {
    result = await response.json();
  } catch (err) {
    // Response body is not JSON
  }

  if (!response.ok) {
    throw new Error(result?.detail || `Server error (${response.status}): Failed to analyze file.`);
  }

  return result;
}

async function parseJsonResponse(response, fallbackMsg = 'Request failed') {
  let data = null;
  try {
    const text = await response.text();
    data = text ? JSON.parse(text) : null;
  } catch (err) {
    data = null;
  }

  if (!response.ok) {
    if (response.status === 502 || response.status === 503 || response.status === 504) {
      const err = new Error('Backend server is offline or unreachable. Please run run_backend.bat to start it.');
      err.status = response.status;
      throw err;
    }
    const msg = data?.detail || data?.message || `${fallbackMsg} (Status ${response.status})`;
    const error = new Error(msg);
    error.status = response.status;
    throw error;
  }

  return data;
}

// User Authentication API Calls
export async function registerUser(email, password) {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return await parseJsonResponse(response, 'Registration failed');
}

export async function loginUser(email, password) {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  return await parseJsonResponse(response, 'Login failed');
}

export async function supabaseLogin(accessToken) {
  const response = await fetch('/api/auth/supabase-login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ access_token: accessToken })
  });
  return await parseJsonResponse(response, 'Supabase authentication failed');
}

export async function logoutUser(token) {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await parseJsonResponse(response, 'Logout failed');
}

export async function getMe(token) {
  const response = await fetch('/api/auth/me', {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await parseJsonResponse(response, 'Failed to fetch user profile');
}


// Conversations Persistence API Calls
export async function fetchConversations(token) {
  const response = await fetch('/api/conversations', {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await parseJsonResponse(response, 'Failed to fetch conversations history');
}

export async function fetchConversationDetail(conversationId, token) {
  const response = await fetch(`/api/conversations/${conversationId}`, {
    method: 'GET',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await parseJsonResponse(response, 'Failed to fetch conversation details');
}

export async function saveConversation(conversationData, token) {
  const response = await fetch('/api/conversations', {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(conversationData)
  });
  return await parseJsonResponse(response, 'Failed to save conversation');
}

export async function deleteConversation(conversationId, token) {
  const response = await fetch(`/api/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return await parseJsonResponse(response, 'Failed to delete conversation');
}


