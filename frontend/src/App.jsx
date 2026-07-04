import { useState } from 'react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [messages, setMessages] = useState([
    { text: "Welcome to EduGuard Auto-Tutor! Upload a textbook to begin.", sender: "bot" }
  ])
  const [input, setInput] = useState("")

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return;
    
    const formData = new FormData();
    formData.append("file", file);

    setMessages([...messages, { text: `Uploading and analyzing ${file.name}...`, sender: "bot" }])

    try {
      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setMessages(prev => [...prev, { text: `Successfully processed ${data.filename}! You can now ask questions about it.`, sender: "bot" }]);
    } catch (error) {
      setMessages(prev => [...prev, { text: "Failed to upload file. Make sure the backend is running.", sender: "bot" }]);
    }
  }

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { text: input, sender: "user" };
    setMessages(prev => [...prev, userMessage]);
    const query = input;
    setInput("");

    try {
      const response = await fetch(`http://localhost:8000/api/query?query=${encodeURIComponent(query)}`, {
        method: "POST"
      });
      const data = await response.json();
      setMessages(prev => [...prev, { text: data.response, sender: "bot" }]);
    } catch (error) {
      setMessages(prev => [...prev, { text: "Error connecting to tutor AI.", sender: "bot" }]);
    }
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>EduGuard</h1>
        <div style={{ color: "var(--text-secondary)" }}>Privacy-First Auto-Tutor</div>
      </header>
      
      <main className="main-content">
        <aside className="sidebar">
          <div className="upload-section">
            <h3>Knowledge Source</h3>
            <label className="upload-box">
              <input type="file" accept=".pdf" onChange={handleFileChange} />
              {file ? file.name : "Drag & Drop PDF or Click to Browse"}
            </label>
            <button className="btn-upload" onClick={handleUpload} disabled={!file}>
              Process Textbook
            </button>
          </div>
          
          <div className="graph-preview" style={{marginTop: "2rem", flex: 1, borderTop: "1px solid var(--glass-border)", paddingTop: "1rem"}}>
            <h3>Concept Graph</h3>
            <div style={{ color: "var(--text-secondary)", fontSize: "0.9rem", textAlign: "center", marginTop: "2rem" }}>
              Upload a document to build the relational knowledge graph.
            </div>
          </div>
        </aside>
        
        <section className="chat-area">
          <div className="messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.sender}`}>
                {msg.text}
              </div>
            ))}
          </div>
          
          <div className="input-area">
            <input 
              type="text" 
              placeholder="Ask a question about the material..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button className="btn-send" onClick={handleSend}>Send</button>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
