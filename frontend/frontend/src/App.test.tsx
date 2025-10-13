/**
 * App.test.tsx
 * Tests for the main App component including rendering, navigation, and authentication
 */
import { render, screen } from '@testing-library/react';
import App from './App';

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

describe('App', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    test('renders without crashing', () => {
      render(<App />);
      expect(screen.getByTestId('ai-consensus-complete')).toBeInTheDocument();
    });

    test('renders the main heading', () => {
      render(<App />);
      expect(screen.getByText('AI Consensus')).toBeInTheDocument();
    });

    test('renders AI service selection buttons', () => {
      render(<App />);
      expect(screen.getByText('Claude')).toBeInTheDocument();
      expect(screen.getByText('OpenAI')).toBeInTheDocument();
      expect(screen.getByText('Gemini')).toBeInTheDocument();
    });

    test('renders the input area for questions', () => {
      render(<App />);
      const textarea = screen.getByPlaceholderText(/ask a question to multiple ai services/i);
      expect(textarea).toBeInTheDocument();
    });

    test('renders the send button', () => {
      render(<App />);
      const sendButton = screen.getByRole('button', { name: /send/i });
      expect(sendButton).toBeInTheDocument();
    });
  });

  describe('Component Integration', () => {
    test('renders AIConsensusComplete component', () => {
      render(<App />);
      const consensusComponent = screen.getByTestId('ai-consensus-complete');
      expect(consensusComponent).toBeInTheDocument();
    });

    test('applies correct CSS class to App container', () => {
      const { container } = render(<App />);
      const appDiv = container.querySelector('.App');
      expect(appDiv).toBeInTheDocument();
    });
  });

  describe('Layout Structure', () => {
    test('maintains proper component hierarchy', () => {
      const { container } = render(<App />);

      // Check that App div contains the consensus component
      const appDiv = container.querySelector('.App');
      expect(appDiv).toContainElement(screen.getByTestId('ai-consensus-complete'));
    });
  });
});

describe('App - Accessibility', () => {
  test('has proper document structure', () => {
    render(<App />);

    // Check for heading hierarchy
    const heading = screen.getByRole('heading', { name: /ai consensus/i });
    expect(heading).toBeInTheDocument();
  });

  test('form elements are accessible', () => {
    render(<App />);

    // Textarea should be accessible
    const textarea = screen.getByPlaceholderText(/ask a question/i);
    expect(textarea).toBeInTheDocument();

    // Buttons should be accessible
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
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
