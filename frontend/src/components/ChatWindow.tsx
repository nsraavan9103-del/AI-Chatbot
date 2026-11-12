import { useEffect, useRef, useState } from 'react'
import { getMessages, streamMessage, type MessageOut, type SourceOut } from '../api'
import MessageBubble from './MessageBubble'

type Props = {
  chatId: number | null
  chatTitle: string
  onChatUpdated: () => void
}

export default function ChatWindow({ chatId, chatTitle, onChatUpdated }: Props) {
  const [messages, setMessages] = useState<MessageOut[]>([])
  // Fresh per chat: App remounts this component via key={chatId} on every
  // chat switch, so the initial loading/error values are always correct and
  // the fetch effect below never needs synchronous setState calls.
  const [loading, setLoading] = useState(true)
  const [streaming, setStreaming] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const listRef = useRef<HTMLDivElement>(null)
  const nextTempId = useRef(-1)

  useEffect(() => {
    if (chatId === null) return
    let cancelled = false
    getMessages(chatId)
      .then((loaded) => {
        if (!cancelled) setMessages(loaded)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load messages.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [chatId])

  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, streaming])

  const send = () => {
    const content = draft.trim()
    if (!content || chatId === null || streaming) return
    setDraft('')
    setError(null)
    setAnnouncement('')
    const userId = nextTempId.current--
    const assistantId = nextTempId.current--
    const now = new Date().toISOString()
    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', content, created_at: now, sources: [], mode: null },
      { id: assistantId, role: 'assistant', content: '', created_at: now, sources: [], mode: null },
    ])
    setStreaming(true)

    const patchAssistant = (fn: (m: MessageOut) => MessageOut) =>
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? fn(m) : m)))

    const failSend = (message: string) => {
      const text = message || 'Something went wrong.'
      patchAssistant((m) => ({ ...m, content: text }))
      setError(text)
      setAnnouncement('Sending failed.')
    }

    void (async () => {
      // Tracks whether the stream reached a terminal event. If the
      // connection drops or the body is truncated, streamMessage resolves
      // without any callback firing, so the finally block below recovers.
      let settled = false
      try {
        await streamMessage(chatId, content, {
          onSources: (sources: SourceOut[]) =>
            patchAssistant((m) => ({ ...m, sources })),
          onToken: (text: string) =>
            patchAssistant((m) => ({ ...m, content: m.content + text })),
          onDone: () => {
            settled = true
            onChatUpdated()
            setAnnouncement('Answer complete.')
            // Reload so the placeholder picks up the persisted id and sources.
            getMessages(chatId)
              .then(setMessages)
              .catch(() => {
                // Keep the streamed text if the reload fails.
              })
          },
          onError: (message: string) => {
            settled = true
            failSend(message)
          },
        })
      } catch (err: unknown) {
        settled = true
        failSend(err instanceof Error ? err.message : 'Something went wrong.')
      } finally {
        if (!settled) {
          patchAssistant((m) => ({
            ...m,
            content: m.content ? m.content : 'The answer stopped early — try again.',
          }))
          setError('The answer stopped early — try again.')
          setAnnouncement('Sending failed.')
        }
        setStreaming(false)
      }
    })()
  }

  return (
    <main className="chat-pane">
      <header className="chat-header">
        <h1>{chatTitle}</h1>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          <button type="button" className="link-btn" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      )}

      <div className="message-list" ref={listRef}>
        <span className="visually-hidden" role="status">{announcement}</span>
        {chatId === null && (
          <p className="muted centre">Create or select a chat to start.</p>
        )}
        {chatId !== null && loading && <p className="muted centre">Loading messages…</p>}
        {chatId !== null && !loading && messages.length === 0 && (
          <p className="muted centre">No messages yet. Ask anything — about your documents or anything else.</p>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
      </div>

      <div className="composer">
        <textarea
          value={draft}
          rows={3}
          placeholder={streaming ? 'Waiting for the answer…' : 'Ask a question… (Enter to send, Shift+Enter for a new line)'}
          disabled={streaming || chatId === null}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
          aria-label="Message"
        />
        <button
          type="button"
          className="send-btn"
          disabled={streaming || chatId === null || draft.trim() === ''}
          onClick={send}
        >
          {streaming ? 'Sending…' : 'Send'}
        </button>
      </div>
    </main>
  )
}
