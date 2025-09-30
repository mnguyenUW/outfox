<!--
Sync Impact Report
Version change: 1.0.0 → 1.1.0
Modified principles: All (template → Outfox-specific)
Added sections: Technology Stack & Compliance, Development Workflow
Removed sections: None
Templates requiring updates:
✅ .specify/templates/plan-template.md
✅ .specify/templates/spec-template.md
✅ .specify/templates/tasks-template.md
⚠ README.md (missing, recommend creation)
Follow-up TODOs:
TODO(RATIFICATION_DATE): original ratification date required
-->

# Outfox Constitution


## Core Principles

### I. Library-First
Every feature starts as a standalone, self-contained library. Libraries MUST be independently testable and documented. No organizational-only libraries permitted.

### II. API-First
All functionality MUST be exposed via REST API endpoints. Text in/out protocol: JSON responses, errors via HTTP status codes. No styling or frontend logic in API layer.

### III. Test-First (NON-NEGOTIABLE)
Test-driven development is mandatory. Tests MUST be written and fail before implementation. Red-Green-Refactor cycle strictly enforced.

### IV. Integration Testing
Integration tests are REQUIRED for new contracts, contract changes, inter-service communication, and shared schemas. All endpoints MUST have contract and integration tests.

### V. Observability & Simplicity
Structured logging is REQUIRED. Interfaces MUST remain minimal and simple. Debuggability and maintainability are prioritized over feature complexity.


## Technology Stack & Compliance
Python >=3.11, FastAPI, async SQLAlchemy, PostgreSQL, and OpenAI API are REQUIRED. All data handling MUST comply with applicable privacy and security standards. ETL scripts MUST clean and validate data before loading. Indexes and search optimizations are REQUIRED for performance.


## Development Workflow
Code review is REQUIRED for all changes. TDD is enforced; tests MUST precede implementation. Deployment approval is REQUIRED. All PRs/reviews MUST verify compliance with this constitution.


## Governance
This constitution supersedes all other practices. Amendments require documentation, approval, and a migration plan. All PRs/reviews MUST verify compliance. Complexity MUST be justified. Use runtime guidance files for development best practices.

**Version**: 1.1.0 | **Ratified**: TODO(RATIFICATION_DATE): original ratification date required | **Last Amended**: 2025-09-29