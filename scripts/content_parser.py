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
            ),
            # Heading pattern for document structure
            'heading': re.compile(
                r'^(#{1,6})\s+(.+)$',
                re.MULTILINE
            )
        }
        self.document_structure = []
        self.current_section = None

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

        # Build document structure first
        sections = self._build_document_structure(mistral_response)

        # Extract tables (markdown format)
        for match in self.patterns['markdown_table'].finditer(mistral_response):
            content = match.group(0)
            headers = self._extract_table_headers(content)
            row_count = self._count_table_rows(content)
            element_index = match.start()

            # Extract title and context
            title_info = self._extract_title_for_element(mistral_response, element_index)
            section_id = self._find_section_for_element(element_index, sections)

            tables.append({
                'content': content,
                'type': 'markdown',
                'index': element_index,
                'title': title_info['title'],
                'context': title_info['context'],
                'metadata': {
                    'headers': headers,
                    'rows': row_count,
                    'columns': len(headers)
                },
                'relations': {
                    'section_id': section_id,
                    'parent_section': next((s['parent_id'] for s in sections if s['id'] == section_id), None),
                    'references': []  # Will be populated after all elements are extracted
                }
            })

        # Extract tables (HTML format)
        for match in self.patterns['html_table'].finditer(mistral_response):
            content = match.group(0)
            headers = self._extract_html_table_headers(content)
            row_count = self._count_html_table_rows(content)
            element_index = match.start()

            # Extract title and context
            title_info = self._extract_title_for_element(mistral_response, element_index)
            section_id = self._find_section_for_element(element_index, sections)

            tables.append({
                'content': content,
                'type': 'html',
                'index': element_index,
                'title': title_info['title'],
                'context': title_info['context'],
                'metadata': {
                    'headers': headers,
                    'rows': row_count,
                    'columns': len(headers)
                },
                'relations': {
                    'section_id': section_id,
                    'parent_section': next((s['parent_id'] for s in sections if s['id'] == section_id), None),
                    'references': []
                }
            })

        # Extract figures (markdown images)
        for match in self.patterns['markdown_image'].finditer(mistral_response):
            alt_text = match.group(1) or 'Untitled figure'
            url = match.group(2)
            element_index = match.start()

            # Extract title and context
            title_info = self._extract_title_for_element(mistral_response, element_index)
            section_id = self._find_section_for_element(element_index, sections)

            figures.append({
                'alt_text': alt_text,
                'url': url,
                'type': 'markdown',
                'index': element_index,
                'title': title_info['title'],
                'context': title_info['context'],
                'metadata': {
                    'format': self._extract_image_format(url),
                    'has_alt': bool(match.group(1))
                },
                'relations': {
                    'section_id': section_id,
                    'parent_section': next((s['parent_id'] for s in sections if s['id'] == section_id), None),
                    'references': []
                }
            })

        # Extract figures (HTML images)
        for match in self.patterns['html_image'].finditer(mistral_response):
            url = match.group(1)
            element_index = match.start()

            # Extract title and context
            title_info = self._extract_title_for_element(mistral_response, element_index)
            section_id = self._find_section_for_element(element_index, sections)

            figures.append({
                'url': url,
                'type': 'html',
                'index': element_index,
                'title': title_info['title'],
                'context': title_info['context'],
                'metadata': {
                    'format': self._extract_image_format(url),
                    'has_alt': False
                },
                'relations': {
                    'section_id': section_id,
                    'parent_section': next((s['parent_id'] for s in sections if s['id'] == section_id), None),
                    'references': []
                }
            })

        # Remove tables and figures from response to extract pure text
        text_only = self._remove_extracted_content(mistral_response, tables, figures)

        # Split text into paragraphs/chunks
        paragraphs = [p.strip() for p in text_only.split('\n\n') if p.strip()]

        for idx, paragraph in enumerate(paragraphs):
            # Find which section this paragraph belongs to
            para_position = mistral_response.find(paragraph)
            section_id = self._find_section_for_element(para_position, sections) if para_position != -1 else None

            text_chunks.append({
                'content': paragraph,
                'chunk_index': idx,
                'type': self._detect_text_type(paragraph),
                'metadata': {
                    'word_count': len(paragraph.split()),
                    'char_count': len(paragraph)
                },
                'relations': {
                    'section_id': section_id,
                    'parent_section': next((s['parent_id'] for s in sections if s['id'] == section_id), None) if section_id else None
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

        # Build relationships between elements (find references)
        all_elements = indexed_tables + indexed_figures + text_chunks
        for table in indexed_tables:
            table['relations']['references'] = self._find_related_elements(
                table['content'] + ' ' + table.get('context', ''),
                all_elements,
                'table'
            )

        for figure in indexed_figures:
            context_text = figure.get('context', '') + ' ' + figure.get('alt_text', '')
            figure['relations']['references'] = self._find_related_elements(
                context_text,
                all_elements,
                'figure'
            )

        return {
            'text': text_chunks,
            'tables': indexed_tables,
            'figures': indexed_figures,
            'sections': sections,
            'metadata': {
                'total_text_chunks': len(text_chunks),
                'total_tables': len(tables),
                'total_figures': len(figures),
                'total_sections': len(sections),
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

    def _extract_title_for_element(self, text: str, element_index: int, context_lines: int = 3) -> Dict[str, str]:
        """
        Extract title and context for a table or figure by looking at surrounding text

        Args:
            text: The full document text
            element_index: Position of the element in the text
            context_lines: Number of lines to look back for title

        Returns:
            Dictionary with title and context information
        """
        # Get text before the element
        text_before = text[:element_index].strip()
        lines_before = text_before.split('\n')

        # Look for the last heading or sentence before this element
        title = None
        context_text = ""

        # Check for heading in previous lines (prioritize closest heading)
        for i in range(len(lines_before) - 1, max(0, len(lines_before) - 10), -1):
            line = lines_before[i].strip()
            heading_match = self.patterns['heading'].match(line)
            if heading_match:
                title = heading_match.group(2).strip()
                break

        # Get context (last few sentences before element)
        context_lines_list = lines_before[-context_lines:] if len(lines_before) >= context_lines else lines_before
        context_text = '\n'.join(context_lines_list).strip()

        # If no heading found, use first sentence from context as title
        if not title and context_text:
            sentences = re.split(r'[.!?]+', context_text)
            if sentences:
                title = sentences[-1].strip()[:100]  # Limit title length

        return {
            'title': title or 'Untitled',
            'context': context_text[:500]  # Limit context length
        }

    def _build_document_structure(self, text: str) -> List[Dict[str, Any]]:
        """
        Build hierarchical document structure from headings

        Args:
            text: The full document text

        Returns:
            List of section dictionaries with hierarchy information
        """
        sections = []
        parent_stack = []  # Track parent sections at each level

        for match in self.patterns['heading'].finditer(text):
            level = len(match.group(1))  # Count # symbols
            heading_text = match.group(2).strip()
            position = match.start()

            section = {
                'id': f'section_{len(sections)}',
                'level': level,
                'title': heading_text,
                'position': position,
                'parent_id': None,
                'children': []
            }

            # Update parent stack
            while parent_stack and parent_stack[-1]['level'] >= level:
                parent_stack.pop()

            # Set parent relationship
            if parent_stack:
                parent = parent_stack[-1]
                section['parent_id'] = parent['id']
                parent['children'].append(section['id'])

            parent_stack.append(section)
            sections.append(section)

        return sections

    def _find_section_for_element(self, element_index: int, sections: List[Dict]) -> str:
        """
        Find which section an element belongs to based on its position

        Args:
            element_index: Position of element in text
            sections: List of document sections

        Returns:
            Section ID or None
        """
        current_section = None
        for section in sections:
            if section['position'] <= element_index:
                current_section = section['id']
            else:
                break
        return current_section

    def _find_related_elements(
        self,
        element_content: str,
        all_elements: List[Dict],
        element_type: str
    ) -> List[str]:
        """
        Find related elements by looking for references in content

        Args:
            element_content: Content of the current element
            all_elements: All other elements to search
            element_type: Type of current element (table/figure)

        Returns:
            List of related element IDs
        """
        related = []

        # Look for references like "Figure 1", "Table 2", etc.
        reference_patterns = {
            'table': re.compile(r'\b(?:table|tbl\.?)\s*(\d+)', re.IGNORECASE),
            'figure': re.compile(r'\b(?:figure|fig\.?|image)\s*(\d+)', re.IGNORECASE)
        }

        for pattern_type, pattern in reference_patterns.items():
            matches = pattern.findall(element_content.lower())
            for match in matches:
                # Find element with matching index
                target_type = pattern_type
                for elem in all_elements:
                    if elem.get('type') == target_type:
                        elem_idx = elem.get(f'{target_type}_index', -1)
                        if str(elem_idx + 1) == match:  # +1 because human numbering starts at 1
                            related.append(f"{target_type}_{elem_idx}")

        return related


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
