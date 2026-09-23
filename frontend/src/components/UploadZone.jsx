import { useRef, useState } from "react";

export default function UploadZone({ file, onFile }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === "application/pdf") onFile(dropped);
  }

  function handleChange(e) {
    const selected = e.target.files[0];
    if (selected) onFile(selected);
  }

  function formatSize(bytes) {
    return bytes > 1024 * 1024
      ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
      : `${(bytes / 1024).toFixed(0)} KB`;
  }

  return (
    <div
      className={`upload-zone ${dragOver ? "drag-over" : ""} ${file ? "has-file" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !file && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={handleChange}
        style={{ display: "none" }}
      />

      {!file ? (
        <>
          <span className="upload-icon">📄</span>
          <h2>Drop your scanned PDF here</h2>
          <p>or click to browse &nbsp;·&nbsp; PDF files only</p>
        </>
      ) : (
        <>
          <span className="upload-icon">✅</span>
          <h2>Document ready</h2>
          <div className="file-info">
            <span className="file-badge">
              📎 {file.name} &nbsp;·&nbsp; {formatSize(file.size)}
            </span>
            <button
              className="file-remove"
              onClick={(e) => { e.stopPropagation(); onFile(null); }}
              title="Remove file"
            >
              ✕
            </button>
          </div>
        </>
      )}
    </div>
  );
}
