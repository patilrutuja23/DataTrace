
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Bot,
  Send,
  UserRound,
  Trash2,
  Sparkles,
} from 'lucide-react'

const API_URL =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

const SUGGESTED_QUESTIONS = [
  'Summarize the data quality of this dataset.',
  'What are the most important anomalies?',
  'Explain the possible root causes of these issues.',
  'What is the status of the recent pipeline executions?',
]

export default function AskDataTrace({ datasetId, datasetName }) {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const askQuestion = async (text = question) => {
    const trimmedQuestion = text.trim()

    if (!trimmedQuestion || loading) return

    if (!datasetId) {
      setError('Please select a dataset before asking a question.')
      return
    }

    setMessages((previous) => [
      ...previous,
      { role: 'user', content: trimmedQuestion },
    ])

    setQuestion('')
    setError('')
    setLoading(true)

    try {
      const response = await fetch(
        `${API_URL}/api/datasets/${datasetId}/ask`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: trimmedQuestion,
          }),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(
          data.detail || 'Unable to get an answer. Please try again.'
        )
      }

      setMessages((previous) => [
        ...previous,
        { role: 'assistant', content: data.answer },
      ])
    } catch (err) {
      setError(
        err.message || 'Ask DataTrace is temporarily unavailable.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    askQuestion()
  }

  const clearChat = () => {
    if (loading) return
    setMessages([])
    setError('')
  }

  return (
    <div className="ask-page">
      <div className="ask-header">
        <div>
          <div className="ask-title">
            <Bot size={25} />
            <h2>Ask DataTrace</h2>
          </div>

          <p>
            Ask questions about your dataset, data quality, anomalies,
            root causes, and pipeline executions.
          </p>

          <span className="ask-dataset">
            Dataset: {datasetName || 'No dataset selected'}
          </span>
        </div>

        <button
          className="ask-clear-button"
          onClick={clearChat}
          disabled={loading || messages.length === 0}
          type="button"
        >
          <Trash2 size={16} />
          Clear chat
        </button>
      </div>

      <div className="ask-chat-container">
        {messages.length === 0 ? (
          <div className="ask-welcome">
            <div className="ask-welcome-icon">
              <Sparkles size={30} />
            </div>

            <h3>How can I help you?</h3>

            <p>
              I can analyze your DataTrace results and explain the
              findings using your selected dataset's information.
            </p>

            <div className="ask-suggestions">
              {SUGGESTED_QUESTIONS.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => askQuestion(item)}
                  disabled={loading || !datasetId}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="ask-messages">
            {messages.map((message, index) => (
              <div
                className={`ask-message ${
                  message.role === 'user'
                    ? 'ask-user-message'
                    : 'ask-assistant-message'
                }`}
                key={index}
              >
                <div className="ask-message-icon">
                  {message.role === 'user' ? (
                    <UserRound size={18} />
                  ) : (
                    <Bot size={18} />
                  )}
                </div>

                <div className="ask-message-content">
                  <strong>
                    {message.role === 'user' ? 'You' : 'DataTrace AI'}
                  </strong>

                  {message.role === 'assistant' ? (
                    <div className="ask-markdown">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        skipHtml
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p>{message.content}</p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="ask-message ask-assistant-message">
                <div className="ask-message-icon">
                  <Bot size={18} />
                </div>

                <div className="ask-message-content">
                  <strong>DataTrace AI</strong>
                  <p className="ask-thinking">
                    Analyzing your dataset and preparing an answer...
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="ask-error">
            {error}
          </div>
        )}
      </div>

      <form className="ask-input-area" onSubmit={handleSubmit}>
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask something about your dataset..."
          disabled={loading || !datasetId}
        />

        <button
          type="submit"
          disabled={loading || !question.trim() || !datasetId}
          aria-label="Send question"
        >
          <Send size={18} />
          Send
        </button>
      </form>

      <p className="ask-disclaimer">
        AI-generated answers are based on available DataTrace evidence.
        Possible root causes should be verified before taking action.
      </p>
    </div>
  )
}
