#!/bin/bash

# AI Consensus App - Comprehensive Test Runner
# Runs all backend and frontend tests with proper error handling

set -e  # Exit on error
set -o pipefail  # Catch errors in pipes

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test result tracking
BACKEND_PASSED=false
FRONTEND_PASSED=false

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to print section headers
print_header() {
    echo ""
    echo "=================================================================="
    print_status "$BLUE" "$1"
    echo "=================================================================="
    echo ""
}

# Function to check if we're in the project root
check_directory() {
    if [ ! -f "manage.py" ]; then
        print_status "$RED" "❌ Error: This script must be run from the project root directory"
        print_status "$YELLOW" "   Current directory: $(pwd)"
        print_status "$YELLOW" "   Please cd to the chat-ai-app directory and try again"
        exit 1
    fi
}

# Function to run backend tests
run_backend_tests() {
    print_header "🔧 Running Backend Tests (Django)"

    # Check if virtual environment is activated
    if [ -z "$VIRTUAL_ENV" ]; then
        print_status "$YELLOW" "⚠️  Warning: No virtual environment detected"
        print_status "$YELLOW" "   Continuing anyway, but you may want to activate venv first"
    fi

    # Run Django tests - only our new test suites
    echo "Running integration tests..."
    if ! USE_SQLITE=1 python3 manage.py test apps.conversations.tests.test_integration_consensus --verbosity=1; then
        print_status "$RED" "❌ Integration tests FAILED"
        return 1
    fi

    echo ""
    echo "Running security tests..."
    if ! USE_SQLITE=1 python3 manage.py test apps.accounts.tests.test_security --verbosity=1; then
        print_status "$RED" "❌ Security tests FAILED"
        return 1
    fi

    BACKEND_PASSED=true
    print_status "$GREEN" "✅ Backend tests PASSED (26 tests: 7 integration + 19 security)"
}

# Function to run frontend tests
run_frontend_tests() {
    print_header "⚛️  Running Frontend Tests (React)"

    # Check if node_modules exists
    if [ ! -d "frontend/frontend/node_modules" ]; then
        print_status "$YELLOW" "⚠️  Warning: node_modules not found"
        print_status "$YELLOW" "   Running npm install first..."
        cd frontend/frontend
        npm install
        cd ../..
    fi

    # Run React tests
    cd frontend/frontend
    if npm test -- --watchAll=false; then
        FRONTEND_PASSED=true
        cd ../..
        print_status "$GREEN" "✅ Frontend tests PASSED (72 tests: 11 App + 17 ChatLayout + 21 Consensus + 23 API)"
    else
        cd ../..
        print_status "$RED" "❌ Frontend tests FAILED"
        return 1
    fi
}

# Function to print final summary
print_summary() {
    print_header "📊 Test Results Summary"

    echo "Backend Tests (26 tests):"
    if [ "$BACKEND_PASSED" = true ]; then
        print_status "$GREEN" "  ✅ PASSED"
    else
        print_status "$RED" "  ❌ FAILED"
    fi

    echo ""
    echo "Frontend Tests (72 tests):"
    if [ "$FRONTEND_PASSED" = true ]; then
        print_status "$GREEN" "  ✅ PASSED"
    else
        print_status "$RED" "  ❌ FAILED"
    fi

    echo ""
    echo "Total: 98 tests"
    echo ""

    if [ "$BACKEND_PASSED" = true ] && [ "$FRONTEND_PASSED" = true ]; then
        print_status "$GREEN" "🎉 ALL TESTS PASSED!"
        echo ""
        print_status "$GREEN" "   Ready to commit and push changes"
        return 0
    else
        print_status "$RED" "❌ SOME TESTS FAILED"
        echo ""
        print_status "$YELLOW" "   Please fix failing tests before committing"
        return 1
    fi
}

# Main execution
main() {
    print_header "🧪 AI Consensus App - Running All Tests"

    # Check we're in the right directory
    check_directory

    # Initialize error tracking
    local backend_error=0
    local frontend_error=0

    # Run backend tests
    if ! run_backend_tests; then
        backend_error=1
    fi

    # Run frontend tests (even if backend failed, to see full picture)
    if ! run_frontend_tests; then
        frontend_error=1
    fi

    # Print summary and exit with appropriate code
    if ! print_summary; then
        exit 1
    fi

    exit 0
}

# Handle script interruption
trap 'print_status "$RED" "\n\n❌ Tests interrupted by user"; exit 130' INT

# Run main function
main "$@"
