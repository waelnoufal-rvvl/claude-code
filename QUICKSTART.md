# Quick Start Guide

Get started with Mistral output separation in 5 minutes!

## 1. Prerequisites

- Docker installed (for Qdrant)
- n8n installed or account created
- Mistral AI API key

## 2. Start Qdrant

```bash
docker run -p 6333:6333 qdrant/qdrant
```

## 3. Configure Environment

```bash
cp config/.env.example .env
# Edit .env with your API keys
```

## 4. Setup Qdrant Collections

```bash
cd config
./setup_qdrant.sh
```

Or using Python:

```bash
python setup_qdrant.py
```

## 5. Import Workflow to n8n

1. Open n8n (http://localhost:5678)
2. Go to **Workflows** → **Import from File**
3. Select `workflows/mistral-qdrant-separation.json`
4. Configure credentials:
   - Add Mistral API key
   - Add Qdrant URL
5. Activate the workflow

## 6. Test the Workflow

Get the webhook URL from n8n and test:

```bash
curl -X POST 'YOUR_WEBHOOK_URL' \
  -H 'Content-Type: application/json' \
  -d '{
    "mistral_response": "# Test\n\nSome text.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n![img](url)"
  }'
```

Expected response:

```json
{
  "success": true,
  "message": "Content processed and stored successfully",
  "stats": {
    "text_chunks": 1,
    "tables": 1,
    "figures": 1
  }
}
```

## 7. Verify Data in Qdrant

```bash
curl http://localhost:6333/collections/mistral_text
curl http://localhost:6333/collections/mistral_tables
curl http://localhost:6333/collections/mistral_figures
```

## That's it! 🎉

Your workflow is now ready to process Mistral outputs and store them in Qdrant.

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Follow the [TUTORIAL.md](examples/TUTORIAL.md) for advanced usage
- Test with `examples/test_workflow.py`

## Need Help?

Check out:
- [Troubleshooting section in README](README.md#troubleshooting)
- [Complete tutorial](examples/TUTORIAL.md)
- Mistral AI docs: https://docs.mistral.ai/
- Qdrant docs: https://qdrant.tech/documentation/
- n8n docs: https://docs.n8n.io/

## Architecture Overview

```
┌─────────────┐
│   Mistral   │
│   Output    │
└──────┬──────┘
       │
       v
┌─────────────┐      ┌──────────────┐
│     n8n     │──────│    Parser    │
│  Workflow   │      │  (JS/Python) │
└──────┬──────┘      └──────────────┘
       │
       v
┌─────────────────────────────┐
│      Content Split          │
├─────────┬─────────┬─────────┤
│  Text   │ Tables  │ Figures │
└────┬────┴────┬────┴────┬────┘
     │         │         │
     v         v         v
┌────────┬────────┬────────┐
│ Qdrant │ Qdrant │ Qdrant │
│  Text  │ Tables │Figures │
└────────┴────────┴────────┘
```

## Key Features

✅ Automatic content separation (text, tables, figures)
✅ Separate Qdrant collections for each type
✅ Mistral embeddings for semantic search
✅ Support for markdown and HTML formats
✅ Metadata preservation
✅ Easy integration with existing workflows

Happy coding! 🚀
