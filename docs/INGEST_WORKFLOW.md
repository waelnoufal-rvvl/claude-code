# Document Ingestion Workflow with Duplicate Detection

This workflow provides intelligent document ingestion with automatic duplicate detection and updating capabilities. It prevents duplicate documents in your vector database and ensures that updated documents replace old versions.

## Overview

The **Ingest & Vectorize Documents** workflow handles:
- Document upload via webhook
- Duplicate detection using file hash
- Content change detection using content hash
- Automatic deletion of old versions
- Document chunking for optimal embedding
- Vector embedding generation
- Storage in Qdrant collections

## Key Features

### 🔍 Duplicate Detection
- **File-based**: Uses SHA-256 hash of filename to identify documents
- **Content-based**: Detects if document content has changed
- **Smart Actions**:
  - `insert`: New document → Store normally
  - `update`: Existing document with changes → Delete old, store new
  - `skip`: Existing document unchanged → Skip processing

### 🔄 Update Handling
When a duplicate is detected with different content:
1. Query Qdrant for existing document chunks
2. Delete all old chunks (by file_hash)
3. Process and store updated version
4. Maintain consistent file_hash for tracking

### 🧩 Document Chunking
- Splits documents into manageable chunks (max 1000 chars)
- Preserves paragraph boundaries
- Each chunk includes:
  - Content
  - Position (chunk_index, total_chunks)
  - File metadata (filename, file_hash, content_hash)
  - Upload timestamp

### ✅ Error Handling
- Validation of inputs and environment variables
- Retry logic for all API calls (3 attempts)
- Graceful failure handling
- Detailed error logging
- Structured error responses

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Document Upload Webhook                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Validate Input & Environment Vars              │
└──────────────┬──────────────────────────────┬───────────────┘
               │ Valid                         │ Invalid
               ↓                               ↓
┌──────────────────────────┐      ┌──────────────────────────┐
│ Generate Document Hash   │      │  Validation Error → Log  │
│  - file_hash (filename)  │      └──────────────────────────┘
│  - content_hash (content)│
└──────────┬───────────────┘
           │
           ↓
┌─────────────────────────────────────────────────────────────┐
│         Check Existing Document in Qdrant (by hash)         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Analyze Duplicate Status                       │
│  - Compare content_hash                                     │
│  - Determine action (insert/update/skip)                    │
└──────────┬────────────────────────────┬─────────────────────┘
           │ Process                     │ Skip
           ↓                             ↓
    ┌──────────────┐          ┌─────────────────────┐
    │ Need Delete? │          │  Skip Response      │
    └──┬────────┬──┘          └─────────────────────┘
       │Yes     │No
       ↓        │
┌──────────────┐│
│ Delete Old   ││
│ Versions     ││
└──────┬───────┘│
       │        │
       └────┬───┘
            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Chunk Document                           │
│  Split into ~1000 char chunks, preserve paragraphs          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Split Chunks (Loop)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│           Generate Embedding (Mistral API)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              Store in Qdrant Collection                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                Success Logger → Response                    │
└─────────────────────────────────────────────────────────────┘
```

## Setup Instructions

### 1. Environment Variables

Set the following environment variable in n8n:

```bash
QDRANT_URL=https://your-qdrant-instance.com:6333
```

### 2. API Credentials

Configure these credentials in n8n:

1. **Mistral AI API**
   - Credential ID: `1`
   - Name: `Mistral AI API`
   - API Key: Your Mistral API key

2. **Qdrant API**
   - Credential ID: `2`
   - Name: `Qdrant API`
   - API URL: Your Qdrant instance URL
   - API Key: Your Qdrant API key (if required)

### 3. Qdrant Collection Setup

Create a collection for documents (or use custom collection name in request):

```bash
curl -X PUT 'http://localhost:6333/collections/documents' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

### 4. Import Workflow

1. Open n8n interface
2. Go to Workflows → Import from File
3. Import `workflows/ingest-vectorize-docs.json`
4. Connect your credentials
5. Activate the workflow

## Usage

### API Endpoint

Once activated, the workflow exposes a webhook endpoint:

```
POST /webhook/ingest-document
```

### Request Format

```json
{
  "filename": "example-document.txt",
  "document_content": "Your document content here...",
  "collection": "documents"
}
```

**Parameters:**
- `filename` (required): Name of the document (used for duplicate detection)
- `document_content` (required): The full text content of the document
- `collection` (optional): Qdrant collection name (defaults to "documents")

### Response Formats

#### Success - New Document
```json
{
  "success": true,
  "message": "Document successfully processed",
  "action": "insert",
  "details": {
    "filename": "example-document.txt",
    "chunks_created": 5,
    "file_hash": "a3d5e9f...",
    "collection": "documents",
    "timestamp": "2025-11-07T12:34:56.789Z"
  }
}
```

#### Success - Updated Document
```json
{
  "success": true,
  "message": "Document successfully processed",
  "action": "update",
  "details": {
    "filename": "example-document.txt",
    "chunks_created": 6,
    "file_hash": "a3d5e9f...",
    "collection": "documents",
    "timestamp": "2025-11-07T12:34:56.789Z"
  }
}
```

#### Success - Skipped (No Changes)
```json
{
  "success": true,
  "message": "Document skipped",
  "action": "skip",
  "details": {
    "filename": "example-document.txt",
    "reason": "Document already exists with same content",
    "file_hash": "a3d5e9f...",
    "timestamp": "2025-11-07T12:34:56.789Z"
  }
}
```

#### Error Response
```json
{
  "success": false,
  "error": {
    "type": "validation_error|hash_generation_error|duplicate_check_error|...",
    "message": "Detailed error message",
    "timestamp": "2025-11-07T12:34:56.789Z"
  }
}
```

## Example Usage

### Using cURL

```bash
# Upload a new document
curl -X POST http://localhost:5678/webhook/ingest-document \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "technical-spec.md",
    "document_content": "# Technical Specification\n\nThis document outlines...",
    "collection": "documents"
  }'

# Update the same document (different content)
curl -X POST http://localhost:5678/webhook/ingest-document \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "technical-spec.md",
    "document_content": "# Technical Specification v2\n\nUpdated version...",
    "collection": "documents"
  }'
```

### Using Python

```python
import requests
import hashlib

def upload_document(filename, content, collection="documents"):
    url = "http://localhost:5678/webhook/ingest-document"

    payload = {
        "filename": filename,
        "document_content": content,
        "collection": collection
    }

    response = requests.post(url, json=payload)
    return response.json()

# Upload document
with open("document.txt", "r") as f:
    content = f.read()

result = upload_document("document.txt", content)
print(f"Action: {result['action']}")
print(f"Chunks: {result['details']['chunks_created']}")
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');
const fs = require('fs');

async function uploadDocument(filename, content, collection = 'documents') {
  const url = 'http://localhost:5678/webhook/ingest-document';

  const payload = {
    filename: filename,
    document_content: content,
    collection: collection
  };

  const response = await axios.post(url, payload);
  return response.data;
}

// Upload document
const content = fs.readFileSync('document.txt', 'utf-8');
uploadDocument('document.txt', content)
  .then(result => {
    console.log(`Action: ${result.action}`);
    console.log(`Chunks: ${result.details.chunks_created}`);
  });
```

## How Duplicate Detection Works

### 1. File Hash Generation
```javascript
// SHA-256 hash of filename
file_hash = sha256(filename)
// Example: "technical-spec.md" → "a3d5e9f1c2b4..."
```

This ensures the same filename always gets the same hash, regardless of content.

### 2. Content Hash Generation
```javascript
// SHA-256 hash of content
content_hash = sha256(document_content)
```

This detects if the document content has changed.

### 3. Duplicate Check Query
```javascript
// Query Qdrant for existing documents with same file_hash
POST /collections/{collection}/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "file_hash",
        "match": { "value": "a3d5e9f1c2b4..." }
      }
    ]
  }
}
```

### 4. Decision Logic
```javascript
if (no_existing_documents) {
  action = "insert"  // New document
} else {
  existing_content_hash = existing_documents[0].payload.content_hash
  if (existing_content_hash != new_content_hash) {
    action = "update"  // Content changed
  } else {
    action = "skip"    // No changes
  }
}
```

### 5. Update Process
For `action = "update"`:
1. Delete all existing chunks with same `file_hash`
2. Create new chunks from updated content
3. Store with same `file_hash`, updated `content_hash`

## Data Storage Schema

### Qdrant Point Structure

Each document chunk is stored as:

```json
{
  "id": "{file_hash}_{chunk_index}",
  "vector": [1024 dimensions],
  "payload": {
    "content": "Chunk text content...",
    "filename": "example-document.txt",
    "file_hash": "a3d5e9f1c2b4...",
    "content_hash": "f7e8d9c6b5a4...",
    "chunk_index": 0,
    "total_chunks": 5,
    "timestamp": "2025-11-07T12:34:56.789Z",
    "metadata": {
      "original_filename": "example-document.txt",
      "upload_timestamp": "2025-11-07T12:34:56.789Z",
      "file_size": 5432
    }
  }
}
```

### Querying Documents

**Find all chunks of a specific document:**
```javascript
POST /collections/documents/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "file_hash",
        "match": { "value": "a3d5e9f1c2b4..." }
      }
    ]
  },
  "with_payload": true
}
```

**Find documents by filename:**
```javascript
POST /collections/documents/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "filename",
        "match": { "value": "example-document.txt" }
      }
    ]
  }
}
```

**Semantic search across all documents:**
```javascript
POST /collections/documents/points/search
{
  "vector": [query_embedding],
  "limit": 10,
  "with_payload": true
}
```

## Error Handling

The workflow includes comprehensive error handling:

### Error Types

1. **validation_error**: Missing required fields or environment variables
2. **hash_generation_error**: Failed to generate document hashes
3. **duplicate_check_error**: Failed to query Qdrant for existing documents
4. **analysis_error**: Failed to analyze duplicate status
5. **delete_error**: Failed to delete old document versions
6. **chunking_error**: Failed to chunk document
7. **embedding_error**: Failed to generate embeddings
8. **storage_error**: Failed to store in Qdrant

### Retry Logic

All API calls include:
- **Max retries**: 3 attempts
- **Retry interval**: 1 second between attempts
- **Timeout**: 30 seconds per request

### Logging

All operations are logged:
- **[INFO LOG]**: Successful operations and skipped documents
- **[ERROR LOG]**: Failed operations with details

View logs in:
- n8n execution logs
- n8n server console output

## Troubleshooting

### Document not detected as duplicate

**Problem**: Uploading same document creates duplicate entries

**Solution**:
- Ensure `filename` is exactly the same in both requests
- Check Qdrant collection name matches
- Verify `file_hash` is being stored in payload

### Old versions not deleted

**Problem**: Updated document doesn't delete old chunks

**Solution**:
- Check "Delete Old Document Versions" node logs
- Verify Qdrant DELETE permission
- Ensure `existing_points` array is populated correctly

### Chunks not linked to document

**Problem**: Can't find all chunks of a document

**Solution**:
- Query by `file_hash` instead of `filename`
- Verify all chunks have same `file_hash` in payload
- Check `chunk_index` and `total_chunks` are correct

### Embedding generation fails

**Problem**: Mistral API returns errors

**Solution**:
- Verify Mistral API credentials
- Check API rate limits
- Ensure chunk content is not empty
- Review chunk size (should be < 8192 tokens)

### Storage fails with dimension mismatch

**Problem**: Qdrant rejects vectors

**Solution**:
- Verify collection vector size is 1024
- Check Mistral embed model output dimensions
- Recreate collection if needed

## Advanced Configuration

### Custom Chunk Size

Edit the "Chunk Document" node:

```javascript
// Change MAX_CHUNK_SIZE
const MAX_CHUNK_SIZE = 2000; // Increase for larger chunks
```

### Custom Collection per Document Type

Pass different collection names:

```json
{
  "filename": "legal-doc.pdf",
  "document_content": "...",
  "collection": "legal_documents"
}
```

### Additional Metadata

Modify "Generate Document Hash" node to include custom metadata:

```javascript
metadata: {
  original_filename: filename,
  upload_timestamp: new Date().toISOString(),
  file_size: documentContent.length,
  // Add custom fields
  document_type: "report",
  author: "John Doe",
  tags: ["technical", "specification"]
}
```

### Integration with File Upload

For actual file uploads (not just text), add a preprocessing node:

```javascript
// Extract text from files
const fileBuffer = $input.item.binary.data;
const fileType = $input.item.binary.mimeType;

let documentContent = '';

if (fileType === 'text/plain') {
  documentContent = fileBuffer.toString('utf-8');
} else if (fileType === 'application/pdf') {
  // Use PDF parser library
  documentContent = await parsePDF(fileBuffer);
}

return {
  filename: $input.item.binary.fileName,
  document_content: documentContent
};
```

## Performance Considerations

### Batch Processing

For multiple documents, call the webhook sequentially or in controlled batches to avoid rate limits.

### Large Documents

- Documents are automatically chunked
- Each chunk is embedded and stored separately
- Max recommended document size: 100KB text

### Rate Limits

- Mistral API: Check your plan's rate limits
- Qdrant: Generally no strict limits for self-hosted
- Consider adding delays between batch uploads

## Security Considerations

### Input Validation

The workflow validates:
- Required fields presence
- Environment variable configuration
- Content is not empty

### Injection Prevention

- All user inputs are parameterized in Qdrant queries
- No direct code execution of user content
- Hash-based identification prevents filename manipulation

### Access Control

- Configure webhook authentication in n8n
- Use API keys for Mistral and Qdrant
- Restrict network access to Qdrant instance

## Monitoring and Maintenance

### Regular Checks

1. **Review logs** for errors and warnings
2. **Monitor Qdrant storage** size
3. **Check Mistral API usage** and costs
4. **Verify duplicate detection** is working correctly

### Cleanup Old Documents

To remove a document and all its chunks:

```bash
curl -X POST "${QDRANT_URL}/collections/documents/points/delete" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "must": [
        {
          "key": "file_hash",
          "match": { "value": "document_hash_here" }
        }
      ]
    }
  }'
```

### Backup Strategy

1. **Qdrant Snapshots**: Regular snapshots of collections
2. **Source Documents**: Keep original documents backed up
3. **Metadata Export**: Export document metadata periodically

## Integration Examples

### With Document Management System

```javascript
// Webhook triggered when document updated in DMS
const documentId = $json.document_id;
const documentContent = await fetchFromDMS(documentId);

return {
  filename: `doc_${documentId}.txt`,
  document_content: documentContent,
  collection: "dms_documents"
};
```

### With Git Repository

```javascript
// Process all markdown files from git repo
const files = await listFilesFromGit(repoUrl, "*.md");

for (const file of files) {
  const content = await fetchFileContent(file.path);
  await uploadDocument(file.name, content, "git_docs");
}
```

### With RAG Application

```javascript
// Upload documents for RAG
async function ingestKnowledgeBase(documents) {
  for (const doc of documents) {
    const result = await uploadDocument(
      doc.filename,
      doc.content,
      "rag_knowledge_base"
    );
    console.log(`${doc.filename}: ${result.action}`);
  }
}
```

## Support

For issues and questions:
- Check n8n execution logs for detailed errors
- Review Qdrant logs for storage issues
- Verify Mistral API status
- Open an issue on GitHub with error logs
