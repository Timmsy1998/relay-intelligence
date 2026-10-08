import { afterEach, expect, it, vi } from "vitest";
import { RelayClient } from "../src/api";
import type { Incident } from "../src/types";
afterEach(() => vi.unstubAllGlobals());
it("preserves the submission key and workspace credentials", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify({ id: "incident" })));
  vi.stubGlobal("fetch", fetcher);
  const client = new RelayClient("private-token");
  await client.submit(
    {
      title: "Queue stalled",
      description: "Messages are waiting for a worker",
      service: "orders",
      severity: "P2",
    },
    "same-retry-key",
  );
  const options = fetcher.mock.calls[0][1];
  expect(options.headers.Authorization).toBe("Bearer private-token");
  expect(options.headers["Idempotency-Key"]).toBe("same-retry-key");
});
it("passes review version so stale writes fail", async () => {
  const fetcher = vi.fn().mockResolvedValue(new Response("{}"));
  vi.stubGlobal("fetch", fetcher);
  await new RelayClient("token").review(
    { id: "abc", version: 2 } as Incident,
    "accepted",
    "Confirmed",
  );
  expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
    decision: "accepted",
    note: "Confirmed",
    version: 2,
  });
});
it("surfaces a conflict to the engineer", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Incident changed. Refresh." }), {
        status: 409,
      }),
    ),
  );
  await expect(new RelayClient("token").list()).rejects.toThrow(
    "Incident changed. Refresh.",
  );
});
