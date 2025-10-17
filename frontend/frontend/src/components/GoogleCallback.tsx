import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import './GoogleCallback.css';

const GoogleCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const error = searchParams.get('error');

      if (error) {
        setStatus('error');
        setErrorMessage('Google authentication was cancelled or failed');
        return;
      }

      if (!code) {
        setStatus('error');
        setErrorMessage('No authorization code received');
        return;
      }

      try {
        // Send authorization code to backend
        const response = await fetch('http://localhost:8000/api/v1/accounts/auth/google/callback/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ code }),
        });

        const data = await response.json();

        if (data.success) {
          // Save token
          localStorage.setItem('auth_token', data.data.token);

          // Save user data
          localStorage.setItem('user', JSON.stringify(data.data.user));

          setStatus('success');

          // Redirect to main app
          setTimeout(() => {
            navigate('/');
          }, 1000);
        } else {
          setStatus('error');
          setErrorMessage(data.message || 'Authentication failed');
        }
      } catch (error) {
        console.error('Error processing Google callback:', error);
        setStatus('error');
        setErrorMessage('Network error during authentication');
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <div className="callback-container">
      {status === 'processing' && (
        <div className="callback-content">
          <div className="spinner"></div>
          <p>Completing Google sign-in...</p>
        </div>
      )}

      {status === 'success' && (
        <div className="callback-content">
          <svg className="success-icon" viewBox="0 0 24 24">
            <path fill="#4CAF50" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
          </svg>
          <p>Successfully signed in! Redirecting...</p>
        </div>
      )}

      {status === 'error' && (
        <div className="callback-content">
          <svg className="error-icon" viewBox="0 0 24 24">
            <path fill="#F44336" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
          <p>{errorMessage}</p>
          <button onClick={() => navigate('/login')} className="back-button">
            Back to login
          </button>
        </div>
      )}
    </div>
  );
};

export default GoogleCallback;
