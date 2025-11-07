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
      mathEquation: /\$\$[\s\S]*?\$\$/g,

      // Heading pattern for document structure
      heading: /^(#{1,6})\s+(.+)$/gm
    };
    this.documentStructure = [];
    this.currentSection = null;
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

    // Build document structure first
    const sections = this.buildDocumentStructure(mistralResponse);

    // Extract tables (markdown format)
    let tableMatch;
    while ((tableMatch = this.patterns.markdownTable.exec(mistralResponse)) !== null) {
      const headers = this.extractTableHeaders(tableMatch[0]);
      const rowCount = this.countTableRows(tableMatch[0]);
      const elementIndex = tableMatch.index;

      // Extract title and context
      const titleInfo = this.extractTitleForElement(mistralResponse, elementIndex);
      const sectionId = this.findSectionForElement(elementIndex, sections);
      const parentSection = sections.find(s => s.id === sectionId)?.parent_id || null;

      tables.push({
        content: tableMatch[0],
        type: 'markdown',
        index: elementIndex,
        title: titleInfo.title,
        context: titleInfo.context,
        metadata: {
          headers: headers,
          rows: rowCount,
          columns: headers.length
        },
        relations: {
          section_id: sectionId,
          parent_section: parentSection,
          references: []
        }
      });
    }

    // Extract tables (HTML format)
    let htmlTableMatch;
    while ((htmlTableMatch = this.patterns.htmlTable.exec(mistralResponse)) !== null) {
      const headers = this.extractHTMLTableHeaders(htmlTableMatch[0]);
      const rowCount = this.countHTMLTableRows(htmlTableMatch[0]);
      const elementIndex = htmlTableMatch.index;

      // Extract title and context
      const titleInfo = this.extractTitleForElement(mistralResponse, elementIndex);
      const sectionId = this.findSectionForElement(elementIndex, sections);
      const parentSection = sections.find(s => s.id === sectionId)?.parent_id || null;

      tables.push({
        content: htmlTableMatch[0],
        type: 'html',
        index: elementIndex,
        title: titleInfo.title,
        context: titleInfo.context,
        metadata: {
          headers: headers,
          rows: rowCount,
          columns: headers.length
        },
        relations: {
          section_id: sectionId,
          parent_section: parentSection,
          references: []
        }
      });
    }

    // Extract figures (markdown images)
    let imageMatch;
    while ((imageMatch = this.patterns.markdownImage.exec(mistralResponse)) !== null) {
      const elementIndex = imageMatch.index;
      const titleInfo = this.extractTitleForElement(mistralResponse, elementIndex);
      const sectionId = this.findSectionForElement(elementIndex, sections);
      const parentSection = sections.find(s => s.id === sectionId)?.parent_id || null;

      figures.push({
        alt_text: imageMatch[1] || 'Untitled figure',
        url: imageMatch[2],
        type: 'markdown',
        index: elementIndex,
        title: titleInfo.title,
        context: titleInfo.context,
        metadata: {
          format: this.extractImageFormat(imageMatch[2]),
          has_alt: Boolean(imageMatch[1])
        },
        relations: {
          section_id: sectionId,
          parent_section: parentSection,
          references: []
        }
      });
    }

    // Extract figures (HTML images)
    let htmlImageMatch;
    while ((htmlImageMatch = this.patterns.htmlImage.exec(mistralResponse)) !== null) {
      const elementIndex = htmlImageMatch.index;
      const titleInfo = this.extractTitleForElement(mistralResponse, elementIndex);
      const sectionId = this.findSectionForElement(elementIndex, sections);
      const parentSection = sections.find(s => s.id === sectionId)?.parent_id || null;

      figures.push({
        url: htmlImageMatch[1],
        type: 'html',
        index: elementIndex,
        title: titleInfo.title,
        context: titleInfo.context,
        metadata: {
          format: this.extractImageFormat(htmlImageMatch[1]),
          has_alt: false
        },
        relations: {
          section_id: sectionId,
          parent_section: parentSection,
          references: []
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
      // Find which section this paragraph belongs to
      const paraPosition = mistralResponse.indexOf(paragraph);
      const sectionId = paraPosition !== -1 ? this.findSectionForElement(paraPosition, sections) : null;
      const parentSection = sectionId ? (sections.find(s => s.id === sectionId)?.parent_id || null) : null;

      textChunks.push({
        content: paragraph,
        chunk_index: idx,
        type: this.detectTextType(paragraph),
        metadata: {
          word_count: paragraph.split(/\s+/).length,
          char_count: paragraph.length
        },
        relations: {
          section_id: sectionId,
          parent_section: parentSection
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

    // Build relationships between elements
    const allElements = [...indexedTables, ...indexedFigures, ...textChunks];
    for (const table of indexedTables) {
      table.relations.references = this.findRelatedElements(
        table.content + ' ' + (table.context || ''),
        allElements,
        'table'
      );
    }

    for (const figure of indexedFigures) {
      const contextText = (figure.context || '') + ' ' + (figure.alt_text || '');
      figure.relations.references = this.findRelatedElements(
        contextText,
        allElements,
        'figure'
      );
    }

    return {
      text: textChunks,
      tables: indexedTables,
      figures: indexedFigures,
      sections: sections,
      metadata: {
        total_text_chunks: textChunks.length,
        total_tables: tables.length,
        total_figures: figures.length,
        total_sections: sections.length,
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

  /**
   * Extract title and context for a table or figure
   * @param {string} text - The full document text
   * @param {number} elementIndex - Position of the element
   * @param {number} contextLines - Number of lines to look back
   * @returns {Object} Title and context information
   */
  extractTitleForElement(text, elementIndex, contextLines = 3) {
    const textBefore = text.substring(0, elementIndex).trim();
    const linesBefore = textBefore.split('\n');

    let title = null;
    let contextText = '';

    // Look for the last heading before this element
    for (let i = linesBefore.length - 1; i >= Math.max(0, linesBefore.length - 10); i--) {
      const line = linesBefore[i].trim();
      const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
      if (headingMatch) {
        title = headingMatch[2].trim();
        break;
      }
    }

    // Get context (last few lines before element)
    const contextLinesList = linesBefore.slice(-contextLines);
    contextText = contextLinesList.join('\n').trim();

    // If no heading found, use last sentence from context
    if (!title && contextText) {
      const sentences = contextText.split(/[.!?]+/);
      if (sentences.length > 0) {
        title = sentences[sentences.length - 1].trim().substring(0, 100);
      }
    }

    return {
      title: title || 'Untitled',
      context: contextText.substring(0, 500)
    };
  }

  /**
   * Build hierarchical document structure from headings
   * @param {string} text - The full document text
   * @returns {Array} List of section objects with hierarchy
   */
  buildDocumentStructure(text) {
    const sections = [];
    const parentStack = [];
    const headingRegex = /^(#{1,6})\s+(.+)$/gm;
    let match;

    while ((match = headingRegex.exec(text)) !== null) {
      const level = match[1].length;
      const headingText = match[2].trim();
      const position = match.index;

      const section = {
        id: `section_${sections.length}`,
        level: level,
        title: headingText,
        position: position,
        parent_id: null,
        children: []
      };

      // Update parent stack
      while (parentStack.length > 0 && parentStack[parentStack.length - 1].level >= level) {
        parentStack.pop();
      }

      // Set parent relationship
      if (parentStack.length > 0) {
        const parent = parentStack[parentStack.length - 1];
        section.parent_id = parent.id;
        parent.children.push(section.id);
      }

      parentStack.push(section);
      sections.push(section);
    }

    return sections;
  }

  /**
   * Find which section an element belongs to
   * @param {number} elementIndex - Position of element
   * @param {Array} sections - List of document sections
   * @returns {string|null} Section ID or null
   */
  findSectionForElement(elementIndex, sections) {
    let currentSection = null;
    for (const section of sections) {
      if (section.position <= elementIndex) {
        currentSection = section.id;
      } else {
        break;
      }
    }
    return currentSection;
  }

  /**
   * Find related elements by looking for references
   * @param {string} elementContent - Content to search for references
   * @param {Array} allElements - All elements to search
   * @param {string} elementType - Type of current element
   * @returns {Array} List of related element IDs
   */
  findRelatedElements(elementContent, allElements, elementType) {
    const related = [];
    const referencePatterns = {
      table: /\b(?:table|tbl\.?)\s*(\d+)/gi,
      figure: /\b(?:figure|fig\.?|image)\s*(\d+)/gi
    };

    for (const [patternType, pattern] of Object.entries(referencePatterns)) {
      let match;
      while ((match = pattern.exec(elementContent.toLowerCase())) !== null) {
        const refNumber = match[1];
        // Find element with matching index
        for (const elem of allElements) {
          if (elem.type === patternType) {
            const elemIdx = elem[`${patternType}_index`];
            if (elemIdx !== undefined && String(elemIdx + 1) === refNumber) {
              related.push(`${patternType}_${elemIdx}`);
            }
          }
        }
      }
    }

    return related;
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
