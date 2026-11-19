# Phase 2 — Agent and Model Management

**Goal:** An administrator can define versioned agents (roles, skills, tools, model profiles) and connect local + external models through a unified gateway.

**Depends on:** Phase 1.\
**Runs parallel to:** Phase 3.\
**Reference:** SRS FR-3, FR-4; README §8, §9.

---

## 2.1 Agent registry data model

**What will be done**
- Tables: `agents`, `agent_versions`, `agent_skills`, `agent_tool_permissions`.
- An agent version captures instructions, capabilities, tools, permissions, skills, and a model profile, as an immutable revision.
- CRUD API + dashboard Agents page listing versions.

**Acceptance criteria**
- An agent can be created, and a configuration change yields a new version rather than an overwrite.

## 2.2 Versioned agent definitions

**What will be done**
- Versioned YAML agent definitions (see README §8.4) with a validation schema.
- A promotion path: a candidate version can be marked active after review (manual for MVP).
- Seed definitions for the six MVP roles (see Phase 5).

**Acceptance criteria**
- Definitions load from YAML, validate, and become agent versions.

## 2.3 Skills and tool registry

**What will be done**
- A registry of tool descriptors (name, input schema, permissions required).
- A registry of skills (name, description, files/instructions).
- Validation that an agent references only known tools and skills.

**Acceptance criteria**
- Tools and skills are discoverable and validated against agent definitions.

## 2.4 Model provider configuration

**What will be done**
- Tables: `model_providers`, `models`.
- Store provider base URL, type (ollama/external-openai-compatible), credential reference, and capability declarations.
- Credential references point to a secret store, never inline values.

**Acceptance criteria**
- A provider + model can be configured; credentials are never exposed via the API.

## 2.5 LiteLLM integration

**What will be done**
- Wire LiteLLM as the model gateway: providers map to LiteLLM config.
- API routes to list providers, test connectivity, and (later) route chat requests.
- Health check against each configured provider.

**Acceptance criteria**
- The gateway lists configured providers and can reach them.

## 2.6 Logical model profiles

**What will be done**
- Profiles: `general-fast`, `reasoning-strong`, `coding-strong`, `coding-fast`, `review-specialist`, `documentation`, `vision`.
- A routing policy maps a profile to a concrete model based on capability + availability.

**Acceptance criteria**
- Requesting `coding-strong` resolves to a configured model; unknown/incompatible combos fail clearly.

## 2.7 Provider health and capability checks

**What will be done**
- On-demand capability checks: tool-calling, structured output, streaming.
- A fallback that never silently routes to an incapable model.
- Record availability, latency, error rate, and usage (FR-3.4).

**Acceptance criteria**
- A provider declared to lack tool-calling is not used for tool-requiring tasks.

---

## Exit criteria (Phase 2)
An admin can register an agent with a model profile, connect Ollama and an external OpenAI-compatible endpoint, and see provider health and capability status.