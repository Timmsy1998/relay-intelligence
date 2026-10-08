export type Decision = "accepted" | "rejected";
export interface Evidence {
  id: string;
  category: string;
  title: string;
  owner: string;
  revision: string;
  similarity: number;
  checks: string[];
  action: string;
}
export interface Analysis {
  category: string;
  suggested_category: string;
  score: number;
  margin: number;
  abstained: boolean;
  summary: string;
  recommendation: string | null;
  checks: string[];
  evidence: Evidence[];
  model_version: string;
  training_digest: string;
  score_note: string;
}
export interface Incident {
  id: string;
  title: string;
  description: string;
  service: string;
  severity: "P1" | "P2" | "P3";
  status: "queued" | "ready" | "reviewed";
  created_at: string;
  version: number;
  analysis: Analysis | null;
  review: { decision: Decision; note: string; at: string } | null;
  timeline: { at: string; label: string }[];
}
export type Submission = Pick<
  Incident,
  "title" | "description" | "service" | "severity"
>;
