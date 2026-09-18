import {Clock, TriangleAlert, CircleCheckBig} from 'lucide-react'

export const labels = [
  {
    value: 'bug',
    label: 'Bug',
  },
  {
    value: 'feature',
    label: 'Feature',
  },
  {
    value: 'documentation',
    label: 'Documentation',
  },
]

// Severity tiers drive badge color. Every status maps to exactly one tier:
//   critical -> red (destructive)   e.g. expired, denied, failed
//   warning  -> amber (warning)     e.g. expiring soon, needs review
//   good     -> green (success)     e.g. valid, approved, done
//   neutral  -> gray (secondary)    e.g. pending, queued, n/a
export type Severity = 'critical' | 'warning' | 'good' | 'neutral'

export const severityToBadgeVariant: Record<Severity, 'destructive' | 'warning' | 'success' | 'secondary'> = {
  critical: 'destructive',
  warning: 'warning',
  good: 'success',
  neutral: 'secondary',
}

// PRODUCT_CUSTOMIZE: replace this list with the real statuses this product
// produces (must match exactly what the backend poller writes to
// records.status). Every status must declare a severity tier above. Default
// values below are generic placeholders only — do not ship as-is.
// __STATUSES_BLOCK_START__
export const statuses: {
  label: string
  value: string
  icon: typeof TriangleAlert
  severity: Severity
}[] = [
  { label: 'Missing', value: 'missing:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Expired', value: 'expired:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Valid', value: 'valid:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Flagged', value: 'flagged:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Compliant', value: 'compliant:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Deviates', value: 'deviates:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'At Risk', value: 'at_risk:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Unverified', value: 'unverified:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Document Derived Fact', value: 'document_derived_fact:good', icon: CircleCheckBig, severity: 'good' as Severity },
  { label: 'Unverified Finding', value: 'unverified_finding:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Silent Change Detected', value: 'silent_change_detected:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Benchmark Outlier', value: 'benchmark_outlier:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Billing Discrepancy', value: 'billing_discrepancy:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Auto Renewal Trap', value: 'auto_renewal_trap:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Escalation Cap Breach', value: 'escalation_cap_breach:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Minimum Commitment Shortfall', value: 'minimum_commitment_shortfall:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Notice Window Passed', value: 'notice_window_passed:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'Notice Window Approaching', value: 'notice_window_approaching:warning', icon: Clock, severity: 'warning' as Severity },
  { label: 'Quote Expired', value: 'quote_expired:critical', icon: TriangleAlert, severity: 'critical' as Severity },
  { label: 'No Baseline', value: 'no_baseline:warning', icon: Clock, severity: 'warning' as Severity }
]
// __STATUSES_BLOCK_END__
