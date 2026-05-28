// Input - reusable labelled text input. Min height 44px for touch targets.

export default function Input({ label, id, error, className = '', ...rest }) {
  // TODO: Forward ref + aria-invalid wiring.
  const inputId = id || rest.name;
  return (
    <div className={`field ${error ? 'field--error' : ''} ${className}`.trim()}>
      {label && <label htmlFor={inputId}>{label}</label>}
      <input id={inputId} {...rest} />
      {error && <p className="field__error">{error}</p>}
    </div>
  );
}
