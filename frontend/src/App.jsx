import { useCallback, useEffect, useState } from 'react'
import { createChat, listChats, listDocuments } from './api'
import ChatWindow from './components/ChatWindow'
import Sidebar from './components/Sidebar'

export default function App() {
  const [chats, setChats] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [documents, setDocuments] = useState([])
  const [bootError, setBootError] = useState(null)
  const [actionError, setActionError] = useState(null)

  // Derive the active id so deleting the selected chat can never strand us.
  const activeChatId = chats.some((c) => c.id === selectedId) ? selectedId : (chats[0]?.id ?? null)
  const activeChat = chats.find((c) => c.id === activeChatId)

  // StrictMode runs the effect twice in dev; the cancelled flag discards the first run.
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [docs, chatList] = await Promise.all([listDocuments(), listChats()])
        if (cancelled) return
        setDocuments(docs)
        if (chatList.length === 0) {
          const created = await createChat()
          if (cancelled) return
          setChats([created])
          setSelectedId(created.id)
        } else {
          setChats(chatList)
          setSelectedId(chatList[0].id)
        }
      } catch (err) {
        if (!cancelled) {
          setBootError(
            err instanceof Error ? err.message : 'Could not reach the server. Is the backend running?',
          )
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const refreshChats = useCallback(async () => {
    try {
      setChats(await listChats())
    } catch {
      // Keep the stale list; the chat itself already updated.
    }
  }, [])

  const handleNewChat = async () => {
    try {
      const created = await createChat()
      setActionError(null)
      setChats((prev) => [created, ...prev])
      setSelectedId(created.id)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Could not create a chat.')
    }
  }

  if (bootError && chats.length === 0) {
    return (
      <div className="app boot-error" role="alert">
        <h1>Research Chat</h1>
        <p>Could not reach the API: {bootError}</p>
        <p className="muted">Start the backend on port 8000, then reload this page.</p>
      </div>
    )
  }

  return (
    <div className="app">
      {actionError && (
        <div className="app-banner" role="alert">
          <span>{actionError}</span>
          <button type="button" className="link-btn" onClick={() => setActionError(null)}>
            Dismiss
          </button>
        </div>
      )}
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        documents={documents}
        onSelectChat={setSelectedId}
        onNewChat={() => void handleNewChat()}
        onChatsChange={setChats}
        onDocumentsChange={setDocuments}
      />
      <ChatWindow
        key={activeChatId ?? 'none'}
        chatId={activeChatId}
        chatTitle={activeChat?.title ?? 'Research Chat'}
        onChatUpdated={() => void refreshChats()}
      />
    </div>
  )
}
