/**
 * Content Parser for Mistral Output
 * Separates text, tables, and figures from Mistral AI responses
 */

class ContentParser {
  constructor() {
    // Regex patterns for content detection
    this.patterns = {
      // Markdown table pattern: | col1 | col2 |
      markdownTable: /\|(.+)\|[\r\n]+\|[-:\s|]+\|[\r\n]+((?:\|.+\|[\r\n]+)+)/g,

      // HTML table pattern
      htmlTable: /<table[\s\S]*?<\/table>/gi,

      // Markdown image pattern: ![alt](url)
      markdownImage: /!\[([^\]]*)\]\(([^)]+)\)/g,

      // HTML image pattern: <img src="url">
      htmlImage: /<img[^>]+src=["']([^"']+)["'][^>]*>/gi,

      // Code blocks (optional - can be treated as text or separate type)
      codeBlock: /```[\s\S]*?```/g,

      // Math equations (optional)
      mathEquation: /\$\$[\s\S]*?\$\$/g
    };
  }

  /**
   * Parse Mistral response and separate into content types
   * @param {string} mistralResponse - The raw response from Mistral AI
   * @returns {Object} Separated content with text, tables, and figures
   */
  parse(mistralResponse) {
    if (!mistralResponse || typeof mistralResponse !== 'string') {
      return {
        text: [],
        tables: [],
        figures: [],
        metadata: {
          total_text_chunks: 0,
          total_tables: 0,
          total_figures: 0,
          timestamp: new Date().toISOString()
        }
      };
    }

    const textChunks = [];
    const tables = [];
    const figures = [];

    // Extract tables (markdown format)
    let tableMatch;
    while ((tableMatch = this.patterns.markdownTable.exec(mistralResponse)) !== null) {
      const headers = this.extractTableHeaders(tableMatch[0]);
      const rowCount = this.countTableRows(tableMatch[0]);

      tables.push({
        content: tableMatch[0],
        type: 'markdown',
        index: tableMatch.index,
        metadata: {
          headers: headers,
          rows: rowCount,
          columns: headers.length
        }
      });
    }

    // Extract tables (HTML format)
    let htmlTableMatch;
    while ((htmlTableMatch = this.patterns.htmlTable.exec(mistralResponse)) !== null) {
      const headers = this.extractHTMLTableHeaders(htmlTableMatch[0]);
      const rowCount = this.countHTMLTableRows(htmlTableMatch[0]);

      tables.push({
        content: htmlTableMatch[0],
        type: 'html',
        index: htmlTableMatch.index,
        metadata: {
          headers: headers,
          rows: rowCount,
          columns: headers.length
        }
      });
    }

    // Extract figures (markdown images)
    let imageMatch;
    while ((imageMatch = this.patterns.markdownImage.exec(mistralResponse)) !== null) {
      figures.push({
        alt_text: imageMatch[1] || 'Untitled figure',
        url: imageMatch[2],
        type: 'markdown',
        index: imageMatch.index,
        metadata: {
          format: this.extractImageFormat(imageMatch[2]),
          has_alt: Boolean(imageMatch[1])
        }
      });
    }

    // Extract figures (HTML images)
    let htmlImageMatch;
    while ((htmlImageMatch = this.patterns.htmlImage.exec(mistralResponse)) !== null) {
      figures.push({
        url: htmlImageMatch[1],
        type: 'html',
        index: htmlImageMatch.index,
        metadata: {
          format: this.extractImageFormat(htmlImageMatch[1]),
          has_alt: false
        }
      });
    }

    // Remove tables and figures from response to extract pure text
    let textOnly = this.removeExtractedContent(mistralResponse, tables, figures);

    // Split text into paragraphs/chunks
    const paragraphs = textOnly
      .split(/\n\n+/)
      .map(p => p.trim())
      .filter(p => p.length > 0);

    paragraphs.forEach((paragraph, idx) => {
      textChunks.push({
        content: paragraph,
        chunk_index: idx,
        type: this.detectTextType(paragraph),
        metadata: {
          word_count: paragraph.split(/\s+/).length,
          char_count: paragraph.length
        }
      });
    });

    // Add indices to tables and figures
    const indexedTables = tables.map((t, idx) => ({
      ...t,
      table_index: idx
    }));

    const indexedFigures = figures.map((f, idx) => ({
      ...f,
      figure_index: idx
    }));

    return {
      text: textChunks,
      tables: indexedTables,
      figures: indexedFigures,
      metadata: {
        total_text_chunks: textChunks.length,
        total_tables: tables.length,
        total_figures: figures.length,
        timestamp: new Date().toISOString()
      }
    };
  }

  /**
   * Extract headers from markdown table
   * @param {string} tableContent - Markdown table content
   * @returns {Array} Array of header names
   */
  extractTableHeaders(tableContent) {
    const lines = tableContent.split('\n');
    if (lines.length < 2) return [];

    const headerLine = lines[0];
    return headerLine
      .split('|')
      .filter(h => h.trim())
      .map(h => h.trim());
  }

  /**
   * Count rows in markdown table
   * @param {string} tableContent - Markdown table content
   * @returns {number} Number of data rows (excluding header and separator)
   */
  countTableRows(tableContent) {
    const lines = tableContent.split('\n').filter(l => l.trim());
    return Math.max(0, lines.length - 2); // Subtract header and separator lines
  }

  /**
   * Extract headers from HTML table
   * @param {string} htmlTable - HTML table content
   * @returns {Array} Array of header names
   */
  extractHTMLTableHeaders(htmlTable) {
    const theadMatch = htmlTable.match(/<thead[\s\S]*?>([\s\S]*?)<\/thead>/i);
    if (!theadMatch) {
      const firstRowMatch = htmlTable.match(/<tr[\s\S]*?>([\s\S]*?)<\/tr>/i);
      if (!firstRowMatch) return [];
      return this.extractCellContents(firstRowMatch[1], 'th|td');
    }
    return this.extractCellContents(theadMatch[1], 'th');
  }

  /**
   * Count rows in HTML table
   * @param {string} htmlTable - HTML table content
   * @returns {number} Number of rows
   */
  countHTMLTableRows(htmlTable) {
    const rows = htmlTable.match(/<tr[\s\S]*?>/gi);
    return rows ? rows.length : 0;
  }

  /**
   * Extract cell contents from HTML
   * @param {string} html - HTML content
   * @param {string} tagPattern - Tag pattern (e.g., 'th', 'td', 'th|td')
   * @returns {Array} Array of cell contents
   */
  extractCellContents(html, tagPattern) {
    const regex = new RegExp(`<(${tagPattern})[^>]*>([\\s\\S]*?)<\\/\\1>`, 'gi');
    const cells = [];
    let match;
    while ((match = regex.exec(html)) !== null) {
      cells.push(match[2].trim().replace(/<[^>]+>/g, ''));
    }
    return cells;
  }

  /**
   * Extract image format from URL
   * @param {string} url - Image URL
   * @returns {string} Image format (e.g., 'png', 'jpg', 'svg')
   */
  extractImageFormat(url) {
    const match = url.match(/\.([a-z0-9]+)(?:[?#]|$)/i);
    return match ? match[1].toLowerCase() : 'unknown';
  }

  /**
   * Remove extracted tables and figures from text
   * @param {string} text - Original text
   * @param {Array} tables - Extracted tables
   * @param {Array} figures - Extracted figures
   * @returns {string} Text with tables and figures removed
   */
  removeExtractedContent(text, tables, figures) {
    let result = text;

    // Create array of all content to remove
    const removals = [
      ...tables.map(t => ({ index: t.index, length: t.content.length })),
      ...figures.map(f => {
        if (f.type === 'markdown') {
          return {
            index: f.index,
            length: `![${f.alt_text}](${f.url})`.length
          };
        } else {
          const match = text.substring(f.index).match(/<img[^>]+>/);
          return {
            index: f.index,
            length: match ? match[0].length : 0
          };
        }
      })
    ];

    // Sort by index (descending) to avoid offset issues when removing
    removals.sort((a, b) => b.index - a.index);

    // Remove each piece
    for (const removal of removals) {
      result = result.substring(0, removal.index) + result.substring(removal.index + removal.length);
    }

    return result;
  }

  /**
   * Detect the type of text content
   * @param {string} text - Text content
   * @returns {string} Text type (heading, list, paragraph, etc.)
   */
  detectTextType(text) {
    if (text.startsWith('#')) return 'heading';
    if (text.match(/^[\s]*[-*+]\s/m)) return 'unordered_list';
    if (text.match(/^[\s]*\d+\.\s/m)) return 'ordered_list';
    if (text.match(/^```/)) return 'code_block';
    if (text.match(/^\$\$/)) return 'math_equation';
    return 'paragraph';
  }
}

// Export for use in Node.js or n8n
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ContentParser;
}

// Example usage
if (require.main === module) {
  const parser = new ContentParser();

  const exampleResponse = `# Analysis Report

This is the introduction paragraph with some analysis.

| Year | Revenue | Growth |
|------|---------|--------|
| 2023 | $1M     | 20%    |
| 2024 | $1.2M   | 20%    |

The table above shows our growth over two years.

![Sales Chart](https://example.com/chart.png)

## Conclusion

We see strong performance across all metrics.`;

  const result = parser.parse(exampleResponse);
  console.log(JSON.stringify(result, null, 2));
}
