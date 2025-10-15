# Unified FastAPI Runtime Entry Points - Brownfield Enhancement

## Epic Goal
Ensure the platform runs through a single, well-configured FastAPI application so deployments, scripts, and troubleshooting always target the same runtime surface.

## Epic Description

**Existing System Context**
- Current relevant functionality: Multiple FastAPI apps (`api/app.py`, `app_simple.py`, `app_minimal.py`, `app_simple_production.py`) each define CORS, metrics, and diagnostics differently, causing inconsistent behavior between CLI, Docker, and PaaS environments.
- Technology stack: Python 3.11, FastAPI, Uvicorn, Prometheus client, Sentry SDK, Supabase integrations.
- Integration points: Uvicorn entrypoints (`start.py`, Dockerfile, Procfile), observability hooks (Prometheus `/metrics`, Sentry), Supabase service initialization.

**Enhancement Details**
- What's being added/changed: Consolidate on one production-ready FastAPI app, expose settings-driven toggles for optional middleware/integrations, and remove redundant app variants.
- How it integrates: Update runtime launchers (CLI `start.py`, Dockerfile CMD, Procfile) to start the unified app and ensure existing routes/health endpoints remain stable.
- Success criteria: All deployments start the same app, health/metrics endpoints respond, and redundant files are archived or deleted without breaking current tooling.

## Stories
1. **Select and streamline the canonical FastAPI app** – Decide the baseline file, merge required functionality from other variants, and remove unused entrypoints.
2. **Introduce configuration toggles for optional integrations** – Add env-driven switches for Prometheus, Sentry, and debug diagnostics to keep parity across environments.
3. **Update launch paths and smoke tests** – Align `start.py`, Dockerfile, Procfile, and basic automated smoke tests to confirm the unified app boots and exposes critical endpoints.

## Compatibility Requirements
- [ ] Existing APIs remain unchanged
- [ ] Database schema changes are backward compatible
- [ ] UI changes follow existing patterns
- [ ] Performance impact is minimal

## Risk Mitigation
- **Primary Risk:** Removing alternate app files breaks ad-hoc scripts or deployments still referencing them.
- **Mitigation:** Provide a migration checklist, update deployment docs, and search repository for references before deletion.
- **Rollback Plan:** Restore previous app files from version control and revert launcher changes if unforeseen issues appear.

## Definition of Done
- [ ] All stories completed with acceptance criteria met
- [ ] Existing functionality verified through smoke tests / health checks
- [ ] Integration points (metrics, diagnostics) operating with unified app
- [ ] Documentation (deployment/README) updated appropriately
- [ ] No regression in existing features

## Validation Checklist

**Scope Validation**
- [x] Epic can be completed in 1–3 stories maximum
- [x] No architectural documentation is required
- [x] Enhancement follows existing patterns
- [x] Integration complexity is manageable

**Risk Assessment**
- [x] Risk to existing system is low
- [x] Rollback plan is feasible
- [x] Testing approach covers existing functionality
- [x] Team has sufficient knowledge of integration points

**Completeness Check**
- [x] Epic goal is clear and achievable
- [x] Stories are properly scoped
- [x] Success criteria are measurable
- [x] Dependencies are identified (launcher scripts, deployment configs)

---

**Story Manager Handoff:**

"Please develop detailed user stories for this brownfield epic. Key considerations:

- This is an enhancement to an existing system running Python 3.11 with FastAPI, Prometheus metrics, and Sentry integrations.
- Integration points: Uvicorn launchers (`start.py`, Dockerfile, Procfile) and observability hooks (`/metrics`, `/healthz`, Sentry init).
- Existing patterns to follow: FastAPI router structure in `api/routes`, environment-driven configuration via `dotenv`, and centralized logging setup.
- Critical compatibility requirements: Maintain existing API responses, keep database interactions untouched, preserve performance characteristics, and ensure health/metrics endpoints stay online.

The epic should maintain system integrity while delivering a single, unified FastAPI runtime entry point."
