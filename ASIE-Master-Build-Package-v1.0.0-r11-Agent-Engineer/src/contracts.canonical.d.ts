import type { RiskAdvisorySummary } from "./contracts";

/**
 * Canonical additive contract alignment.
 *
 * These fields are already emitted by the backend projections. The declaration
 * augmentation makes the public TypeScript surface describe the as-built JSON
 * without changing runtime payloads or frozen contract identifiers.
 */
declare module "./contracts" {
  interface ProjectOverview {
    risk_advisory_summary: RiskAdvisorySummary;
  }

  interface SnapshotReport {
    risk_advisory_summary: RiskAdvisorySummary;
    funder_report: Record<string, unknown>;
  }

  interface SnapshotReportView {
    risk_advisory_summary: RiskAdvisorySummary;
    funder_report: Record<string, unknown>;
  }
}

export {};
