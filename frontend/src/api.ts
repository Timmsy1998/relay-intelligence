import type { Decision, Incident, Submission } from "./types";

export class RelayClient {
  constructor(private token: string) {}
  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`/api/${path}`, {
      ...init,
      signal: AbortSignal.timeout(15000),
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.token}`,
        ...init.headers,
      },
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(
        body.detail ||
          `Request failed (${response.status}). Check the connection and input.`,
      );
    }
    return response.json() as Promise<T>;
  }
  async list() {
    return (await this.request<{ items: Incident[] }>("incidents/")).items;
  }
  submit(payload: Submission, key: string) {
    return this.request<Incident>("incidents/", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "Idempotency-Key": key },
    });
  }
  review(incident: Incident, decision: Decision, note: string) {
    return this.request<Incident>(`incidents/${incident.id}/review/`, {
      method: "POST",
      body: JSON.stringify({ decision, note, version: incident.version }),
    });
  }
}
