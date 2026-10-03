import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Session, StreamingMessage, Citation } from '../types';
import { streamMessage } from '../api';
import { MessageBubble } from './MessageBubble';

interface ChatPaneProps {
  session: Session | null;
  onNewMessage: (sessionId: string) => void;
  onArtifactCreated?: (artifactId: string) => void;
  onNewChat: () => void;
}

const SUGGESTIONS = [
  { text: "What did Molly Graham say about giving away your Legos?", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
  )},
  { text: "Write a Ship 30 essay about building high talent density.", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 19-7-7 7-7 7 7-7 7z"/><path d="m19 12-7 7-7-7"/></svg>
  )},
  { text: "How do leaders think about product and growth loops?", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
  )},
  { text: "What is Tara Seshan's framework for AI coworkers?", icon: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"/><path d="M12 8v-1a4 4 0 1 0-4 4h1"/></svg>
  )}
];

export function ChatPane({ session, onNewMessage, onArtifactCreated, onNewChat }: ChatPaneProps) {
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMsg, setStreamingMsg] = useState<StreamingMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<(() => void) | null>(null);
  const liveRegionRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session?.messages?.length, streamingMsg?.content]);

  const autoResize = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
  };

  const handleSend = (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || !session || isStreaming) return;

    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setError(null);
    setIsStreaming(true);
    setStreamingMsg({ role: 'assistant', content: '', state: 'streaming' });

    cancelRef.current = streamMessage(
      session.id,
      content,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (event: any) => {
        setStreamingMsg((prev) => {
          if (!prev) return prev;
          switch (event.type) {
            case 'token':
              const newContent = prev.content + (event.content ?? '');
              if (liveRegionRef.current) liveRegionRef.current.textContent = newContent;
              return { ...prev, content: newContent };
            case 'citations':
              return { ...prev, citations: event.citations };
            case 'insufficient_evidence':
              return { ...prev, state: 'insufficient_evidence' as const, content: event.message ?? '', closest_episodes: event.closest_episodes };
            case 'validation':
              return { ...prev, validation_result: { passed: !!event.passed, word_count: event.word_count ?? 0, failures: event.failures ?? [] } };
            case 'artifact':
              if (event.artifact_id && onArtifactCreated) onArtifactCreated(event.artifact_id as string);
              return prev;
            case 'done':
              return { ...prev, latency_ms: event.latency_ms };
            case 'error':
              setError((event.message as string) ?? 'Generation failed');
              return { ...prev, state: 'error' as const };
            default:
              return prev;
          }
        });
      },
      () => { setIsStreaming(false); setStreamingMsg(null); onNewMessage(session.id); },
      (err) => { setError(err); setIsStreaming(false); setStreamingMsg(null); }
    );
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleCancel = () => { cancelRef.current?.(); setIsStreaming(false); setStreamingMsg(null); };

  const messages = session?.messages ?? [];
  const showEmpty = !session || (messages.length === 0 && !streamingMsg);

  return (
    <main className="chat-pane" aria-label="Chat">
      {/* ARIA live region (off-screen) */}
      <div ref={liveRegionRef} aria-live="polite" aria-atomic="false"
        style={{ position: 'absolute', left: '-9999px', width: 1, height: 1, overflow: 'hidden' }} />

      <div className="chat-messages" role="list" aria-label="Messages">
        {showEmpty ? (
          <div className="chat-empty">
            <div className="chat-empty-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 4C6 3.44772 6.44772 3 7 3H10C10.5523 3 11 3.44772 11 4V16H18C18.5523 16 19 16.4477 19 17V19C19 19.5523 18.5523 20 18 20H7C6.44772 20 6 19.5523 6 19V4Z" fill="currentColor"/>
              </svg>
            </div>
            <h2>Lenny Growth Assistant</h2>
            <p className="chat-empty-sub">
              Ask questions grounded in real podcast transcripts — with inline citations, Ship 30 essays, and exportable artifacts.
            </p>
            {session && (
              <div className="chat-suggestions" role="list">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s.text}
                    className="chat-suggestion"
                    onClick={() => handleSend(s.text)}
                    role="listitem"
                    aria-label={`Ask: ${s.text}`}
                  >
                    <span className="chat-suggestion-icon" aria-hidden="true">{s.icon}</span>
                    <span className="chat-suggestion-text">{s.text}</span>
                  </button>
                ))}
              </div>
            )}
            {!session && (
              <button className="btn-new-chat" onClick={onNewChat} style={{ marginTop: 24, maxWidth: 200 }}>
                Start a new chat
              </button>
            )}
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {streamingMsg && (
              <MessageBubble message={streamingMsg} />
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {session && (
        <div className="chat-input-container">
          {error && (
            <div className="error-banner" role="alert">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>{error}</span>
              <button className="banner-dismiss" onClick={() => setError(null)}>Dismiss</button>
            </div>
          )}
          <div className="chat-input-wrapper">
            <div className="chat-input-box">
              <textarea
                ref={textareaRef}
                className="chat-input"
                value={input}
                onChange={(e) => { setInput(e.target.value); autoResize(); }}
                onKeyDown={handleKeyDown}
                placeholder="Ask about podcast transcripts…"
                disabled={isStreaming}
                rows={1}
                aria-label="Message input"
                aria-multiline="true"
              />
              {isStreaming ? (
                <button className="btn-stop" onClick={handleCancel} aria-label="Stop generation">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="6" y="6" width="12" height="12" rx="2" ry="2"/>
                  </svg>
                  Stop
                </button>
              ) : (
                <button
                  className="btn-send"
                  onClick={() => handleSend()}
                  disabled={!input.trim()}
                  aria-label="Send message"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="19" x2="12" y2="5"/>
                    <polyline points="5 12 12 5 19 12"/>
                  </svg>
                </button>
              )}
            </div>
            <div className="chat-input-hint">
              <span className="hint-kbd">Enter</span> to send
              <span className="hint-kbd" style={{marginLeft: 8}}>Shift</span> + <span className="hint-kbd">Enter</span> for newline
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
