import React, { useState, useEffect } from 'react';
import { X, Settings } from 'lucide-react';
import axios from 'axios';

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
      const response = await axios.get<ApiResponse>('http://localhost:8000/api/v1/auth/model-preferences/', {
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
        'http://localhost:8000/api/v1/auth/model-preferences/',
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-800 border-b border-gray-700 p-6 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Settings className="text-blue-400" size={24} />
            <h2 className="text-xl font-semibold text-white">Select AI Models</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Success Message */}
          {successMessage && (
            <div className="bg-green-900 border border-green-700 text-green-100 px-4 py-3 rounded-lg">
              {successMessage}
            </div>
          )}

          {/* OpenAI Models */}
          <div>
            <h3 className="text-lg font-medium text-white mb-3 flex items-center gap-2">
              <span className="bg-green-600 text-white text-xs px-2 py-1 rounded">OpenAI</span>
            </h3>
            <div className="space-y-2">
              {modelsByProvider.openai.map(model => (
                <label
                  key={model.model_id}
                  className="flex items-center gap-3 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg cursor-pointer transition-colors"
                >
                  <input
                    type="radio"
                    name="openai"
                    value={model.model_id}
                    checked={selectedModels.openai === model.model_id}
                    onChange={() => handleModelChange('openai', model.model_id)}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-gray-100">{model.display_name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Claude Models */}
          <div>
            <h3 className="text-lg font-medium text-white mb-3 flex items-center gap-2">
              <span className="bg-purple-600 text-white text-xs px-2 py-1 rounded">Claude</span>
            </h3>
            <div className="space-y-2">
              {modelsByProvider.claude.map(model => (
                <label
                  key={model.model_id}
                  className="flex items-center gap-3 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg cursor-pointer transition-colors"
                >
                  <input
                    type="radio"
                    name="claude"
                    value={model.model_id}
                    checked={selectedModels.claude === model.model_id}
                    onChange={() => handleModelChange('claude', model.model_id)}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-gray-100">{model.display_name}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Gemini Models */}
          <div>
            <h3 className="text-lg font-medium text-white mb-3 flex items-center gap-2">
              <span className="bg-blue-600 text-white text-xs px-2 py-1 rounded">Gemini</span>
            </h3>
            <div className="space-y-2">
              {modelsByProvider.gemini.map(model => (
                <label
                  key={model.model_id}
                  className="flex items-center gap-3 p-3 bg-gray-700 hover:bg-gray-600 rounded-lg cursor-pointer transition-colors"
                >
                  <input
                    type="radio"
                    name="gemini"
                    value={model.model_id}
                    checked={selectedModels.gemini === model.model_id}
                    onChange={() => handleModelChange('gemini', model.model_id)}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-gray-100">{model.display_name}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-800 border-t border-gray-700 p-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-300 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ModelSelectionModal;
