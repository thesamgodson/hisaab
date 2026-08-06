export default function SectionHeader({
  title,
  count,
  description,
}: {
  title: string;
  count?: number;
  description?: string;
}) {
  return (
    <header className="section-heading">
      <div>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {count != null && <span className="count-chip">{count}</span>}
    </header>
  );
}
