# Mini-Guru PDF Q&A

A full-stack AI application that allows users to upload PDF documents, ask natural-language questions, and receive GPT-generated answers with page-level citations.

## 🚀 Quick Start

### One-Command Setup

```bash
# Clone the repository
git clone <repository-url>
cd mini-guru-pdf-qa

# Start the application
make dev
```

Then open [http://localhost:3000](http://localhost:3000) in your browser.

## 🔧 Configuration

### Environment Variables

1. Copy the example environment file:
```bash
cp env.example .env
```

2. Edit `.env` and add your OpenAI API key:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Required Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `CHUNK_SIZE` | Token size for text chunks | 400 |
| `CHUNK_OVERLAP` | Token overlap between chunks | 50 |
| `OPENAI_LLM_MODEL` | LLM model for answers | gpt-4o-mini |
| `OPENAI_EMBEDDING_MODEL` | Embedding model | text-embedding-3-small |
| `OPENAI_MAX_ANSWER_TOKENS` | Max tokens for answers | 500 |

## 🏗️ Architecture

### Backend (Django 5)
- **Framework**: Django 5 with Django REST Framework
- **Database**: PostgreSQL
- **Vector Store**: Qdrant
- **PDF Processing**: PyMuPDF
- **AI Pipeline**: LangChain + OpenAI
- **Server**: Gunicorn

### Frontend (Next.js 14)
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: SWR for data fetching
- **PDF Viewer**: PDF.js

### Containers
- **web**: Django backend
- **frontend**: Next.js development server
- **postgres**: PostgreSQL database
- **vector**: Qdrant vector database

## 📋 Features

### ✅ Implemented
- **PDF Upload**: Drag & drop multiple PDFs (max 15MB each)
- **Progress Tracking**: Per-file upload progress
- **PDF Processing**: Text extraction, chunking, embedding
- **Vector Search**: Semantic search with Qdrant
- **Q&A Interface**: Natural language questions with citations
- **Streaming Responses**: Real-time answer generation
- **Chat History**: Session-based conversation history
- **Citation System**: Page-level citations with PDF viewer
- **Follow-up Questions**: Context-aware conversations

### 🎯 Core Requirements Met
- ✅ Upload: Drag & drop, progress bars, file validation
- ✅ Ingest: PDF parsing, chunking, embeddings, vector storage
- ✅ Ask: Natural language questions with streaming responses
- ✅ Answer: Markdown rendering with citation badges
- ✅ History: Chat session management

## 🔌 API Contract

### Upload Endpoints

#### `POST /api/documents/upload/`
Upload a PDF document

**Request:**
```json
{
  "file": "multipart/form-data"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "document.pdf",
  "size": 1024000,
  "uploaded_at": "2024-01-01T12:00:00Z",
  "processing_status": "pending"
}
```

### Chat Endpoints

#### `POST /api/chat/ask/`
Ask a question about uploaded documents

**Request:**
```json
{
  "question": "What is the main topic?",
  "session_id": "uuid (optional)",
  "document_ids": ["uuid1", "uuid2"],
  "stream": true
}
```

**Response (Streaming):**
```json
{
  "answer": "The main topic is...",
  "citations": [
    {
      "chunk_id": "uuid",
      "page_start": 1,
      "page_end": 2,
      "relevance_score": 0.95
    }
  ]
}
```

#### `GET /api/chat/sessions/`
Get chat sessions

#### `GET /api/chat/sessions/{id}/messages/`
Get messages for a session

### Document Endpoints

#### `GET /api/documents/`
List uploaded documents

#### `GET /api/documents/{id}/`
Get document details

## 🛠️ Development

### Prerequisites
- Docker and Docker Compose
- Make (optional, for convenience commands)

### Available Commands

```bash
# Development
make dev              # Start all services
make build            # Build containers
make stop             # Stop all services
make clean            # Clean everything

# Database
make migrate          # Run Django migrations
make db-reset         # Reset database
make db-backup        # Backup database

# Development helpers
make shell            # Django shell
make logs             # View all logs
make frontend-logs    # Frontend logs only
make backend-logs     # Backend logs only
```

### Project Structure

```
mini-guru-pdf-qa/
├── backend/                 # Django backend
│   ├── apps/
│   │   ├── core/           # Core models
│   │   ├── pdf_processor/  # PDF processing
│   │   ├── chat/           # Chat functionality
│   │   └── vector_store/   # Vector operations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # Next.js frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── lib/           # Utilities
│   │   └── types/         # TypeScript types
│   └── package.json
├── docker-compose.yml
├── Makefile
└── README.md
```

## 🚀 Deployment

### Production Setup

1. Set production environment variables
2. Build production images:
```bash
docker-compose -f docker-compose.prod.yml build
```

3. Run with production settings:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 🔮 Future Enhancements

### Planned Features
- [ ] OAuth authentication (Google, GitHub)
- [ ] Dark mode toggle
- [ ] Advanced PDF viewer with annotations
- [ ] Export chat conversations
- [ ] Batch document processing
- [ ] Custom embedding models
- [ ] Reranker for improved citations

### Performance Optimizations
- [ ] Redis caching layer
- [ ] CDN for static files
- [ ] Database connection pooling
- [ ] Async PDF processing
- [ ] Vector search optimization

### Developer Experience
- [ ] CI/CD with GitHub Actions
- [ ] Automated testing
- [ ] Code quality checks
- [ ] API documentation with Swagger
- [ ] Development environment improvements

## 🐛 Known Limitations

1. **File Size**: Maximum 15MB per PDF file
2. **Processing Time**: Large PDFs may take time to process
3. **Memory Usage**: Vector operations can be memory-intensive
4. **Concurrent Users**: Limited by OpenAI API rate limits
5. **PDF Quality**: Text extraction depends on PDF quality

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- OpenAI for GPT models and embeddings
- Qdrant for vector database
- PyMuPDF for PDF processing
- Next.js and Django communities 