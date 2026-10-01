import React from 'react';

/**
 * Format inline markdown tokens:
 * - **bold**
 * - *italic*
 * - `code`
 */
function renderInline(text) {
  if (!text) return null;

  // Split tokens by **bold**, *italic*, and `code`
  const regex = /(\*\*[^*]+?\*\*|\*[^*]+?\*|`[^`]+?`)/g;
  const parts = text.split(regex);

  return parts.map((part, idx) => {
    if (!part) return null;
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return <em key={idx}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return <code key={idx} className="md-inline-code">{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function parseMarkdownTable(lines) {
  if (lines.length < 2) return null;

  const parseRow = (line) => {
    let raw = line.trim();
    if (raw.startsWith('|')) raw = raw.slice(1);
    if (raw.endsWith('|')) raw = raw.slice(0, -1);
    return raw.split('|').map(c => c.trim());
  };

  const headerCells = parseRow(lines[0]);
  const alignTokens = parseRow(lines[1]);

  // Determine alignments (:---: is center, ---: is right, default left)
  const alignments = alignTokens.map(tok => {
    const trimmed = tok.replace(/\s+/g, '');
    if (trimmed.startsWith(':') && trimmed.endsWith(':')) return 'center';
    if (trimmed.endsWith(':')) return 'right';
    return 'left';
  });

  const bodyRows = lines.slice(2).map(parseRow);

  return (
    <div className="md-table-wrap">
      <table className="md-table">
        <thead>
          <tr>
            {headerCells.map((h, i) => (
              <th key={i} style={{ textAlign: alignments[i] || 'left' }}>
                {renderInline(h)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, rIdx) => (
            <tr key={rIdx}>
              {row.map((cell, cIdx) => (
                <td key={cIdx} style={{ textAlign: alignments[cIdx] || 'left' }}>
                  {renderInline(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function MarkdownRenderer({ content, className = '' }) {
  if (!content) return null;

  const rawLines = content.split(/\r?\n/);
  const elements = [];
  let i = 0;

  while (i < rawLines.length) {
    const line = rawLines[i];
    const trimmed = line.trim();

    // 1. Empty lines
    if (!trimmed) {
      i++;
      continue;
    }

    // 2. Horizontal divider: --- or ***
    if (/^(\*{3,}|-{3,}|_{3,})$/.test(trimmed)) {
      elements.push(<hr key={`hr-${i}`} className="md-hr" />);
      i++;
      continue;
    }

    // 3. Headers: #, ##, ###, ####
    const headerMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headerMatch) {
      const level = headerMatch[1].length;
      const text = headerMatch[2];
      const Tag = `h${level}`;
      elements.push(
        <Tag key={`h-${i}`} className={`md-header md-h${level}`}>
          {renderInline(text)}
        </Tag>
      );
      i++;
      continue;
    }

    // 4. Markdown Table detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const tableLines = [];
      let j = i;
      while (j < rawLines.length && rawLines[j].trim().startsWith('|') && rawLines[j].trim().endsWith('|')) {
        tableLines.push(rawLines[j]);
        j++;
      }
      if (tableLines.length >= 2 && tableLines[1].includes('-')) {
        const tableElem = parseMarkdownTable(tableLines);
        if (tableElem) {
          elements.push(<React.Fragment key={`tbl-${i}`}>{tableElem}</React.Fragment>);
          i = j;
          continue;
        }
      }
    }

    // 5. Unordered List Items: - , * , • 
    if (/^[-*•]\s+/.test(trimmed)) {
      const listItems = [];
      let j = i;
      while (j < rawLines.length && /^[-*•]\s+/.test(rawLines[j].trim())) {
        const itemText = rawLines[j].trim().replace(/^[-*•]\s+/, '');
        listItems.push(itemText);
        j++;
      }
      elements.push(
        <ul key={`ul-${i}`} className="md-list">
          {listItems.map((item, idx) => (
            <li key={idx} className="md-list-item">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      i = j;
      continue;
    }

    // 6. Ordered List Items: 1. 2. 3.
    const numMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (numMatch) {
      const listItems = [];
      let j = i;
      while (j < rawLines.length && /^\d+\.\s+/.test(rawLines[j].trim())) {
        const itemText = rawLines[j].trim().replace(/^\d+\.\s+/, '');
        listItems.push(itemText);
        j++;
      }
      elements.push(
        <ol key={`ol-${i}`} className="md-ol">
          {listItems.map((item, idx) => (
            <li key={idx} className="md-ol-item">
              {renderInline(item)}
            </li>
          ))}
        </ol>
      );
      i = j;
      continue;
    }

    // 7. Regular paragraph
    elements.push(
      <p key={`p-${i}`} className="md-paragraph">
        {renderInline(trimmed)}
      </p>
    );
    i++;
  }

  return (
    <div className={`md-content ${className}`}>
      {elements}
    </div>
  );
}
