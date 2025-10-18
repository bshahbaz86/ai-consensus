import React, { useState } from 'react';
import './PasswordLogin.css';

interface PasswordLoginProps {
  onBack: () => void;
}

const PasswordLogin: React.FC<PasswordLoginProps> = ({ onBack }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/v1/accounts/auth/password/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (data.success) {
        // Store authentication data
        localStorage.setItem('auth_token', data.data.token);
        localStorage.setItem('user', JSON.stringify(data.data.user));

        // Redirect to main app
        window.location.href = '/';
      } else {
        if (data.errors?.detail && data.errors.detail.includes('does not have a password set')) {
          setError('This account does not have a password set. Please use Google OAuth or email passcode login.');
        } else {
          setError(data.message || 'Invalid email or password');
        }
      }
    } catch (error) {
      console.error('Error logging in:', error);
      setError('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="password-login">
      <div className="password-container">
        <button onClick={onBack} className="back-btn">
          ← Back to all options
        </button>

        <div className="password-header">
          <h2>Sign in with Password</h2>
          <p>Enter your email and password to continue</p>
        </div>

        <form onSubmit={handlePasswordLogin} className="password-form">
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="email">Email Address</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              disabled={isLoading}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-input-wrapper">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="toggle-password-btn"
                tabIndex={-1}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          <button type="submit" disabled={isLoading} className="submit-btn">
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="password-footer">
          <p>
            Don't have a password yet? Sign in with Google or email, then set a password in your
            account settings.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PasswordLogin;
