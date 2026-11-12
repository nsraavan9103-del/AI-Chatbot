import { useState } from 'react'
import { deleteChat, deleteDocument, listDocuments, type ChatOut, type DocumentOut } from '../api'
import UploadButton from './UploadButton'

type Props = {
  chats: ChatOut[]
  activeChatId: number | null
  documents: DocumentOut[]
  onSelectChat: (id: number) => void
  onNewChat: () => void
  onChatsChange: (chats: ChatOut[]) => void
  onDocumentsChange: (documents: DocumentOut[]) => void
}

export default function Sidebar({
  chats,
  activeChatId,
  documents,
  onSelectChat,
  onNewChat,
  onChatsChange,
  onDocumentsChange,
}: Props) {
  const [uploadErrors, setUploadErrors] = useState<{ filename: string; error: string }[]>([])
  const [docError, setDocError] = useState<string | null>(null)
  const [chatError, setChatError] = useState<string | null>(null)

  const refreshDocuments = async () => {
    try {
      onDocumentsChange(await listDocuments())
    } catch {
      setDocError('Could not refresh the document list.')
    }
  }

  const handleDeleteChat = async (id: number) => {
    const remaining = chats.filter((c) => c.id !== id)
    setChatError(null)
    try {
      await deleteChat(id)
      onChatsChange(remaining)
      if (id === activeChatId && remaining.length > 0) onSelectChat(remaining[0].id)
    } catch {
      setChatError('Could not delete that chat.')
    }
  }

  const handleDeleteDocument = async (doc: DocumentOut) => {
    if (!window.confirm(`Delete "${doc.filename}" and its ${doc.chunk_count} chunks?`)) return
    setDocError(null)
    try {
      await deleteDocument(doc.id)
      onDocumentsChange(documents.filter((d) => d.id !== doc.id))
    } catch {
      setDocError(`Could not delete "${doc.filename}".`)
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <span className="brand">Research Chat</span>
        <button type="button" className="new-chat-btn" onClick={onNewChat}>
          New chat
        </button>
      </div>

      <nav className="chat-list" aria-label="Chats">
        {chatError && <p className="inline-error" role="alert">{chatError}</p>}
        {chats.length === 0 && <p className="muted">No chats yet.</p>}
        {chats.map((chat) => (
          <div
            key={chat.id}
            className={chat.id === activeChatId ? 'chat-item active' : 'chat-item'}
          >
            <button
              type="button"
              className="chat-title"
              onClick={() => onSelectChat(chat.id)}
              aria-current={chat.id === activeChatId ? 'true' : undefined}
            >
              {chat.title}
            </button>
            <button
              type="button"
              className="icon-btn"
              aria-label={`Delete chat "${chat.title}"`}
              onClick={() => void handleDeleteChat(chat.id)}
            >
              ×
            </button>
          </div>
        ))}
      </nav>

      <section className="docs-section" aria-label="Documents">
        <div className="docs-header">
          <h2>Documents</h2>
          <UploadButton
            onUploaded={() => void refreshDocuments()}
            onErrors={setUploadErrors}
          />
        </div>
        {docError && <p className="inline-error" role="alert">{docError}</p>}
        {uploadErrors.length > 0 && (
          <div className="upload-errors" role="alert">
            <ul>
              {uploadErrors.map((e) => (
                <li key={e.filename}>{e.filename}: {e.error}</li>
              ))}
            </ul>
            <button type="button" className="link-btn" onClick={() => setUploadErrors([])}>
              Dismiss
            </button>
          </div>
        )}
        {documents.length === 0 ? (
          <p className="muted">No documents yet. Upload a PDF, DOCX, TXT or MD file.</p>
        ) : (
          <ul className="doc-list">
            {documents.map((doc) => (
              <li key={doc.id} className="doc-row">
                <span className="doc-name" title={doc.filename}>
                  {doc.filename}
                  <span className="doc-meta"> · {doc.chunk_count} chunks</span>
                </span>
                <button
                  type="button"
                  className="icon-btn"
                  aria-label={`Delete document "${doc.filename}"`}
                  onClick={() => void handleDeleteDocument(doc)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </aside>
  )
}
