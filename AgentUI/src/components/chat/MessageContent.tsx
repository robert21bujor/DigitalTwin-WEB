import React from 'react';

interface MessageContentProps {
  content: string;
  className?: string;
}

const MessageContent: React.FC<MessageContentProps> = ({ content, className = '' }) => {
  const parseMarkdownLinks = (text: string) => {
    // Regular expression to match markdown links: [text](url)
    const markdownLinkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    
    // Split the text by markdown links and create an array of text and link elements
    const parts: (string | JSX.Element)[] = [];
    let lastIndex = 0;
    let match;
    let keyCounter = 0;

    while ((match = markdownLinkRegex.exec(text)) !== null) {
      // Add text before the link
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }

      const linkText = match[1];
      const linkUrl = match[2];
      
      // Determine link style based on content
      let linkClass = "text-blue-600 hover:text-blue-800 underline";
      let buttonClass = "";
      
      // Style view and download links as buttons
      if (linkText.includes('View File') || linkText.includes('Download')) {
        if (linkText.includes('View File')) {
          buttonClass = "inline-flex items-center px-3 py-1 mr-2 mb-1 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 transition-colors";
        } else if (linkText.includes('Download')) {
          buttonClass = "inline-flex items-center px-3 py-1 mr-2 mb-1 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 focus:ring-4 focus:ring-green-300 transition-colors";
        }
        
        parts.push(
          <a
            key={`link-${keyCounter++}`}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClass}
          >
            {linkText.includes('View File') && (
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            )}
            {linkText.includes('Download') && (
              <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            )}
            {linkText.replace('**', '').replace('View File', 'View').replace('Download', 'Download')}
          </a>
        );
      } else {
        // Regular text links
        parts.push(
          <a
            key={`link-${keyCounter++}`}
            href={linkUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={linkClass}
          >
            {linkText}
          </a>
        );
      }

      lastIndex = markdownLinkRegex.lastIndex;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }

    return parts;
  };

  const formatContent = (text: string) => {
    // First handle markdown links
    const withLinks = parseMarkdownLinks(text);
    
    // Convert the result to JSX elements, handling line breaks
    return withLinks.map((part, index) => {
      if (typeof part === 'string') {
        // Handle line breaks in text parts
        const lines = part.split('\n');
        return lines.map((line, lineIndex) => (
          <React.Fragment key={`text-${index}-${lineIndex}`}>
            {line}
            {lineIndex < lines.length - 1 && <br />}
          </React.Fragment>
        ));
      } else {
        // Return JSX elements as-is
        return part;
      }
    }).flat();
  };

  return (
    <div className={`text-sm leading-relaxed ${className}`}>
      {formatContent(content)}
    </div>
  );
};

export default MessageContent; 