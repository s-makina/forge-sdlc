export function PlaceholderPage({ title, note }: { title: string; note: string }) {
  return (
    <div>
      <h1>{title}</h1>
      <div className="card">
        <p className="placeholder">{note}</p>
      </div>
    </div>
  );
}
