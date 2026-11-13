export default function Sources({ sources }) {
  if (sources.length === 0) return null
  return (
    <details className="sources">
      <summary>
        Sources ({sources.length})
      </summary>
      <ol>
        {sources.map((s, i) => (
          <li key={s.chunk_id}>
            <div className="source-meta">
              [{i + 1}] {s.filename} · part {s.idx} · {s.score.toFixed(2)}
            </div>
            <p className="source-snippet">{s.snippet}</p>
          </li>
        ))}
      </ol>
    </details>
  )
}
