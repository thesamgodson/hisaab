interface SourceLinkProps {
  url: string;
  label?: string;
}

export default function SourceLink({ url, label = "Official source" }: SourceLinkProps) {
  if (!url) return null;
  const href = url.startsWith("http") ? url : `https://${url}`;

  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="source-link">
      {label}<span className="sr-only"> (opens official source in a new tab)</span>
    </a>
  );
}
