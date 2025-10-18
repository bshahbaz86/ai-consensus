import React, { useState, useEffect } from 'react';
import { X, Settings } from 'lucide-react';
import axios from 'axios';
import './ModelSelectionModal.css';

// Helper function to get CSRF token from cookies
const getCsrfToken = (): string | null => {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const [cookieName, cookieValue] = cookie.trim().split('=');
    if (cookieName === name) {
      return cookieValue;
    }
  }
  return null;
};

interface Model {
  provider: string;
  model_id: string;
  display_name: string;
  is_default: boolean;
}

interface ModelPreferences {
  openai_model: string;
  claude_model: string;
  gemini_model: string;
}

interface ApiResponse {
  success: boolean;
  data?: ModelPreferences;
  message?: string;
}

interface ModelSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Curated list of 8 top models
const CURATED_MODELS: Model[] = [
  {
    provider: 'openai',
    model_id: 'gpt-4o',
    display_name: 'gpt-4o',
    is_default: true
  },
  {
    provider: 'openai',
    model_id: 'gpt-3.5-turbo',
    display_name: 'gpt-3.5-turbo',
    is_default: false
  },
  {
    provider: 'claude',
    model_id: 'claude-3-7-sonnet-20250219',
    display_name: 'Claude Sonnet 3.7',
    is_default: false
  },
  {
    provider: 'claude',
    model_id: 'claude-opus-4-20250514',
    display_name: 'Claude Opus 4',
    is_default: false
  },
  {
    provider: 'claude',
    model_id: 'claude-sonnet-4-5-20250929',
    display_name: 'Claude Sonnet 4.5',
    is_default: true
  },
  {
    provider: 'gemini',
    model_id: 'models/gemini-2.5-pro',
    display_name: 'Gemini 2.5 Pro',
    is_default: false
  },
  {
    provider: 'gemini',
    model_id: 'models/gemini-2.5-flash',
    display_name: 'Gemini 2.5 Flash',
    is_default: false
  },
  {
    provider: 'gemini',
    model_id: 'models/gemini-flash-latest',
    display_name: 'Gemini Flash Latest',
    is_default: true
  }
];

const ModelSelectionModal: React.FC<ModelSelectionModalProps> = ({ isOpen, onClose }) => {
  const [selectedModels, setSelectedModels] = useState<{
    openai: string;
    claude: string;
    gemini: string;
  }>({
    openai: 'gpt-4o',
    claude: 'claude-sonnet-4-5-20250929',
    gemini: 'models/gemini-flash-latest'
  });

  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  // Fetch current user preferences
  useEffect(() => {
    if (isOpen) {
      fetchPreferences();
    }
  }, [isOpen]);

  const fetchPreferences = async () => {
    try {
      const response = await axios.get<ApiResponse>('http://localhost:8000/api/v1/accounts/model-preferences/', {
        withCredentials: true
      });

      if (response.data.success && response.data.data) {
        const prefs = response.data.data;
        setSelectedModels({
          openai: prefs.openai_model || 'gpt-4o',
          claude: prefs.claude_model || 'claude-sonnet-4-5-20250929',
          gemini: prefs.gemini_model || 'models/gemini-flash-latest'
        });
      }
    } catch (error) {
      console.error('Error fetching model preferences:', error);
    }
  };

  const handleModelChange = (provider: string, modelId: string) => {
    setSelectedModels(prev => ({
      ...prev,
      [provider]: modelId
    }));
  };

  const handleSave = async () => {
    setLoading(true);
    setSuccessMessage('');

    try {
      const csrfToken = getCsrfToken();
      const response = await axios.put<ApiResponse>(
        'http://localhost:8000/api/v1/accounts/model-preferences/',
        {
          openai_model: selectedModels.openai,
          claude_model: selectedModels.claude,
          gemini_model: selectedModels.gemini
        },
        {
          withCredentials: true,
          headers: csrfToken ? {
            'X-CSRFToken': csrfToken
          } : {}
        }
      );

      if (response.data.success) {
        setSuccessMessage('Model preferences updated successfully!');
        setTimeout(() => {
          setSuccessMessage('');
          onClose();
        }, 1500);
      }
    } catch (error) {
      console.error('Error saving model preferences:', error);
      alert('Failed to save model preferences. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  // Group models by provider
  const modelsByProvider = {
    openai: CURATED_MODELS.filter(m => m.provider === 'openai'),
    claude: CURATED_MODELS.filter(m => m.provider === 'claude'),
    gemini: CURATED_MODELS.filter(m => m.provider === 'gemini')
  };

  return (
    <div className="model-selection-overlay" onClick={onClose}>
      <div className="model-selection-modal" onClick={(e) => e.stopPropagation()}>
        <div className="model-selection-header">
          <h2>Select AI Models</h2>
          <button onClick={onClose} className="close-btn">
            <X size={20} />
          </button>
        </div>

        <div className="model-selection-content">
          {/* Success Message */}
          {successMessage && (
            <div className="success-message">{successMessage}</div>
          )}

          {/* OpenAI Models */}
          <div className="model-section">
            <div className="section-icon">
              <Settings size={24} />
            </div>
            <h3>OpenAI</h3>
            <p>Select your preferred OpenAI model</p>

            <div className="model-options">
              {modelsByProvider.openai.map(model => (
                <label
                  key={model.model_id}
                  className="model-option"
                >
                  <input
                    type="radio"
                    name="openai"
                    value={model.model_id}
                    checked={selectedModels.openai === model.model_id}
                    onChange={() => handleModelChange('openai', model.model_id)}
                  />
                  <span className="model-label">{model.display_name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Claude Models */}
          <div className="model-section">
            <div className="section-icon">
              <Settings size={24} />
            </div>
            <h3>Claude</h3>
            <p>Select your preferred Claude model</p>

            <div className="model-options">
              {modelsByProvider.claude.map(model => (
                <label
                  key={model.model_id}
                  className="model-option"
                >
                  <input
                    type="radio"
                    name="claude"
                    value={model.model_id}
                    checked={selectedModels.claude === model.model_id}
                    onChange={() => handleModelChange('claude', model.model_id)}
                  />
                  <span className="model-label">{model.display_name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Gemini Models */}
          <div className="model-section">
            <div className="section-icon">
              <Settings size={24} />
            </div>
            <h3>Gemini</h3>
            <p>Select your preferred Gemini model</p>

            <div className="model-options">
              {modelsByProvider.gemini.map(model => (
                <label
                  key={model.model_id}
                  className="model-option"
                >
                  <input
                    type="radio"
                    name="gemini"
                    value={model.model_id}
                    checked={selectedModels.gemini === model.model_id}
                    onChange={() => handleModelChange('gemini', model.model_id)}
                  />
                  <span className="model-label">{model.display_name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Save Button */}
          <button
            onClick={handleSave}
            disabled={loading}
            className="save-btn"
          >
            {loading ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModelSelectionModal;
