
import { useState } from 'react'
import axios from 'axios'
import { Upload, Database, ShieldCheck, AlertTriangle, FileSpreadsheet } from 'lucide-react'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function analyzeFile(event) {
    event.preventDefault()

    if (!file) {
      setError('Please select a CSV file first.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post(
        `${API_URL}/api/datasets/analyze`,
        formData
      )
      setResult(response.data)
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        'Could not analyze the file. Check that the backend is running.'
      )
    } finally {
      setLoading(false)
    }
  }

  const quality = result?.quality

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon"><Database size={23} /></div>
          <div>
            <h2>DataTrace</h2>
            <span>DATA INTELLIGENCE</span>
          </div>
        </div>

        <nav>
          <div className="nav-item active">
            <Database size={18} /> Overview
          </div>
          <div className="nav-item">
            <FileSpreadsheet size={18} /> Data Quality
          </div>
          <div className="nav-item">
            <ShieldCheck size={18} /> Analysis
          </div>
        </nav>

        <div className="sidebar-bottom">
          <span className="status-dot" />
          Backend connection
          <strong>API :8000</strong>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">DATA PLATFORM / OVERVIEW</p>
            <h1>Data Quality Dashboard</h1>
            <p className="subtitle">
              Understand your data. Detect quality issues. Make better decisions.
            </p>
          </div>
          <div className="api-badge">
            <span className="status-dot" /> API configured
          </div>
        </header>

        <section className="stats-grid">
          <article className="stat-card">
            <div className="stat-heading">Quality score <ShieldCheck size={20} /></div>
            <div className="stat-value">
              {quality ? `${quality.quality_score}%` : '—'}
            </div>
            <p>{quality ? 'Latest analysis' : 'Analyze a CSV to begin'}</p>
          </article>

          <article className="stat-card">
            <div className="stat-heading">Missing cells <AlertTriangle size={20} /></div>
            <div className="stat-value">{quality?.missing_cells ?? '—'}</div>
            <p>Empty or missing values</p>
          </article>

          <article className="stat-card">
            <div className="stat-heading">Duplicate rows <Database size={20} /></div>
            <div className="stat-value">{quality?.duplicate_rows ?? '—'}</div>
            <p>Repeated complete rows</p>
          </article>

          <article className="stat-card">
            <div className="stat-heading">Rows analyzed <FileSpreadsheet size={20} /></div>
            <div className="stat-value">{result?.profile?.row_count ?? '—'}</div>
            <p>{result ? `${result.profile.column_count} columns detected` : 'Dataset size'}</p>
          </article>
        </section>

        <section className="content-grid">
          <article className="panel upload-panel">
            <div className="panel-title">
              <div>
                <h2>Analyze a dataset</h2>
                <p>Upload a CSV file to generate a data quality report.</p>
              </div>
              <Upload size={22} />
            </div>

            <form onSubmit={analyzeFile}>
              <label className="upload-zone">
                <Upload size={34} />
                <strong>{file ? file.name : 'Choose a CSV file'}</strong>
                <span>
                  {file
                    ? `${(file.size / 1024).toFixed(1)} KB selected`
                    : 'Click here to browse your computer'}
                </span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(event) => {
                    setFile(event.target.files?.[0] ?? null)
                    setError('')
                  }}
                />
              </label>

              <button className="analyze-button" type="submit" disabled={loading}>
                {loading ? 'Analyzing dataset...' : 'Analyze dataset'}
              </button>
            </form>

            {error && <p className="error-message">{error}</p>}

            {quality && (
              <div className="result-summary">
                <ShieldCheck size={20} />
                <div>
                  <strong>Analysis complete — {quality.status}</strong>
                  <p>Dataset ID: {result.id} · File: {result.dataset}</p>
                </div>
              </div>
            )}
          </article>

          <article className="panel">
            <div className="panel-title">
              <div>
                <h2>Dataset profile</h2>
                <p>Columns found in your latest upload.</p>
              </div>
              <FileSpreadsheet size={22} />
            </div>

            {result?.profile?.columns?.length ? (
              <div className="column-list">
                {result.profile.columns.map((column) => (
                  <div className="column-row" key={column}>
                    <span>{column}</span>
                    <span className="type-label">
                      {result.profile.data_types?.[column] ?? 'Unknown'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <Database size={32} />
                <strong>No dataset analyzed yet</strong>
                <span>Your column profile will appear here after upload.</span>
              </div>
            )}
          </article>
        </section>

        {result && (
          <section className="panel details-panel">
            <div className="panel-title">
              <div>
                <h2>Quality report</h2>
                <p>Summary of the most recent CSV analysis.</p>
              </div>
              <span className={`quality-pill ${quality.status.toLowerCase()}`}>
                {quality.status}
              </span>
            </div>

            <div className="report-grid">
              <div>
                <span>Dataset</span>
                <strong>{result.dataset}</strong>
              </div>
              <div>
                <span>Rows</span>
                <strong>{result.profile.row_count}</strong>
              </div>
              <div>
                <span>Columns</span>
                <strong>{result.profile.column_count}</strong>
              </div>
              <div>
                <span>Quality score</span>
                <strong>{quality.quality_score}/100</strong>
              </div>
            </div>

            <h3>Missing values by column</h3>
            <div className="column-list">
              {Object.entries(result.profile.missing_values ?? {}).map(
                ([column, count]) => (
                  <div className="column-row" key={column}>
                    <span>{column}</span>
                    <strong>{count}</strong>
                  </div>
                )
              )}
            </div>
          </section>
        )}

        <footer>DataTrace AI · Data quality and lineage platform</footer>
      </main>
    </div>
  )
}

export default App
