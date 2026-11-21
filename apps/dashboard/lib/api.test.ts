import { describe, expect, it } from "vitest";
import {
  getProjects,
  getAuditLogs,
  getHealth,
  getWorkflows,
  getWorkflowTemplates,
  getTasks,
} from "@/lib/api";

describe("API client", () => {
  it("exposes the core dashboard endpoints", () => {
    expect(typeof getProjects).toBe("function");
    expect(typeof getAuditLogs).toBe("function");
    expect(typeof getHealth).toBe("function");
  });

  it("exposes the Phase 4 workflow and task endpoints", () => {
    expect(typeof getWorkflows).toBe("function");
    expect(typeof getWorkflowTemplates).toBe("function");
    expect(typeof getTasks).toBe("function");
  });
});
