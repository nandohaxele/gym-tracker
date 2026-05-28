// SetRow - inline editor for a single Set: reps + weight + delete.
// Inputs are sized for thumb input (>=44px height, numeric keyboard).

export default function SetRow({ index, set, onChange, onDelete }) {
  // TODO: Use inputMode="numeric" + pattern for fast on-screen keyboard.
  return (
    <div className="set-row">
      <span className="set-row__index">{index + 1}</span>
      <input
        type="number"
        inputMode="numeric"
        min="0"
        value={set?.reps ?? ''}
        onChange={(e) => onChange?.({ ...set, reps: Number(e.target.value) })}
        placeholder="Reps"
        aria-label="Reps"
      />
      <input
        type="number"
        inputMode="decimal"
        min="0"
        step="0.5"
        value={set?.weight ?? ''}
        onChange={(e) => onChange?.({ ...set, weight: Number(e.target.value) })}
        placeholder="kg"
        aria-label="Weight"
      />
      <button type="button" className="btn btn--ghost" onClick={onDelete} aria-label="Delete set">
        x
      </button>
    </div>
  );
}
