// Types mirror backend/app/schemas.py exactly: same names, same fields.
export type DocumentOut = {
  id: number
  filename: string
  content_type: string
  size_bytes: number
  char_count: number
  chunk_count: number
  created_at: string
}

export type ChatOut = {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export type SourceOut = {
  chunk_id: number
  document_id: number
  filename: string
  idx: number
  snippet: string
  score: number
}

export type MessageOut = {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
  sources: SourceOut[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) throw new Error((await res.text()) || `Request failed: ${res.status}`)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export async function listDocuments(): Promise<DocumentOut[]> {
  return request<DocumentOut[]>('/api/documents')
}

export async function uploadFiles(
  files: File[],
): Promise<{ documents: DocumentOut[]; errors: { filename: string; error: string }[] }> {
  const form = new FormData()
  for (const file of files) form.append('files', file)
  const res = await fetch('/api/documents', { method: 'POST', body: form })
  if (!res.ok) throw new Error((await res.text()) || `Upload failed: ${res.status}`)
  return (await res.json()) as {
    documents: DocumentOut[]
    errors: { filename: string; error: string }[]
  }
}

export async function deleteDocument(id: number): Promise<void> {
  await request<void>(`/api/documents/${id}`, { method: 'DELETE' })
}

export async function listChats(): Promise<ChatOut[]> {
  return request<ChatOut[]>('/api/chats')
}

export async function createChat(title?: string): Promise<ChatOut> {
  return request<ChatOut>('/api/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(title === undefined ? {} : { title }),
  })
}

export async function deleteChat(id: number): Promise<void> {
  await request<void>(`/api/chats/${id}`, { method: 'DELETE' })
}

export async function getMessages(chatId: number): Promise<MessageOut[]> {
  return request<MessageOut[]>(`/api/chats/${chatId}/messages`)
}

type StreamCallbacks = {
  onSources(sources: SourceOut[]): void
  onToken(text: string): void
  onDone(messageId: number): void
  onError(message: string): void
}

// Reads the SSE stream from POST /api/chats/{id}/messages. Events arrive as
// `event: <name>` + `data: <json>` pairs separated by blank lines. The buffer
// is kept across chunks so an event split over two reads still parses.
export function streamMessage(
  chatId: number,
  content: string,
  on: StreamCallbacks,
): Promise<void> {
  return (async () => {
    const res = await fetch(`/api/chats/${chatId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!res.ok) throw new Error((await res.text()) || `Request failed: ${res.status}`)
    if (!res.body) throw new Error('Empty response body')

    const dispatch = (rawEvent: string) => {
      let event = ''
      const dataLines: string[] = []
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''))
      }
      if (!event || dataLines.length === 0) return
      let payload: Record<string, unknown>
      try {
        payload = JSON.parse(dataLines.join('\n')) as Record<string, unknown>
      } catch {
        on.onError('Could not parse the server response.')
        return
      }
      if (event === 'sources') on.onSources((payload.sources ?? []) as SourceOut[])
      else if (event === 'token') on.onToken(String(payload.text ?? ''))
      else if (event === 'done') on.onDone(payload.message_id as number)
      else if (event === 'error') on.onError(String(payload.message ?? 'Unknown error'))
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let idx: number
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
