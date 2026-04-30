import type { Severity } from '../types';

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`severity severity-${severity.toLowerCase()}`}>{severity}</span>;
}
