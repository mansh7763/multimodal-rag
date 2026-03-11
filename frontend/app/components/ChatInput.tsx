"use client";

import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
  courseFilter: string | null;
  onCourseFilterChange: (course: string | null) => void;
  courses: string[];
}

function formatCourseName(slug: string): string {
  return slug
    .replace(/-/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ChatInput({
  onSend,
  disabled,
  courseFilter,
  onCourseFilterChange,
  courses,
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 150) + "px";
    }
  }, [input]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <div
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--bg-secondary)",
        padding: "16px 24px",
      }}
    >
      {/* Course filter */}
      <div
        style={{
          display: "flex",
          gap: 6,
          marginBottom: 10,
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={() => onCourseFilterChange(null)}
          style={{
            padding: "4px 12px",
            borderRadius: 16,
            border: "1px solid",
            borderColor: !courseFilter ? "var(--accent)" : "var(--border)",
            background: !courseFilter ? "var(--accent-subtle)" : "transparent",
            color: !courseFilter ? "var(--accent)" : "var(--text-muted)",
            fontSize: 12,
            cursor: "pointer",
            transition: "all 0.15s ease",
          }}
        >
          All Courses
        </button>
        {courses.map((course) => (
          <button
            key={course}
            onClick={() =>
              onCourseFilterChange(courseFilter === course ? null : course)
            }
            style={{
              padding: "4px 12px",
              borderRadius: 16,
              border: "1px solid",
              borderColor:
                courseFilter === course ? "var(--accent)" : "var(--border)",
              background:
                courseFilter === course ? "var(--accent-subtle)" : "transparent",
              color:
                courseFilter === course ? "var(--accent)" : "var(--text-muted)",
              fontSize: 12,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            {formatCourseName(course)}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "flex-end",
        }}
      >
        <div
          style={{
            flex: 1,
            background: "var(--bg-tertiary)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: "10px 14px",
            transition: "border-color 0.15s ease",
          }}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="Ask about HuggingFace courses..."
            disabled={disabled}
            rows={1}
            style={{
              width: "100%",
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--text-primary)",
              fontSize: 14,
              lineHeight: 1.5,
              resize: "none",
              fontFamily: "inherit",
            }}
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={disabled || !input.trim()}
          style={{
            width: 42,
            height: 42,
            borderRadius: 10,
            border: "none",
            background:
              disabled || !input.trim()
                ? "var(--bg-tertiary)"
                : "var(--accent)",
            color:
              disabled || !input.trim() ? "var(--text-muted)" : "#000",
            cursor: disabled || !input.trim() ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all 0.15s ease",
            flexShrink: 0,
          }}
        >
          <Send size={16} />
        </button>
      </div>
      <div
        style={{
          fontSize: 11,
          color: "var(--text-muted)",
          marginTop: 8,
          textAlign: "center",
        }}
      >
        Press Enter to send &middot; Shift+Enter for new line
      </div>
    </div>
  );
}
