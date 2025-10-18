import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import ConversationHistory from './ConversationHistory';
import ConversationDetailView from './ConversationDetailView';
import { Conversation, ConversationDetail, apiService } from '../services/api';

interface ChatLayoutProps {
  children?: React.ReactNode;
  className?: string;
}

const ChatLayout: React.FC<ChatLayoutProps> = ({ children, className = '' }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  // Check if we're on mobile
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
      // Auto-close sidebar on mobile when not needed
      if (window.innerWidth >= 768) {
        setSidebarOpen(true);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Auto-close sidebar on mobile when conversation is selected
  useEffect(() => {
    if (isMobile && selectedConversation) {
      setSidebarOpen(false);
    }
  }, [selectedConversation, isMobile]);

  const handleNewConversation = async () => {
    try {
      const newConversation = await apiService.createConversation({
        title: 'New Chat',
        agent_mode: 'standard',
      });
      setSelectedConversation(newConversation);

      // Close sidebar on mobile after creating new conversation
      if (isMobile) {
        setSidebarOpen(false);
      }
    } catch (err) {
      console.error('Error creating new conversation:', err);
    }
  };

  const handleConversationSelect = (conversation: Conversation) => {
    setSelectedConversation(conversation);
  };

  const handleBackToHistory = () => {
    setSelectedConversation(null);
    // Open sidebar when going back on mobile
    if (isMobile) {
      setSidebarOpen(true);
    }
  };

  const handleConversationUpdate = (updatedConversation: ConversationDetail) => {
    setSelectedConversation(updatedConversation);
  };

  return (
    <div className={`flex h-screen bg-gray-50 ${className}`}>
      {/* Sidebar */}
      <div
        className={`${
          isMobile
            ? `fixed inset-y-0 left-0 z-50 w-80 transform transition-transform duration-300 ease-in-out ${
                sidebarOpen ? 'translate-x-0' : '-translate-x-full'
              }`
            : `w-80 ${sidebarOpen ? 'block' : 'hidden'}`
        } bg-white shadow-lg`}
      >
        <ConversationHistory
          currentConversationId={selectedConversation?.id}
          onConversationSelect={handleConversationSelect}
          onNewConversation={handleNewConversation}
          className="h-full"
        />
      </div>

      {/* Mobile sidebar overlay */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black bg-opacity-50"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        {isMobile && (
          <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
            </button>

            <h1 className="text-lg font-semibold text-gray-900">
              {selectedConversation?.title || 'AI Consensus Chat'}
            </h1>

            <div className="w-10"></div> {/* Spacer for center alignment */}
          </div>
        )}

        {/* Desktop header (when sidebar is hidden) */}
        {!isMobile && !sidebarOpen && (
          <div className="bg-white border-b border-gray-200 p-4 flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Menu size={24} />
            </button>

            <h1 className="text-lg font-semibold text-gray-900">
              {selectedConversation?.title || 'AI Consensus Chat'}
            </h1>
          </div>
        )}

        {/* Content area */}
        <div className="flex-1 overflow-hidden">
          {selectedConversation ? (
            <ConversationDetailView
              conversationId={selectedConversation.id}
              onBack={handleBackToHistory}
              onConversationUpdate={handleConversationUpdate}
              className="h-full"
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-8">
              <div className="max-w-md">
                <h2 className="text-2xl font-bold text-gray-900 mb-4">
                  Welcome to AI Consensus Chat
                </h2>
                <p className="text-gray-600 mb-6">
                  Select a conversation from the sidebar to continue chatting, or start a new
                  conversation to begin.
                </p>
                <div className="space-y-3">
                  <button
                    onClick={handleNewConversation}
                    className="w-full px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
                  >
                    Start New Conversation
                  </button>
                  {!sidebarOpen && (
                    <button
                      onClick={() => setSidebarOpen(true)}
                      className="w-full px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      Browse Chat History
                    </button>
                  )}
                </div>
              </div>

              {/* Tips for new users */}
              <div className="mt-12 max-w-lg">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Features:</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600">
                  <div className="bg-white p-4 rounded-lg border border-gray-200">
                    <h4 className="font-medium text-gray-900 mb-2">🔍 Search History</h4>
                    <p>Quickly find past conversations with full-text search</p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200">
                    <h4 className="font-medium text-gray-900 mb-2">🔄 Fork Conversations</h4>
                    <p>Branch off from any point in a conversation</p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200">
                    <h4 className="font-medium text-gray-900 mb-2">📱 Mobile Friendly</h4>
                    <p>Optimized for both desktop and mobile use</p>
                  </div>
                  <div className="bg-white p-4 rounded-lg border border-gray-200">
                    <h4 className="font-medium text-gray-900 mb-2">💰 Cost Tracking</h4>
                    <p>See tokens and costs for each conversation</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Render custom children if provided */}
          {children}
        </div>
      </div>
    </div>
  );
};

export default ChatLayout;