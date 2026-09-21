# TAM MỸ SMART FRUIT — AGENT INSTRUCTIONS

You are working on a production-grade agricultural supply-chain platform.

Before doing ANY task:

1. Read `/docs/MASTER_SPEC.md`.
2. Read all relevant documents under `/docs`.
3. Do not contradict MASTER_SPEC.md.
4. Do not simplify business rules without explicit approval.
5. Do not start coding if the required analysis/design phase has not been approved.
6. Preserve bilingual VI/EN architecture.
7. Never hard-code user-facing text.
8. Never allow verified upstream data to be manually re-entered downstream.
9. Never send raw user-declared critical data directly to blockchain.
10. Blockchain anchoring must follow:
   Capture → Validate → Evidence → Risk → Verify → Approve → Anchor.
11. Preserve traceability across split/merge.
12. Enforce mass balance.
13. Enforce RBAC + Data Scope on backend.
14. Business status transitions must use actions/workflows, not arbitrary status editing.
15. Critical business records must remain auditable/versioned.
16. Prefer Modular Monolith initially; do not create unnecessary microservices.
17. UI must remain simple for non-technical users.
18. Primary brand color: #2F8F3A.
19. Font: Be Vietnam Pro.
20. Before modifying architecture, explain the impact first.

At the beginning of each major task:
- summarize the relevant requirements from MASTER_SPEC.md;
- state what you are going to change;
- identify affected modules;
- then implement.

After completing each task:
- check business consistency;
- check VI/EN;
- check authorization;
- check validation;
- check audit;
- check traceability;
- check tests.