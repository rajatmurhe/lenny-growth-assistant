import { Citation } from '../types';

interface SourceCardProps {
  citation: Citation;
}

export function SourceCard({ citation }: SourceCardProps) {
  // Strip the generic System instructions or frontmatter if present
  const cleanSnippet = citation.text_snippet
    .replace(/^.*?<UNTRUSTED_CONTEXT>/s, '')
    .replace(/<\/UNTRUSTED_CONTEXT>.*?$/s, '')
    .trim();

  return (
    <article className="source-card">
      <div className="source-card-number">Source [{citation.ordinal}]</div>
      <div className="source-card-title">{citation.episode_title}</div>
      
      {citation.guest && (
        <div className="source-card-guest">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span>{citation.guest}</span>
        </div>
      )}
      
      <div className="source-card-snippet">"{cleanSnippet}"</div>
      
      <div className="source-card-footer">
        <span className="source-card-score">
          {Math.round(citation.rrf_score * 100)}% Match
        </span>
        {citation.post_url && (
          <a href={citation.post_url} target="_blank" rel="noopener noreferrer">
            Read Post
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="7" y1="17" x2="17" y2="7"></line>
              <polyline points="7 7 17 7 17 17"></polyline>
            </svg>
          </a>
        )}
      </div>
    </article>
  );
}
