# Complete Tutorial: Mistral Output Separation with n8n and Qdrant

This tutorial walks you through the complete setup and usage of the Mistral-Qdrant separation workflow.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Setup Qdrant](#setup-qdrant)
5. [Import n8n Workflow](#import-n8n-workflow)
6. [Testing the Workflow](#testing-the-workflow)
7. [Querying Data](#querying-data)
8. [Advanced Usage](#advanced-usage)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting, ensure you have:

- **n8n** installed (self-hosted or cloud)
  - [Installation guide](https://docs.n8n.io/hosting/)
- **Qdrant** running (local or cloud)
  - Local: `docker run -p 6333:6333 qdrant/qdrant`
  - Cloud: [Qdrant Cloud](https://cloud.qdrant.io/)
- **Mistral AI API key**
  - Get yours at [Mistral AI](https://console.mistral.ai/)

## Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd claude-code
```

### Step 2: Install Dependencies (for standalone scripts)

```bash
# For Python scripts
pip install requests python-dotenv

# For JavaScript/Node.js scripts
npm init -y
npm install axios dotenv
```

## Configuration

### Step 1: Create Environment File

Copy the example environment file:

```bash
cp config/.env.example .env
```

### Step 2: Edit Configuration

Edit `.env` with your actual credentials:

```bash
# Mistral AI Configuration
MISTRAL_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
MISTRAL_API_URL=https://api.mistral.ai/v1
MISTRAL_EMBED_MODEL=mistral-embed
MISTRAL_CHAT_MODEL=mistral-large-latest

# Qdrant Configuration
QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=your_key_here  # Uncomment if using Qdrant Cloud
QDRANT_COLLECTION_TEXT=mistral_text
QDRANT_COLLECTION_TABLES=mistral_tables
QDRANT_COLLECTION_FIGURES=mistral_figures

# Vector Configuration
VECTOR_SIZE=1024
VECTOR_DISTANCE=Cosine
```

## Setup Qdrant

### Option 1: Using Bash Script

```bash
cd config
./setup_qdrant.sh
```

### Option 2: Using Python Script

```bash
cd config
python setup_qdrant.py
```

### Option 3: Manual Setup (using curl)

```bash
# Create text collection
curl -X PUT 'http://localhost:6333/collections/mistral_text' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'

# Create tables collection
curl -X PUT 'http://localhost:6333/collections/mistral_tables' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'

# Create figures collection
curl -X PUT 'http://localhost:6333/collections/mistral_figures' \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
```

### Verify Collections

```bash
curl http://localhost:6333/collections
```

You should see three collections: `mistral_text`, `mistral_tables`, and `mistral_figures`.

## Import n8n Workflow

### Step 1: Access n8n Interface

Open your n8n instance (e.g., `http://localhost:5678`)

### Step 2: Import Workflow

1. Click on **Workflows** in the left sidebar
2. Click **Import from File**
3. Select `workflows/mistral-qdrant-separation.json`
4. Click **Import**

### Step 3: Configure Credentials

#### Mistral AI Credentials

1. In the workflow, click on any node that uses Mistral (e.g., "Generate Text Embedding")
2. Click **Credentials** → **Create New**
3. Select **HTTP Request** credential type
4. Configure:
   - **Name**: Mistral AI API
   - **Authentication**: Generic Credential Type
   - **Generic Auth Type**: Header Auth
   - **Name**: Authorization
   - **Value**: `Bearer YOUR_MISTRAL_API_KEY`

#### Qdrant Credentials

1. Click on any Qdrant node (e.g., "Store Text in Qdrant")
2. Click **Credentials** → **Create New**
3. Select **HTTP Request** credential type
4. Configure:
   - **Name**: Qdrant API
   - **Base URL**: Your Qdrant URL
   - (Optional) **Header Auth** with `api-key` if using Qdrant Cloud

### Step 4: Update Environment Variables

1. Go to **Settings** → **Environment Variables**
2. Add:
   - `QDRANT_URL`: Your Qdrant instance URL

### Step 5: Activate Workflow

Click **Active** toggle in the top right corner.

## Testing the Workflow

### Method 1: Using Webhook Trigger

The workflow is configured with a webhook trigger. Get the webhook URL:

1. Click on the **Webhook Trigger** node
2. Copy the **Production URL**

Send a test request:

```bash
curl -X POST 'http://localhost:5678/webhook/mistral-process' \
  -H 'Content-Type: application/json' \
  -d '{
    "mistral_response": "# Sales Report\n\nOur Q4 results show strong performance.\n\n| Quarter | Revenue | Growth |\n|---------|---------|--------|\n| Q1 | $1M | 10% |\n| Q2 | $1.2M | 20% |\n| Q3 | $1.5M | 25% |\n| Q4 | $2M | 33% |\n\n![Growth Chart](https://example.com/chart.png)\n\nThe chart above illustrates our trajectory."
  }'
```

Expected response:

```json
{
  "success": true,
  "message": "Content processed and stored successfully",
  "stats": {
    "text_chunks": 2,
    "tables": 1,
    "figures": 1
  }
}
```

### Method 2: Manual Execution

1. Click **Execute Workflow** button
2. Provide test input in the webhook node
3. Watch the workflow execute step by step

## Querying Data

### Query Text Collection

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(url="http://localhost:6333")

# Search for text about "revenue"
results = client.search(
    collection_name="mistral_text",
    query_vector=embedding_vector,  # Get from Mistral embeddings API
    limit=5,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="type",
                match=MatchValue(value="text")
            )
        ]
    )
)

for result in results:
    print(f"Score: {result.score}")
    print(f"Content: {result.payload['content']}")
    print("---")
```

### Query Tables Collection

```python
# Search for tables with specific data
results = client.search(
    collection_name="mistral_tables",
    query_vector=embedding_vector,
    limit=5
)

for result in results:
    print(f"Table content:\n{result.payload['content']}")
    print(f"Rows: {result.payload['metadata']['rows']}")
    print(f"Columns: {result.payload['metadata']['columns']}")
    print("---")
```

### Query Figures Collection

```python
# Search for figures
results = client.search(
    collection_name="mistral_figures",
    query_vector=embedding_vector,
    limit=5
)

for result in results:
    print(f"Description: {result.payload['content']}")
    print(f"URL: {result.payload['image_url']}")
    print(f"Format: {result.payload['metadata']['format']}")
    print("---")
```

## Advanced Usage

### Batch Processing

For processing multiple Mistral responses:

```python
import requests

webhook_url = "http://localhost:5678/webhook/mistral-process"

responses = [
    "Response 1 with tables and figures...",
    "Response 2 with tables and figures...",
    "Response 3 with tables and figures..."
]

for i, response in enumerate(responses):
    result = requests.post(
        webhook_url,
        json={"mistral_response": response}
    )
    print(f"Batch {i+1}: {result.json()}")
```

### Custom Content Parser

To add custom parsing logic:

1. Edit `scripts/content_parser.js` or `scripts/content_parser.py`
2. Add new regex patterns
3. Update the n8n Code node with your custom logic

Example - Add code block detection:

```javascript
// In content_parser.js
const codeBlocks = [];
const codeRegex = /```[\s\S]*?```/g;

let codeMatch;
while ((codeMatch = codeRegex.exec(mistralResponse)) !== null) {
  codeBlocks.push({
    content: codeMatch[0],
    type: 'code',
    index: codeMatch.index
  });
}
```

### Integrate with Mistral Chat

Create a complete flow: Query → Mistral → Parse → Store

```javascript
// n8n workflow addition
// 1. HTTP Request to Mistral Chat API
{
  "model": "mistral-large-latest",
  "messages": [
    {
      "role": "user",
      "content": "Analyze sales data and create a report with tables"
    }
  ]
}

// 2. Extract response
const mistralResponse = $json.choices[0].message.content;

// 3. Pass to Content Parser (existing workflow)
```

### Scheduled Processing

Add a Schedule trigger to process Mistral outputs periodically:

1. Add **Schedule Trigger** node
2. Set interval (e.g., every day at 9 AM)
3. Connect to HTTP Request node to fetch Mistral data
4. Connect to existing parsing workflow

## Troubleshooting

### Issue: "Collection not found"

**Solution**: Run the Qdrant setup script again:

```bash
cd config
./setup_qdrant.sh
```

### Issue: "Vector dimension mismatch"

**Problem**: Your embedding model produces vectors of different size

**Solution**: Update Qdrant collections with correct size:

```bash
# Delete old collections
curl -X DELETE http://localhost:6333/collections/mistral_text
curl -X DELETE http://localhost:6333/collections/mistral_tables
curl -X DELETE http://localhost:6333/collections/mistral_figures

# Update VECTOR_SIZE in .env
VECTOR_SIZE=768  # Or whatever your model outputs

# Recreate collections
./config/setup_qdrant.sh
```

### Issue: "Mistral API authentication failed"

**Solution**: Verify your API key:

```bash
curl -X GET 'https://api.mistral.ai/v1/models' \
  -H 'Authorization: Bearer YOUR_API_KEY'
```

### Issue: "n8n workflow execution timeout"

**Solution**: Increase timeout in n8n settings:

1. Go to Settings → Environment Variables
2. Add `EXECUTIONS_TIMEOUT=300` (5 minutes)
3. Restart n8n

### Issue: "Tables not detected correctly"

**Problem**: Table format not matching regex

**Solution**: Check table format. Must be:

```markdown
| Column 1 | Column 2 |
|----------|----------|
| Data 1   | Data 2   |
```

Or HTML:

```html
<table>
  <tr><th>Column 1</th><th>Column 2</th></tr>
  <tr><td>Data 1</td><td>Data 2</td></tr>
</table>
```

### Debug Mode

Enable debug logging in n8n:

1. Set environment variable: `N8N_LOG_LEVEL=debug`
2. Restart n8n
3. Check logs for detailed execution information

## Next Steps

- Explore [Mistral AI Documentation](https://docs.mistral.ai/)
- Learn about [Qdrant filtering](https://qdrant.tech/documentation/concepts/filtering/)
- Build custom n8n nodes for your use case
- Integrate with your existing data pipeline

## Support

For issues:
- Check the main README.md
- Review n8n documentation
- Visit Qdrant community forums
- Check Mistral AI documentation
