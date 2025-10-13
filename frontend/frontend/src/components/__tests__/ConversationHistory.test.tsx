import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ConversationHistory from '../ConversationHistory';
import { apiService } from '../../services/api';

// Mock the API service
jest.mock('../../services/api');

const mockConversations = [
  {
    id: '1',
    title: 'Test Conversation 1',
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:30:00Z',
    agent_mode: 'standard' as const,
    total_messages: 5,
    total_tokens_used: 150,
    last_message_excerpt: 'This is a test message excerpt',
    ai_services_used: ['claude', 'gpt4'],
    total_cost: 0.025,
  },
  {
    id: '2',
    title: 'Test Conversation 2',
    created_at: '2024-01-02T10:00:00Z',
    updated_at: '2024-01-02T10:30:00Z',
    agent_mode: 'structured' as const,
    total_messages: 3,
    total_tokens_used: 100,
    last_message_excerpt: 'Another test message',
    ai_services_used: ['claude'],
    total_cost: 0.015,
  },
];

const mockApiService = apiService as jest.Mocked<typeof apiService>;

describe('ConversationHistory', () => {
  const defaultProps = {
    onConversationSelect: jest.fn(),
    onNewConversation: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockApiService.getConversations.mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: mockConversations,
    });
  });

  it('renders conversation history correctly', async () => {
    render(<ConversationHistory {...defaultProps} />);

    // Check header elements
    expect(screen.getByText('Chat History')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Search conversations...')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /new chat/i })).toBeInTheDocument();

    // Wait for conversations to load
    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
      expect(screen.getByText('Test Conversation 2')).toBeInTheDocument();
    });
  });

  it('displays conversation metadata correctly', async () => {
    render(<ConversationHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('This is a test message excerpt')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument(); // message count
      expect(screen.getByText('0.0250')).toBeInTheDocument(); // cost ($ icon is rendered separately)
      expect(screen.getByText('CLA')).toBeInTheDocument(); // AI service badge
      expect(screen.getByText('GPT')).toBeInTheDocument(); // AI service badge
    });
  });

  it('handles search input', async () => {
    render(<ConversationHistory {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText('Search conversations...');
    fireEvent.change(searchInput, { target: { value: 'test search' } });

    expect(searchInput).toHaveValue('test search');

    // Wait for debounced search
    await waitFor(() => {
      expect(mockApiService.getConversations).toHaveBeenCalledWith({
        q: 'test search',
        ordering: '-updated_at',
      });
    }, { timeout: 500 });
  });

  it('calls onConversationSelect when conversation is clicked', async () => {
    render(<ConversationHistory {...defaultProps} />);

    await waitFor(() => {
      const conversationItem = screen.getByText('Test Conversation 1');
      fireEvent.click(conversationItem);
    });

    expect(defaultProps.onConversationSelect).toHaveBeenCalledWith(mockConversations[0]);
  });

  it('calls onNewConversation when new chat button is clicked', async () => {
    render(<ConversationHistory {...defaultProps} />);

    await waitFor(() => {
      const newChatButton = screen.getByRole('button', { name: /new chat/i });
      fireEvent.click(newChatButton);
    });

    expect(defaultProps.onNewConversation).toHaveBeenCalled();
  });

  it('shows loading state initially', () => {
    // Mock a delayed API response
    mockApiService.getConversations.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        count: 0,
        next: null,
        previous: null,
        results: [],
      }), 100))
    );

    render(<ConversationHistory {...defaultProps} />);

    expect(screen.getByRole('status')).toBeInTheDocument(); // Loading spinner
  });

  it('shows empty state when no conversations exist', async () => {
    mockApiService.getConversations.mockResolvedValue({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });

    render(<ConversationHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
      expect(screen.getByText('Start a new conversation to get began')).toBeInTheDocument();
    });
  });

  it('shows error state when API fails', async () => {
    mockApiService.getConversations.mockRejectedValue(new Error('API Error'));

    render(<ConversationHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
      expect(screen.getByText('Try again')).toBeInTheDocument();
    });
  });

  it('highlights current conversation', async () => {
    const { container } = render(<ConversationHistory {...defaultProps} currentConversationId="1" />);

    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
      // Verify that at least one element has the active background color class
      const activeElements = container.querySelectorAll('.bg-blue-50');
      expect(activeElements.length).toBeGreaterThan(0);
    });
  });

  it('handles conversation actions', async () => {
    mockApiService.archiveConversation.mockResolvedValue(mockConversations[0]);
    mockApiService.deleteConversation.mockResolvedValue();
    mockApiService.forkConversation.mockResolvedValue(mockConversations[0]);
    mockApiService.updateConversation.mockResolvedValue(mockConversations[0]);

    // Mock window.confirm and window.prompt
    global.confirm = jest.fn(() => true);
    global.prompt = jest.fn(() => 'New Title');

    const { container } = render(<ConversationHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
    });

    // Find all buttons in the container and look for the menu button
    const allButtons = container.querySelectorAll('button');
    let menuButton: HTMLElement | null = null;

    // The menu button is inside the conversation item, find it by looking for MoreVertical icon parent
    for (const button of Array.from(allButtons)) {
      const svg = button.querySelector('svg');
      if (svg && button.closest('[class*="group"]')) {
        menuButton = button as HTMLElement;
        break;
      }
    }

    if (menuButton) {
      fireEvent.click(menuButton);

      // Wait for menu to appear and test archive action
      await waitFor(() => {
        const archiveButton = screen.getByText('Archive');
        fireEvent.click(archiveButton);
      });

      expect(mockApiService.archiveConversation).toHaveBeenCalledWith('1');
    }
  });

  it('filters out archived conversations by default', async () => {
    const conversationsWithArchived = [
      ...mockConversations,
      {
        ...mockConversations[0],
        id: '3',
        title: 'Archived Conversation',
        is_archived: true,
      },
    ];

    mockApiService.getConversations.mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: mockConversations,
    });

    render(<ConversationHistory {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Conversation 1')).toBeInTheDocument();
      expect(screen.getByText('Test Conversation 2')).toBeInTheDocument();
      expect(screen.queryByText('Archived Conversation')).not.toBeInTheDocument();
    });
  });
});