# DoqToq API Documentation

## Overview

DoqToq provides both a web interface and a programmatic API for integrating document conversation capabilities into your applications.

## Installation

```bash
# Install from PyPI (when available)
pip install doqtoq

# Or install from source
git clone https://github.com/shre-db/doqtoq.git
cd doqtoq
pip install -e .
```

## Quick Start

### Basic Usage

```python
from doqtoq import DocumentRAG

# Initialize with a document
rag = DocumentRAG(
    file_path="path/to/your/document.pdf",
    model_provider="google",  # or "mistral", "ollama"
    temperature=0.7
)

# Ask questions
response = rag.query("What is the main topic of this document?")
print(response)
```

### Streaming Responses

```python
# Enable streaming for real-time responses
rag = DocumentRAG(
    file_path="document.pdf",
    model_provider="google",
    streaming=True
)

# Stream responses
for chunk in rag.stream_query("Summarize the key points"):
    print(chunk, end="", flush=True)
```

## Core Classes

### DocumentRAG

The main class for document conversation functionality.

#### Constructor

```python
DocumentRAG(
    file_path: str,
    model_provider: Literal["google", "mistral", "ollama"] = "google",
    temperature: float = 0.7,
    top_k: int = 4,
    embedding_provider: str = "huggingface",
    embedding_model: str = "all-MiniLM-L6-v2",
    streaming: bool = False
)
```

**Parameters:**
- `file_path`: Path to the document file (PDF, TXT, JSON, MD)
- `model_provider`: LLM provider to use
- `temperature`: Creativity level (0.0-1.0)
- `top_k`: Number of relevant chunks to retrieve
- `embedding_provider`: Embedding model provider
- `embedding_model`: Specific embedding model name
- `streaming`: Enable streaming responses

#### Methods

##### `query(question: str) -> str`

Ask a question and get a complete response.

```python
response = rag.query("What are the main conclusions?")
```

##### `stream_query(question: str) -> Iterator[str]`

Ask a question and get streaming response chunks.

```python
for chunk in rag.stream_query("Explain the methodology"):
    print(chunk, end="")
```

##### `get_similarity_metrics(question: str) -> Dict[str, float]`

Get relevance metrics for a question.

```python
metrics = rag.get_similarity_metrics("Is this question relevant?")
print(f"Similarity score: {metrics['similarity_score']}")
```

##### `reset_conversation()`

Clear conversation history.

```python
rag.reset_conversation()
```

## Configuration

### Environment Variables

Create a `.env` file with your API keys:

```env
GOOGLE_API_KEY=your_google_api_key_here
MISTRAL_API_KEY=your_mistral_api_key_here
```

### Model Providers

#### Google Gemini

```python
rag = DocumentRAG(
    file_path="document.pdf",
    model_provider="google",
    temperature=0.7
)
```

**Required:** `GOOGLE_API_KEY` environment variable

#### Mistral AI

```python
rag = DocumentRAG(
    file_path="document.pdf",
    model_provider="mistral",
    temperature=0.7
)
```

**Required:** `MISTRAL_API_KEY` environment variable

#### Ollama (Local)

```python
rag = DocumentRAG(
    file_path="document.pdf",
    model_provider="ollama",
    temperature=0.7
)
```

**Required:** Ollama running locally with a model installed

### Embedding Models

#### HuggingFace (Default)

```python
rag = DocumentRAG(
    file_path="document.pdf",
    embedding_provider="huggingface",
    embedding_model="all-MiniLM-L6-v2"  # Default
)
```

Available models:
- `all-MiniLM-L6-v2` (fast, good quality)
- `all-mpnet-base-v2` (slower, better quality)

## Advanced Usage

### Custom Configuration

```python
from doqtoq import DocumentRAG
from doqtoq.backend.embedder import get_embedding_model

# Custom embedding model
embedding_model = get_embedding_model("huggingface", "all-mpnet-base-v2")

rag = DocumentRAG(
    file_path="document.pdf",
    model_provider="google",
    temperature=0.3,  # More focused responses
    top_k=6,          # More context
    streaming=True
)
```

### Batch Processing

```python
documents = ["doc1.pdf", "doc2.txt", "doc3.md"]
rags = []

for doc_path in documents:
    rag = DocumentRAG(file_path=doc_path)
    rags.append(rag)

# Ask the same question to all documents
question = "What is this document about?"
for i, rag in enumerate(rags):
    print(f"Document {i+1}: {rag.query(question)}")
```

### Error Handling

```python
from doqtoq import DocumentRAG
from doqtoq.exceptions import DocumentProcessingError, QueryError

try:
    rag = DocumentRAG(file_path="document.pdf")
    response = rag.query("Your question here")
except DocumentProcessingError as e:
    print(f"Failed to process document: {e}")
except QueryError as e:
    print(f"Query failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Supported File Formats

| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Full text extraction |
| Text | `.txt` | Plain text files |
| Markdown | `.md` | Markdown formatting preserved |
| JSON | `.json` | Structured data support |

## Performance Optimization

### Memory Management

```python
# For large documents, use smaller chunk sizes
rag = DocumentRAG(
    file_path="large_document.pdf",
    chunk_size=500,  # Smaller chunks
    chunk_overlap=50
)
```

### Caching

```python
# Enable vector store persistence
rag = DocumentRAG(
    file_path="document.pdf",
    persist_directory="./vector_cache"
)
```

## Integration Examples

### Flask API

```python
from flask import Flask, request, jsonify
from doqtoq import DocumentRAG

app = Flask(__name__)
rag_instances = {}

@app.route('/upload', methods=['POST'])
def upload_document():
    file = request.files['document']
    file_path = f"uploads/{file.filename}"
    file.save(file_path)

    rag = DocumentRAG(file_path=file_path)
    doc_id = str(hash(file_path))
    rag_instances[doc_id] = rag

    return jsonify({"document_id": doc_id})

@app.route('/query', methods=['POST'])
def query_document():
    data = request.json
    doc_id = data['document_id']
    question = data['question']

    if doc_id not in rag_instances:
        return jsonify({"error": "Document not found"}), 404

    rag = rag_instances[doc_id]
    response = rag.query(question)

    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True)
```

### Streamlit Integration

```python
import streamlit as st
from doqtoq import DocumentRAG

st.title("Document Chat")

uploaded_file = st.file_uploader("Upload a document")
if uploaded_file:
    # Save uploaded file
    with open(f"temp_{uploaded_file.name}", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Initialize RAG
    if 'rag' not in st.session_state:
        st.session_state.rag = DocumentRAG(f"temp_{uploaded_file.name}")

    # Chat interface
    question = st.text_input("Ask a question:")
    if question:
        response = st.session_state.rag.query(question)
        st.write(response)
```

## Troubleshooting

### Common Issues

1. **"Model not found" error**
   - Ensure API keys are set correctly
   - Check model availability in your region

2. **"Document processing failed"**
   - Verify file format is supported
   - Check file isn't corrupted or password-protected

3. **Slow responses**
   - Reduce `top_k` parameter
   - Use smaller embedding models
   - Enable streaming for better UX

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

rag = DocumentRAG(file_path="document.pdf", debug=True)
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.

## License

Apache License 2.0 - see [LICENSE.md](../LICENSE.md) for details.
