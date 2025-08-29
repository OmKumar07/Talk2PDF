import { useState, useRef, useEffect } from "react";
import {
  uploadPDF,
  askQuestion,
  testConnection,
  checkProcessingStatus,
} from "./api";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [docId, setDocId] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [messages, setMessages] = useState([
    {
      type: "system",
      content:
        "Welcome to Talk2PDF! Upload a PDF document to start asking questions about its content.",
      timestamp: new Date(),
    },
  ]);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [backendConnected, setBackendConnected] = useState(false);

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

  // Test backend connection on mount
  useEffect(() => {
    const checkBackendConnection = async () => {
      try {
        const result = await testConnection();
        setBackendConnected(result.connected);
        if (!result.connected) {
          console.warn("Backend connection failed:", result.error);
        } else {
          console.log("Backend connection successful!");
        }
      } catch (error) {
        console.error("Connection test error:", error);
        setBackendConnected(false);
      }
    };

    checkBackendConnection();
  }, []); // Auto-scroll to bottom when new messages are added
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
        setProcessingStatus({ status: "processing" });

        setMessages([
          {
            type: "system",
            content: `Successfully uploaded "${file.name}". Processing document...`,
            timestamp: new Date(),
          },
        ]);

        // Start polling for processing status
        pollProcessingStatus(resp.doc_id);
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

  // Poll processing status
  const pollProcessingStatus = async (docId) => {
    try {
      const status = await checkProcessingStatus(docId);
      setProcessingStatus(status);

      if (status.status === "completed") {
        setMessages((prev) => [
          ...prev,
          {
            type: "system",
            content: `Document processed successfully! Found ${
              status.num_chunks || 0
            } text chunks. You can now ask questions!`,
            timestamp: new Date(),
          },
          {
            type: "system",
            content:
              "Try asking: " +
              sampleQuestions[
                Math.floor(Math.random() * sampleQuestions.length)
              ],
            timestamp: new Date(),
          },
        ]);
      } else if (status.status === "failed") {
        setError(
          `Document processing failed: ${status.error || "Unknown error"}`
        );
        setProcessingStatus(null);
        setDocId(null);
      } else {
        // Continue polling if still processing
        setTimeout(() => pollProcessingStatus(docId), 2000);
      }
    } catch (err) {
      console.error("Status check failed:", err);
      setError("Failed to check processing status.");
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
      console.log("Sending question to backend:", { docId, question });

      const resp = await askQuestion(docId, question);
      console.log("Received response:", resp);

      // Validate response structure
      if (!resp || typeof resp !== "object") {
        throw new Error("Invalid response format from server");
      }

      // Add assistant response
      const assistantMessage = {
        type: "assistant",
        content:
          resp.answer || "Sorry, I couldn't find an answer to your question.",
        sources: resp.sources || [],
        confidence: resp.confidence || resp.score || 0, // Handle both confidence and score
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Ask failed:", err);

      // More detailed error handling
      let errorContent =
        "Sorry, I encountered an error while processing your question.";

      if (err.code === "ECONNREFUSED") {
        errorContent =
          "Cannot connect to server. Please make sure the backend is running on port 8000.";
      } else if (err.response?.status === 500) {
        errorContent =
          "Server error occurred. Please try again or check the server logs.";
      } else if (err.response?.status === 400) {
        errorContent = "Invalid request. Please check your question format.";
      } else if (err.message.includes("timeout")) {
        errorContent =
          "Request timed out. Please try again with a shorter question.";
      } else if (err.message.includes("Network Error")) {
        errorContent =
          "Network error. Please check your internet connection and server status.";
      }

      const errorMessage = {
        type: "assistant",
        content: errorContent,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setError(errorContent);
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
  const retryBackendConnection = async () => {
    try {
      const result = await testConnection();
      setBackendConnected(result.connected);
      if (!result.connected && result.error) {
        console.warn("Backend connection failed:", result.error);
      } else if (result.connected) {
        console.log("Backend connection retry successful!");
      }
    } catch (error) {
      console.error("Connection retry error:", error);
      setBackendConnected(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setDocId(null);
    setMessages([
      {
        type: "system",
        content:
          "Welcome to Talk2PDF! Upload a PDF document to start asking questions about its content.",
        timestamp: new Date(),
      },
    ]);
    setCurrentQuestion("");
    setError("");
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
        <h1>Talk2PDF</h1>
        <p>Upload a PDF and start asking questions about its content</p>

        {/* Backend Status */}
        <div
          style={{
            position: "absolute",
            top: "1rem",
            left: "1rem",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            background: "rgba(255,255,255,0.15)",
            padding: "0.5rem 1rem",
            borderRadius: "6px",
            color: "white",
            fontSize: "0.9rem",
          }}
        >
          <div
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: backendConnected ? "#4ade80" : "#ef4444",
            }}
          ></div>
          {backendConnected ? "Backend Connected" : "Backend Disconnected"}
          {!backendConnected && (
            <button
              onClick={retryBackendConnection}
              style={{
                marginLeft: "0.5rem",
                background: "rgba(255,255,255,0.2)",
                color: "white",
                border: "1px solid rgba(255,255,255,0.3)",
                borderRadius: "4px",
                padding: "0.25rem 0.5rem",
                fontSize: "0.8rem",
                cursor: "pointer",
              }}
            >
              Retry
            </button>
          )}
        </div>

        {docId && (
          <button
            onClick={handleReset}
            disabled={processingStatus?.status === "processing"}
            style={{
              position: "absolute",
              top: "1rem",
              right: "1rem",
              background:
                processingStatus?.status === "processing"
                  ? "rgba(156,163,175,0.3)"
                  : "rgba(255,255,255,0.2)",
              color:
                processingStatus?.status === "processing" ? "#9ca3af" : "white",
              border: "none",
              borderRadius: "6px",
              padding: "0.5rem 1rem",
              cursor:
                processingStatus?.status === "processing"
                  ? "not-allowed"
                  : "pointer",
              fontSize: "0.85rem",
            }}
          >
            New PDF
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
            <div className="upload-icon">PDF</div>
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
                    marginTop: "1.5rem",
                    color: "#64748b",
                    fontSize: "0.85rem",
                  }}
                >
                  <div
                    style={{
                      marginBottom: "1rem",
                      padding: "1rem",
                      backgroundColor: "#fef3c7",
                      borderRadius: "8px",
                      border: "1px solid #fbbf24",
                    }}
                  >
                    <div
                      style={{
                        fontWeight: "600",
                        color: "#92400e",
                        marginBottom: "0.5rem",
                      }}
                    >
                      For Best Performance:
                    </div>
                    <div
                      style={{
                        color: "#92400e",
                        fontSize: "0.8rem",
                        lineHeight: "1.4",
                      }}
                    >
                      • Upload PDFs with fewer than 50 pages
                      <br />• File size under 20MB
                      <br />• Processing timeout: 10 minutes
                      <br />• Text-based PDFs work better than scanned images
                    </div>
                  </div>
                  <div style={{ marginBottom: "0.5rem" }}>
                    Try it with documents like:
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
              <div className="file-name">File: {file.name}</div>
              <div className="file-size">{formatFileSize(file.size)}</div>
              <button
                className="upload-btn"
                onClick={handleUpload}
                disabled={
                  uploading ||
                  (processingStatus && processingStatus.status === "processing")
                }
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
                ) : processingStatus &&
                  processingStatus.status === "processing" ? (
                  <span>Document Processing...</span>
                ) : (
                  "Upload & Process PDF"
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Document Processing Spinner */}
      {processingStatus && processingStatus.status === "processing" && (
        <div className="processing-loader">
          <div className="spinner"></div>
          <div className="processing-title">Processing Your Document</div>
          <div className="processing-subtitle">
            Analyzing content and creating searchable chunks...
          </div>
          <div
            style={{
              marginTop: "1rem",
              fontSize: "0.8rem",
              color: "#64748b",
              fontStyle: "italic",
            }}
          >
            This may take 30-60 seconds for large documents...
          </div>
          <div
            style={{
              marginTop: "1.5rem",
              padding: "1rem",
              backgroundColor: "#fef3c7",
              borderRadius: "8px",
              border: "1px solid #fbbf24",
              color: "#92400e",
              fontSize: "0.9rem",
            }}
          >
            Please wait while we process your document. Chat will be available
            once processing is complete.
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && <div className="error-message">Error: {error}</div>}

      {/* Chat Container */}
      {docId && processingStatus?.status !== "processing" && (
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
                          <div className="sources-label">Sources:</div>
                          <div className="sources-list">
                            {message.sources.map((source, idx) => (
                              <span
                                key={idx}
                                className="source-tag"
                                title={
                                  typeof source === "object" && source.text
                                    ? `"${source.text.slice(0, 100)}..."`
                                    : undefined
                                }
                              >
                                {typeof source === "object"
                                  ? `Page ${source.page}${
                                      source.relevance
                                        ? ` (${(source.relevance * 100).toFixed(
                                            0
                                          )}%)`
                                        : ""
                                    }`
                                  : `Page ${source}`}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {message.confidence !== undefined && (
                        <div className="confidence-score">
                          Confidence: {(message.confidence * 100).toFixed(1)}%
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
                  Send
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
