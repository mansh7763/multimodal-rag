"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import ChatMessage from "./components/ChatMessage";
import ChatInput from "./components/ChatInput";
import Sidebar from "./components/Sidebar";
import { Loader2, Sparkles } from "lucide-react";

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

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  rewrittenQuery?: string;
}

interface Session {
  id: string;
  title: string;
  messages: Message[];
}

const API_BASE =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

const EXAMPLE_QUERIES = [
  "How does LoRA fine-tuning work?",
  "Explain how diffusion models generate images",
  "What are AI agents and how do they use tools?",
  "How does audio preprocessing work for transformers?",
];

export default function Home() {
  const [sessions, setSessions] = useState<Session[]>([
    { id: "default", title: "New Chat", messages: [] },
  ]);
  const [activeSessionId, setActiveSessionId] = useState("default");
  const [loading, setLoading] = useState(false);
  const [courses, setCourses] = useState<string[]>([]);
  const [courseFilter, setCourseFilter] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId)!;

  useEffect(() => {
    fetch(`${API_BASE}/courses`)
      .then((r) => r.json())
      .then((data) => setCourses(data.courses || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeSession.messages, loading]);

  const updateSession = useCallback(
    (id: string, update: Partial<Session>) => {
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, ...update } : s))
      );
    },
    []
  );

  const handleSend = async (message: string) => {
    const sessionId = activeSessionId;

    // Add user message
    const userMsg: Message = { role: "user", content: message };
    const updatedMessages = [...activeSession.messages, userMsg];
    updateSession(sessionId, {
      messages: updatedMessages,
      title:
        activeSession.messages.length === 0
          ? message.slice(0, 40) + (message.length > 40 ? "..." : "")
          : activeSession.title,
    });

    setLoading(true);

    try {
      // Call backend directly (not via Next.js proxy) to enable real streaming
      const response = await fetch(`${API_BASE}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: message,
          session_id: sessionId,
          course_filter: courseFilter,
          include_images: true,
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => null);
        throw new Error(err?.detail || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let sources: Source[] = [];
      let rewrittenQuery: string | undefined;
      let answerTokens: string[] = [];
      let buffer = "";
      let currentEventType = "token";
      let currentDataLines: string[] = [];

      const dispatchEvent = (eventType: string, data: string) => {
        if (eventType === "sources") {
          try {
            sources = JSON.parse(data);
          } catch {}
        } else if (eventType === "rewrite") {
          rewrittenQuery = data;
        } else if (eventType === "token") {
          answerTokens.push(data);
          const assistantMsg: Message = {
            role: "assistant",
            content: answerTokens.join(""),
            sources,
            rewrittenQuery,
          };
          setSessions((prev) =>
            prev.map((s) =>
              s.id === sessionId
                ? { ...s, messages: [...updatedMessages, assistantMsg] }
                : s
            )
          );
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        // Normalize \r\n to \n
        buffer = buffer.replace(/\r\n/g, "\n");

        // Process line by line per SSE spec
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // last segment may be incomplete

        for (const line of lines) {
          if (line === "") {
            // Blank line = end of event
            if (currentDataLines.length > 0) {
              dispatchEvent(currentEventType, currentDataLines.join("\n"));
            }
            currentEventType = "token";
            currentDataLines = [];
          } else if (line.startsWith("event: ")) {
            currentEventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            currentDataLines.push(line.slice(6));
          } else if (line === "data:" || line === "data") {
            currentDataLines.push("");
          }
        }
      }

      // Dispatch any remaining buffered event
      if (currentDataLines.length > 0) {
        dispatchEvent(currentEventType, currentDataLines.join("\n"));
      }

      // Final message
      const finalMsg: Message = {
        role: "assistant",
        content: answerTokens.join("") || "No response generated.",
        sources,
        rewrittenQuery,
      };
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, messages: [...updatedMessages, finalMsg] }
            : s
        )
      );
    } catch (error: unknown) {
      console.error("Query error:", error);
      const errMsg =
        error instanceof Error ? error.message : "Something went wrong";
      const errorResponse: Message = {
        role: "assistant",
        content: `Sorry, I encountered an error: ${errMsg}. Please try again.`,
      };
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, messages: [...updatedMessages, errorResponse] }
            : s
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleNewSession = () => {
    const id = `session-${Date.now()}`;
    setSessions((prev) => [...prev, { id, title: "New Chat", messages: [] }]);
    setActiveSessionId(id);
  };

  const handleDeleteSession = (id: string) => {
    setSessions((prev) => prev.filter((s) => s.id !== id));
    if (activeSessionId === id) {
      const remaining = sessions.filter((s) => s.id !== id);
      setActiveSessionId(remaining[0]?.id || "default");
    }
    // Clear backend session
    fetch(`${API_BASE}/session/${id}/clear`, { method: "POST" }).catch(
      () => {}
    );
  };

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <Sidebar
        sessions={sessions}
        activeSession={activeSessionId}
        onSelectSession={setActiveSessionId}
        onNewSession={handleNewSession}
        onDeleteSession={handleDeleteSession}
      />

      {/* Main chat area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          height: "100vh",
        }}
      >
        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "24px 24px 0",
          }}
        >
          <div style={{ maxWidth: 780, margin: "0 auto" }}>
            {activeSession.messages.length === 0 ? (
              /* Welcome screen */
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  minHeight: "60vh",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    width: 64,
                    height: 64,
                    borderRadius: 16,
                    background: "linear-gradient(135deg, #f59e0b, #d97706)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: 20,
                  }}
                >
                  <Sparkles size={28} color="#000" />
                </div>
                <h1
                  style={{
                    fontSize: 24,
                    fontWeight: 700,
                    marginBottom: 8,
                    color: "var(--text-primary)",
                  }}
                >
                  HuggingFace Course Assistant
                </h1>
                <p
                  style={{
                    fontSize: 14,
                    color: "var(--text-muted)",
                    marginBottom: 32,
                    maxWidth: 460,
                    lineHeight: 1.6,
                  }}
                >
                  Ask questions about HuggingFace courses — AI agents, NLP,
                  computer vision, audio, reinforcement learning, and more.
                </p>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 10,
                    width: "100%",
                    maxWidth: 520,
                  }}
                >
                  {EXAMPLE_QUERIES.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(q)}
                      disabled={loading}
                      style={{
                        padding: "14px 16px",
                        borderRadius: 10,
                        border: "1px solid var(--border)",
                        background: "var(--bg-secondary)",
                        color: "var(--text-secondary)",
                        fontSize: 13,
                        textAlign: "left",
                        cursor: "pointer",
                        transition: "all 0.15s ease",
                        lineHeight: 1.4,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor =
                          "var(--border-light)";
                        e.currentTarget.style.background = "var(--bg-tertiary)";
                        e.currentTarget.style.color = "var(--text-primary)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = "var(--border)";
                        e.currentTarget.style.background =
                          "var(--bg-secondary)";
                        e.currentTarget.style.color = "var(--text-secondary)";
                      }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              /* Message list */
              activeSession.messages.map((msg, i) => (
                <ChatMessage
                  key={i}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                  rewrittenQuery={msg.rewrittenQuery}
                />
              ))
            )}

            {/* Loading indicator */}
            {loading &&
              activeSession.messages[activeSession.messages.length - 1]
                ?.role === "user" && (
                <div
                  className="animate-fade-in"
                  style={{
                    display: "flex",
                    gap: 12,
                    alignItems: "flex-start",
                    marginBottom: 24,
                  }}
                >
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: "50%",
                      background:
                        "linear-gradient(135deg, #f59e0b, #d97706)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <Loader2
                      size={16}
                      color="#000"
                      className="animate-spin"
                      style={{
                        animation: "spin 1s linear infinite",
                      }}
                    />
                  </div>
                  <div style={{ paddingTop: 6 }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      <span
                        className="typing-dot"
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          background: "var(--text-muted)",
                        }}
                      />
                      <span
                        className="typing-dot"
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          background: "var(--text-muted)",
                        }}
                      />
                      <span
                        className="typing-dot"
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          background: "var(--text-muted)",
                        }}
                      />
                    </div>
                  </div>
                </div>
              )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div style={{ maxWidth: 780, margin: "0 auto", width: "100%" }}>
          <ChatInput
            onSend={handleSend}
            disabled={loading}
            courseFilter={courseFilter}
            onCourseFilterChange={setCourseFilter}
            courses={courses}
          />
        </div>
      </div>

      <style jsx global>{`
        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}
