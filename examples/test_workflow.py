#!/usr/bin/env python3
"""
Test script for the Mistral → Qdrant workflow
Sends test data to the n8n webhook and verifies the results
"""

import os
import sys
import json
import requests
from typing import Dict, Any


class WorkflowTester:
    """Test utility for the Mistral-Qdrant separation workflow"""

    def __init__(self, webhook_url: str, qdrant_url: str = None, qdrant_api_key: str = None):
        """
        Initialize tester

        Args:
            webhook_url: n8n webhook URL
            qdrant_url: Qdrant instance URL
            qdrant_api_key: Qdrant API key (optional)
        """
        self.webhook_url = webhook_url
        self.qdrant_url = qdrant_url or os.getenv('QDRANT_URL', 'http://localhost:6333')
        self.qdrant_api_key = qdrant_api_key or os.getenv('QDRANT_API_KEY')

        self.qdrant_headers = {'Content-Type': 'application/json'}
        if self.qdrant_api_key:
            self.qdrant_headers['api-key'] = self.qdrant_api_key

    def test_simple_response(self) -> Dict[str, Any]:
        """Test with a simple Mistral response"""
        print("\n=== Test 1: Simple Response ===")

        test_data = {
            "mistral_response": """# Introduction

This is a simple test paragraph.

## Conclusion

Another paragraph here."""
        }

        return self._send_request(test_data, expected_text=2, expected_tables=0, expected_figures=0)

    def test_with_table(self) -> Dict[str, Any]:
        """Test with a response containing a table"""
        print("\n=== Test 2: Response with Table ===")

        test_data = {
            "mistral_response": """# Sales Report

Our quarterly results are shown below:

| Quarter | Revenue | Growth |
|---------|---------|--------|
| Q1      | $1M     | 10%    |
| Q2      | $1.2M   | 20%    |

Strong performance across the board."""
        }

        return self._send_request(test_data, expected_text=2, expected_tables=1, expected_figures=0)

    def test_with_figure(self) -> Dict[str, Any]:
        """Test with a response containing a figure"""
        print("\n=== Test 3: Response with Figure ===")

        test_data = {
            "mistral_response": """# Analysis

Here is the data analysis.

![Performance Chart](https://example.com/chart.png)

The chart shows positive trends."""
        }

        return self._send_request(test_data, expected_text=2, expected_tables=0, expected_figures=1)

    def test_complete_response(self) -> Dict[str, Any]:
        """Test with a complete response containing text, tables, and figures"""
        print("\n=== Test 4: Complete Response (Text + Tables + Figures) ===")

        test_data = {
            "mistral_response": """# Comprehensive Report

## Executive Summary

This report analyzes our performance across multiple dimensions.

## Financial Data

| Year | Revenue | Profit | Margin |
|------|---------|--------|--------|
| 2021 | $5M     | $1M    | 20%    |
| 2022 | $7M     | $1.5M  | 21.4%  |
| 2023 | $10M    | $2.5M  | 25%    |
| 2024 | $15M    | $4M    | 26.7%  |

The financial performance shows consistent growth year over year.

## Visual Analysis

![Revenue Growth Chart](https://example.com/revenue-chart.png)

![Profit Margin Trends](https://example.com/margin-chart.png)

Both charts demonstrate the upward trajectory of our business.

## Regional Performance

| Region     | Revenue | Growth Rate |
|------------|---------|-------------|
| North      | $6M     | 30%         |
| South      | $4M     | 20%         |
| East       | $3M     | 15%         |
| West       | $2M     | 10%         |

Regional analysis reveals strong performance in the North region.

## Conclusion

Overall, the company is performing exceptionally well with sustainable growth patterns."""
        }

        return self._send_request(test_data, expected_text=5, expected_tables=2, expected_figures=2)

    def test_html_table(self) -> Dict[str, Any]:
        """Test with HTML table format"""
        print("\n=== Test 5: HTML Table ===")

        test_data = {
            "mistral_response": """# HTML Table Test

<table>
  <thead>
    <tr>
      <th>Name</th>
      <th>Age</th>
      <th>City</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Alice</td>
      <td>30</td>
      <td>NYC</td>
    </tr>
    <tr>
      <td>Bob</td>
      <td>25</td>
      <td>LA</td>
    </tr>
  </tbody>
</table>

This table shows user data."""
        }

        return self._send_request(test_data, expected_text=1, expected_tables=1, expected_figures=0)

    def _send_request(
        self,
        data: Dict[str, Any],
        expected_text: int,
        expected_tables: int,
        expected_figures: int
    ) -> Dict[str, Any]:
        """
        Send request to webhook and verify results

        Args:
            data: Request payload
            expected_text: Expected number of text chunks
            expected_tables: Expected number of tables
            expected_figures: Expected number of figures

        Returns:
            Response from webhook
        """
        try:
            response = requests.post(self.webhook_url, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            print(f"✓ Request successful")
            print(f"  Response: {json.dumps(result, indent=2)}")

            # Verify counts
            if 'stats' in result:
                stats = result['stats']
                text_count = stats.get('text_chunks', 0)
                tables_count = stats.get('tables', 0)
                figures_count = stats.get('figures', 0)

                print(f"\n  Expected: {expected_text} text, {expected_tables} tables, {expected_figures} figures")
                print(f"  Actual:   {text_count} text, {tables_count} tables, {figures_count} figures")

                if (text_count == expected_text and
                    tables_count == expected_tables and
                    figures_count == expected_figures):
                    print(f"  ✓ Counts match!")
                else:
                    print(f"  ✗ Counts don't match!")

            return result

        except requests.exceptions.RequestException as e:
            print(f"✗ Request failed: {e}")
            return {"error": str(e)}

    def verify_qdrant_data(self) -> None:
        """Verify data was stored in Qdrant collections"""
        print("\n=== Verifying Qdrant Data ===")

        collections = ['mistral_text', 'mistral_tables', 'mistral_figures']

        for collection in collections:
            try:
                url = f"{self.qdrant_url}/collections/{collection}"
                response = requests.get(url, headers=self.qdrant_headers)
                response.raise_for_status()

                data = response.json()
                count = data.get('result', {}).get('points_count', 0)
                print(f"✓ Collection '{collection}': {count} points")

            except requests.exceptions.RequestException as e:
                print(f"✗ Failed to check collection '{collection}': {e}")

    def run_all_tests(self) -> None:
        """Run all tests"""
        print(f"\n{'='*60}")
        print("Testing Mistral → Qdrant Workflow")
        print(f"{'='*60}")
        print(f"Webhook URL: {self.webhook_url}")
        print(f"Qdrant URL: {self.qdrant_url}")

        tests = [
            self.test_simple_response,
            self.test_with_table,
            self.test_with_figure,
            self.test_complete_response,
            self.test_html_table
        ]

        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"✗ Test failed with exception: {e}")
                results.append({"error": str(e)})

        # Verify Qdrant data
        self.verify_qdrant_data()

        # Summary
        print(f"\n{'='*60}")
        print("Test Summary")
        print(f"{'='*60}")
        successful = sum(1 for r in results if 'success' in r and r['success'])
        print(f"Tests run: {len(results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(results) - successful}")


def main():
    """Main entry point"""
    # Get webhook URL from command line or environment
    webhook_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv('N8N_WEBHOOK_URL')

    if not webhook_url:
        print("Error: Webhook URL not provided")
        print("Usage: python test_workflow.py <webhook_url>")
        print("Or set N8N_WEBHOOK_URL environment variable")
        sys.exit(1)

    # Create tester and run tests
    tester = WorkflowTester(webhook_url)
    tester.run_all_tests()


if __name__ == '__main__':
    main()
