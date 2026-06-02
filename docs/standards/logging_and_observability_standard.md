# Logging & Observability Standard

**Status:** Active  
**Governing ADRs:** ADR-003 (Authority of Declarations), ADR-005 (Testing), ADR-008 (Observability and Explicit Failure)  

---

## 1. Purpose

This document defines operational standards for:

- Logging behavior
- Log levels
- Error propagation patterns
- Alerting and observability expectations

This standard operationalizes:

> Structural failures must be raised explicitly and logged persistently. (ADR-008)

It does not redefine architectural principles.

---

## 2. Core Principles

### 2.1 Fail Loud and Persist

- Structural failures must:
  - be logged at `ERROR` or higher
  - be raised as exceptions
- Logging is not a substitute for raising.
- Raising is not a substitute for logging.

Silent degradation is prohibited.

---

### 2.2 Logs Must Support Understanding

Logs must:
- provide sufficient context to reconstruct state
- include relevant identifiers (pipeline stage, GID batch, ensemble name, etc.)
- avoid ambiguity

Logs must not:
- rely on implicit assumptions
- require tribal knowledge to interpret

---

### 2.3 Logs Must Not Leak Sensitive Data

- API keys (Appwrite credentials) must never be logged.
- Environment variable values must not be logged directly.
- File paths are acceptable; credentials are not.

---

## 3. Log Levels (Normative Definitions)

### DEBUG
- Development diagnostics.
- Spatial overlap calculations for individual cells.
- Cache hit/miss details.
- Must not be required to understand production failures.

### INFO
- High-level lifecycle events.
- Pipeline stage transitions (read/transform/validate/save).
- Batch progress (e.g., "Processing batch 5/12").
- Configuration summaries at startup.

### WARNING
- Unexpected but recoverable conditions.
- Invalid geometries in shapefiles (logged, skipped).
- Cache directory creation.
- Must not mask structural errors.

Warnings must not be used to hide invariant violations.

### ERROR
- Structural failure within a component.
- Missing required columns after enrichment.
- Appwrite upload failure.
- Must be raised and logged.

### CRITICAL
- System-wide failure.
- Shapefile loading failure blocking all spatial operations.
- Complete inability to connect to Appwrite.
- Immediate attention required.

---

## 4. Error Propagation Pattern

Structural errors must follow this minimal pattern:

1. Construct a clear, descriptive error message.
2. Log the error (`ERROR` or `CRITICAL`).
3. Raise the appropriate exception with the same message.

Example:

```python
err_msg = f"Required metadata column missing: {col}. Found columns: {df.columns.tolist()}"
logger.error(err_msg)
raise ValueError(err_msg)
```

Clarity and consistency are required.

---

## 5. Logging Scope Expectations

### 5.1 Required Logging

The following must be logged:

* Pipeline stage transitions (read, transform, validate, save)
* Data source connections (Appwrite, ViewsER)
* Batch processing progress
* Spatial mapping initialization (shapefile loading)
* All structural failures

### 5.2 Optional Logging

* Individual cell overlap calculations (DEBUG)
* Cache statistics (DEBUG/INFO)
* DataFrame shape at each stage (INFO)

---

## 6. Log Structure and Context

Log entries should include:

* Timestamp
* Level
* Module or component name
* Relevant identifiers (batch number, GID range, ensemble name)

Structured logging (JSON or key-value format) is recommended where possible.

---

## 7. Alerting

Alerting is an operational layer built on logging.

At minimum:

* `ERROR` and `CRITICAL` logs must be alertable.
* `CRITICAL` logs must escalate.
* Alert routing must avoid noise amplification.

Alert configuration is operational and may evolve.

---

## 8. Testing Requirements

Logging behavior must be testable where meaningful.

Tests should verify:

* Errors are both logged and raised.
* Log level separation works as expected.
* Sensitive data is never logged.

Logging tests must not rely on manual inspection.

---

## 9. Anti-Patterns (Prohibited)

* Swallowing exceptions without logging
* Logging and continuing after invariant violation
* Downgrading errors to warnings to "keep things running"
* Using `print()` for structural diagnostics
* Logging entire DataFrames without context
* `warnings.filterwarnings("ignore")` for structural issues

---

## 10. Evolution

This document may evolve independently of ADRs.

If logging semantics change in a way that affects system meaning,
ADR-008 must be revisited.
