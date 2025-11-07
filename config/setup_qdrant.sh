#!/bin/bash

# Setup Qdrant Collections for Mistral Output Separation
# This script creates three collections in Qdrant for storing text, tables, and figures

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values if not set in .env
QDRANT_URL=${QDRANT_URL:-"http://localhost:6333"}
VECTOR_SIZE=${VECTOR_SIZE:-1024}
VECTOR_DISTANCE=${VECTOR_DISTANCE:-"Cosine"}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Setting up Qdrant collections...${NC}"
echo "Qdrant URL: $QDRANT_URL"
echo "Vector size: $VECTOR_SIZE"
echo "Distance metric: $VECTOR_DISTANCE"
echo ""

# Function to create a collection
create_collection() {
    local collection_name=$1
    local description=$2

    echo -e "${BLUE}Creating collection: ${collection_name}${NC}"

    # Prepare the request body
    local request_body=$(cat <<EOF
{
  "vectors": {
    "size": ${VECTOR_SIZE},
    "distance": "${VECTOR_DISTANCE}"
  },
  "optimizers_config": {
    "indexing_threshold": 20000
  },
  "replication_factor": 1
}
EOF
    )

    # Check if collection exists
    response=$(curl -s -w "\n%{http_code}" \
        -X GET "${QDRANT_URL}/collections/${collection_name}" \
        ${QDRANT_API_KEY:+-H "api-key: ${QDRANT_API_KEY}"})

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Collection '${collection_name}' already exists${NC}"
    else
        # Create the collection
        response=$(curl -s -w "\n%{http_code}" \
            -X PUT "${QDRANT_URL}/collections/${collection_name}" \
            -H "Content-Type: application/json" \
            ${QDRANT_API_KEY:+-H "api-key: ${QDRANT_API_KEY}"} \
            -d "$request_body")

        http_code=$(echo "$response" | tail -n1)

        if [ "$http_code" = "200" ]; then
            echo -e "${GREEN}✓ Collection '${collection_name}' created successfully${NC}"
        else
            echo -e "${RED}✗ Failed to create collection '${collection_name}'${NC}"
            echo "Response: $(echo "$response" | head -n -1)"
            exit 1
        fi
    fi
    echo ""
}

# Create collections
create_collection "mistral_text" "Storage for text content from Mistral responses"
create_collection "mistral_tables" "Storage for tables from Mistral responses"
create_collection "mistral_figures" "Storage for figures/images from Mistral responses"

echo -e "${GREEN}All collections created successfully!${NC}"
echo ""
echo "You can verify the collections by visiting:"
echo "  ${QDRANT_URL}/dashboard"
echo ""
echo "To list all collections, run:"
echo "  curl ${QDRANT_URL}/collections"
