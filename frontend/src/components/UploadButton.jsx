import { useRef, useState } from 'react'
import { uploadFiles } from '../api'

export default function UploadButton({ onUploaded, onErrors }) {
  const inputRef = useRef(null)
  const [uploading, setUploading] = useState(false)

  const handleChange = async (files) => {
    if (!files || files.length === 0 || uploading) return
    setUploading(true)
    try {
      const result = await uploadFiles(Array.from(files))
      onUploaded(result.documents)
      onErrors(result.errors)
    } catch (err) {
      onErrors([{ filename: 'upload', error: err instanceof Error ? err.message : 'Upload failed' }])
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.md"
        hidden
        aria-label="Choose documents to upload"
        onChange={(e) => void handleChange(e.target.files)}
      />
      <button
        type="button"
        className="upload-btn"
        disabled={uploading}
        onClick={() => inputRef.current?.click()}
      >
        {uploading ? 'Uploading…' : 'Upload'}
      </button>
    </>
  )
}
