export default function StepProgress({ steps, currentStep }) {
  return (
    <div className="step-progress">
      <h3>Processing your document</h3>
      <div className="step-list">
        {steps.map((step) => {
          const done   = currentStep > step.id;
          const active = currentStep === step.id;
          return (
            <div
              key={step.id}
              className={`step-item ${done ? "done" : ""} ${active ? "active" : ""}`}
            >
              <div className="step-dot">
                {done ? "✓" : step.id}
              </div>
              <div className="step-text">
                <div className="step-label">{step.label}</div>
                {active && <div className="step-desc">{step.desc}</div>}
              </div>
              {active && <div className="step-spinner" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
