import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { getBriefing, sendChatMessage } from '../../api/client'

export default function ChatPanel() {
  const [briefing, setBriefing]   = useState(null)
  const [messages, setMessages]   = useState([])
  const [input, setInput]         = useState('')
  const [view, setView]           = useState('briefing') // 'briefing' | 'chat'
  const messagesEndRef             = useRef(null)

  const briefingMut = useMutation({
    mutationFn: getBriefing,
    onSuccess: (data) => {
      if (data.briefing) setBriefing(data.briefing)
      else if (data.error) setBriefing(`Error: ${data.error}`)
    },
  })

  const chatMut = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (data) => {
      if (data.reply) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply }])
      } else if (data.error) {
        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.error}` }])
      }
    },
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const text = input.trim()
    if (!text || chatMut.isPending) return
    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    chatMut.mutate([...messages, userMsg])
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-panel">
      {/* Tab bar */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <button
          className="stream-tab"
          style={view === 'briefing' ? { background: 'var(--ac-light)', color: 'var(--ac)', borderColor: 'var(--ac-mid)' } : {}}
          onClick={() => setView('briefing')}
        >
          Situation Briefing
        </button>
        <button
          className="stream-tab"
          style={view === 'chat' ? { background: 'var(--ac-light)', color: 'var(--ac)', borderColor: 'var(--ac-mid)' } : {}}
          onClick={() => setView('chat')}
        >
          Ask the Data
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
          {view === 'briefing' && (
            <button
              className="briefing-btn"
              onClick={() => briefingMut.mutate()}
              disabled={briefingMut.isPending}
            >
              {briefingMut.isPending ? 'Generating…' : 'Generate Briefing'}
            </button>
          )}
          {view === 'chat' && messages.length > 0 && (
            <button
              className="briefing-btn"
              onClick={() => setMessages([])}
              style={{ color: 'var(--tx-faint)', background: 'transparent', border: '1px solid var(--border)' }}
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Briefing view */}
      {view === 'briefing' && (
        briefing
          ? <div className="chat-briefing">{briefing}</div>
          : (
            <div className="briefing-placeholder">
              {briefingMut.isPending
                ? 'Analyzing surveillance data…'
                : 'Click "Generate Briefing" for an AI-synthesized situation report across all streams.'
              }
            </div>
          )
      )}

      {/* Chat view */}
      {view === 'chat' && (
        <>
          <div className="chat-messages">
            {messages.length === 0 && (
              <div className="briefing-placeholder" style={{ padding: '1rem' }}>
                Ask questions like "Which variants are rising?", "Any concordant signals across streams?", or "What's the NWSS trend?"
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`chat-msg ${m.role}`}>
                {m.content}
              </div>
            ))}
            {chatMut.isPending && (
              <div className="chat-msg assistant" style={{ color: 'var(--tx-faint)' }}>
                Analyzing…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className="chat-input-row">
            <input
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about the surveillance data…"
              disabled={chatMut.isPending}
            />
            <button
              className="chat-send-btn"
              onClick={handleSend}
              disabled={!input.trim() || chatMut.isPending}
            >
              Send
            </button>
          </div>
        </>
      )}
    </div>
  )
}
