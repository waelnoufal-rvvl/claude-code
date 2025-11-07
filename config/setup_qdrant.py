#!/usr/bin/env python3
"""
Setup Qdrant Collections for Mistral Output Separation
Creates three collections in Qdrant for storing text, tables, and figures
"""

import os
import sys
import requests
from typing import Dict, Any


class QdrantSetup:
    """Setup utility for Qdrant collections"""

    def __init__(
        self,
        qdrant_url: str = None,
        api_key: str = None,
        vector_size: int = 1024,
        distance_metric: str = "Cosine"
    ):
        """
        Initialize Qdrant setup

        Args:
            qdrant_url: Qdrant instance URL
            api_key: Qdrant API key (optional for local instances)
            vector_size: Dimension of vectors (default: 1024 for mistral-embed)
            distance_metric: Distance metric (Cosine, Euclid, or Dot)
        """
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.api_key = api_key or os.getenv('QDRANT_API_KEY')
        self.vector_size = vector_size
        self.distance_metric = distance_metric

        self.headers = {'Content-Type': 'application/json'}
        if self.api_key:
            self.headers['api-key'] = self.api_key

        self.collections = {
            'mistral_text': 'Storage for text content from Mistral responses',
            'mistral_tables': 'Storage for tables from Mistral responses',
            'mistral_figures': 'Storage for figures/images from Mistral responses'
        }

    def create_collection(self, collection_name: str, description: str = "") -> bool:
        """
        Create a Qdrant collection with payload indexes for hybrid search

        Args:
            collection_name: Name of the collection
            description: Description of the collection

        Returns:
            True if successful, False otherwise
        """
        print(f"Creating collection: {collection_name}")

        # Check if collection exists
        check_url = f"{self.qdrant_url}/collections/{collection_name}"
        collection_exists = False
        try:
            response = requests.get(check_url, headers=self.headers)
            if response.status_code == 200:
                print(f"✓ Collection '{collection_name}' already exists")
                collection_exists = True
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not check collection existence: {e}")

        # Create collection if it doesn't exist
        if not collection_exists:
            create_url = f"{self.qdrant_url}/collections/{collection_name}"
            payload = {
                "vectors": {
                    "size": self.vector_size,
                    "distance": self.distance_metric
                },
                "optimizers_config": {
                    "indexing_threshold": 20000
                },
                "replication_factor": 1
            }

            try:
                response = requests.put(create_url, json=payload, headers=self.headers)
                response.raise_for_status()
                print(f"✓ Collection '{collection_name}' created successfully")
            except requests.exceptions.RequestException as e:
                print(f"✗ Failed to create collection '{collection_name}': {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response: {e.response.text}")
                return False

        # Create payload indexes for hybrid search
        return self._create_payload_indexes(collection_name)

    def _create_payload_indexes(self, collection_name: str) -> bool:
        """
        Create payload indexes for efficient filtering and hybrid search

        Args:
            collection_name: Name of the collection

        Returns:
            True if successful
        """
        print(f"  Creating payload indexes for '{collection_name}'...")

        indexes = [
            {"field_name": "title", "field_schema": "keyword"},
            {"field_name": "type", "field_schema": "keyword"},
            {"field_name": "source", "field_schema": "keyword"},
            {"field_name": "relations.section_id", "field_schema": "keyword"},
            {"field_name": "relations.parent_section", "field_schema": "keyword"},
            {"field_name": "timestamp", "field_schema": "datetime"}
        ]

        # Add collection-specific indexes
        if 'table' in collection_name:
            indexes.extend([
                {"field_name": "metadata.rows", "field_schema": "integer"},
                {"field_name": "metadata.columns", "field_schema": "integer"}
            ])
        elif 'figure' in collection_name:
            indexes.append(
                {"field_name": "metadata.format", "field_schema": "keyword"}
            )

        success = True
        for index in indexes:
            index_url = f"{self.qdrant_url}/collections/{collection_name}/index"
            try:
                response = requests.put(index_url, json=index, headers=self.headers)
                # Index creation returns 200 or 202 if successful
                if response.status_code in [200, 202]:
                    print(f"    ✓ Created index on '{index['field_name']}'")
                else:
                    # Index might already exist, which is fine
                    print(f"    ⚠ Index on '{index['field_name']}' may already exist")
            except requests.exceptions.RequestException as e:
                print(f"    ⚠ Could not create index on '{index['field_name']}': {e}")
                # Don't fail the whole process for index creation issues
                # Indexes are optional for functionality

        return success

    def setup_all_collections(self) -> bool:
        """
        Set up all required collections

        Returns:
            True if all collections created successfully
        """
        print("\nSetting up Qdrant collections...")
        print(f"Qdrant URL: {self.qdrant_url}")
        print(f"Vector size: {self.vector_size}")
        print(f"Distance metric: {self.distance_metric}\n")

        success = True
        for collection_name, description in self.collections.items():
            if not self.create_collection(collection_name, description):
                success = False
            print()

        if success:
            print("✓ All collections created successfully!\n")
            print(f"You can verify the collections by visiting:")
            print(f"  {self.qdrant_url}/dashboard\n")
            print("To list all collections, run:")
            print(f"  curl {self.qdrant_url}/collections")
        else:
            print("✗ Some collections failed to create")

        return success

    def list_collections(self) -> Dict[str, Any]:
        """List all collections in Qdrant"""
        url = f"{self.qdrant_url}/collections"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error listing collections: {e}")
            return {}

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection (use with caution!)

        Args:
            collection_name: Name of collection to delete

        Returns:
            True if successful
        """
        url = f"{self.qdrant_url}/collections/{collection_name}"
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            print(f"✓ Collection '{collection_name}' deleted")
            return True
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to delete collection '{collection_name}': {e}")
            return False


def main():
    """Main entry point"""
    # Load environment variables from .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # Get configuration from environment
    qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
    api_key = os.getenv('QDRANT_API_KEY')
    vector_size = int(os.getenv('VECTOR_SIZE', '1024'))
    distance_metric = os.getenv('VECTOR_DISTANCE', 'Cosine')

    # Create setup instance
    setup = QdrantSetup(
        qdrant_url=qdrant_url,
        api_key=api_key,
        vector_size=vector_size,
        distance_metric=distance_metric
    )

    # Run setup
    success = setup.setup_all_collections()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
