export function AuthTriangleField() {
  return (
    <div className="auth-triangle-field" aria-hidden="true">
      {Array.from({ length: 10 }, (_, index) => <span key={index} />)}
    </div>
  );
}
