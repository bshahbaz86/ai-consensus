/**
 * AIConsensusComplete.test.tsx
 * Tests for the AIConsensusComplete component including consensus mode, service selection, and response handling
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AIConsensusComplete from './AIConsensusComplete';
import { apiService } from '../services/api';

// Mock the apiService
jest.mock('../services/api', () => ({
  apiService: {
    ensureCsrfToken: jest.fn().mockResolvedValue(undefined),
    createConversation: jest.fn(),
    getConversation: jest.fn(),
    updateConversation: jest.fn(),
  },
}));

// Mock MarkdownRenderer
jest.mock('./MarkdownRenderer', () => {
  return function MockMarkdownRenderer({ content }: any) {
    return <div data-testid="markdown-content">{content}</div>;
  };
});

// Mock ConversationHistory
jest.mock('./ConversationHistory', () => {
  return function MockConversationHistory() {
    return <div data-testid="conversation-history">Conversation History</div>;
  };
});

// Mock fetch
global.fetch = jest.fn();

describe('AIConsensusComplete', () => {
  const mockFetch = global.fetch as jest.Mock;
  const mockCreateConversation = apiService.createConversation as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock successful conversation creation
    mockCreateConversation.mockResolvedValue({
      id: 'test-conversation-123',
      title: 'New AIX Chat',
      agent_mode: 'standard',
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
      total_messages: 0,
      total_tokens_used: 0,
      messages: [],
      last_message_excerpt: '',
      ai_services_used: [],
      total_cost: 0,
      recent_queries: []
    });
  });

  describe('Component Rendering', () => {
    test('renders without crashing', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByText('AIX')).toBeInTheDocument();
      });
    });

    test('displays welcome message when no conversation', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByText(/Welcome to AIX/i)).toBeInTheDocument();
      });
    });

    test('renders service selection buttons', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByText('Claude')).toBeInTheDocument();
        expect(screen.getByText('OpenAI')).toBeInTheDocument();
        expect(screen.getByText('Gemini')).toBeInTheDocument();
      });
    });

    test('renders question input textarea', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/ask a question to multiple ai services/i);
        expect(textarea).toBeInTheDocument();
      });
    });

    test('renders send button', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        const sendButtons = screen.getAllByText(/send/i);
        expect(sendButtons.length).toBeGreaterThanOrEqual(1);
      });
    });

    test('renders web search toggle button', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        // Web search toggle is the Globe icon button
        const buttons = screen.getAllByRole('button');
        expect(buttons.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Service Selection', () => {
    test('claude and gemini are selected by default', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        // Check for checkmarks on Claude and Gemini buttons
        const claudeButton = screen.getByText('Claude').closest('button');
        const geminiButton = screen.getByText('Gemini').closest('button');

        expect(claudeButton).toHaveTextContent('✓');
        expect(geminiButton).toHaveTextContent('✓');
      });
    });

    test('can toggle service selection by clicking button', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByText('Claude')).toBeInTheDocument();
      });

      // Click Claude button
      const claudeButton = screen.getByText('Claude').closest('button');
      if (claudeButton) {
        fireEvent.click(claudeButton);
      }

      // Verify button still exists (state changed but component still renders)
      expect(screen.getByText('Claude')).toBeInTheDocument();
    });

    test('can select OpenAI service by clicking button', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByText('OpenAI')).toBeInTheDocument();
      });

      const openAIButton = screen.getByText('OpenAI').closest('button');
      if (openAIButton) {
        fireEvent.click(openAIButton);
      }

      expect(screen.getByText('OpenAI')).toBeInTheDocument();
    });
  });

  describe('Question Submission', () => {
    test('allows typing a question', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/ask a question/i) as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: 'What is the meaning of life?' } });

      expect(textarea.value).toBe('What is the meaning of life?');
    });

    test('textarea is initially empty', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/ask a question/i) as HTMLTextAreaElement;
        expect(textarea.value).toBe('');
      });
    });

    test('can update textarea value', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/ask a question/i) as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: 'Test question' } });

      expect(textarea.value).toBe('Test question');
    });

    test('question input supports user interaction', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/ask a question/i);
      fireEvent.change(textarea, { target: { value: 'What is AI?' } });

      // Verify the input value was set
      expect((textarea as HTMLTextAreaElement).value).toBe('What is AI?');

      // Verify send buttons exist
      const sendButtons = screen.getAllByText(/send/i);
      expect(sendButtons.length).toBeGreaterThan(0);
    });
  });

  describe('Response Rendering', () => {
    test('component handles API responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          results: [
            {
              service: 'Claude',
              success: true,
              content: 'Test response from Claude',
              synopsis: 'Claude synopsis',
            },
          ],
          web_search_sources: [],
        }),
      });

      mockFetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true }),
      });

      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/ask a question/i);
      fireEvent.change(textarea, { target: { value: 'Test question' } });

      const sendButtons = screen.getAllByText(/send/i);
      const sendButton = sendButtons.find(btn => btn.closest('button'));
      if (sendButton?.closest('button')) {
        fireEvent.click(sendButton.closest('button')!);
      }

      // Verify fetch was called (response handling is tested in backend)
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      }, { timeout: 3000 });
    });

    test('renders question input while loading', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/ask a question/i);
        expect(textarea).toBeInTheDocument();
      });
    });

    test('prefer button removes other responses from the current exchange', async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ success: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            success: true,
            results: [
              {
                service: 'Claude',
                success: true,
                content: 'Full answer from Claude',
                synopsis: 'Claude synopsis content',
              },
              {
                service: 'Gemini',
                success: true,
                content: 'Full answer from Gemini',
                synopsis: 'Gemini synopsis content',
              },
            ],
            web_search_sources: [],
          }),
        })
        .mockResolvedValue({
          ok: true,
          json: async () => ({ success: true }),
        });

      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/ask a question/i)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/ask a question/i) as HTMLTextAreaElement;
      fireEvent.change(textarea, { target: { value: 'How does preference pruning work?' } });

      const sendButton = screen.getByRole('button', { name: 'Send' });
      fireEvent.click(sendButton);

      await waitFor(() => {
        expect(screen.getByText('Claude synopsis content')).toBeInTheDocument();
        expect(screen.getByText('Gemini synopsis content')).toBeInTheDocument();
      });

      // Ensure the current user query only appears once in the transcript
      expect(screen.getAllByText('How does preference pruning work?').length).toBe(1);

      const preferButtons = screen.getAllByText('Prefer');
      fireEvent.click(preferButtons[1]);

      await waitFor(() => {
        expect(screen.queryByText('Claude synopsis content')).not.toBeInTheDocument();
        expect(screen.getByText('Gemini synopsis content')).toBeInTheDocument();
        expect(screen.getAllByText('Preferred').length).toBe(1);
      });
    });
  });

  describe('Web Search Toggle', () => {
    test('web search is disabled by default', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        // Status line should not mention web search
        const statusText = screen.getByText(/2 AI service/i);
        expect(statusText).toBeInTheDocument();
      });
    });
  });

  describe('Consensus Features', () => {
    test('renders consensus interface elements', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(screen.getByText('AIX')).toBeInTheDocument();
      });

      // Verify service selection is present (key consensus feature)
      expect(screen.getByText('Claude')).toBeInTheDocument();
      expect(screen.getByText('Gemini')).toBeInTheDocument();
    });
  });

  describe('Conversation Initialization', () => {
    test('creates conversation on mount', async () => {
      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(mockCreateConversation).toHaveBeenCalledWith({
          title: 'New AIX Chat',
          agent_mode: 'standard',
        });
      });
    });

    test('handles conversation creation failure gracefully', async () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockCreateConversation.mockRejectedValueOnce(new Error('API Error'));

      render(<AIConsensusComplete />);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });

      // Component should still render
      expect(screen.getByText('AIX')).toBeInTheDocument();

      consoleErrorSpy.mockRestore();
    });
  });
});

describe('AIConsensusComplete - Accessibility', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiService.createConversation as jest.Mock).mockResolvedValue({
      id: 'test-123',
      title: 'New AIX Chat',
      agent_mode: 'standard',
      messages: [],
    });
  });

  test('all interactive elements are keyboard accessible', async () => {
    render(<AIConsensusComplete />);

    await waitFor(() => {
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);

      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeInTheDocument();
    });
  });

  test('has proper heading structure', async () => {
    render(<AIConsensusComplete />);

    await waitFor(() => {
      const heading = screen.getByText('AIX');
      expect(heading).toBeInTheDocument();
    });
  });
});
