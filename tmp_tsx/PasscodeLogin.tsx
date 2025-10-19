import React, { useState } from 'react';
import './PasscodeLogin.css';

interface PasscodeLoginProps {
  onBack: () => void;
}

const PasscodeLogin: React.FC<PasscodeLoginProps> = ({ onBack }) => {
  const [step, setStep] = useState<'email' | 'passcode'>('email');
  const [email, setEmail] = useState('');
  const [passcode, setPasscode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const handleSendPasscode = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setSuccessMessage('');

    try {
      const response = await fetch('http://localhost:8000/api/v1/accounts/auth/passcode/send/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (data.success) {
        setSuccessMessage(`Passcode sent to ${email}. Check your email!`);
        setStep('passcode');
      } else {
        setError(data.message || 'Failed to send passcode');
      }
    } catch (error) {
      console.error('Error sending passcode:', error);
      setError('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyPasscode = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/v1/accounts/auth/passcode/verify/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, passcode }),
      });

      const data = await response.json();

      if (data.success) {
        // Store authentication data
        localStorage.setItem('auth_token', data.data.token);
        localStorage.setItem('user', JSON.stringify(data.data.user));

        // Redirect to main app
        window.location.href = '/';
      } else {
        setError(data.message || data.errors?.passcode?.[0] || 'Invalid passcode');
      }
    } catch (error) {
      console.error('Error verifying passcode:', error);
      setError('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToEmail = () => {
    setStep('email');
    setPasscode('');
    setError('');
    setSuccessMessage('');
  };

  return (
    <div className="passcode-login">
      <div className="passcode-container">
        <button onClick={onBack} className="back-btn">
          ← Back to all options
        </button>

        <div className="passcode-header">
          <h2>Sign in with Email</h2>
          <p>
            {step === 'email'
              ? 'Enter your email to receive a temporary login code'
              : 'Enter the 6-digit code sent to your email'}
          </p>
        </div>

        {step === 'email' ? (
          <form onSubmit={handleSendPasscode} className="passcode-form">
            {successMessage && <div className="success-message">{successMessage}</div>}
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

            <button type="submit" disabled={isLoading} className="submit-btn">
              {isLoading ? 'Sending...' : 'Send Code'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleVerifyPasscode} className="passcode-form">
            {error && <div className="error-message">{error}</div>}

            <div className="form-group">
              <label htmlFor="passcode">6-Digit Code</label>
              <input
                type="text"
                id="passcode"
                value={passcode}
                onChange={(e) => setPasscode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                required
                disabled={isLoading}
                autoFocus
                className="passcode-input"
              />
              <small>Code sent to {email}</small>
            </div>

            <button type="submit" disabled={isLoading || passcode.length !== 6} className="submit-btn">
              {isLoading ? 'Verifying...' : 'Verify & Sign In'}
            </button>

            <button type="button" onClick={handleBackToEmail} className="link-btn">
              Use a different email
            </button>

            <button
              type="button"
              onClick={handleSendPasscode}
              disabled={isLoading}
              className="link-btn"
            >
              Resend code
            </button>
          </form>
        )}

        <div className="passcode-footer">
          <p>The code will expire in 15 minutes</p>
        </div>
      </div>
    </div>
  );
};

export default PasscodeLogin;
