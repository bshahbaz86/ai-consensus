import React, { useState } from 'react';
import { X, Lock } from 'lucide-react';
import { apiService } from '../services/api';
import './AccountSettings.css';

interface AccountSettingsProps {
  onClose: () => void;
}

const AccountSettings: React.FC<AccountSettingsProps> = ({ onClose }) => {
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch('http://localhost:8000/api/v1/accounts/auth/password/set/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${localStorage.getItem('auth_token')}`,
        },
        credentials: 'include',
        body: JSON.stringify({ password, password_confirm: passwordConfirm }),
      });

      const data = await response.json();

      if (data.success) {
        setSuccess('Password set successfully! You can now use it to sign in.');
        setPassword('');
        setPasswordConfirm('');

        // Close modal after 2 seconds
        setTimeout(() => {
          onClose();
        }, 2000);
      } else {
        setError(data.message || 'Failed to set password');
      }
    } catch (error) {
      console.error('Error setting password:', error);
      setError('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="account-settings-overlay" onClick={onClose}>
      <div className="account-settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="account-settings-header">
          <h2>Account Settings</h2>
          <button onClick={onClose} className="close-btn">
            <X size={20} />
          </button>
        </div>

        <div className="account-settings-content">
          <div className="settings-section">
            <div className="section-icon">
              <Lock size={24} />
            </div>
            <h3>Set Password</h3>
            <p>Create a password to enable password-based login for your account.</p>

            <form onSubmit={handleSetPassword} className="password-form">
              {error && <div className="error-message">{error}</div>}
              {success && <div className="success-message">{success}</div>}

              <div className="form-group">
                <label htmlFor="password">New Password</label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter new password"
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
                <small>Use a password at least 15 letters long, or at least 8 characters long with both letters and numbers.</small>
              </div>

              <div className="form-group">
                <label htmlFor="password-confirm">Confirm Password</label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password-confirm"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  placeholder="Re-enter password"
                  required
                  disabled={isLoading}
                />
              </div>

              <button type="submit" disabled={isLoading} className="submit-btn">
                {isLoading ? 'Setting Password...' : 'Set Password'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AccountSettings;
