import { useCallback, useEffect, useMemo, useState } from 'react'
import axios from 'axios'
import {
  Activity, AlertTriangle, ArrowDownRight, BarChart3, CheckCircle2,
  ChevronRight, Database, FileSpreadsheet, GitBranch, LayoutDashboard,
  LoaderCircle, RefreshCw, Search, ShieldCheck, Upload, Workflow,
} from 'lucide-react'
import './App.css'
import DatabaseConnections from './DatabaseConnections'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const api = axios.create({ baseURL: API_URL, timeout: 30000 })

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'quality', label: 'Data Quality', icon: ShieldCheck },
  { id: 'anomalies', label: 'Anomaly Detection', icon: AlertTriangle },
  { id: 'lineage', label: 'Data Lineage', icon: GitBranch },
  { id: 'investigation', label: 'Root Cause & Impact', icon: Activity },
  { id: 'connections', label: 'Database Connections', icon: Database },
]

function errorText(error) {
  const detail = error?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Request failed. Check the backend and try again.'
}

function StatCard({ label, value, note, icon: Icon }) {
  return <article className="stat-card">
    <div className="stat-heading"><span>{label}</span><Icon size={19} /></div>
    <div className="stat-value">{value ?? '—'}</div>
    <p>{note}</p>
  </article>
}

function EmptyState({ title, detail }) {
  return <div className="empty-state"><Database size={30} /><strong>{title}</strong><span>{detail}</span></div>
}

function DataTable({ columns, rows, emptyText = 'No records to display.' }) {
  if (!rows?.length) return <EmptyState title="Nothing here yet" detail={emptyText} />
  return <div className="table-wrap"><table><thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
    <tbody>{rows.map((row, i) => <tr key={row.id ?? `${i}-${row.column_name ?? row.name ?? ''}`}>
      {columns.map((c) => <td key={c.key}>{c.render ? c.render(row[c.key], row) : String(row[c.key] ?? '—')}</td>)}
    </tr>)}</tbody></table></div>
}

function App() {
  const [page, setPage] = useState('overview')
  const [file, setFile] = useState(null)
  const [datasetFile, setDatasetFile] = useState(null)
  const [result, setResult] = useState(null)
  const [datasets, setDatasets] = useState([])
  const [datasetId, setDatasetId] = useState('')
  const [detail, setDetail] = useState(null)
  const [anomalies, setAnomalies] = useState([])
  const [anomalyMethod, setAnomalyMethod] = useState('IQR')
  const [lineage, setLineage] = useState(null)
  const [investigation, setInvestigation] = useState(null)
  const [impact, setImpact] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const selectedId = datasetId || result?.id || ''
  const selectedDataset = datasets.find(
    (d) => String(d.id) === String(selectedId)
  )

  const selectedFilename = (
    selectedDataset?.filename ?? detail?.dataset ?? result?.dataset ?? ''
  ).toLowerCase()

  const isDatabaseDataset =
  selectedDataset?.source_type === 'database' ||
  detail?.source_type === 'database'

  const [sourceMode, setSourceMode] = useState('csv')
  const [liveAnomalyCount, setLiveAnomalyCount] = useState(0)
  const [lastLiveRefresh, setLastLiveRefresh] = useState(null)

  useEffect(() => {
    if (!selectedId) return

    if (isDatabaseDataset) {
      setSourceMode('database')
    } else if (selectedFilename.endsWith('.csv')) {
      setSourceMode('csv')
    }
  }, [selectedId, isDatabaseDataset, selectedFilename])
  const quality = detail?.quality ?? result?.quality
  const columnQualityRows = quality?.column_profiles ?? []
  const whitespaceIssues = Object.entries(
    quality?.whitespace_issues ?? {}
  ).map(([column, count]) => ({ column, count }))

  const duplicateColumnNames = quality?.duplicate_column_names ?? []
  const profile = detail?.profile ?? result?.profile
  const pageTitle = NAV_ITEMS.find((item) => item.id === page)?.label ?? 'Overview'

  const refreshDatasets = useCallback(async (preferId) => {
    try {
      const response = await api.get('/api/datasets')
      const list = response.data ?? []
      setDatasets(list)
      const wanted = preferId ?? selectedId
      if (wanted && list.some((d) => String(d.id) === String(wanted))) setDatasetId(String(wanted))
      else if (!datasetId && list.length) setDatasetId(String(list[0].id))
      return list
    } catch (err) {
      setError(errorText(err))
      return []
    }
  }, [datasetId, selectedId])

  useEffect(() => { refreshDatasets() }, []) // initial dataset list

const loadDataset = useCallback(async (id) => {
  if (!id) return

  try {
    const response = await api.get(`/api/datasets/${id}`)
    setDetail(response.data)
  } catch (err) {
    setDetail(null)
    setError(errorText(err))
  }
}, [])

  useEffect(() => {
    if (selectedId) loadDataset(selectedId)
    else setDetail(null)
  }, [selectedId, loadDataset])


  // Automatically refresh the selected database dataset every 5 seconds.
useEffect(() => {
  if (sourceMode !== 'database' || !selectedId) {
    return
  }

  let active = true
  let refreshing = false

  const refreshLiveData = async () => {
    if (refreshing) return

    refreshing = true

    try {
      const [detailResponse, listResponse, anomalyResponse] =
        await Promise.all([
          api.get(`/api/datasets/${selectedId}`),
          api.get('/api/datasets'),
          api.get(`/api/datasets/${selectedId}/anomalies`),
        ])

      if (!active) return

      setDetail(detailResponse.data)
      setDatasets(listResponse.data ?? [])

      setLiveAnomalyCount(
        anomalyResponse.data.anomaly_count ??
        anomalyResponse.data.anomalies?.length ??
        0
      )

      setLastLiveRefresh(new Date())

    } catch (err) {
      console.error('Live refresh failed:', err)
    } finally {
      refreshing = false
    }
  }

  refreshLiveData()

  const intervalId = window.setInterval(
    refreshLiveData,
    5000
  )

  return () => {
    active = false
    window.clearInterval(intervalId)
  }

}, [sourceMode, selectedId])
  async function analyzeFile(event) {
    event.preventDefault()
    if (!file) { setError('Choose a CSV file first.'); return }
    setBusy(true); setError(''); setNotice('')
    const formData = new FormData(); formData.append('file', file)
    try {
      const response = await api.post('/api/datasets/analyze', formData)
      setResult(response.data); setDetail(response.data); setDatasetFile(file)
      setDatasetId(String(response.data.id))
      await refreshDatasets(response.data.id)
      setNotice(`Analysis completed. Dataset ID: ${response.data.id}`)
      setPage('overview')
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }

  async function loadAnomalies() {
    if (!selectedId) return
    setBusy(true); setError(''); setNotice('')
    try {
      const response = await api.get(`/api/datasets/${selectedId}/anomalies`)
      setAnomalies(response.data.anomalies ?? [])
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }


async function detectAnomalies(event) {
  event.preventDefault()

  if (!selectedId) {
    setError('Analyze or select a dataset first.')
    return
  }

  if (!datasetFile) {
    setError(
      'Select the original CSV file for this dataset before running detection.'
    )
    return
  }

  setBusy(true)
  setError('')
  setNotice('')

  try {
    const formData = new FormData()
    formData.append('file', datasetFile)

    const response = await api.post(
      `/api/datasets/${selectedId}/anomalies`,
      formData,
      { params: { method: anomalyMethod } }
    )

    setAnomalies(response.data.anomalies ?? [])
    setNotice(
      `${response.data.method} detection finished: ${
        response.data.anomaly_count ?? 0
      } findings.`
    )
  } catch (err) {
    setError(errorText(err))
  } finally {
    setBusy(false)
  }
}


  async function loadLineage() {
    if (!selectedId) return
    setBusy(true); setError(''); setNotice('')
    try {
      const response = await api.get(`/api/datasets/${selectedId}/lineage`)
      setLineage(response.data)
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }

  async function createLineage() {
    if (!selectedId) { setError('Analyze or select a dataset first.'); return }
    setBusy(true); setError(''); setNotice('')
    try {
      const response = await api.post(`/api/datasets/${selectedId}/lineage`)
      setLineage(response.data); setNotice('PostgreSQL lineage created successfully.')
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }

  async function syncLineage() {
    if (!selectedId) return
    setBusy(true); setError(''); setNotice('')
    try {
      const response = await api.post(`/api/datasets/${selectedId}/lineage/sync`)
      setNotice(response.data.message || 'Lineage synced to Neo4j.')
    } catch (err) { setError(errorText(err)) }
    finally { setBusy(false) }
  }

  async function loadInvestigation() {
    if (!selectedId) return
    setBusy(true); setError(''); setNotice('')
    try {
      const [rcaResponse, impactResponse] = await Promise.allSettled([
        api.get(`/api/datasets/${selectedId}/rca`),
        api.get(`/api/datasets/${selectedId}/impact`),
      ])
      if (rcaResponse.status === 'fulfilled') setInvestigation(rcaResponse.value.data)
      else setInvestigation({ error: errorText(rcaResponse.reason) })
      if (impactResponse.status === 'fulfilled') setImpact(impactResponse.value.data)
      else setImpact({ error: errorText(impactResponse.reason) })
      if (rcaResponse.status === 'rejected' && impactResponse.status === 'rejected') setError('RCA and impact requests failed. Check the backend and Neo4j connection.')
    } finally { setBusy(false) }
  }

  useEffect(() => {
    if (page === 'anomalies' && selectedId) loadAnomalies()
    if (page === 'lineage' && selectedId) loadLineage()
    if (page === 'investigation' && selectedId) loadInvestigation()
  }, [page, selectedId])

  const columnRows = useMemo(() => Object.entries(profile?.data_types ?? {}).map(([name, type]) => ({ name, type, missing: profile?.missing_values?.[name] ?? 0 })), [profile])
  const missingRows = useMemo(() => Object.entries(profile?.missing_values ?? {}).map(([column, count]) => ({ column, count })), [profile])
  const rcaItems = Array.isArray(investigation) ? investigation : (investigation?.findings ?? investigation?.root_causes ?? investigation?.causes ?? [])
  const impactedAssets = impact?.impacted_assets ?? []

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-icon"><Database size={23} /></div><div><h2>DataTrace</h2><span>DATA INTELLIGENCE</span></div></div>
      <nav>{NAV_ITEMS.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${page === id ? 'active' : ''}`} onClick={() => { setPage(id); setError(''); setNotice('') }}><Icon size={18} />{label}<ChevronRight className="nav-chevron" size={15} /></button>)}</nav>
      <div className="sidebar-bottom"><span className="status-dot" /> Backend URL<strong>{API_URL}</strong></div>
    </aside>

    <main className="main-content">
      <header className="topbar"><div><p className="eyebrow">DATATRACE / {pageTitle.toUpperCase()}</p><h1>{page === 'overview' ? 'Data Intelligence Dashboard' : pageTitle}</h1><p className="subtitle">Understand your data, trace issues, and investigate downstream impact.</p></div>
        <div className="dataset-picker"><label htmlFor="dataset-select">Active dataset</label><select id="dataset-select" value={selectedId} onChange={(e) => { setDatasetId(e.target.value); setResult(null); setDatasetFile(null); setLineage(null); setAnomalies([]); setInvestigation(null); setImpact(null) }}><option value="">Select dataset</option>{datasets.map((d) => <option key={d.id} value={d.id}>#{d.id} · {d.filename}</option>)}</select><button className="icon-button" title="Refresh datasets" onClick={() => refreshDatasets()}><RefreshCw size={16} /></button></div>
      </header>

      {error && <div className="alert error-alert"><AlertTriangle size={18} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
      {notice && <div className="alert success-alert"><CheckCircle2 size={18} /><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss notice">×</button></div>}
      {busy && <div className="loading-line"><LoaderCircle size={16} className="spin" /> Working with the backend…</div>}

      
{page === 'overview' && <>
  <section className="source-mode-section">
    <div className="source-mode-heading">
      <h2>Choose your data source</h2>
      <p>Analyze uploaded files or monitor a connected database.</p>
    </div>

    <div className="source-mode-grid">
      <button
        className={`source-mode-card ${sourceMode === 'csv' ? 'selected csv-mode' : ''}`}
        onClick={() => setSourceMode('csv')}
        type="button"
      >
        <div className="source-mode-icon csv-icon">
          <FileSpreadsheet size={25} />
        </div>
        <div className="source-mode-copy">
          <strong>CSV Analysis</strong>
          <span>Upload CSV files and analyze data quality, profiles and anomalies.</span>
          <small>STATIC DATASET ANALYSIS</small>
        </div>
        <span className="mode-indicator">
          {sourceMode === 'csv' ? 'Selected' : 'Select'}
        </span>
      </button>

      <button
        className={`source-mode-card ${sourceMode === 'database' ? 'selected database-mode' : ''}`}
        onClick={() => setSourceMode('database')}
        type="button"
      >
        <div className="source-mode-icon database-icon">
          <Database size={25} />
        </div>
        <div className="source-mode-copy">
          <strong>Live Database</strong>
          <span>Connect PostgreSQL or MySQL and analyze records from database tables.</span>
          <small>DATABASE MONITORING</small>
        </div>
        <span className="mode-indicator">
          {sourceMode === 'database' ? 'Selected' : 'Select'}
        </span>
      </button>
    </div>
  </section>

  <section className="stats-grid">
    <StatCard
      label="Quality score"
      value={quality ? `${quality.quality_score}%` : '—'}
      note={quality?.status ?? 'Select a dataset'}
      icon={ShieldCheck}
    />
    <StatCard
      label="Missing cells"
      value={quality?.missing_cells ?? '—'}
      note="Empty or missing values"
      icon={AlertTriangle}
    />
    <StatCard
      label="Duplicate rows"
      value={quality?.duplicate_rows ?? '—'}
      note="Repeated complete rows"
      icon={Database}
    />
    <StatCard
      label="Rows analyzed"
      value={profile?.row_count ?? '—'}
      note={profile ? `${profile.column_count} columns detected` : 'Dataset size'}
      icon={FileSpreadsheet}
    />
    {sourceMode === 'database' && (
  <StatCard
    label="Anomalies detected"
    value={liveAnomalyCount}
    note="Latest database snapshot"
    icon={AlertTriangle}
  />
)}
  </section>

  <section className="content-grid">
    {sourceMode === 'csv' ? (
      <article className="panel">
        <div className="panel-title">
          <div>
            <h2>Analyze a CSV dataset</h2>
            <p>Upload a CSV file to generate a profile and quality report.</p>
          </div>
          <Upload size={22} />
        </div>

        <form onSubmit={analyzeFile}>
          <label className="upload-zone">
            <Upload size={32} />
            <strong>{file ? file.name : 'Choose a CSV file'}</strong>
            <span>
              {file
                ? `${(file.size / 1024).toFixed(1)} KB selected`
                : 'Browse your computer for a .csv file'}
            </span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null)
                setError('')
              }}
            />
          </label>

          <button
            className="primary-button"
            type="submit"
            disabled={busy}
          >
            {busy ? 'Processing…' : 'Analyze CSV dataset'}
          </button>
        </form>

        {result && (
          <div className="result-summary">
            <CheckCircle2 size={20} />
            <div>
              <strong>Analysis complete</strong>
              <p>Dataset ID: {result.id} · {result.dataset}</p>
            </div>
          </div>
        )}
      </article>
    ) : (
      <article className="panel database-monitor-panel">
        <div className="panel-title">
          <div>
            <h2>Database monitoring</h2>
            <p>Analyze data from your connected database source.</p>
          </div>
          <Database size={22} />
        </div>

        {isDatabaseDataset ? (
          <>
            <div className="database-source-status">
              <span className="status-dot" />
              <strong>Database dataset selected</strong>
            </div>

            <div className="database-source-details">
              <div>
                <span>Selected dataset</span>
                <strong>{selectedDataset?.filename ?? detail?.dataset}</strong>
              </div>
              <div>
                <span>Dataset ID</span>
                <strong>#{selectedId}</strong>
              </div>
              <div>
                <span>Records analyzed</span>
                <strong>{profile?.row_count ?? '—'}</strong>
              </div>
              <div>
                <span>Columns detected</span>
                <strong>{profile?.column_count ?? '—'}</strong>
              </div>
            </div>

            <div className="database-info">
              <Activity size={19} />
              <span>
                Database metrics refresh automatically every 5 seconds.
              </span>
            </div>
            {lastLiveRefresh && (
  <div className="live-refresh-indicator">
    <span className="status-dot" />
    Last dashboard refresh: {lastLiveRefresh.toLocaleTimeString()}
  </div>
)}
          </>
        ) : (
          <EmptyState
            title="No database dataset selected"
            detail="Connect a database, browse its tables and select a table to begin."
          />
        )}

        <button
          className="primary-button database-action"
          type="button"
          onClick={() => setPage('connections')}
        >
          <Database size={16} />
          Open Database Connections
        </button>
      </article>
    )}

    <article className="panel">
      <div className="panel-title">
        <div>
          <h2>Dataset profile</h2>
          <p>Columns and data types in the active dataset.</p>
        </div>
        <FileSpreadsheet size={22} />
      </div>

      {columnRows.length ? (
        <DataTable
          columns={[
            { key: 'name', label: 'Column' },
            { key: 'type', label: 'Data type' },
            { key: 'missing', label: 'Missing' },
          ]}
          rows={columnRows}
        />
      ) : (
        <EmptyState
          title="No dataset selected"
          detail="Upload a CSV or choose a saved database dataset."
        />
      )}
    </article>
  </section>

  {detail && (
    <section className="panel details-panel">
      <div className="panel-title">
        <div>
          <h2>Latest quality report</h2>
          <p>{detail.dataset} · Dataset ID {detail.id}</p>
        </div>
        <span className={`quality-pill ${(quality?.status ?? '').toLowerCase()}`}>
          {quality?.status ?? 'Unknown'}
        </span>
      </div>

      <div className="report-grid">
        <div><span>Rows</span><strong>{profile?.row_count ?? '—'}</strong></div>
        <div><span>Columns</span><strong>{profile?.column_count ?? '—'}</strong></div>
        <div><span>Quality score</span><strong>{quality?.quality_score ?? '—'}/100</strong></div>
        <div><span>Missing cells</span><strong>{quality?.missing_cells ?? '—'}</strong></div>
      </div>

      <h3>Missing values by column</h3>
      <DataTable
        columns={[
          { key: 'column', label: 'Column' },
          { key: 'count', label: 'Missing values' },
        ]}
        rows={missingRows}
        emptyText="No missing-value counts are available."
      />
    </section>
  )}
</>}


      
{page === 'quality' && <section className="panel">
  <div className="panel-title">
    <div>
      <h2>Data Quality Report</h2>
      <p>Saved profile and quality metrics for the active dataset.</p>
    </div>
    <ShieldCheck size={22} />
  </div>

  {!detail ? (
    <EmptyState
      title="Select a dataset"
      detail="Analyze a CSV from Overview or choose a saved dataset."
    />
  ) : (
    <>
      <div className="stats-grid compact-stats">
        <StatCard
          label="Quality score"
          value={`${quality?.quality_score ?? '—'}%`}
          note={quality?.status ?? 'Status unavailable'}
          icon={ShieldCheck}
        />
        <StatCard
          label="Missing cells"
          value={quality?.missing_cells ?? '—'}
          note="Across all columns"
          icon={AlertTriangle}
        />
        <StatCard
          label="Duplicate rows"
          value={quality?.duplicate_rows ?? '—'}
          note="Repeated rows"
          icon={Database}
        />
        <StatCard
          label="Total rows"
          value={profile?.row_count ?? '—'}
          note={`${profile?.column_count ?? 0} columns`}
          icon={BarChart3}
        />
      </div>

      <h3>Column-level quality</h3>
      <DataTable
        columns={[
          { key: 'column', label: 'Column' },
          { key: 'data_type', label: 'Data type' },
          { key: 'missing_count', label: 'Missing values' },
          {
            key: 'missing_percentage',
            label: 'Missing %',
            render: (v) => `${v ?? 0}%`,
          },
          { key: 'unique_count', label: 'Unique values' },
          {
            key: 'constant_column',
            label: 'Constant column',
            render: (v) => v ? 'Yes' : 'No',
          },
        ]}
        rows={columnQualityRows}
        emptyText="No enhanced column profile is saved. Upload the CSV again to generate it."
      />

      <h3 className="spaced-heading">Whitespace issues</h3>
      <DataTable
        columns={[
          { key: 'column', label: 'Column' },
          { key: 'count', label: 'Values with extra whitespace' },
        ]}
        rows={whitespaceIssues}
        emptyText="No leading or trailing whitespace detected."
      />

      <h3 className="spaced-heading">Duplicate column names</h3>
      {duplicateColumnNames.length ? (
        <ul>
          {duplicateColumnNames.map((name, index) => (
            <li key={`${name}-${index}`}>{name}</li>
          ))}
        </ul>
      ) : (
        <p>No duplicate column names detected.</p>
      )}
    </>
  )}
</section>}


      {page === 'anomalies' && <section className="panel"><div className="panel-title"><div><h2>Anomaly Detection</h2><p>Uses your backend IQR detector and stored anomaly findings.</p></div><AlertTriangle size={22} /></div>
        
<form className="detect-form" onSubmit={detectAnomalies}>
  <label className="file-inline">
    <span>CSV file for the active dataset</span>
    <input
      type="file"
      accept=".csv,text/csv"
      onChange={(e) => setDatasetFile(e.target.files?.[0] ?? null)}
    />
  </label>

  <label className="file-inline">
    <span>Anomaly detection method</span>
    <select
      value={anomalyMethod}
      onChange={(e) => setAnomalyMethod(e.target.value)}
      disabled={busy}
    >
      <option value="IQR">Standard IQR</option>
      <option value="LOG_IQR">Log-IQR (for skewed non-negative data)</option>
    </select>
  </label>

  <button
    className="primary-button"
    type="submit"
    disabled={busy || !selectedId}
  >
    {busy ? 'Detecting…' : `Run ${anomalyMethod === 'IQR' ? 'IQR' : 'Log-IQR'} detection`}
  </button>

  <button
    className="secondary-button"
    type="button"
    onClick={loadAnomalies}
    disabled={busy || !selectedId}
  >
    Load saved findings
  </button>
</form>
        <div className="section-summary"><strong>{anomalies.length}</strong><span>stored anomaly findings</span></div>
        <DataTable columns={[{ key: 'column_name', label: 'Column' }, { key: 'row_index', label: 'Row index' }, { key: 'observed_value', label: 'Observed value' }, { key: 'lower_bound', label: 'Lower bound' }, { key: 'upper_bound', label: 'Upper bound' }, { key: 'direction', label: 'Direction' }, { key: 'severity', label: 'Severity', render: (v) => <span className={`severity ${String(v ?? '').toLowerCase()}`}>{v ?? '—'}</span> }]} rows={anomalies} emptyText="No saved anomalies. Select the matching CSV and run IQR detection." />
      </section>}

      {page === 'lineage' && <section className="panel"><div className="panel-title"><div><h2>Data Lineage</h2><p>Inspect PostgreSQL lineage nodes and relationships; optionally sync them to Neo4j.</p></div><Workflow size={22} /></div>
        <div className="action-row"><button className="primary-button" onClick={createLineage} disabled={busy || !selectedId}>Create / refresh lineage</button><button className="secondary-button" onClick={loadLineage} disabled={busy || !selectedId}>Load lineage</button><button className="secondary-button" onClick={syncLineage} disabled={busy || !selectedId}>Sync to Neo4j</button></div>
        {lineage && <><div className="stats-grid compact-stats"><StatCard label="Nodes" value={lineage.nodes?.length ?? 0} note="Lineage entities" icon={Database} /><StatCard label="Relationships" value={lineage.edges?.length ?? 0} note="Directed connections" icon={GitBranch} /></div><h3>Lineage nodes</h3><DataTable columns={[{ key: 'name', label: 'Name' }, { key: 'type', label: 'Type' }, { key: 'properties', label: 'Properties', render: (v) => <code className="json-cell">{JSON.stringify(v ?? {})}</code> }]} rows={lineage.nodes ?? []} emptyText="No lineage nodes yet. Create lineage first." /><h3 className="spaced-heading">Relationships</h3><DataTable columns={[{ key: 'source', label: 'Source node ID' }, { key: 'relationship', label: 'Relationship' }, { key: 'target', label: 'Target node ID' }]} rows={lineage.edges ?? []} emptyText="No lineage relationships yet." /></>}
        {!lineage && <EmptyState title="No lineage loaded" detail="Choose a dataset, then create or load its lineage." />}
      </section>}

      {page === 'investigation' && <>
        <section className="panel"><div className="panel-title"><div><h2>Root Cause Analysis</h2><p>Rule-based analysis from Phase 6; it uses saved anomaly records.</p></div><Search size={22} /></div>
          <div className="action-row"><button className="primary-button" onClick={loadInvestigation} disabled={busy || !selectedId}>Refresh investigation</button><button className="secondary-button" onClick={() => setPage('anomalies')}>Open anomalies</button></div>
          {investigation?.error ? <div className="alert error-alert">{investigation.error}</div> : rcaItems.length ? <DataTable columns={[{ key: 'title', label: 'Finding', render: (v, row) => v ?? row.cause ?? row.rule ?? row.message ?? 'Root cause finding' }, { key: 'severity', label: 'Severity', render: (v) => v ? <span className={`severity ${String(v).toLowerCase()}`}>{v}</span> : '—' }, { key: 'description', label: 'Details', render: (v, row) => v ?? row.explanation ?? row.recommendation ?? row.action ?? '—' }]} rows={rcaItems} emptyText="No root-cause findings were returned. Run anomaly detection first." /> : <EmptyState title="Investigation not loaded" detail="Select a dataset and refresh investigation. Run anomaly detection first for meaningful RCA." />}
        </section>
        <section className="panel details-panel"><div className="panel-title"><div><h2>Downstream Impact</h2><p>Impacted lineage assets returned by Neo4j.</p></div><ArrowDownRight size={22} /></div>
          {impact?.error ? <div className="alert error-alert">{impact.error} Make sure Neo4j is running and lineage has been synced.</div> : <><div className="section-summary"><strong>{impact?.impacted_asset_count ?? impactedAssets.length}</strong><span>impacted assets</span></div><DataTable columns={[{ key: 'name', label: 'Asset' }, { key: 'type', label: 'Type' }, { key: 'path_relationships', label: 'Path', render: (v) => Array.isArray(v) ? v.join(' → ') : '—' }]} rows={impactedAssets} emptyText="No downstream impact returned. Create lineage and sync it to Neo4j first." /></>}
        </section>
      </>}
      
      {page === 'connections' && <DatabaseConnections />}
      <footer>DataTrace AI · Data quality, anomaly detection, lineage, and investigation</footer>
    </main>
  </div>
}

export default App
