"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import TopBar from "./components/TopBar";

const API_BASE = "http://localhost:8000";
// const API_BASE = "https://ai-driven-ticket-management-and-helpdesk.onrender.com";

/** Formats the AI markdown-lite response: bold **text**, inline `code`. */
function formatMessage(text) {
  if (!text) return text;
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

/** Renders a single chat message bubble */
function Message({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`message ${isUser ? "user" : "ai"}`}>
      <div className="message-avatar" aria-hidden="true">
        {isUser ? "YOU" : "AI"}
      </div>
      <div className="message-body">
        {/* Image attachment preview (user side) */}
        {msg.imageUrl && (
          <img
            src={msg.imageUrl}
            alt="Attached screenshot"
            style={{
              maxWidth: 200,
              maxHeight: 130,
              border: "1px solid var(--border-mid)",
              display: "block",
              marginBottom: 4,
            }}
          />
        )}

        {/* Main bubble */}
        <div
          className={`message-bubble ${msg.resolved === true
            ? "resolved"
            : msg.resolved === false
              ? "escalated"
              : ""
            }`}
          dangerouslySetInnerHTML={{ __html: formatMessage(msg.content) }}
        />

        {/* Ticket chip for escalated tickets */}
        {msg.ticketId && (
          <div className="ticket-chip" role="status" aria-label="Ticket created">
            <span>🎫</span>
            <span>#{msg.ticketId}</span>
            {msg.priority && (
              <span className={`ticket-chip-priority ${msg.priority}`}>
                {msg.priority}
              </span>
            )}
            {msg.assignedTo && (
              <span>→ {msg.assignedTo}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Animated typing indicator while waiting for AI response */
function TypingIndicator() {
  return (
    <div className="message ai" role="status" aria-label="AI is thinking">
      <div className="message-avatar" aria-hidden="true">AI</div>
      <div className="message-body">
        <div className="typing-indicator">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      </div>
    </div>
  );
}

/** Hint prompts shown in the empty state */
const HINT_PROMPTS = [
  "I have an authentication error with my JWT token",
  "The deploy pipeline is broken and not running",
  "Database migration failed on staging",
  "CORS errors in the mobile API calls",
];

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Auto-grow textarea
  const handleTextareaInput = useCallback((e) => {
    setInputText(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + "px";
  }, []);

  const handleImageSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreviewUrl(URL.createObjectURL(file));
  }, []);

  const removeImage = useCallback(() => {
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    setImageFile(null);
    setImagePreviewUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [imagePreviewUrl]);

  const sendMessage = useCallback(
    async (text) => {
      const messageText = (text ?? inputText).trim();
      if (!messageText || isLoading) return;

      setError(null);

      // Snapshot image data before clearing state
      const currentImageFile = imageFile;
      const currentImageUrl = imagePreviewUrl;

      // Optimistically add user message
      const userMsg = {
        id: Date.now(),
        role: "user",
        content: messageText,
        imageUrl: currentImageUrl,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInputText("");
      setImageFile(null);
      setImagePreviewUrl(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }

      setIsLoading(true);

      try {
        const formData = new FormData();
        formData.append("message", messageText);
        if (currentImageFile) {
          formData.append("image", currentImageFile);
        }

        const res = await fetch(`${API_BASE}/api/chat`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail ?? `Server error ${res.status}`);
        }

        const data = await res.json();

        const aiMsg = {
          id: Date.now() + 1,
          role: "ai",
          content: data.ai_response,
          resolved: data.resolved,
          ticketId: data.ticket_id ? data.ticket_id.slice(0, 8) : null,
          priority: data.priority,
          assignedTo: data.assigned_to,
        };
        setMessages((prev) => [...prev, aiMsg]);
      } catch (err) {
        setError(err.message ?? "Failed to reach the API. Is the backend running?");
        // Remove the optimistic user message on failure
        setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      } finally {
        setIsLoading(false);
      }
    },
    [inputText, imageFile, imagePreviewUrl, isLoading]
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage]
  );

  const canSend = inputText.trim().length > 0 && !isLoading;

  return (
    <div className="page-shell">
      <TopBar />

      <div className="chat-container">
        {/* ── Messages area ── */}
        <div
          className="chat-messages"
          role="log"
          aria-live="polite"
          aria-label="Chat messages"
        >
          {messages.length === 0 && !isLoading && (
            <div className="chat-empty" aria-label="Empty state">
              <div className="chat-empty-icon" aria-hidden="true">⟩_</div>
              <p className="chat-empty-title">Describe your issue below</p>
              <div className="chat-empty-hints" role="list">
                {HINT_PROMPTS.map((hint) => (
                  <button
                    key={hint}
                    className="chat-empty-hint"
                    onClick={() => sendMessage(hint)}
                    role="listitem"
                    aria-label={`Try: ${hint}`}
                  >
                    {hint}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <Message key={msg.id} msg={msg} />
          ))}

          {isLoading && <TypingIndicator />}

          {error && (
            <div
              role="alert"
              style={{
                padding: "10px 14px",
                border: "1px solid var(--status-red)",
                color: "var(--status-red)",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                background: "rgba(255,68,68,0.06)",
              }}
            >
              ⚠ {error}
            </div>
          )}

          <div ref={messagesEndRef} aria-hidden="true" />
        </div>

        {/* ── Input dock ── */}
        <div className="chat-input-dock">
          {/* Image preview */}
          {imagePreviewUrl && (
            <div className="chat-input-preview-row">
              <div className="image-preview">
                <img src={imagePreviewUrl} alt="Attachment preview" />
                <button
                  className="image-preview-remove"
                  onClick={removeImage}
                  aria-label="Remove attached image"
                >
                  ✕
                </button>
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--text-dim)",
                }}
              >
                {imageFile?.name}
              </span>
            </div>
          )}

          <div className="chat-input-row">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={handleImageSelect}
              aria-label="Attach image"
              id="image-upload"
            />

            {/* Attach button */}
            <button
              className="chat-attach-btn"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Attach a screenshot"
              title="Attach image"
              disabled={isLoading}
            >
              📎
            </button>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder="Describe your issue… (Shift+Enter for newline)"
              value={inputText}
              onInput={handleTextareaInput}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isLoading}
              aria-label="Message input"
              aria-multiline="true"
              id="chat-message-input"
            />

            {/* Send button */}
            <button
              className="chat-send-btn"
              onClick={() => sendMessage()}
              disabled={!canSend}
              aria-label="Send message"
              title="Send (Enter)"
            >
              ↑
            </button>
          </div>

          <p className="chat-hint">
            Enter to send · Shift+Enter for newline · Attach a screenshot for
            richer context
          </p>
        </div>
      </div>
    </div>
  );
}
