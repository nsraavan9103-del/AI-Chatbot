import type { MessageOut } from '../api'
import Sources from './Sources'

export default function MessageBubble({ message }: { message: MessageOut }) {
  if (message.role === 'user') {
    return (
      <div className="message-row user">
        <div className="bubble">{message.content}</div>
      </div>
    )
  }
  return (
    <div className="message-row assistant">
      <div className="answer">
        <p>{message.content}</p>
        <Sources sources={message.sources} />
      </div>
    </div>
  )
}
