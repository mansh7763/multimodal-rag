"use client";

import { MessageSquare, Plus, Trash2, GraduationCap } from "lucide-react";

interface Session {
  id: string;
  title: string;
}

interface SidebarProps {
  sessions: Session[];
  activeSession: string;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onDeleteSession: (id: string) => void;
}

export default function Sidebar({
  sessions,
  activeSession,
  onSelectSession,
  onNewSession,
  onDeleteSession,
}: SidebarProps) {
  return (
    <div
      style={{
        width: 260,
        background: "var(--bg-secondary)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: "20px 16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: "linear-gradient(135deg, #f59e0b, #d97706)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <GraduationCap size={20} color="#000" />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)" }}>
              HF Course RAG
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              Multimodal Search
            </div>
          </div>
        </div>
      </div>

      {/* New chat button */}
      <div style={{ padding: "12px 12px 4px" }}>
        <button
          onClick={onNewSession}
          style={{
            width: "100%",
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px dashed var(--border-light)",
            background: "transparent",
            color: "var(--text-secondary)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontSize: 13,
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--accent)";
            e.currentTarget.style.color = "var(--accent)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--border-light)";
            e.currentTarget.style.color = "var(--text-secondary)";
          }}
        >
          <Plus size={14} />
          New Chat
        </button>
      </div>

      {/* Session list */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px 12px",
        }}
      >
        {sessions.map((session) => (
          <div
            key={session.id}
            onClick={() => onSelectSession(session.id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 12px",
              borderRadius: 8,
              cursor: "pointer",
              marginBottom: 2,
              background:
                activeSession === session.id
                  ? "var(--bg-hover)"
                  : "transparent",
              border:
                activeSession === session.id
                  ? "1px solid var(--border)"
                  : "1px solid transparent",
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              if (activeSession !== session.id) {
                e.currentTarget.style.background = "var(--bg-tertiary)";
              }
            }}
            onMouseLeave={(e) => {
              if (activeSession !== session.id) {
                e.currentTarget.style.background = "transparent";
              }
            }}
          >
            <MessageSquare
              size={14}
              color={
                activeSession === session.id
                  ? "var(--accent)"
                  : "var(--text-muted)"
              }
              style={{ flexShrink: 0 }}
            />
            <span
              style={{
                flex: 1,
                fontSize: 13,
                color:
                  activeSession === session.id
                    ? "var(--text-primary)"
                    : "var(--text-secondary)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {session.title}
            </span>
            {sessions.length > 1 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(session.id);
                }}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: 2,
                  opacity: 0.5,
                  color: "var(--text-muted)",
                  display: "flex",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.opacity = "1")}
                onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.5")}
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: "1px solid var(--border)",
          fontSize: 11,
          color: "var(--text-muted)",
          textAlign: "center",
        }}
      >
        Powered by Gemini + Qdrant
      </div>
    </div>
  );
}
