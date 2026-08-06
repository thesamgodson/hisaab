/** Section title with an optional count chip and a rule filling the row. */
export default function SectionHeader({
  title,
  count,
}: {
  title: string;
  count?: number;
}) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <h2
        className="text-lg font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        {title}
      </h2>
      {count != null && count > 0 && (
        <span
          className="inline-flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-semibold"
          style={{
            background: "var(--accent-light)",
            color: "var(--accent)",
          }}
        >
          {count}
        </span>
      )}
      <div
        className="flex-1 h-px"
        style={{ background: "var(--border-subtle)" }}
      />
    </div>
  );
}
