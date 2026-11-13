// Types mirror backend/app/schemas.py (plus the upload payload in routes/documents.py); StreamCallbacks is frontend-only.

/**
 * @typedef {Object} DocumentOut
 * @property {number} id
 * @property {string} filename
 * @property {string} content_type
 * @property {number} size_bytes
 * @property {number} char_count
 * @property {number} chunk_count
 * @property {string} created_at
 */

/**
 * @typedef {Object} ChatOut
 * @property {number} id
 * @property {string} title
 * @property {string} created_at
 * @property {string} updated_at
 * @property {number} message_count
 */

/**
 * @typedef {Object} SourceOut
 * @property {number} chunk_id
 * @property {number} document_id
 * @property {string} filename
 * @property {number} idx
 * @property {string} snippet
 * @property {number} score
 */

/** @typedef {'documents' | 'general'} MessageMode */

/**
 * @typedef {Object} MessageOut
 * @property {number} id
 * @property {'user' | 'assistant'} role
 * @property {string} content
 * @property {string} created_at
 * @property {SourceOut[]} sources
 * @property {(MessageMode | null)} mode
 */

/**
 * @typedef {Object} UploadError
 * @property {string} filename
 * @property {string} error
 */

/**
 * @typedef {Object} UploadResult
 * @property {DocumentOut[]} documents
 * @property {UploadError[]} errors
 */

/**
 * @typedef {Object} StreamCallbacks
 * @property {(sources: SourceOut[]) => void} onSources
 * @property {(text: string) => void} onToken
 * @property {(messageId: number) => void} onDone
 * @property {(message: string) => void} onError
 */

/**
 * @param {string} path
 * @param {RequestInit} [init]
 * @returns {Promise<any>}
 */
async function request(path, init) {
  const res = await fetch(path, init)
  if (!res.ok) throw new Error((await res.text()) || `Request failed: ${res.status}`)
  if (res.status === 204) return undefined
  return await res.json()
}

/**
 * @returns {Promise<DocumentOut[]>}
 */
export async function listDocuments() {
  return request('/api/documents')
}

/**
 * @param {File[]} files
 * @returns {Promise<UploadResult>}
 */
export async function uploadFiles(files) {
  const form = new FormData()
  for (const file of files) form.append('files', file)
  const res = await fetch('/api/documents', { method: 'POST', body: form })
  if (!res.ok) throw new Error((await res.text()) || `Upload failed: ${res.status}`)
  return await res.json()
}

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export async function deleteDocument(id) {
  await request(`/api/documents/${id}`, { method: 'DELETE' })
}

/**
 * @returns {Promise<ChatOut[]>}
 */
export async function listChats() {
  return request('/api/chats')
}

/**
 * @param {string} [title]
 * @returns {Promise<ChatOut>}
 */
export async function createChat(title) {
  return request('/api/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(title === undefined ? {} : { title }),
  })
}

/**
 * @param {number} id
 * @returns {Promise<void>}
 */
export async function deleteChat(id) {
  await request(`/api/chats/${id}`, { method: 'DELETE' })
}

/**
 * @param {number} chatId
 * @returns {Promise<MessageOut[]>}
 */
export async function getMessages(chatId) {
  return request(`/api/chats/${chatId}/messages`)
}

// Reads the SSE stream from POST /api/chats/{id}/messages. Events arrive as
// `event: <name>` + `data: <json>` pairs separated by blank lines. The buffer
// is kept across chunks so an event split over two reads still parses.
/**
 * @param {number} chatId
 * @param {string} content
 * @param {StreamCallbacks} on
 * @returns {Promise<void>}
 */
export function streamMessage(chatId, content, on) {
  return (async () => {
    const res = await fetch(`/api/chats/${chatId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!res.ok) throw new Error((await res.text()) || `Request failed: ${res.status}`)
    if (!res.body) throw new Error('Empty response body')

    const dispatch = (rawEvent) => {
      let event = ''
      const dataLines = []
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
      }
      if (!event || dataLines.length === 0) return
      let payload
      try {
        payload = JSON.parse(dataLines.join('\n'))
      } catch {
        on.onError('Could not parse the server response.')
        return
      }
      if (event === 'sources') on.onSources(payload.sources ?? [])
      else if (event === 'token') on.onToken(String(payload.text ?? ''))
      else if (event === 'done') on.onDone(payload.message_id)
      else if (event === 'error') on.onError(String(payload.message ?? 'Unknown error'))
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const raw = buffer.slice(0, idx)
        buffer = buffer.slice(idx + 2)
        dispatch(raw)
      }
    }
    buffer += decoder.decode()
    if (buffer.trim()) dispatch(buffer)
  })()
}
