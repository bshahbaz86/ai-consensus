import React, { useState, useEffect, useCallback } from 'react';
import {
  Search, Plus, MessageSquare, Clock, DollarSign,
  Archive, MoreVertical, Trash2, Edit2, ExternalLink
} from 'lucide-react';
import { apiService, Conversation, SearchParams } from '../services/api';

interface ConversationHistoryProps {
  currentConversationId?: string;
  onConversationSelect: (conversation: Conversation) => void;
  onNewConversation: () => void;
  className?: string;
  refreshTrigger?: number; // Add this to trigger refresh when incremented
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onArchive: () => void;
  onDelete: () => void;
  onFork: () => void;
  onRename: () => void;
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  isActive,
  onSelect,
  onArchive,
  onDelete,
  onFork,
  onRename,
}) => {
  const [showMenu, setShowMenu] = useState(false);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const formatCost = (cost: number) => {
    return cost.toFixed(4);
  };

  return (
    <div
      className={`p-3 rounded-lg cursor-pointer transition-all duration-200 relative group ${
        isActive
          ? 'bg-blue-50 border-l-4 border-blue-500'
          : 'hover:bg-gray-50 border-l-4 border-transparent'
      }`}
      onClick={onSelect}
    >
      {/* Conversation header */}
      <div className="flex items-start justify-between mb-2">
        <h3 className={`font-medium text-sm line-clamp-2 ${
          isActive ? 'text-blue-900' : 'text-gray-900'
        }`}>
          {conversation.title || `Chat ${conversation.id.slice(0, 8)}`}
        </h3>

        {/* Menu button */}
        <button
          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-200 transition-opacity"
          onClick={(e) => {
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
        >
          <MoreVertical size={14} />
        </button>

        {/* Dropdown menu */}
        {showMenu && (
          <div className="absolute right-2 top-8 bg-white border border-gray-200 rounded-md shadow-lg z-10 py-1 min-w-[150px]">
            <button
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
              onClick={(e) => {
                e.stopPropagation();
                onRename();
                setShowMenu(false);
              }}
            >
              <Edit2 size={14} />
              Rename
            </button>
            <button
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
              onClick={(e) => {
                e.stopPropagation();
                onFork();
                setShowMenu(false);
              }}
            >
              <ExternalLink size={14} />
              Fork Chat
            </button>
            <button
              className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
              onClick={(e) => {
                e.stopPropagation();
                onArchive();
                setShowMenu(false);
              }}
            >
              <Archive size={14} />
              Archive
            </button>
            <hr className="my-1" />
            <button
              className="w-full px-3 py-2 text-left text-sm hover:bg-red-50 text-red-600 flex items-center gap-2"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
                setShowMenu(false);
              }}
            >
              <Trash2 size={14} />
              Delete
            </button>
          </div>
        )}
      </div>

      {/* Message excerpt */}
      {conversation.last_message_excerpt && (
        <p className="text-xs text-gray-600 line-clamp-2 mb-2">
          {conversation.last_message_excerpt}
        </p>
      )}

      {/* Metadata */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Clock size={12} />
            {formatDate(conversation.last_message_at || conversation.updated_at)}
          </span>

          <span className="flex items-center gap-1">
            <MessageSquare size={12} />
            {conversation.total_messages}
          </span>

          {conversation.total_cost >= 0.0001 && (
            <span className="flex items-center gap-1">
              <DollarSign size={12} />
              {formatCost(conversation.total_cost)}
            </span>
          )}
        </div>
      </div>

      {/* Click outside to close menu */}
      {showMenu && (
        <div
          className="fixed inset-0 z-5"
          onClick={() => setShowMenu(false)}
        />
      )}
    </div>
  );
};

const ConversationHistory: React.FC<ConversationHistoryProps> = ({
  currentConversationId,
  onConversationSelect,
  onNewConversation,
  className = '',
  refreshTrigger = 0,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchParams, setSearchParams] = useState<SearchParams>({});
  const [error, setError] = useState<string | null>(null);

  // Debounced search
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery);
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Load conversations
  const loadConversations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params: SearchParams = {
        ...searchParams,
        q: debouncedSearchQuery || undefined,
        ordering: '-updated_at',
      };

      const response = await apiService.getConversations(params);
      // Filter out conversations with zero messages, but keep the current active conversation
      const filteredConversations = response.results.filter(
        (conv) => conv.total_messages > 0 || conv.id === currentConversationId
      );
      setConversations(filteredConversations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
      console.error('Error loading conversations:', err);
    } finally {
      setLoading(false);
    }
  }, [debouncedSearchQuery, searchParams, currentConversationId]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Refresh conversations when refreshTrigger changes
  useEffect(() => {
    if (refreshTrigger > 0) {
      loadConversations();
    }
  }, [refreshTrigger, loadConversations]);

  // Conversation actions
  const handleArchive = async (conversationId: string) => {
    try {
      await apiService.archiveConversation(conversationId);
      await loadConversations();
    } catch (err) {
      console.error('Error archiving conversation:', err);
    }
  };

  const handleDelete = async (conversationId: string) => {
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      try {
        await apiService.deleteConversation(conversationId);
        await loadConversations();
      } catch (err) {
        console.error('Error deleting conversation:', err);
      }
    }
  };

  const handleFork = async (conversationId: string) => {
    try {
      const forkedConversation = await apiService.forkConversation(conversationId, {
        title: `Fork of conversation`
      });
      await loadConversations();
      onConversationSelect(forkedConversation);
    } catch (err) {
      console.error('Error forking conversation:', err);
    }
  };

  const handleRename = async (conversationId: string) => {
    const newTitle = window.prompt('Enter new conversation title:');
    if (newTitle) {
      try {
        await apiService.updateConversation(conversationId, { title: newTitle });
        await loadConversations();
      } catch (err) {
        console.error('Error renaming conversation:', err);
      }
    }
  };

  return (
    <div className={`flex flex-col h-full bg-white border-r border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex flex-col gap-2 mb-3">
          <button
            onClick={onNewConversation}
            className="w-full flex items-center justify-center gap-2 bg-blue-500 text-white rounded-lg px-4 py-3 hover:bg-blue-600 transition-colors font-medium"
          >
            <Plus size={16} />
            New Chat
          </button>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
          <input
            type="text"
            placeholder="Search conversations..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" role="status" aria-label="Loading conversations"></div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
            <p className="text-red-600 mb-2">{error}</p>
            <button
              onClick={loadConversations}
              className="text-blue-500 hover:text-blue-700"
            >
              Try again
            </button>
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
            <MessageSquare className="text-gray-400 mb-3" size={48} />
            <p className="text-gray-600 mb-2">
              {searchQuery ? 'No conversations found' : 'No conversations yet'}
            </p>
            <p className="text-gray-500 text-sm mb-4">
              {searchQuery ? 'Try adjusting your search' : 'Start a new conversation to get began'}
            </p>
            {!searchQuery && (
              <button
                onClick={onNewConversation}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                Start New Chat
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {conversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                isActive={conversation.id === currentConversationId}
                onSelect={() => onConversationSelect(conversation)}
                onArchive={() => handleArchive(conversation.id)}
                onDelete={() => handleDelete(conversation.id)}
                onFork={() => handleFork(conversation.id)}
                onRename={() => handleRename(conversation.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ConversationHistory;
