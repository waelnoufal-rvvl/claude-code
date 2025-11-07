# Enhanced Features Guide

## Overview

This document describes the enhanced features added to the Mistral-Qdrant integration, including:
- Auto-creation of Qdrant collections with payload indexes
- Title and context extraction for tables and figures
- Document structure tracking and relationship mapping
- Hybrid search capabilities (vector + keyword filtering)

## Auto-Creation of Collections

### Feature Description

The enhanced workflow automatically creates Qdrant collections if they don't exist, eliminating the need for manual setup.

### How It Works

1. **Collection Check**: On workflow execution, the system checks if required collections exist
2. **Auto-Creation**: Missing collections are automatically created with proper configuration
3. **Payload Indexes**: Indexes are created on key fields for efficient filtering and hybrid search

### Collections Created

- **mistral_text**: Text content from Mistral responses
- **mistral_tables**: Table data with structure and context
- **mistral_figures**: Images and figures with metadata

### Payload Indexes

Each collection includes indexes on:
- `title`: Keyword index for title-based filtering
- `type`: Content type filtering (text/table/figure)
- `source`: Source system identification
- `relations.section_id`: Document section relationships
- `relations.parent_section`: Hierarchical section tracking
- `timestamp`: Temporal filtering

Collection-specific indexes:
- **Tables**: `metadata.rows`, `metadata.columns` (integer indexes)
- **Figures**: `metadata.format` (image format keyword index)

### Usage

The enhanced n8n workflow (`workflows/mistral-qdrant-enhanced.json`) includes an "Initialize Collections" node that handles auto-creation transparently.

## Title and Context Extraction

### Feature Description

Tables and figures are now stored with their titles and surrounding context, making them more searchable and understandable.

### How It Works

For each table or figure:
1. **Title Extraction**: Searches backward from the element to find the nearest heading
2. **Context Capture**: Captures the 3 lines of text immediately before the element
3. **Fallback**: If no heading found, uses the last sentence before the element as title

### Example

**Input:**
```markdown
## Financial Analysis

The following table shows our performance:

| Year | Revenue |
|------|---------|
| 2023 | $1M     |
```

**Extracted Data:**
- **Title**: "Financial Analysis"
- **Context**: "The following table shows our performance:"
- **Content**: The full table

### Benefits

- **Better Search**: Search by title or context to find relevant tables/figures
- **Understanding**: Know what each table/figure represents without viewing it
- **References**: Track which section contains each element

## Document Structure and Relationships

### Feature Description

The system now builds a hierarchical graph of document structure, tracking sections, subsections, and relationships between content elements.

### Document Structure

**Sections** are extracted from headings:
```javascript
{
  "id": "section_0",
  "level": 2,              // Heading level (# = 1, ## = 2, etc.)
  "title": "Introduction",
  "position": 0,           // Character position in document
  "parent_id": null,       // Parent section (for nested structure)
  "children": ["section_1", "section_2"]
}
```

### Relationship Tracking

Each content element (text, table, figure) includes:
```javascript
{
  "relations": {
    "section_id": "section_2",        // Which section contains this element
    "parent_section": "section_0",    // Parent of containing section
    "references": ["table_1", "figure_0"]  // Referenced elements
  }
}
```

### Reference Detection

The system automatically detects references like:
- "Table 1", "Table 2" → Links to specific tables
- "Figure 3", "Fig. 4" → Links to specific figures
- "as shown in table 1" → Cross-references

### Benefits

- **Navigation**: Traverse document structure programmatically
- **Context**: Understand where each element appears in the document
- **Relationships**: Find related content (e.g., "show me all tables in Section 2")

## Hybrid Search

### Feature Description

Combine vector similarity search with keyword filtering for precise, efficient retrieval.

### Basic Search

```python
from hybrid_search import HybridSearch

searcher = HybridSearch()

# Vector similarity search
results = searcher.search(
    collection_name="mistral_tables",
    query="revenue analysis",
    limit=5
)
```

### Filtered Search

```python
# Search with filters
results = searcher.search(
    collection_name="mistral_text",
    query="machine learning trends",
    filters={
        "type": "paragraph",
        "relations.section_id": "section_2"
    },
    limit=10
)
```

### Multi-Collection Search

Search across all collections simultaneously:

```python
results = searcher.multi_collection_search(
    query="financial performance",
    limit_per_collection=3
)

# Returns:
# {
#   "mistral_text": [...],
#   "mistral_tables": [...],
#   "mistral_figures": [...]
# }
```

### Section-Based Search

Find content within a specific document section:

```python
results = searcher.search_by_section(
    query="growth metrics",
    section_id="section_1",
    limit=5
)
```

### Find Related Content

Discover content related to a specific table or figure:

```python
results = searcher.find_related_content(
    element_type="table",
    element_index=0,
    limit=5
)
```

### Advanced Filtering

Combine multiple filters:

```python
results = searcher.search(
    collection_name="mistral_tables",
    query="quarterly results",
    filters={
        "type": "table",
        "metadata.rows": [3, 4, 5],  # Tables with 3-5 rows
        "relations.section_id": ["section_1", "section_2"]
    },
    score_threshold=0.7
)
```

## Payload Structure

### Text Elements

```json
{
  "content": "Paragraph text...",
  "type": "text",
  "source": "mistral",
  "timestamp": "2025-11-07T12:00:00Z",
  "relations": {
    "section_id": "section_1",
    "parent_section": "section_0"
  },
  "metadata": {
    "chunk_index": 0,
    "word_count": 42,
    "char_count": 256
  }
}
```

### Table Elements

```json
{
  "content": "| Col1 | Col2 |\n|------|------|\n| A | B |",
  "title": "Financial Summary",
  "context": "The following table shows...",
  "type": "table",
  "source": "mistral",
  "timestamp": "2025-11-07T12:00:00Z",
  "relations": {
    "section_id": "section_2",
    "parent_section": "section_0",
    "references": ["figure_0"]
  },
  "metadata": {
    "table_index": 0,
    "table_type": "markdown",
    "rows": 2,
    "columns": 2,
    "headers": ["Col1", "Col2"]
  }
}
```

### Figure Elements

```json
{
  "content": "Performance Chart",
  "title": "Q4 Results",
  "context": "The chart below illustrates...",
  "image_url": "https://example.com/chart.png",
  "type": "figure",
  "source": "mistral",
  "timestamp": "2025-11-07T12:00:00Z",
  "relations": {
    "section_id": "section_2",
    "parent_section": "section_0",
    "references": []
  },
  "metadata": {
    "figure_index": 0,
    "figure_type": "markdown",
    "format": "png",
    "alt_text": "Performance Chart"
  }
}
```

## Use Cases

### 1. Semantic Search with Filtering

Find specific types of content:

```python
# Find all tables about revenue in the Financial section
results = searcher.search(
    collection_name="mistral_tables",
    query="revenue breakdown",
    filters={"relations.section_id": "section_financial"},
    limit=5
)
```

### 2. Document Navigation

Traverse document structure:

```python
# Get all content from a specific section
section_content = searcher.search_by_section(
    query="",  # Empty query = get all
    section_id="section_3",
    collections=["mistral_text", "mistral_tables"],
    limit=100
)
```

### 3. Cross-Reference Analysis

Find related elements:

```python
# Find all content that references a specific table
table_refs = searcher.find_related_content(
    element_type="table",
    element_index=2
)
```

### 4. Context-Aware Retrieval

Get elements with their full context:

```python
# Each result includes title, context, and relations
for result in results:
    print(f"Title: {result['payload']['title']}")
    print(f"Context: {result['payload']['context']}")
    print(f"Section: {result['payload']['relations']['section_id']}")
```

## Migration Guide

### From Original Workflow

1. **Update Workflow**: Import `workflows/mistral-qdrant-enhanced.json` into n8n
2. **Update Webhook URL**: Use the new webhook endpoint
3. **Run Tests**: Verify with `python examples/test_workflow.py <webhook_url>`

### Backward Compatibility

- Original payloads still work (missing fields default to empty)
- Old collections can coexist with new enhanced collections
- Gradual migration supported

### Reindexing Existing Data

To add titles and relations to existing data:

```python
# Re-process existing Mistral responses through enhanced workflow
# The system will extract titles, context, and relations
```

## Configuration

### Environment Variables

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key_here

# Mistral Configuration
MISTRAL_API_KEY=your_mistral_key_here

# Vector Configuration
VECTOR_SIZE=1024
VECTOR_DISTANCE=Cosine

# n8n Webhook
N8N_WEBHOOK_URL=http://localhost:5678/webhook/mistral-process-enhanced
```

### Collection Configuration

Modify `config/setup_qdrant.py` to customize:
- Vector size
- Distance metric
- Replication factor
- Collection names
- Payload indexes

## Performance Considerations

### Indexing

- Payload indexes improve filter performance by 10-100x
- Index creation is automatic and idempotent
- Indexes consume additional storage (~5-10% overhead)

### Search Performance

- **Vector-only search**: ~10-50ms for 1M vectors
- **Hybrid search (vector + 1-2 filters)**: ~15-60ms
- **Complex filters (3+ conditions)**: ~20-100ms

### Best Practices

1. **Use Filters**: Combine vector search with filters for best performance
2. **Limit Results**: Keep `limit` parameter reasonable (5-20 for most use cases)
3. **Index Strategic Fields**: Focus on frequently filtered fields
4. **Batch Operations**: Process multiple documents in parallel when possible

## Troubleshooting

### Collections Not Created

**Issue**: Collections don't auto-create
**Solution**: Check Qdrant connectivity and permissions

```bash
curl http://localhost:6333/collections
```

### Missing Indexes

**Issue**: Payload indexes not created
**Solution**: Re-run collection setup

```bash
python config/setup_qdrant.py
```

### Empty Titles/Context

**Issue**: Tables/figures have no titles
**Solution**: Ensure documents have proper heading structure

### Slow Search Performance

**Issue**: Searches taking too long
**Solution**:
1. Check if payload indexes exist
2. Reduce result limit
3. Use more specific filters

## API Reference

### HybridSearch Class

```python
class HybridSearch:
    def __init__(self, qdrant_url=None, api_key=None, mistral_api_key=None)
    def search(self, collection_name, query, filters=None, limit=5, score_threshold=0.0)
    def multi_collection_search(self, query, collections=None, filters=None, limit_per_collection=3)
    def search_by_section(self, query, section_id, collections=None, limit=5)
    def find_related_content(self, element_type, element_index, collection_name=None, limit=5)
```

### ContentParser Class

```python
class ContentParser:
    def parse(self, mistral_response)  # Returns enhanced parsed data
    def build_document_structure(self, text)  # Extract sections
    def extract_title_for_element(self, text, element_index)  # Get title/context
```

## Future Enhancements

- [ ] Full-text search integration
- [ ] Graph database export for relationships
- [ ] Multi-modal search (text + image embeddings)
- [ ] Automatic summarization of sections
- [ ] Relationship strength scoring
- [ ] Temporal queries (search by date range)
