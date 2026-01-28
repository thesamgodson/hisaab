import type { ContactCard } from "@/lib/action-types";

const FRESHNESS_STYLES: Record<
  ContactCard["freshness"],
  { bg: string; color: string; label: string }
> = {
  fresh: {
    bg: "oklch(0.96 0.06 145)",
    color: "oklch(0.40 0.15 145)",
    label: "Verified",
  },
  stale: {
    bg: "oklch(0.97 0.04 65)",
    color: "oklch(0.50 0.14 65)",
    label: "Possibly outdated",
  },
  expired: {
    bg: "oklch(0.97 0.04 25)",
    color: "oklch(0.50 0.18 25)",
    label: "Outdated",
  },
};

interface ContactCardDisplayProps {
  contact: ContactCard;
}

export default function ContactCardDisplay({
  contact,
}: ContactCardDisplayProps) {
  const freshStyle = FRESHNESS_STYLES[contact.freshness];

  return (
    <div
      className="rounded-xl p-5 flex flex-col gap-4 h-full card-hover"
      style={{
        background: "var(--elevated)",
        border: "1px solid var(--border)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {/* Role + freshness badge */}
      <div className="flex items-start justify-between gap-2">
        <span
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: "var(--accent)" }}
        >
          {contact.role}
        </span>
        <span
          className="text-xs font-medium px-2 py-0.5 rounded-full flex-shrink-0"
          style={{ background: freshStyle.bg, color: freshStyle.color }}
        >
          {freshStyle.label}
        </span>
      </div>

      {/* Name */}
      <div>
        {contact.name ? (
          <p
            className="text-base font-semibold leading-snug"
            style={{ color: "var(--text-primary)" }}
          >
            {contact.name}
          </p>
        ) : (
          <p
            className="text-base font-medium italic"
            style={{ color: "var(--text-muted)" }}
          >
            Name not on record
          </p>
        )}
      </div>

      {/* Contact details */}
      <div className="space-y-2 flex-1">
        {contact.phone && (
          <a
            href={`tel:${contact.phone}`}
            className="flex items-center gap-2 text-sm transition-colors duration-150 hover:text-[var(--accent)] group"
            style={{ color: "var(--text-secondary)" }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="flex-shrink-0 group-hover:stroke-[var(--accent)]"
              aria-hidden="true"
            >
              <path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 10.8a19.79 19.79 0 01-3.07-8.67A2 2 0 012 0h3a2 2 0 012 1.72 12.84 12.84 0 00.7 2.81 2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45 12.84 12.84 0 002.81.7A2 2 0 0122 14.92v2z" />
            </svg>
            <span className="font-mono tabular-nums">{contact.phone}</span>
          </a>
        )}

        {contact.email && (
          <a
            href={`mailto:${contact.email}`}
            className="flex items-center gap-2 text-sm transition-colors duration-150 hover:text-[var(--accent)] group min-w-0"
            style={{ color: "var(--text-secondary)" }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="flex-shrink-0"
              aria-hidden="true"
            >
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
              <polyline points="22,6 12,13 2,6" />
            </svg>
            <span className="truncate">{contact.email}</span>
          </a>
        )}

        {contact.office_address && (
          <div
            className="flex items-start gap-2 text-sm"
            style={{ color: "var(--text-muted)" }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="flex-shrink-0 mt-0.5"
              aria-hidden="true"
            >
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z" />
              <circle cx="12" cy="10" r="3" />
            </svg>
            <span className="leading-snug">{contact.office_address}</span>
          </div>
        )}

        {!contact.phone && !contact.email && !contact.office_address && (
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            No contact details available
          </p>
        )}
      </div>

      {/* Relevance + last verified */}
      <div
        className="pt-3 border-t space-y-2"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <p
          className="text-xs leading-snug"
          style={{ color: "var(--text-secondary)" }}
        >
          {contact.relevance}
        </p>
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Last verified: {contact.last_verified}
          </p>
          {contact.source_url && (
            <a
              href={contact.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs transition-colors duration-150 hover:underline"
              style={{ color: "var(--accent)" }}
            >
              Source
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
