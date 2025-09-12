#!/bin/bash
# Claude Code New Project Setup Script

PROJECT_DIR="$1"

if [ -z "$PROJECT_DIR" ]; then
    echo "Usage: $0 <project-directory>"
    echo "Example: $0 ~/my-new-project"
    exit 1
fi

# Create project directory if it doesn't exist
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Add filesystem MCP for this specific project
claude mcp add "filesystem" -- /opt/homebrew/bin/npx -y @modelcontextprotocol/server-filesystem "$PROJECT_DIR"

echo "✅ New project setup complete at: $PROJECT_DIR"
echo "🔧 Available MCP servers:"
echo "  - filesystem (project-specific)"
echo "  - fetch (global)"
echo "  - github (global)"
echo "  - playwright (global)"
echo ""
echo "Run 'claude mcp list' to verify all servers are connected."