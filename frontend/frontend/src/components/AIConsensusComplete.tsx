import React, { useState, useRef, useEffect } from 'react';
import { X, Menu, Globe, Copy, Check, Star, LogOut, Settings } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';
import ConversationHistory from './ConversationHistory';
import AccountSettings from './AccountSettings';
import ModelSelectionModal from './ModelSelectionModal';
import { apiService, Conversation, ConversationDetail } from '../services/api';

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

// Helper function to get headers with both CSRF and Authorization tokens
const getAuthHeaders = (): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Add CSRF token
  const csrfToken = getCsrfToken();
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }

  // Add Authorization token (DRF TokenAuthentication format)
  const authToken = localStorage.getItem('auth_token');
  if (authToken) {
    headers['Authorization'] = `Token ${authToken}`;
  }

  return headers;
};

const AIConsensusComplete: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [responses, setResponses] = useState<AIResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchingInternet, setSearchingInternet] = useState(false);
  const [selectedServices, setSelectedServices] = useState(['claude', 'gemini']);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [userLocation, setUserLocation] = useState<{city?: string; region?: string; country?: string; timezone?: string} | null>(null);
  const [expandedResponses, setExpandedResponses] = useState<Set<number>>(new Set());
  const [selectedForCritique, setSelectedForCritique] = useState<Set<number>>(new Set());
  const [preferredResponses, setPreferredResponses] = useState<Set<number>>(new Set());
  const [critiqueResult, setCritiqueResult] = useState<string | null>(null);
  const [critiqueProvider, setCritiqueProvider] = useState<string | null>(null);
  const [loadingCritique, setLoadingCritique] = useState(false);
  const [webSearchSources, setWebSearchSources] = useState<WebSearchSource[]>([]);

  // Chat history sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [showAccountSettings, setShowAccountSettings] = useState(false);
  const [showModelSelection, setShowModelSelection] = useState(false);

  // Textarea ref for height reset
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Ref to prevent duplicate conversation creation in StrictMode
  const conversationInitialized = useRef(false);
  const isSendingRef = useRef(false);

  // Conversation tracking for chat history
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [currentConversation, setCurrentConversation] = useState<ConversationDetail | null>(null);
  const [conversationHistory, setConversationHistory] = useState<Array<{role: string, content: string}>>([]);
  const [conversationRefreshTrigger, setConversationRefreshTrigger] = useState(0);

  // Keep track of all conversation exchanges (question + responses + analysis results)
  const [conversationExchanges, setConversationExchanges] = useState<Array<{
    question: string;
    responses: AIResponse[];
    webSearchSources: WebSearchSource[];
    critiqueResult?: string;
    critiqueProvider?: string;
    synthesisResult?: string;
    synthesisProvider?: string;
  }>>([]);

  // Track expanded states for previous exchanges (collapsed by default)
  const [previousExchangesExpanded, setPreviousExchangesExpanded] = useState<{[key: string]: Set<number>}>({});
  const [previousExchangesSelected, setPreviousExchangesSelected] = useState<{[key: string]: Set<number>}>({});
  const [previousExchangesPreferred, setPreviousExchangesPreferred] = useState<{[key: string]: Set<number>}>({});
  const [exchangesCollapsed, setExchangesCollapsed] = useState<Set<number>>(new Set());
  const [previousCritiqueResults, setPreviousCritiqueResults] = useState<{[key: string]: string}>({});
  const [previousCritiqueProviders, setPreviousCritiqueProviders] = useState<{[key: string]: string}>({});
  const [loadingPreviousCritique, setLoadingPreviousCritique] = useState<{[key: string]: boolean}>({});

  // Synthesis/Combine state
  const [synthesisResult, setSynthesisResult] = useState<string | null>(null);
  const [synthesisProvider, setSynthesisProvider] = useState<string | null>(null);
  const [loadingSynthesis, setLoadingSynthesis] = useState(false);
  const [previousSynthesisResults, setPreviousSynthesisResults] = useState<{[key: string]: string}>({});
  const [previousSynthesisProviders, setPreviousSynthesisProviders] = useState<{[key: string]: string}>({});
  const [loadingPreviousSynthesis, setLoadingPreviousSynthesis] = useState<{[key: string]: boolean}>({});

  // Cross-Reflection state
  const [crossReflectionResults, setCrossReflectionResults] = useState<AIResponse[]>([]);
  const [loadingCrossReflection, setLoadingCrossReflection] = useState(false);
  const [previousCrossReflectionResults, setPreviousCrossReflectionResults] = useState<{[key: string]: AIResponse[]}>({});
  const [loadingPreviousCrossReflection, setLoadingPreviousCrossReflection] = useState<{[key: string]: boolean}>({});
  const [expandedCrossReflections, setExpandedCrossReflections] = useState<Set<number>>(new Set());
  const [previousExpandedCrossReflections, setPreviousExpandedCrossReflections] = useState<{[key: string]: Set<number>}>({});
  const [preferredCrossReflections, setPreferredCrossReflections] = useState<Set<number>>(new Set());
  const [previousPreferredCrossReflections, setPreviousPreferredCrossReflections] = useState<{[key: string]: Set<number>}>({});

  // Expand/Collapse state for analysis results
  const [critiqueExpanded, setCritiqueExpanded] = useState(true);
  const [synthesisExpanded, setSynthesisExpanded] = useState(true);
  const [crossReflectionExpanded, setCrossReflectionExpanded] = useState(true);
  const [previousCritiqueExpanded, setPreviousCritiqueExpanded] = useState<{[key: string]: boolean}>({});
  const [previousSynthesisExpanded, setPreviousSynthesisExpanded] = useState<{[key: string]: boolean}>({});
  const [previousCrossReflectionExpanded, setPreviousCrossReflectionExpanded] = useState<{[key: string]: boolean}>({});

  // Copy state tracking
  const [copiedItems, setCopiedItems] = useState<{[key: string]: boolean}>({});

  // Initialize conversation on component mount
  useEffect(() => {
    // Prevent duplicate initialization in React StrictMode
    if (conversationInitialized.current) return;
    conversationInitialized.current = true;

    const initializeConversation = async () => {
      try {
        // Ensure CSRF token is available before making POST requests
        await apiService.ensureCsrfToken();

        const newConversation = await apiService.createConversation({
          title: 'New AIX Chat',
          agent_mode: 'standard'
        });
        setCurrentConversationId(newConversation.id);
        setCurrentConversation(newConversation);
        // Trigger conversation history refresh
        setConversationRefreshTrigger(prev => prev + 1);
        console.log('Created new conversation:', newConversation.id);
      } catch (error) {
        console.error('Failed to create conversation:', error);
        // Continue without persistence if API fails
      }
    };

    initializeConversation();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle conversation selection from sidebar
  const handleConversationSelect = async (conversation: Conversation) => {
    try {
      // Load the full conversation details
      const fullConversation = await apiService.getConversation(conversation.id);
      setCurrentConversationId(conversation.id);
      setCurrentConversation(fullConversation);
      setSelectedConversation(conversation);

      // Load conversation history from messages and reconstruct exchanges
      if (fullConversation.messages && fullConversation.messages.length > 0) {
        const history = fullConversation.messages.map(msg => ({
          role: msg.role,
          content: msg.content
        }));
        setConversationHistory(history);

        // Reconstruct conversationExchanges from messages
        const exchanges: Array<{
          question: string;
          responses: AIResponse[];
          webSearchSources: WebSearchSource[];
          critiqueResult?: string;
          critiqueProvider?: string;
          synthesisResult?: string;
          synthesisProvider?: string;
        }> = [];

        let currentExchange: {
          question: string;
          responses: AIResponse[];
          webSearchSources: WebSearchSource[];
        } | null = null;

        for (const msg of fullConversation.messages) {
          if (msg.role === 'user') {
            // Save previous exchange if it has responses
            if (currentExchange && currentExchange.responses.length > 0) {
              exchanges.push(currentExchange);
            }
            // Start a new exchange
            currentExchange = {
              question: msg.content,
              responses: [],
              webSearchSources: []
            };
          } else if (msg.role === 'assistant' && currentExchange) {
            // Add assistant response to the current exchange
            const metadata = msg.metadata || {};
            const service = metadata.service || 'Unknown';

            // Check if this service response already exists to avoid duplicates
            const existingResponse = currentExchange.responses.find(r => r.service === service);
            if (!existingResponse) {
              currentExchange.responses.push({
                service: service,
                content: msg.content,
                success: true,
                synopsis: metadata.synopsis || ''
              });

              // Extract web search sources if available
              if (metadata.web_search_sources && metadata.web_search_sources.length > 0) {
                currentExchange.webSearchSources = metadata.web_search_sources;
              }
            }
          }
        }

        // Add the final exchange if it has responses
        if (currentExchange && currentExchange.responses.length > 0) {
          exchanges.push(currentExchange);
        }

        setConversationExchanges(exchanges);

        // Clear the question input
        setQuestion('');
      } else {
        setConversationHistory([]);
        setConversationExchanges([]);
      }

      // Clear current UI state
      setResponses([]);
      setCritiqueResult(null);
      setExpandedResponses(new Set());
      setSelectedForCritique(new Set());
      setPreferredResponses(new Set());

      // Close sidebar on mobile
      setSidebarOpen(false);
      console.log('Loaded conversation:', conversation.id);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  // Handle creating new conversation
  const handleNewConversation = async () => {
    try {
      const newConversation = await apiService.createConversation({
        title: 'New AIX Chat',
        agent_mode: 'standard'
      });
      setCurrentConversationId(newConversation.id);
      setCurrentConversation(newConversation);
      setSelectedConversation(null);

      // Clear all state for fresh conversation
      setConversationHistory([]);
      setResponses([]);
      setConversationExchanges([]);
      setCritiqueResult(null);
      setCritiqueProvider(null);
      setSynthesisResult(null);
      setSynthesisProvider(null);
      setExpandedResponses(new Set());
      setSelectedForCritique(new Set());
      setPreferredResponses(new Set());
      setPreviousExchangesExpanded({});
      setPreviousExchangesSelected({});
      setPreviousExchangesPreferred({});
      setCritiqueExpanded(true);
      setSynthesisExpanded(true);
      setCrossReflectionExpanded(true);
      setPreviousCritiqueResults({});
      setPreviousCritiqueProviders({});
      setLoadingPreviousCritique({});
      setPreviousCritiqueExpanded({});
      setPreviousSynthesisResults({});
      setPreviousSynthesisProviders({});
      setLoadingPreviousSynthesis({});
      setPreviousSynthesisExpanded({});
      setCrossReflectionResults([]);
      setLoadingCrossReflection(false);
      setPreviousCrossReflectionResults({});
      setLoadingPreviousCrossReflection({});
      setExpandedCrossReflections(new Set());
      setPreviousExpandedCrossReflections({});
      setPreferredCrossReflections(new Set());
      setPreviousPreferredCrossReflections({});

      // Close sidebar
      setSidebarOpen(false);
      // Trigger conversation history refresh
      setConversationRefreshTrigger(prev => prev + 1);
      console.log('Created new conversation:', newConversation.id);
    } catch (error) {
      console.error('Failed to create new conversation:', error);
    }
  };

  // Helper function to save a message to the database
  const saveMessage = async (role: 'user' | 'assistant' | 'system', content: string, metadata: any = {}): Promise<boolean> => {
    if (!currentConversationId) return false;

    try {
      // Using direct fetch since we don't have a messages endpoint in apiService yet
      const headers = getAuthHeaders();

      const response = await fetch(`http://localhost:8000/api/v1/conversations/${currentConversationId}/messages/`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          role,
          content,
          metadata,
          tokens_used: Math.ceil(content.length / 4) // Rough token estimate
        })
      });
      return response.ok;
    } catch (error) {
      console.error('Failed to save message:', error);
      return false;
    }
  };

  // Helper function to update conversation title based on first message
  const updateConversationTitle = async (message: string) => {
    if (!currentConversationId || !currentConversation || currentConversation.total_messages > 0) return;

    try {
      const title = message.length > 50 ? message.substring(0, 50) + '...' : message;
      await apiService.updateConversation(currentConversationId, { title });
      setCurrentConversation(prev => prev ? { ...prev, title } : null);
    } catch (error) {
      console.error('Failed to update conversation title:', error);
    }
  };

  // Function to get user's geolocation from browser
  const getUserLocation = async (): Promise<{city?: string; region?: string; country?: string; timezone?: string} | null> => {
    try {
      // Get timezone from browser
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

      // Try to infer country from browser locale/region settings
      let country: string | undefined;

      // Method 1: Try to get from navigator.language (e.g., "en-US" -> "US")
      if (navigator.language) {
        const parts = navigator.language.split('-');
        if (parts.length === 2 && parts[1].length === 2) {
          country = parts[1].toUpperCase();
          console.log(`Inferred country code from browser language: ${country}`);
        }
      }

      // Method 2: Try to infer from timezone if country not found
      if (!country && timezone) {
        // Map common timezones to country codes
        const timezoneToCountry: {[key: string]: string} = {
          'America/New_York': 'US',
          'America/Los_Angeles': 'US',
          'America/Chicago': 'US',
          'America/Denver': 'US',
          'America/Toronto': 'CA',
          'America/Vancouver': 'CA',
          'Europe/London': 'GB',
          'Europe/Paris': 'FR',
          'Europe/Berlin': 'DE',
          'Europe/Rome': 'IT',
          'Europe/Madrid': 'ES',
          'Asia/Tokyo': 'JP',
          'Asia/Shanghai': 'CN',
          'Asia/Hong_Kong': 'HK',
          'Asia/Singapore': 'SG',
          'Australia/Sydney': 'AU',
          'Australia/Melbourne': 'AU',
        };

        country = timezoneToCountry[timezone];
        if (country) {
          console.log(`Inferred country code from timezone: ${country}`);
        }
      }

      // Validate country code format (must be exactly 2 uppercase letters)
      if (country && (country.length !== 2 || !/^[A-Z]{2}$/.test(country))) {
        console.warn(`Invalid country code format: ${country}, removing location data`);
        country = undefined;
      }

      // Only return location data if we have a valid country code
      if (country) {
        return {
          country,
          timezone
        };
      } else {
        console.log('No valid country code could be determined from browser');
        return null;
      }
    } catch (error) {
      console.error('Error getting location from browser:', error);
      return null;
    }
  };

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
    if (isSendingRef.current) {
      return;
    }

    if (!question.trim() || selectedServices.length === 0) {
      alert('Please enter a question and select at least one AI service');
      return;
    }

    isSendingRef.current = true;
    setLoading(true);
    const currentQuestion = question;

    // Archive current responses as a conversation exchange if we have any
    if (responses?.length > 0 && conversationHistory?.length > 0) {
      // Find the last user message in the conversation history
      const lastUserMessage = conversationHistory?.filter(msg => msg.role === 'user').slice(-1)[0];
      const newExchangeIndex = conversationExchanges?.length || 0;

      // Archive the responses along with any analysis results
      setConversationExchanges(prev => [...prev, {
        question: lastUserMessage?.content || 'Previous question',
        responses: responses,
        webSearchSources: webSearchSources,
        critiqueResult: critiqueResult || undefined,
        critiqueProvider: critiqueProvider || undefined,
        synthesisResult: synthesisResult || undefined,
        synthesisProvider: synthesisProvider || undefined,
      }]);

      // Save current cross-reflection results to previous results for the new exchange index
      if (crossReflectionResults?.length > 0) {
        setPreviousCrossReflectionResults(prev => ({...prev, [`${newExchangeIndex}`]: crossReflectionResults}));
      }

      // Auto-collapse the new exchange by default
      setExchangesCollapsed(prev => {
        const newSet = new Set(prev);
        newSet.add(newExchangeIndex);
        return newSet;
      });
    }

    setResponses([]); // Clear current responses for new query
    setCritiqueResult(null);
    setCritiqueProvider(null);
    setSynthesisResult(null);
    setSynthesisProvider(null);
    setCrossReflectionResults([]); // Clear current cross-reflection results
    setSelectedForCritique(new Set());
    setPreferredResponses(new Set());
    setPreferredCrossReflections(new Set());
    setExpandedResponses(new Set());
    setExpandedCrossReflections(new Set());
    setQuestion(''); // Clear input immediately

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = '48px'; // Reset to min height
    }

    try {
      // Save user message to database and add to conversation history
      await saveMessage('user', currentQuestion);
      await updateConversationTitle(currentQuestion);
      setConversationHistory(prev => [...prev, { role: 'user', content: currentQuestion }]);

      // Trigger conversation list refresh after first message (so it appears in sidebar)
      if (conversationHistory?.length === 0) {
        setConversationRefreshTrigger(prev => prev + 1);
      }

      // Get user location if web search is enabled
      let locationData = null;
      if (webSearchEnabled) {
        setSearchingInternet(true);
        console.log('[FRONTEND] Web search is enabled, getting location...');
        locationData = await getUserLocation();
        if (locationData) {
          setUserLocation(locationData);
          console.log('[FRONTEND] Location data:', locationData);
        }
      } else {
        console.log('[FRONTEND] Web search is NOT enabled');
      }

      // Build chat history string for API
      const chatHistoryString = conversationHistory.map(msg => `${msg.role}: ${msg.content}`).join('\n');

      const requestBody = {
        message: currentQuestion,
        services: selectedServices,
        use_web_search: webSearchEnabled,
        user_location: locationData,
        chat_history: chatHistoryString,
        conversation_id: currentConversationId
      };

      console.log('[FRONTEND] Sending request to backend:', {
        ...requestBody,
        message: requestBody.message.substring(0, 50) + '...',
        chat_history: requestBody.chat_history ? 'present' : 'empty'
      });

      const headers = getAuthHeaders();
      const csrfToken = getCsrfToken();
      console.log('[FRONTEND] CSRF Token:', csrfToken ? 'found' : 'NOT FOUND');
      console.log('[FRONTEND] All cookies:', document.cookie);

      // Keep searchingInternet true if web search is enabled (backend will do web search first)
      // Otherwise, show AI thinking indicator with loading state
      // If webSearchEnabled is true, searchingInternet is already true from above

      const response = await fetch('http://localhost:8000/api/v1/consensus/', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();

      if (data.success) {
        console.log('[FRONTEND] Received web_search_sources:', data.web_search_sources);
        setResponses(data.results);
        setWebSearchSources(data.web_search_sources || []);

        // Save AI responses to database and add to conversation history
        if (data.results && data.results.length > 0) {
          const successfulResults = data.results.filter((r: any) => r.success);

          // Save each AI response to the database
          let savedSuccessfully = false;
          for (const result of successfulResults) {
            const saved = await saveMessage('assistant', result.content, {
              service: result.service,
              synopsis: result.synopsis,
              web_search_sources: webSearchEnabled ? data.web_search_sources : undefined
            });
            if (saved) savedSuccessfully = true;
          }

          const newResponses = successfulResults.map((result: any) => ({ role: result.service, content: result.content }));
          setConversationHistory(prev => [...prev, ...newResponses]);

          // Refresh conversation list after saving messages
          if (savedSuccessfully) {
            setConversationRefreshTrigger(prev => prev + 1);
          }
        }
      } else {
        console.error('API Error:', data.error);
        alert('Error: ' + (data.error || 'An unexpected error occurred. Please try again.'));
      }
    } catch (error) {
      console.error('Network error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Network connection failed. Please check your connection and try again.';
      alert('Network error: ' + errorMessage);
    } finally {
      isSendingRef.current = false;
      setSearchingInternet(false);
      setLoading(false);
    }
  };

  const toggleExpanded = (index: number) => {
    setExpandedResponses(prev => {
      const newSet = new Set<number>();
      // If clicking the same one that's expanded, collapse it
      if (!prev.has(index)) {
        newSet.add(index);
      }
      // Otherwise, only expand the clicked one (collapse others)
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
      console.log('[CRITIQUE DEBUG] currentConversationId:', currentConversationId);
      console.log('[CRITIQUE DEBUG] selectedConversation?.id:', selectedConversation?.id);

      const requestBody = {
        user_query: conversationHistory.filter(msg => msg.role === 'user').slice(-1)[0]?.content || question,
        llm1_name: response1.service,
        llm1_response: response1.content,
        llm2_name: response2.service,
        llm2_response: response2.content,
        chat_history: '',
        conversation_id: currentConversationId
      };

      console.log('[CRITIQUE DEBUG] Request body:', JSON.stringify(requestBody, null, 2));

      const headers = getAuthHeaders();

      const response = await fetch('http://localhost:8000/api/v1/consensus/critique/', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();

      if (data.success) {
        setCritiqueResult(data.critique);
        setCritiqueProvider(data.critique_provider || 'Unknown');
        // Refresh conversation list to show updated costs
        setConversationRefreshTrigger(prev => prev + 1);
      } else {
        alert('Critique failed: ' + (data.error || 'Unable to generate critique. Please try again.'));
      }
    } catch (error) {
      console.error('Critique error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate critique. Please try again.';
      alert('Critique error: ' + errorMessage);
    } finally {
      setLoadingCritique(false);
    }
  };

  const performSynthesis = async () => {
    if (selectedForCritique.size !== 2) {
      alert('Please select exactly 2 responses to combine');
      return;
    }

    const selectedIndices = Array.from(selectedForCritique);
    const response1 = responses[selectedIndices[0]];
    const response2 = responses[selectedIndices[1]];

    setLoadingSynthesis(true);

    try {
      const headers = getAuthHeaders();

      const response = await fetch('http://localhost:8000/api/v1/consensus/synthesis/', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          user_query: conversationHistory.filter(msg => msg.role === 'user').slice(-1)[0]?.content || question,
          llm1_name: response1.service,
          llm1_response: response1.content,
          llm2_name: response2.service,
          llm2_response: response2.content,
          chat_history: '',
          conversation_id: currentConversationId
        })
      });

      const data = await response.json();

      if (data.success) {
        setSynthesisResult(data.synthesis);
        setSynthesisProvider(data.synthesis_provider || 'Unknown');
        // Refresh conversation list to show updated costs
        setConversationRefreshTrigger(prev => prev + 1);
      } else {
        alert('Synthesis failed: ' + (data.error || 'Unable to generate synthesis. Please try again.'));
      }
    } catch (error) {
      console.error('Synthesis error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate synthesis. Please try again.';
      alert('Synthesis error: ' + errorMessage);
    } finally {
      setLoadingSynthesis(false);
    }
  };

  const performCrossReflection = async () => {
    if (selectedForCritique.size !== 2) {
      alert('Please select exactly 2 responses for cross-reflection');
      return;
    }

    const selectedIndices = Array.from(selectedForCritique);
    const response1 = responses[selectedIndices[0]];
    const response2 = responses[selectedIndices[1]];

    setLoadingCrossReflection(true);

    try {
      const headers = getAuthHeaders();

      const response = await fetch('http://localhost:8000/api/v1/consensus/cross-reflect/', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          user_query: conversationHistory.filter(msg => msg.role === 'user').slice(-1)[0]?.content || question,
          llm1_name: response1.service,
          llm1_response: response1.content,
          llm2_name: response2.service,
          llm2_response: response2.content,
          chat_history: '',
          conversation_id: currentConversationId
        })
      });

      const data = await response.json();

      if (data.success && data.reflections) {
        // Store reflections as AIResponse objects
        const reflections: AIResponse[] = data.reflections.map((reflection: any) => ({
          service: `${reflection.service} (reflecting on ${reflection.reflecting_on})`,
          success: true,
          content: reflection.content,
          synopsis: reflection.synopsis
        }));
        setCrossReflectionResults(reflections);

        // Save cross-reflection results to conversation history
        for (const reflection of reflections) {
          if (reflection.content) {
            await saveMessage('assistant', reflection.content, { service: reflection.service, type: 'cross-reflection' });
            setConversationHistory(prev => [...prev, { role: reflection.service, content: reflection.content || '' }]);
          }
        }

        // Refresh conversation list after saving
        setConversationRefreshTrigger(prev => prev + 1);
      } else {
        alert('Cross-reflection failed: ' + (data.error || 'Unable to generate cross-reflection. Please try again.'));
      }
    } catch (error) {
      console.error('Cross-reflection error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate cross-reflection. Please try again.';
      alert('Cross-reflection error: ' + errorMessage);
    } finally {
      setLoadingCrossReflection(false);
    }
  };

  const performPreviousCritique = async (exchangeIndex: number, exchange: any) => {
    const exchangeKey = `${exchangeIndex}`;
    const selectedSet = previousExchangesSelected[exchangeKey] || new Set();

    if (selectedSet.size !== 2) {
      alert('Please select exactly 2 responses for comparison');
      return;
    }

    const selectedIndices = Array.from(selectedSet);
    const response1 = exchange.responses[selectedIndices[0]];
    const response2 = exchange.responses[selectedIndices[1]];

    setLoadingPreviousCritique(prev => ({...prev, [exchangeKey]: true}));

    try {
      const headers = getAuthHeaders();

      const response = await fetch('http://localhost:8000/api/v1/consensus/critique/', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          user_query: exchange.question,
          llm1_name: response1.service,
          llm1_response: response1.content,
          llm2_name: response2.service,
          llm2_response: response2.content,
          chat_history: '',
          conversation_id: currentConversationId
        })
      });

      const data = await response.json();

      if (data.success) {
        setPreviousCritiqueResults(prev => ({...prev, [exchangeKey]: data.critique}));
        setPreviousCritiqueProviders(prev => ({...prev, [exchangeKey]: data.critique_provider || 'Unknown'}));
        setPreviousCritiqueExpanded(prev => ({...prev, [exchangeKey]: true})); // Default to expanded
        // Refresh conversation list to show updated costs
        setConversationRefreshTrigger(prev => prev + 1);
      } else {
        alert('Critique failed: ' + (data.error || 'Unable to generate critique. Please try again.'));
      }
    } catch (error) {
      console.error('Critique error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate critique. Please try again.';
      alert('Critique error: ' + errorMessage);
    } finally {
      setLoadingPreviousCritique(prev => ({...prev, [exchangeKey]: false}));
    }
  };

  const performPreviousSynthesis = async (exchangeIndex: number, exchange: any) => {
    const exchangeKey = `${exchangeIndex}`;
    const selectedSet = previousExchangesSelected[exchangeKey] || new Set();

    if (selectedSet.size !== 2) {
      alert('Please select exactly 2 responses to combine');
      return;
    }

    const selectedIndices = Array.from(selectedSet);
    const response1 = exchange.responses[selectedIndices[0]];
    const response2 = exchange.responses[selectedIndices[1]];

    setLoadingPreviousSynthesis(prev => ({...prev, [exchangeKey]: true}));

    try {
      const headers = getAuthHeaders();

      const response = await fetch('http://localhost:8000/api/v1/consensus/synthesis/', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          user_query: exchange.question,
          llm1_name: response1.service,
          llm1_response: response1.content,
          llm2_name: response2.service,
          llm2_response: response2.content,
          chat_history: '',
          conversation_id: currentConversationId
        })
      });

      const data = await response.json();

      if (data.success) {
        setPreviousSynthesisResults(prev => ({...prev, [exchangeKey]: data.synthesis}));
        setPreviousSynthesisProviders(prev => ({...prev, [exchangeKey]: data.synthesis_provider || 'Unknown'}));
        setPreviousSynthesisExpanded(prev => ({...prev, [exchangeKey]: true})); // Default to expanded
        // Refresh conversation list to show updated costs
        setConversationRefreshTrigger(prev => prev + 1);
      } else {
        alert('Synthesis failed: ' + (data.error || 'Unable to generate synthesis. Please try again.'));
      }
    } catch (error) {
      console.error('Synthesis error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate synthesis. Please try again.';
      alert('Synthesis error: ' + errorMessage);
    } finally {
      setLoadingPreviousSynthesis(prev => ({...prev, [exchangeKey]: false}));
    }
  };

  const performPreviousCrossReflection = async (exchangeIndex: number, exchange: any) => {
    const exchangeKey = `${exchangeIndex}`;
    const selectedSet = previousExchangesSelected[exchangeKey] || new Set();

    if (selectedSet.size !== 2) {
      alert('Please select exactly 2 responses for cross-reflection');
      return;
    }

    const selectedIndices = Array.from(selectedSet);
    const response1 = exchange.responses[selectedIndices[0]];
    const response2 = exchange.responses[selectedIndices[1]];

    setLoadingPreviousCrossReflection(prev => ({...prev, [exchangeKey]: true}));

    try {
      const headers = getAuthHeaders();

      const response = await fetch('http://localhost:8000/api/v1/consensus/cross-reflect/', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          user_query: exchange.question,
          llm1_name: response1.service,
          llm1_response: response1.content,
          llm2_name: response2.service,
          llm2_response: response2.content,
          chat_history: '',
          conversation_id: currentConversationId
        })
      });

      const data = await response.json();

      if (data.success && data.reflections) {
        const reflections: AIResponse[] = data.reflections.map((reflection: any) => ({
          service: `${reflection.service} (reflecting on ${reflection.reflecting_on})`,
          success: true,
          content: reflection.content,
          synopsis: reflection.synopsis
        }));
        setPreviousCrossReflectionResults(prev => ({...prev, [exchangeKey]: reflections}));
        setPreviousCrossReflectionExpanded(prev => ({...prev, [exchangeKey]: true})); // Default to expanded
        // Refresh conversation list to show updated costs
        setConversationRefreshTrigger(prev => prev + 1);
      } else {
        alert('Cross-reflection failed: ' + (data.error || 'Unable to generate cross-reflection. Please try again.'));
      }
    } catch (error) {
      console.error('Cross-reflection error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to generate cross-reflection. Please try again.';
      alert('Cross-reflection error: ' + errorMessage);
    } finally {
      setLoadingPreviousCrossReflection(prev => ({...prev, [exchangeKey]: false}));
    }
  };


  const togglePreference = (index: number) => {
    setPreferredResponses(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  // Helper functions for previous exchanges
  const toggleExchangeCollapsed = (exchangeIndex: number) => {
    setExchangesCollapsed(prev => {
      const newSet = new Set(prev);
      if (newSet.has(exchangeIndex)) {
        newSet.delete(exchangeIndex);
      } else {
        newSet.add(exchangeIndex);
      }
      return newSet;
    });
  };

  // Copy to clipboard function
  const copyToClipboard = async (text: string, itemId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedItems(prev => ({ ...prev, [itemId]: true }));

      // Reset copied state after 2 seconds
      setTimeout(() => {
        setCopiedItems(prev => ({ ...prev, [itemId]: false }));
      }, 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
      alert('Failed to copy to clipboard');
    }
  };

  const handleSignOut = async () => {
    if (window.confirm('Are you sure you want to sign out?')) {
      try {
        await apiService.logout();
        // Redirect to login page
        window.location.href = '/login';
      } catch (error) {
        console.error('Sign out error:', error);
        // Even if API call fails, still redirect to login
        window.location.href = '/login';
      }
    }
  };

  const togglePreviousExpanded = (exchangeIndex: number, responseIndex: number) => {
    const key = `${exchangeIndex}`;
    setPreviousExchangesExpanded(prev => {
      const newState = { ...prev };
      const currentSet = newState[key] || new Set();

      // Create new Set: if clicking the same one that's expanded, collapse it
      // Otherwise, only expand the clicked one (collapse others)
      const newSet = new Set<number>();
      if (!currentSet.has(responseIndex)) {
        newSet.add(responseIndex);
      }

      newState[key] = newSet;
      return newState;
    });
  };

  const togglePreviousSelected = (exchangeIndex: number, responseIndex: number) => {
    const key = `${exchangeIndex}`;
    setPreviousExchangesSelected(prev => {
      const newState = { ...prev };
      if (!newState[key]) newState[key] = new Set();

      const newSet = new Set(newState[key]);
      if (newSet.size >= 2 && !newSet.has(responseIndex)) {
        return newState; // Don't allow more than 2 selections
      }

      if (newSet.has(responseIndex)) {
        newSet.delete(responseIndex);
      } else {
        newSet.add(responseIndex);
      }
      newState[key] = newSet;
      return newState;
    });
  };

  const togglePreviousPreferred = (exchangeIndex: number, responseIndex: number) => {
    const key = `${exchangeIndex}`;
    setPreviousExchangesPreferred(prev => {
      const newState = { ...prev };
      if (!newState[key]) newState[key] = new Set();

      const newSet = new Set(newState[key]);
      if (newSet.has(responseIndex)) {
        newSet.delete(responseIndex);
      } else {
        newSet.add(responseIndex);
      }
      newState[key] = newSet;
      return newState;
    });
  };

  const toggleCrossReflectionPreference = (index: number) => {
    setPreferredCrossReflections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
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
          </div>
          <div className="flex-1 overflow-hidden">
            <ConversationHistory
              currentConversationId={selectedConversation?.id}
              onConversationSelect={handleConversationSelect}
              onNewConversation={handleNewConversation}
              className="h-full border-r-0"
              refreshTrigger={conversationRefreshTrigger}
            />
          </div>
          <div className="p-4 border-t border-gray-200 space-y-2">
            <button
              onClick={() => setShowModelSelection(true)}
              className="w-full px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 border-2 bg-white text-gray-700 border-gray-300 hover:border-gray-400 hover:bg-gray-50"
              title="Select AI Models"
            >
              <Settings size={16} />
              Select AI Models
            </button>
            <button
              onClick={() => setShowAccountSettings(true)}
              className="w-full px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 border-2 bg-white text-gray-700 border-gray-300 hover:border-gray-400 hover:bg-gray-50"
              title="Account Settings"
            >
              <Settings size={16} />
              Account Settings
            </button>
            <button
              onClick={handleSignOut}
              className="w-full px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 border-2 bg-white text-red-600 border-red-300 hover:border-red-400 hover:bg-red-50"
              title="Sign Out"
            >
              <LogOut size={16} />
              Sign Out
            </button>
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
      <div className="max-w-5xl mx-auto px-8 py-8 pb-32">
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
            <h1 className="text-2xl font-bold text-gray-900">AIX</h1>
          </div>

          <div className="flex items-center gap-4">
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




        {/* Previous Conversation Exchanges */}
        {conversationExchanges.map((exchange, exchangeIndex) => {
          const isCollapsed = exchangesCollapsed.has(exchangeIndex);
          const exchangeKey = `${exchangeIndex}`;
          const expandedSet = previousExchangesExpanded[exchangeKey] || new Set();
          const selectedSet = previousExchangesSelected[exchangeKey] || new Set();
          const preferredSet = previousExchangesPreferred[exchangeKey] || new Set();

          return (
            <div key={exchangeIndex} className="max-w-4xl mx-auto mb-8">
              {/* Previous User Query with collapse toggle */}
              <div className="flex justify-center mb-6">
                <div className="rounded-2xl px-6 py-4 max-w-3xl bg-blue-500 text-white relative">
                  <div className="text-xs opacity-70 mb-1">You</div>
                  <div>{exchange.question}</div>
                  <button
                    onClick={() => toggleExchangeCollapsed(exchangeIndex)}
                    className="absolute -bottom-3 left-1/2 transform -translate-x-1/2 bg-blue-600 hover:bg-blue-700 text-white p-1 rounded-full text-xs"
                  >
                    {isCollapsed ? '▼' : '▲'}
                  </button>
                </div>
              </div>

              {/* Previous AI Responses - Collapsible */}
              {!isCollapsed && (
                <div className="space-y-6">
                  {exchange.responses.map((response, responseIndex) => (
                    <div key={responseIndex} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
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
                        </div>

                        {/* Action buttons for previous exchanges - positioned on the right */}
                        {response.success && (
                          <div className="flex gap-2 justify-end mb-4">
                            <button
                              onClick={() => togglePreviousExpanded(exchangeIndex, responseIndex)}
                              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors text-gray-700"
                            >
                              {expandedSet.has(responseIndex) ? '-Collapse' : '+Expand'}
                            </button>
                            <button
                              onClick={() => togglePreviousSelected(exchangeIndex, responseIndex)}
                              className={`px-3 py-1 text-sm border rounded transition-colors ${
                                selectedSet.has(responseIndex)
                                  ? 'bg-gray-100 border-gray-400 text-gray-700'
                                  : 'border-gray-300 hover:bg-gray-50 text-gray-700'
                              }`}
                            >
                              {selectedSet.has(responseIndex) ? 'Selected' : 'Select'}
                            </button>
                            <button
                              onClick={() => togglePreviousPreferred(exchangeIndex, responseIndex)}
                              className={`px-3 py-1 text-sm border rounded transition-colors ${
                                preferredSet.has(responseIndex)
                                  ? 'bg-gray-100 border-gray-400 text-blue-600'
                                  : 'border-gray-300 hover:bg-gray-50 text-gray-700'
                              }`}
                            >
                              {preferredSet.has(responseIndex) ? 'Preferred' : 'Prefer'}
                            </button>
                            <button
                              onClick={() => copyToClipboard(response.content || '', `prev-${exchangeIndex}-${responseIndex}`)}
                              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors flex items-center gap-1 text-gray-700"
                              title="Copy to clipboard"
                            >
                              {copiedItems[`prev-${exchangeIndex}-${responseIndex}`] ? (
                                <>
                                  <Check size={14} className="text-green-600" />
                                  <span>Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy size={14} />
                                  <span>Copy</span>
                                </>
                              )}
                            </button>
                          </div>
                        )}

                        {/* Response Content */}
                        <div className={`text-gray-800 leading-relaxed ${
                          expandedSet.has(responseIndex)
                            ? 'max-h-[600px] overflow-y-auto border-t border-gray-100 pt-4 pr-2'
                            : ''
                        }`}>
                          {response.success ? (
                            expandedSet.has(responseIndex) ? (
                              <MarkdownRenderer content={response.content || ''} webSearchSources={exchange.webSearchSources} />
                            ) : (
                              <div className="relative">
                                <MarkdownRenderer content={response.synopsis || response.content || ''} webSearchSources={exchange.webSearchSources} />
                                {!response.synopsis && response.content && response.content.length > 500 && (
                                  <div className="mt-2 text-gray-500 text-sm italic">Click "+Expand" to read the full response...</div>
                                )}
                              </div>
                            )
                          ) : (
                            <div className="text-red-600">Error: {response.error}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* AI Analysis section for previous exchange */}
                  {selectedSet.size > 0 && (
                    <div className="mt-6 bg-purple-50 border border-purple-200 rounded-lg p-4">
                      <div className="text-center">
                        <h3 className="font-semibold text-purple-900 mb-3">
                          AI Analysis ({selectedSet.size}/2 selected)
                        </h3>

                        {selectedSet.size === 2 ? (
                          <div className="flex gap-3 justify-center">
                            <button
                              onClick={() => performPreviousCritique(exchangeIndex, exchange)}
                              disabled={loadingPreviousCritique[`${exchangeIndex}`]}
                              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400 transition-colors font-medium"
                            >
                              {loadingPreviousCritique[`${exchangeIndex}`] ? 'Analyzing...' : '⚖️ Compare'}
                            </button>
                            <button
                              onClick={() => performPreviousSynthesis(exchangeIndex, exchange)}
                              disabled={loadingPreviousSynthesis[`${exchangeIndex}`]}
                              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
                            >
                              {loadingPreviousSynthesis[`${exchangeIndex}`] ? '🔗 Combining...' : '🔗 Combine'}
                            </button>
                            <button
                              onClick={() => performPreviousCrossReflection(exchangeIndex, exchange)}
                              disabled={loadingPreviousCrossReflection[`${exchangeIndex}`]}
                              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 transition-colors font-medium"
                            >
                              {loadingPreviousCrossReflection[`${exchangeIndex}`] ? '🔀 Cross-reflecting...' : '🔀 Cross-reflect'}
                            </button>
                          </div>
                        ) : (
                          <p className="text-purple-700 text-sm">Select 2 responses to get AI-powered analysis</p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Critique Result for previous exchange - from archived or generated */}
                  {(exchange.critiqueResult || previousCritiqueResults[`${exchangeIndex}`]) && (
                    <div className="mt-6 bg-purple-50 border border-purple-200 rounded-lg p-6">
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="font-semibold text-purple-900">AI Comparison</h3>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setPreviousCritiqueExpanded(prev => ({...prev, [`${exchangeIndex}`]: !prev[`${exchangeIndex}`]}))}
                            className="px-3 py-1 text-sm border border-purple-300 rounded hover:bg-purple-100 transition-colors text-purple-900"
                          >
                            {previousCritiqueExpanded[`${exchangeIndex}`] !== false ? '-Collapse' : '+Expand'}
                          </button>
                          <button
                            onClick={() => copyToClipboard(
                              exchange.critiqueResult || previousCritiqueResults[`${exchangeIndex}`],
                              `prev-critique-${exchangeIndex}`
                            )}
                            className="px-3 py-1 text-sm border border-purple-300 rounded hover:bg-purple-100 transition-colors flex items-center gap-1 text-purple-900"
                            title="Copy critique to clipboard"
                          >
                            {copiedItems[`prev-critique-${exchangeIndex}`] ? (
                              <>
                                <Check size={14} className="text-green-600" />
                                <span>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy size={14} />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                          {(exchange.critiqueProvider || previousCritiqueProviders[`${exchangeIndex}`]) && (
                            <span className="text-xs text-purple-600 bg-purple-100 px-2 py-1 rounded">
                              Compared by: {exchange.critiqueProvider || previousCritiqueProviders[`${exchangeIndex}`]}
                            </span>
                          )}
                        </div>
                      </div>
                      {previousCritiqueExpanded[`${exchangeIndex}`] !== false && (
                        <MarkdownRenderer content={exchange.critiqueResult || previousCritiqueResults[`${exchangeIndex}`]} className="text-gray-700" />
                      )}
                    </div>
                  )}

                  {/* Synthesis Result for previous exchange - from archived or generated */}
                  {(exchange.synthesisResult || previousSynthesisResults[`${exchangeIndex}`]) && (
                    <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="font-semibold text-blue-900">AI Combination</h3>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setPreviousSynthesisExpanded(prev => ({...prev, [`${exchangeIndex}`]: !prev[`${exchangeIndex}`]}))}
                            className="px-3 py-1 text-sm border border-blue-300 rounded hover:bg-blue-100 transition-colors text-blue-900"
                          >
                            {previousSynthesisExpanded[`${exchangeIndex}`] !== false ? '-Collapse' : '+Expand'}
                          </button>
                          <button
                            onClick={() => copyToClipboard(
                              exchange.synthesisResult || previousSynthesisResults[`${exchangeIndex}`],
                              `prev-synthesis-${exchangeIndex}`
                            )}
                            className="px-3 py-1 text-sm border border-blue-300 rounded hover:bg-blue-100 transition-colors flex items-center gap-1 text-blue-900"
                            title="Copy synthesis to clipboard"
                          >
                            {copiedItems[`prev-synthesis-${exchangeIndex}`] ? (
                              <>
                                <Check size={14} className="text-green-600" />
                                <span>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy size={14} />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                          {(exchange.synthesisProvider || previousSynthesisProviders[`${exchangeIndex}`]) && (
                            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                              Combined by: {exchange.synthesisProvider || previousSynthesisProviders[`${exchangeIndex}`]}
                            </span>
                          )}
                        </div>
                      </div>
                      {previousSynthesisExpanded[`${exchangeIndex}`] !== false && (
                        <MarkdownRenderer content={exchange.synthesisResult || previousSynthesisResults[`${exchangeIndex}`]} className="text-gray-700" />
                      )}
                    </div>
                  )}

                  {/* Cross-Reflection Results for previous exchange */}
                  {previousCrossReflectionResults[`${exchangeIndex}`] && previousCrossReflectionResults[`${exchangeIndex}`].length > 0 && (
                    <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-6">
                      <div className="flex justify-between items-center mb-3">
                        <h3 className="font-semibold text-green-900">AI Cross-Reflection</h3>
                        <button
                          onClick={() => setPreviousCrossReflectionExpanded(prev => ({...prev, [`${exchangeIndex}`]: !prev[`${exchangeIndex}`]}))}
                          className="px-3 py-1 text-sm border border-green-300 rounded hover:bg-green-100 transition-colors text-green-900"
                        >
                          {previousCrossReflectionExpanded[`${exchangeIndex}`] !== false ? '-Collapse All' : '+Expand All'}
                        </button>
                      </div>
                      {previousCrossReflectionExpanded[`${exchangeIndex}`] !== false && (
                        <div className="space-y-4 mt-4">
                          {previousCrossReflectionResults[`${exchangeIndex}`].map((reflection: AIResponse, reflectionIndex: number) => (
                            <div key={reflectionIndex} className="bg-white border border-green-200 rounded-lg overflow-hidden">
                              <div className="p-6">
                                <div className="flex items-center justify-between mb-4">
                                  <div className="flex items-center gap-3">
                                    <h3 className="text-lg font-medium text-gray-900">{reflection.service}</h3>
                                    <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                                      Cross-Reflection
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <button
                                      onClick={() => {
                                        const key = `${exchangeIndex}`;
                                        setPreviousExpandedCrossReflections(prev => {
                                          const currentSet = prev[key] || new Set();
                                          const newSet = new Set<number>();
                                          // If clicking the same one that's expanded, collapse it
                                          if (!currentSet.has(reflectionIndex)) {
                                            newSet.add(reflectionIndex);
                                          }
                                          // Otherwise, only expand the clicked one (collapse others)
                                          return {...prev, [key]: newSet};
                                        });
                                      }}
                                      className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 transition-colors"
                                    >
                                      {(previousExpandedCrossReflections[`${exchangeIndex}`] || new Set()).has(reflectionIndex) ? '-Collapse' : '+Expand'}
                                    </button>
                                    <button
                                      onClick={() => copyToClipboard(reflection.content || '', `prev-cross-${exchangeIndex}-${reflectionIndex}`)}
                                      className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 transition-colors flex items-center gap-1"
                                      title="Copy reflection to clipboard"
                                    >
                                      {copiedItems[`prev-cross-${exchangeIndex}-${reflectionIndex}`] ? (
                                        <>
                                          <Check size={14} className="text-green-600" />
                                          <span>Copied</span>
                                        </>
                                      ) : (
                                        <>
                                          <Copy size={14} />
                                          <span>Copy</span>
                                        </>
                                      )}
                                    </button>
                                    <button
                                      onClick={() => {
                                        const key = `${exchangeIndex}`;
                                        setPreviousPreferredCrossReflections(prev => {
                                          const preferred = new Set(prev[key] || new Set());
                                          if (preferred.has(reflectionIndex)) {
                                            preferred.delete(reflectionIndex);
                                          } else {
                                            preferred.add(reflectionIndex);
                                          }
                                          return {...prev, [key]: preferred};
                                        });
                                      }}
                                      className={`px-3 py-1 text-sm border rounded transition-colors flex items-center gap-1 ${
                                        (previousPreferredCrossReflections[`${exchangeIndex}`] || new Set()).has(reflectionIndex)
                                          ? 'bg-yellow-100 border-yellow-400 text-yellow-800'
                                          : 'border-gray-300 hover:bg-gray-100'
                                      }`}
                                      title="Mark as preferred response"
                                    >
                                      <Star size={14} className={(previousPreferredCrossReflections[`${exchangeIndex}`] || new Set()).has(reflectionIndex) ? 'fill-yellow-500' : ''} />
                                      <span>Prefer</span>
                                    </button>
                                  </div>
                                </div>
                                {reflection.synopsis && (
                                  <div className="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                                    <p className="text-sm text-gray-700 font-medium"></p>
                                    <p className="text-sm text-gray-600 mt-1">{reflection.synopsis}</p>
                                  </div>
                                )}
                                {(previousExpandedCrossReflections[`${exchangeIndex}`] || new Set()).has(reflectionIndex) && reflection.content && (
                                  <MarkdownRenderer content={reflection.content} className="text-gray-700" />
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* Current User Query Display */}
        {conversationHistory?.length > 0 && (
          <div className="max-w-4xl mx-auto mb-8">
            {conversationHistory
              ?.filter(message => message.role === 'user')
              .slice(-1)
              .map((message, index) => (
                <div key={index} className="flex justify-center">
                  <div className="rounded-2xl px-6 py-4 max-w-3xl bg-blue-500 text-white">
                    <div className="text-xs opacity-70 mb-1">You</div>
                    <div>{message.content}</div>
                  </div>
                </div>
              ))}
          </div>
        )}

        {/* AI Responses - Only show current responses, not in history */}
        {responses?.length > 0 && (
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
                          className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors text-gray-700"
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
                          {selectedForCritique.has(index) ? 'Selected' : 'Select'}
                        </button>
                        <button
                          onClick={() => togglePreference(index)}
                          className={`px-3 py-1 text-sm border rounded transition-colors ${
                            preferredResponses.has(index)
                              ? 'bg-gray-100 border-gray-400 text-blue-600'
                              : 'border-gray-300 hover:bg-gray-50 text-gray-700'
                          }`}
                        >
                          {preferredResponses.has(index) ? 'Preferred' : 'Prefer'}
                        </button>
                        <button
                          onClick={() => copyToClipboard(response.content || '', `current-${index}`)}
                          className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 transition-colors flex items-center gap-1 ml-auto text-gray-700"
                          title="Copy to clipboard"
                        >
                          {copiedItems[`current-${index}`] ? (
                            <>
                              <Check size={14} className="text-green-600" />
                              <span>Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy size={14} />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Response Content */}
                  <div className={`text-gray-800 leading-relaxed ${
                    expandedResponses.has(index)
                      ? 'max-h-[600px] overflow-y-auto border-t border-gray-100 pt-4 pr-2'
                      : ''
                  }`}>
                    {response.success ? (
                      expandedResponses.has(index) ? (
                        <MarkdownRenderer content={response.content || ''} webSearchSources={webSearchSources} />
                      ) : (
                        <div className="relative">
                          <MarkdownRenderer content={response.synopsis || response.content || ''} webSearchSources={webSearchSources} />
                          {!response.synopsis && response.content && response.content.length > 500 && (
                            <div className="mt-2 text-gray-500 text-sm italic">Click "+Expand" to read the full response...</div>
                          )}
                        </div>
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
            <div className="text-center">
              <h3 className="font-semibold text-purple-900 mb-3">
                AI Analysis ({selectedForCritique.size}/2 selected)
              </h3>

              {selectedForCritique.size === 2 ? (
                <div className="flex gap-3 justify-center">
                  <button
                    onClick={performCritique}
                    disabled={loadingCritique}
                    className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400 transition-colors font-medium"
                  >
                    {loadingCritique ? '⚖️ Comparing...' : '⚖️ Compare'}
                  </button>
                  <button
                    onClick={performSynthesis}
                    disabled={loadingSynthesis}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors font-medium"
                  >
                    {loadingSynthesis ? 'Combining...' : '🔗 Combine'}
                  </button>
                  <button
                    onClick={performCrossReflection}
                    disabled={loadingCrossReflection}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400 transition-colors font-medium"
                  >
                    {loadingCrossReflection ? '🔀 Cross-reflecting...' : '🔀 Cross-reflect'}
                  </button>
                </div>
              ) : (
                <p className="text-purple-700 text-sm">Select 2 responses to get AI-powered analysis</p>
              )}
            </div>
          </div>
        )}

        {/* Critique Result */}
        {critiqueResult && (
          <div className="mt-6 bg-purple-50 border border-purple-200 rounded-lg p-6">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold text-purple-900">AI Comparison</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCritiqueExpanded(!critiqueExpanded)}
                  className="px-3 py-1 text-sm border border-purple-300 rounded hover:bg-purple-100 transition-colors text-purple-900"
                >
                  {critiqueExpanded ? '-Collapse' : '+Expand'}
                </button>
                <button
                  onClick={() => copyToClipboard(critiqueResult, 'current-critique')}
                  className="px-3 py-1 text-sm border border-purple-300 rounded hover:bg-purple-100 transition-colors flex items-center gap-1 text-purple-900"
                  title="Copy critique to clipboard"
                >
                  {copiedItems['current-critique'] ? (
                    <>
                      <Check size={14} className="text-green-600" />
                      <span>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
                {critiqueProvider && (
                  <span className="text-xs text-purple-600 bg-purple-100 px-2 py-1 rounded">
                    Compared by: {critiqueProvider}
                  </span>
                )}
              </div>
            </div>
            {critiqueExpanded && (
              <MarkdownRenderer content={critiqueResult} className="text-gray-700" />
            )}
          </div>
        )}

        {/* Synthesis Result */}
        {synthesisResult && (
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold text-blue-900">AI Combination</h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSynthesisExpanded(!synthesisExpanded)}
                  className="px-3 py-1 text-sm border border-blue-300 rounded hover:bg-blue-100 transition-colors text-blue-900"
                >
                  {synthesisExpanded ? '-Collapse' : '+Expand'}
                </button>
                <button
                  onClick={() => copyToClipboard(synthesisResult, 'current-synthesis')}
                  className="px-3 py-1 text-sm border border-blue-300 rounded hover:bg-blue-100 transition-colors flex items-center gap-1 text-blue-900"
                  title="Copy synthesis to clipboard"
                >
                  {copiedItems['current-synthesis'] ? (
                    <>
                      <Check size={14} className="text-green-600" />
                      <span>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
                {synthesisProvider && (
                  <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                    Combined by: {synthesisProvider}
                  </span>
                )}
              </div>
            </div>
            {synthesisExpanded && (
              <MarkdownRenderer content={synthesisResult} className="text-gray-700" />
            )}
          </div>
        )}

        {/* Cross-Reflection Results */}
        {crossReflectionResults?.length > 0 && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-6">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold text-green-900">AI Cross-Reflection</h3>
              <button
                onClick={() => setCrossReflectionExpanded(!crossReflectionExpanded)}
                className="px-3 py-1 text-sm border border-green-300 rounded hover:bg-green-100 transition-colors text-green-900"
              >
                {crossReflectionExpanded ? '-Collapse All' : '+Expand All'}
              </button>
            </div>
            {crossReflectionExpanded && (
              <div className="space-y-4 mt-4">
                {crossReflectionResults.map((reflection, index) => (
                  <div key={index} className="bg-white border border-green-200 rounded-lg overflow-hidden">
                    <div className="p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <h3 className="text-lg font-medium text-gray-900">{reflection.service}</h3>
                          <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                            Cross-Reflection
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => {
                              setExpandedCrossReflections(prev => {
                                const newSet = new Set<number>();
                                // If clicking the same one that's expanded, collapse it
                                if (!prev.has(index)) {
                                  newSet.add(index);
                                }
                                // Otherwise, only expand the clicked one (collapse others)
                                return newSet;
                              });
                            }}
                            className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 transition-colors"
                          >
                            {expandedCrossReflections.has(index) ? '-Collapse' : '+Expand'}
                          </button>
                          <button
                            onClick={() => copyToClipboard(reflection.content || '', `cross-reflection-${index}`)}
                            className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100 transition-colors flex items-center gap-1"
                            title="Copy reflection to clipboard"
                          >
                            {copiedItems[`cross-reflection-${index}`] ? (
                              <>
                                <Check size={14} className="text-green-600" />
                                <span>Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy size={14} />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                          <button
                            onClick={() => toggleCrossReflectionPreference(index)}
                            className={`px-3 py-1 text-sm border rounded transition-colors flex items-center gap-1 ${
                              preferredCrossReflections.has(index)
                                ? 'bg-yellow-100 border-yellow-400 text-yellow-800'
                                : 'border-gray-300 hover:bg-gray-100'
                            }`}
                            title="Mark as preferred response"
                          >
                            <Star size={14} className={preferredCrossReflections.has(index) ? 'fill-yellow-500' : ''} />
                            <span>Prefer</span>
                          </button>
                        </div>
                      </div>
                      {reflection.synopsis && (
                        <div className="mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                          <p className="text-sm text-gray-700 font-medium"></p>
                          <p className="text-sm text-gray-600 mt-1">{reflection.synopsis}</p>
                        </div>
                      )}
                      {expandedCrossReflections.has(index) && reflection.content && (
                        <MarkdownRenderer content={reflection.content} className="text-gray-700" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Searching Internet State - Show during web search */}
        {searchingInternet && (
          <div className="max-w-4xl mx-auto mb-20">
            <div className="bg-white border border-blue-200 rounded-lg overflow-hidden">
              <div className="p-6">
                <div className="flex items-center gap-3">
                  <Globe className="w-5 h-5 text-blue-500 animate-pulse" />
                  <h3 className="text-lg font-medium text-gray-900">Searching internet...</h3>
                </div>
                <div className="mt-2 text-gray-600 text-sm">
                  Gathering information from web sources to enhance responses
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Loading State - Show when generating AI responses (and not searching) */}
        {loading && !searchingInternet && (
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
        {!loading && conversationHistory?.length === 0 && (
          <div className="text-center py-16 mb-20">
            <div className="text-4xl mb-4">🤖</div>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">Welcome to AIX</h2>
            <p className="text-gray-600 text-lg mb-6">
              Get informed answers by analyzing responses from multiple AI services simultaneously
            </p>
            <div className="text-sm text-gray-500 space-y-2">
              <p>✨ Select multiple AI services</p>
              <p>🌐 Enable deep web search for current information</p>
              <p>🔍 Use AI analysis to compare, combine and cross-reference AI responses</p>
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
                title={webSearchEnabled ? 'Deep web search enabled' : 'Click to enable deep web search'}
              >
                <Globe size={18} />
              </button>

              {/* Question Input */}
              <div className="flex-1">
                <textarea
                  ref={textareaRef}
                  value={question}
                  onChange={(e) => {
                    setQuestion(e.target.value);
                    // Auto-resize textarea
                    const textarea = e.target;
                    textarea.style.height = 'auto';
                    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
                  }}
                  placeholder="Ask a question to multiple AI services..."
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none min-h-[48px] max-h-[120px] overflow-y-auto"
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
              {webSearchEnabled && ' • Deep web search enabled'}
            </div>
          </div>
        </div>
      </div>

      {/* Account Settings Modal */}
      {showAccountSettings && (
        <AccountSettings onClose={() => setShowAccountSettings(false)} />
      )}

      {/* Model Selection Modal */}
      <ModelSelectionModal
        isOpen={showModelSelection}
        onClose={() => setShowModelSelection(false)}
      />
    </div>
  );
};

export default AIConsensusComplete;
