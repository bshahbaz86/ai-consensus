import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
  // Process numbered citations to make them clickable hyperlinks
  let processedContent = content;

  if (webSearchSources.length > 0) {
    // Remove any existing markdown links from numbered citations
    processedContent = processedContent.replace(/\[(\d+(?:,\s*\d+)*)\]\(https?:\/\/[^)]+(?:\s*"[^"]*")?\)/g, '[$1]');

    // Convert numbered citations [1], [2], [3] into clickable links
    processedContent = processedContent.replace(/\[(\d+)\]/g, (match, num) => {
      const sourceIndex = parseInt(num) - 1;
      if (sourceIndex < webSearchSources.length) {
        const source = webSearchSources[sourceIndex];
        return `[${num}](${source.url})`;
      }
      return match; // Keep as-is if no matching source
    });
  }

  return (
    <div className={className}>
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: ({ node, children, ...props }) => (
              <a
                {...props}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 underline"
              >
                {children}
              </a>
            ),
            table: ({ node, ...props }) => (
              <div className="overflow-x-auto my-4">
                <table {...props} className="min-w-full divide-y divide-gray-300 border border-gray-300" />
              </div>
            ),
            thead: ({ node, ...props }) => (
              <thead {...props} className="bg-gray-50" />
            ),
            tbody: ({ node, ...props }) => (
              <tbody {...props} className="divide-y divide-gray-200 bg-white" />
            ),
            tr: ({ node, ...props }) => (
              <tr {...props} className="hover:bg-gray-50" />
            ),
            th: ({ node, ...props }) => (
              <th {...props} className="px-3 py-2 text-left text-xs font-semibold text-gray-900 border-r border-gray-300 last:border-r-0" />
            ),
            td: ({ node, ...props }) => (
              <td {...props} className="px-3 py-2 text-sm text-gray-700 border-r border-gray-200 last:border-r-0" />
            ),
          }}
        >
          {processedContent}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default MarkdownRenderer;