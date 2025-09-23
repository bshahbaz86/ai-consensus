import React, { useState } from 'react';
import { X, Plus, Menu, Globe } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';
import ConversationHistory from './ConversationHistory';
import { apiService, Conversation } from '../services/api';

interface AIResponse {
  service: string;
  success: boolean;
  content?: string;
  synopsis?: string;
  error?: string;
}

interface WebSearchSource {
  title: string;
  url: string;
  source?: string;
  published_date?: string;
  snippet?: string;
}

const AIConsensusComplete: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [responses, setResponses] = useState<AIResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedServices, setSelectedServices] = useState(['claude', 'gemini']);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [expandedResponses, setExpandedResponses] = useState<Set<number>>(new Set());
  const [selectedForCritique, setSelectedForCritique] = useState<Set<number>>(new Set());
  const [critiqueResult, setCritiqueResult] = useState<string | null>(null);
  const [loadingCritique, setLoadingCritique] = useState(false);
  const [webSearchSources, setWebSearchSources] = useState<WebSearchSource[]>([]);

  // Chat history sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);

  // Conversation tracking for chat history
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<Array<{role: string, content: string}>>([]);

  const services = [
    { id: 'claude', name: 'Claude', color: '#FF6B35' },
    { id: 'openai', name: 'OpenAI', color: '#00A67E' },
    { id: 'gemini', name: 'Gemini', color: '#4285F4' }
  ];

  const toggleService = (serviceId: string) => {
    setSelectedServices(prev =>
      prev.includes(serviceId)
        ? prev.filter(id => id !== serviceId)
        : [...prev, serviceId]
    );
  };

  const sendQuestion = async () => {
    if (!question.trim() || selectedServices.length === 0) {
      alert('Please enter a question and select at least one AI service');
      return;
    }

    const currentQuestion = question;
    setLoading(true);
    setResponses([]);
    setCritiqueResult(null);
    setSelectedForCritique(new Set());
    setQuestion(''); // Clear input immediately

    // Add user message to conversation history
    setConversationHistory(prev => [...prev, { role: 'user', content: currentQuestion }]);

    try {
      // Build chat history string for API
      const chatHistoryString = [...conversationHistory, { role: 'user', content: currentQuestion }]
        .map(msg => `${msg.role}: ${msg.content}`).join('\n');

      const response = await fetch('http://localhost:8000/api/v1/test-ai/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: currentQuestion,
          services: selectedServices,
          use_web_search: webSearchEnabled,
          chat_history: chatHistoryString
        })
      });

      const data = await response.json();

      if (data.success) {
        setResponses(data.results);
        setWebSearchSources(data.web_search_sources || []);

        // Add AI responses to conversation history - individual responses for each service
        if (data.results && data.results.length > 0) {
          const successfulResults = data.results.filter((r: any) => r.success);
          let updatedHistory = [...conversationHistory, { role: 'user', content: currentQuestion }];
          successfulResults.forEach((result: any) => {
            updatedHistory = [...updatedHistory, { role: result.service, content: result.content }];
          });
          setConversationHistory(updatedHistory);
        }
      } else {
        console.error('API Error:', data.error);
        alert('Error: ' + data.error);
      }
    } catch (error) {
      console.error('Network error:', error);
      alert('Network error: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpanded = (index: number) => {
    setExpandedResponses(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const toggleCritiqueSelection = (index: number) => {
    setSelectedForCritique(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const performCritique = async () => {
    if (selectedForCritique.size !== 2) {
      alert('Please select exactly 2 responses for comparison');
      return;
    }

    const selectedIndices = Array.from(selectedForCritique);
    const response1 = responses[selectedIndices[0]];
    const response2 = responses[selectedIndices[1]];

    setLoadingCritique(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/critique/compare/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_query: question,
          llm1_name: response1.service,
          llm1_response: response1.content,
          llm2_name: response2.service,
          llm2_response: response2.content,
          chat_history: ''
        })
      });

      const data = await response.json();

      if (data.success) {
        setCritiqueResult(data.critique);
      } else {
        alert('Critique failed: ' + data.error);
      }
    } catch (error) {
      console.error('Critique error:', error);
      alert('Critique error: ' + error);
    } finally {
      setLoadingCritique(false);
    }
  };

  const preferResponse = (index: number) => {
    // Keep only the preferred response
    setResponses([responses[index]]);
    setExpandedResponses(new Set([0]));
    setSelectedForCritique(new Set());
    setCritiqueResult(null);
  };

  const handleNewConversation = async () => {
    try {
      const newConversation = await apiService.createConversation({
        title: 'New Chat',
        agent_mode: 'standard',
      });
      setSelectedConversation(newConversation);
      setSidebarOpen(false);
      // Reset state for new conversation
      setQuestion('');
      setResponses([]);
      setCritiqueResult(null);
      setSelectedForCritique(new Set());
    } catch (err) {
      console.error('Error creating new conversation:', err);
    }
  };

  const handleConversationSelect = (conversation: Conversation) => {
    setSelectedConversation(conversation);
    setSidebarOpen(false);
    // Reset state when selecting conversation
    setQuestion('');
    setResponses([]);
    setCritiqueResult(null);
    setSelectedForCritique(new Set());
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Chat History Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-50 w-80 transform transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } bg-white shadow-lg border-r border-gray-200`}
      >
        <div className="flex flex-col h-full">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors ml-auto"
              >
                <X size={20} />
              </button>
            </div>
            <button
              onClick={handleNewConversation}
              className="w-full flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
            >
              <Plus size={16} />
              New Chat
            </button>
          </div>
          <div className="flex-1 overflow-hidden">
            <ConversationHistory
              currentConversationId={selectedConversation?.id}
              onConversationSelect={handleConversationSelect}
              onNewConversation={handleNewConversation}
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
      <div className="max-w-5xl mx-auto px-8 py-8">
        {/* Header - Exactly like PNG */}
        <div className="flex items-center justify-between mb-12">
          <div className="flex items-center gap-3">
            {/* Hidden hamburger menu - only show if needed */}
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-1 hover:bg-gray-100 rounded transition-colors opacity-30 hover:opacity-100"
              title="Chat History"
            >
              <Menu size={16} />
            </button>
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              💬
            </div>
            <h1 className="text-2xl font-bold text-gray-900">AI Consensus</h1>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">Select AI Services:</span>
            <div className="flex gap-2">
              {services.map(service => {
                const isSelected = selectedServices.includes(service.id);
                return (
                  <button
                    key={service.id}
                    onClick={() => toggleService(service.id)}
                    className="px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 border-2 bg-white text-gray-700 border-gray-300 hover:border-gray-400"
                  >
                    {service.name}
                    {isSelected && (
                      <span className="w-4 h-4 bg-green-500 text-white rounded-full text-xs flex items-center justify-center font-bold">
                        ✓
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>



        {/* Complete Chat History */}
        {conversationHistory.length > 0 && (
          <div className="max-w-4xl mx-auto mb-8 space-y-6">
            {conversationHistory.map((message, index) => {
              if (message.role === 'user') {
                return (
                  <div key={index} className="flex justify-center">
                    <div className="rounded-2xl px-6 py-4 max-w-3xl bg-blue-500 text-white">
                      <div className="text-xs opacity-70 mb-1">You</div>
                      <div>{message.content}</div>
                    </div>
                  </div>
                );
              } else {
                // AI service response in history
                return (
                  <div key={index} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                    <div className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-medium text-gray-900">{message.role}</h3>
                          <div className="flex items-center gap-1 text-sm text-gray-600">
                            <span className="text-green-500">✓</span>
                            <span>Completed</span>
                          </div>
                        </div>
                      </div>
                      <div className="text-gray-800 leading-relaxed">
                        <MarkdownRenderer content={message.content || ''} webSearchSources={webSearchSources} />
                      </div>
                    </div>
                  </div>
                );
              }
            })}
          </div>
        )}

        {/* Current Loading Responses (only shown while loading) */}
        {responses.length > 0 && loading && (
          <div className="space-y-6 max-w-4xl mx-auto">
            {responses.map((response, index) => (
              <div key={index} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-medium text-gray-900">{response.service}</h3>
                      {response.success && (
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <span className="text-green-500">✓</span>
                          <span>Completed</span>
                        </div>
                      )}
                    </div>

                    {response.success && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => toggleExpanded(index)}
                          className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors"
                        >
                          {expandedResponses.has(index) ? '-Collapse' : '+Expand'}
                        </button>
                        <button
                          onClick={() => toggleCritiqueSelection(index)}
                          className={`px-3 py-1 text-sm border rounded transition-colors ${
                            selectedForCritique.has(index)
                              ? 'bg-gray-100 border-gray-400 text-gray-700'
                              : 'border-gray-300 hover:bg-gray-50 text-gray-700'
                          }`}
                        >
                          Select for AI Critic
                        </button>
                        <button
                          onClick={() => preferResponse(index)}
                          className="px-3 py-1 text-sm bg-gray-100 text-blue-600 border border-gray-300 rounded hover:bg-gray-200 transition-colors"
                        >
                          Preferred This
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Response Content */}
                  <div className="text-gray-800 leading-relaxed">
                    {response.success ? (
                      expandedResponses.has(index) ? (
                        <MarkdownRenderer content={response.content || ''} webSearchSources={webSearchSources} />
                      ) : (
                        <MarkdownRenderer content={response.synopsis || (response.content?.substring(0, 200) + '...')} webSearchSources={webSearchSources} />
                      )
                    ) : (
                      <div className="text-red-600">Error: {response.error}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* AI Critique Section */}
        {selectedForCritique.size > 0 && (
          <div className="mt-6 bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-purple-900">
                AI Critique & Comparison ({selectedForCritique.size}/2 selected)
              </h3>
              {selectedForCritique.size === 2 && (
                <button
                  onClick={performCritique}
                  disabled={loadingCritique}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400 transition-colors font-medium"
                >
                  {loadingCritique ? 'Analyzing...' : '🗨️ Critique Selected Responses'}
                </button>
              )}
            </div>

            {selectedForCritique.size < 2 && (
              <p className="text-purple-700 text-sm">Select 2 responses to get AI-powered comparative analysis</p>
            )}
          </div>
        )}

        {/* Critique Result */}
        {critiqueResult && (
          <div className="mt-6 bg-purple-50 border border-purple-200 rounded-lg p-6">
            <h3 className="font-semibold text-purple-900 mb-3">AI Critique & Analysis</h3>
            <MarkdownRenderer content={critiqueResult} className="text-gray-700" />
          </div>
        )}

        {/* Loading State - Exactly like PNG */}
        {loading && (
          <div className="space-y-6 max-w-4xl mx-auto mb-20">
            {selectedServices.map((serviceId, index) => {
              const service = services.find(s => s.id === serviceId);
              return (
                <div key={index} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-medium text-gray-900">{service?.name}</h3>
                        <div className="flex items-center gap-1 text-sm text-gray-600">
                          <span className="animate-pulse text-blue-500">⏳</span>
                          <span>Thinking...</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-gray-600">Generating response...</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Welcome State */}
        {!loading && conversationHistory.length === 0 && (
          <div className="text-center py-16 mb-20">
            <div className="text-6xl mb-4">🤖</div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Welcome to AI Consensus</h2>
            <p className="text-gray-600 text-lg mb-6">
              Get informed answers by comparing responses from multiple AI services simultaneously
            </p>
            <div className="text-sm text-gray-500 space-y-2">
              <p>✨ Select multiple AI services for comparison</p>
              <p>🌐 Enable web search for current information</p>
              <p>🔍 Use AI Critique to compare responses</p>
              <p>💬 Access chat history from the sidebar</p>
            </div>
          </div>
        )}

        {/* Bottom Input Section - Exactly like PNG */}
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-end gap-3">
              {/* Web Search Toggle (subtle) */}
              <button
                onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                className={`p-2 rounded-lg transition-all ${
                  webSearchEnabled
                    ? 'bg-green-100 text-green-600'
                    : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                }`}
                title={webSearchEnabled ? 'Web search enabled' : 'Click to enable web search'}
              >
                <Globe size={18} />
              </button>

              {/* Question Input */}
              <div className="flex-1">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask a question to multiple AI services..."
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                  rows={1}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      if (!loading && question.trim() && selectedServices.length > 0) {
                        sendQuestion();
                      }
                    }
                  }}
                />
              </div>

              {/* Send Button */}
              <button
                onClick={sendQuestion}
                disabled={loading || !question.trim() || selectedServices.length === 0}
                className="bg-blue-500 text-white px-4 py-3 rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <span>{loading ? 'Thinking...' : 'Send'}</span>
              </button>
            </div>

            {/* Status line */}
            <div className="mt-2 text-xs text-gray-500 text-center">
              Press Enter to send • {selectedServices.length} AI service{selectedServices.length !== 1 ? 's' : ''} selected
              {webSearchEnabled && ' • Web search enabled'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIConsensusComplete;