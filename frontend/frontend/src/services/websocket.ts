export interface WebSocketMessage {
  type: string;
  data: any;
}

export interface AIQueryStatus {
  query_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  responses: any[];
  total_services: number;
  completed_services: number;
  failed_services: number;
}

export class ChatWebSocketService {
  private ws: WebSocket | null = null;
  private conversationId: string | null = null;
  private messageCallbacks: Map<string, (data: any) => void> = new Map();

  constructor(private baseUrl: string = 'ws://localhost:8000') {}

  connect(conversationId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // For demo purposes, we'll simulate WebSocket functionality
        // In production, this would connect to Django Channels WebSocket
        this.conversationId = conversationId;
        console.log(`Simulating WebSocket connection to ${this.baseUrl}/ws/chat/${conversationId}/`);
        
        setTimeout(() => {
          console.log('WebSocket connected (simulated)');
          resolve();
        }, 100);
      } catch (error) {
        reject(error);
      }
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.conversationId = null;
    this.messageCallbacks.clear();
  }

  sendMessage(message: string, context?: any): Promise<string> {
    return new Promise((resolve) => {
      // Simulate sending message and getting query_id back
      const queryId = `query_${Date.now()}`;
      console.log('Simulating message send:', { message, context, queryId });
      
      // Simulate server response delay
      setTimeout(() => {
        resolve(queryId);
        
        // Simulate AI response updates
        this.simulateAIResponse(queryId);
      }, 500);
    });
  }

  subscribeToQueryUpdates(queryId: string, callback: (status: AIQueryStatus) => void): void {
    this.messageCallbacks.set(`query_${queryId}`, callback);
  }

  private simulateAIResponse(queryId: string): void {
    const callback = this.messageCallbacks.get(`query_${queryId}`);
    if (!callback) return;

    // Simulate processing status
    callback({
      query_id: queryId,
      status: 'processing',
      responses: [],
      total_services: 2,
      completed_services: 0,
      failed_services: 0
    });

    // Simulate Claude response after 1.5s
    setTimeout(() => {
      callback({
        query_id: queryId,
        status: 'processing',
        responses: [{
          id: 'claude_response',
          service: 'Claude',
          content: 'This is a simulated response from Claude...',
          summary: 'Claude provides a comprehensive analysis',
          reasoning: 'Based on contextual understanding',
          status: 'completed'
        }],
        total_services: 2,
        completed_services: 1,
        failed_services: 0
      });
    }, 1500);

    // Simulate OpenAI response after 2s
    setTimeout(() => {
      callback({
        query_id: queryId,
        status: 'completed',
        responses: [{
          id: 'claude_response',
          service: 'Claude',
          content: 'This is a simulated response from Claude...',
          summary: 'Claude provides a comprehensive analysis',
          reasoning: 'Based on contextual understanding',
          status: 'completed'
        }, {
          id: 'openai_response',
          service: 'OpenAI',
          content: 'This is a simulated response from OpenAI...',
          summary: 'OpenAI suggests a different approach',
          reasoning: 'Using advanced reasoning',
          status: 'completed'
        }],
        total_services: 2,
        completed_services: 2,
        failed_services: 0
      });
    }, 2000);
  }

  // Real implementation would connect to Django Channels WebSocket
  private connectToRealWebSocket(conversationId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = `${this.baseUrl}/ws/chat/${conversationId}/`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('Connected to ChatAI WebSocket');
        resolve();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket connection error:', error);
        reject(error);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
          
          if (data.type === 'ai_response_update' || data.type === 'query_completed') {
            const callback = this.messageCallbacks.get(`query_${data.query_id}`);
            if (callback) {
              callback(data);
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket connection closed');
      };
    });
  }
}

export const chatWebSocketService = new ChatWebSocketService();