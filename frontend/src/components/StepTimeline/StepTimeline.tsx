import type { StepStatus } from '../../types';

export function StepTimeline({ steps }: { steps: StepStatus[] }) {
  return (
    <div className="timeline">
      {steps.map((step) => (
        <div key={step.name} className={`timeline-step ${step.state}`}>
          <span />
          <div>
            <strong>{step.label}</strong>
            <small>{step.message || step.state}</small>
          </div>
        </div>
      ))}
    </div>
  );
}
