# AI Consensus 🤖✨

**Get informed answers by comparing responses from multiple AI services simultaneously**

## Why AI Consensus?

In today's AI-driven world, different AI models often provide varying perspectives on the same question. **AI Consensus** solves the problem of AI response uncertainty by letting you:

- **Compare multiple AI perspectives** side-by-side
- **Make informed decisions** based on consensus across leading AI services
- **Identify the most comprehensive answer** for your specific needs
- **Save time** by querying multiple AIs in parallel instead of switching between platforms

## The Problem This App Solves

### Before: The AI Shopping Problem
- 🔄 **Switching between platforms**: Multiple AI services separately  
- ❓ **Uncertain which AI gives the best answer** for your question
- ⏱️ **Time-consuming** to get multiple perspectives
- 🤔 **Hard to compare responses** when they're on different platforms

### After: AI Consensus Solution
- ⚡ **One query, multiple responses** - instantly compare responses from leading AI models
- 📊 **Side-by-side comparison** with AI-generated intelligent summaries and full details
- 🎯 **Choose the best response** and continue the conversation seamlessly  
- 🔧 **Advanced features** like structured summarization with each AI using its own intelligence

## Demo

**Sample Query**: "Which top three state-of-the-art LLMs are most frequently fine-tuned to support mission-critical business applications, with model weights either publicly accessible or available for licensing from leading frontier AI providers?"

### Clean Interface with Consistent Action Buttons
![AI Consensus Interface](ai-consensus-improved-interface.png)

*Clean, modern interface with consistent action buttons: Expand/Collapse, Select for AI Critic, and Preferred This*

### Detailed Response View
![AI Consensus Expanded Response](ai-consensus-expanded-response.png)

*Expandable responses with full AI-generated content, structured markdown rendering, and action buttons*

### AI Critique & Comparison Feature
![AI Consensus Critique Ready](ai-consensus-critique-ready.png)

*Select multiple responses to get AI-powered comparative analysis and critique*

## Key Features

### 🚀 Core Functionality
- **Multi-AI Query**: Simultaneous responses from multiple leading AI models
- **AI-Generated Smart Summaries**: Each AI creates its own intelligent 35-45 word synopsis
- **Web Search Integration**: Optional real-time web search to enhance AI responses with up-to-date information
- **Response Selection**: Choose your preferred response and continue the conversation
- **Conversation Continuity**: Seamless chat experience with selected responses
- **Real-time Visual Feedback**: Blinking animation while AIs are thinking, hover tooltips showing model information

### 🧠 Advanced AI Features
- **AI-Generated Smart Summaries**: Each AI creates its own intelligent 35-45 word synopsis
- **AI Critique & Comparison**: Select any two responses for detailed AI-powered comparative analysis
- **Structured Summaries**: Advanced structured summarization across all AI providers
- **Enhanced API Endpoints**: `/summary/structured/` and `/critique/compare/` for specialized tasks
- **Flexible Response Modes**: Standard chat or structured summary mode

### 🎨 UI/UX Improvements
- **Consistent Action Buttons**: Uniform styling across Expand/Collapse, Select for AI Critic, and Preferred This buttons
- **Intelligent Response Selection**: "Preferred This" removes all other responses including AI Critic for clean continuation
- **No Auto-Expansion**: Select for AI Critic doesn't automatically expand responses, giving users full control
- **Professional Button Design**: Consistent height, padding, and visual weight across all interactive elements

### 🌐 Web Search Features
- **Real-time Web Search**: Toggle-enabled Reka Research API integration for current information
- **Intelligent Search**: Reka handles up to 2 web searches per query automatically with smart optimization
- **Location-Aware Search**: Browser geolocation support for location-specific results
- **Rate Limiting**: Proper rate limiting per user for efficient resource usage
- **Caching Layer**: 15-minute Redis TTL for efficient search result caching
- **Source Display**: Collapsible web sources with clickable links (collapsed by default)
- **Context Enhancement**: Web search results seamlessly integrated into AI prompts

### 🛠️ Technical Features
- **REST API** backend with async AI service integration
- **Modern web frontend** with real-time updates
- **Modular AI Service Architecture** supporting easy addition of new AI providers
- **Comprehensive Error Handling** with fallback mechanisms
- **Authentication & Permissions** ready for multi-user deployment

## Architecture

```mermaid
graph TB
    U[User] -->|Query + Web Search Toggle + Location| FE[React Frontend]
    FE -->|HTTP/REST API| API[Django REST API v1]

    API -->|Route Requests| ORCH[Multi-Agent Orchestrator]

    %% Web Search Layer
    ORCH -->|Web Search Enabled?| WSC[Web Search Coordinator]
    WSC -->|Rate Limiting & Caching| RC[Redis Cache - 15min TTL]
    WSC -->|Search Query + Location| REKA[Reka Research API]
    REKA -->|Search Results + AI Summary| WSC
    WSC -->|Enriched Context| ORCH

    %% AI Service Layer
    ORCH -->|Parallel Async Requests| AS[AI Services Manager]
    AS -->|Service Call + Context| C[Claude API]
    AS -->|Service Call + Context| O[OpenAI API]
    AS -->|Service Call + Context| G[Gemini API]

    %% Structured Summaries
    AS -->|Pydantic JSON Schema| PS[Structured Summary Service]
    PS -->|Validate Response| C
    PS -->|Validate Response| O
    PS -->|Validate Response| G

    %% Response Collection
    C -->|Response + Tokens| AS
    O -->|Response + Tokens| AS
    G -->|Response + Tokens| AS

    AS -->|All Responses| ORCH

    %% Data Persistence
    ORCH -->|Save| CONV[Conversations App]
    ORCH -->|Save| RESP[Responses App]
    ORCH -->|Save| AIQ[AI Services App]

    CONV -->|Store| DB[(PostgreSQL Database)]
    RESP -->|Store| DB
    AIQ -->|Store| DB

    %% Database Models
    DB -->|Conversations, Messages| CONV
    DB -->|AI Responses, Tokens, Cost| RESP
    DB -->|AI Queries, Service Tasks| AIQ
    DB -->|User Accounts| AUTH[Accounts App]

    %% Response to Frontend
    ORCH -->|JSON Response| API
    API -->|Responses + Web Sources + Cost| FE
    FE -->|Display| UI[UI Components]

    UI -->|Expand/Collapse| FE
    UI -->|Select for AI Critic| CRIT[AI Critique Service]
    UI -->|Preferred Response| ORCH

    CRIT -->|Compare 2 Responses| AS
    AS -->|Critique Analysis| CRIT
    CRIT -->|Comparison Result| FE

    %% Conversation Continuity
    FE -->|Continue with Selected AI| ORCH
    ORCH -->|Load Context| CONV
    CONV -->|Previous Messages| ORCH

    subgraph "Frontend Layer"
        FE
        UI
    end

    subgraph "API Layer"
        API
        ORCH
    end

    subgraph "Web Search Layer"
        WSC
        GSA
        RC
    end

    subgraph "AI Services Layer"
        AS
        C
        O
        G
        PS
        CRIT
    end

    subgraph "Django Apps"
        CONV
        RESP
        AIQ
        AUTH
    end

    subgraph "Data Layer"
        DB
    end
```

### Architecture Components

#### Frontend Layer
- **React/TypeScript SPA**: Modern frontend with real-time updates
- **UI Components**: AIConsensusComplete, ConversationHistory, Sidebar, MarkdownRenderer
- **Features**: Expandable responses, AI critique selection, response preference, web source display

#### API Layer
- **Django REST API v1**: RESTful endpoints with versioning
- **Multi-Agent Orchestrator**: Coordinates parallel AI service calls and web search
- **Rate Limiting**: Per-user rate limiting for web searches
- **Context Management**: Conversation continuity and history tracking

#### Web Search Layer
- **Web Search Coordinator**: Intelligent search orchestration with location support
- **Reka Research API**: AI-powered web search with automatic optimization (max 2 searches per query)
- **Redis Cache**: 15-minute TTL for search results and deduplication

#### AI Services Layer
- **AI Services Manager**: Unified interface for Claude, OpenAI, and Gemini
- **Structured Summary Service**: Pydantic-based JSON schema validation
- **AI Critique Service**: Comparative analysis of multiple AI responses
- **Async Processing**: Parallel service calls for optimal performance

#### Django Apps
- **Accounts**: User authentication and management
- **Conversations**: Conversation sessions, messages, and context
- **Responses**: AI responses with token tracking and cost calculation
- **AI Services**: Service configuration, queries, and task management

#### Data Layer
- **PostgreSQL**: Primary database with conversation_cost_view for accurate pricing
- **Models**: Conversation, Message, AIQuery, AIResponse, AIService, ConversationContext
- **Indexing**: Optimized queries with strategic database indexes


## Setup and Installation

### Prerequisites

- Modern Python environment
- Current Node.js runtime
- Optional caching service (for production; app works without it)
- API Keys for supported AI services

### Backend Setup

1. **Clone and navigate to project**
   ```bash
   git clone <repository-url>
   cd chat-ai-app
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your API keys:
   ```env
   # AI Service API Keys (get these from respective providers)
   OPENAI_API_KEY=sk-your-openai-key
   CLAUDE_API_KEY=sk-ant-your-claude-key
   GEMINI_API_KEY=your-gemini-key

   # Reka API Key (for web search functionality)
   REKA_API_KEY=your-reka-api-key

   # Django Configuration
   SECRET_KEY=your-secret-key-here
   DEBUG=True

   # Other settings are optional for basic setup
   ```

5. **Run database migrations**
   ```bash
   python3 manage.py migrate
   ```

6. **Load AI service data (required for cost tracking)**
   ```bash
   python3 manage.py loaddata apps/ai_services/fixtures/initial_services.json
   ```
   This creates the AI service records (Claude, OpenAI, Gemini) with pricing information.

7. **Create a superuser account (required for accessing the application)**
   ```bash
   python3 manage.py createsuperuser
   ```
   Follow the prompts to create your admin account.

8. **Start backend server**
   ```bash
   python3 manage.py runserver 8000
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend/frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

   **Note**: The project includes modern dependencies like React 19, TailwindCSS 3.x with PostCSS plugin, and TypeScript.

3. **Start frontend development server**
   ```bash
   npm start
   ```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001

## Security Configuration

### Authentication Requirements

**IMPORTANT**: As of the latest security updates, all API endpoints now require authentication to prevent unauthorized access and protect user data.

#### What Changed
1. **Conversations API**: All conversation and message endpoints now require user authentication
2. **Structured Summary API**: Requires authentication to prevent abuse of AI API credits
3. **Test AI Endpoints**: Protected with authentication and can be disabled in production

#### Authentication Implementation

The application uses Django REST Framework's built-in authentication:
- **Session Authentication**: For browser-based access
- **Token Authentication**: For API clients

**To use the API, you must:**
1. Create a user account (see setup step 6)
2. Authenticate your requests using one of these methods:
   - **Session Auth**: Log in via Django admin at http://localhost:8000/admin/
   - **Token Auth**: Obtain a token via the authentication endpoint

#### Security Best Practices

**For Development:**
- Use the superuser account created during setup
- Keep `DEBUG=True` and `ENABLE_TEST_AI_ENDPOINTS=True` in your `.env`

**For Production Deployment:**
- Set `DEBUG=False` in production environment
- Set `ENABLE_TEST_AI_ENDPOINTS=False` to disable diagnostic endpoints
- Use strong, randomly generated `SECRET_KEY`
- Implement proper user registration and login UI
- Enable HTTPS/TLS for all API communications
- Regularly rotate API keys for AI services

#### Test Endpoints Configuration

Test/diagnostic endpoints (`/api/v1/test-ai/`, `/api/v1/combine-responses/`, etc.) can be disabled in production by setting:
```env
ENABLE_TEST_AI_ENDPOINTS=False
```

These endpoints should only be enabled in development environments to prevent unauthorized consumption of AI API credits.

### Troubleshooting

**Common Issues:**

1. **Python command not found**: Use `python3` instead of `python` on Mac/Linux
2. **Port already in use**: Change the port number (e.g., `python3 manage.py runserver 8002`)
3. **API keys not working**: Ensure API keys are correctly set in `.env` file
4. **Frontend won't start**:
   - Make sure you're in `frontend/frontend` directory
   - Run `npm install` again if needed
   - Security warnings are normal for development
   - For TailwindCSS compilation errors, ensure `@tailwindcss/postcss` is installed
5. **Redis connection errors**: App works without Redis - cache is configured to use dummy backend for development
6. **Dependency cache issues**: If you encounter npm dependency problems or need to reclaim disk space:
   ```bash
   cd frontend/frontend
   rm -rf node_modules
   npm ci  # Restores exact versions from package-lock.json
   ```
   The `node_modules/` directory is just a local install cache (not committed to git) and can be safely deleted and recreated anytime.

**Required API Keys:**
- **OpenAI**: Get from https://platform.openai.com/api-keys
- **Claude**: Get from https://console.anthropic.com/
- **Gemini**: Get from https://ai.google.dev/
- **Reka**: Get from https://platform.reka.ai/ (for web search functionality)

**Note**: The app will work with just one AI API key, but you'll get the best experience with all three. Reka API key is optional but enables location-aware web search functionality.

## API Endpoints

### Core Endpoints
- `POST /api/v1/test-ai/` - Multi-AI query endpoint (supports web search via `use_web_search` parameter)
- `POST /api/v1/conversations/` - Create conversation
- `GET /api/v1/conversations/` - List conversations

### Advanced AI Endpoints
- `POST /api/v1/ai-services/summary/structured/` - Structured intelligent summaries
- `POST /api/v1/critique/compare/` - AI-powered response comparison and critique

### Authentication
- `POST /api/v1/auth/register/` - User registration
- `POST /api/v1/auth/login/` - User login
- `POST /api/v1/auth/logout/` - User logout

## Usage Examples

**Note**: All examples below require authentication. Make sure you're logged in or include authentication headers.

### Basic Multi-AI Query (with Session Authentication)
```bash
# First, log in via Django admin at http://localhost:8000/admin/
# Then use session cookies with curl:
curl -X POST http://localhost:8001/api/v1/test-ai/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"message": "Explain machine learning", "services": ["claude", "openai", "gemini"]}'
```

### Multi-AI Query with Web Search (with Token Authentication)
```bash
# First, obtain an auth token (implementation needed in your app)
# Then use token authentication:
curl -X POST http://localhost:8001/api/v1/test-ai/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -d '{
    "message": "What are the latest developments in AI safety research?",
    "services": ["claude", "openai", "gemini"],
    "use_web_search": true
  }'
```

### Structured Summary
```bash
curl -X POST http://localhost:8001/api/v1/ai-services/summary/structured/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "content": "Your text to summarize",
    "ai_service": "openai", // or "claude" or "gemini"
    "use_enhanced": true
  }'
```

### AI Critique & Comparison
```bash
curl -X POST http://localhost:8001/api/v1/critique/compare/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "Your original question",
    "llm1_name": "Claude",
    "llm1_response": "First AI response to compare",
    "llm2_name": "Gemini",
    "llm2_response": "Second AI response to compare",
    "chat_history": "Previous conversation context"
  }'
```


## Development

### Running Tests
```bash
# Backend tests
python manage.py test

# Frontend tests  
cd frontend/frontend
npm test
```

### Code Quality
```bash
# Backend linting
flake8 .
black .

# Frontend type checking
cd frontend/frontend
npm run type-check
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **OpenAI** for API access
- **Anthropic** for API access
- **Google** for API access
- **Reka AI** for Research API access
- Open source communities for excellent frameworks and tools