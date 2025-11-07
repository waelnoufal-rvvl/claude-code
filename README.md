# Mistral Output Separation with n8n and Qdrant

This project provides a complete workflow for processing Mistral AI output, separating content into text, tables, and figures, and storing each type separately in Qdrant vector database.

## Overview

The workflow processes Mistral AI responses that may contain:
- **Text**: Regular paragraphs and content
- **Tables**: Structured data in markdown or HTML tables
- **Figures**: Images, charts, diagrams (as URLs or base64)

Each content type is stored in separate Qdrant collections for optimized retrieval and semantic search.

## Architecture

```
Mistral AI Output
       ↓
   [n8n Workflow]
       ↓
   Content Parser
       ↓
   ┌─────┴─────┬─────────┐
   ↓           ↓         ↓
 Text      Tables    Figures
   ↓           ↓         ↓
Qdrant     Qdrant    Qdrant
(text)    (tables)  (figures)
```

## Prerequisites

1. **n8n** - Workflow automation platform
   - Self-hosted or n8n cloud
   - Version 1.0+ recommended

2. **Mistral AI** - API access
   - API key from Mistral AI
   - Model: mistral-large or mistral-medium

3. **Qdrant** - Vector database
   - Self-hosted or Qdrant Cloud
   - API key (if using cloud)

## Quick Start

### Step 1: Set up Qdrant Collections

Create three separate collections in Qdrant:

```bash
# Create collection for text
curl -X PUT 'http://localhost:6333/collections/mistral_text' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'

# Create collection for tables
curl -X PUT 'http://localhost:6333/collections/mistral_tables' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'

# Create collection for figures
curl -X PUT 'http://localhost:6333/collections/mistral_figures' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

### Step 2: Configure n8n Credentials

In n8n, add the following credentials:

1. **Mistral AI Credentials**
   - Credential Type: HTTP Request (or custom Mistral node if available)
   - API Key: Your Mistral API key
   - Base URL: https://api.mistral.ai/v1

2. **Qdrant Credentials**
   - Credential Type: HTTP Request
   - API Key: Your Qdrant API key (if using cloud)
   - Base URL: Your Qdrant instance URL

### Step 3: Import n8n Workflow

1. Open n8n interface
2. Go to Workflows → Import from File
3. Import `workflows/mistral-qdrant-separation.json`
4. Connect your credentials
5. Activate the workflow

## Workflow Steps

The n8n workflow performs the following operations:

### 1. Receive Mistral Output
- Trigger: Webhook, Schedule, or Manual trigger
- Input: Mistral AI response (text/markdown format)

### 2. Parse and Separate Content
- Extract text paragraphs
- Identify and extract tables (markdown/HTML)
- Identify and extract figures (image URLs, base64)

### 3. Generate Embeddings
- Use Mistral Embeddings API for each content piece
- Model: mistral-embed

### 4. Store in Qdrant
- Store text chunks in `mistral_text` collection
- Store tables in `mistral_tables` collection
- Store figures metadata in `mistral_figures` collection

## Content Separation Logic

### Text Detection
- Regular paragraphs
- Headings
- Lists (bullet and numbered)
- Excludes tables and figure references

### Table Detection
Supports multiple formats:
- Markdown tables (pipe-delimited)
- HTML tables (`<table>` tags)
- CSV-like structures

Example patterns:
```
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
```

### Figure Detection
Supports multiple formats:
- Markdown images: `![alt](url)`
- HTML images: `<img src="url">`
- Base64 encoded images
- Figure references with URLs

## Data Storage Schema

### Text Collection (mistral_text)
```json
{
  "id": "uuid",
  "vector": [1024 dimensions],
  "payload": {
    "content": "The actual text content",
    "type": "text",
    "source": "mistral",
    "timestamp": "2025-11-07T00:00:00Z",
    "metadata": {
      "model": "mistral-large",
      "chunk_index": 0
    }
  }
}
```

### Table Collection (mistral_tables)
```json
{
  "id": "uuid",
  "vector": [1024 dimensions],
  "payload": {
    "content": "Table in markdown/HTML format",
    "type": "table",
    "source": "mistral",
    "timestamp": "2025-11-07T00:00:00Z",
    "metadata": {
      "rows": 10,
      "columns": 5,
      "headers": ["Col1", "Col2", "Col3", "Col4", "Col5"]
    }
  }
}
```

### Figure Collection (mistral_figures)
```json
{
  "id": "uuid",
  "vector": [1024 dimensions],
  "payload": {
    "content": "Figure description or alt text",
    "image_url": "https://example.com/image.png",
    "type": "figure",
    "source": "mistral",
    "timestamp": "2025-11-07T00:00:00Z",
    "metadata": {
      "format": "png",
      "alt_text": "Description of the figure",
      "size": "1024x768"
    }
  }
}
```

## Usage Examples

### Example 1: Process Mistral Response

Input to n8n workflow:
```json
{
  "mistral_response": "Here is the analysis:\n\n# Overview\nThe data shows interesting trends.\n\n| Year | Revenue | Growth |\n|------|---------|--------|\n| 2023 | $1M | 20% |\n| 2024 | $1.2M | 20% |\n\n![Chart](https://example.com/chart.png)\n\nConclusion: Strong performance."
}
```

Result:
- 3 items in `mistral_text` (Overview paragraph, Conclusion)
- 1 item in `mistral_tables` (Revenue table)
- 1 item in `mistral_figures` (Chart image)

### Example 2: Query by Content Type

Search for tables only:
```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

results = client.search(
    collection_name="mistral_tables",
    query_vector=embedding,
    limit=5
)
```

## Advanced Configuration

### Custom Content Filters

Edit `scripts/content_parser.js` to add custom detection rules:

```javascript
const customPatterns = {
  code_blocks: /```[\s\S]*?```/g,
  equations: /\$\$[\s\S]*?\$\$/g,
  citations: /\[@[\w\s,]+\]/g
};
```

### Embedding Model Options

Mistral Embeddings API options:
- `mistral-embed`: 1024 dimensions (default)
- Adjust `size` in Qdrant collections accordingly

### Batch Processing

For large documents:
1. Split Mistral output into chunks
2. Process each chunk through the workflow
3. Maintain chunk relationships in metadata

## Error Handling and Logging

The workflow includes comprehensive error handling and logging capabilities:

### Error Handling Features

1. **Environment Variable Validation**
   - Validates `QDRANT_URL` is set before processing
   - Validates input data contains `mistral_response`
   - Returns HTTP 500 with clear error message if validation fails

2. **Content Parser Error Handling**
   - Catches JavaScript execution errors in content parsing
   - Logs parse errors with full context
   - Provides detailed error response

3. **API Call Error Handling**
   - All Mistral API calls include:
     - Automatic retry (3 attempts with 1-second intervals)
     - 30-second timeout
     - Graceful failure handling
   - All Qdrant API calls include:
     - Automatic retry (3 attempts with 1-second intervals)
     - 30-second timeout
     - Graceful failure handling

### Logging System

The workflow includes two types of loggers:

1. **Error Logger** (`workflows/mistral-qdrant-separation.json:484-493`)
   - Captures all error types (validation, parsing, API failures)
   - Logs to n8n console with `[ERROR LOG]` prefix
   - Includes execution ID for tracing
   - Returns HTTP 500 response to webhook caller

2. **Success Logger** (`workflows/mistral-qdrant-separation.json:508-517`)
   - Logs successful operations
   - Includes processing statistics
   - Logs to n8n console with `[INFO LOG]` prefix
   - Returns HTTP 200 response with stats

### Error Response Format

Error responses follow this structure:
```json
{
  "success": false,
  "error": {
    "type": "validation_error|parser_error|api_error",
    "message": "Detailed error message",
    "timestamp": "2025-11-07T12:34:56.789Z"
  }
}
```

Success responses include:
```json
{
  "success": true,
  "message": "Content processed and stored successfully",
  "stats": {
    "text_chunks": 5,
    "tables": 2,
    "figures": 1
  },
  "timestamp": "2025-11-07T12:34:56.789Z"
}
```

### Viewing Logs

Logs can be viewed in multiple ways:

1. **n8n Web Interface**
   - Open the workflow execution
   - Check the execution log for console output
   - Look for `[ERROR LOG]` or `[INFO LOG]` prefixes

2. **n8n Server Logs**
   - Check your n8n server console/logs
   - All errors and successes are logged there

3. **External Logging** (Optional)
   - Modify the Error Logger and Success Logger nodes
   - Add HTTP Request nodes to send logs to external services
   - Examples: Datadog, Splunk, CloudWatch, or custom logging endpoints

## Troubleshooting

### Issue: Missing environment variable QDRANT_URL
- **Error**: `validation_error: Missing QDRANT_URL environment variable`
- **Solution**: Set the `QDRANT_URL` environment variable in n8n settings
- Example: `QDRANT_URL=https://your-qdrant-instance.com:6333`

### Issue: Missing input data
- **Error**: `validation_error: Missing or empty mistral_response in request body`
- **Solution**: Ensure your webhook POST request includes `mistral_response` field
- Example payload:
```json
{
  "mistral_response": "Your Mistral AI output text here..."
}
```

### Issue: Mistral API authentication failed
- **Error**: `api_error: API Request Failed` with status code 401/403
- **Solution**:
  - Verify your Mistral API credentials in n8n
  - Check API key is valid and has proper permissions
  - Ensure credentials are attached to all Mistral embedding nodes

### Issue: Qdrant connection failed
- **Error**: `api_error: API Request Failed` when storing data
- **Solution**:
  - Verify Qdrant URL is correct and accessible
  - Check Qdrant API credentials
  - Ensure collections exist (`mistral_text`, `mistral_tables`, `mistral_figures`)
  - Check network connectivity between n8n and Qdrant

### Issue: Tables not detected
- Check table format (must have proper markdown pipes or HTML tags)
- Verify regex patterns in Content Parser node

### Issue: Vector dimensions mismatch
- Ensure Qdrant collection size matches embedding model output
- Mistral-embed produces 1024-dimensional vectors

### Issue: API rate limiting
- Mistral API calls include retry logic (3 attempts)
- If rate limited, increase retry intervals in HTTP Request node options
- Consider implementing exponential backoff

## API Reference

### Mistral AI API
- Docs: https://docs.mistral.ai/
- Embeddings: `POST /v1/embeddings`
- Chat: `POST /v1/chat/completions`

### Qdrant API
- Docs: https://qdrant.tech/documentation/
- Upsert: `PUT /collections/{collection}/points`
- Search: `POST /collections/{collection}/points/search`

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check n8n community forums
- Refer to Mistral and Qdrant documentation
