import { describe, expect, it } from "vitest";
import { getProjects, getAuditLogs, getHealth } from "@/lib/api";

describe("API client", () => {
  it("exposes the core dashboard endpoints", () => {
    expect(typeof getProjects).toBe("function");
    expect(typeof getAuditLogs).toBe("function");
    expect(typeof getHealth).toBe("function");
  });
});
