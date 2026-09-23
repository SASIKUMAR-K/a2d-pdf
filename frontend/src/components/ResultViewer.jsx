import { useRef } from "react";

export default function ResultViewer({ result, onReset }) {
  const iframeRef = useRef(null);

  function handlePrint() {
    const iframe = iframeRef.current;
    if (!iframe) return;
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
  }

  // Inject the HTML into the iframe via srcdoc
  const htmlContent = result.html || "";

  return (
    <div className="result-section">
      <div className="result-header">
        <div className="result-meta">
          <h2>{result.title || "Digitalized Document"}</h2>
          <p>Your document has been successfully digitalized</p>
        </div>
        <div className="result-badges">
          <span className="badge badge-pages">📄 {result.total_pages} page{result.total_pages !== 1 ? "s" : ""}</span>
          <span className="badge badge-type">{result.document_type || "Document"}</span>
        </div>
      </div>

      <div className="result-actions">
        <button className="btn-print" onClick={handlePrint}>
          🖨️ Print Document
        </button>
        <button className="btn-secondary" onClick={onReset}>
          ↩ New Document
        </button>
      </div>

      <div className="result-frame-wrap">
        <iframe
          ref={iframeRef}
          className="result-frame"
          srcDoc={htmlContent}
          title="Digitalized Document"
          sandbox="allow-same-origin allow-modals"
        />
      </div>
    </div>
  );
}
