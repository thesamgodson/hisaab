import type { ActionItem } from "@/lib/action-types";

interface ActionCardProps {
  item: ActionItem;
}

export default function ActionCard({ item }: ActionCardProps) {
  return (
    <div
      className="rounded-xl p-5 card-hover"
      style={{
        background: "var(--elevated)",
        border: "1px solid var(--border)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {/* Scheme label */}
      <span
        className="text-xs font-semibold uppercase tracking-wider"
        style={{ color: "var(--accent)" }}
      >
        {item.scheme}
      </span>

      {/* Action text */}
      <p
        className="text-sm font-medium leading-relaxed mt-2 mb-4"
        style={{ color: "var(--text-primary)" }}
      >
        {item.action}
      </p>

      {/* Portal button */}
      {item.portal_url && (
        <a
          href={item.portal_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm font-semibold px-4 py-2 rounded-lg transition-all duration-150 hover:opacity-90 mb-4"
          style={{
            background: "var(--accent-gradient)",
            color: "#ffffff",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          {item.portal_name || "Visit Portal"}
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M7 17L17 7M17 7H7M17 7v10" />
          </svg>
        </a>
      )}

      {/* Escalation note */}
      {item.escalation && (
        <div
          className="rounded-lg p-3 flex items-start gap-2"
          style={{
            background: "var(--surface-tinted)",
            border: "1px solid var(--border-subtle)",
          }}
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
            style={{ color: "var(--accent)" }}
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <div className="flex-1 min-w-0">
            <p
              className="text-xs leading-snug"
              style={{ color: "var(--text-secondary)" }}
            >
              {item.escalation}
            </p>
            {item.escalation_url && (
              <a
                href={item.escalation_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs font-medium mt-1 inline-block transition-colors duration-150 hover:underline"
                style={{ color: "var(--accent)" }}
              >
                Escalate here
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
