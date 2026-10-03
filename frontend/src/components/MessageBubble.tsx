import ReactMarkdown from 'react-markdown';
import { Message, StreamingMessage } from '../types';
import { SourceCard } from './SourceCard';

interface MessageBubbleProps {
  message: Message | StreamingMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className={`message-avatar ${isUser ? 'user' : 'assistant'}`} aria-hidden="true">
        {isUser ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="10" rx="2"></rect>
            <circle cx="12" cy="5" r="2"></circle>
            <path d="M12 7v4"></path>
            <line x1="8" y1="16" x2="8" y2="16"></line>
            <line x1="16" y1="16" x2="16" y2="16"></line>
          </svg>
        )}
      </div>

      <div className="message-content-wrap">
        <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
          {isUser ? (
            <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
          ) : (
            <>
              {message.content === '' && (message as StreamingMessage).state === 'streaming' ? (
                <div className="thinking-dots">
                  <div className="thinking-dot" />
                  <div className="thinking-dot" />
                  <div className="thinking-dot" />
                </div>
              ) : (
                <ReactMarkdown>{message.content}</ReactMarkdown>
              )}
            </>
          )}
        </div>

        {/* Insufficient Evidence specific UI */}
        {(message as StreamingMessage).state === 'insufficient_evidence' && (
          <div className="insufficient-evidence" style={{ marginTop: '16px' }}>
            <div className="insufficient-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
              Insufficient Evidence
            </div>
            <div className="insufficient-body">
              There is not enough information in the transcripts to answer this question accurately.
            </div>
            
            {((message as StreamingMessage).closest_episodes?.length ?? 0) > 0 && (
              <>
                <div className="insufficient-label">Closest Episodes</div>
                <ul className="insufficient-episodes">
                  {(message as StreamingMessage).closest_episodes?.map((ep, i) => (
                    <li key={i} className="insufficient-episode-item">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                        <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                      </svg>
                      {ep}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        {/* Source Citations */}
        {message.citations && message.citations.length > 0 && (
          <div className="source-cards">
            {message.citations.map((c, i) => (
              <SourceCard key={i} citation={c} />
            ))}
          </div>
        )}

        {/* Validation Badges */}
        {(message as StreamingMessage).validation && (
          <div className="message-meta">
            {message.latency_ms && (
              <div className="message-latency">{message.latency_ms}ms</div>
            )}
            
            {(message as StreamingMessage).validation?.passed ? (
              <div className="validation-badge pass">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                Ship30 Spec Passed
              </div>
            ) : (
              <div className="validation-badge fail" title={(message as StreamingMessage).validation?.failures.join('\n')}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="15" y1="9" x2="9" y2="15"></line>
                  <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
                Did not meet format
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
