import React, { useState } from 'react';
import './SetPassword.css';

interface SetPasswordProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

const SetPassword: React.FC<SetPasswordProps> = ({ onSuccess, onCancel }) => {
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setSuccessMessage('');

    // Client-side validation
    if (password !== passwordConfirm) {
      setError("Passwords don't match");
      setIsLoading(false);
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      setIsLoading(false);
      return;
    }

    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        setError('You must be logged in to set a password');
        setIsLoading(false);
        return;
      }

      const response = await fetch('http://localhost:8000/api/v1/accounts/auth/password/set/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Token ${token}`,
        },
        credentials: 'include',
        body: JSON.stringify({ password, password_confirm: passwordConfirm }),
      });

      const data = await response.json();

      if (data.success) {
        setSuccessMessage('Password set successfully! You can now login with your password.');

        // Update user data in localStorage to reflect the change
        const userStr = localStorage.getItem('user');
        if (userStr) {
          const user = JSON.parse(userStr);
          user.has_permanent_password = true;
          localStorage.setItem('user', JSON.stringify(user));
        }

        // Clear form
        setPassword('');
        setPasswordConfirm('');

        // Call success callback after a brief delay
        if (onSuccess) {
          setTimeout(onSuccess, 2000);
        }
      } else {
        setError(data.message || data.errors?.password?.[0] || 'Failed to set password');
      }
    } catch (error) {
      console.error('Error setting password:', error);
      setError('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="set-password">
      <div className="set-password-container">
        <div className="set-password-header">
          <h2>Set a Permanent Password</h2>
          <p>Add a password to your account for an alternative way to sign in</p>
        </div>

        <form onSubmit={handleSetPassword} className="set-password-form">
          {successMessage && <div className="success-message">{successMessage}</div>}
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="password">New Password</label>
            <div className="password-input-wrapper">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter a strong password"
                required
                disabled={isLoading}
                minLength={8}
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
            <small>Must be at least 8 characters long</small>
          </div>

          <div className="form-group">
            <label htmlFor="passwordConfirm">Confirm Password</label>
            <div className="password-input-wrapper">
              <input
                type={showPasswordConfirm ? 'text' : 'password'}
                id="passwordConfirm"
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="Re-enter your password"
                required
                disabled={isLoading}
                minLength={8}
              />
              <button
                type="button"
                onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
                className="toggle-password-btn"
                tabIndex={-1}
              >
                {showPasswordConfirm ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          <div className="button-group">
            <button type="submit" disabled={isLoading} className="submit-btn">
              {isLoading ? 'Setting Password...' : 'Set Password'}
            </button>

            {onCancel && (
              <button type="button" onClick={onCancel} disabled={isLoading} className="cancel-btn">
                Cancel
              </button>
            )}
          </div>
        </form>

        <div className="set-password-footer">
          <p>
            Once set, you'll be able to sign in using either your email and password or your
            existing authentication method.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SetPassword;
