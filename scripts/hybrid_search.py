#!/usr/bin/env python3
"""
Hybrid Search Utilities for Qdrant
Combines vector similarity search with keyword filtering for enhanced retrieval
"""

import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime


class HybridSearch:
    """Hybrid search combining vector similarity and keyword filtering"""

    def __init__(
        self,
        qdrant_url: str = None,
        api_key: str = None,
        mistral_api_key: str = None
    ):
        """
        Initialize hybrid search

        Args:
            qdrant_url: Qdrant instance URL
            api_key: Qdrant API key (optional)
            mistral_api_key: Mistral API key for embedding generation
        """
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.api_key = api_key or os.getenv('QDRANT_API_KEY')
        self.mistral_api_key = mistral_api_key or os.getenv('MISTRAL_API_KEY')

        self.headers = {'Content-Type': 'application/json'}
        if self.api_key:
            self.headers['api-key'] = self.api_key

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using Mistral Embed

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        url = "https://api.mistral.ai/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.mistral_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistral-embed",
            "input": [text]
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data['data'][0]['embedding']
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to generate embedding: {e}")

    def search(
        self,
        collection_name: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 5,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and keyword filtering

        Args:
            collection_name: Name of the collection to search
            query: Search query text
            filters: Optional filters to apply (e.g., {"type": "table", "section_id": "section_0"})
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score threshold

        Returns:
            List of search results with scores and payloads
        """
        # Generate embedding for query
        query_vector = self.generate_embedding(query)

        # Build search payload
        search_payload = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True,
            "with_vector": False
        }

        # Add score threshold if specified
        if score_threshold > 0:
            search_payload["score_threshold"] = score_threshold

        # Add filters if specified
        if filters:
            filter_conditions = self._build_filter_conditions(filters)
            if filter_conditions:
                search_payload["filter"] = filter_conditions

        # Execute search
        url = f"{self.qdrant_url}/collections/{collection_name}/points/search"
        try:
            response = requests.post(url, json=search_payload, headers=self.headers)
            response.raise_for_status()
            results = response.json()
            return results.get('result', [])
        except requests.exceptions.RequestException as e:
            raise Exception(f"Search failed: {e}")

    def multi_collection_search(
        self,
        query: str,
        collections: List[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit_per_collection: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across multiple collections simultaneously

        Args:
            query: Search query text
            collections: List of collection names (defaults to all Mistral collections)
            filters: Optional filters to apply to all searches
            limit_per_collection: Maximum results per collection

        Returns:
            Dictionary mapping collection names to search results
        """
        if collections is None:
            collections = ['mistral_text', 'mistral_tables', 'mistral_figures']

        results = {}
        for collection in collections:
            try:
                results[collection] = self.search(
                    collection_name=collection,
                    query=query,
                    filters=filters,
                    limit=limit_per_collection
                )
            except Exception as e:
                print(f"Warning: Search in {collection} failed: {e}")
                results[collection] = []

        return results

    def search_by_section(
        self,
        query: str,
        section_id: str,
        collections: List[str] = None,
        limit: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search within a specific document section

        Args:
            query: Search query text
            section_id: Section ID to search within
            collections: Collections to search (defaults to all)
            limit: Maximum total results

        Returns:
            Search results grouped by collection
        """
        filters = {"relations.section_id": section_id}
        return self.multi_collection_search(
            query=query,
            collections=collections,
            filters=filters,
            limit_per_collection=limit
        )

    def find_related_content(
        self,
        element_type: str,
        element_index: int,
        collection_name: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find content related to a specific element (table or figure)

        Args:
            element_type: Type of element ('table' or 'figure')
            element_index: Index of the element
            collection_name: Collection to search (auto-detected if None)
            limit: Maximum results

        Returns:
            List of related content items
        """
        if collection_name is None:
            collection_name = f"mistral_{element_type}s"

        # First, get the element itself
        element_id = f"{element_type}_{element_index}"
        filters = {"id": element_id}

        try:
            # Get the element's context and section
            results = self.search(
                collection_name=collection_name,
                query="",  # We'll use filters only
                filters=filters,
                limit=1
            )

            if not results:
                return []

            element = results[0]['payload']
            section_id = element.get('relations', {}).get('section_id')

            # Search for related content in the same section
            if section_id:
                return self.search_by_section(
                    query=element.get('context', ''),
                    section_id=section_id,
                    limit=limit
                )
        except Exception as e:
            print(f"Error finding related content: {e}")
            return []

    def _build_filter_conditions(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Qdrant filter conditions from simple key-value filters

        Args:
            filters: Dictionary of field names and values

        Returns:
            Qdrant filter condition object
        """
        must_conditions = []

        for field, value in filters.items():
            if isinstance(value, list):
                # Multiple values - use "should" (OR)
                should_conditions = [
                    {
                        "key": field,
                        "match": {"value": v}
                    }
                    for v in value
                ]
                must_conditions.append({
                    "should": should_conditions
                })
            else:
                # Single value - use "must" (AND)
                must_conditions.append({
                    "key": field,
                    "match": {"value": value}
                })

        if len(must_conditions) == 1:
            return must_conditions[0]
        elif len(must_conditions) > 1:
            return {"must": must_conditions}
        else:
            return {}


def main():
    """Example usage of hybrid search"""
    from dotenv import load_dotenv
    load_dotenv()

    # Initialize hybrid search
    searcher = HybridSearch()

    # Example 1: Basic search
    print("Example 1: Basic search in tables collection")
    results = searcher.search(
        collection_name="mistral_tables",
        query="revenue growth analysis",
        limit=3
    )
    print(f"Found {len(results)} results\n")

    # Example 2: Search with filters
    print("Example 2: Search with type filter")
    results = searcher.search(
        collection_name="mistral_text",
        query="machine learning",
        filters={"type": "paragraph"},
        limit=5
    )
    print(f"Found {len(results)} results\n")

    # Example 3: Multi-collection search
    print("Example 3: Search across all collections")
    results = searcher.multi_collection_search(
        query="performance metrics",
        limit_per_collection=2
    )
    for collection, items in results.items():
        print(f"{collection}: {len(items)} results")
    print()

    # Example 4: Section-based search
    print("Example 4: Search within a specific section")
    results = searcher.search_by_section(
        query="data analysis",
        section_id="section_0",
        limit=3
    )
    print(f"Found results in {len(results)} collections\n")


if __name__ == '__main__':
    main()
