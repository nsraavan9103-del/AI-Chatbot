import { useRef, useState } from 'react'
import { uploadFiles, type DocumentOut } from '../api'

type Props = {
  onUploaded: (documents: DocumentOut[]) => void
  onErrors: (errors: { filename: string; error: string }[]) => void
}

export default function UploadButton({ onUploaded, onErrors }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const handleChange = async (files: FileList | null) => {
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
