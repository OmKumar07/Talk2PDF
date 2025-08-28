// frontend/src/App.jsx
import { useState } from "react";
import { uploadPDF, askQuestion } from "./api";

function App() {
  const [file, setFile] = useState(null);
  const [docId, setDocId] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  async function handleUpload() {
    if (!file) return;
    const resp = await uploadPDF(file);
    setDocId(resp.doc_id);
  }

  async function handleAsk() {
    if (!docId || !question) return;
    const resp = await askQuestion(docId, question);
    setAnswer(resp.answer);
  }

  return (
    <div style={{ padding: "20px" }}>
      <h1>Talk2PDF</h1>

      <div>
        <input type="file" onChange={(e) => setFile(e.target.files[0])} />
        <button onClick={handleUpload}>Upload PDF</button>
      </div>

      {docId && (
        <div style={{ marginTop: "20px" }}>
          <input
            type="text"
            placeholder="Ask a question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button onClick={handleAsk}>Ask</button>
        </div>
      )}

      {answer && (
        <div style={{ marginTop: "20px" }}>
          <h3>Answer:</h3>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}

export default App; // 👈 this is required
