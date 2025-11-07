"""
Content Parser for Mistral Output
Separates text, tables, and figures from Mistral AI responses
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Any


class ContentParser:
    """Parser for separating Mistral AI output into text, tables, and figures"""

    def __init__(self):
        """Initialize the parser with regex patterns"""
        self.patterns = {
            # Markdown table pattern
            'markdown_table': re.compile(
                r'\|(.+)\|[\r\n]+\|[-:\s|]+\|[\r\n]+((?:\|.+\|[\r\n]+)+)',
                re.MULTILINE
            ),
            # HTML table pattern
            'html_table': re.compile(
                r'<table[\s\S]*?</table>',
                re.IGNORECASE
            ),
            # Markdown image pattern
            'markdown_image': re.compile(
                r'!\[([^\]]*)\]\(([^)]+)\)'
            ),
            # HTML image pattern
            'html_image': re.compile(
                r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>',
                re.IGNORECASE
            ),
            # Code blocks (optional)
            'code_block': re.compile(
                r'```[\s\S]*?```'
            ),
            # Math equations (optional)
            'math_equation': re.compile(
                r'\$\$[\s\S]*?\$\$'
            )
        }

    def parse(self, mistral_response: str) -> Dict[str, Any]:
        """
        Parse Mistral response and separate into content types

        Args:
            mistral_response: The raw response from Mistral AI

        Returns:
            Dictionary with separated content (text, tables, figures) and metadata
        """
        if not mistral_response or not isinstance(mistral_response, str):
            return {
                'text': [],
                'tables': [],
                'figures': [],
                'metadata': {
                    'total_text_chunks': 0,
                    'total_tables': 0,
                    'total_figures': 0,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }

        text_chunks = []
        tables = []
        figures = []

        # Extract tables (markdown format)
        for match in self.patterns['markdown_table'].finditer(mistral_response):
            content = match.group(0)
            headers = self._extract_table_headers(content)
            row_count = self._count_table_rows(content)

            tables.append({
                'content': content,
                'type': 'markdown',
                'index': match.start(),
                'metadata': {
                    'headers': headers,
                    'rows': row_count,
                    'columns': len(headers)
                }
            })

        # Extract tables (HTML format)
        for match in self.patterns['html_table'].finditer(mistral_response):
            content = match.group(0)
            headers = self._extract_html_table_headers(content)
            row_count = self._count_html_table_rows(content)

            tables.append({
                'content': content,
                'type': 'html',
                'index': match.start(),
                'metadata': {
                    'headers': headers,
                    'rows': row_count,
                    'columns': len(headers)
                }
            })

        # Extract figures (markdown images)
        for match in self.patterns['markdown_image'].finditer(mistral_response):
            alt_text = match.group(1) or 'Untitled figure'
            url = match.group(2)

            figures.append({
                'alt_text': alt_text,
                'url': url,
                'type': 'markdown',
                'index': match.start(),
                'metadata': {
                    'format': self._extract_image_format(url),
                    'has_alt': bool(match.group(1))
                }
            })

        # Extract figures (HTML images)
        for match in self.patterns['html_image'].finditer(mistral_response):
            url = match.group(1)

            figures.append({
                'url': url,
                'type': 'html',
                'index': match.start(),
                'metadata': {
                    'format': self._extract_image_format(url),
                    'has_alt': False
                }
            })

        # Remove tables and figures from response to extract pure text
        text_only = self._remove_extracted_content(mistral_response, tables, figures)

        # Split text into paragraphs/chunks
        paragraphs = [p.strip() for p in text_only.split('\n\n') if p.strip()]

        for idx, paragraph in enumerate(paragraphs):
            text_chunks.append({
                'content': paragraph,
                'chunk_index': idx,
                'type': self._detect_text_type(paragraph),
                'metadata': {
                    'word_count': len(paragraph.split()),
                    'char_count': len(paragraph)
                }
            })

        # Add indices to tables and figures
        indexed_tables = [
            {**table, 'table_index': idx}
            for idx, table in enumerate(tables)
        ]

        indexed_figures = [
            {**figure, 'figure_index': idx}
            for idx, figure in enumerate(figures)
        ]

        return {
            'text': text_chunks,
            'tables': indexed_tables,
            'figures': indexed_figures,
            'metadata': {
                'total_text_chunks': len(text_chunks),
                'total_tables': len(tables),
                'total_figures': len(figures),
                'timestamp': datetime.utcnow().isoformat()
            }
        }

    def _extract_table_headers(self, table_content: str) -> List[str]:
        """Extract headers from markdown table"""
        lines = table_content.split('\n')
        if len(lines) < 2:
            return []

        header_line = lines[0]
        return [h.strip() for h in header_line.split('|') if h.strip()]

    def _count_table_rows(self, table_content: str) -> int:
        """Count rows in markdown table (excluding header and separator)"""
        lines = [l for l in table_content.split('\n') if l.strip()]
        return max(0, len(lines) - 2)

    def _extract_html_table_headers(self, html_table: str) -> List[str]:
        """Extract headers from HTML table"""
        thead_match = re.search(r'<thead[\s\S]*?>([\s\S]*?)</thead>', html_table, re.IGNORECASE)

        if thead_match:
            return self._extract_cell_contents(thead_match.group(1), 'th')
        else:
            first_row_match = re.search(r'<tr[\s\S]*?>([\s\S]*?)</tr>', html_table, re.IGNORECASE)
            if first_row_match:
                return self._extract_cell_contents(first_row_match.group(1), r'th|td')

        return []

    def _count_html_table_rows(self, html_table: str) -> int:
        """Count rows in HTML table"""
        rows = re.findall(r'<tr[\s\S]*?>', html_table, re.IGNORECASE)
        return len(rows)

    def _extract_cell_contents(self, html: str, tag_pattern: str) -> List[str]:
        """Extract cell contents from HTML"""
        regex = re.compile(f'<({tag_pattern})[^>]*>([\\s\\S]*?)</\\1>', re.IGNORECASE)
        cells = []

        for match in regex.finditer(html):
            cell_content = re.sub(r'<[^>]+>', '', match.group(2)).strip()
            cells.append(cell_content)

        return cells

    def _extract_image_format(self, url: str) -> str:
        """Extract image format from URL"""
        match = re.search(r'\.([a-z0-9]+)(?:[?#]|$)', url, re.IGNORECASE)
        return match.group(1).lower() if match else 'unknown'

    def _remove_extracted_content(
        self,
        text: str,
        tables: List[Dict],
        figures: List[Dict]
    ) -> str:
        """Remove extracted tables and figures from text"""
        # Create list of all content to remove
        removals = []

        for table in tables:
            removals.append({
                'index': table['index'],
                'length': len(table['content'])
            })

        for figure in figures:
            if figure['type'] == 'markdown':
                removal_text = f"![{figure.get('alt_text', '')}]({figure['url']})"
                removals.append({
                    'index': figure['index'],
                    'length': len(removal_text)
                })
            else:  # HTML
                match = re.search(r'<img[^>]+>', text[figure['index']:])
                if match:
                    removals.append({
                        'index': figure['index'],
                        'length': len(match.group(0))
                    })

        # Sort by index (descending) to avoid offset issues
        removals.sort(key=lambda x: x['index'], reverse=True)

        # Remove each piece
        result = text
        for removal in removals:
            idx = removal['index']
            length = removal['length']
            result = result[:idx] + result[idx + length:]

        return result

    def _detect_text_type(self, text: str) -> str:
        """Detect the type of text content"""
        if text.startswith('#'):
            return 'heading'
        if re.match(r'^[\s]*[-*+]\s', text, re.MULTILINE):
            return 'unordered_list'
        if re.match(r'^[\s]*\d+\.\s', text, re.MULTILINE):
            return 'ordered_list'
        if text.startswith('```'):
            return 'code_block'
        if text.startswith('$$'):
            return 'math_equation'
        return 'paragraph'


# Example usage
if __name__ == '__main__':
    parser = ContentParser()

    example_response = """# Analysis Report

This is the introduction paragraph with some analysis.

| Year | Revenue | Growth |
|------|---------|--------|
| 2023 | $1M     | 20%    |
| 2024 | $1.2M   | 20%    |

The table above shows our growth over two years.

![Sales Chart](https://example.com/chart.png)

## Conclusion

We see strong performance across all metrics."""

    result = parser.parse(example_response)
    print(json.dumps(result, indent=2))
