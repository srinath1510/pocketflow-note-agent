#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}${BOLD}════════════════════════════════════════${NC}"
    echo -e "${BLUE}${BOLD}    🧠 BrowserBud - Setup Script    ${NC}"
    echo -e "${BLUE}${BOLD}════════════════════════════════════════${NC}"
    echo
}

print_step() {
    echo -e "${BLUE}${BOLD}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

check_prerequisites() {
    print_step "Checking prerequisites..."
    
    if ! command_exists python3; then
        print_error "Python 3 is required but not installed."
        echo "Please install Python 3.9+ and try again."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    python_major=$(echo $python_version | cut -d. -f1)
    python_minor=$(echo $python_version | cut -d. -f2)
    
    if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 9 ]); then
        print_error "Python 3.9+ is required. Found: $python_version"
        exit 1
    fi
    
    print_success "Python $python_version found"
    
    if ! command_exists pip3; then
        print_warning "pip3 not found, trying pip..."
        if ! command_exists pip; then
            print_error "pip is required but not installed."
            exit 1
        fi
        PIP_CMD="pip"
    else
        PIP_CMD="pip3"
    fi
    
    print_success "pip found"
    
    if command_exists docker; then
        print_success "Docker found"
        DOCKER_AVAILABLE=true
    else
        print_warning "Docker not found. You'll need to install Neo4j manually."
        DOCKER_AVAILABLE=false
    fi
}

setup_venv() {
    print_step "Setting up Python virtual environment..."
    
    if [ -d "venv" ]; then
        print_info "Virtual environment already exists. Removing old one..."
        rm -rf venv
    fi
    
    python3 -m venv venv
    source venv/bin/activate
    python -m pip install --upgrade pip
    
    print_success "Virtual environment created and activated"
}

install_dependencies() {
    print_step "Installing Python dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found!"
        exit 1
    fi
    
    pip install -r requirements.txt
    
    print_success "Dependencies installed"
}

setup_env_file() {
    print_step "Setting up environment configuration..."
    
    if [ -f ".env" ]; then
        print_warning "Existing .env file found. Creating backup..."
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    if [ ! -f ".env.example" ]; then
        print_error ".env.example not found!"
        exit 1
    fi
    
    cp .env.example .env
    
    print_success "Environment file created from template"
    print_info "You'll need to edit .env with your actual credentials"
}

setup_neo4j() {
    if [ "$DOCKER_AVAILABLE" = true ]; then
        print_step "Setting up Neo4j database with Docker..."
        
        if docker ps -a | grep -q "browserbud_neo4j"; then
            print_info "Existing Neo4j container found. Stopping and removing..."
            docker stop browserbud_neo4j >/dev/null 2>&1 || true
            docker rm browserbud_neo4j >/dev/null 2>&1 || true
        fi
        
        if docker-compose up -d neo4j; then
            print_success "Neo4j started with Docker Compose"
            print_info "Neo4j will be available at: http://localhost:7474"
            print_info "Default credentials: neo4j / (set NEO4J_PASSWORD in .env)"
        else
            print_warning "Docker Compose failed. Trying direct Docker command..."
            
            docker run -d \
                --name browserbud_neo4j \
                -p 7474:7474 -p 7687:7687 \
                -e NEO4J_AUTH=neo4j/smartnotes123 \
                -e NEO4J_PLUGINS='["apoc"]' \
                -v "$(pwd)/data/neo4j/data:/data" \
                -v "$(pwd)/data/neo4j/logs:/logs" \
                -v "$(pwd)/data/neo4j/import:/var/lib/neo4j/import" \
                -v "$(pwd)/data/neo4j/plugins:/plugins" \
                neo4j:5-community
                
            if [ $? -eq 0 ]; then
                print_success "Neo4j started with Docker"
                print_warning "Remember to set NEO4J_PASSWORD=smartnotes123 in your .env file"
            else
                print_error "Failed to start Neo4j. You'll need to set it up manually."
            fi
        fi
    else
        print_warning "Docker not available. Please install Neo4j manually:"
        echo "  1. Download Neo4j from: https://neo4j.com/download/"
        echo "  2. Start Neo4j service"
        echo "  3. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in .env"
    fi
}

create_directories() {
    print_step "Creating data directories..."
    
    directories=(
        "data"
        "data/notes"
        "data/batches" 
        "data/results"
        "data/temp"
        "data/neo4j/data"
        "data/neo4j/logs"
        "data/neo4j/import"
        "data/neo4j/plugins"
        "logs"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
    done
    
    print_success "Data directories created"
}

test_installation() {
    print_step "Testing installation..."
    
    if python -c "import anthropic, neo4j, fastapi, uvicorn; print('Core imports successful')" 2>/dev/null; then
        print_success "Core Python packages imported successfully"
    else
        print_error "Some core packages failed to import"
        return 1
    fi
    
    if python -c "from config.pipeline_config import PipelineConfig" 2>/dev/null; then
        print_success "Configuration module loads correctly"
    else
        print_error "Configuration module failed to load"
        return 1
    fi
    
    print_success "Installation test passed"
}

generate_summary() {
    print_step "Setup Summary"
    echo
    echo -e "${GREEN}${BOLD}🎉 Setup Complete!${NC}"
    echo
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Edit your .env file with actual credentials:"
    echo "   ${YELLOW}nano .env${NC}"
    echo
    echo "2. Required environment variables:"
    echo "   • ${BOLD}ANTHROPIC_API_KEY${NC}: Get from https://console.anthropic.com/"
    echo "   • ${BOLD}NOTION_TOKEN${NC}: Create integration at https://www.notion.so/my-integrations"
    echo "   • ${BOLD}NEO4J_PASSWORD${NC}: Set a secure password for Neo4j"
    echo
    echo "3. Start the services:"
    echo "   ${BLUE}# Start Neo4j (if using Docker):${NC}"
    echo "   docker-compose up -d neo4j"
    echo
    echo "   ${BLUE}# Activate virtual environment:${NC}"
    echo "   source venv/bin/activate"
    echo
    echo "   ${BLUE}# Start the API server:${NC}"
    echo "   python start_fastapi.py"
    echo
    echo "4. Test the installation:"
    echo "   ${BLUE}# Run pipeline tests:${NC}"
    echo "   python test_pipeline_no_api.py"
    echo
    echo -e "${GREEN}📚 Documentation: See README.md for detailed usage instructions${NC}"
    echo -e "${GREEN}🐛 Issues: Report at https://github.com/your-repo/issues${NC}"
    echo
}

main() {
    print_header
    
    check_prerequisites
    create_directories
    setup_venv
    install_dependencies
    setup_env_file
    setup_neo4j
    
    if test_installation; then
        generate_summary
        exit 0
    else
        print_error "Installation test failed. Please check the errors above."
        exit 1
    fi
}

trap 'echo -e "\n${YELLOW}Setup interrupted by user${NC}"; exit 130' INT

main "$@"