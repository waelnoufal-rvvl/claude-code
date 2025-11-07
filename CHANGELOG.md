# Changelog

All notable changes to this project will be documented in this file.

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
