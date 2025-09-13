from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt 
def demo_view(request):
    """
    Simple demo page to test all AI services
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChatAI Multi-Service Demo</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .question {
            background: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #2196f3;
        }
        .services {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .service-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-top: 4px solid;
        }
        .claude { border-top-color: #FF6B35; }
        .openai { border-top-color: #00A67E; }
        .gemini { border-top-color: #4285F4; }
        
        .service-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .service-logo {
            width: 24px;
            height: 24px;
            margin-right: 10px;
            border-radius: 4px;
        }
        .service-name {
            font-weight: bold;
            font-size: 18px;
        }
        .status {
            margin-left: auto;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        .status.success {
            background: #e8f5e8;
            color: #2e7d32;
        }
        .status.error {
            background: #ffebee;
            color: #c62828;
        }
        .response {
            line-height: 1.6;
            color: #333;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .test-button {
            background: #2196f3;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px;
        }
        .test-button:hover {
            background: #1976d2;
        }
        .test-button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .implementation-note {
            background: #f0f7ff;
            border: 1px solid #0066cc;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
        }
        .implementation-note h3 {
            color: #0066cc;
            margin-top: 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 ChatAI Multi-Service Demo</h1>
        <p>Testing all three AI services with the question from README.md</p>
        <button onclick="testAllServices()" class="test-button" id="testBtn">
            Test All AI Services
        </button>
        <button onclick="testStructuredSummary()" class="test-button">
            Show Structured Summary Info
        </button>
        <button onclick="testStructuredSummary()" class="test-button">
            Show Structured Summary Info
        </button>
    </div>

    <div class="question">
        <strong>Question from README.md:</strong> "How will lower US interest rates affect USD to EUR conversion rate?"
    </div>

    <div class="implementation-note">
        <h3>✨ New Features Implemented:</h3>
        <ul>
            <li><strong>Pydantic-based Intelligent Summaries:</strong> Using OpenAI function calling with structured models</li>
            <li><strong>Structured Summaries:</strong> Pydantic-based intelligent summarization with OpenAI function calling</li>
            <li><strong>Enhanced API Endpoints:</strong> Structured summary endpoints for intelligent analysis</li>
            <li><strong>Updated Models:</strong> Conversation model with structured mode support</li>
        </ul>
    </div>

    <div id="results">
        <div class="loading">Click "Test All AI Services" to see responses from Claude, OpenAI, and Gemini</div>
    </div>

    <script>
        async function testAllServices() {
            const btn = document.getElementById('testBtn');
            btn.disabled = true;
            btn.textContent = 'Testing...';
            
            document.getElementById('results').innerHTML = `
                <div class="services">
                    <div class="service-card claude">
                        <div class="service-header">
                            <div class="service-logo" style="background: #FF6B35;"></div>
                            <div class="service-name">Claude (Anthropic)</div>
                            <div class="status">Loading...</div>
                        </div>
                        <div class="response">Generating response...</div>
                    </div>
                    <div class="service-card openai">
                        <div class="service-header">
                            <div class="service-logo" style="background: #00A67E;"></div>
                            <div class="service-name">GPT-4 (OpenAI)</div>
                            <div class="status">Loading...</div>
                        </div>
                        <div class="response">Generating response...</div>
                    </div>
                    <div class="service-card gemini">
                        <div class="service-header">
                            <div class="service-logo" style="background: #4285F4;"></div>
                            <div class="service-name">Gemini (Google)</div>
                            <div class="status">Loading...</div>
                        </div>
                        <div class="response">Generating response...</div>
                    </div>
                </div>
            `;

            try {
                const response = await fetch('/api/v1/test-ai/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: 'how will lower us interest rates affect usd to euro conversion rate?',
                        services: ['claude', 'openai', 'gemini']
                    })
                });

                const data = await response.json();
                
                if (data.success) {
                    displayResults(data.results);
                } else {
                    document.getElementById('results').innerHTML = `<div class="error">Error: ${data.error}</div>`;
                }
            } catch (error) {
                document.getElementById('results').innerHTML = `<div class="error">Network error: ${error.message}</div>`;
            }
            
            btn.disabled = false;
            btn.textContent = 'Test All AI Services';
        }

        function displayResults(results) {
            const services = {
                'Claude': { class: 'claude', color: '#FF6B35' },
                'OpenAI': { class: 'openai', color: '#00A67E' },
                'Gemini': { class: 'gemini', color: '#4285F4' }
            };

            let html = '<div class="services">';
            
            results.forEach(result => {
                const service = services[result.service];
                const statusClass = result.success ? 'success' : 'error';
                const statusText = result.success ? '✅ Success' : '❌ Error';
                
                html += `
                    <div class="service-card ${service.class}">
                        <div class="service-header">
                            <div class="service-logo" style="background: ${service.color};"></div>
                            <div class="service-name">${result.service}</div>
                            <div class="status ${statusClass}">${statusText}</div>
                        </div>
                        <div class="response">
                            ${result.success ? result.content : `Error: ${result.error}`}
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            document.getElementById('results').innerHTML = html;
        }

        async function testStructuredSummary() {
            alert(`🎯 Pydantic-Based Structured Summaries

Endpoint: POST /api/v1/ai-services/summary/structured/

Features:
• Uses your proposed Overview BaseModel pattern
• OpenAI function calling with convert_pydantic_to_openai_function()
• Rich metadata: complexity, tone, actionability, key points
• Backward compatible with existing ResponseSummarizer

Example:
{
  "content": "Your text to summarize",
  "ai_service": "openai", 
  "use_enhanced": true
}

Response includes structured summary with confidence scores, follow-up questions, and related concepts!`);
        }

        async function testStructuredSummary() {
            alert(`📝 Structured Summary Mode

Features:
• Pydantic-based structured summaries using OpenAI function calling
• Enhanced summarization with intelligent extraction
• Django model integration with structured mode

Example endpoint: POST /api/v1/ai-services/summary/structured/`);
        }
    </script>
</body>
</html>
    """
    return HttpResponse(html_content)