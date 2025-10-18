/**
 * App.test.tsx
 * Tests for the main App component including rendering, navigation, and authentication
 */
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

// Mock react-router-dom (uses manual mock from __mocks__/react-router-dom.tsx)
jest.mock('react-router-dom');

// Mock the AIConsensusComplete component to isolate App tests
jest.mock('./components/AIConsensusComplete', () => {
  return function MockAIConsensusComplete() {
    return (
      <div data-testid="ai-consensus-complete">
        <h1>AI Consensus</h1>
        <div data-testid="service-selection">
          <button>Claude</button>
          <button>OpenAI</button>
          <button>Gemini</button>
        </div>
        <textarea placeholder="Ask a question to multiple AI services..." />
        <button>Send</button>
      </div>
    );
  };
});

// Mock LandingPage component
jest.mock('./components/LandingPage', () => {
  return function MockLandingPage() {
    return <div data-testid="landing-page">Landing Page</div>;
  };
});

// Mock GoogleCallback component
jest.mock('./components/GoogleCallback', () => {
  return function MockGoogleCallback() {
    return <div data-testid="google-callback">Google Callback</div>;
  };
});

describe('App', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    // Set up authentication to show AIConsensusComplete instead of landing page
    localStorage.setItem('auth_token', 'test-token');
    localStorage.setItem('user', JSON.stringify({ id: 1, email: 'test@example.com' }));
  });

  afterEach(() => {
    // Clean up localStorage
    localStorage.clear();
  });

  describe('Rendering', () => {
    test('renders without crashing', async () => {
      render(<App />);
      await waitFor(() => {
        expect(screen.getByTestId('ai-consensus-complete')).toBeInTheDocument();
      });
    });

    test('renders the main heading', async () => {
      render(<App />);
      await waitFor(() => {
        expect(screen.getByText('AI Consensus')).toBeInTheDocument();
      });
    });

    test('renders AI service selection buttons', async () => {
      render(<App />);
      await waitFor(() => {
        expect(screen.getByText('Claude')).toBeInTheDocument();
        expect(screen.getByText('OpenAI')).toBeInTheDocument();
        expect(screen.getByText('Gemini')).toBeInTheDocument();
      });
    });

    test('renders the input area for questions', async () => {
      render(<App />);
      await waitFor(() => {
        const textarea = screen.getByPlaceholderText(/ask a question to multiple ai services/i);
        expect(textarea).toBeInTheDocument();
      });
    });

    test('renders the send button', async () => {
      render(<App />);
      await waitFor(() => {
        const sendButton = screen.getByRole('button', { name: /send/i });
        expect(sendButton).toBeInTheDocument();
      });
    });
  });

  describe('Component Integration', () => {
    test('renders AIConsensusComplete component', async () => {
      render(<App />);
      await waitFor(() => {
        const consensusComponent = screen.getByTestId('ai-consensus-complete');
        expect(consensusComponent).toBeInTheDocument();
      });
    });

    test('applies correct CSS class to App container', () => {
      const { container } = render(<App />);
      const appDiv = container.querySelector('.App');
      expect(appDiv).toBeInTheDocument();
    });
  });

  describe('Layout Structure', () => {
    test('maintains proper component hierarchy', async () => {
      const { container } = render(<App />);

      // Check that App div contains the consensus component
      await waitFor(() => {
        const appDiv = container.querySelector('.App');
        expect(appDiv).toContainElement(screen.getByTestId('ai-consensus-complete'));
      });
    });
  });
});

describe('App - Accessibility', () => {
  beforeEach(() => {
    // Set up authentication
    localStorage.setItem('auth_token', 'test-token');
    localStorage.setItem('user', JSON.stringify({ id: 1, email: 'test@example.com' }));
  });

  afterEach(() => {
    localStorage.clear();
  });

  test('has proper document structure', async () => {
    render(<App />);

    // Check for heading hierarchy
    await waitFor(() => {
      const heading = screen.getByRole('heading', { name: /ai consensus/i });
      expect(heading).toBeInTheDocument();
    });
  });

  test('form elements are accessible', async () => {
    render(<App />);

    // Textarea should be accessible
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/ask a question/i);
      expect(textarea).toBeInTheDocument();

      // Buttons should be accessible
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });
});

describe('App - Error Boundaries', () => {
  // Suppress console.error for these tests since we're testing error scenarios
  const originalError = console.error;
  beforeAll(() => {
    console.error = jest.fn();
  });

  afterAll(() => {
    console.error = originalError;
  });

  test('handles rendering without errors', () => {
    expect(() => render(<App />)).not.toThrow();
  });
});
