import { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
}

export function Sidebar({ sessions, activeSessionId, onSelect, onNewChat }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <button className="btn-new-chat" onClick={onNewChat} aria-label="Start new chat">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          <span>New Chat</span>
        </button>
      </div>

      <div className="sidebar-section-label" id="sessions-heading">Chat History</div>

      <nav className="sidebar-sessions" aria-labelledby="sessions-heading">
        {sessions.length === 0 ? (
          <div className="sidebar-empty">
            No previous chats
          </div>
        ) : (
          sessions.map((session) => (
            <button
              key={session.id}
              className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
              onClick={() => onSelect(session.id)}
              aria-current={session.id === activeSessionId ? 'page' : undefined}
            >
              <div className="session-item-icon" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
              <div className="session-title">
                {session.title || 'Untitled Session'}
              </div>
            </button>
          ))
        )}
      </nav>
    </aside>
  );
}
