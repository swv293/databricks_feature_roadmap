# TRB sample corpus: canonical facts (SYNTHETIC)

Single source of truth for the synthetic sample data. `trb/table/` rows and `trb/docs/samples/`
documents must agree with this file exactly. If they disagree, this file wins.

Org: **Acme Health Plan** (fictional). People are referenced by role only.
Schemas: `platform.trb` (TRB tables) · `platform.feature_tracker` (tracker tables, owned by the weekly job).

## Rule
PHI-eligible ⇔ **current** Databricks phase = GA **AND** TRB status = **Approved**.
"Approved with Conditions" is NOT PHI-eligible until every condition is verified closed and the
TRB moves the review to Approved. The Databricks phase comes from `platform.feature_tracker.features`,
not from the TRB tables. TRB tables record only `dbx_phase_at_decision` as a snapshot.

## Approved scope values
`PHI` · `Non-PHI only` · `Sandbox only (synthetic data)` · `None`

## Reviews
| review_id | feature_key | phase at decision | status | scope | decided at | notes |
|---|---|---|---|---|---|---|
| TRB-2026-001 | Row filters & column masks@Platform & Governance | GA | Approved | PHI | TRBM-2026-07-14 | DR-2026-001 |
| TRB-2026-002 | Attribute-based access control (ABAC)@Platform & Governance | GA | Under Review | None | — | Intro 07-28. Deferred: governed-tag source of truth and IdP attribute sync not yet designed. Follow-up 08-25: still open. |
| TRB-2026-003 | SQL Server (cloud + on-prem)@Ingestion | Public Preview | Approved | Non-PHI only | TRBM-2026-07-14 | DR-2026-003. Conditions COND-003-1..2. Re-review trigger: Databricks phase → GA. |
| TRB-2026-004 | Kafka-compatible APIs@Ingestion | Beta | Rejected | None | TRBM-2026-07-14 | DR-2026-004. Beta is out of compliance scope. Resubmit at GA. |
| TRB-2026-005 | Genie One@SQL & BI Analytics | GA | Approved with Conditions | PHI (after all conditions close) | TRBM-2026-07-28 | DR-2026-005. COND-005-1..4. Approval letter. |
| TRB-2026-006 | Knowledge Assistant@Generative AI & Agents | Beta | Under Review | Sandbox only (synthetic data) | — | Intro 08-11. Sandbox pilot runs under EXC-2026-002. |
| TRB-2026-007 | Mode: Databricks-to-Open (bearer/OIDC)@Sharing & Collaboration | GA | Approved with Conditions | Non-PHI only (PHI requires a BAA per COND-007-1) | TRBM-2026-08-25 | DR-2026-007. COND-007-1..3. Approval letter. |
| TRB-2026-008 | Databricks Apps@Apps & Developer Tools | GA | Under Review | None | — | Intro 08-11. Follow-up 08-25: pending app-auth (user vs service-principal) and egress testing. |
| TRB-2026-009 | MCP servers@Generative AI & Agents | GA | Not Reviewed | None | — | Intake submitted 2026-09-22. Triage scheduled for the next meeting. |

## Meetings (biweekly)
- **TRBM-2026-07-14**: 001 Approved · 003 Approved (Non-PHI only) · 004 Rejected
- **TRBM-2026-07-28**: 005 Approved with Conditions · 002 introduced → Under Review (deferred)
- **TRBM-2026-08-11**: 006 introduced → Under Review, EXC-2026-002 Approved · 008 introduced → Under Review
- **TRBM-2026-08-25**: 007 Approved with Conditions · 002 follow-up, still Under Review · 008 follow-up, still Under Review
- **TRBM-2026-09-08**: EXC-2026-001 **DENIED** · condition verification status for COND-005-x
- **TRBM-2026-09-22**: 009 intake received (Not Reviewed) · status check on 002, 006, 008

## Conditions
| id | review | short title | due |
|---|---|---|---|
| COND-003-1 | 003 | Connector limited to non-PHI source tables; monthly audit | 2026-08-14 |
| COND-003-2 | 003 | On-prem TLS validation + encryption-in-transit audit | 2026-09-14 |
| COND-005-1 | 005 | Query audit logging (prompt, generated SQL, row count) via system tables | 2026-09-15 |
| COND-005-2 | 005 | Row filters / column masks verified with 3 test identities | 2026-09-15 |
| COND-005-3 | 005 | Monthly response sampling; small-cell suppression (count < 5) | monthly |
| COND-005-4 | 005 | User training (HIPAA minimum-necessary + Genie usage); annual refresh | 2026-09-15 |
| COND-007-1 | 007 | Signed BAA with the recipient before any PHI share or token issuance | per engagement |
| COND-007-2 | 007 | Token lifetime ≤ 30 days; recipient IP access list; quarterly rotation | 2026-10-25 |
| COND-007-3 | 007 | Share-access audit logs retained 180 days; monthly anomaly review | 2026-10-25 |

Verification status as of 2026-09-22: COND-003-1 Closed, COND-003-2 Closed, COND-005-1 Closed,
COND-005-2 Closed, COND-005-3 In Progress, COND-005-4 Open, COND-007-1..3 Open.
So 005 stays "Approved with Conditions".

## Exceptions
| id | review | request | status | decided at |
|---|---|---|---|---|
| EXC-2026-001 | TRB-2026-003 | Finance asks to ingest member name + ID (PHI) through the SQL Server connector before GA, for annual reconciliation | **Denied** | TRBM-2026-09-08 |
| EXC-2026-002 | TRB-2026-006 | Sandbox pilot of the Beta Knowledge Assistant, using synthetic/non-PHI documents only | Approved, expires 2026-11-11 | TRBM-2026-08-11 |

EXC-2026-001 denial rationale: Public Preview is subject to compliance restrictions, so it cannot
carry PHI. Alternatives offered: use an already-approved GA ingestion path, or wait for GA plus a re-review.

## Documents (doc_id → path under trb/docs/samples/)
Charter `CHARTER-2026` · minutes `MIN-TRBM-2026-MM-DD` · intake `INT-TRB-2026-NNN` · risk assessment `RA-TRB-2026-NNN`
· decision record `DR-2026-NNN` · approval letter `CAL-TRB-2026-NNN` · exception `EXC-2026-NNN`.
Required set: charter; 6 minutes; INT-006, INT-009; RA-005, RA-007; DR-001, 003, 004, 005, 007;
CAL-005, CAL-007; EXC-2026-001, EXC-2026-002.

## Extended reviews TRB-2026-010..035 (platform baseline and October intake)
Source of truth: `trb/data/reviews_extended.json`. The 26 features are exactly the tracker features whose
seed TRB status was not "Not Reviewed". Statuses match the tracker. Decisions were made at the platform-baseline
meetings TRBM-2026-04-21, 05-05, 05-19, 06-02, 06-16, 06-30; the six Under Review items were introduced at
TRBM-2026-10-06. Only TRB-2026-034 (Serverless compute, Approved with Conditions) has conditions (COND-034-1..3,
none closed). `trb/genie/generate_extended.py` produces all table rows and documents for these reviews from that file,
and rebuilds the `documents` index from every sample document's front-matter.
