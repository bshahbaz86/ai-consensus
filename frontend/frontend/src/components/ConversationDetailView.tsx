import React, { useState, useEffect } from 'react';
import { ArrowLeft, Send, MoreVertical, ExternalLink, Archive, Share2 } from 'lucide-react';
import { apiService, ConversationDetail, Message } from '../services/api';

interface ConversationDetailViewProps {
  conversationId: string;
  onBack: () => void;
  onConversationUpdate?: (conversation: ConversationDetail) => void;
  className?: string;
}

interface MessageBubbleProps {
  message: Message;
  isLast: boolean;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isLast }) => {
  const isUser = message.role === 'user';

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-blue-500 text-white'
            : 'bg-gray-100 text-gray-900 border border-gray-200'
        }`}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>

        {/* Timestamp and metadata */}
        <div className={`text-xs mt-2 ${isUser ? 'text-blue-100' : 'text-gray-500'}`}>
          <span>{formatTimestamp(message.timestamp)}</span>
          {message.tokens_used > 0 && (
            <span className="ml-2">• {message.tokens_used} tokens</span>
          )}
        </div>
      </div>
    </div>
  );
};

const ConversationDetailView: React.FC<ConversationDetailViewProps> = ({
  conversationId,
  onBack,
  onConversationUpdate,
  className = '',
}) => {
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showMenu, setShowMenu] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);

  // Load conversation details
  useEffect(() => {
    const loadConversation = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiService.getConversation(conversationId);
        setConversation(data);
        onConversationUpdate?.(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load conversation');
      } finally {
        setLoading(false);
      }
    };

    loadConversation();
  }, [conversationId, onConversationUpdate]);

  // Handle send message (placeholder - would integrate with websocket service)
  const handleSendMessage = async () => {
    if (!newMessage.trim() || sending) return;

    setSending(true);
    try {
      // In a real implementation, this would use the WebSocket service
      // For now, we'll just add the message locally
      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: newMessage.trim(),
        timestamp: new Date().toISOString(),
        tokens_used: 0,
      };

      if (conversation) {
        setConversation({
          ...conversation,
          messages: [...conversation.messages, userMessage],
        });
      }

      setNewMessage('');
      // Here you would normally trigger the AI response via WebSocket
    } catch (err) {
      console.error('Error sending message:', err);
    } finally {
      setSending(false);
    }
  };

  // Handle conversation actions
  const handleArchive = async () => {
    if (!conversation) return;

    try {
      const updated = await apiService.archiveConversation(conversation.id);
      setConversation(updated);
      onConversationUpdate?.(updated);
    } catch (err) {
      console.error('Error archiving conversation:', err);
    }
  };

  const handleFork = async () => {
    if (!conversation) return;

    try {
      const forked = await apiService.forkConversation(conversation.id, {
        title: `Fork of ${conversation.title}`,
      });
      // Navigate to the new conversation
      window.location.hash = `#conversation/${forked.id}`;
    } catch (err) {
      console.error('Error forking conversation:', err);
    }
  };

  const handleRename = async () => {
    if (!conversation) return;

    const newTitle = window.prompt('Enter new conversation title:', conversation.title);
    if (newTitle && newTitle !== conversation.title) {
      try {
        const updated = await apiService.updateConversation(conversation.id, {
          title: newTitle,
        });
        setConversation(updated);
        onConversationUpdate?.(updated);
      } catch (err) {
        console.error('Error renaming conversation:', err);
      }
    }
  };

  const formatCost = (cost: number) => {
    return `$${cost.toFixed(4)}`;
  };

  if (loading) {
    return (
      <div className={`flex items-center justify-center h-full ${className}`}>
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error || !conversation) {
    return (
      <div className={`flex flex-col items-center justify-center h-full ${className}`}>
        <p className="text-red-600 mb-4">{error || 'Conversation not found'}</p>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full bg-white ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ArrowLeft size={20} />
          </button>

          <div>
            <h1 className="text-lg font-semibold text-gray-900 line-clamp-1">
              {conversation.title || `Chat ${conversation.id.slice(0, 8)}`}
            </h1>
            <div className="flex items-center gap-4 text-sm text-gray-500">
              <span>{conversation.total_messages} messages</span>
              <span>{conversation.total_tokens_used} tokens</span>
              {conversation.total_cost > 0 && (
                <span>{formatCost(conversation.total_cost)}</span>
              )}
            </div>
          </div>
        </div>

        {/* Actions menu */}
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <MoreVertical size={20} />
          </button>

          {showMenu && (
            <>
              <div className="absolute right-0 top-12 bg-white border border-gray-200 rounded-lg shadow-lg z-10 py-1 min-w-[180px]">
                <button
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                  onClick={() => {
                    handleRename();
                    setShowMenu(false);
                  }}
                >
                  Rename Conversation
                </button>
                <button
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                  onClick={() => {
                    handleFork();
                    setShowMenu(false);
                  }}
                >
                  <ExternalLink size={16} />
                  Fork Conversation
                </button>
                <button
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                  onClick={() => {
                    handleArchive();
                    setShowMenu(false);
                  }}
                >
                  <Archive size={16} />
                  {conversation.is_archived ? 'Unarchive' : 'Archive'}
                </button>
                <hr className="my-1" />
                <button
                  className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                  onClick={() => {
                    navigator.clipboard.writeText(window.location.href);
                    setShowMenu(false);
                  }}
                >
                  <Share2 size={16} />
                  Copy Link
                </button>
              </div>
              <div
                className="fixed inset-0 z-5"
                onClick={() => setShowMenu(false)}
              />
            </>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {conversation.messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <p className="text-gray-600 mb-2">No messages in this conversation yet</p>
            <p className="text-gray-500 text-sm">Send a message to continue the conversation</p>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            {conversation.messages.map((message, index) => (
              <MessageBubble
                key={message.id}
                message={message}
                isLast={index === conversation.messages.length - 1}
              />
            ))}
          </div>
        )}
      </div>

      {/* Message input */}
      <div className="p-4 border-t border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Continue the conversation..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              disabled={sending}
            />
            <button
              onClick={handleSendMessage}
              disabled={!newMessage.trim() || sending}
              className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <Send size={16} />
              {sending ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConversationDetailView;