// Button - reusable primitive. Min height 44px for touch targets.

export default function Button({
  type = 'button',
  variant = 'primary',
  className = '',
  children,
  ...rest
}) {
  // TODO: Add loading state + icon slot if needed.
  const cls = `btn btn--${variant} ${className}`.trim();
  return (
    <button type={type} className={cls} {...rest}>
      {children}
    </button>
  );
}
