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

  const handleDeleteNotebook = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this notebook and all its data?")) return;
    try {
      await fetch(`http://localhost:8000/api/notebooks/${id}`, { method: "DELETE" })
      setNotebooks(notebooks.filter(n => n.id !== id))
      if (activeNotebook === id) {
        setActiveNotebook(null)
        setNbMessages([])
        setSources([])
      }
    } catch (e) { console.error(e) }
  }

  const handleRenameNotebook = async (id, e) => {
    e.stopPropagation();
    const newName = window.prompt("Enter new name:");
    if (!newName) return;
    try {
      await fetch(`http://localhost:8000/api/notebooks/${id}`, { 
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newName }) 
      })
      setNotebooks(notebooks.map(n => n.id === id ? {...n, name: newName} : n))
    } catch (e) { console.error(e) }
  }

  const handleDeleteSource = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Delete this source?")) return;
    try {
      await fetch(`http://localhost:8000/api/sources/${id}`, { method: "DELETE" })
      setSources(sources.filter(s => s.id !== id))
      setSelectedSources(selectedSources.filter(sId => sId !== id))
    } catch (e) { console.error(e) }
  }

  const handleRenameSource = async (id, e) => {
    e.stopPropagation();
    const newName = window.prompt("Enter new source name (keep .pdf extension if you wish):");
    if (!newName) return;
    try {
      await fetch(`http://localhost:8000/api/sources/${id}`, { 
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: newName }) 
      })
      setSources(sources.map(s => s.id === id ? {...s, filename: newName} : s))
    } catch (e) { console.error(e) }
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
        body: JSON.stringify({ action_type: actionType, sources: selectedSources, notebook_id: activeNotebook })
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

  const [localEndpoint, setLocalEndpoint] = useState("http://localhost:11434")
  const [cloudEndpoint, setCloudEndpoint] = useState("")

  useEffect(() => {
    // Fetch initial endpoints
    fetch("http://localhost:8000/api/config/endpoint")
      .then(res => res.json())
      .then(data => {
        setLocalEndpoint(data.local_endpoint)
        setCloudEndpoint(data.cloud_endpoint)
      })
      .catch(e => console.error(e))
  }, [])

  const handleUpdateEndpoint = async () => {
    try {
      await fetch("http://localhost:8000/api/config/endpoint", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ local_endpoint: localEndpoint, cloud_endpoint: cloudEndpoint })
      })
      alert("Endpoints updated successfully!")
    } catch(e) {
      alert("Failed to update endpoints.")
    }
  }

  return (
    <div className="app-container">
      <header className="header" style={{flexDirection: "column", alignItems: "stretch", gap: "1rem"}}>
        <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
          <h1>EduGuard</h1>
          <div className="nav-menu">
            <button className={`nav-btn ${appMode === 'notebook' ? 'active' : ''}`} onClick={() => setAppMode('notebook')}>Notebook Mode</button>
            <button className={`nav-btn ${appMode === 'diary' ? 'active' : ''}`} onClick={() => setAppMode('diary')}>AI Diary Mode</button>
          </div>
        </div>
        <div style={{display: "flex", gap: "0.5rem", alignItems: "center", alignSelf: "flex-end"}}>
          <input 
            type="text" 
            value={localEndpoint} 
            onChange={e => setLocalEndpoint(e.target.value)} 
            placeholder="Local LLM API (e.g. localhost:11434)"
            style={{background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.1)", color: "white", padding: "0.5rem", borderRadius: "4px", width: "250px"}}
          />
          <input 
            type="text" 
            value={cloudEndpoint} 
            onChange={e => setCloudEndpoint(e.target.value)} 
            placeholder="Cloud LLM API (e.g. Kaggle loca.lt)"
            style={{background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.1)", color: "white", padding: "0.5rem", borderRadius: "4px", width: "250px"}}
          />
          <button onClick={handleUpdateEndpoint} style={{background: "var(--accent)", color: "white", border: "none", padding: "0.5rem", borderRadius: "4px", cursor: "pointer"}}>Save Config</button>
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
                      <span className="nb-name">{nb.name}</span>
                      <div className="item-actions">
                        <button onClick={(e) => handleRenameNotebook(nb.id, e)}>✏️</button>
                        <button onClick={(e) => handleDeleteNotebook(nb.id, e)}>🗑️</button>
                      </div>
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
                        <div key={source.id} className="source-item">
                          <label style={{display: "flex", gap: "0.5rem", flex: 1, alignItems: "center", cursor: "pointer"}}>
                            <input type="checkbox" checked={selectedSources.includes(source.id)} onChange={() => toggleSource(source.id)} />
                            <span className="source-name" title={source.filename}>{source.filename}</span>
                          </label>
                          <div className="item-actions">
                            <button onClick={(e) => handleRenameSource(source.id, e)}>✏️</button>
                            <button onClick={(e) => handleDeleteSource(source.id, e)}>🗑️</button>
                          </div>
                        </div>
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
