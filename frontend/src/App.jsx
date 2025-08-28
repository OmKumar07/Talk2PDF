import { useState, useRef, useEffect } from "react";
import { uploadPDF, askQuestion } from "./api";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [docId, setDocId] = useState(null);
  const [messages, setMessages] = useState([
    {
      type: "system",
      content:
        "👋 Welcome to Talk2PDF! Upload a PDF document to start asking questions about its content.",
      timestamp: new Date(),
    },
    {
      type: "system",
      content:
        "✨ Features: AI-powered answers, source citations, confidence scores, and more!",
      timestamp: new Date(),
    },
  ]);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Sample questions for user inspiration
  const sampleQuestions = [
    "What is the main topic of this document?",
    "Can you summarize the key points?",
    "What are the conclusions mentioned?",
    "Who are the authors or main contributors?",
  ];

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Handle file selection
  const handleFileSelect = (selectedFile) => {
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setError("");
    } else {
      setError("Please select a valid PDF file.");
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    handleFileSelect(droppedFile);
  };

  // Upload PDF
  const handleUpload = async () => {
    if (!file) {
      setError("Please select a PDF file to upload.");
      return;
    }

    try {
      setError("");
      setUploading(true);
      const resp = await uploadPDF(file);
      if (resp && resp.doc_id) {
        setDocId(resp.doc_id);
        setMessages([
          {
            type: "system",
            content: `✅ Successfully uploaded "${file.name}". You can now ask questions about the document!`,
            timestamp: new Date(),
          },
          {
            type: "system",
            content:
              "💡 Try asking: " +
              sampleQuestions[
                Math.floor(Math.random() * sampleQuestions.length)
              ],
            timestamp: new Date(),
          },
        ]);
      } else {
        setError("Upload failed: no document ID returned.");
      }
    } catch (err) {
      console.error("Upload failed:", err);
      setError("Upload failed. Please check if the server is running.");
    } finally {
      setUploading(false);
    }
  };

  // Ask a question
  const handleAsk = async (e) => {
    e.preventDefault();

    if (!docId) {
      setError("No document uploaded yet.");
      return;
    }
    if (!currentQuestion.trim()) {
      setError("Please enter a question.");
      return;
    }

    const question = currentQuestion.trim();
    setCurrentQuestion("");
    setError("");

    // Add user message
    const userMessage = {
      type: "user",
      content: question,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      setLoading(true);
      const resp = await askQuestion(docId, question);

      // Add assistant response
      const assistantMessage = {
        type: "assistant",
        content:
          resp.answer || "Sorry, I couldn't find an answer to your question.",
        sources: resp.sources || [],
        confidence: resp.score,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Ask failed:", err);
      const errorMessage = {
        type: "assistant",
        content:
          "Sorry, I encountered an error while processing your question. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // Handle textarea auto-resize
  const handleTextareaChange = (e) => {
    setCurrentQuestion(e.target.value);
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
    }
  };

  // Reset to upload new document
  const handleReset = () => {
    setFile(null);
    setDocId(null);
    setMessages([
      {
        type: "system",
        content:
          "👋 Welcome to Talk2PDF! Upload a PDF document to start asking questions about its content.",
        timestamp: new Date(),
      },
      {
        type: "system",
        content:
          "✨ Features: AI-powered answers, source citations, confidence scores, and more!",
        timestamp: new Date(),
      },
    ]);
    setCurrentQuestion("");
    setError("");
  };

  // Show demo conversation
  const showDemo = () => {
    setMessages([
      {
        type: "system",
        content:
          "🎭 Demo Mode: Here's how a conversation looks after uploading a PDF",
        timestamp: new Date(),
      },
      {
        type: "user",
        content: "What is machine learning?",
        timestamp: new Date(),
      },
      {
        type: "assistant",
        content:
          "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It involves algorithms that can identify patterns in data and make predictions or decisions based on those patterns.",
        sources: [1, 3, 7],
        confidence: 0.92,
        timestamp: new Date(),
      },
      {
        type: "user",
        content: "Can you explain neural networks?",
        timestamp: new Date(),
      },
      {
        type: "assistant",
        content:
          "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) that process information in layers. Each connection has a weight that adjusts as learning proceeds, allowing the network to recognize complex patterns in data.",
        sources: [4, 5, 6],
        confidence: 0.87,
        timestamp: new Date(),
      },
      {
        type: "system",
        content: "💡 Upload your own PDF to start asking real questions!",
        timestamp: new Date(),
      },
    ]);
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk(e);
    }
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="app-container">
      {/* Header */}
      <div className="header">
        <h1>💬 Talk2PDF</h1>
        <p>Upload a PDF and start asking questions about its content</p>
        {docId && (
          <button
            onClick={handleReset}
            style={{
              position: "absolute",
              top: "1rem",
              right: "1rem",
              background: "rgba(255,255,255,0.2)",
              color: "white",
              border: "none",
              borderRadius: "6px",
              padding: "0.5rem 1rem",
              cursor: "pointer",
              fontSize: "0.85rem",
            }}
          >
            📄 New PDF
          </button>
        )}
      </div>

      {/* Upload Section */}
      {!docId && (
        <div className="upload-section">
          <div
            className={`upload-area ${dragOver ? "dragover" : ""}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="upload-icon">📄</div>
            <div className="upload-text">
              {file
                ? "Click to change file or drag a new one"
                : "Drag & drop your PDF here or click to browse"}
            </div>
            <div
              style={{
                color: "#64748b",
                fontSize: "0.9rem",
                marginBottom: "1rem",
              }}
            >
              Supports PDF files up to 10MB
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={(e) => handleFileSelect(e.target.files[0])}
              className="file-input"
            />
            {!file && (
              <>
                <button className="upload-btn" type="button">
                  Choose PDF File
                </button>
                <div
                  style={{
                    margin: "1rem 0",
                    color: "#64748b",
                    fontSize: "0.9rem",
                  }}
                >
                  or
                </div>
                <button
                  onClick={showDemo}
                  style={{
                    background: "linear-gradient(135deg, #10b981, #059669)",
                    color: "white",
                    border: "none",
                    padding: "0.75rem 1.5rem",
                    borderRadius: "12px",
                    fontWeight: "600",
                    cursor: "pointer",
                    fontSize: "0.9rem",
                    transition: "all 0.3s ease",
                  }}
                >
                  🎭 View Demo
                </button>
                <div
                  style={{
                    marginTop: "1.5rem",
                    color: "#64748b",
                    fontSize: "0.85rem",
                  }}
                >
                  <div style={{ marginBottom: "0.5rem" }}>
                    ✨ Try it with documents like:
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "0.5rem",
                      justifyContent: "center",
                    }}
                  >
                    <span
                      style={{
                        background: "#f1f5f9",
                        padding: "0.25rem 0.5rem",
                        borderRadius: "4px",
                      }}
                    >
                      Research Papers
                    </span>
                    <span
                      style={{
                        background: "#f1f5f9",
                        padding: "0.25rem 0.5rem",
                        borderRadius: "4px",
                      }}
                    >
                      Reports
                    </span>
                    <span
                      style={{
                        background: "#f1f5f9",
                        padding: "0.25rem 0.5rem",
                        borderRadius: "4px",
                      }}
                    >
                      Manuals
                    </span>
                    <span
                      style={{
                        background: "#f1f5f9",
                        padding: "0.25rem 0.5rem",
                        borderRadius: "4px",
                      }}
                    >
                      Articles
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>

          {file && (
            <div className="file-info">
              <div className="file-name">📎 {file.name}</div>
              <div className="file-size">{formatFileSize(file.size)}</div>
              <button
                className="upload-btn"
                onClick={handleUpload}
                disabled={uploading}
                style={{ marginTop: "1rem" }}
              >
                {uploading ? (
                  <span>
                    Uploading...{" "}
                    <div className="loading-dots">
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                    </div>
                  </span>
                ) : (
                  "Upload & Process PDF"
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {error && <div className="error-message">⚠️ {error}</div>}

      {/* Chat Container */}
      {docId && (
        <div className="chat-container">
          {/* Messages */}
          <div className="messages-container">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.type}`}>
                <div className="message-content">
                  {message.type === "system" ? (
                    <div
                      style={{
                        textAlign: "center",
                        fontStyle: "italic",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {message.content}
                    </div>
                  ) : (
                    <>
                      <div>{message.content}</div>

                      {message.sources && message.sources.length > 0 && (
                        <div className="message-sources">
                          <div className="sources-label">📖 Sources:</div>
                          <div className="sources-list">
                            {message.sources.map((page, idx) => (
                              <span key={idx} className="source-tag">
                                Page {page}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {message.confidence !== undefined && (
                        <div className="confidence-score">
                          🎯 Confidence: {(message.confidence * 100).toFixed(1)}
                          %
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="message assistant">
                <div className="message-content">
                  <div className="loading-dots">
                    <span>Thinking</span>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Section */}
          <div className="input-section">
            <form onSubmit={handleAsk} className="input-container">
              <div className="input-wrapper">
                <textarea
                  ref={textareaRef}
                  value={currentQuestion}
                  onChange={handleTextareaChange}
                  onKeyDown={handleKeyPress}
                  placeholder="Ask a question about your PDF..."
                  className="question-input"
                  disabled={loading}
                  rows="1"
                />
                <button
                  type="submit"
                  className="send-btn"
                  disabled={loading || !currentQuestion.trim()}
                >
                  {loading ? (
                    <div className="loading-dots">
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                      <div className="loading-dot"></div>
                    </div>
                  ) : (
                    "➤"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
