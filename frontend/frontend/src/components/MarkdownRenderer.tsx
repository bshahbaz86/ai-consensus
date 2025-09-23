import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface WebSearchSource {
  title: string;
  url: string;
  source?: string;
  published_date?: string;
  snippet?: string;
}

interface MarkdownRendererProps {
  content: string;
  className?: string;
  webSearchSources?: WebSearchSource[];
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '', webSearchSources = [] }) => {
  const [sourcesExpanded, setSourcesExpanded] = useState(false);

  // Split content into main content and sources
  const splitContent = (text: string) => {
    // Look for sources section (various patterns)
    const sourcesPatterns = [
      /(\*\*Sources?\*\*[\s\S]*$)/i,
      /(---[\s\S]*Sources?[\s\S]*$)/i,
      /(Sources?:[\s\S]*$)/i,
      /(References?:[\s\S]*$)/i
    ];

    // Check for formal sources section first
    for (const pattern of sourcesPatterns) {
      const match = text.match(pattern);
      if (match) {
        const mainContent = text.substring(0, match.index);
        const sourcesContent = match[1];
        return { mainContent, sourcesContent };
      }
    }

    // If no formal sources section, check for different types of inline citations

    // Pattern 1: [Source: ...] format
    const inlineSourcePattern = /\[Source:[^\]]+\]/g;
    const inlineSourceMatches = text.match(inlineSourcePattern);

    if (inlineSourceMatches && inlineSourceMatches.length > 0) {
      // Remove inline sources from main content
      const mainContent = text.replace(inlineSourcePattern, '').trim();

      // Create a sources section from inline citations with hyperlinks
      const sourcesContent = `**Sources**\n${inlineSourceMatches.map((source, index) => {
        const sourceText = source.replace(/\[Source:\s*/, '').replace(/\]$/, '');
        return `${index + 1}. ${sourceText}`;
      }).join('\n')}`;

      return { mainContent, sourcesContent };
    }

    // Pattern 2: Numbered citations like [1], [2], [3, 4] format
    const numberedCitationPattern = /\[\d+(?:,\s*\d+)*\]/g;
    const numberedCitations = text.match(numberedCitationPattern);

    if (numberedCitations && numberedCitations.length > 0 && webSearchSources.length > 0) {
      // Keep numbered citations as clickable links in main content
      let processedContent = text;

      // Replace numbered citations with clickable links
      processedContent = processedContent.replace(numberedCitationPattern, (match) => {
        const numbers = match.replace(/[\[\]]/g, '').split(',').map(n => parseInt(n.trim()));
        const links = numbers.map(num => {
          const sourceIndex = num - 1;
          if (sourceIndex < webSearchSources.length) {
            const source = webSearchSources[sourceIndex];
            return `[${num}](${source.url} "${source.title || 'Source'}")` ;
          }
          return `[${num}](#)`;
        });
        return `[${links.join(', ')}]`;
      });

      return { mainContent: processedContent, sourcesContent: null };
    }

    return { mainContent: text, sourcesContent: null };
  };

  const { mainContent, sourcesContent } = splitContent(content);

  // Process numbered citations and clean up URLs in main content
  let processedMainContent = mainContent;

  if (webSearchSources.length > 0) {
    // First, remove URL text that appears after citations like "[6](https://...)"
    processedMainContent = processedMainContent.replace(/\[(\d+(?:,\s*\d+)*)\]\(https?:\/\/[^\)]+\s*"[^"]*"\)/g, '[$1]');

    // Also remove standalone URL references that might appear
    processedMainContent = processedMainContent.replace(/\(https?:\/\/[^\s\)]+\s*"[^"]*"\)/g, '');

    // Then make the clean numbered citations clickable
    processedMainContent = processedMainContent.replace(/\[(\d+(?:,\s*\d+)*)\]/g, (match, numbers) => {
      const nums = numbers.split(',').map((n: string) => n.trim());
      const links = nums.map((num: string) => {
        const sourceIndex = parseInt(num) - 1;
        if (sourceIndex < webSearchSources.length) {
          const source = webSearchSources[sourceIndex];
          const tooltip = source.title || source.snippet?.substring(0, 80) || 'Click to view source';
          return `[${num}](${source.url} "${tooltip}")` ;
        }
        return num;
      });
      return `[${links.join(', ')}]`;
    });
  }

  // Convert numbered sources to links using actual web search sources
  const processSourcesContent = (sources: string) => {
    if (webSearchSources.length === 0) {
      // Fallback: try to find URLs in the source text or use Google search
      return sources.replace(/(\d+\.\s*)([^\n]+)/g, (match, number, text) => {
        const cleanText = text.trim();

        // Check if the text contains recognizable source patterns
        const urlPattern = /(https?:\/\/[^\s]+)/;
        const urlMatch = cleanText.match(urlPattern);

        if (urlMatch) {
          const url = urlMatch[1];
          const linkText = cleanText.replace(urlPattern, '').trim() || 'Source';
          return `${number}[${linkText}](${url})`;
        }

        // Check for common source patterns and create appropriate URLs
        if (cleanText.toLowerCase().includes('reddit')) {
          const searchQuery = cleanText.replace(/reddit[,\s]*/i, '');
          const redditUrl = `https://www.reddit.com/search/?q=${encodeURIComponent(searchQuery)}`;
          return `${number}[${cleanText}](${redditUrl})`;
        }

        if (cleanText.toLowerCase().includes('github')) {
          const searchQuery = cleanText.replace(/github[,\s]*/i, '');
          const githubUrl = `https://github.com/search?q=${encodeURIComponent(searchQuery)}`;
          return `${number}[${cleanText}](${githubUrl})`;
        }

        if (cleanText.toLowerCase().includes('stackoverflow')) {
          const searchQuery = cleanText.replace(/stackoverflow[,\s]*/i, '');
          const soUrl = `https://stackoverflow.com/search?q=${encodeURIComponent(searchQuery)}`;
          return `${number}[${cleanText}](${soUrl})`;
        }

        // Default to Google search
        const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(cleanText)}`;
        return `${number}[${cleanText}](${searchUrl})`;
      });
    }

    // Use actual web search sources
    return sources.replace(/(\d+\.\s*)([^\n]+)/g, (match, number, text) => {
      const sourceIndex = parseInt(number) - 1;
      if (sourceIndex < webSearchSources.length) {
        const source = webSearchSources[sourceIndex];
        const linkText = source.title || text.trim();
        const tooltip = source.snippet ? ` "${source.snippet.substring(0, 100)}..."` : '';
        return `${number}[${linkText}](${source.url}${tooltip})`;
      }

      // Fallback processing for sources that don't match web search indices
      const cleanText = text.trim();

      // Check for URLs in text
      const urlPattern = /(https?:\/\/[^\s]+)/;
      const urlMatch = cleanText.match(urlPattern);

      if (urlMatch) {
        const url = urlMatch[1];
        const linkText = cleanText.replace(urlPattern, '').trim() || 'Source';
        return `${number}[${linkText}](${url})`;
      }

      // Use intelligent search based on source content
      if (cleanText.toLowerCase().includes('reddit')) {
        const searchQuery = cleanText.replace(/reddit[,\s]*/i, '');
        const redditUrl = `https://www.reddit.com/search/?q=${encodeURIComponent(searchQuery)}`;
        return `${number}[${cleanText}](${redditUrl})`;
      }

      // Default fallback
      const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(cleanText)}`;
      return `${number}[${cleanText}](${searchUrl})`;
    });
  };

  return (
    <div className={className}>
      {/* Main content */}
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown
          components={{
            a: ({ node, ...props }) => {
              // Check if this is a numbered citation link
              const isNumberedCitation = /^\d+$/.test(props.children?.toString() || '');

              return (
                <a
                  {...props}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`text-blue-600 hover:text-blue-800 underline transition-all duration-200 cursor-pointer ${
                    isNumberedCitation
                      ? 'hover:bg-blue-50 px-1 py-0.5 rounded font-medium'
                      : 'hover:bg-blue-50 px-1 py-0.5 rounded'
                  }`}
                  title={props.title || 'Click to view source'}
                />
              );
            },
          }}
        >
          {processedMainContent}
        </ReactMarkdown>
      </div>

      {/* Sources section */}
      {sourcesContent && (
        <div className="mt-4 border-t border-gray-200 pt-4">
          <button
            onClick={() => setSourcesExpanded(!sourcesExpanded)}
            className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
          >
            {sourcesExpanded ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )}
            Sources ({webSearchSources.length > 0 ? webSearchSources.length : (sourcesContent.match(/^\d+\.\s/gm) || []).length})
          </button>

          {sourcesExpanded && (
            <div className="mt-3 prose prose-sm max-w-none text-gray-600">
              <ReactMarkdown
                components={{
                  a: ({ node, ...props }) => (
                    <a
                      {...props}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 underline hover:bg-blue-50 px-1 py-0.5 rounded transition-all duration-200 cursor-pointer"
                      title={props.title || 'Click to view source'}
                    />
                  ),
                }}
              >
                {processSourcesContent(sourcesContent)}
              </ReactMarkdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MarkdownRenderer;