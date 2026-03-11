"use client";

import { BookOpen, ExternalLink, Bot, User } from "lucide-react";

interface Source {
  content: string;
  course: string;
  chapter: string;
  section: string;
  url: string;
  score: number;
  content_type: string;
  image_srcs: string[];
}

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  rewrittenQuery?: string;
}

function formatCourseName(slug: string): string {
  return slug
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function renderMarkdown(text: string): string {
  // Basic markdown rendering
  let html = text
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.06);padding:2px 6px;border-radius:4px;">$1</code>')
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    // Italic
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    // Headers
    .replace(/^### (.+)$/gm, '<h3 style="font-size:1em;font-weight:600;margin:1em 0 0.5em;">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 style="font-size:1.1em;font-weight:600;margin:1em 0 0.5em;">$1</h2>')
    // Lists
    .replace(/^\d+\.\s+(.+)$/gm, "<li>$1</li>")
    .replace(/^[-*]\s+(.+)$/gm, "<li>$1</li>")
    // Paragraphs
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br/>");

  return `<p>${html}</p>`;
}

export default function ChatMessage({
  role,
  content,
  sources,
  rewrittenQuery,
}: ChatMessageProps) {
  return (
    <div className="animate-fade-in" style={{ marginBottom: "24px" }}>
      <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
        {/* Avatar */}
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            background:
              role === "assistant"
                ? "linear-gradient(135deg, #f59e0b, #d97706)"
                : "var(--bg-tertiary)",
            border: role === "user" ? "1px solid var(--border)" : "none",
          }}
        >
          {role === "assistant" ? (
            <Bot size={16} color="#000" />
          ) : (
            <User size={16} color="var(--text-secondary)" />
          )}
        </div>

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "var(--text-muted)",
              marginBottom: 6,
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {role === "assistant" ? "Assistant" : "You"}
          </div>

          {rewrittenQuery && (
            <div
              style={{
                fontSize: 12,
                color: "var(--text-muted)",
                marginBottom: 8,
                padding: "6px 10px",
                background: "var(--accent-subtle)",
                borderRadius: 6,
                border: "1px solid rgba(245, 158, 11, 0.2)",
              }}
            >
              Interpreted as: <em>{rewrittenQuery}</em>
            </div>
          )}

          <div
            className="markdown-content"
            style={{
              lineHeight: 1.7,
              color: "var(--text-primary)",
              fontSize: 14,
            }}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />

          {/* Sources */}
          {sources && sources.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: "var(--text-muted)",
                  marginBottom: 8,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <BookOpen size={12} />
                SOURCES
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {sources.map((source, idx) => (
                  <a
                    key={idx}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "8px 12px",
                      background: "var(--bg-tertiary)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      textDecoration: "none",
                      transition: "all 0.15s ease",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = "var(--border-light)";
                      e.currentTarget.style.background = "var(--bg-hover)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = "var(--border)";
                      e.currentTarget.style.background = "var(--bg-tertiary)";
                    }}
                  >
                    <div
                      style={{
                        width: 20,
                        height: 20,
                        borderRadius: "50%",
                        background: "var(--accent-subtle)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        fontSize: 11,
                        fontWeight: 600,
                        color: "var(--accent)",
                      }}
                    >
                      {idx + 1}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 500,
                          color: "var(--text-primary)",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {source.section || source.chapter}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                        {formatCourseName(source.course)} &middot;{" "}
                        {source.chapter}
                        {source.content_type === "code" && (
                          <span
                            style={{
                              marginLeft: 6,
                              padding: "1px 5px",
                              background: "rgba(59, 130, 246, 0.1)",
                              color: "#60a5fa",
                              borderRadius: 3,
                              fontSize: 10,
                            }}
                          >
                            code
                          </span>
                        )}
                      </div>
                    </div>
                    <ExternalLink
                      size={12}
                      color="var(--text-muted)"
                      style={{ flexShrink: 0 }}
                    />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
