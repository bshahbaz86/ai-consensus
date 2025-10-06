/**
 * API service for conversation management and chat history
 */

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  agent_mode: 'standard' | 'structured';
  total_messages: number;
  total_tokens_used: number;
  last_message_at?: string;
  last_message_excerpt: string;
  ai_services_used: string[];
  total_cost: number;
  is_archived?: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  tokens_used: number;
  metadata?: any;
  query_session?: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  context?: {
    selected_ai_service?: string;
    context_data: any;
    last_selected_response_id?: string;
    updated_at: string;
  };
  recent_queries: any[];
}

export interface SearchParams {
  q?: string;
  date_from?: string;
  date_to?: string;
  service?: string;
  min_tokens?: number;
  archived?: boolean;
  ordering?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

class ApiService {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    // In a real app, this would come from authentication
    this.token = localStorage.getItem('auth_token');
  }

  private getCsrfToken(): string | null {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [cookieName, cookieValue] = cookie.trim().split('=');
      if (cookieName === name) {
        return cookieValue;
      }
    }
    return null;
  }

  /**
   * Ensure CSRF token is available by making a GET request to Django.
   * This must be called before any POST/PUT/DELETE requests.
   */
  async ensureCsrfToken(): Promise<void> {
    // Check if we already have a CSRF token
    if (this.getCsrfToken()) {
      return;
    }

    // Make a GET request to obtain the CSRF token cookie
    // We'll use the conversations endpoint which doesn't require any specific params
    try {
      await this.request<PaginatedResponse<Conversation>>('/conversations/?page=1');
    } catch (error) {
      console.error('Failed to obtain CSRF token:', error);
      throw error;
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}/api/v1${endpoint}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add CSRF token for non-GET requests
    const csrfToken = this.getCsrfToken();
    if (csrfToken && options.method && options.method !== 'GET') {
      headers['X-CSRFToken'] = csrfToken;
      console.log('[API] Adding CSRF token to request:', endpoint);
    } else if (!csrfToken && options.method && options.method !== 'GET') {
      console.warn('[API] No CSRF token found for non-GET request:', endpoint);
    }

    // Add any additional headers from options
    if (options.headers) {
      Object.entries(options.headers).forEach(([key, value]) => {
        if (typeof value === 'string') {
          headers[key] = value;
        }
      });
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include', // Include cookies for session authentication
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Conversation management
  async getConversations(params?: SearchParams & { page?: number }): Promise<PaginatedResponse<Conversation>> {
    const searchParams = new URLSearchParams();

    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.q) searchParams.append('search', params.q);
    if (params?.ordering) searchParams.append('ordering', params.ordering);
    if (params?.date_from) searchParams.append('date_from', params.date_from);
    if (params?.date_to) searchParams.append('date_to', params.date_to);
    if (params?.service) searchParams.append('service', params.service);
    if (params?.min_tokens) searchParams.append('min_tokens', params.min_tokens.toString());
    if (params?.archived !== undefined) searchParams.append('archived', params.archived.toString());

    const queryString = searchParams.toString();
    const endpoint = `/conversations/${queryString ? `?${queryString}` : ''}`;

    return this.request<PaginatedResponse<Conversation>>(endpoint);
  }

  async getConversation(id: string): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/conversations/${id}/`);
  }

  async createConversation(data: { title?: string; agent_mode?: string }): Promise<ConversationDetail> {
    return this.request<ConversationDetail>('/conversations/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateConversation(
    id: string,
    data: { title?: string; is_active?: boolean; agent_mode?: string }
  ): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/conversations/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteConversation(id: string): Promise<void> {
    return this.request<void>(`/conversations/${id}/`, {
      method: 'DELETE',
    });
  }

  // Search functionality
  async searchConversations(params: SearchParams): Promise<PaginatedResponse<Conversation>> {
    const searchParams = new URLSearchParams();

    if (params.q) searchParams.append('q', params.q);
    if (params.date_from) searchParams.append('date_from', params.date_from);
    if (params.date_to) searchParams.append('date_to', params.date_to);
    if (params.service) searchParams.append('service', params.service);
    if (params.min_tokens) searchParams.append('min_tokens', params.min_tokens.toString());
    if (params.archived !== undefined) searchParams.append('archived', params.archived.toString());
    if (params.ordering) searchParams.append('ordering', params.ordering);

    return this.request<PaginatedResponse<Conversation>>(`/conversations/search/?${searchParams.toString()}`);
  }

  // Conversation actions
  async forkConversation(
    id: string,
    data: { title?: string; from_message_id?: string }
  ): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/conversations/${id}/fork/`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async archiveConversation(id: string): Promise<ConversationDetail> {
    return this.request<ConversationDetail>(`/conversations/${id}/archive/`, {
      method: 'PATCH',
    });
  }

  // Messages
  async getMessages(conversationId: string): Promise<Message[]> {
    const response = await this.request<PaginatedResponse<Message>>(`/conversations/${conversationId}/messages/`);
    return response.results;
  }

  // Utility methods
  setAuthToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  clearAuthToken() {
    this.token = null;
    localStorage.removeItem('auth_token');
  }
}

export const apiService = new ApiService();
export default apiService;