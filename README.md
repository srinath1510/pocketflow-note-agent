# 🧠 Smart Notes AI - AI-Powered Learning Companion

**Transform chaotic web browsing into organized, connected knowledge with beautiful Notion notes.**

Smart Notes AI is an intelligent learning system that, when paired with the Smart Notes Chrome extension, captures your web research, analyzes it with AI, builds knowledge connections, and generates beautiful structured notes in Notion automatically.

## 🌟 Overview

Smart Notes AI consists of a **Chrome Extension** + **AI Pipeline** that turns scattered learning into organized knowledge:

1. **📥 Capture**: Chrome extension saves interesting content with context
2. **🧠 Analyze**: AI extracts concepts, entities, and learning patterns  
3. **🕸️ Connect**: Builds knowledge graph connecting new learning to existing knowledge
4. **🔗 History**: Identifies knowledge gaps and suggests reviews using spaced repetition
5. **📄 Generate**: Creates beautiful, structured Notion pages with actionable insights

## ✨ Key Features

### 🎯 **Intelligent Learning Analysis**
- **Concept Extraction**: AI identifies key learning concepts and terminology
- **Content Classification**: Automatically categorizes research papers, documentation, tutorials
- **Complexity Assessment**: Evaluates knowledge level (basic → advanced)
- **Learning Intent Detection**: Understands your learning goals and patterns

### 🕸️ **Knowledge Graph & Connections**
- **Neo4j Knowledge Graph**: Persistent storage of concepts and relationships
- **Historical Connections**: Links new learning to your existing knowledge base
- **Knowledge Gap Detection**: Identifies missing prerequisites and foundational concepts
- **Learning Pathways**: Suggests optimal order for learning complex topics

### 📄 **Beautiful Notion Integration**
- **Rich Session Pages**: Formatted learning sessions with emojis and structure
- **Connected Databases**: Concepts, Sources, and Sessions with cross-references
- **Actionable Todos**: Knowledge gaps and recommendations as checkable tasks
- **Mobile Accessible**: Review and organize learning anywhere via Notion mobile

### 🔄 **Spaced Repetition & Review**
- **Forgetting Curve Analysis**: Identifies concepts needing review
- **Smart Recommendations**: Prioritized next steps based on learning patterns
- **Progress Tracking**: Visual confidence levels and mastery indicators

## 🏗️ Architecture

### **5-Node AI Pipeline**
```
📥 Capture Ingestion → 🧠 Content Analysis → 🕸️ Knowledge Graph → 🔗 Historical Retrieval → 📄 Notion Generation
```

1. **Capture Ingestion**: Validates and normalizes browser capture data
2. **Content Analysis**: LLM-powered concept extraction and semantic analysis
3. **Knowledge Graph**: Builds persistent Neo4j graph of concepts and relationships
4. **Historical Knowledge**: Connects new learning to existing knowledge, finds gaps
5. **Notion Generation**: Creates beautiful, structured notes with rich formatting

### **Technology Stack**
- **Backend**: Python Flask API with PocketFlow pipeline framework
- **AI/LLM**: Anthropic Claude for concept extraction and analysis
- **Database**: Neo4j for knowledge graph storage
- **Frontend**: Chrome Extension (capture interface)
- **Notes**: Notion API for rich note generation
- **Infrastructure**: Docker for Neo4j, environment-based configuration

## 🚀 Quick Start

### **Prerequisites**
- Python 3.9+
- Neo4j database (Docker recommended)
- Notion workspace and integration
- Anthropic API key (for AI analysis)

### **1. Installation**
```bash
# Clone repository
git clone https://github.com/your-username/smart-notes-ai
cd smart-notes-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Environment Setup**
Create `.env` file:
```bash
# Required: AI Analysis
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Required: Notion Integration  
NOTION_TOKEN=secret_your-notion-token-here

# Required: Neo4j Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=smartnotes123

# Optional: Notion Organization
NOTION_PARENT_PAGE_ID=your-page-id
NOTION_DATABASE_ID=existing-database-id
```

### **3. Start Services**
```bash
# Start Neo4j (Docker)
docker run --name neo4j-smartnotes \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/smartnotes123 \
  -d neo4j:latest

# Start Flask API server
python flask_server.py
```

### **4. Test the Pipeline**
```bash
# Test with sample data
python main.py --sample --verbose

# Test through API
curl -X POST http://localhost:8000/api/bake \
  -H "Content-Type: application/json" \
  -d '{"bake_id": "test_session"}'
```

## 🎯 Usage

### **Basic Workflow**

1. **Capture Learning Content**
   - Use Chrome extension to save interesting content
   - System captures context, highlights, and metadata

2. **Trigger AI Analysis**
   - Click "Bake" in extension or call API endpoint
   - AI pipeline processes all captured content

3. **Review Notion Notes**
   - Open generated Notion page for rich, formatted results
   - Follow actionable recommendations and todos

4. **Build Knowledge Over Time**
   - Subsequent sessions connect to previous learning
   - Knowledge gaps and review suggestions improve learning efficiency

### **API Endpoints**

#### **Capture Notes**
```bash
POST /api/notes/batch
{
  "batch_id": "session_123",
  "notes": [
    {
      "content": "HTML content",
      "url": "https://example.com",
      "metadata": {"content_category": "research_paper"}
    }
  ]
}
```

#### **Trigger Analysis**
```bash
POST /api/bake
{
  "bake_id": "session_123",
  "includeAdditionalNotes": false
}
```

#### **Get Results**
```bash
GET /api/results
# Returns processed sessions with Notion URLs
```

## 📊 Sample Output

### **Console Output**
```
🧠 CONTENT ANALYSIS:
   Learning Concepts: 12
   Session Theme: Machine Learning Fundamentals
   Top Concepts: Neural Networks, Backpropagation, Deep Learning

🕸️ KNOWLEDGE GRAPH:
   Concepts: 12 nodes, Relationships: 8
   Graph Density: 0.45

🔗 HISTORICAL KNOWLEDGE:
   Connections Found: 5
   Knowledge Gaps: 2 (Linear Algebra, Statistics)
   Recommendations: 4 high-priority actions

📄 NOTION GENERATION:
   Session Page: ✅ https://notion.so/Learning-Session-ML-abc123
   Total Pages: 17
```

### **Notion Page Structure (Example)**
```
🧠 Learning Session - Machine Learning Fundamentals
├── 💡 Key Concepts Learned
│   • Neural Network Architecture
│   • Backpropagation Algorithm
│   • Gradient Descent Optimization
├── 🔗 Historical Connections
│   → Connected to "Statistics" (learned 2 weeks ago)
│   → Builds upon "Linear Algebra" concepts
├── ⚠️ Knowledge Gaps Identified
│   🔥 Linear Algebra - Study matrix operations
│   ⚡ Calculus - Review derivatives
├── ✅ Next Steps
│   ☐ 🔥 Study linear algebra before neural networks
│   ☐ ⚡ Review matrix multiplication examples
│   ☐ 📝 Practice backpropagation by hand
└── 📚 Captured Sources
    → Stanford CS229 Lecture Notes
    → 3Blue1Brown Neural Networks Video
```

## 🔧 Configuration

### **Pipeline Configuration**
Customize pipeline behavior in `config/pipeline_config.py`:
- LLM provider and model selection
- Knowledge graph connection parameters
- Logging levels and output formats

### **Notion Customization**
- **Database Schemas**: Modify properties and relationships
- **Page Templates**: Customize formatting and content structure
- **Emoji Mappings**: Change visual indicators and priorities

### **Knowledge Graph Tuning**
- **Connection Thresholds**: Adjust similarity requirements
- **Relationship Types**: Define semantic relationship categories
- **Confidence Scoring**: Tune mastery level calculations

## 🧪 Testing

### **Unit Tests**
```bash
# Run comprehensive test suite (no API credits required)
python test_no_api.py

# Test specific components
python main.py --node content_analysis --sample --verbose
```

### **Integration Tests**
```bash
# Test full pipeline
python main.py --input test_data.json --verbose

# Test API endpoints
curl -X GET http://localhost:8000/api/health
```

### **Manual Testing**
```bash
# Test individual components
python -c "from nodes.notion_note_generation import test_notion_connection; test_notion_connection()"
```

## 📈 Roadmap

### **Phase 1: Core Pipeline** ✅
- [x] Capture ingestion and validation
- [x] LLM-powered content analysis
- [x] Neo4j knowledge graph construction
- [x] Historical knowledge retrieval
- [x] Notion note generation

### **Phase 2: Enhanced Features** 🚧
- [ ] Spaced repetition scheduling
- [ ] Advanced learning analytics
- [ ] Multi-format export (PDF, Anki, Markdown)
- [ ] Team collaboration features

### **Phase 3: Advanced AI** 🔮
- [ ] Personalized learning recommendations
- [ ] Automatic curriculum generation
- [ ] Voice note integration
- [ ] Real-time learning coaching

## 🤝 Contributing

### **Development Setup**
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Pre-commit hooks
pre-commit install

# Run tests
python -m pytest tests/
```

### **Architecture Guidelines**
- **Node-based Design**: Each pipeline stage is an independent, testable node
- **Error Resilience**: Graceful degradation when services unavailable
- **Configurable**: Environment-based configuration for different deployments
- **Observable**: Comprehensive logging and metrics

## 📜 License

MIT License - see [LICENSE](LICENSE.md) file for details.

## 🙏 Acknowledgments

- **PocketFlow**: Pipeline framework for node-based processing
- **Anthropic**: Claude LLM for intelligent content analysis
- **Neo4j**: Graph database for knowledge relationship storage
- **Notion**: Beautiful note-taking platform and API

## 🔗 Links

- **Documentation**: [docs/](docs/)
- **Chrome Extension**: [extension/](extension/)
- **Example Configs**: [examples/](examples/)
- **Troubleshooting**: [docs/troubleshooting.md](docs/troubleshooting.md)

---

**Transform your learning journey with AI-powered knowledge management.** 🧠✨

*Built for lifelong learners and knowledge builders.*