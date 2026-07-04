import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [messages, setMessages] = useState([
    { text: "Welcome to EduGuard Auto-Tutor! Upload a textbook to begin.", sender: "bot" }
  ])
  const [input, setInput] = useState("")
  const [sources, setSources] = useState([])
  const [selectedSources, setSelectedSources] = useState([])

  const fetchSources = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/sources")
      const data = await response.json()
      setSources(data.sources)
      // Automatically select all new sources
      setSelectedSources(data.sources.map(s => s.id))
    } catch (e) {
      console.error("Could not fetch sources", e)
    }
  }

  useEffect(() => {
    fetchSources()
  }, [])

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return;
    
    const formData = new FormData();
    formData.append("file", file);

    setMessages([...messages, { text: `Uploading and analyzing ${file.name}... this may take a minute.`, sender: "bot" }])

    try {
      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setMessages(prev => [...prev, { text: `Successfully processed ${data.filename}!`, sender: "bot" }]);
      fetchSources();
    } catch (error) {
      setMessages(prev => [...prev, { text: "Failed to upload file.", sender: "bot" }]);
    }
  }

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { text: input, sender: "user" };
    setMessages(prev => [...prev, userMessage]);
    const query = input;
    setInput("");

    try {
      const response = await fetch("http://localhost:8000/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, sources: selectedSources.length > 0 ? selectedSources : null })
      });
      const data = await response.json();
      setMessages(prev => [...prev, { text: data.response, sender: "bot" }]);
    } catch (error) {
      setMessages(prev => [...prev, { text: "Error connecting to tutor AI.", sender: "bot" }]);
    }
  }

  const handleAction = async (actionType) => {
    setMessages(prev => [...prev, { text: `Generating ${actionType}...`, sender: "bot" }]);
    try {
      const response = await fetch("http://localhost:8000/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_type: actionType, sources: selectedSources.length > 0 ? selectedSources : null })
      });
      const data = await response.json();
      setMessages(prev => [...prev, { text: data.response, sender: "bot" }]);
    } catch (error) {
      setMessages(prev => [...prev, { text: "Error performing action.", sender: "bot" }]);
    }
  }

  const clearMemory = async () => {
    try {
      await fetch("http://localhost:8000/api/clear", { method: "POST" })
      setMessages([{ text: "Memory wiped. Upload a new textbook to begin.", sender: "bot" }])
      setSources([])
      setSelectedSources([])
    } catch (e) {
      console.error(e)
    }
  }

  const toggleSource = (id) => {
    setSelectedSources(prev => 
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    )
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>EduGuard</h1>
        <div style={{ color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "1rem" }}>
          <span>Privacy-First Auto-Tutor</span>
          <button className="btn-clear" onClick={clearMemory}>Clean Memory</button>
        </div>
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
          
          <div className="sources-list" style={{marginTop: "1.5rem", flex: 1, overflowY: "auto"}}>
            <h3>Active Sources</h3>
            {sources.length === 0 ? (
              <div style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>No sources uploaded yet.</div>
            ) : (
              <div style={{display: "flex", flexDirection: "column", gap: "0.5rem"}}>
                {sources.map(source => (
                  <label key={source.id} className="source-item">
                    <input 
                      type="checkbox" 
                      checked={selectedSources.includes(source.id)} 
                      onChange={() => toggleSource(source.id)} 
                    />
                    <span className="source-name">{source.filename}</span>
                  </label>
                ))}
              </div>
            )}
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

          <div className="quick-actions">
            <button className="btn-action" onClick={() => handleAction("report")}>Generate Report</button>
            <button className="btn-action" onClick={() => handleAction("quiz")}>Create Quiz</button>
            <button className="btn-action" onClick={() => handleAction("keywords")}>List Keywords</button>
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
