import { useState, useEffect, useRef } from 'react'
import './App.css'

function App() {
  const [appMode, setAppMode] = useState("notebook") // "notebook" | "diary"
  
  // Notebook States
  const [notebooks, setNotebooks] = useState([])
  const [activeNotebook, setActiveNotebook] = useState(null)
  const [newNotebookName, setNewNotebookName] = useState("")
  
  const [file, setFile] = useState(null)
  const [sources, setSources] = useState([])
  const [selectedSources, setSelectedSources] = useState([])
  
  const [nbMessages, setNbMessages] = useState([])
  const [nbInput, setNbInput] = useState("")

  // Diary States
  const [diaryEntries, setDiaryEntries] = useState([])
  const [diaryInput, setDiaryInput] = useState("")

  // Fetch Notebooks
  const fetchNotebooks = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/notebooks")
      const data = await res.json()
      setNotebooks(data.notebooks)
      if (data.notebooks.length > 0 && !activeNotebook) {
        setActiveNotebook(data.notebooks[0].id)
      }
    } catch (e) {
      console.error(e)
    }
  }

  // Fetch Sources for Active Notebook
  const fetchSources = async (nbId) => {
    try {
      const res = await fetch(`http://localhost:8000/api/sources?notebook_id=${nbId}`)
      const data = await res.json()
      setSources(data.sources)
      setSelectedSources(data.sources.map(s => s.id))
    } catch (e) {
      console.error(e)
    }
  }

  // Fetch Chat History
  const fetchHistory = async (nbId) => {
    try {
      const res = await fetch(`http://localhost:8000/api/notebooks/${nbId}/history`)
      const data = await res.json()
      const formatted = data.history.map(h => ({
        text: h.text,
        sender: h.role === "user" ? "user" : "bot"
      }))
      setNbMessages([{ text: "Welcome back to your notebook!", sender: "bot" }, ...formatted])
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchNotebooks()
  }, [])

  useEffect(() => {
    if (activeNotebook && appMode === 'notebook') {
      fetchSources(activeNotebook)
      fetchHistory(activeNotebook)
    }
  }, [activeNotebook, appMode])

  // Create Notebook
  const handleCreateNotebook = async () => {
    if (!newNotebookName.trim()) return;
    try {
      const res = await fetch("http://localhost:8000/api/notebooks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newNotebookName })
      })
      const data = await res.json()
      setNotebooks([...notebooks, data])
      setActiveNotebook(data.id)
      setNewNotebookName("")
    } catch (e) {
      console.error(e)
    }
  }

  // Notebook Handlers
  const handleUpload = async () => {
    if (!file || !activeNotebook) return;
    const formData = new FormData();
    formData.append("file", file);
    
    setNbMessages(prev => [...prev, { text: `Uploading and analyzing ${file.name}...`, sender: "bot" }])

    try {
      const res = await fetch(`http://localhost:8000/api/upload?notebook_id=${activeNotebook}`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setNbMessages(prev => [...prev, { text: `Successfully processed ${data.filename}!`, sender: "bot" }]);
      fetchSources(activeNotebook);
      setFile(null);
    } catch (error) {
      setNbMessages(prev => [...prev, { text: "Failed to upload file.", sender: "bot" }]);
    }
  }

  const handleSendNb = async () => {
    if (!nbInput.trim() || !activeNotebook) return;
    const q = nbInput;
    setNbMessages(prev => [...prev, { text: q, sender: "user" }]);
    setNbInput("");

    try {
      const res = await fetch("http://localhost:8000/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, sources: selectedSources, notebook_id: activeNotebook })
      });
      const data = await res.json();
      setNbMessages(prev => [...prev, { text: data.response, sender: "bot" }]);
    } catch (error) {
      setNbMessages(prev => [...prev, { text: "Error connecting to tutor AI.", sender: "bot" }]);
    }
  }

  const handleAction = async (actionType) => {
    if (!activeNotebook) return;
    setNbMessages(prev => [...prev, { text: `Generating ${actionType}...`, sender: "bot" }]);
    try {
      const res = await fetch("http://localhost:8000/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_type: actionType, sources: selectedSources })
      });
      const data = await res.json();
      setNbMessages(prev => [...prev, { text: data.response, sender: "bot" }]);
    } catch (error) {
      setNbMessages(prev => [...prev, { text: "Error performing action.", sender: "bot" }]);
    }
  }

  // Diary Handlers
  const fetchDiaryHistory = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/diary/history")
      const data = await res.json()
      setDiaryEntries(data.entries)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    if (appMode === 'diary') {
      fetchDiaryHistory()
    }
  }, [appMode])

  const handleSendDiary = async () => {
    if (!diaryInput.trim()) return;
    const text = diaryInput;
    setDiaryInput("");
    
    // Optimistic UI
    const tempEntry = { text: text, response: "...", synth: "Synthesizing...", date: "Just now" };
    setDiaryEntries(prev => [...prev, tempEntry]);

    try {
      await fetch("http://localhost:8000/api/diary/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
      fetchDiaryHistory();
    } catch (e) {
      console.error(e)
    }
  }

  const handleExportDiary = () => {
    window.open("http://localhost:8000/api/diary/export", "_blank");
  }

  const toggleSource = (id) => {
    setSelectedSources(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id])
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>EduGuard</h1>
        <div className="nav-menu">
          <button className={`nav-btn ${appMode === 'notebook' ? 'active' : ''}`} onClick={() => setAppMode('notebook')}>Notebook Mode</button>
          <button className={`nav-btn ${appMode === 'diary' ? 'active' : ''}`} onClick={() => setAppMode('diary')}>AI Diary Mode</button>
        </div>
      </header>
      
      <main className="main-content">
        {appMode === 'notebook' && (
          <>
            <aside className="sidebar">
              <div className="notebook-selector">
                <h3>My Notebooks</h3>
                <div style={{display: 'flex', gap: '0.5rem', marginBottom: '1rem'}}>
                  <input type="text" placeholder="New Notebook..." value={newNotebookName} onChange={e => setNewNotebookName(e.target.value)} />
                  <button onClick={handleCreateNotebook}>Add</button>
                </div>
                <div className="nb-list">
                  {notebooks.map(nb => (
                    <div 
                      key={nb.id} 
                      className={`nb-item ${activeNotebook === nb.id ? 'active' : ''}`}
                      onClick={() => setActiveNotebook(nb.id)}
                    >
                      {nb.name}
                    </div>
                  ))}
                </div>
              </div>

              {activeNotebook && (
                <>
                  <div className="upload-section" style={{marginTop: '2rem'}}>
                    <h3>Add to Notebook</h3>
                    <label className="upload-box">
                      <input type="file" accept=".pdf" onChange={e => setFile(e.target.files[0])} />
                      {file ? file.name : "Select PDF..."}
                    </label>
                    <button className="btn-upload" onClick={handleUpload} disabled={!file}>Upload</button>
                  </div>

                  <div className="sources-list" style={{marginTop: "1.5rem", flex: 1, overflowY: "auto"}}>
                    <h3>Notebook Sources</h3>
                    <div style={{display: "flex", flexDirection: "column", gap: "0.5rem"}}>
                      {sources.map(source => (
                        <label key={source.id} className="source-item">
                          <input type="checkbox" checked={selectedSources.includes(source.id)} onChange={() => toggleSource(source.id)} />
                          <span className="source-name">{source.filename}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </aside>
            
            <section className="chat-area">
              {!activeNotebook ? (
                <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)'}}>
                  Select or create a notebook to begin.
                </div>
              ) : (
                <>
                  <div className="messages">
                    {nbMessages.map((msg, idx) => (
                      <div key={idx} className={`message ${msg.sender}`}>{msg.text}</div>
                    ))}
                  </div>
                  <div className="quick-actions">
                    <button className="btn-action" onClick={() => handleAction("report")}>Generate Report</button>
                    <button className="btn-action" onClick={() => handleAction("quiz")}>Create Quiz</button>
                    <button className="btn-action" onClick={() => handleAction("keywords")}>List Keywords</button>
                  </div>
                  <div className="input-area">
                    <input type="text" placeholder="Ask your notebook..." value={nbInput} onChange={e => setNbInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSendNb()} />
                    <button className="btn-send" onClick={handleSendNb}>Send</button>
                  </div>
                </>
              )}
            </section>
          </>
        )}

        {appMode === 'diary' && (
          <div className="diary-container">
            <div className="diary-header">
              <h2>My Personal AI Diary</h2>
              <button className="btn-export" onClick={handleExportDiary}>Export to PDF</button>
            </div>
            
            <div className="diary-entries">
              {diaryEntries.map((e, idx) => (
                <div key={idx} className="diary-entry-card">
                  <div className="diary-meta">
                    <span className="diary-date">{e.date}</span>
                    <span className="diary-synth">Theme: {e.synth}</span>
                  </div>
                  <div className="diary-text">{e.text}</div>
                  <div className="diary-companion">
                    <strong>Companion:</strong> {e.response}
                  </div>
                </div>
              ))}
            </div>

            <div className="diary-input-area">
              <textarea 
                placeholder="How are you feeling today? Write your journal entry..." 
                value={diaryInput} 
                onChange={e => setDiaryInput(e.target.value)}
              />
              <button className="btn-send" onClick={handleSendDiary}>Save Entry</button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
