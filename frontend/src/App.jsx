import { useState, useRef } from "react";
import UploadZone from "./components/UploadZone";
import StepProgress from "./components/StepProgress";
import ResultViewer from "./components/ResultViewer";
import "./App.css";

const STEPS = [
  { id: 1, label: "Uploading PDF",       desc: "Sending your document securely" },
  { id: 2, label: "Reading Document",    desc: "Gemini AI is scanning all pages" },
  { id: 3, label: "Analyzing Structure", desc: "Detecting tables, forms, headings" },
  { id: 4, label: "Building HTML",       desc: "Creating pixel-perfect replica" },
  { id: 5, label: "Done",               desc: "Your document is ready" },
];

export default function App() {
  const [file, setFile]           = useState(null);
  const [status, setStatus]       = useState("idle"); // idle | processing | done | error
  const [currentStep, setStep]    = useState(0);
  const [result, setResult]       = useState(null);
  const [error, setError]         = useState("");
  const abortRef                  = useRef(null);

  const API = import.meta.env.VITE_API_URL;

  async function handleDigitalize() {
    if (!file) return;
    setStatus("processing");
    setError("");
    setResult(null);
    setStep(1);

    const formData = new FormData();
    formData.append("file", file);

    // Simulate step progression while waiting for API
    const stepTimer = simulateSteps(setStep);

    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch(`${API}/digitalize`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      clearInterval(stepTimer);

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Server error");
      }

      const data = await res.json();
      setStep(5);
      setResult(data);
      setStatus("done");
    } catch (e) {
      clearInterval(stepTimer);
      if (e.name === "AbortError") return;
      setError(e.message);
      setStatus("error");
      setStep(0);
    }
  }

  function handleReset() {
    setFile(null);
    setStatus("idle");
    setStep(0);
    setResult(null);
    setError("");
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">⚡</span>
          <span className="logo-text">a2d<span className="logo-accent">pdf</span></span>
        </div>
        <p className="logo-tagline">Scanned PDF → Digital HTML in seconds</p>
      </header>

      <main className="app-main">
        {status === "idle" && (
          <div className="upload-section">
            <UploadZone file={file} onFile={setFile} />
            {file && (
              <button className="btn-digitalize" onClick={handleDigitalize}>
                <span className="btn-icon">✦</span>
                Digitalize Document
              </button>
            )}
          </div>
        )}

        {status === "processing" && (
          <div className="processing-section">
            <StepProgress steps={STEPS} currentStep={currentStep} />
            <p className="processing-note">
              This may take 30–90 seconds depending on document size.
            </p>
          </div>
        )}

        {status === "error" && (
          <div className="error-section">
            <div className="error-box">
              <span className="error-icon">✕</span>
              <p>{error}</p>
            </div>
            <button className="btn-secondary" onClick={handleReset}>Try Again</button>
          </div>
        )}

        {status === "done" && result && (
          <ResultViewer result={result} onReset={handleReset} />
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by Gemini 2.5 Flash &nbsp;·&nbsp; a2d-pdf</p>
      </footer>
    </div>
  );
}

function simulateSteps(setStep) {
  const delays = [0, 4000, 12000, 25000]; // step 1→2→3→4
  delays.forEach((delay, i) => {
    setTimeout(() => setStep(i + 1), delay);
  });
  // keep at step 4 until real response
  return null;
}
