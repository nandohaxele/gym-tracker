// Modal - bottom-sheet style modal optimized for mobile (slides from bottom).

export default function Modal({ open, onClose, title, children }) {
  // TODO: Trap focus, close on Escape, body scroll lock when open.
  if (!open) return null;
  return (
    <div className="modal" role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal__backdrop" onClick={onClose} />
      <div className="modal__sheet">
        {title && <h2 className="modal__title">{title}</h2>}
        <div className="modal__body">{children}</div>
      </div>
    </div>
  );
}
