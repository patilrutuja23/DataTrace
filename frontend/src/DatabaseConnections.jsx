
import { useEffect, useState } from 'react'
import axios from 'axios'
import { Database, RefreshCw, ShieldCheck } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const api = axios.create({ baseURL: API_URL, timeout: 30000 })

const emptyForm = {
  name: '',
  db_type: 'postgresql',
  host: 'localhost',
  port: '5432',
  database_name: '',
  username: '',
  password: '',
}

function messageFrom(error) {
  return error?.response?.data?.detail
    || 'Request failed. Check the backend and connection settings.'
}

export default function DatabaseConnections() {
  const [form, setForm] = useState(emptyForm)
  const [sources, setSources] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState('')
  const [selectedSchema, setSelectedSchema] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  function updateField(event) {
    const { name, value } = event.target
    setForm((previous) => {
      const next = { ...previous, [name]: value }
      if (name === 'db_type') {
        next.port = value === 'postgresql' ? '5432' : '3306'
      }
      return next
    })
  }

  async function loadSources() {
    try {
      const response = await api.get('/api/sources')
      setSources(response.data ?? [])
    } catch (err) {
      setError(messageFrom(err))
    }
  }

  useEffect(() => {
    loadSources()
  }, [])

  async function testConnection(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await api.post('/api/sources/test-connection', {
        ...form,
        port: Number(form.port),
      })
      setNotice('Connection test successful.')
    } catch (err) {
      setError(messageFrom(err))
    } finally {
      setBusy(false)
    }
  }

  async function saveSource() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const response = await api.post('/api/sources', {
        ...form,
        port: Number(form.port),
      })
      setNotice(`Source "${response.data.name}" saved successfully.`)
      setForm(emptyForm)
      setTables([])
      setSelectedTable('')
      setSelectedSchema('')
      setSelectedId(String(response.data.id))
      await loadSources()
    } catch (err) {
      setError(messageFrom(err))
    } finally {
      setBusy(false)
    }
  }

  async function loadTables() {
    if (!selectedId) {
      setError('Select a saved database source first.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    setTables([])
    try {
      const response = await api.get(`/api/sources/${selectedId}/tables`)
      setTables(response.data.tables ?? [])
      setNotice(`Loaded ${response.data.tables?.length ?? 0} tables.`)
    } catch (err) {
      setError(messageFrom(err))
    } finally {
      setBusy(false)
    }
  }

  async function saveSelectedTable() {
    if (!selectedId || !selectedTable) {
      setError('Select a source and a table first.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await api.post(`/api/sources/${selectedId}/select-table`, {
        schema_name: selectedSchema || null,
        table_name: selectedTable,
      })
      setNotice(`Selected table: ${selectedSchema ? `${selectedSchema}.` : ''}${selectedTable}`)
      await loadSources()
    } catch (err) {
      setError(messageFrom(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <div className="panel-title">
        <div>
          <h2>Database Connections</h2>
          <p>Connect PostgreSQL or MySQL and choose a table to monitor.</p>
        </div>
        <Database size={22} />
      </div>

      {error && <div className="alert error-alert">{error}</div>}
      {notice && <div className="alert success-alert">{notice}</div>}

      <h3>New database source</h3>
      <form className="detect-form" onSubmit={testConnection}>
        <label className="file-inline">
          Source name
          <input name="name" value={form.name} onChange={updateField} required maxLength={255} />
        </label>

        <label className="file-inline">
          Database type
          <select name="db_type" value={form.db_type} onChange={updateField}>
            <option value="postgresql">PostgreSQL</option>
            <option value="mysql">MySQL</option>
          </select>
        </label>

        <label className="file-inline">
          Host
          <input name="host" value={form.host} onChange={updateField} required />
        </label>

        <label className="file-inline">
          Port
          <input name="port" type="number" min="1" max="65535" value={form.port} onChange={updateField} required />
        </label>

        <label className="file-inline">
          Database name
          <input name="database_name" value={form.database_name} onChange={updateField} required />
        </label>

        <label className="file-inline">
          Username
          <input name="username" value={form.username} onChange={updateField} required />
        </label>

        <label className="file-inline">
          Password
          <input name="password" type="password" value={form.password} onChange={updateField} required autoComplete="new-password" />
        </label>

        <button className="primary-button" type="submit" disabled={busy}>
          {busy ? 'Working…' : 'Test connection'}
        </button>
      </form>

      <button
        className="primary-button"
        type="button"
        onClick={saveSource}
        disabled={busy || !form.name.trim() || !form.host.trim()
          || !form.database_name.trim() || !form.username.trim() || !form.password}
      >
        Save source
      </button>

      <div className="panel-title" style={{ marginTop: 28 }}>
        <div>
          <h2>Saved sources</h2>
          <p>Credentials are never displayed in this list.</p>
        </div>
        <button className="icon-button" type="button" onClick={loadSources} title="Refresh sources">
          <RefreshCw size={16} />
        </button>
      </div>

      {sources.length === 0 ? (
        <p>No database sources saved yet.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Database</th>
                <th>Selected table</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>
                    <label>
                      <input
                        type="radio"
                        name="source"
                        checked={selectedId === String(source.id)}
                        onChange={() => {
                          setSelectedId(String(source.id))
                          setTables([])
                          setSelectedTable('')
                          setSelectedSchema('')
                        }}
                      />
                      {' '}{source.name}
                    </label>
                  </td>
                  <td>{source.db_type}</td>
                  <td>{source.database_name}</td>
                  <td>
                    {source.selected_table
                      ? `${source.selected_schema ? `${source.selected_schema}.` : ''}${source.selected_table}`
                      : 'Not selected'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="action-row" style={{ marginTop: 16 }}>
        <button className="secondary-button" onClick={loadTables} disabled={busy || !selectedId}>
          Browse tables
        </button>
      </div>

      {tables.length > 0 && (
        <>
          <h3>Available tables</h3>
          <label className="file-inline">
            Choose table
            <select
              value={selectedTable}
              onChange={(event) => {
                const table = tables.find((item) => item.table_name === event.target.value)
                setSelectedTable(event.target.value)
                setSelectedSchema(table?.schema ?? '')
              }}
            >
              <option value="">Select a table</option>
              {tables.map((table) => (
                <option key={`${table.schema}.${table.table_name}`} value={table.table_name}>
                  {table.schema}.{table.table_name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="primary-button"
            style={{ marginTop: 12 }}
            onClick={saveSelectedTable}
            disabled={busy || !selectedTable}
          >
            Save selected table
          </button>
        </>
      )}

      <p style={{ marginTop: 20, color: '#78849a', fontSize: 12 }}>
        <ShieldCheck size={14} style={{ verticalAlign: 'middle' }} /> Connection credentials are encrypted at rest.
      </p>
    </section>
  )
}
