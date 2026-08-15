interface SourceLinkProps {
  /** Absolute source URL, a bare host, or a root-relative Hisaab path. */
  url: string;
  label?: string;
  accessibleLabel?: string;
  /** Optional hover/long-press detail — never the only place a fact appears. */
  title?: string;
}

export default function SourceLink({ url, label = "Data source", accessibleLabel, title }: SourceLinkProps) {
  if (!url) return null;
  const href = url.startsWith("http") || url.startsWith("/") ? url : `https://${url}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="source-link"
      aria-label={accessibleLabel}
      title={title}
    >
      {label}<span className="sr-only"> (opens source in a new tab)</span>
    </a>
  );
}
