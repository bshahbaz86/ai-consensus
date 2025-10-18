/**
 * api.test.ts
 * Tests for the API service including contract tests for conversation management endpoints
 */
import { apiService } from './api';

// Mock fetch globally
global.fetch = jest.fn();

describe('ApiService', () => {
  const mockFetch = global.fetch as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    // Clear cookies
    Object.defineProperty(document, 'cookie', {
      writable: true,
      value: '',
    });
  });

  describe('CSRF Token Management', () => {
    test('getCsrfToken extracts token from cookies', async () => {
      // Set a CSRF token cookie
      document.cookie = 'csrftoken=test-csrf-token-123';

      const token = (apiService as any).getCsrfToken();

      expect(token).toBe('test-csrf-token-123');
    });

    test('getCsrfToken returns null when no token exists', () => {
      const token = (apiService as any).getCsrfToken();

      expect(token).toBeNull();
    });

    test('ensureCsrfToken fetches token if not present', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ count: 0, results: [] }),
      });

      await apiService.ensureCsrfToken();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/?page=1',
        expect.objectContaining({
          credentials: 'include',
        })
      );
    });

    test('ensureCsrfToken skips fetch if token already exists', async () => {
      document.cookie = 'csrftoken=existing-token';

      await apiService.ensureCsrfToken();

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe('Conversation Management', () => {
    beforeEach(() => {
      document.cookie = 'csrftoken=test-token';
    });

    test('getConversations makes correct API call', async () => {
      const mockResponse = {
        count: 2,
        next: null,
        previous: null,
        results: [
          { id: '1', title: 'Conv 1' },
          { id: '2', title: 'Conv 2' },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await apiService.getConversations();

      expect(result).toEqual(mockResponse);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/',
        expect.objectContaining({
          credentials: 'include',
        })
      );
    });

    test('getConversations includes search parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ count: 0, results: [] }),
      });

      await apiService.getConversations({
        q: 'test query',
        page: 2,
        ordering: '-created_at',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/?page=2&search=test+query&ordering=-created_at',
        expect.any(Object)
      );
    });

    test('getConversation fetches single conversation', async () => {
      const mockConversation = {
        id: 'test-123',
        title: 'Test Conversation',
        messages: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockConversation,
      });

      const result = await apiService.getConversation('test-123');

      expect(result).toEqual(mockConversation);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/test-123/',
        expect.any(Object)
      );
    });

    test('createConversation makes POST request with CSRF token', async () => {
      const newConversation = {
        id: 'new-123',
        title: 'New Chat',
        agent_mode: 'standard',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => newConversation,
      });

      const result = await apiService.createConversation({
        title: 'New Chat',
        agent_mode: 'standard',
      });

      expect(result).toEqual(newConversation);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-CSRFToken': 'test-token',
          }),
          credentials: 'include',
          body: JSON.stringify({
            title: 'New Chat',
            agent_mode: 'standard',
          }),
        })
      );
    });

    test('updateConversation makes PATCH request', async () => {
      const updated = {
        id: 'test-123',
        title: 'Updated Title',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => updated,
      });

      await apiService.updateConversation('test-123', {
        title: 'Updated Title',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/test-123/',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ title: 'Updated Title' }),
        })
      );
    });

    test('deleteConversation makes DELETE request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await apiService.deleteConversation('test-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/test-123/',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  describe('Search Functionality', () => {
    beforeEach(() => {
      document.cookie = 'csrftoken=test-token';
    });

    test('searchConversations includes all query parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ count: 0, results: [] }),
      });

      await apiService.searchConversations({
        q: 'search term',
        date_from: '2024-01-01',
        date_to: '2024-12-31',
        service: 'claude',
        min_tokens: 100,
        archived: false,
        ordering: '-created_at',
      });

      const call = mockFetch.mock.calls[0];
      const url = call[0] as string;

      expect(url).toContain('q=search+term');
      expect(url).toContain('date_from=2024-01-01');
      expect(url).toContain('date_to=2024-12-31');
      expect(url).toContain('service=claude');
      expect(url).toContain('min_tokens=100');
      expect(url).toContain('archived=false');
      expect(url).toContain('ordering=-created_at');
    });
  });

  describe('Conversation Actions', () => {
    beforeEach(() => {
      document.cookie = 'csrftoken=test-token';
    });

    test('forkConversation makes POST request', async () => {
      const forked = { id: 'forked-123', title: 'Forked Chat' };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => forked,
      });

      await apiService.forkConversation('original-123', {
        title: 'Forked Chat',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/original-123/fork/',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    test('archiveConversation makes PATCH request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 'test-123', is_archived: true }),
      });

      await apiService.archiveConversation('test-123');

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/test-123/archive/',
        expect.objectContaining({
          method: 'PATCH',
        })
      );
    });
  });

  describe('Messages', () => {
    beforeEach(() => {
      document.cookie = 'csrftoken=test-token';
    });

    test('getMessages fetches messages for conversation', async () => {
      const mockMessages = {
        count: 2,
        results: [
          { id: 'm1', content: 'Hello' },
          { id: 'm2', content: 'Hi there' },
        ],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockMessages,
      });

      const result = await apiService.getMessages('conv-123');

      expect(result).toEqual(mockMessages.results);
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/conversations/conv-123/messages/',
        expect.any(Object)
      );
    });
  });

  describe('Error Handling', () => {
    test('throws error on non-ok response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      await expect(apiService.getConversation('nonexistent')).rejects.toThrow(
        'API Error: 404 Not Found'
      );
    });

    test('handles network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(apiService.getConversations()).rejects.toThrow('Network error');
    });
  });

  describe('Authentication Token Management', () => {
    test('setAuthToken stores token in localStorage', () => {
      apiService.setAuthToken('test-auth-token');

      expect(localStorage.getItem('auth_token')).toBe('test-auth-token');
    });

    test('clearAuthToken removes token from localStorage', () => {
      localStorage.setItem('auth_token', 'test-token');

      apiService.clearAuthToken();

      expect(localStorage.getItem('auth_token')).toBeNull();
    });

    test('includes Authorization header when token is set', async () => {
      document.cookie = 'csrftoken=test-token';

      // Use the API service method to set the token
      apiService.setAuthToken('bearer-token-123');

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ count: 0, results: [] }),
      });

      await apiService.getConversations();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Token bearer-token-123',
          }),
        })
      );

      // Clean up
      apiService.clearAuthToken();
    });
  });

  describe('Request Headers', () => {
    test('includes Content-Type header for JSON requests', async () => {
      document.cookie = 'csrftoken=test-token';

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await apiService.createConversation({ title: 'Test' });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
    });

    test('includes credentials for cookie-based auth', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ count: 0, results: [] }),
      });

      await apiService.getConversations();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          credentials: 'include',
        })
      );
    });
  });
});

describe('apiService singleton', () => {
  test('exports a singleton instance', () => {
    expect(apiService).toBeDefined();
  });

  test('singleton maintains state across imports', () => {
    apiService.setAuthToken('singleton-test-token');
    expect(localStorage.getItem('auth_token')).toBe('singleton-test-token');

    // Clean up
    apiService.clearAuthToken();
  });
});
