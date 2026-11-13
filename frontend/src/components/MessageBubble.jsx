import Sources from './Sources'

export default function MessageBubble({ message }) {
  if (message.role === 'user') {
    return (
      <div className="message-row user">
        <div className="bubble">{message.content}</div>
      </div>
    )
  }
  const content = message.content
    .replace(/【(\d+)】/g, '[$1]')
    .replace(/［(\d+)］/g, '[$1]')
  return (
    <div className="message-row assistant">
      <div className="answer">
        <p>{content}</p>
        {message.mode != null && (
          <span className="mode-badge">
            {message.mode === 'documents' ? 'From your documents' : 'General knowledge'}
          </span>
        )}
        {message.mode !== 'general' && <Sources sources={message.sources} />}
      </div>
    </div>
  )
}
