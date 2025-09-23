import React, { useState } from 'react';
import { X, Plus, Menu } from 'lucide-react';
import ConversationHistory from './ConversationHistory';
import { apiService, Conversation } from '../services/api';

interface AIResponse {
  service: string;
  success: boolean;
  content?: string;
  error?: string;
}

interface AIConsensusState {
  loading: boolean;
  results: AIResponse[];
  question: string;
}

const AIConsensusDemo: React.FC = () => {
  const [state, setState] = useState<AIConsensusState>({
    loading: false,
    results: [],
    question: ''
  });
  
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);

  const serviceConfig = {
    claude: { name: 'Claude (Anthropic)', color: '#FF6B35', model: 'Claude 3 Haiku' },
    openai: { name: 'GPT-4 (OpenAI)', color: '#00A67E', model: 'GPT-4' },
    gemini: { name: 'Gemini (Google)', color: '#4285F4', model: 'Gemini Flash' }
  };

  const testAllServices = async () => {
    if (!state.question.trim()) {
      alert('Please enter a question first');
      return;
    }

    setState(prev => ({ ...prev, loading: true, results: [] }));

    try {
      const response = await fetch('http://localhost:8001/api/v1/test-ai/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: state.question,
          services: ['claude', 'openai', 'gemini']
        })
      });

      const data = await response.json();
      
      if (data.success) {
        setState(prev => ({ ...prev, results: data.results, loading: false }));
      } else {
        console.error('API Error:', data.error);
        setState(prev => ({ ...prev, loading: false }));
      }
    } catch (error) {
      console.error('Network error:', error);
      setState(prev => ({ ...prev, loading: false }));
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConversation = await apiService.createConversation({
        title: 'New Chat',
        agent_mode: 'standard',
      });
      setSelectedConversation(newConversation);
      setSidebarOpen(false);
    } catch (err) {
      console.error('Error creating new conversation:', err);
    }
  };

  const handleConversationSelect = (conversation: Conversation) => {
    setSelectedConversation(conversation);
    setSidebarOpen(false);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Slide-in Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-80 transform transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } bg-white shadow-lg border-r border-gray-200`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Chats</h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            <button
              onClick={() => {
                handleNewConversation();
                setSidebarOpen(false);
              }}
              className="w-full flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
            >
              <Plus size={16} />
              New Chat
            </button>
          </div>

          {/* Chat History from API */}
          <div className="flex-1 overflow-hidden">
            <ConversationHistory
              currentConversationId={selectedConversation?.id}
              onConversationSelect={(conversation) => {
                handleConversationSelect(conversation);
                setSidebarOpen(false);
              }}
              onNewConversation={() => {
                handleNewConversation();
                setSidebarOpen(false);
              }}
              className="h-full border-r-0"
            />
          </div>
        </div>
      </div>

      {/* Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="max-w-6xl mx-auto p-5">
        {/* Header */}
        <div className="text-center mb-8 bg-white p-5 rounded-lg shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              title="Chat History"
            >
              <Menu size={20} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                AI
              </div>
              <h1 className="text-2xl font-bold text-gray-900">AI Consensus</h1>
            </div>

            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600 font-medium">Select AI Services:</span>
              <div className="flex gap-3">
                <button className="px-4 py-2 rounded-full border-2 border-orange-600 text-orange-600 bg-orange-50 font-medium text-sm flex items-center gap-2">
                  Claude
                  <span className="w-4 h-4 bg-green-500 text-white rounded-full text-xs flex items-center justify-center">✓</span>
                </button>
                <button className="px-4 py-2 rounded-full border-2 border-gray-700 text-gray-700 bg-white font-medium text-sm">
                  OpenAI
                </button>
                <button className="px-4 py-2 rounded-full border-2 border-blue-600 text-blue-600 bg-blue-50 font-medium text-sm flex items-center gap-2">
                  Gemini
                  <span className="w-4 h-4 bg-green-500 text-white rounded-full text-xs flex items-center justify-center">✓</span>
                </button>
              </div>
            </div>
          </div>
          
          <p className="text-gray-600 mb-4">Get consensus from multiple AI services on any question</p>
          
          {/* Question Input */}
          <div className="mb-4">
            <textarea
              className="w-full p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              rows={3}
              placeholder="Enter your question here..."
              value={state.question}
              onChange={(e) => setState(prev => ({ ...prev, question: e.target.value }))}
            />
          </div>
          
          <button
            onClick={testAllServices}
            disabled={state.loading || !state.question.trim()}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white font-medium py-3 px-6 rounded-lg transition-colors disabled:cursor-not-allowed"
          >
            {state.loading ? (
              <span className="flex items-center gap-2">
                <span>AIs are thinking</span>
                <div className="flex gap-1">
                  <span className="animate-pulse">.</span>
                  <span className="animate-pulse" style={{ animationDelay: '0.2s' }}>.</span>
                  <span className="animate-pulse" style={{ animationDelay: '0.4s' }}>.</span>
                </div>
              </span>
            ) : (
              'Ask All AI Services'
            )}
          </button>
        </div>

        {/* Question Display */}
        {state.question && !state.loading && state.results.length === 0 && (
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded">
            <strong>Question:</strong> {state.question}
          </div>
        )}

        {/* Results */}
        {state.loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
            {Object.entries(serviceConfig).map(([key, config]) => (
              <div key={key} className="bg-white rounded-lg p-5 shadow-sm border-t-4" style={{ borderTopColor: config.color }}>
                <div className="flex items-center mb-4">
                  <div
                    className="w-6 h-6 rounded mr-3"
                    style={{ backgroundColor: config.color }}
                  ></div>
                  <div className="font-bold text-lg">{config.name}</div>
                  <div className="ml-auto text-sm bg-gray-100 px-2 py-1 rounded-full">
                    Loading...
                  </div>
                </div>
                <div className="text-gray-600">Generating response...</div>
              </div>
            ))}
          </div>
        )}

        {state.results.length > 0 && (
          <>
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6 rounded">
              <strong>Question:</strong> {state.question}
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
              {state.results.map((result, index) => {
                const config = serviceConfig[result.service.toLowerCase() as keyof typeof serviceConfig];
                if (!config) return null;
                
                return (
                  <div key={index} className="bg-white rounded-lg p-5 shadow-sm border-t-4" style={{ borderTopColor: config.color }}>
                    <div className="flex items-center mb-4">
                      <div
                        className="w-6 h-6 rounded mr-3"
                        style={{ backgroundColor: config.color }}
                        title={config.model}
                      ></div>
                      <div className="font-bold text-lg">{config.name}</div>
                      <div className={`ml-auto text-sm px-2 py-1 rounded-full font-bold ${
                        result.success 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {result.success ? '✅ Success' : '❌ Error'}
                      </div>
                    </div>
                    <div className="text-gray-700 leading-relaxed">
                      {result.success ? result.content : `Error: ${result.error}`}
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Default state */}
        {!state.loading && state.results.length === 0 && !state.question && (
          <div className="text-center py-12 text-gray-500">
            <div className="text-6xl mb-4">🤖</div>
            <p className="text-xl mb-2">Welcome to AI Consensus</p>
            <p>Enter a question above to get responses from multiple AI services</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIConsensusDemo;