# Changelog

All notable changes to this project will be documented in this file.

## [3.0.0] - 2025-11-07

### Added - Document Ingestion Workflow with Duplicate Detection

#### New Workflow: `workflows/ingest-vectorize-docs.json`

A comprehensive document ingestion system that prevents duplicate documents in vector databases:

**Key Features:**
- **Duplicate Detection**: SHA-256 hash-based identification using filename
- **Content Change Detection**: SHA-256 hash of content to detect updates
- **Smart Actions**:
  - `insert`: New documents are stored normally
  - `update`: Existing documents with changes are updated (old deleted, new stored)
  - `skip`: Unchanged documents are skipped to avoid wasted processing
- **Automatic Cleanup**: Deletes all old chunks before storing updated versions
- **Document Chunking**: Splits documents into ~1000 character chunks
- **Comprehensive Error Handling**: Validates inputs, retries API calls, logs all operations

**Workflow Nodes:**
1. Document Upload Webhook - Receives document via POST request
2. Validate Input & Env - Checks required fields and environment variables
3. Generate Document Hash - Creates file_hash and content_hash for tracking
4. Check Existing Document - Queries Qdrant for existing documents by file_hash
5. Analyze Duplicate Status - Determines if document is new, changed, or unchanged
6. Should Process Document? - Decides whether to process or skip
7. Need to Delete Old? - Checks if old versions need deletion
8. Delete Old Document Versions - Removes all chunks with same file_hash
9. Chunk Document - Splits into manageable pieces for embedding
10. Split Chunks - Loops through each chunk
11. Generate Embedding - Creates vector embeddings via Mistral API
12. Store in Qdrant - Saves chunks with metadata
13. Success/Skip/Error Loggers - Comprehensive logging system
14. Response Nodes - Returns structured JSON responses

**API Endpoint:**
```
POST /webhook/ingest-document
```

**Request Format:**
```json
{
  "filename": "document.txt",
  "document_content": "Full document text...",
  "collection": "documents"
}
```

**Response Actions:**
- `insert`: New document added (HTTP 200)
- `update`: Existing document updated (HTTP 200)
- `skip`: No changes detected (HTTP 200)
- `error`: Processing failed (HTTP 500)

**Data Storage:**
Each chunk stored with:
- `id`: `{file_hash}_{chunk_index}`
- `vector`: 1024-dimensional embedding
- `payload`:
  - `content`: Chunk text
  - `filename`: Original filename
  - `file_hash`: SHA-256 of filename (for duplicate detection)
  - `content_hash`: SHA-256 of content (for change detection)
  - `chunk_index`: Position in document
  - `total_chunks`: Total number of chunks
  - `timestamp`: Upload time
  - `metadata`: Additional file information

**Error Handling:**
- validation_error: Missing inputs or env vars
- hash_generation_error: Hash creation failed
- duplicate_check_error: Qdrant query failed
- analysis_error: Duplicate analysis failed
- delete_error: Old version deletion failed
- chunking_error: Document chunking failed
- embedding_error: Mistral API failed
- storage_error: Qdrant storage failed

**Documentation:**
- Comprehensive guide: `docs/INGEST_WORKFLOW.md`
- Usage examples in Python, JavaScript, cURL
- Integration patterns for DMS, Git, RAG applications
- Troubleshooting guide
- Performance and security considerations

### Changed
- Updated main README to list both workflows
- Added workflow comparison table
- Enhanced project description

## [2.0.0] - 2025-11-07

### Added - Error Handling and Logging

#### New Nodes
- **Validate Inputs & Env Vars** - IF node that validates:
  - `QDRANT_URL` environment variable is set
  - `mistral_response` input data is present
- **Prepare Validation Error** - Formats validation errors for logging
- **Prepare Parser Error** - Captures and formats content parser errors
- **Prepare API Error** - Captures and formats API call failures
- **Error Logger** - Centralized error logging with console output
- **Error Response** - Returns HTTP 500 with structured error JSON
- **Success Logger** - Logs successful operations with statistics
- **Success Response** - Returns HTTP 200 with success status and stats

#### Enhanced Existing Nodes
- **Content Parser** - Added `continueOnFail: true` to handle parsing errors gracefully
- **Generate Text/Table/Figure Embedding** nodes:
  - Added `continueOnFail: true`
  - Added automatic retry (3 attempts, 1-second interval)
  - Added 30-second timeout
- **Store Text/Tables/Figures in Qdrant** nodes:
  - Added `continueOnFail: true`
  - Added automatic retry (3 attempts, 1-second interval)
  - Added 30-second timeout

#### Error Handling Flow
1. **Validation Phase**: Checks environment variables and input data
2. **Parsing Phase**: Catches JavaScript execution errors in Content Parser
3. **API Phase**: Handles Mistral API and Qdrant API failures with retry logic
4. **Logging Phase**: All errors route to centralized Error Logger
5. **Response Phase**: Returns structured error response to webhook caller

#### Error Types
- `validation_error` - Missing environment variables or input data
- `parser_error` - Content parsing failures
- `api_error` - API call failures (Mistral or Qdrant)

#### Success Logging
- Logs successful operations with processing statistics
- Includes text chunks, tables, and figures counts
- Includes execution ID for tracing

### Changed
- Updated workflow version from 1 to 2
- Enhanced README with comprehensive error handling documentation
- Added troubleshooting section with common error scenarios
- Renamed "Webhook Response" to "Success Response" for clarity

### Technical Details

#### Retry Configuration
All HTTP API calls now include:
```json
{
  "options": {
    "retry": {
      "retry": {
        "maxRetries": 3,
        "retryInterval": 1000
      }
    },
    "timeout": 30000
  }
}
```

#### Error Response Structure
```json
{
  "success": false,
  "error": {
    "type": "validation_error|parser_error|api_error",
    "message": "Detailed error message",
    "timestamp": "ISO 8601 timestamp"
  }
}
```

#### Success Response Structure
```json
{
  "success": true,
  "message": "Content processed and stored successfully",
  "stats": {
    "text_chunks": 5,
    "tables": 2,
    "figures": 1
  },
  "timestamp": "ISO 8601 timestamp"
}
```

## [1.0.0] - 2025-11-07

### Initial Release
- Webhook trigger for receiving Mistral AI output
- Content parser for separating text, tables, and figures
- Integration with Mistral Embeddings API
- Storage in Qdrant vector database (separate collections)
- Basic success response
