# Security & Privacy (HIPAA) Risk Assessment

**Classification:** Internal – Technical Review Board  
**Standard:** NIST SP 800-30 Risk Management Guide; HIPAA Security Rule (45 CFR §§ 164.308, 164.312, 164.314)

---

## 1. Executive Summary

| Field | Value |
|-------|-------|
| **Feature Name** | [Feature] |
| **Review ID** | [TRB-YYYY-NNN] |
| **Assessment Date** | [YYYY-MM-DD] |
| **Assessed By** | [Enterprise Architect / Privacy Officer] |
| **Overall Risk Level** | [ ] Low | [ ] Moderate | [ ] High | [ ] Critical |
| **PHI-Eligible (GA + Conditions Met)?** | [ ] Yes | [ ] No | [ ] Conditional |

---

## 2. Risk Assessment Context

### 2.1 System Boundaries

**What is in scope:**
- Databricks feature functionality and data flows within Acme Health Plan environments
- Authentication, authorization, and access control mechanisms
- Data encryption and masking capabilities
- Audit logging and monitoring

**What is out of scope:**
- Databricks infrastructure security (inherited via AWS Shared Responsibility Model)
- Third-party tool integrations (assessed separately)

### 2.2 Data Classification

**Data Types Processed:**
- [ ] Public | [ ] Internal | [ ] Confidential | [ ] PHI/Restricted

**Sensitivity Level:**
- [ ] Non-sensitive | [ ] Sensitive | [ ] Highly sensitive (PHI, PII)

**Data Volume:**
- Expected rows: [estimate]
- Storage: [estimate GB/TB]
- Processing frequency: [batch/real-time/ad-hoc]

---

## 3. Threat and Vulnerability Identification

### 3.1 Threat Sources

**Identify potential threat actors and attack vectors:**

| Threat Source | Likelihood | Impact If Realized | Examples |
|---------------|-----------|------------------|----------|
| Insider (accidental data mishandling) | [ ] Low/Med/High | [ ] Low/Med/High | Query logs exposed, overly broad role assignment |
| Insider (malicious) | [ ] Low/Med/High | [ ] Low/Med/High | Unauthorized data export, privilege escalation |
| External (unauthorized access) | [ ] Low/Med/High | [ ] Low/Med/High | Compromised credentials, network breach |
| System failure (data loss, outage) | [ ] Low/Med/High | [ ] Low/Med/High | Unplanned downtime, corruption |
| Compliance violation | [ ] Low/Med/High | [ ] Low/Med/High | Sharing with unauthorized recipients, retention breach |

### 3.2 Vulnerability Assessment

**Security Control Gap Analysis:**

For each HIPAA safeguard category below, assess the feature's implementation:

#### Administrative Safeguards (45 CFR § 164.308)

| Control | Required? | Implemented? | Evidence | Gap/Risk |
|---------|-----------|-------------|----------|----------|
| Security Management Process | Yes | [ ] Yes/No | [e.g., feature reviewed per TRB charter] | [describe gap] |
| Workforce Security | Yes | [ ] Yes/No | [e.g., role-based access per UC permissions] | |
| Information Access Management | Yes | [ ] Yes/No | [e.g., row-level filtering by user identity] | |
| Security Awareness & Training | Yes | [ ] Yes/No | [e.g., user training required before access] | |
| Security Incident Procedures | Yes | [ ] Yes/No | [e.g., breach response plan includes this feature] | |
| Contingency Planning | Yes | [ ] Yes/No | [e.g., disaster recovery SLA defined] | |
| Business Associate Agreements | Conditional | [ ] Yes/No | [e.g., Databricks BAA in place] | |

#### Technical Safeguards (45 CFR § 164.312)

| Control | Required? | Implemented? | Evidence | Gap/Risk |
|---------|-----------|-------------|----------|----------|
| Access Control (authentication) | Yes | [ ] Yes/No | [e.g., Databricks SSO + MFA enforced] | |
| Access Control (authorization) | Yes | [ ] Yes/No | [e.g., UC permission model + row/column masks] | |
| Audit Controls & Logging | Yes | [ ] Yes/No | [e.g., query audit logs retained 90+ days] | |
| Integrity Controls | Yes | [ ] Yes/No | [e.g., change tracking, immutable logs] | |
| Transmission Security | Yes | [ ] Yes/No | [e.g., TLS 1.2+ for all data transfers] | |
| Encryption | Addressable | [ ] Yes/No | [e.g., encryption at rest via AWS KMS] | |

#### Physical Safeguards (45 CFR § 164.314)

| Control | Required? | Implemented? | Evidence | Gap/Risk |
|---------|-----------|-------------|----------|----------|
| Facility Access Controls | Yes | [ ] Yes/No | [inherited from AWS data centers] | |
| Workstation Security | Yes | [ ] Yes/No | [e.g., only from corporate network] | |
| Device & Media Controls | Yes | [ ] Yes/No | [e.g., no data export to personal devices] | |

---

## 4. Risk Analysis

### 4.1 Risk Level Calculation

For each identified threat-vulnerability pair, calculate risk:

**Risk = Likelihood × Impact**

| # | Threat | Vulnerability | Likelihood (1-5) | Impact (1-5) | Risk Score | Mitigation |
|---|--------|--------------|-----------------|-------------|-----------|-----------|
| 1 | [Threat name] | [Gap description] | [1-5] | [1-5] | [L×I] | [control/process] |
| 2 | | | | | | |
| 3 | | | | | | |

### 4.2 Risk Acceptance Criteria

- **Low (score 1-3):** Accept; monitor  
- **Moderate (4-9):** Mitigate via conditions or controls; re-assess  
- **High (10-20):** Reject or require major conditions; executive approval needed  
- **Critical (>20):** Reject; feature may not be usable in current form  

---

## 5. Findings & Conditions

### 5.1 Critical Findings

**[If any]**
- Finding: [Description]  
  Mitigation: [Required remediation]  
  Responsibility: [Requestor / Databricks / Acme IT]  
  Target Date: [YYYY-MM-DD]  

### 5.2 Conditions for Approval

(Link to Decision Record with COND-IDs)

| Condition ID | Requirement | Verification Method | Responsibility | Deadline |
|--------------|-------------|-------------------|-----------------|----------|
| COND-XXX-1 | [e.g., Enable query audit logging] | [e.g., TRB audits system tables] | [Requestor] | [Date] |
| COND-XXX-2 | [e.g., Require PHI data masking] | [e.g., TRB spot-checks queries] | [Databricks support] | [Date] |

---

## 6. Residual Risk Statement

**After mitigation controls and conditions, what risk remains?**

[Narrative: e.g., "Residual risk is low if requestor adheres to conditions. Greatest risk is user error (e.g., accidentally querying full SSN column). Mitigated by column mask enforcement and annual user training. Monitored via query audit logs for anomalies."]

---

## 7. Recommendations

- [ ] **Approve** – Risk within tolerance; conditions satisfied  
- [ ] **Approve with Conditions** – Conditions required; see Section 5.2  
- [ ] **Reject** – Risk exceeds organizational tolerance; resubmit if Databricks releases mitigations  
- [ ] **Deferred** – Request additional information (see below)  

**Additional Information Needed (if Deferred):**

---

## 8. Compliance & Audit Notes

**For Knowledge Assistant Retrieval:**
- This assessment used NIST 800-30 risk methodology with HIPAA Security Rule criteria.
- Data sensitivity: [PHI / Internal / etc.]
- Inheritance model: [Databricks controls] + [Acme controls] = [Shared responsibility].
- Audit trail: Query logs, system tables, and change history retained per policy [Ref].

---

**Assessment Completed By:**  
[Enterprise Architect / Privacy Officer] — [Title]  
Signature: _________________ Date: [YYYY-MM-DD]

**Reviewed By:**  
[CISO or CPO] — [Title]  
Signature: _________________ Date: [YYYY-MM-DD]

---

**Classification:** Internal – Synthetic Sample
