# Authenticity Validator for Academia — Project Report Source

**Source material for the B.Tech final-year project report (The NorthCap University format).**

Every statement in this file was taken from the code in this repository as it
stands. Where the project specification (`CLAUDE.md`) names something that the
code does not contain, that is said explicitly as **Not found in project**
rather than described as if it existed.

Repository scanned: `backend/` (Python 3.12 / FastAPI), `frontend/` (React +
TypeScript), `db/`, `samples/`, `keys/`, `docker-compose.yml`, Alembic
migrations and the full `backend/tests/` suite. Generated directories
(`node_modules`, `__pycache__`, `.git`, `dist`) were excluded.

Measured size of the codebase:

| Part | Files | Lines |
|---|---|---|
| Backend application (`backend/app`) | 60 Python files | 6,699 |
| Backend tests (`backend/tests`) | 19 Python files | 5,390 |
| Frontend source (`frontend/src`) | 48 TS/TSX files | 7,698 (of which `api/schema.ts` is 2,454 generated lines) |
| Alembic migrations | 6 revisions | — |
| Backend test functions | — | 308 (expanding to **373** collected test cases, since some are parametrised) |

---

# PART A: FRONT MATTER INFORMATION

## A.1 Project title

**Suggested academic title:**

> **An Explainable Cryptographic Framework for Academic Credential
> Verification using Ed25519 Digital Signatures, Signed QR Codes and
> Confidence-Banded Optical Character Recognition**

Shorter alternatives, should the department prefer a less technical title:

1. *Authenticity Validator for Academia: A Web Platform for Explainable Verification of Academic Certificates*
2. *Design and Implementation of a Tamper-Evident Academic Credential Verification System using Digital Signatures and OCR*
3. *An Evidence-Based Approach to Degree Certificate Verification with Per-Check Explainability*

The title registered inside the application itself is
**"Authenticity Validator for Academia"** (`backend/app/main.py`,
`FastAPI(title=...)`, and `frontend/index.html`). The problem statement
reference in `CLAUDE.md` is **SIH25029**.

## A.2 Abstract draft (≈270 words)

Fraudulent academic credentials undermine the value of genuine degrees and
impose a slow, manual verification burden on employers, universities and
government agencies. Existing verification is largely a human process — a
letter or telephone call to a registrar — which does not scale and leaves no
auditable record. This project presents the *Authenticity Validator for
Academia*, a prototype web platform that allows issuing institutions to
register credentials and allows verifiers to check them in three ways: by
certificate number, by the signed QR code printed on the document, or by
uploading a photograph, scan or PDF of the certificate.

The system's foundation is cryptographic rather than statistical. Each
institution holds an Ed25519 key pair; on issuance, a canonical JSON
representation of the nine identifying fields of a certificate is signed, and
the signature is embedded both in the registry row and in a compact QR payload
(`AVA1|<number>|<code>|<signature>`) printed on the generated PDF. Verification
re-derives the canonical bytes and re-checks the signature, so any alteration
of the stored record or of the QR is detected mathematically.

For documents presented as images, a QR-first pipeline decodes the signature
from the original pixels using a two-reader, three-scale ladder (zxing-cpp then
pyzbar), then masks the code and reads the printed text with Tesseract 5 behind
an abstract `OcrEngine` interface. Each extracted field is compared against the
registry within three confidence bands, so a value the reader was sure of can
raise a conflict, a value it was moderately sure of blocks a "verified" verdict
and requests human review, and a value it could not read blocks nothing and is
reported honestly as unread.

Every verification yields one of four statuses — `VERIFIED`, `MISMATCH`,
`REVOKED`, `MANUAL_REVIEW` — never "fake" or "forged", together with the full
list of individual checks that produced it. A verification-request workflow
lets a verifier escalate an unsettled result to the issuing institution, and an
append-only audit log records every state change. All data in the prototype is
synthetic.

### Keywords

1. Academic credential verification
2. Ed25519 digital signature
3. Signed QR code
4. Optical Character Recognition (OCR)
5. Explainable verification / per-check evidence
6. Tamper detection
7. Confidence-banded field matching
8. Role-based access control (RBAC)

## A.3 List of tables

| Table no. | Caption |
|---|---|
| Table 3.1 | Functional requirements, mapped to the implementing module |
| Table 3.2 | Non-functional requirements and how the code addresses each |
| Table 3.3 | Hardware requirements (development and deployment) |
| Table 3.4 | Backend software dependencies with pinned versions |
| Table 3.5 | Frontend software dependencies with pinned versions |
| Table 3.6 | System packages installed in the backend container image |
| Table 3.7 | Actors and their permitted operations |
| Table 3.8 | Use-case summary (ID, actor, precondition, outcome) |
| Table 4.1 | Docker Compose services and their responsibilities |
| Table 4.2 | Database table `institutions` — column definitions |
| Table 4.3 | Database table `users` — column definitions |
| Table 4.4 | Database table `certificates` — column definitions |
| Table 4.5 | Database table `verifications` — column definitions |
| Table 4.6 | Database table `uploads` — column definitions |
| Table 4.7 | Database table `review_cases` — column definitions |
| Table 4.8 | Database table `review_messages` — column definitions |
| Table 4.9 | Database table `audit_log` — column definitions |
| Table 4.10 | Alembic migration history |
| Table 4.11 | Backend folder and file inventory with purpose |
| Table 4.12 | Frontend folder and file inventory with purpose |
| Table 4.13 | The six verification checks and their possible statuses |
| Table 4.14 | Decision rules of the verification engine, in priority order |
| Table 4.15 | Confidence bands for field comparison |
| Table 4.16 | Field normalization rules by data type |
| Table 4.17 | OCR template rules (`nbit.yaml`) — anchors and patterns |
| Table 4.18 | QR reader ladder — measured decode performance |
| Table 4.19 | Complete REST API endpoint reference |
| Table 4.20 | Audit log action vocabulary |
| Table 4.21 | Frontend routes, guards and purpose |
| Table 4.22 | Error codes returned by the API |
| Table 4.23 | Review case state transitions |
| Table 5.1 | Test file inventory with test counts |
| Table 5.2 | Representative test cases (ID, input, expected, actual, status) |
| Table 5.3 | Known defects and open issues |
| Table 5.4 | Environment variables (`.env.example`) |
| Table 6.1 | Measured verification results on `samples/photos` |
| Table 6.2 | Observed latency per verification path |
| Table 7.1 | Future enhancements mapped to the current code |

## A.4 List of figures and diagrams

All diagrams below are supplied as Mermaid source in Chapter 4 and can be
rendered directly, or redrawn in Visio/draw.io for the printed report.

| Figure no. | Caption |
|---|---|
| Figure 4.1 | Overall system architecture (containers, services and data stores) |
| Figure 4.2 | Layered software architecture of the backend |
| Figure 4.3 | Data Flow Diagram — Level 0 (context diagram) |
| Figure 4.4 | Data Flow Diagram — Level 1 (processes and data stores) |
| Figure 4.5 | DFD Level 2 — the upload verification pipeline |
| Figure 4.6 | Use-case diagram (three actors) |
| Figure 4.7 | Class diagram — domain model and verification engine |
| Figure 4.8 | Entity-Relationship diagram of the database |
| Figure 4.9 | Sequence diagram — issuing a certificate |
| Figure 4.10 | Sequence diagram — verification by certificate number |
| Figure 4.11 | Sequence diagram — verification by document upload (asynchronous job) |
| Figure 4.12 | Sequence diagram — verification request between verifier and institution |
| Figure 4.13 | Flowchart — the verification decision rules |
| Figure 4.14 | Flowchart — QR decode ladder (two readers, three scales) |
| Figure 4.15 | Flowchart — image preprocessing pipeline (`prepare()`) |
| Figure 4.16 | State diagram — certificate lifecycle (`active` → `revoked`) |
| Figure 4.17 | State diagram — review case lifecycle |
| Figure 4.18 | Activity diagram — CSV bulk import (all-or-nothing validation) |
| Figure 4.19 | Canonical record and signature construction |
| Figure 4.20 | Layout of the issued certificate PDF (field positions) |
| Figure 4.21 | Frontend route tree with role guards |
| Figure 4.22 | Screen flow / navigation map by role |
| Figure 4.23 | Authentication and token-refresh flow |
| Figure 5.1 | Test pyramid as implemented (pure unit → service → API → end-to-end) |
| Figure 6.1 | Verification outcome distribution on the 12-photo evaluation set |

### Screenshot placeholders required (to be captured for the report)

| Figure no. | Caption |
|---|---|
| Figure 6.2 | Login screen |
| Figure 6.3 | Administrator dashboard with statistics cards |
| Figure 6.4 | Institution certificate registry with search |
| Figure 6.5 | "Add certificate" dialog |
| Figure 6.6 | CSV import screen showing per-row validation errors |
| Figure 6.7 | An issued certificate PDF with its signed QR code |
| Figure 6.8 | Verify screen — "Verify document" tab |
| Figure 6.9 | Result page — `VERIFIED` through file hash |
| Figure 6.10 | Result page — `VERIFIED` through the signed QR, with unread fields listed |
| Figure 6.11 | Result page — `MISMATCH` with the field-level difference box |
| Figure 6.12 | Result page — `MANUAL_REVIEW` / "Possible discrepancy" |
| Figure 6.13 | Result page — `REVOKED` |
| Figure 6.14 | "What the document says" extracted-fields table with confidence badges |
| Figure 6.15 | Verification request — institution's view with document preview |
| Figure 6.16 | "Confirm & add to registry" prefilled form |
| Figure 6.17 | Requests list (institution inbox) |
| Figure 6.18 | Administrator audit log with filters |
| Figure 6.19 | Institutions management screen with generated first password |
| Figure 6.20 | Printed / PDF-saved verification result |

## A.5 List of symbols and abbreviations

| Abbreviation | Expansion |
|---|---|
| API | Application Programming Interface |
| ARIA | Accessible Rich Internet Applications |
| AVA1 | *Authenticity Validator for Academia*, version 1 — the QR payload prefix used by this project |
| base64url | URL-safe Base64 encoding (RFC 4648 §5), used here without padding |
| BGR | Blue-Green-Red channel order, OpenCV's default image layout |
| CGPA | Cumulative Grade Point Average |
| CLAHE | Contrast Limited Adaptive Histogram Equalization (evaluated, not retained) |
| CORS | Cross-Origin Resource Sharing |
| CRUD | Create, Read, Update, Delete |
| CSV | Comma-Separated Values |
| DDL | Data Definition Language |
| DFD | Data Flow Diagram |
| DPI | Dots Per Inch |
| Ed25519 | Edwards-curve Digital Signature Algorithm over Curve25519 |
| ER / ERD | Entity-Relationship (Diagram) |
| HMR | Hot Module Replacement (Vite development feature) |
| HS256 | HMAC using SHA-256, the JWT signing algorithm used here |
| HTTP / HTTPS | HyperText Transfer Protocol (Secure) |
| JSON | JavaScript Object Notation |
| JSONB | PostgreSQL binary JSON column type |
| JWT | JSON Web Token |
| MIME | Multipurpose Internet Mail Extensions (media type) |
| OCR | Optical Character Recognition |
| OEM | OCR Engine Mode (Tesseract parameter) |
| ONNX | Open Neural Network Exchange (evaluated, not retained) |
| ORM | Object-Relational Mapping |
| Otsu | Otsu's method of automatic global image thresholding |
| PDF | Portable Document Format |
| PEM | Privacy-Enhanced Mail — the Base64 container format used for keys |
| PKCS#8 | Public-Key Cryptography Standards #8, private-key serialization |
| PNG / JPEG | Portable Network Graphics / Joint Photographic Experts Group image formats |
| PSM | Page Segmentation Mode (Tesseract parameter) |
| QR | Quick Response (two-dimensional barcode) |
| RBAC | Role-Based Access Control |
| REST | Representational State Transfer |
| RQ | Redis Queue — the Python background job library used here |
| SHA-256 | Secure Hash Algorithm, 256-bit digest |
| SPA | Single-Page Application |
| SPKI | SubjectPublicKeyInfo, the public-key PEM structure used here |
| SQL | Structured Query Language |
| SVG | Scalable Vector Graphics |
| TSV | Tab-Separated Values (Tesseract's word-level output) |
| TTL | Time To Live |
| UI / UX | User Interface / User Experience |
| UML | Unified Modeling Language |
| URL | Uniform Resource Locator |
| UTC | Coordinated Universal Time |
| UUID | Universally Unique Identifier |
| VC | Verifiable Credential (W3C standard — listed as a Tier 3 stretch goal only) |
| W3C | World Wide Web Consortium |
| WCAG | Web Content Accessibility Guidelines |
| YAML | YAML Ain't Markup Language |

### Mathematical and notational symbols

| Symbol | Meaning |
|---|---|
| *c* | Confidence of an OCR reading, 0.0 ≤ *c* ≤ 1.0 |
| *τ_conflict* | `OCR_MIN_FIELD_CONFIDENCE` = 0.85 — at or above this a differing field is a conflict |
| *τ_discrepancy* | `OCR_DISCREPANCY_CONFIDENCE` = 0.50 — at or above this a differing field is a possible discrepancy |
| *H(·)* | SHA-256 hash function |
| *Sign_k(·)* | Ed25519 signature under private key *k* |
| *Verify_K(·)* | Ed25519 verification under public key *K* |
| *canon(r)* | Canonical UTF-8 JSON byte serialization of certificate record *r* |
| ‖ | String concatenation (the `|` separator in the QR payload) |

---

# PART B: CHAPTER-WISE CONTENT

# CHAPTER 1: INTRODUCTION

## 1.1 Background and overview of the project

An academic certificate is a claim made by an institution about a person. For
that claim to be useful to a third party — an employer, a university admitting
a postgraduate student, a licensing body — the third party must be able to
confirm that the institution really made it. Today that confirmation is almost
entirely manual: the verifier photocopies the certificate, emails or posts it
to the issuing registrar, and waits. The process is slow, inconsistent between
institutions, and leaves no durable record of what was checked or when.

This project implements a working prototype of a web platform that makes that
confirmation immediate and, importantly, **explainable**. It is built around
three roles:

- An **institution** registers the credentials it issues, either one at a time
  or by bulk CSV import. On registration the platform signs a canonical
  representation of the record with the institution's own Ed25519 private key
  and generates a one-page PDF certificate carrying that signature inside a QR
  code.
- A **verifier** checks a credential in any of three ways: typing the
  certificate number, or presenting the document itself — a photograph taken on
  a phone, a scanned image, or the original PDF. The platform reads the signed
  QR code and the printed text from whatever arrives and compares both against
  the registry.
- An **administrator** manages institutions and their key pairs, and reads the
  append-only audit log and platform statistics.

The defining design choice is that the system never returns a bare verdict. The
result of every verification is one of four statuses — `VERIFIED`, `MISMATCH`,
`REVOKED` or `MANUAL_REVIEW` — accompanied by the complete list of individual
checks that produced it: whether the number was found in the registry, whether
the record is revoked, whether the signature stored with the record still
verifies, whether the QR signature verifies, whether the uploaded file's
SHA-256 matches the issued PDF byte for byte, and, field by field, whether what
is printed on the document agrees with what the institution recorded. A
verifier sees the evidence, not just the conclusion.

A second deliberate choice runs through the whole codebase: the vocabulary
never accuses. The words "fake" and "forged" appear nowhere in any result or
message, and a test (`test_no_result_ever_says_fake`,
`test_a_mismatch_still_does_not_accuse`) enforces that. Absence of evidence is
not evidence of fraud: an unknown certificate number, an unreadable
photograph, or a layout the system does not recognise all resolve to
`MANUAL_REVIEW` — a request for a human to look — and never to an allegation
against the person holding the document.

**This is a prototype.** All data in it is synthetic: the demonstration
institution is the fictional "Northbridge Institute of Technology (NBIT)", the
twenty seeded students are invented, and every generated PDF carries a diagonal
`SPECIMEN — NOT A REAL DOCUMENT` watermark and the footer "Prototype issuance —
synthetic data, not a real academic document." There is no connection to any
real university record system and no DigiLocker integration.

## 1.2 Objectives

The objectives below are taken from the scope section of the project
specification and checked against what the code actually implements.

**Primary objectives (Tier 1 — all implemented):**

1. **Provide authenticated, role-separated access.** Implement JWT
   authentication with three roles (`admin`, `institution`, `verifier`) and
   enforce authorisation on every protected route through a single reusable
   dependency. *(Implemented: `app/core/security.py`, `app/core/deps.py`,
   `require_role()`.)*
2. **Maintain an institutional credential registry.** Allow an institution to
   add a certificate individually and to bulk-import certificates from a CSV
   file with all-or-nothing validation. *(Implemented:
   `app/services/certificates.py`, `POST /certificates`,
   `POST /certificates/import`.)*
3. **Issue a cryptographically signed certificate document.** Generate a
   one-page PDF per credential containing the printed fields and a QR code that
   embeds an Ed25519 signature over the canonical record, and store the PDF's
   SHA-256 so the exact bytes can later be recognised. *(Implemented:
   `app/services/pdf_issue.py`, `app/services/signing.py`,
   `app/services/qr.py`.)*
4. **Verify a credential by number or by QR payload.** Look the record up,
   re-check every signature, and return a result.
   *(Implemented: `POST /verify/id`, `POST /verify/qr`.)*
5. **Explain every result and record it.** Return the per-check evidence with
   each result, persist it, give each result its own shareable and printable
   URL, and write an audit row for every state change. *(Implemented:
   `app/services/verification/engine.py`, `verifications.checks` JSONB column,
   `/verifications/:id`, `app/services/audit.py`.)*

**Secondary objectives (Tier 2):**

6. **Verify from an uploaded document.** Accept a PDF, PNG or JPEG, extract
   text (from the PDF text layer where present, otherwise by OCR), decode any
   signed QR code, extract the critical fields and verify — all in a background
   worker so the request returns immediately. *(Implemented:
   `POST /verify/upload`, `app/services/ocr/`, `app/workers/ocr_job.py`.)*
7. **Match fields with confidence and show a field-level difference.**
   *(Partially implemented: the three-band confidence comparison and the
   field-level difference display are complete; **fuzzy** name matching with
   `rapidfuzz` is **not** implemented — see §1.4 and §5.3.)*
8. **Check the uploaded file's SHA-256 against the issued PDF.**
   *(Implemented: the `file_hash` check.)*
9. **Provide a manual-review queue for institutions.** *(Implemented as the
   verification-request workflow: `app/services/reviews.py`, `/reviews`
   endpoints, `/requests` pages.)*
10. **Revocation and a shareable time-limited verification link.**
    *(Revocation is implemented: `POST /certificates/{id}/revoke`. The
    shareable link is **Not found in project** — only the
    `SHARE_LINK_TTL_HOURS` setting exists.)*

**Tertiary objectives (Tier 3 — stretch, none implemented):** verifier API
keys, administrator analytics beyond the current statistics endpoint, W3C
Verifiable Credential export, Hindi OCR. The Hindi Tesseract language data
(`tesseract-ocr-hin`) *is* installed in the container image in preparation, but
no code requests it.

## 1.3 Motivation and need for the project

**The problem is real and large.** Certificate fraud is widespread enough that
verification has become a standard step in recruitment and admissions, yet the
mechanics of that step have barely changed in decades. The cost falls on
everyone: institutions staff a verification desk, employers wait weeks, and
honest graduates are delayed by the suspicion created by a minority.

**Scanned-image verification alone is not trustworthy.** A natural first
instinct — upload a scan, let OCR read it, compare the text with a database —
is far weaker than it appears, and the development history recorded in this
project demonstrates why. OCR of a real phone photograph of a printed
certificate is unreliable: measured on this project's own evaluation set of 12
photographs, the certificate number and roll number were unreadable on almost
every image, and no layout template matched at all on 4 of the 12. A system
that trusted OCR alone would either reject genuine documents or accept altered
ones.

**Cryptography moves the burden off the reader.** The project's response is to
put the institution's Ed25519 signature on the document itself, inside a QR
code. A QR code carries error correction, so it survives blur, shadow, skew
and JPEG compression far better than 7-point grey printed labels; and it is
checked by arithmetic rather than by comparing characters, so there is no
threshold to tune and no ambiguity in the outcome. On the same 12 photographs,
the QR decoded 12 out of 12 times. The printed text is still read — but as a
*cross-check* on what the signature asserts, not as the primary evidence.

**A signature alone is also not enough, and this is the subtler motivation.**
A valid signature proves what the institution *issued*. It says nothing
whatever about what is printed on the paper in the verifier's hand. Someone can
take a genuine certificate, alter the printed CGPA, and the original QR code
will still verify perfectly. The project's answer is the three-band confidence
rule: a `VERIFIED` result requires that nothing on the document *differs* from
the registry, so a confidently-read difference produces `MISMATCH` even when
the signature is valid, and a moderately-read difference blocks `VERIFIED` and
asks for review. This rule was added after a measured bug in which a CGPA
printed as 9.99 and read at 76 % confidence against a registry value of 9.32
was reported as `VERIFIED` because the QR was valid.

**Explainability is a requirement, not a nicety.** A verifier who is shown only
a green tick learns nothing and can defend nothing. A verifier shown
"the QR signature matches the registry record and the public key of NBIT", "the
CGPA on the document reads 9.99 but the registry has 9.32", and "the
certificate number could not be read from the document" can act, can escalate,
and can justify the decision afterwards. This is why the checks are stored with
every verification rather than recomputed, and why there is deliberately **no
overall authenticity percentage** anywhere in the system — a document is not
80 % genuine, and a single differing CGPA matters more than six fields that
happen to agree.

**Finally, the workflow has to end somewhere human.** When the system cannot
settle a question — an unknown number, an unreadable page — the only authority
that can is the issuing institution. The verification-request feature makes
that conversation a recorded, auditable part of the system rather than an email
that disappears.

## 1.4 Scope of the project

### 1.4.1 In scope and implemented

| Area | What the code does |
|---|---|
| Authentication | Email/password login, argon2 password hashing, JWT access (15 min) and refresh (7 d) tokens, `GET /auth/me`, token refresh endpoint |
| Authorisation | Three roles enforced by a FastAPI dependency on every protected route; row-level scoping inside services |
| Institution management | Create (with automatic Ed25519 key-pair generation and a one-time generated password), list with counts, update name/active flag, delete-or-deactivate rules |
| Credential registry | Add one certificate; bulk CSV import with all-or-nothing per-row validation; paginated listing with search by number, roll number or name; fetch by ID |
| Issuance | Ed25519 signature over a canonical record; one-page A4-landscape PDF with printed fields, diagonal watermark and signed QR; SHA-256 of the PDF stored on the row; PDF written once and never regenerated |
| Revocation | Revoke with a mandatory reason; the record, signature and PDF are left untouched; verification then reports `REVOKED` |
| Verification by number | `POST /verify/id` |
| Verification by QR payload | `POST /verify/qr` (endpoint retained; no longer called by the UI) |
| Verification by document | `POST /verify/upload` → magic-byte type sniffing → stored upload → RQ background job → QR decode ladder → preprocessing → Tesseract OCR → template-driven field extraction → engine → stored verification; polled via `GET /verify/jobs/{id}` |
| Verification engine | Six checks, four result statuses, nine decision rules, three confidence bands, implemented as pure functions with no I/O |
| Result presentation | Per-check evidence list, field-by-field document-versus-registry comparison, unread-field notice, match count, own URL, print stylesheet |
| Verification requests | Verifier escalates an unsettled result to the issuing institution; message thread; `needs_info` round trip; three decisions including "confirm & add to registry"; document preview for the institution; open cases hold their upload back from retention |
| Audit | Append-only `audit_log` table protected by a PostgreSQL trigger that rejects `UPDATE` and `DELETE`; a row for every state change including login successes and failures |
| Administration | Platform statistics endpoint and dashboard cards; audit log browser with action-prefix and date-range filters |
| Housekeeping | Upload retention with a prune command (`--dry-run` supported), orphan-file detection with a one-hour grace period, PDF backfill script, idempotent seed script |

### 1.4.2 In the specification but **not found in project**

| Item | Evidence |
|---|---|
| Shareable time-limited verification link (Tier 2 item 10) | No `share_links` model, no migration, no `api/v1/share.py`. `app/api/v1/router.py` carries the comment "Remaining routers are mounted here as they land: share". Only the setting `share_link_ttl_hours` exists in `config.py`. |
| Fuzzy field matching with `rapidfuzz` (Tier 2 item 7) | `rapidfuzz==3.11.0` is in `requirements.txt` but is **never imported** anywhere in `backend/app` or `backend/tests`. `engine._compare_field` compares `student_name` and `programme` by exact equality after normalization. The settings `name_match_threshold` (90) and `name_conflict_threshold` (75) exist but are unused. Test `test_a_name_must_match_exactly_for_now` pins the current behaviour. |
| `app/services/matching.py` | Named in the specification's repo layout; the file does not exist. |
| `app/adapters/registry_local.py` and `app/adapters/digilocker_mock.py` | Named in the specification's repo layout; `app/adapters/` contains only an empty `__init__.py`. |
| Playwright end-to-end tests ("2–3 e2e flows" in the stack table) | No Playwright configuration, no `e2e/` directory, no Playwright dependency in `frontend/package.json`. End-to-end coverage is achieved at the API level in Python instead (`tests/test_upload_verification_e2e.py`). |
| `html5-qrcode` live camera scanner | Listed in the specification's stack table but removed from the project. It is absent from `frontend/package.json` and from all source. Camera capture is now an `<input type="file" capture="environment">` in `UploadDropzone.tsx`. |
| Hindi OCR (Tier 3) | The `tesseract-ocr-hin` language pack is installed in the Docker image, but no code passes `lang="hin"`; `recognise()` defaults to `"eng"` everywhere. |
| Verifier API keys, W3C VC export, ML tamper detection (Tier 3 / out of scope) | Not present, by design. |

### 1.4.3 Explicitly out of scope

The specification rules these out and the code respects all of them: a
standalone test-certificate generator (test documents are generated *inside*
the test run from the project's own issuance code and nothing is shipped),
blockchain, OAuth/social login, real DigiLocker integration, machine-learning
tamper detection, and a microservice architecture.

## 1.5 Target users and real-world applications

### 1.5.1 Target users

| User | Role in the system | What they need from it |
|---|---|---|
| University / college registrar or examination cell | `institution` | A fast way to publish issued credentials, in bulk at the end of a session; the ability to revoke a credential issued in error; a queue of verification requests to answer with the document in front of them |
| Employer HR / background-verification agency | `verifier` | An immediate answer about a certificate presented by a candidate, with evidence they can keep; a way to escalate to the institution when the answer is unclear |
| Admitting institution for higher study | `verifier` | The same, applied to transcripts presented with an application |
| Platform operator / government nodal agency | `admin` | Onboarding institutions and issuing their keys; oversight of volume and of institutions that do not answer requests; an audit trail |
| Credential holder (graduate) | *No account* | Indirect benefit: a signed QR on their own certificate that lets anyone confirm it in seconds. **Note:** the prototype has no holder-facing role; a holder cannot log in or share their own credential. The planned shareable link (§1.4.2) would have served this and is not built. |

### 1.5.2 Real-world applications

1. **Recruitment screening.** An HR team photographs a candidate's degree
   certificate with a phone and receives a result with per-check evidence in
   under two seconds, with the institution's own signature as the basis.
2. **Postgraduate and overseas admissions.** An admissions office verifies
   transcripts in bulk without correspondence, and escalates only the
   ambiguous cases.
3. **Professional licensing and public appointments.** Where statute requires a
   verified qualification, the audit log provides a durable record of what was
   checked, by whom and when.
4. **Institutional self-service.** A registrar's verification desk answers
   enquiries through the request queue instead of by letter, with the uploaded
   document visible beside its own registry record.
5. **Correcting the registry.** The "Confirm & add to registry" decision turns
   a verification failure into a registry improvement: a genuine certificate
   that was never published can be added, signed and issued a PDF through the
   same code path as any other, closing the gap permanently.
6. **A reference architecture for national credential infrastructure.** The
   signing scheme, the canonical record format and the QR payload are simple,
   documented and transport-independent, and the QR carries no personal data —
   only a number, an institution code and a signature.

## 1.6 Organization of the report

**Chapter 1 — Introduction** establishes the problem, states the objectives
against what the code implements, explains the motivation (including why OCR
alone and signatures alone are each insufficient), fixes the scope and names
what was specified but not built.

**Chapter 2 — Literature Review** surveys existing credential-verification
approaches (manual verification, DigiLocker and the National Academic
Depository, blockchain credential projects, W3C Verifiable Credentials,
commercial background-verification services), gives a theoretical account of
every technology this project uses and why it was chosen over its alternatives,
compares those systems against this one, and states the research gap.

**Chapter 3 — Problem Definition and Requirement Analysis** states the problem
formally, enumerates every functional requirement traced to its implementing
module, lists the non-functional requirements with the code that addresses
each, specifies hardware and software with pinned versions, assesses technical,
economic and operational feasibility, and catalogues the actors and use cases.

**Chapter 4 — Design and Implementation** is the core of the report. It
presents the system architecture, data flow diagrams at three levels, the UML
diagrams (use case, class, sequence, ER, state, activity), the complete
database design, a file-by-file inventory of the repository, a module-by-module
walk-through of the implementation with code extracts, the algorithms in
step-by-step form, the full API reference, every UI screen with its user flow,
and the security, validation and error-handling design.

**Chapter 5 — Testing and Deployment** describes the four-level testing
strategy and the 308 tests that implement it, tabulates representative test
cases, documents the known defects honestly (including one deliberately
unfixed), and gives the deployment, installation and environment-variable
procedure.

**Chapter 6 — Analysis and Results** describes the working output of each
feature screen by screen, reports the measured performance figures recorded in
the project, discusses what the results mean, and lists the advantages and the
limitations.

**Chapter 7 — Conclusion and Future Enhancements** summarises what was
achieved and proposes enhancements grounded in the present code, each with the
file it would touch.

**Chapter 8 — References** lists every framework, library, specification and
documentation source in IEEE style.

**Chapter 9 — Appendices** carries the important full code listings, the
configuration files, sample inputs and outputs, and the screenshot
placeholders.

---

# CHAPTER 2: LITERATURE REVIEW

## 2.1 Existing systems and similar applications

### 2.1.1 Manual verification by correspondence

The prevailing method. The verifier sends a copy of the certificate to the
issuing institution's examination cell and waits for a letter, email or
telephone confirmation.

*Strengths:* the answer comes from the only authoritative source, and the
institution can apply judgement to an unusual case.
*Weaknesses:* latency of days to weeks; no standard format; no audit trail;
cost scales linearly with volume; vulnerable to impersonation of the registrar
in both directions; and the verifier has no way to check anything themselves.

This project does not try to remove the institution from the loop — the
verification-request feature deliberately preserves it — but it removes the
institution from the *common* case, where a signature settles the question
immediately.

### 2.1.2 DigiLocker and the National Academic Depository (NAD), India

Government-backed digital repositories in which issuers deposit credentials and
holders access them from a government-authenticated wallet, sharing them with
verifiers through the platform.

*Strengths:* authoritative, national in scope, legally recognised, and removes
paper entirely for credentials that are in the depository.
*Weaknesses:* only covers participating issuers and the years they have
uploaded; requires the *holder* to initiate sharing, which does not help a
verifier holding a paper certificate from 2015; and offers no mechanism for
checking a physical document presented in person.

This project's relationship to DigiLocker is explicit in the specification: a
real integration is **out of scope**, and no mock adapter exists in the code
either (§1.4.2). The system is designed for the case DigiLocker does not
address — a physical or scanned document in a verifier's hand — and would
complement rather than replace it.

### 2.1.3 Blockchain-based credential platforms

A family of projects (Blockcerts and its derivatives; various university
pilots) that anchor a hash of each credential in a public blockchain, so that
the credential's existence at a point in time can be proved without trusting a
server.

*Strengths:* tamper-evidence that does not depend on the issuer remaining
online; public verifiability; immutability of the anchor.
*Weaknesses:* revocation is genuinely hard, because immutability is the point —
most schemes bolt on a mutable revocation list and thereby reintroduce the
trusted server; transaction cost and latency; key loss is unrecoverable; and
the blockchain proves only that *a hash* existed, not that the institution
stood behind the content.

The specification for this project rules blockchain **out of scope**, and the
design reflects a defensible reason: the property actually needed is *the
institution's attestation*, which an Ed25519 signature provides directly, in
microseconds, at zero cost, with revocation as a simple status change. The
trust assumption — that the institution's public key is correctly registered —
is the same assumption a blockchain-anchored system makes about the issuer's
identity.

### 2.1.4 W3C Verifiable Credentials and Decentralized Identifiers

A standards-track data model in which a credential is a JSON-LD document
carrying an issuer, a subject, claims and a cryptographic proof, resolvable
through DIDs.

*Strengths:* interoperable by design, standardised proof formats, selective
disclosure and holder-mediated presentation, a rich revocation ecosystem.
*Weaknesses:* substantial implementation complexity (JSON-LD canonicalisation,
DID method support, proof suites); heavy for a prototype; and still requires an
answer to the physical-document problem.

This project's canonical-record-plus-Ed25519 design is a deliberate
simplification along the same lines: a fixed nine-field record, sorted keys,
compact separators, one signature algorithm. W3C VC export is listed as a
**Tier 3 stretch goal and is not implemented**, but the canonical record is a
clean mapping target for one, which §7.2 notes.

### 2.1.5 Commercial background-verification services

Agencies that verify credentials on behalf of employers, combining their own
databases, institutional relationships and manual follow-up.

*Strengths:* turnkey; cover many credential types and jurisdictions; accept
legal responsibility for the result.
*Weaknesses:* opaque — the client receives a verdict, rarely the evidence;
per-check cost; latency still measured in days for anything unusual; and the
agency becomes a third party holding candidate data.

The explainability of this project is a direct response to the opacity: the
`verifications.checks` column stores the reasoning, and the result page renders
all of it.

### 2.1.6 Generic document-OCR and tamper-detection tools

Commercial and open-source pipelines that read an identity or academic document
and flag anomalies statistically (font inconsistency, compression artefacts,
copy-move detection).

*Strengths:* work on documents from issuers who have no digital infrastructure.
*Weaknesses:* probabilistic, so they produce false accusations; require
training data per layout; and are difficult to explain to the person affected.

The specification places ML-based tamper detection **out of scope**, and the
project's OCR serves a narrower, safer purpose: it cross-checks the printed
text against a record the institution has already signed, and reports what it
could not read rather than guessing.

### 2.1.7 Summary positioning

| System class | Proves issuer attestation | Works on a paper document | Explains its answer | Revocation | Implemented here |
|---|---|---|---|---|---|
| Manual correspondence | Yes | Yes | Partly | Yes | Preserved as the escalation path |
| DigiLocker / NAD | Yes | No | No | Yes | Out of scope |
| Blockchain credentials | Hash only | Via QR, usually | Rarely | Awkward | Out of scope |
| W3C VC / DID | Yes | No | Partly | Yes | Tier 3, not built |
| Background-verification agency | Indirectly | Yes | No | n/a | — |
| Document OCR + ML tamper detection | No | Yes | Poorly | n/a | Out of scope |
| **This project** | **Yes (Ed25519)** | **Yes (signed QR + OCR)** | **Yes (per-check evidence)** | **Yes (status change)** | — |

## 2.2 Technologies and concepts used — theory, rationale and mechanism

For each technology: *what it is*, *why it was chosen for this project*, and
*how it works here*.

### 2.2.1 Ed25519 digital signatures

**What it is.** Ed25519 is a digital-signature scheme using the Edwards-curve
Digital Signature Algorithm (EdDSA) over the twisted Edwards curve Curve25519.
A signer holds a 32-byte private key and publishes a 32-byte public key;
signatures are 64 bytes. It provides existential unforgeability: without the
private key it is computationally infeasible to produce a signature that
verifies for a message the signer never signed.

**Why chosen.** Four properties mattered here. (i) *Small and fixed-size
output* — a 64-byte signature becomes 86 base64url characters, which fits
comfortably in a QR code alongside the certificate number and institution code;
an RSA-2048 signature at 256 bytes would roughly quadruple the QR's data and
its physical print size. (ii) *Determinism* — Ed25519 needs no random nonce at
signing time, so a given record and key always produce the identical signature,
which makes the behaviour reproducible and testable. (iii) *No parameter
choices to get wrong* — unlike RSA or ECDSA there is no padding scheme, hash
selection or curve negotiation to misconfigure. (iv) *Speed* — verification is
sub-millisecond, which matters because this system verifies a signature twice
on every single verification (once for the stored record, once for the QR).

**How it works here.** `app/services/signing.py` builds a `CertificateRecord`
dataclass of nine fields, normalizes each of them, serialises the result to
canonical JSON, and signs those exact bytes:

```python
def canonical_dict(record: CertificateRecord) -> dict[str, str | int | None]:
    return {
        "cert_number": normalize_id(record.cert_number),
        "institution_code": normalize_id(record.institution_code),
        "student_name": normalize_text(record.student_name),
        "roll_number": normalize_id(record.roll_number),
        "programme": normalize_text(record.programme),
        "year_of_passing": normalize_year(record.year_of_passing),
        # Strings ("8.50"), not JSON floats, so the bytes never depend on float repr.
        "cgpa": format_decimal(record.cgpa),
        "marks": format_decimal(record.marks),
        "issue_date": format_date(record.issue_date),
    }

def canonical_bytes(record: CertificateRecord) -> bytes:
    return json.dumps(
        canonical_dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
```

Three details in that function are load-bearing. `sort_keys=True` and
`separators=(",", ":")` remove every degree of freedom in the serialisation, so
the signer and the verifier cannot disagree about the byte sequence. Grades are
emitted as two-decimal **strings** rather than JSON numbers, because a float's
textual representation is platform-dependent and a signature must not be. And
every value passes through the normalization functions first, so
`"  nbit2024cs0001 "` and `"NBIT-2024-CS-0001"` sign identically — a property
pinned by the test `test_equivalent_inputs_sign_the_same`.

The private key for institution `CODE` lives at `<KEYS_DIR>/CODE.pem` in
PKCS#8 PEM with mode `0600`; the matching public key is stored in the database
as SubjectPublicKeyInfo PEM in `institutions.public_key`. Verification is
failure-safe by construction — a malformed signature or a corrupt key returns
`False` rather than raising:

```python
def verify_record(public_key_pem: str, record: CertificateRecord, signature: str) -> bool:
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
        if not isinstance(public_key, Ed25519PublicKey):
            return False
        public_key.verify(_b64url_decode(signature), canonical_bytes(record))
        return True
    except (InvalidSignature, ValueError, binascii.Error, UnicodeEncodeError):
        return False
```

### 2.2.2 SHA-256 cryptographic hashing

**What it is.** A one-way function mapping arbitrary input to a fixed 256-bit
digest, with collision and preimage resistance.

**Why chosen.** Two distinct uses. First, as a *document fingerprint*: the
SHA-256 of the issued PDF is stored in `certificates.file_sha256`, so if a
verifier uploads the original file unchanged, the match is exact and
conclusive — no OCR, no thresholds, and measured at roughly 0.09 s. Second, as
a *lookup key*: a certificate can be found by the hash of the bytes uploaded.

**How it works here.** `app/services/hashing.py` provides `sha256_bytes()` and
a chunked `sha256_file()`. The crucial design consequence is that issued PDFs
are **generated once and never regenerated** — ReportLab embeds a creation
timestamp, so rebuilding a PDF would change its hash and silently invalidate
the stored value. `GET /certificates/{id}/pdf` therefore streams the stored
file, and returns `404 pdf_not_available` if the file is missing rather than
rebuilding it.

An important subtlety in the engine: a hash *mismatch* is reported as
`uncertain`, not `fail`. Printing to PDF, scanning, or re-saving all change the
bytes of a perfectly genuine document, so a difference is not evidence against
it. Only an exact match is conclusive.

### 2.2.3 JSON Web Tokens (JWT) with HS256

**What it is.** A compact, URL-safe token of three base64url segments — header,
claims, signature — that carries claims the server can validate without a
session store.

**Why chosen.** The API is stateless and the frontend is a separate
single-page application, so a bearer token is the natural fit; HS256 (HMAC with
SHA-256) is appropriate because a single service both issues and validates the
tokens, making asymmetric signing unnecessary complexity.

**How it works here.** `app/core/security.py` issues two token types carrying
`sub` (user id), `role`, `type` and `exp`. Access tokens live 15 minutes,
refresh tokens 7 days. Decoding requires the `sub`, `type` and `exp` claims to
be present and checks that the token type is the expected one, so a refresh
token cannot be used as an access token — a distinction tested by
`test_me_rejects_refresh_token` and `test_refresh_rejects_access_token`.

**Documented limitation.** Refresh tokens are **not stored server-side**, so
logging out only clears them in the browser and a stolen refresh token stays
valid until it expires. Deactivating a user blocks both token types
immediately, because every request re-loads the user and checks `is_active`.
Tokens are kept in `localStorage`, which is explicitly a prototype choice;
production would move the refresh token to an `httpOnly` cookie. Both decisions
are recorded as such in the project's decision log.

### 2.2.4 Argon2 password hashing

**What it is.** The winner of the 2015 Password Hashing Competition: a
memory-hard key-derivation function with tunable time, memory and parallelism
cost.

**Why chosen.** Memory-hardness is what distinguishes it from bcrypt and
PBKDF2 — it resists GPU and ASIC acceleration, because the attacker must
provide memory bandwidth as well as compute.

**How it works here.** `passlib`'s `CryptContext(schemes=["argon2"])` hashes on
user creation and verifies on login. Two defensive details: `verify_password`
catches `ValueError` and returns `False` rather than raising on a malformed
stored hash; and `authenticate()` verifies the supplied password against a
module-level dummy hash when the email is unknown, so the response time does
not reveal which email addresses exist.

### 2.2.5 QR codes (generation and decoding)

**What it is.** A two-dimensional matrix barcode with Reed–Solomon error
correction, specified in ISO/IEC 18004. At error-correction level M, roughly
15 % of the code's modules can be destroyed and the payload still recovers.

**Why chosen.** Error correction is the whole point. A printed certificate is
photographed at an angle, in uneven light, by a phone camera that applies lossy
compression. Grey 7-point text does not survive that; a QR code does. It is
also the only part of the page that carries a *verifiable* claim rather than a
readable one.

**How it works here.** Generation uses `qrcode` at `ERROR_CORRECT_M`, embedded
into the PDF at 34 mm square. The payload format is deliberately minimal and
carries **no personal data**:

```
AVA1|<cert_number>|<institution_code>|<signature>
```

The verifier parses it, fetches the record by number, and re-checks the
signature against the institution's public key — so the QR is a pointer plus an
attestation, not a source of truth. `parse_payload()` validates the part count,
the prefix and the base64url character set, and raises `QrPayloadError` on
anything malformed.

Decoding is the measured part of the design. `app/services/ocr/qr_scan.py`
implements a ladder of two readers at three scales, stopping at the first valid
AVA1 payload:

| Reader | 1× | 2× | 3× | Time |
|---|---|---|---|---|
| zxing-cpp | 11 / 12 | 12 / 12 | — | 1–43 ms |
| pyzbar | 2 / 12 | 10 / 12 | never read sample3 | 12–242 ms |

zxing-cpp therefore runs first; pyzbar is retained as a fallback because the
two libraries do not fail on the same images and pyzbar was already a
dependency. Upscaling is by cubic interpolation, which adds no information but
gives the binariser and the perspective-correction step more pixels per module;
an upscale that would exceed 40 megapixels is skipped as pointless. The ladder
stops at an *AVA1* payload rather than at any barcode, because a page may also
carry a library sticker or printer barcode.

### 2.2.6 Optical Character Recognition — Tesseract 5

**What it is.** An open-source OCR engine; since version 4 its recogniser is an
LSTM neural network operating on text lines, with a legacy pattern-matching
engine retained for compatibility.

**Why chosen — and the measured reasoning.** The alternative considered was
PaddleOCR, and it was rejected on dependency grounds after measurement, not by
assumption: `paddleocr==3.0.0` cannot install on Python 3.12 at all (its
`paddlex` dependency caps `pandas<=1.5.3`, which publishes no cp312 wheel);
`paddleocr==3.0.3` adds **109** packages including LangChain, the OpenAI SDK
and tiktoken; `paddleocr==3.7.0` adds **55** and pulls in
`opencv-contrib-python`, the GUI-linked build that would shadow the headless
OpenCV this project installs. Tesseract adds **three** packages
(`pytesseract`, `opencv-python-headless`, `numpy`). Against the project's
stated constraint of keeping the dependency list small, and given that the
corpus is this project's own cleanly-rendered certificates, Tesseract wins.

**How it works here.** `TesseractEngine` runs with `--oem 3 --psm 6`. PSM 6
assumes a single uniform block of text, which suits a certificate's
label-above-value layout markedly better than the default PSM 3. Output is
taken at word level via `image_to_data`, then grouped into lines by Tesseract's
own `(block_num, par_num, line_num)` triple. A line's confidence is the **mean
of its scored words**, so an uncertain line scores *itself* down rather than
dragging the page average with it — and that per-line confidence is what
reaches the engine's confidence bands.

### 2.2.7 The `OcrEngine` abstraction (Strategy pattern)

**What it is.** A `typing.Protocol` defining the two operations the pipeline
needs from any recogniser.

**Why chosen.** To keep the recogniser replaceable without touching the
pipeline — the engine was expected to change, and it did.

**How it works here.**

```python
@runtime_checkable
class OcrEngine(Protocol):
    name: str
    def is_available(self) -> bool: ...
    def recognise(self, image: np.ndarray, *, lang: str = "eng") -> list[OcrLine]: ...
```

`extract_text.py` depends only on this protocol and on `OcrLine`, never on
`pytesseract`. The abstraction was tested for real: during development a
PP-OCRv5 ONNX engine was added and later reverted, and adding it touched only
`engines.py` — which is exactly the claim the design made.

### 2.2.8 Image preprocessing with OpenCV

**What it is.** Classical (non-learned) image operations: colour conversion,
non-local-means denoising, perspective rectification, rotation, thresholding,
interpolation.

**Why chosen.** Each step raises recognition accuracy on *some* inputs and can
damage *others*, so they are written as separate pure functions over numpy
arrays — individually testable and individually skippable.

**How it works here.** `prepare()` applies a fixed order, and the order is the
design:

```python
def prepare(image: np.ndarray, *, binarise: bool = True) -> np.ndarray:
    flattened, _ = correct_perspective(image)
    gray = to_grayscale(flattened)
    cleaned = denoise(gray)
    unwatermarked = suppress_light(cleaned)
    straightened, _ = deskew(unwatermarked)
    enlarged = upscale_if_small(straightened)
    return threshold(enlarged) if binarise else enlarged
```

Perspective first, while the page outline is still findable; deskew next, to
remove residual rotation; thresholding **last**, so the earlier steps operate
on continuous tones rather than on hard black and white. Each step carries a
guard rail: deskew refuses corrections beyond 15° (a larger estimate means the
angle finder locked onto something that is not a text baseline) and ignores
anything below 0.1°; perspective correction requires a detected quadrilateral
covering at least 35 % of the frame, and rejects one covering more than 98 %
because that is the image border rather than a page inside a photograph;
rotation fills new canvas area with **white**, since black padding would read
as a giant glyph.

Two steps exist for reasons specific to this project's own document.
`suppress_light()` flattens pixels at or above grey 205 to pure white, which
removes the diagonal `SPECIMEN` watermark that Otsu would otherwise keep and
that OCR then reads as words overlapping real fields (`"NBIT2024CS0001 rat a"`).
`mask_regions()` paints the QR code white before OCR, because the code sits in
the same horizontal band as the boxed fields and page-level segmentation reads
its modules as glyphs on those baselines — masking it took mean line confidence
from 0.77 to 0.92 and fixed every field, and costs nothing because the payload
is decoded separately beforehand.

### 2.2.9 Template-driven, label-anchored field extraction

**What it is.** Rather than training a layout model, each known certificate
layout is described declaratively in YAML, with two kinds of rule: an *anchor*
(a label whose value is on the next line or the same line) and a *pattern* (a
regular expression whose first capture group is the value).

**Why chosen.** Three reasons. It needs no training data. A new layout is a new
YAML file, not a code change. And — most importantly — an unrecognised layout
can yield *nothing*, which is the honest outcome; guessing fields from a layout
the system does not know would convert "unreadable" into "mismatch".

**How it works here.** `templates/nbit.yaml` declares the markers that must
appear for the template to apply (`DEGREE CERTIFICATE` plus at least one of
`Institution code`, `CERTIFICATE NUMBER`, `This is to certify that`) and a rule
per field. Two rules are shaped by measured OCR behaviour: `issue_date` is
found by the pattern `([0-9]{4}-[0-9]{2}-[0-9]{2})` rather than by its label,
because OCR reflows the page so the line after `DATE OF ISSUE` is the QR's
"Scan to verify" caption — and the ISO date is the only `YYYY-MM-DD` on the
page anyway; and the grade patterns use `\s*` rather than `\s+` because
Tesseract routinely reads the label and value as one word, `CGPA8.72`.

The `id` normalizer takes only the **first whitespace token** of its line,
because OCR of this project's own certificates pulls the diagonal watermark
onto the same line and an identifier never contains a space.

### 2.2.10 Normalization and OCR-confusable collapsing

**What it is.** Canonicalising values so that equivalent inputs compare equal:
trimming, collapsing internal whitespace, upper-casing, stripping punctuation
from identifiers, fixing decimal precision, and — separately — tolerating the
character pairs OCR habitually confuses.

**Why chosen.** Both sides of every comparison must land in the same form.
When they did not, every name and programme conflicted and genuine degraded
scans were reported as `MISMATCH`.

**How it works here — and the instructive mistake.** The first attempt
*rewrote* OCR output to fix confusions, and it corrupted a **correct** reading
of `NBIT2024CS0001` into `N81T2024C50001`. The pairs are ambiguous in both
directions, so rewriting one side cannot be safe. The fix was to collapse both
sides only at comparison time:

```python
_CONFUSABLES = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "S": "5", "B": "8"})

def collapse_confusables(value: str) -> str:
    return normalize_id(value).translate(_CONFUSABLES)

def ids_match(left: str, right: str) -> bool:
    return collapse_confusables(left) == collapse_confusables(right)
```

The set was deliberately **not** widened to C/0 or S/8, even though Tesseract
makes those mistakes on 11-point text, because collapsing more characters makes
genuinely different identifiers compare equal — the wrong risk for a verifier.
Those misreads are caught by the confidence bands instead.

### 2.2.11 Confidence-banded comparison (the project's central algorithm)

**What it is.** A three-band rule converting a recogniser's confidence in a
field, plus whether that field agrees with the registry, into a verdict
contribution.

**Why chosen.** Confidence is not a yes/no, and the earlier two-state treatment
produced a real bug: a CGPA printed 9.99 and read at 76 % against a registry
9.32 was reported `VERIFIED`, because 76 % was below the conflict threshold and
a valid QR carried the result. But a signature proves what the institution
*issued*, not what is printed on the paper — and "the document disagrees but we
are not sure" is the single most important thing a verifier can be told.

**How it works here.** For a field that differs from the registry:

| Confidence *c* | Interpretation | Check status | Field state | Effect on result |
|---|---|---|---|---|
| *c* ≥ 0.85 | Conflict — the reader was sure | `fail` | `differs` | `MISMATCH` |
| 0.50 ≤ *c* < 0.85 | Possible discrepancy | `uncertain` | `differs` | Blocks `VERIFIED` → `MANUAL_REVIEW` |
| *c* < 0.50 | Not a reading at all | `uncertain` | `not_read` | Blocks nothing; listed for the verifier |

A threshold value belongs to the **stricter** band (`>=`, not `>`), so a tuned
threshold means exactly what it says — pinned by
`test_the_band_edges_are_the_thresholds_not_approximations`.

The separation of `state` from `status` is the key insight: `status` is what the
check made of the evidence, `state` is what the document actually said. They
come apart precisely where it matters — a value read at 76 % that disagrees is
weak *evidence* but it unambiguously *differs*, and the verifier must be shown
that rather than a shrug. A value nobody could read differs from nothing.

### 2.2.12 FastAPI, Pydantic v2 and generated client types

**What it is.** FastAPI is an ASGI web framework that derives request
validation, response serialisation and an OpenAPI schema from Python type
hints; Pydantic v2 performs the validation.

**Why chosen.** The type hints are the single source of truth for the contract.
Because FastAPI publishes OpenAPI, the frontend's TypeScript types are
*generated* (`npm run gen:api` → `openapi-typescript` → `src/api/schema.ts`,
2,454 lines) rather than hand-written, so a backend field rename becomes a
TypeScript compile error instead of a runtime surprise.

**How it works here.** Routers stay thin and delegate to services. Validation
lives in the schemas — `CertificateFields` normalizes identifiers, cleans text,
rounds grades, and enforces cross-field rules (CGPA 0–10, marks 0–100, at least
one of the two, year between 1950 and the current year, issue date neither in
the future nor before the year of passing). Errors are uniform: services raise
`AppError(status, code, message, **extra)` and a single handler in `main.py`
renders `{"error": {"code", "message", ...}}`.

### 2.2.13 PostgreSQL 16, SQLAlchemy 2 and Alembic

**What it is.** A relational database; a Python ORM and SQL toolkit; and a
migration tool driven by the ORM's metadata.

**Why chosen.** The data is strongly relational and the integrity rules belong
in the database rather than in application code. PostgreSQL specifically, for
three features the design uses: `JSONB` columns for the evidence list and audit
metadata (schema-flexible but queryable), **partial unique indexes** for "at
most one *open* case per verification", and triggers for the append-only audit
log.

**How it works here.** Models use SQLAlchemy 2's typed `Mapped[]` declarative
style with synchronous sessions over `psycopg` 3. Invariants are expressed as
`CheckConstraint`s so they hold regardless of which code path writes:

- `users`: role ∈ {admin, institution, verifier}, and
  `(role = 'institution') = (institution_id IS NOT NULL)` — institution users
  must belong to an institution and others must not.
- `certificates`: status ∈ {active, revoked}; at least one of CGPA or marks;
  and `(status = 'revoked') = (revoked_at IS NOT NULL)`.
- `review_cases`: status and decision vocabularies, plus
  `(status = 'closed') = (decision IS NOT NULL)`.

The append-only guarantee is a database trigger, not a convention:

```sql
CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION USING MESSAGE = 'audit_log is append-only (' || TG_OP || ' not allowed)';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
```

The same DDL is attached to an `after_create` event on the table, so tests
using `create_all` get the trigger too — and
`test_audit_log_rejects_update_and_delete` proves it fires.

### 2.2.14 Redis and RQ background jobs

**What it is.** Redis is an in-memory data store; RQ (Redis Queue) is a
lightweight Python job queue built on it.

**Why chosen.** OCR of a photograph takes seconds — too long to hold an HTTP
request. RQ rather than Celery because the project needs exactly one queue and
one job type, and RQ's API is small enough to read in full.

**How it works here.** `POST /verify/upload` stores the file, **commits**, then
enqueues — in that order, because the worker looks the upload up by id from a
different connection and the row must be visible. It returns `202 Accepted`
with a `job_id`, which the frontend polls. The job returns the verification id
and nothing else; the worker opens its own session because the enqueuing
request is long gone.

Two deliberate safety properties: an unmapped RQ status is reported as
`failed` rather than as still-running, so a client can never poll for ever; and
job ownership is held in the job's `meta` and checked on every poll, so another
verifier's job returns `404` identically to an unknown one, meaning job ids
cannot be probed.

### 2.2.15 PyMuPDF and ReportLab

**PyMuPDF (`fitz`)** reads PDFs. Its `get_text("dict")` output already groups
spans into lines in reading order, which is exactly the structure
label-anchored extraction needs. It also renders pages to pixmaps at 300 DPI
when a PDF turns out to have no usable text layer, and extracts embedded images
so the QR can be decoded at the resolution it was issued at rather than from a
re-rasterised page. The text-layer path is preferred and is tried first: it is
exact, needs no preprocessing, carries confidence 1.0, and runs in about
0.09 s. A page with fewer than 120 characters of embedded text is treated as
image-only, because a scanned PDF often carries a few stray characters from the
scanner's own stamp and that is not a text layer.

**ReportLab** writes the issued PDF: A4 landscape, a diagonal `SPECIMEN`
watermark at grey 0.88, a double border, centred institution name and student
name, boxed label-above-value fields at the lower left, the QR at 34 mm bottom
right with a "Scan to verify" caption, and a footer declaring the document
synthetic. Writing is atomic — temp file then `os.replace` — so a reader never
sees a half-written file.

### 2.2.16 React 18, Vite, TypeScript, Tailwind CSS and shadcn/ui

**React with TypeScript** for the single-page application; **Vite** as the dev
server and bundler; **Tailwind CSS** for utility-first styling; **shadcn/ui**
components built on Radix UI primitives for accessible dialogs, tabs, tables
and toasts. Routing is React Router 7. The verify route is lazy-loaded with
`React.lazy` + `Suspense` so a route only verifiers reach stays out of the main
bundle.

### 2.2.17 TanStack Query as the only state manager

**What it is.** A library that treats server data as a cache with keys,
staleness, background refetching and mutation invalidation — rather than as
application state to be copied into a store.

**Why chosen.** Almost all state in this application *is* server state. Adding
Redux or Zustand would mean maintaining a second copy of the database in the
browser and keeping it synchronised by hand.

**How it works here.** Every server interaction is a hook in `src/hooks/`
(`useAuth`, `useVerify`, `useCertificates`, `useReviews`, `useAdmin`,
`useInstitutions`). Mutations invalidate the query keys they affect. Two
non-obvious uses: `useUploadJob` returns `false` from `refetchInterval` once
the job settles, which stops polling rather than leaving a timer running; and
`useReviewDocument` fetches the uploaded document through axios as a blob and
hands the component an object URL, because the endpoint requires a bearer token
and a browser sends no `Authorization` header for an `<img src>` or `<iframe
src>` — revoking the URL on unmount so a long-lived tab does not accumulate
copies of the file.

### 2.2.18 Docker Compose

Five services — `api`, `worker`, `db`, `redis`, `web` — with health checks and
dependency ordering, two named volumes for Postgres and Redis data, one for
uploads and one for the web container's `node_modules`. The backend image
deliberately installs `libzbar0`, `tesseract-ocr`, `tesseract-ocr-hin` and
`libglib2.0-0` but **not** `libgl1`: only the headless OpenCV build is used and
it does not link libGL, so installing libGL would serve only
`opencv-contrib-python`, which nothing is allowed to pull in.

## 2.3 Comparison of existing systems versus this project

### 2.3.1 Feature comparison

| Capability | Manual | DigiLocker / NAD | Blockchain certs | W3C VC | OCR + ML tamper tools | **This project** |
|---|---|---|---|---|---|---|
| Verify a physical/paper certificate | Yes | No | Via printed QR | Rarely | Yes | **Yes** |
| Issuer's cryptographic attestation | No | Platform-mediated | Hash anchor | Yes | No | **Yes (Ed25519)** |
| Works offline from the document alone | No | No | Partly | Partly | Yes | Partly (QR carries the signature; registry lookup still needed) |
| Per-check evidence shown to the verifier | Partly | No | No | Partly | No | **Yes (6 checks, stored)** |
| Field-level document-vs-record difference | Manual | n/a | No | No | Statistical | **Yes, with confidence bands** |
| Honest reporting of what could not be read | n/a | n/a | n/a | n/a | Rarely | **Yes ("not read", listed)** |
| Revocation | Yes | Yes | Awkward | Yes | n/a | **Yes (status + reason, audited)** |
| Bulk onboarding of credentials | Paper | Yes | Varies | Varies | n/a | **Yes (CSV, all-or-nothing)** |
| Institution-mediated escalation, recorded | Informal | No | No | No | No | **Yes (review cases + thread)** |
| Append-only audit trail | No | Internal | Chain | Varies | No | **Yes (DB trigger enforced)** |
| Avoids accusatory language by construction | Varies | n/a | n/a | n/a | No | **Yes (tested)** |
| Holder-controlled sharing | n/a | Yes | Yes | Yes | n/a | **No (not built)** |
| Standards interoperability | No | National | Varies | **Yes** | No | No (custom AVA1 payload) |
| Response time | Days–weeks | Seconds | Seconds | Seconds | Seconds | **0.09 s (PDF) – 1.8 s (photo)** |

### 2.3.2 Where this project is weaker

Honesty requires stating this explicitly:

- **No standards interoperability.** The `AVA1` payload and the canonical
  nine-field record are specific to this project. A W3C VC implementation
  would be interoperable where this is not.
- **No holder role.** DigiLocker's holder-mediated sharing has no analogue
  here, and the planned shareable link was not built.
- **Trust is centralised in the platform's key registry.** If an attacker can
  register a fraudulent institution and its public key, they can issue
  signatures that verify. Blockchain-anchored schemes distribute that trust
  differently (though they face an equivalent issuer-identity problem).
- **Single layout template.** One YAML template exists (`nbit.yaml`),
  describing this project's own certificate. A real deployment would need one
  per institutional layout.
- **OCR is weak on real photographs.** Documented and measured; see §6.5.

## 2.4 Research gap and how this project fills it

### 2.4.1 The gap

Reviewing the system classes in §2.1 against each other, four gaps emerge.

**Gap 1 — The digital-repository approaches do not address the document in the
verifier's hand.** DigiLocker, NAD and the W3C VC ecosystem all assume the
credential is already digital and that the *holder* initiates the
presentation. None of them helps an HR officer holding a printed 2015
certificate. Conversely, the document-OCR tools that do address that case have
no access to any issuer attestation, so they are reduced to statistical
guessing.

**Gap 2 — Verification systems report verdicts, not evidence.** Across manual
correspondence, commercial agencies and most automated tools, the verifier
receives a conclusion. There is no established model for presenting the
*reasoning* — which checks ran, which passed, which could not be performed, and
what specifically differed.

**Gap 3 — A valid signature is routinely treated as sufficient.** This is the
most interesting gap and it is not merely theoretical: this project encountered
it as a measured bug. Signature-based credential systems verify the
attestation and stop. But a signature is a statement about what the issuer
issued; it is not a statement about the artefact being presented. A genuine
certificate with an altered printed CGPA carries a perfectly valid signature.
No reviewed system reconciles the signed record against the presented document
field by field.

**Gap 4 — Uncertainty is collapsed into a binary, and unread fields are
silently omitted.** OCR-based systems typically threshold once: above the
threshold, act; below it, ignore. That conflates two completely different
situations — "the document disagrees and I am unsure" and "I could not read
this field" — and it silently omits the second, which reads to a verifier as
though the field had agreed.

### 2.4.2 How this project fills each gap

**Filling Gap 1 — signature on the artefact, read QR-first.** The institution's
Ed25519 signature is printed *onto the document itself* inside a QR code, so a
physical certificate carries its own attestation. The pipeline then reads the
QR **before any image processing touches the pixels**, from the image exactly as
uploaded, because a signature survives a photograph that 7-point grey labels do
not, and because the strongest evidence on the page must not be at the mercy of
a threshold chosen for OCR. Measured outcome: 12/12 photographs decoded, versus
an OCR path that loses the certificate number on almost every one.

**Filling Gap 2 — evidence as a first-class, persisted artefact.** Every
verification stores a list of six named checks, each with a status
(`pass` / `fail` / `skipped` / `uncertain`) and a human-readable `detail`
sentence written for a verifier rather than for a log. The checks are emitted in
a stable order so the result page lists the same evidence in the same place
every time, and field comparisons appear as one entry per field
(`field_match.cgpa`). The result page additionally names *which evidence carried
the verdict* ("Verified by the signed QR code on the document; its printed text
was read as a cross-check") — derived from the checks themselves, so it cannot
drift out of step with the verdict. There is deliberately **no overall
percentage**.

**Filling Gap 3 — `VERIFIED` requires that nothing differs.** The engine checks
field conflicts *before* it accepts a valid QR signature. A confidently-read
difference produces `MISMATCH` even with a perfect signature — which is exactly
what catches a document edited after issue while keeping its original QR — and
a moderately-read difference blocks `VERIFIED` and routes to `MANUAL_REVIEW`.
The ordering of rules in `_decide()` is the contribution: `conflicting` is
tested above `qr_signature == pass`.

**Filling Gap 4 — three bands, and `state` separated from `status`.** The
three-band rule distinguishes conflict, possible discrepancy and not-read, with
both thresholds in configuration rather than hard-coded, and passed into the
engine as `VerificationInput.thresholds` so the engine stays pure and every
band is testable at a chosen threshold. Each compared field carries a `state`
(`matches` / `differs` / `not_read`) alongside its `status`, and the result page
renders unread fields explicitly — "Couldn't read on the document: Roll number,
Certificate number" — beside the registry's values for the verifier to check by
eye. A field nobody could read blocks nothing and is never silently dropped.

### 2.4.3 Measured evidence that the gap-filling works

From the project's own evaluation on `samples/photos` (12 phone photographs of
2 printed certificates, run through the real upload API):

| Metric | Before the confidence bands | After |
|---|---|---|
| QR decoded | 12 / 12 | 12 / 12 (11 at 1×, one at 2×, all zxing-cpp) |
| `VERIFIED` | 12 | 10 |
| `MANUAL_REVIEW` | 0 | 2 |
| `MISMATCH` | 0 | 0 |
| Median time per photo | 1.6 s | 1.8 s |

The two results that moved are genuine certificates whose OCR misread a value
(a CGPA of 8.56 read as "8" at 70 %; a date of issue 2022-07-20 read as
"2072-01-20" at exactly 50 %). Both are now shown to the verifier as a possible
discrepancy to check against the paper, rather than passed as `VERIFIED` on the
strength of the QR alone. **Nothing genuine became a `MISMATCH`** — which is the
property that makes the rule safe to deploy.

### 2.4.4 Topics and keywords for literature search

The project contains no bibliography of academic papers, and none is claimed
here. For the report's literature review, the following search terms are the
relevant ones:

**Core topic searches**
- "academic credential verification system"
- "degree certificate fraud detection"
- "digital certificate verification QR code"
- "tamper-evident academic records"
- "credential verification architecture developing countries"

**Cryptography**
- "EdDSA Ed25519 RFC 8032"
- "canonical JSON serialization signature" / "JSON Canonicalization Scheme RFC 8785"
- "digital signature revocation status list"
- "Argon2 password hashing competition"

**Standards and national infrastructure**
- "W3C Verifiable Credentials Data Model"
- "Decentralized Identifiers DID core"
- "DigiLocker architecture India"
- "National Academic Depository India"
- "Blockcerts blockchain certificates MIT"

**OCR and document analysis**
- "Tesseract LSTM OCR accuracy evaluation"
- "document image binarization Otsu adaptive comparison"
- "skew detection and correction document images"
- "camera-captured document image analysis"
- "OCR confidence score reliability post-processing"
- "template-based information extraction documents"
- "key-value extraction semi-structured documents"

**QR and barcode decoding**
- "QR code ISO/IEC 18004 Reed-Solomon error correction"
- "QR decoding under blur and perspective distortion"
- "zxing barcode detection evaluation"

**Systems and evaluation methodology**
- "explainable verification user trust"
- "human-in-the-loop document verification"
- "append-only audit log database trigger"
- "role-based access control web application"
- "synthetic versus real evaluation data OCR pitfalls"

The last of those is worth emphasising in the review, because this project's
own development produced a direct lesson about it (§5.3): a round of OCR work
measured 48/48 critical fields on *synthetically degraded* renders and read
*worse* than the code it replaced on real phone photographs. The synthetic test
set was the error, not the measurement — a Gaussian gradient over a crisp
300 DPI render is not a photograph.

---

# CHAPTER 3: PROBLEM DEFINITION AND REQUIREMENT ANALYSIS

## 3.1 Problem statement

> **Given a physical or digital academic certificate presented by an unknown
> party, determine whether the institution named on it actually issued a
> credential with those exact details — and present the basis for that
> determination as evidence a human can inspect, act on and justify, without
> ever accusing the holder of fraud.**

Decomposed into the sub-problems the system must solve:

**P1 — Authoritative attestation.** The verifier has no reason to trust the
paper in their hand, and no practical way to reach the registrar. The system
must carry the institution's own attestation to the point of verification, in a
form that cannot be forged without the institution's private key.

**P2 — The attestation must survive the real world.** The document will arrive
as a phone photograph taken at an angle in office lighting, compressed by the
camera app. Whatever carries the attestation must survive blur, skew, shadow
and JPEG artefacts.

**P3 — The signed record and the printed artefact may disagree.** A valid
signature proves what the institution issued; it says nothing about what is
printed on the page. The system must reconcile the two field by field, and must
not let a valid signature mask an altered printed value.

**P4 — Reading the page is unreliable, and the unreliability must be
represented, not hidden.** OCR of a photograph fails in degrees. The system
must distinguish "this field disagrees and I am confident", "this field
disagrees and I am unsure", and "I could not read this field" — and must never
present the third as agreement.

**P5 — Absence of evidence must not become an accusation.** An unknown
certificate number, an unrecognised layout, an unreadable page: each means the
system has nothing to say, not that the document is fraudulent. The result
vocabulary must make that distinction structurally impossible to blur.

**P6 — Unsettled cases need an authority and a record.** When the system cannot
decide, only the issuing institution can. That escalation must be part of the
system, scoped so that each party sees only what it is entitled to, and
recorded so that what was asked and answered survives.

**P7 — Every state change must be accountable.** Issuance, import, revocation,
verification, login attempts and review decisions must all leave a record that
cannot subsequently be altered, including by the platform operator.

**P8 — Role separation must be strict.** A verifier must not be able to browse
institutional registries. An institution must not see another institution's
records or another verifier's cases. An administrator must be able to read
everything and to adjudicate nothing.

## 3.2 Functional requirements

Every requirement below was read off the implementing code. "Module" names the
file where the logic lives.

### 3.2.1 Authentication and session management

| ID | Requirement | Module |
|---|---|---|
| FR-1.1 | A user signs in with email and password and receives an access token (15 min) and a refresh token (7 d). | `services/auth.py: login()`, `api/v1/auth.py` |
| FR-1.2 | Email is matched case-insensitively and whitespace-trimmed. | `auth.normalize_email()` |
| FR-1.3 | Passwords are stored only as argon2 hashes; plaintext is never persisted or logged. | `core/security.py: hash_password()` |
| FR-1.4 | An unknown email and a wrong password return the identical error (`invalid_credentials`), and an unknown email is still verified against a dummy hash so timing does not reveal account existence. | `services/auth.py: authenticate()`, `_DUMMY_HASH` |
| FR-1.5 | A deactivated user (`is_active = false`) cannot sign in or use an existing token. | `authenticate()`, `deps.get_current_user()` |
| FR-1.6 | A user belonging to a deactivated institution cannot sign in, while that institution's certificates stay verifiable. | `authenticate()` |
| FR-1.7 | A refresh token exchanges for a new token pair; an access token presented to the refresh endpoint is rejected, and vice versa. | `auth.refresh_tokens()`, `security.decode_token(expected_type=...)` |
| FR-1.8 | `GET /auth/me` returns the current user with their institution summary. | `api/v1/auth.py: me()` |
| FR-1.9 | Both successful and failed login attempts are audited; a failure records **only the email's domain**, never the address or the password. | `services/auth.py: _email_domain()` |
| FR-1.10 | The browser transparently refreshes an expired access token once per request and emits a session-expired event if that fails. | `frontend/src/api/client.ts` interceptor |

### 3.2.2 Authorisation and role separation

| ID | Requirement | Module |
|---|---|---|
| FR-2.1 | Three roles exist: `admin`, `institution`, `verifier`. | `models/user.py: Role` |
| FR-2.2 | Role checks are applied by a single reusable dependency on every protected route. | `core/deps.py: require_role()` |
| FR-2.3 | An institution user must be linked to an institution; an admin and a verifier must not be — enforced by a database check constraint. | `ck_users_institution_link` |
| FR-2.4 | Verifiers **cannot browse the registry**: `GET /certificates` and `/certificates/{id}` are institution+admin only. | `api/v1/certificates.py: RegistryReader` |
| FR-2.5 | An institution user sees only its own institution's certificates; another institution's certificate returns **404, not 403**, so existence never leaks. | `certificates._scope()`, `get_certificate()` |
| FR-2.6 | Institution users are blocked from the verify endpoints entirely. | `api/v1/verify.py: Verifier` |
| FR-2.7 | A verification is readable only by the verifier who ran it or an admin; otherwise 404. | `verifications.get_verification()` |
| FR-2.8 | An upload job is pollable only by its submitting verifier or an admin; another's job returns 404 identically to an unknown one. | `upload_jobs.status()` |
| FR-2.9 | A review case is visible to the institution addressed, the verifier who asked, and an admin — 404 to anyone else. | `reviews._visible()` |
| FR-2.10 | An admin may read every review case and perform **no** action on one (403). | `reviews._may_write()`, `_institution_case()` |

### 3.2.3 Institution management (administrator)

| ID | Requirement | Module |
|---|---|---|
| FR-3.1 | Create an institution with a display name, a normalized unique code and the email of its first user. | `services/institutions.py: create_institution()` |
| FR-3.2 | On creation, generate an Ed25519 key pair: private key to `<KEYS_DIR>/<code>.pem` at mode 0600, public key as SPKI PEM in the row. | `signing.load_or_create_private_key()`, `public_key_pem()` |
| FR-3.3 | Generate the first user's password server-side (16 characters from an alphabet excluding O/0 and l/1), return it **exactly once**, hash it immediately, and never write it to the audit log. | `institutions.generate_password()` |
| FR-3.4 | List institutions with a certificate count and a user count per row. | `institutions._with_counts()` |
| FR-3.5 | Update **only** the display name and the active flag; the code and public key are immutable because issued signatures refer to them. | `update_institution()`, `schemas.InstitutionUpdate` |
| FR-3.6 | Deleting an institution that has issued certificates is refused with 409 `institution_has_certificates`; it must be deactivated instead so its certificates stay verifiable. | `delete_institution()` |
| FR-3.7 | An institution that never issued is deleted together with its users; if the append-only audit trail still references those users the delete fails with 409 `institution_in_use`. | `delete_institution()` |
| FR-3.8 | The private key file is deliberately **left on disk** when an institution is deleted — removing key material is a separate, explicit act. | documented in `delete_institution()` |
| FR-3.9 | Any signed-in user may list active institutions as form choices (name, code and id only — not the public key or the counts). | `GET /institutions/options`, `schemas.InstitutionOption` |

### 3.2.4 Credential registry (institution)

| ID | Requirement | Module |
|---|---|---|
| FR-4.1 | Add one certificate with the nine fields; the institution is taken from the signed-in user and cannot be chosen in the request. | `certificates.create_certificate()` |
| FR-4.2 | Reject a duplicate certificate number with 409 `duplicate_cert_number`, including when lost as a race (IntegrityError). | `_duplicate_error()`, `_commit_with_pdfs()` |
| FR-4.3 | Validate CGPA 0–10, marks 0–100, at least one of the two present. | `schemas.CertificateFields` |
| FR-4.4 | Validate year of passing between 1950 and the current year. | `CertificateFields._cross_field()` |
| FR-4.5 | Validate that the issue date is not in the future and not earlier than the year of passing. | `CertificateFields._cross_field()` |
| FR-4.6 | Store identifiers normalized (upper-case, non-alphanumerics stripped); keep names and programmes in their original case. | `normalize_id()`, `clean_text()` |
| FR-4.7 | Bulk-import certificates from a CSV whose header must match the nine columns exactly — missing or unknown columns are rejected. | `certificates._parse_csv()` |
| FR-4.8 | Import is **all-or-nothing**: every row is validated first, and if any row fails nothing is inserted and the response lists `{row, field, message}` per problem. | `import_csv()` |
| FR-4.9 | Import rejects rows naming another institution, duplicates within the file, and duplicates against the registry. | `import_csv()` |
| FR-4.10 | Import limits: `IMPORT_MAX_ROWS` (5000) and `IMPORT_MAX_MB` (2); tolerates a UTF-8 BOM, CRLF line endings and reordered columns. | `_parse_csv()`, `utf-8-sig` decode |
| FR-4.11 | List certificates with pagination (`page`, `size`, max 100) and search across certificate number, roll number and student name, with SQL `LIKE` wildcards escaped. | `list_certificates()`, `_escape_like()` |
| FR-4.12 | Revoke a certificate with a **mandatory** reason of at least 3 characters; the record, its signature and its PDF are left exactly as issued. | `revoke_certificate()`, `schemas.RevokeRequest` |
| FR-4.13 | Revoking an already-revoked certificate is refused with 409 `already_revoked`. | `revoke_certificate()` |
| FR-4.14 | The revocation reason goes to the audit log **only** — verifiers never see it. | `revoke_certificate()` audit meta |

### 3.2.5 Issuance of the signed certificate document

| ID | Requirement | Module |
|---|---|---|
| FR-5.1 | Build the canonical nine-field record, normalize every value, serialise with sorted keys and compact separators, and sign with the institution's Ed25519 private key (base64url, unpadded). | `signing.canonical_bytes()`, `sign_record()` |
| FR-5.2 | Emit grades as two-decimal **strings** in the canonical record, never JSON floats, so the signature cannot depend on float representation. | `signing.canonical_dict()` |
| FR-5.3 | Generate a one-page A4-landscape PDF carrying the institution name and code, the heading, the student name, the programme, year and grade, and boxed certificate number / roll number / date of issue. | `pdf_issue.build_certificate_pdf()` |
| FR-5.4 | Print a diagonal `SPECIMEN — NOT A REAL DOCUMENT` watermark and a footer declaring the document synthetic. | `_draw_watermark()`, `FOOTER_TEXT` |
| FR-5.5 | Embed the QR payload `AVA1\|number\|code\|signature` at 34 mm square, bottom right, with a "Scan to verify" caption. | `pdf_issue`, `qr.build_payload()`, `qr.qr_png()` |
| FR-5.6 | Store the PDF's SHA-256 in `certificates.file_sha256`. | `certificates._issue_pdf()` |
| FR-5.7 | Write the PDF atomically (temp file + `os.replace`) to `ISSUED_DIR/<id>.pdf` so a reader never sees a partial file. | `pdf_issue.write_issued_pdf()` |
| FR-5.8 | Write the PDF **before** committing, and remove it on rollback, so a stored file never outlives its row. | `_commit_with_pdfs()` |
| FR-5.9 | Serve the stored PDF byte-for-byte; **never regenerate** it, and return 404 `pdf_not_available` if the file is missing. | `certificates.issued_pdf()`, `GET /certificates/{id}/pdf` |
| FR-5.10 | Return the certificate's SHA-256 in an `X-Certificate-SHA256` response header with the PDF. | `api/v1/certificates.py` |
| FR-5.11 | A backfill command issues PDFs for rows that have none, and is idempotent — a certificate whose file is present is skipped so a hash a verifier has already seen is never replaced. | `scripts/backfill_pdfs.py`, `certificates.needs_pdf()` |
| FR-5.12 | Issuance is synchronous inside create and import (RQ stays OCR-only). | documented decision |

### 3.2.6 Verification by certificate number and by QR payload

| ID | Requirement | Module |
|---|---|---|
| FR-6.1 | Verify by certificate number; the number is normalized before lookup. | `verifications.verify_by_number()`, `schemas.VerifyByIdRequest` |
| FR-6.2 | A verifier's lookup is **not** scoped to one institution — any institution's certificate can be found. | `verifications._lookup()` |
| FR-6.3 | Verify a scanned QR payload: parse it, look the record up by number, re-check the signature against the institution's public key. | `verify_by_payload()` |
| FR-6.4 | An unreadable QR payload is a **422 `qr_payload_invalid`** and **nothing is recorded**, because text that is not an AVA1 payload is not a verification of any credential. | `verify_by_payload()` |
| FR-6.5 | A QR naming a different institution than the registry record fails the `qr_signature` check. | `engine._qr_signature()` |
| FR-6.6 | Every verification persists its result, its ordered check list, and what the request carried (`cert_number`, and `institution_code` for a QR) so an unknown number is still auditable. | `verifications._run()` |
| FR-6.7 | Every verification writes an audit row. | `verifications._run()` |

### 3.2.7 Verification by uploaded document

| ID | Requirement | Module |
|---|---|---|
| FR-7.1 | Accept a PDF, PNG or JPEG up to `UPLOAD_MAX_MB` (10). | `services/uploads.py` |
| FR-7.2 | Decide the file's type from its **leading bytes**, never from the filename or the client's `Content-Type`; anything else is 415 before the file is written. | `uploads.sniff_type()` |
| FR-7.3 | Read the request body in capped 256 kB chunks so an oversized upload is refused without being held in memory in full. | `api/v1/verify.py: _read_capped()` |
| FR-7.4 | Reject an empty file (400) and an oversized file (413). | `uploads.store()` |
| FR-7.5 | Store uploads under `UPLOAD_DIR/verify/`, never inside `ISSUED_DIR`, so pruning can never reach an issued PDF. | `uploads.upload_root()` |
| FR-7.6 | Return `202 Accepted` with a `job_id` and `upload_id`; run extraction in an RQ worker. | `upload_jobs.submit()` |
| FR-7.7 | Commit the upload row **before** enqueuing, because the worker reads it from another connection. | `upload_jobs.submit()` |
| FR-7.8 | Poll a job via `GET /verify/jobs/{job_id}` reporting `queued` / `running` / `done` / `failed`; an unmapped RQ status reports `failed` rather than still-running. | `workers/queue.py: state_for()` |
| FR-7.9 | A job that finishes without a usable verification id is reported `failed`, never left pending. | `upload_jobs.status()` |
| FR-7.10 | Decode the QR from the image **exactly as uploaded**, before any preprocessing, climbing zxing-cpp at 1×/2×/3× then pyzbar at 1×/2×/3×, stopping at the first valid AVA1 payload. | `ocr/qr_scan.py: scan()` |
| FR-7.11 | Skip an upscale that would exceed 40 megapixels. | `qr_scan.MAX_SCALED_PIXELS` |
| FR-7.12 | For a PDF, prefer the embedded text layer (exact, confidence 1.0); treat a page with fewer than 120 characters of text as image-only and rasterise it at 300 DPI for OCR. | `ocr/extract_text.py` |
| FR-7.13 | For a PDF, try the embedded images for the QR first (at issue resolution) and only then the rendered page. | `_qr_from_pdf_page()` |
| FR-7.14 | Mask the QR region white before OCR so its modules are not read as text on the adjacent baselines. | `preprocess.mask_regions()` |
| FR-7.15 | Preprocess in the order perspective → grayscale → denoise → light suppression → deskew → upscale → Otsu threshold. | `preprocess.prepare()` |
| FR-7.16 | Extract fields by matching a YAML template; an unrecognised layout yields **no fields at all**. | `ocr/fields.py: extract_fields()` |
| FR-7.17 | Report what the document said (`raw`, original casing) alongside the normalized comparison form (`value`) and the line's confidence. | `fields.ExtractedField` |
| FR-7.18 | Find the candidate record by QR payload, then by file SHA-256, then by the extracted certificate number. | `upload_verification.verify_upload()` |
| FR-7.19 | Never raise for an unreadable document — an empty extraction is a legitimate outcome that becomes `MANUAL_REVIEW`. | `extract_text.extract()` |
| FR-7.20 | Store the field values, confidences, template, text source, OCR engine, line count and mean line confidence — **never** the document's full text and never the file contents. | `upload_verification._extracted_summary()` |
| FR-7.21 | Record which QR reader decoded the code and at what upscale, as evidence of how marginal the photograph was. | `_extracted_summary()`, `ExtractedPage.qr_reader/qr_scale` |
| FR-7.22 | Keep the upload reachable from its verification (`verifications.upload_id`). | `models/verification.py` |

### 3.2.8 The verification engine

| ID | Requirement | Module |
|---|---|---|
| FR-8.1 | Produce exactly one of four statuses: `VERIFIED`, `MISMATCH`, `REVOKED`, `MANUAL_REVIEW`. Never "fake" or "forged". | `engine.VerificationResult` |
| FR-8.2 | Run six named checks in a stable order: `registry_lookup`, `revocation`, `record_signature`, `qr_signature`, `file_hash`, `field_match`. | `engine.evaluate()` |
| FR-8.3 | Each check returns `{name, status ∈ pass\|fail\|skipped\|uncertain, detail}`, with `detail` written as a sentence for a human. | `engine.Check` |
| FR-8.4 | Emit one `field_match.<field>` entry per compared critical field; use the bare `field_match` name only for the single entry explaining why nothing could be compared. | `engine._field_match()` |
| FR-8.5 | Re-verify the signature stored with the registry row, so a record altered after issuance resolves to `MISMATCH`. | `engine._record_signature()` |
| FR-8.6 | Check `qr_signature` whenever a payload is present, regardless of method, so a QR decoded from an upload is checked identically to a scanned one. | `engine._qr_signature()` |
| FR-8.7 | Treat a file-hash **difference** as `uncertain`, not `fail` — a scan or re-save legitimately changes the bytes. | `engine._file_hash()` |
| FR-8.8 | Compare each critical field in three confidence bands (≥0.85 conflict, ≥0.50 possible discrepancy, below 0.50 not read), with the threshold value belonging to the stricter band. | `engine._compare_field()` |
| FR-8.9 | Give each compared field a `state` (`matches` / `differs` / `not_read`) in addition to its `status`. | `engine.FieldState` |
| FR-8.10 | Compare identifiers tolerating OCR confusables on **both** sides; compare other fields exactly after normalization. | `normalize.ids_match()` |
| FR-8.11 | Compare `cgpa` or `marks` only when the registry record actually holds that one. | `engine._field_match()` |
| FR-8.12 | Compare `issue_date` like any other critical field. | `engine.CRITICAL_FIELDS` |
| FR-8.13 | `VERIFIED` requires that **nothing differs** — a differing field blocks it even with a valid signature. | `engine._decide()` |
| FR-8.14 | A field that could not be read blocks nothing and is listed for the verifier instead. | `engine._decide()` |
| FR-8.15 | Receive thresholds through `VerificationInput.thresholds` rather than reading configuration, so the engine stays pure and every band is testable. | `engine.Thresholds` |
| FR-8.16 | Contain no database, network or clock access anywhere. | `engine.py` module contract |

### 3.2.9 Result presentation

| ID | Requirement | Module |
|---|---|---|
| FR-9.1 | Give every result its own URL (`/verifications/:id`) so it can be reopened, shared and printed. | `pages/VerificationDetail.tsx` |
| FR-9.2 | Lead with a coloured banner naming the result, and distinguish a review caused by a *differing* value as "Possible discrepancy". | `VerificationResult.tsx` |
| FR-9.3 | State which evidence carried the verdict, derived from the checks so it cannot drift from the verdict. | `VerificationResult.pathUsed()` |
| FR-9.4 | Show a discrepancy box listing each differing field as "CGPA — document shows 9.99, institution issued 9.32". | `DocumentMatch.tsx` |
| FR-9.5 | Name the fields that could not be read, with the registry's values beside them. | `DocumentMatch.tsx`, `ExtractedFieldsTable.tsx` |
| FR-9.6 | Show a count ("Document match: 4 of 7 fields match · 1 differ · 2 not read") and **no overall authenticity percentage**. | `DocumentMatch.tsx` |
| FR-9.7 | Show a four-column table of field / on the document / in the registry / result, with a confidence badge per OCR value highlighted when below the conflict threshold. | `ExtractedFieldsTable.tsx` |
| FR-9.8 | Give a critical field the reader missed its own row reading "not checked" beside the registry's value, because a silent omission reads as agreement. | `ExtractedFieldsTable.tsx` |
| FR-9.9 | List every check with an icon, a label, its `detail` sentence and its status. | `VerificationResult.CheckRow` |
| FR-9.10 | Provide "Print / Save as PDF" via a print stylesheet, with no PDF library on the frontend. | `index.css` `@media print`, `print:` variants |
| FR-9.11 | Show verification history, newest first — a verifier's own, or all of them for an admin. | `pages/MyVerifications.tsx`, `GET /verifications` |

### 3.2.10 Verification requests (institution review queue)

| ID | Requirement | Module |
|---|---|---|
| FR-10.1 | Only the verifier who ran a verification may escalate it. | `reviews._verification_for_request()` |
| FR-10.2 | Only `MANUAL_REVIEW` and `MISMATCH` results may be escalated (409 `not_escalatable` otherwise). | `reviews.ESCALATABLE_RESULTS` |
| FR-10.3 | Address the request to the record's own institution when the document identified one; otherwise require the verifier to choose an **active** institution. | `reviews._institution_for()` |
| FR-10.4 | Allow at most one **open** case per verification, enforced by a partial unique index rather than a service-level check, so two browser tabs cannot both open one. | `uq_review_cases_open_per_verification` |
| FR-10.5 | Never edit the verification — the institution's answer is a later, separate fact shown beside the original result. | `models/review.py`, `models/verification.py: reviews` property |
| FR-10.6 | Support the state machine `pending → needs_info ↔ pending → closed`, with `closed` terminal. | `reviews.ReviewStatus` |
| FR-10.7 | Let either party post a message while the case is open; a verifier's reply clears `needs_info` back to `pending`, while the institution replying again leaves it needing info. | `reviews.add_message()` |
| FR-10.8 | Let the institution ask for more information, which posts a message and moves the case to `needs_info` in one transaction. | `reviews.ask_for_info()` |
| FR-10.9 | Offer exactly three decisions: `confirmed`, `confirmed_added`, `not_issued`. | `reviews`, `schemas.DecisionRequest` |
| FR-10.10 | Require a reason for `not_issued` — the one answer a holder can be harmed by — and show it to the verifier worded as "the institution has no such record", never "forged". | `reviews.not_issued()`, `DECISION_LABEL` |
| FR-10.11 | Route "Confirm & add" through the ordinary `certificates.create_certificate()` service, so the new row gets the same validation, Ed25519 signature, issued PDF and audit row; there is deliberately no second way into the registry. | `reviews.confirm_and_add()` |
| FR-10.12 | Create the certificate **before** closing the case, so a failure (duplicate number, missing key) leaves the case open to correct and retry. | `reviews.confirm_and_add()` |
| FR-10.13 | Prefill the "confirm & add" form from what the document said, in the document's own casing, with every field editable and validated on submit. | `reviews.prefill()`, `ConfirmAndAddForm.tsx` |
| FR-10.14 | Show the institution its own matching record when it has one, found by the extracted number scoped to that institution. | `reviews.registry_match()` |
| FR-10.15 | Stream the uploaded document inline to the institution addressed, the verifier who asked, or an admin — the one place a document leaves the verification pipeline. | `GET /reviews/{id}/document` |
| FR-10.16 | Hold an open case's upload back from retention, however old, and resume ordinary expiry once the case closes. | `uploads.held_upload_ids()`, `prune_expired()` |
| FR-10.17 | Serve one `/requests` page to all three roles, scoped by the API, with role-appropriate headings. | `pages/Requests.tsx` |
| FR-10.18 | Provide open and overdue (>7 days) counts for the nav badge and the admin dashboard. | `GET /reviews/counts` |
| FR-10.19 | Audit case creation, each message, the needs-info transition and each decision. | `reviews` audit calls |

### 3.2.11 Audit and administration

| ID | Requirement | Module |
|---|---|---|
| FR-11.1 | Write an audit row for every state change: login success/failure, certificate create/import/revoke/PDF-backfill, institution create/update/delete, user create, upload create, verification create, review create/message/needs-info/decision. | `services/audit.py` and call sites |
| FR-11.2 | Make `audit_log` append-only by database trigger — `UPDATE` and `DELETE` raise. | `models/audit.py` |
| FR-11.3 | Keep `meta` free of personal data: identifiers, counts, hashes and, for a failed login, the email domain only. | `audit.record()` contract |
| FR-11.4 | Filter the audit log by action **prefix** and by an inclusive UTC date range, newest first, paginated. | `services/admin.py: list_audit()` |
| FR-11.5 | Report platform statistics: institutions (total and active), users, certificates (total and revoked), verifications by result, open and overdue requests, and a rolling 7-day window of certificates, verifications, logins and failed logins. | `services/admin.py: stats()` |
| FR-11.6 | Restrict `/admin/*` to administrators. | `api/v1/admin.py` |

### 3.2.12 Housekeeping and operations

| ID | Requirement | Module |
|---|---|---|
| FR-12.1 | Expire uploads after `UPLOAD_RETENTION_DAYS` (7) and delete the row with its file; a file already gone is not an error. | `uploads.prune_expired()` |
| FR-12.2 | Provide a prune command with `--dry-run`, reporting what would be deleted, what is held for an open request, and which files are orphaned. | `scripts/prune_uploads.py` |
| FR-12.3 | Treat a file as an orphan only once it is older than one hour, because `store()` writes the file before committing the row. | `prune_uploads.ORPHAN_GRACE` |
| FR-12.4 | Never let pruning reach `ISSUED_DIR`; it walks the `uploads` table only. | `uploads.upload_root()` |
| FR-12.5 | Provide an idempotent seed script creating the demo institution, three demo users and 20 synthetic certificates. | `scripts/seed.py` |
| FR-12.6 | Expose `GET /health` and the OpenAPI document. | `main.py` |

## 3.3 Non-functional requirements

| Category | Requirement | How the code addresses it | Evidence |
|---|---|---|---|
| **Performance** | A verification of the original PDF must be effectively instant. | The PDF text-layer path skips OCR and preprocessing entirely; a byte-identical file short-circuits on the hash check. | Measured ≈ 0.09 s |
| | A photographed certificate must verify in a couple of seconds. | QR read first at 1× (1–43 ms for zxing-cpp); OCR runs once on a single prepared image. | Median 1.8 s per photo across 12 photos |
| | A long-running extraction must not block the HTTP request. | `POST /verify/upload` returns 202 with a job id; RQ worker does the work; client polls at 1 s. | `upload_jobs.submit()` |
| | Polling must stop when the job settles. | `refetchInterval` returns `false` on `done`/`failed`. | `useUploadJob` |
| | Database queries must not degrade with table size. | Indexes on `certificates.cert_number` (unique), `roll_number`, `institution_id`; `uploads.sha256`; `verifications.verifier_id/result/created_at`; `audit_log.action/created_at/actor_id`; `review_cases` on verification, institution, created_at, updated_at. | migrations |
| | Wasteful work must be avoided. | An upscale beyond 40 MP is skipped; the QR ladder stops at the first valid payload; the OCR availability probe is paid once per process. | `qr_scan`, `engines.get_engine()` |
| **Security** | Passwords must resist offline cracking. | argon2 (memory-hard). | `core/security.py` |
| | Account existence must not leak through errors or timing. | Identical error message; dummy-hash verification on unknown email. | `auth.authenticate()` |
| | Record existence must not leak through status codes. | 404 (not 403) for another institution's certificate, another verifier's verification, another party's review case, and an unknown job id. | `_scope()`, `get_verification()`, `_visible()`, `status()` |
| | Uploaded file types must not be attacker-declared. | Magic-byte sniffing; filename and `Content-Type` ignored. | `uploads.sniff_type()` |
| | An oversized upload must not exhaust memory. | Capped chunked reads, limit + 1 byte. | `_read_capped()` |
| | Secrets must never be in code or git. | All configuration via env; `.env`, `keys/*` gitignored; private keys mode 0600. | `.gitignore`, `config.py` |
| | The generated first password must be shown once and never recoverable. | Hashed immediately; excluded from the audit row; returned only in the creation response. | `create_institution()` |
| | The audit trail must resist tampering, including by an operator. | Database trigger rejecting `UPDATE`/`DELETE`. | `models/audit.py` |
| | Personal data must not be over-collected or logged. | Only verification-relevant fields stored; no document text or file contents in `extracted_fields`; failed logins keep the email domain only. | `_extracted_summary()`, `_email_domain()` |
| | SQL injection must be impossible. | SQLAlchemy parameter binding throughout; `LIKE` wildcards escaped explicitly. | `_escape_like()` |
| | Cross-origin access must be restricted. | `CORSMiddleware` with an explicit allow-list from `CORS_ORIGINS`; no wildcard, because credentials are allowed. | `main.py` |
| | An institution must not confirm a document it cannot see. | `GET /reviews/{id}/document` streams the file, scoped exactly like the case. | `api/v1/reviews.py` |
| **Reliability** | A stored PDF must never outlive its database row, or vice versa. | PDF written before commit; removed on rollback; row inserted before the file is served. | `_commit_with_pdfs()` |
| | A partially written file must never be read. | Atomic temp-file + `os.replace`. | `write_issued_pdf()` |
| | A served PDF's hash must always equal the stored hash. | PDFs are generated once, never regenerated; a missing file is a 404, not a rebuild. | `issued_pdf()` |
| | A client must never poll a job for ever. | Unknown RQ status → `failed`; finished-without-id → `failed`. | `queue.state_for()`, `status()` |
| | Evidence behind an institution's answer must survive. | Open cases hold their upload back from retention. | `held_upload_ids()` |
| | A failed registry add must not corrupt a case. | Certificate created before the case closes. | `confirm_and_add()` |
| | Concurrency must not create two open cases. | Partial unique index, with `IntegrityError` translated to 409. | `create_case()` |
| **Usability** | A verifier must not have to choose in advance which evidence their photo will yield. | "Scan QR" and "Upload document" merged into one **Verify document** tab; the server reads both the code and the text from whatever arrives. | `pages/Verify.tsx` |
| | The result must be comprehensible without reading the code. | Check `detail` strings are full sentences naming fields as the page does; result banners carry an explanatory paragraph. | `engine._FIELD_LABELS`, `RESULTS` |
| | The verifier must be told what could not be read. | Unread fields named explicitly with registry values beside them. | `DocumentMatch.tsx` |
| | No result may read as an accusation. | Four-status vocabulary; "not issued" worded as "has no such record"; tested. | `test_no_result_ever_says_fake` |
| | Bulk import errors must be actionable. | Per-row `{line, column, problem}` table; nothing imported until clean; downloadable CSV template. | `ImportCertificates.tsx` |
| | Work-in-progress must be visible. | Staged spinner labels: "Uploading…" → "Queued for extraction…" → "Reading the document…". | `JOB_LABELS` |
| | A result must be retainable offline. | Print stylesheet with `print-keep` page-break control. | `index.css` |
| | Accessibility basics must hold. | Radix UI primitives; `role="alert"` / `role="status"`; `aria-label` on icon-only buttons; `sr-only` check status text. | components |
| **Scalability** | OCR load must be horizontally scalable. | Work is in an RQ queue; `docker compose up --scale worker=N` adds consumers with no code change. | `docker-compose.yml` |
| | API instances must be stateless. | JWT auth with no server-side session; all state in Postgres/Redis. | `core/security.py` |
| | Large lists must not be returned whole. | Pagination with `size` capped at 100 on every list endpoint. | routers |
| | A second OCR engine must be addable cheaply. | `OcrEngine` protocol; `get_engine()` is the only switch point — exercised for real once. | `ocr/engines.py` |
| | A new certificate layout must not require code. | Declarative YAML templates loaded from a directory. | `ocr/fields.py`, `templates/` |
| **Maintainability** | Business rules must be testable without infrastructure. | The engine, normalization, signing, QR parsing and preprocessing are pure functions; 373 backend test cases, all passing. | `tests/` |
| | Routers must stay thin. | Routers call services; services raise `AppError`; one handler renders the envelope. | `main.py`, `core/errors.py` |
| | Frontend API types must not drift. | Generated from OpenAPI via `npm run gen:api`; never hand-written. | `scripts/gen-api.mjs` |
| | Style must be enforced, not debated. | `ruff` with `E,F,I,UP,B,SIM`, line length 100; `tsc --noEmit` as the frontend lint. | `pyproject.toml`, `package.json` |
| | Decisions must be recorded with their reasoning. | A standing decision log in `CLAUDE.md`, including reverted attempts and why. | `CLAUDE.md` |
| **Portability** | The stack must run identically on any developer machine. | Docker Compose with five services, health checks and pinned base images. | `docker-compose.yml` |
| | Line endings must not break container files. | `* text=auto eol=lf` enforced by `.gitattributes`. | `.gitattributes` |
| | No OCR model download at runtime. | Tesseract traineddata ships in the apt packages and is baked into the image — no warm-up on first verify. | `backend/Dockerfile` |
| **Privacy** | The QR must carry no personal data. | Payload is prefix, number, institution code, signature. | `services/qr.py` |
| | Document contents must not be retained beyond need. | Uploads expire after 7 days; extracted text is never stored, only fields. | `uploads`, `_extracted_summary()` |

## 3.4 Hardware requirements

### 3.4.1 Development machine (the configuration this project was built on)

| Component | Minimum | Recommended | Notes |
|---|---|---|---|
| CPU | 2 cores, x86-64 | 4+ cores | Tesseract OCR is CPU-bound; a photo takes ~1–2 s on 4 cores |
| RAM | 8 GB | 16 GB | Five containers plus Postgres; OpenCV holds decoded images in memory, and a 2× upscale of a 12 MP photo is ~150 MB |
| Disk | 10 GB free | 20 GB SSD | Images: `python:3.12-slim` + Tesseract + OpenCV ≈ 1.2 GB, `node:22-alpine` + `node_modules` ≈ 0.5 GB, plus Postgres data and issued PDFs |
| Network | Required for the initial build | — | Pulling images and packages; nothing is downloaded at runtime |
| Display | 1366 × 768 | 1920 × 1080 | The admin navigation has five items and wraps to a second row below ~1280 px |
| Camera | Optional | Phone camera | For the "Take a photo" capture path on a mobile browser |

Verified host configuration: Windows 11 with Docker Desktop. The containers
themselves are Linux (`python:3.12-slim`, `node:22-alpine`,
`postgres:16-alpine`, `redis:7-alpine`).

### 3.4.2 Server deployment (indicative — not yet deployed; see §5.5)

| Component | Specification | Reasoning |
|---|---|---|
| Application host | 2 vCPU, 4 GB RAM | `api` + `web` are light; FastAPI is I/O-bound |
| Worker host | 2–4 vCPU, 4 GB RAM per worker | OCR is the only CPU-heavy work; scale this tier independently |
| Database | PostgreSQL 16, 2 vCPU, 4 GB RAM, SSD | `pg_trgm` extension required |
| Cache/queue | Redis 7, 1 GB RAM | Queue only; append-only persistence enabled |
| Object storage | Sized by retention | Issued PDFs are permanent (~25 kB each); uploads expire after 7 days |
| TLS | Required | Tokens and documents in transit; also required for browser camera access on non-localhost origins |

### 3.4.3 Client requirements

A modern browser with ES2022 support and `localStorage` (Chrome, Edge, Firefox
or Safari, current versions). No plugin, no desktop install. On a phone, the
camera is reached through the operating system's own camera app via
`<input type="file" capture="environment">`, so no camera permission prompt or
`getUserMedia` support is needed.

## 3.5 Software requirements

### 3.5.1 Languages, runtimes and tools

| Item | Version | Role |
|---|---|---|
| Python | 3.12 (`python:3.12-slim`) | Backend language |
| Node.js | 22 (`node:22-alpine`) | Frontend build tooling |
| TypeScript | 5.7.2 | Frontend language |
| PostgreSQL | 16 (`postgres:16-alpine`) | Primary data store |
| Redis | 7 (`redis:7-alpine`) | Job queue broker |
| Docker Compose | v2 syntax | Orchestration of five services |
| Tesseract OCR | 5 (Debian `tesseract-ocr`) | OCR engine |
| ruff | 0.8.4 | Python lint and format |
| pytest | 8.3.4 | Backend test runner |
| Alembic | 1.14.0 | Database migrations |

### 3.5.2 Backend Python dependencies (`backend/requirements.txt`, all pinned)

| Package | Version | Purpose in this project |
|---|---|---|
| fastapi | 0.115.6 | Web framework, dependency injection, OpenAPI generation |
| uvicorn[standard] | 0.34.0 | ASGI server |
| pydantic | 2.10.4 | Request/response validation and field normalization |
| pydantic-settings | 2.7.0 | Environment-variable configuration binding |
| python-multipart | 0.0.20 | Multipart form parsing for file uploads |
| SQLAlchemy | 2.0.36 | ORM and SQL toolkit (synchronous sessions) |
| psycopg[binary] | 3.2.3 | PostgreSQL driver |
| alembic | 1.14.0 | Schema migrations |
| redis | 5.2.1 | Redis client |
| rq | 2.0.0 | Background job queue for OCR |
| passlib[argon2] | 1.7.4 | Password hashing context |
| argon2-cffi | 23.1.0 | Argon2 implementation |
| PyJWT | 2.10.1 | JWT encode/decode (HS256) |
| cryptography | 44.0.0 | Ed25519 key generation, signing, verification, PEM serialisation |
| qrcode[pil] | 8.0 | QR code generation for the issued PDF |
| pyzbar | 0.1.9 | QR decoding — fallback reader in the ladder |
| zxing-cpp | 2.3.0 | QR decoding — primary reader (one package, no dependencies, 0.96 MB wheel) |
| PyMuPDF | 1.25.1 | PDF text-layer extraction, page rasterisation, embedded-image extraction |
| reportlab | 4.2.5 | Issued certificate PDF generation |
| pytesseract | 0.3.13 | Tesseract binding (word-level TSV output) |
| opencv-python-headless | 4.10.0.84 | Image preprocessing (headless build only) |
| PyYAML | 6.0.2 | Loading OCR field templates |
| rapidfuzz | 3.11.0 | **Declared for Tier 2 item 7 but never imported** — see §1.4.2 |
| pytest | 8.3.4 | Test runner |
| httpx | 0.28.1 | Test client transport for FastAPI's `TestClient` |
| ruff | 0.8.4 | Lint and format |

**Deliberately absent:** `paddleocr` (cannot install on Python 3.12 at the
pinned version; installable versions add 55–109 packages and pull in
`opencv-contrib-python`, which would shadow the headless OpenCV build).

### 3.5.3 Frontend dependencies (`frontend/package.json`, all pinned)

**Runtime:**

| Package | Version | Purpose |
|---|---|---|
| react / react-dom | 18.3.1 | UI library |
| react-router-dom | 7.1.1 | Client-side routing with nested role guards |
| @tanstack/react-query | 5.62.11 | The only state manager — server-state cache, mutations, polling |
| axios | 1.7.9 | HTTP client with auth and refresh interceptors |
| @radix-ui/react-dialog | 1.3.1 | Accessible modal dialogs |
| @radix-ui/react-tabs | 1.2.1 | The Verify page's two tabs |
| @radix-ui/react-label | 2.1.17 | Accessible form labels |
| @radix-ui/react-slot | 1.5.0 | `asChild` composition for buttons |
| @radix-ui/react-toast | 1.3.1 | Toast notifications |
| lucide-react | 1.72.0 | Icon set |
| class-variance-authority | 0.7.1 | Component variant definitions |
| clsx | 2.1.1 | Conditional class names |
| tailwind-merge | 2.6.0 | Conflict-free Tailwind class merging (`cn()`) |
| tailwindcss-animate | 1.0.7 | Animation utilities for Radix state transitions |

**Development:**

| Package | Version | Purpose |
|---|---|---|
| vite | 6.0.7 | Dev server and bundler |
| @vitejs/plugin-react | 4.3.4 | React fast-refresh and JSX transform |
| typescript | 5.7.2 | Type checking (`tsc --noEmit` is the lint script) |
| tailwindcss | 3.4.17 | Utility CSS framework |
| postcss | 8.4.49 | CSS pipeline |
| autoprefixer | 10.4.20 | Vendor prefixing |
| openapi-typescript | 7.5.0 | Generates `src/api/schema.ts` from the live OpenAPI document |
| @types/react / @types/react-dom | 18.3.18 / 18.3.5 | React type definitions |

**Not present:** `html5-qrcode` (removed with the live scanner), Playwright,
and `@types/node` (deliberately avoided — the Vite config declares the one
Node global it needs locally).

### 3.5.4 System packages in the backend image (`backend/Dockerfile`)

| Package | Why it is installed |
|---|---|
| `libzbar0` | Native library behind `pyzbar` |
| `tesseract-ocr` | The OCR engine plus English traineddata |
| `tesseract-ocr-hin` | Hindi traineddata, pre-installed for the Tier 3 goal so no rebuild is needed |
| `libglib2.0-0` | Required by `opencv-python-headless` |
| `curl` | The container health check (`curl -fsS http://localhost:8000/health`) |
| **`libgl1` — deliberately NOT installed** | The headless OpenCV build does not link libGL; installing it would serve only `opencv-contrib-python`, which nothing is permitted to pull in |

### 3.5.5 Database extensions (`db/init/01-extensions.sql`)

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

Both are created once on first boot of an empty data volume. `pg_trgm` is
installed per the specification's stack; the current search implementation uses
`ILIKE`/`LIKE` patterns rather than trigram operators, so the extension is
available but not yet exploited.

## 3.6 Feasibility study

### 3.6.1 Technical feasibility — **demonstrated, with one unsolved area**

The decisive evidence is that the system works end to end today: the backend
test suite passes in full, and the measured evaluation on real phone
photographs verifies 10 of 12 as `VERIFIED` with 2 routed to review and **zero
false mismatches**.

*Favourable factors.* Every technology chosen is mature and freely available.
Ed25519 signing and verification are provided by `cryptography`, a widely
audited library, and the per-verification cost is sub-millisecond. The
QR-first design sidesteps the hardest technical risk: the project does not need
OCR to be good, only good enough to cross-check a signature it has already
verified. The architecture is a conventional three-tier web application with
one background queue — nothing exotic to operate.

*The unsolved area, stated plainly.* OCR of a real phone photograph remains
weak. `prepare()` is tuned for a clean render or a flat scan: a **global** Otsu
threshold floods a shadowed half of a page to solid black, and nothing corrects
uneven illumination or rescales small text. On the 12-photo set it loses the
certificate number and roll number on almost every image and matches no
template at all on 4 of 12. This is survivable **only** while a QR decodes; a
photograph whose code is damaged or cropped away falls back to this OCR and
will reach `MANUAL_REVIEW`. One attempt to fix it was made and reverted (§5.3),
and the lesson — that the evaluation set must be real photographs — is now
institutionalised in the project.

*Residual technical risks.* Trust is centralised in the platform's key
registry. A single OCR template exists. Private keys are unencrypted PEM files
on a volume, with no hardware security module and no key rotation path (the
institution code and public key are deliberately immutable).

### 3.6.2 Economic feasibility — **highly favourable**

*Development cost.* Zero in licensing. Every dependency is open-source under a
permissive or compatible licence (MIT, BSD, Apache 2.0 for Tesseract, AGPL for
PyMuPDF — which is worth noting for any commercial derivative). The cost is
student time.

*Infrastructure cost.* The whole stack runs on one developer machine for
demonstration. For a pilot deployment the indicative monthly cost is a small
application instance, a small worker instance, a managed Postgres instance and
a minimal Redis — within a low-cost cloud tier, and well inside a typical
institutional IT budget. There are no per-verification costs: no blockchain
transaction fees, no third-party OCR API charges, no per-check agency fees.
This compares favourably with commercial background verification, which is
charged per credential checked.

*Storage economics.* An issued PDF is roughly 25 kB, so 100,000 credentials
occupy about 2.5 GB permanently. Uploads self-expire after 7 days, so the
verification-side storage is bounded by throughput rather than by cumulative
volume.

*Operational cost.* The expensive human activity — answering verification
enquiries — is reduced rather than relocated: the common case is settled by a
signature, and only genuinely ambiguous cases reach a registrar, now with the
document and the matching registry row already on screen.

### 3.6.3 Operational feasibility — **feasible, with adoption as the real constraint**

*Favourable factors.* The verifier's workflow is one screen and one action:
photograph the certificate. There is nothing to install and no account for the
credential holder to create. The institution's workflow maps onto what a
registrar already does — publish results, correct records, answer enquiries —
and the CSV import matches how examination data already exists. Role
separation means no retraining of concepts: a registrar sees only their own
registry.

*The genuine obstacle is organisational, not technical.* The system's value is
proportional to the number of institutions that register their credentials and
protect their private keys. That requires institutional buy-in, a key-custody
policy, and backfilling historical records — none of which a prototype can
deliver. Partial adoption degrades gracefully, however: an unregistered
institution's certificate simply reaches `MANUAL_REVIEW` and can be escalated
through the request workflow, which is exactly the manual process it replaces.

*Operational risks and mitigations present in the code.* A lost private key
cannot be rotated for already-issued certificates (code and key are immutable
by design) — mitigated only by custody discipline. An institution that never
answers requests is the failure mode most likely to erode trust, which is why
the admin dashboard surfaces the count of requests open more than seven days.
The administrator deliberately **cannot** adjudicate a case, so a platform
operator cannot be pressured into ruling on whether a university issued a
degree.

*Legal and ethical posture.* The system never labels a document fraudulent;
the strongest statement available is that an institution has no such record,
and that statement requires a written reason. Personal data collection is
minimised, uploads expire, and the audit log stores identifiers rather than
names. For a real deployment, data-protection review, a retention policy and a
consent flow for the credential holder would all be prerequisites — none of
which exist in the prototype.

## 3.7 Use cases and actors

### 3.7.1 Actors

| Actor | Authenticated | Scope | Cannot do |
|---|---|---|---|
| **Administrator** (`admin`) | Yes | Platform-wide: all institutions, all certificates, all verifications, all review cases, the audit log, statistics | Cannot add or revoke a certificate (that requires an institution); **cannot decide a review case** (403 by design) |
| **Institution user** (`institution`) | Yes | Its own institution only: its certificates, the review cases addressed to it | Cannot verify anything (blocked from `/verify/*`); cannot see another institution's records; cannot open a review case |
| **Verifier** (`verifier`) | Yes | Its own verifications and its own review requests | **Cannot browse the registry**; cannot see another verifier's verification or job; cannot answer a review case |
| **Background worker** (system) | n/a (internal) | Reads an upload, writes a verification | Not reachable over HTTP |
| **Credential holder** | **No account exists** | — | The prototype has no holder-facing role |
| **Anonymous visitor** | No | `GET /health`, the OpenAPI document, and the login endpoint only | Everything else requires a bearer token |

### 3.7.2 Use-case summary

| ID | Use case | Primary actor | Precondition | Main outcome |
|---|---|---|---|---|
| UC-01 | Sign in | Any user | An active account in an active institution (if applicable) | Access + refresh tokens issued; attempt audited |
| UC-02 | Refresh an expired session | Any user | A valid refresh token | New token pair; or session-expired event in the browser |
| UC-03 | Sign out | Any user | Signed in | Tokens cleared locally (not revoked server-side) |
| UC-04 | Register an institution | Administrator | Unique code and email | Institution + Ed25519 key pair + first user created; password shown once |
| UC-05 | Deactivate an institution | Administrator | Institution exists | Its users can no longer sign in; its certificates remain verifiable |
| UC-06 | Delete an institution | Administrator | It has issued nothing | Institution and its users removed; refused with 409 otherwise |
| UC-07 | Add a certificate | Institution | Signing key present | Signed record + issued PDF + stored hash + audit row |
| UC-08 | Bulk-import certificates | Institution | A valid CSV for its own code | All rows imported, or none with a per-row error report |
| UC-09 | Download an issued PDF | Institution / Administrator | A stored PDF exists | Exact stored bytes streamed with its SHA-256 header |
| UC-10 | Revoke a certificate | Institution | Its own, currently active | Status `revoked`, timestamp set, reason audited |
| UC-11 | Verify by certificate number | Verifier | — | A verification with four-status result and six checks |
| UC-12 | Verify a QR payload | Verifier | A well-formed AVA1 payload | A verification; malformed text is 422 and records nothing |
| UC-13 | Verify by uploading a document | Verifier | PDF/PNG/JPEG ≤ 10 MB | 202 + job id → background extraction → stored verification |
| UC-14 | Photograph a certificate | Verifier | A device camera | Same path as UC-13 |
| UC-15 | Poll an extraction job | Verifier | Owns the job | `queued` / `running` / `done` + verification id / `failed` |
| UC-16 | Read a verification result | Verifier / Administrator | Owns it, or is an admin | Banner, evidence path, field comparison, unread fields, check list |
| UC-17 | Print or save a result | Verifier / Administrator | A result is open | A print-styled page / PDF |
| UC-18 | Browse verification history | Verifier / Administrator | — | Own history, or all of it for an admin, newest first, paginated |
| UC-19 | Request confirmation from an institution | Verifier | Own result is `MANUAL_REVIEW` or `MISMATCH`, with no case already open | A `pending` case addressed to the issuing or chosen institution |
| UC-20 | Review the request inbox | Institution / Verifier / Administrator | — | One `/requests` list, scoped by role |
| UC-21 | Inspect the presented document | Institution / requesting Verifier / Administrator | The file is still stored | The uploaded document streamed inline, with the extracted fields beside it |
| UC-22 | Ask the verifier for more information | Institution | An open case addressed to it | Case moves to `needs_info` with a message |
| UC-23 | Reply on a case | Institution / requesting Verifier | The case is open | A message; a verifier's reply returns `needs_info` to `pending` |
| UC-24 | Confirm a document as genuine | Institution | An open case addressed to it | Case closed `confirmed`; verification left untouched |
| UC-25 | Confirm and add to the registry | Institution | An open case; the form validates | A signed certificate with its PDF created; case closed `confirmed_added` |
| UC-26 | Record "no such record" | Institution | An open case; a reason supplied | Case closed `not_issued` with the reason shown to the verifier |
| UC-27 | View platform statistics | Administrator | — | Counts by result, registry totals, open and overdue requests, 7-day window |
| UC-28 | Browse the audit log | Administrator | — | Append-only rows filtered by action prefix and date range |
| UC-29 | Seed demo data | Operator (CLI) | Empty or partial database | Demo institution, three users, 20 synthetic certificates — idempotent |
| UC-30 | Backfill missing PDFs | Operator (CLI) | Rows without a stored PDF | PDFs issued and hashes written; idempotent |
| UC-31 | Prune expired uploads | Operator (CLI) | — | Expired rows and files deleted; open-case uploads held; orphans >1 h removed |

### 3.7.3 Use-case relationships worth noting in the diagram

- UC-13 **includes** UC-15 (an upload is always followed by polling).
- UC-14 **extends** UC-13 (photographing is one way of supplying the file).
- UC-19 **extends** UC-16, and is available only for two of the four results.
- UC-25 **includes** UC-07 — "Confirm & add" runs the ordinary create service,
  which is the design point: there is no second way into the registry.
- UC-11, UC-12 and UC-13 all **include** the verification engine, which is a
  single shared component rather than three parallel implementations.
- The Administrator actor **generalises** read access across UC-16, UC-18,
  UC-20, UC-21, UC-27 and UC-28, and is deliberately **excluded** from UC-22
  through UC-26.

---

# CHAPTER 4: DESIGN AND IMPLEMENTATION

## 4.1 System architecture

### 4.1.1 Architectural style

The system is a **three-tier web application with an asynchronous worker
tier**, deployed as five Docker Compose services. Within the backend, a
**layered architecture** is enforced by convention and by import direction:

```
HTTP boundary   →  app/api/v1/*.py        thin routers: role gates, request/response shapes
Validation      →  app/schemas/*.py       Pydantic models; normalization happens here
Business logic  →  app/services/*.py      all rules, all I/O orchestration
Pure domain     →  app/services/verification/engine.py, normalize.py, signing.py, qr.py
Persistence     →  app/models/*.py        SQLAlchemy models + database constraints
Infrastructure  →  app/core/*.py          config, session factory, security, dependencies
Async work      →  app/workers/*.py       RQ queue, worker entrypoint, the OCR job
```

Two rules give the layering teeth:

1. **Routers never contain business logic and never build error bodies.** They
   call a service and return its result. Services raise
   `AppError(status, code, message, **extra)`, and one handler in `main.py`
   renders the `{"error": {...}}` envelope.
2. **The verification engine is pure.** `engine.py` imports no database
   module, performs no I/O, and reads no configuration — even its thresholds
   arrive inside `VerificationInput`. The dependency actually runs the other
   way: `models/verification.py` imports `VerificationMethod` and
   `VerificationResult` *from the engine* for its check constraints, so the
   domain owns the vocabulary and the table merely constrains it.

### 4.1.2 Figure 4.1 — Overall system architecture

```mermaid
flowchart TB
    subgraph client["Client tier"]
        browser["Browser / phone<br/>React 18 SPA"]
        camera["Device camera<br/>input capture=environment"]
    end

    subgraph web["web container · Vite 6 :5173"]
        vite["Vite dev server<br/>serves the SPA<br/>proxies /api to api:8000"]
    end

    subgraph api["api container · uvicorn :8000"]
        routers["FastAPI routers<br/>auth · institutions · certificates<br/>verify · reviews · admin"]
        svc["Services layer"]
        engine["verification/engine.py<br/>PURE · no I/O"]
    end

    subgraph worker["worker container · RQ"]
        job["ocr_job.verify_upload_job"]
        pipeline["OCR pipeline<br/>qr_scan → preprocess → Tesseract → fields"]
    end

    subgraph data["Data tier"]
        pg[("PostgreSQL 16<br/>pg_trgm · JSONB<br/>8 tables")]
        redisq[("Redis 7<br/>queue 'ocr'")]
        vol[("uploads volume<br/>verify/ · certificates/")]
        keys[("keys volume<br/>Ed25519 private keys<br/>mode 0600")]
    end

    browser -->|HTTPS| vite
    camera -.->|photo file| browser
    vite -->|"/api/v1/*"| routers
    routers --> svc
    svc --> engine
    svc --> pg
    svc --> keys
    svc --> vol
    svc -->|enqueue| redisq
    redisq -->|dequeue| job
    job --> pipeline
    job --> pg
    job --> vol
    browser -. "poll GET /verify/jobs/{id}" .-> routers
```

### 4.1.3 Table 4.1 — Docker Compose services

| Service | Image / build | Port | Command | Health check | Depends on |
|---|---|---|---|---|---|
| `db` | `postgres:16-alpine` | 5432 | default | `pg_isready -U $USER -d $DB`, 5 s / 12 retries | — |
| `redis` | `redis:7-alpine` | 6379 | `redis-server --appendonly yes` | `redis-cli ping`, 5 s / 12 retries | — |
| `api` | build `./backend` | 8000 | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | `curl -fsS /health`, 10 s / 6 retries, 10 s start period | `db` healthy, `redis` healthy |
| `worker` | build `./backend` | — | `python -m app.workers.worker` | Python Redis `ping()`, 15 s / 6 retries | `db` healthy, `redis` healthy |
| `web` | build `./frontend` | 5173 | `npm run dev -- --host 0.0.0.0 --port 5173` | `wget -q -O /dev/null http://127.0.0.1:5173/`, 10 s / 6 retries, 15 s start | `api` |

Named volumes: `pgdata`, `redisdata`, `uploads`, `web_node_modules`. Bind
mounts: `./backend:/app` and `./keys:/keys` on both `api` and `worker`;
`./frontend:/app` on `web`.

**An operational consequence worth recording in the report:** `api` runs with
`--reload`, but `worker` is a plain process. After changing anything the OCR
job touches — including settings — the worker must be restarted
(`docker compose restart worker`) or every upload fails with "Extraction
failed". This has been a recurring development trap.

### 4.1.4 Figure 4.2 — Layered backend architecture with dependency direction

```mermaid
flowchart TD
    subgraph L1["1 · HTTP boundary — app/api/v1/"]
        R["router.py · auth · institutions<br/>certificates · verify · reviews · admin"]
    end
    subgraph L2["2 · Contract — app/schemas/"]
        S["Pydantic models<br/>validation + normalization + OpenAPI"]
    end
    subgraph L3["3 · Business logic — app/services/"]
        SV["auth · institutions · certificates<br/>verifications · upload_verification<br/>uploads · upload_jobs · reviews · admin · audit"]
    end
    subgraph L4["4 · Pure domain"]
        E["verification/engine.py"]
        N["normalize.py"]
        SG["signing.py"]
        Q["qr.py"]
        H["hashing.py"]
    end
    subgraph L5["5 · OCR subsystem — app/services/ocr/"]
        O["engines.py · qr_scan.py · preprocess.py<br/>extract_text.py · fields.py · templates/"]
    end
    subgraph L6["6 · Persistence — app/models/"]
        M["SQLAlchemy models + CheckConstraints + trigger"]
    end
    subgraph L7["7 · Infrastructure — app/core/"]
        C["config.py · db.py · security.py<br/>deps.py · errors.py"]
    end

    R --> S
    R --> SV
    SV --> L4
    SV --> O
    SV --> M
    O --> L4
    M -->|"imports enums FROM"| E
    SV --> C
    R --> C
    M --> C
```

The one arrow that looks backwards — `models` → `engine` — is deliberate and is
the single source of truth for the result vocabulary.

### 4.1.5 Request paths through the architecture

**Synchronous path** (verify by number or QR, all registry operations):
browser → Vite proxy → router → role dependency → service → engine (pure) →
Postgres → response. Typical latency: tens of milliseconds.

**Asynchronous path** (verify by document):

1. `POST /verify/upload` — router reads the body in capped chunks → `uploads.store()`
   sniffs magic bytes, writes the file, adds the row → audit row → **commit** →
   `get_queue().enqueue(...)` → returns `202 {job_id, upload_id}`.
2. Worker dequeues, opens **its own** session, runs the pipeline, writes the
   `Verification` row plus an audit row, returns the verification id.
3. Browser polls `GET /verify/jobs/{job_id}` every second until `done`, then
   navigates to `/verifications/{id}`.

The commit-before-enqueue ordering is required: the worker reads the upload by
id on a different connection, so the row must already be visible.

### 4.1.6 The one same-origin design decision

The frontend calls the API at a **relative** `/api/v1` path, and the Vite dev
server proxies `/api` to `API_PROXY_TARGET` (`http://api:8000` under Compose).
The browser therefore only ever talks to the origin it loaded from. The
consequence is that exposing the stack — VS Code port forwarding, a tunnel —
needs **one** public port (5173) rather than two, CORS is not in the request
path at all, and nothing breaks under HTTPS as mixed content.
`VITE_API_BASE_URL` remains as an absolute-URL escape hatch, and setting it
re-introduces the CORS requirement. Postgres (5432) and Redis (6379) are
published for local tooling only and must never be forwarded.

## 4.2 Data flow diagrams

### 4.2.1 Figure 4.3 — DFD Level 0 (context diagram)

```mermaid
flowchart LR
    ADM(["Administrator"])
    INST(["Institution user"])
    VER(["Verifier"])
    OPS(["Operator / CLI"])

    SYS["<b>0</b><br/>Authenticity Validator<br/>for Academia"]

    ADM -->|"institution details, audit filters"| SYS
    SYS -->|"generated password, statistics, audit rows"| ADM

    INST -->|"certificate fields, CSV file, revocation reason, decisions"| SYS
    SYS -->|"signed certificate + PDF, import report, request inbox"| INST

    VER -->|"certificate number, QR payload, document file, request note"| SYS
    SYS -->|"result + per-check evidence, field comparison, institution's answer"| VER

    OPS -->|"seed / backfill / prune commands"| SYS
    SYS -->|"command report"| OPS
```

### 4.2.2 Figure 4.4 — DFD Level 1

```mermaid
flowchart TB
    ADM(["Administrator"])
    INST(["Institution user"])
    VER(["Verifier"])

    P1["<b>1.0</b><br/>Authenticate<br/>& authorise"]
    P2["<b>2.0</b><br/>Manage<br/>institutions"]
    P3["<b>3.0</b><br/>Maintain<br/>registry"]
    P4["<b>4.0</b><br/>Issue signed<br/>certificate"]
    P5["<b>5.0</b><br/>Verify<br/>credential"]
    P6["<b>6.0</b><br/>Handle verification<br/>request"]
    P7["<b>7.0</b><br/>Record<br/>audit"]
    P8["<b>8.0</b><br/>Report<br/>& administer"]

    D1[("D1 institutions")]
    D2[("D2 users")]
    D3[("D3 certificates")]
    D4[("D4 verifications")]
    D5[("D5 uploads")]
    D6[("D6 review_cases<br/>+ review_messages")]
    D7[("D7 audit_log")]
    D8[("D8 keys/ · PEM files")]
    D9[("D9 ISSUED_DIR · PDFs")]

    ADM --> P1
    INST --> P1
    VER --> P1
    P1 --> D2
    P1 --> D1
    P1 --> P7

    ADM --> P2
    P2 --> D1
    P2 --> D2
    P2 --> D8
    P2 --> P7

    INST --> P3
    P3 --> D3
    P3 --> P4
    P4 --> D8
    P4 --> D9
    P4 --> D3
    P3 --> P7

    VER --> P5
    P5 --> D3
    P5 --> D1
    P5 --> D5
    P5 --> D9
    P5 --> D4
    P5 --> P7
    P5 -->|"result + evidence"| VER

    VER --> P6
    INST --> P6
    P6 --> D6
    P6 --> D4
    P6 --> D5
    P6 -->|"confirm & add"| P3
    P6 --> P7
    P6 -->|"institution's answer"| VER

    ADM --> P8
    P8 --> D7
    P8 --> D3
    P8 --> D4
    P8 --> D6
    P8 -->|"statistics, audit page"| ADM
```

### 4.2.3 Figure 4.5 — DFD Level 2: process 5.0, the upload verification pipeline

```mermaid
flowchart TB
    VER(["Verifier"])
    F5_1["<b>5.1</b> Sniff type<br/>from magic bytes"]
    F5_2["<b>5.2</b> Store file<br/>+ SHA-256 + expiry"]
    F5_3["<b>5.3</b> Enqueue job<br/>return 202"]
    F5_4["<b>5.4</b> Decode QR<br/>zxing 1x/2x/3x → pyzbar 1x/2x/3x"]
    F5_5["<b>5.5</b> Choose text source<br/>PDF text layer or OCR"]
    F5_6["<b>5.6</b> Mask QR +<br/>preprocess image"]
    F5_7["<b>5.7</b> Recognise text<br/>Tesseract, per-line confidence"]
    F5_8["<b>5.8</b> Match template<br/>+ extract fields"]
    F5_9["<b>5.9</b> Find candidate record<br/>QR → hash → number"]
    F5_10["<b>5.10</b> Evaluate<br/>6 checks, 9 rules, 3 bands"]
    F5_11["<b>5.11</b> Persist verification<br/>+ evidence + audit"]

    D5[("D5 uploads")]
    D3[("D3 certificates")]
    D4[("D4 verifications")]
    D7[("D7 audit_log")]
    DV[("uploads volume")]

    VER -->|"PDF / PNG / JPEG"| F5_1
    F5_1 -->|"415 if unrecognised"| VER
    F5_1 --> F5_2
    F5_2 --> DV
    F5_2 --> D5
    F5_2 --> F5_3
    F5_3 -->|"202 job_id"| VER
    F5_3 --> F5_4
    F5_4 -->|"original pixels"| F5_5
    F5_5 -->|"text layer ≥120 chars"| F5_8
    F5_5 -->|"image-only"| F5_6
    F5_6 --> F5_7
    F5_7 --> F5_8
    F5_8 --> F5_9
    F5_4 -.->|"AVA1 payload"| F5_9
    F5_2 -.->|"sha256"| F5_9
    F5_9 --> D3
    F5_9 --> F5_10
    F5_10 --> F5_11
    F5_11 --> D4
    F5_11 --> D7
    F5_11 -.->|"poll → result"| VER
```

## 4.3 UML diagrams

### 4.3.1 Figure 4.6 — Use-case diagram

```mermaid
flowchart LR
    ADM(["Administrator"])
    INST(["Institution user"])
    VER(["Verifier"])

    subgraph system["Authenticity Validator for Academia"]
        UC01(["UC-01 Sign in"])
        UC04(["UC-04 Register institution"])
        UC05(["UC-05 Deactivate institution"])
        UC07(["UC-07 Add certificate"])
        UC08(["UC-08 Bulk import CSV"])
        UC09(["UC-09 Download issued PDF"])
        UC10(["UC-10 Revoke certificate"])
        UC11(["UC-11 Verify by number"])
        UC13(["UC-13 Verify by upload"])
        UC15(["UC-15 Poll job"])
        UC16(["UC-16 Read result"])
        UC19(["UC-19 Request confirmation"])
        UC20(["UC-20 Request inbox"])
        UC21(["UC-21 Inspect document"])
        UC22(["UC-22 Ask for info"])
        UC24(["UC-24 Confirm genuine"])
        UC25(["UC-25 Confirm and add"])
        UC26(["UC-26 Record not issued"])
        UC27(["UC-27 View statistics"])
        UC28(["UC-28 Browse audit log"])
    end

    ADM --- UC01
    INST --- UC01
    VER --- UC01

    ADM --- UC04
    ADM --- UC05
    ADM --- UC09
    ADM --- UC16
    ADM --- UC20
    ADM --- UC21
    ADM --- UC27
    ADM --- UC28

    INST --- UC07
    INST --- UC08
    INST --- UC09
    INST --- UC10
    INST --- UC20
    INST --- UC21
    INST --- UC22
    INST --- UC24
    INST --- UC25
    INST --- UC26

    VER --- UC11
    VER --- UC13
    VER --- UC16
    VER --- UC19
    VER --- UC20

    UC13 -.->|"includes"| UC15
    UC19 -.->|"extends"| UC16
    UC25 -.->|"includes"| UC07
```

### 4.3.2 Figure 4.7 — Class diagram (domain model and engine)

```mermaid
classDiagram
    class Institution {
        +int id
        +str name
        +str code (unique, immutable)
        +str public_key (SPKI PEM, immutable)
        +bool is_active
        +datetime created_at
    }

    class User {
        +int id
        +str email (unique)
        +str password_hash (argon2)
        +str role
        +int institution_id (nullable)
        +bool is_active
    }

    class Certificate {
        +UUID id
        +str cert_number (unique, normalized)
        +int institution_id
        +str student_name
        +str roll_number
        +str programme
        +int year_of_passing
        +Decimal cgpa (nullable)
        +Decimal marks (nullable)
        +date issue_date
        +str file_sha256 (nullable)
        +str signature (Ed25519, b64url)
        +str status
        +datetime revoked_at (nullable)
    }

    class Verification {
        +UUID id
        +int verifier_id
        +str method
        +UUID certificate_id (nullable)
        +UUID upload_id (nullable)
        +str result
        +JSONB checks
        +JSONB extracted_fields
        +datetime created_at
        +cert_number() str
        +reviews() list
    }

    class Upload {
        +UUID id
        +str path
        +str sha256
        +str mime
        +datetime expires_at
    }

    class ReviewCase {
        +UUID id
        +UUID verification_id
        +int institution_id
        +int requested_by
        +str status
        +str note
        +str decision (nullable)
        +str decision_note (nullable)
        +int decided_by (nullable)
        +datetime decided_at
        +is_open() bool
    }

    class ReviewMessage {
        +UUID id
        +UUID case_id
        +int author_id
        +str body
        +datetime created_at
    }

    class AuditLog {
        +bigint id
        +int actor_id (nullable)
        +str action
        +str entity
        +str entity_id
        +JSONB meta
        +datetime created_at
    }

    class CertificateRecord {
        <<frozen dataclass>>
        +str cert_number
        +str institution_code
        +str student_name
        +str roll_number
        +str programme
        +int year_of_passing
        +cgpa
        +marks
        +date issue_date
    }

    class VerificationInput {
        <<frozen dataclass>>
        +VerificationMethod method
        +str cert_number
        +RegistryRecord record
        +QrPayload qr
        +UploadEvidence upload
        +Thresholds thresholds
    }

    class RegistryRecord {
        <<frozen dataclass>>
        +CertificateRecord record
        +str signature
        +str public_key_pem
        +str status
        +datetime revoked_at
        +str file_sha256
        +is_revoked() bool
        +field_value(name) str
    }

    class UploadEvidence {
        <<frozen dataclass>>
        +str sha256
        +str template
        +dict fields
        +bool has_text
    }

    class Thresholds {
        <<frozen dataclass>>
        +float min_field_confidence = 0.85
        +float min_discrepancy_confidence = 0.50
    }

    class Check {
        <<frozen dataclass>>
        +str name
        +CheckStatus status
        +str detail
        +FieldState state
        +as_dict() dict
    }

    class VerificationOutcome {
        <<frozen dataclass>>
        +VerificationResult result
        +list~Check~ checks
    }

    class OcrEngine {
        <<Protocol>>
        +str name
        +is_available() bool
        +recognise(image, lang) list~OcrLine~
    }

    class TesseractEngine {
        +str name = "tesseract"
        -int _psm = 6
        -int _oem = 3
    }

    class OcrLine {
        <<frozen dataclass>>
        +str text
        +float confidence
        +tuple bbox
    }

    class ExtractedField {
        <<frozen dataclass>>
        +str name
        +str value
        +str raw
        +float confidence
    }

    class Template {
        <<frozen dataclass>>
        +str name
        +tuple require_all
        +tuple require_any
        +tuple~FieldRule~ rules
        +matches(text) bool
    }

    class QrSymbol {
        <<frozen dataclass>>
        +str payload
        +tuple rect
        +str reader
        +int scale
        +is_certificate_payload() bool
    }

    Institution "1" --> "0..*" User
    Institution "1" --> "0..*" Certificate
    User "1" --> "0..*" Verification : runs
    Certificate "0..1" --> "0..*" Verification
    Upload "0..1" --> "0..*" Verification
    Verification "1" --> "0..*" ReviewCase
    ReviewCase "1" --> "0..*" ReviewMessage
    Institution "1" --> "0..*" ReviewCase : addressed to
    User "1" --> "0..*" ReviewCase : requested_by
    User "1" --> "0..*" AuditLog : actor

    VerificationInput --> RegistryRecord
    VerificationInput --> UploadEvidence
    VerificationInput --> Thresholds
    RegistryRecord --> CertificateRecord
    VerificationOutcome --> Check
    VerificationInput ..> VerificationOutcome : evaluate()
    OcrEngine <|.. TesseractEngine
    TesseractEngine --> OcrLine
    Template --> ExtractedField : produces
```

### 4.3.3 Figure 4.8 — Entity-Relationship diagram

```mermaid
erDiagram
    INSTITUTIONS ||--o{ USERS : "employs"
    INSTITUTIONS ||--o{ CERTIFICATES : "issues"
    INSTITUTIONS ||--o{ REVIEW_CASES : "is asked"
    USERS ||--o{ VERIFICATIONS : "runs"
    USERS ||--o{ REVIEW_CASES : "requests"
    USERS ||--o{ REVIEW_CASES : "decides"
    USERS ||--o{ REVIEW_MESSAGES : "writes"
    USERS ||--o{ AUDIT_LOG : "acts"
    CERTIFICATES |o--o{ VERIFICATIONS : "is subject of"
    UPLOADS |o--o{ VERIFICATIONS : "is evidence for"
    VERIFICATIONS ||--o{ REVIEW_CASES : "is escalated by"
    REVIEW_CASES ||--o{ REVIEW_MESSAGES : "contains"

    INSTITUTIONS {
        int id PK
        varchar name
        varchar code UK "immutable"
        text public_key "SPKI PEM, immutable"
        boolean is_active
        timestamptz created_at
    }
    USERS {
        int id PK
        varchar email UK
        varchar password_hash "argon2"
        varchar role "admin|institution|verifier"
        int institution_id FK "null unless institution"
        boolean is_active
    }
    CERTIFICATES {
        uuid id PK
        varchar cert_number UK "normalized"
        int institution_id FK
        varchar student_name
        varchar roll_number
        varchar programme
        int year_of_passing
        numeric cgpa "0-10, nullable"
        numeric marks "0-100, nullable"
        date issue_date
        varchar file_sha256 "nullable"
        text signature "Ed25519 b64url"
        varchar status "active|revoked"
        timestamptz revoked_at
        timestamptz created_at
    }
    VERIFICATIONS {
        uuid id PK
        int verifier_id FK
        varchar method "id|qr|upload"
        uuid certificate_id FK "nullable"
        uuid upload_id FK "nullable"
        varchar result "VERIFIED|MISMATCH|REVOKED|MANUAL_REVIEW"
        jsonb checks "ordered evidence list"
        jsonb extracted_fields "nullable"
        timestamptz created_at
    }
    UPLOADS {
        uuid id PK
        varchar path
        varchar sha256
        varchar mime
        timestamptz expires_at
        timestamptz created_at
    }
    REVIEW_CASES {
        uuid id PK
        uuid verification_id FK
        int institution_id FK
        int requested_by FK
        varchar status "pending|needs_info|closed"
        text note
        varchar decision "confirmed|confirmed_added|not_issued"
        text decision_note
        int decided_by FK
        timestamptz decided_at
        timestamptz created_at
        timestamptz updated_at
    }
    REVIEW_MESSAGES {
        uuid id PK
        uuid case_id FK
        int author_id FK
        text body
        timestamptz created_at
    }
    AUDIT_LOG {
        bigint id PK
        int actor_id FK "nullable"
        varchar action
        varchar entity
        varchar entity_id
        jsonb meta
        timestamptz created_at
    }
```

### 4.3.4 Figure 4.9 — Sequence diagram: issuing a certificate

```mermaid
sequenceDiagram
    actor I as Institution user
    participant R as POST /certificates
    participant S as certificates service
    participant SG as signing.py
    participant K as keys/CODE.pem
    participant P as pdf_issue.py
    participant FS as ISSUED_DIR
    participant DB as PostgreSQL

    I->>R: CertificateCreate (9 fields)
    R->>R: Pydantic validates + normalizes<br/>(IDs, text, grades, cross-field rules)
    R->>S: create_certificate(user, data)
    S->>DB: SELECT id WHERE cert_number = ?
    DB-->>S: none
    S->>K: load_private_key(code)
    K-->>S: Ed25519PrivateKey
    S->>SG: sign_record(key, CertificateRecord)
    SG->>SG: canonical_dict → sorted keys,<br/>(",", ":"), grades as "8.50"
    SG-->>S: base64url signature
    S->>P: build_certificate_pdf(data + signature)
    P->>P: watermark, border, fields,<br/>QR = AVA1|num|code|sig
    P-->>S: PDF bytes
    S->>S: file_sha256 = sha256(pdf)
    S->>DB: INSERT certificate (pending)
    S->>DB: INSERT audit_log certificate.create
    S->>FS: write temp file + os.replace
    FS-->>S: ok
    S->>DB: COMMIT
    Note over S,FS: On IntegrityError or OSError:<br/>ROLLBACK and delete written PDFs,<br/>so a file never outlives its row
    S-->>R: Certificate
    R-->>I: 201 CertificateOut
```

### 4.3.5 Figure 4.10 — Sequence diagram: verification by certificate number

```mermaid
sequenceDiagram
    actor V as Verifier
    participant R as POST /verify/id
    participant S as verifications service
    participant E as engine.evaluate (pure)
    participant DB as PostgreSQL

    V->>R: {cert_number: "nbit-2024-cs-0001"}
    R->>R: normalize_id → "NBIT2024CS0001"
    R->>R: require_role(VERIFIER, ADMIN)
    R->>S: verify_by_number(user, number)
    S->>DB: SELECT certificate WHERE cert_number = ?
    DB-->>S: Certificate + Institution (joined)
    S->>S: registry_record(cert) → RegistryRecord
    S->>E: evaluate(VerificationInput)
    E->>E: 1 registry_lookup → pass
    E->>E: 2 revocation → pass
    E->>E: 3 record_signature → Ed25519 verify → pass
    E->>E: 4 qr_signature → skipped (no payload)
    E->>E: 5 file_hash → skipped (no upload)
    E->>E: 6 field_match → skipped (no document)
    E->>E: _decide → rule 9 → VERIFIED
    E-->>S: VerificationOutcome(VERIFIED, 6 checks)
    S->>DB: INSERT verification (result + checks JSONB)
    S->>DB: INSERT audit_log verification.create
    S->>DB: COMMIT
    S-->>R: Verification
    R-->>V: 200 VerificationOut
    V->>V: redirect to /verifications/{id}
```

### 4.3.6 Figure 4.11 — Sequence diagram: verification by document upload

```mermaid
sequenceDiagram
    actor V as Verifier
    participant R as POST /verify/upload
    participant U as uploads service
    participant J as upload_jobs
    participant Q as Redis queue 'ocr'
    participant W as RQ worker
    participant X as OCR pipeline
    participant E as engine (pure)
    participant DB as PostgreSQL

    V->>R: multipart file (photo.jpg)
    R->>R: _read_capped — 256 kB chunks, limit+1
    R->>U: store(data)
    U->>U: sniff_type(first 8 bytes) → JPEG
    Note over U: 415 before writing if unrecognised
    U->>U: write UPLOAD_DIR/verify/{uuid}.jpg
    U->>DB: INSERT upload (sha256, mime, expires_at)
    R->>DB: INSERT audit_log upload.create
    R->>DB: COMMIT
    R->>Q: enqueue(verify_upload_job, upload_id, verifier_id)
    R-->>V: 202 {job_id, upload_id}

    loop every 1 s until settled
        V->>R: GET /verify/jobs/{job_id}
        R->>Q: Job.fetch + ownership check from meta
        R-->>V: {status: queued|running}
    end

    Q->>W: dequeue
    W->>W: SessionLocal() — its own session
    W->>X: extract(data, mime)
    X->>X: qr_scan.scan(original pixels)<br/>zxing 1x → AVA1 payload
    X->>X: mask QR, prepare(): perspective → gray →<br/>denoise → suppress_light → deskew → upscale → Otsu
    X->>X: Tesseract recognise → lines + confidences
    X->>X: match template "nbit" → extract fields
    X-->>W: ExtractedPage + ExtractionResult
    W->>DB: find record by QR number
    W->>E: evaluate(input with upload evidence + thresholds)
    E->>E: 6 checks; field_match.* per field, 3 bands
    E->>E: _decide → VERIFIED (QR valid, nothing differs)
    E-->>W: outcome
    W->>DB: INSERT verification (+ extracted_fields summary)
    W->>DB: INSERT audit_log verification.create
    W->>DB: COMMIT
    W-->>Q: return str(verification.id)

    V->>R: GET /verify/jobs/{job_id}
    R-->>V: {status: done, verification_id}
    V->>V: navigate to /verifications/{id}
```

### 4.3.7 Figure 4.12 — Sequence diagram: verification request, end to end

```mermaid
sequenceDiagram
    actor V as Verifier
    actor I as Institution user
    participant RV as POST /reviews
    participant SR as reviews service
    participant RD as GET /reviews/{id}/document
    participant RC as POST /reviews/{id}/decision
    participant SC as certificates service
    participant DB as PostgreSQL

    Note over V: Result is MANUAL_REVIEW
    V->>RV: {verification_id, institution_id?, note}
    RV->>SR: create_case(...)
    SR->>DB: verification owned by this verifier?
    SR->>SR: result in {MANUAL_REVIEW, MISMATCH}?
    SR->>SR: institution = record's own, else chosen active one
    SR->>DB: INSERT review_case (pending)
    Note over DB: partial unique index blocks<br/>a second open case → 409
    SR->>DB: INSERT audit_log review.create
    RV-->>V: 201 ReviewOut, redirect to /requests/{id}

    I->>RD: fetch document (blob, bearer token)
    RD->>SR: get_case — scoped to this institution
    RD-->>I: the uploaded file, inline

    I->>RC: {decision: "needs more info"} via /needs-info
    RC->>SR: ask_for_info — message + status needs_info
    V->>RV: POST /reviews/{id}/messages (reply)
    Note over SR: verifier's reply clears needs_info → pending

    I->>RC: {decision: "confirmed_added", certificate: {...}}
    RC->>SR: confirm_and_add(fields)
    SR->>SC: create_certificate(user, fields)
    SC->>SC: validate → sign → build PDF → store hash
    SC->>DB: INSERT certificate + audit
    SC-->>SR: Certificate
    Note over SR: certificate created BEFORE the case closes,<br/>so a failure leaves the case open to retry
    SR->>DB: UPDATE case → closed, confirmed_added
    SR->>DB: INSERT audit_log review.confirmed_added
    RC-->>I: 200 ReviewOut

    Note over V: Original verification is UNCHANGED.<br/>Result page now shows<br/>"Confirmed and added to the registry by NBIT".<br/>Re-verifying the number produces a NEW VERIFIED verification.
```

### 4.3.8 Figure 4.16 — State diagram: certificate lifecycle

```mermaid
stateDiagram-v2
    [*] --> active : create_certificate / import_csv<br/>(signed, PDF issued, hash stored)
    active --> revoked : POST /revoke<br/>reason required (≥3 chars)<br/>status + revoked_at set, reason audited
    revoked --> revoked : POST /revoke → 409 already_revoked
    note right of revoked
        The record, its Ed25519 signature
        and its issued PDF are left exactly
        as issued. A genuine QR still
        verifies; the status decides the
        result (REVOKED outranks even a
        byte-perfect file hash).
    end note
    active --> [*] : institution deleted<br/>(only if it never issued — otherwise 409)
```

### 4.3.9 Figure 4.17 — State diagram: review case lifecycle

```mermaid
stateDiagram-v2
    [*] --> pending : verifier escalates<br/>MANUAL_REVIEW or MISMATCH only<br/>at most one open case per verification
    pending --> needs_info : institution asks for more<br/>(message + status, one transaction)
    needs_info --> pending : <b>verifier</b> replies
    needs_info --> needs_info : institution replies again<br/>(still waiting on the verifier)
    pending --> closed : decision = confirmed
    pending --> closed : decision = confirmed_added<br/>(certificate created first)
    pending --> closed : decision = not_issued<br/>(reason REQUIRED)
    needs_info --> closed : any decision
    closed --> [*]
    note right of closed
        Terminal. A further question about
        the same document is a NEW request,
        so "what was answered, when, by whom"
        stays intact. A closed case does not
        block a fresh one.
    end note
```

### 4.3.10 Figure 4.23 — Authentication and token-refresh flow

```mermaid
sequenceDiagram
    actor U as User
    participant L as Login page
    participant AX as axios interceptors
    participant API as FastAPI
    participant DB as PostgreSQL

    U->>L: email + password
    L->>API: POST /auth/login
    API->>DB: SELECT user WHERE email = lower(trim(email))
    alt unknown email
        API->>API: verify against _DUMMY_HASH<br/>(constant-time appearance)
        API->>DB: INSERT audit auth.login_failed<br/>meta = {email_domain} only
        API-->>L: 401 invalid_credentials
    else wrong password / inactive user / inactive institution
        API->>DB: INSERT audit auth.login_failed
        API-->>L: 401 invalid_credentials (identical message)
    else valid
        API->>DB: INSERT audit auth.login {role}
        API-->>L: TokenPair (access 15 min, refresh 7 d)
        L->>L: tokenStore.set() → localStorage
    end

    U->>AX: any API call
    AX->>AX: attach Authorization: Bearer <access>
    AX->>API: request
    alt access token expired
        API-->>AX: 401
        AX->>API: POST /auth/refresh {refresh_token}
        Note over AX: one shared in-flight refresh<br/>for all concurrent 401s
        alt refresh valid and user still active
            API-->>AX: new TokenPair
            AX->>API: retry original request once (_retried)
            API-->>AX: 200
        else refresh invalid or user deactivated
            AX->>AX: tokenStore.clear()
            AX->>AX: dispatch ava:session-expired
            Note over AX: App.tsx clears the query cache<br/>and navigates to /login
        end
    end
```

## 4.4 Database design

Eight tables in PostgreSQL 16. All timestamps are `timestamptz` defaulting to
`now()`. Primary keys are `uuid` for the entities a client may reference by URL
(certificates, verifications, uploads, review cases and messages) and `integer`
identity columns for institutions and users; `audit_log` uses `bigint` because
it is the highest-volume table.

### 4.4.1 Table 4.2 — `institutions`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | integer | PK | Surrogate key |
| `name` | varchar(255) | not null | Display name; the only mutable field besides `is_active` |
| `code` | varchar(32) | **unique**, indexed, not null | Normalized short code (e.g. `NBIT`). **Immutable** — issued signatures refer to it |
| `public_key` | text | not null | Ed25519 public key, SubjectPublicKeyInfo PEM. **Immutable** |
| `is_active` | boolean | not null, default `true` | `false` blocks this institution's users from signing in while keeping its certificates verifiable |
| `created_at` | timestamptz | server default `now()` | — |

### 4.4.2 Table 4.3 — `users`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | integer | PK | — |
| `email` | varchar(255) | **unique**, indexed, not null | Login identity, stored lower-cased |
| `password_hash` | varchar(255) | not null | argon2 hash; plaintext never stored |
| `role` | varchar(20) | not null, `ck_users_role` | `admin` \| `institution` \| `verifier` |
| `institution_id` | integer | FK → `institutions.id` `ON DELETE RESTRICT`, nullable, indexed | Set only for institution users |
| `is_active` | boolean | not null, default `true` | `false` blocks login and invalidates existing tokens |

**Check constraints:**
```sql
ck_users_role             role IN ('admin', 'institution', 'verifier')
ck_users_institution_link (role = 'institution') = (institution_id IS NOT NULL)
```
The second is the interesting one: it makes "an institution user with no
institution" and "an admin attached to an institution" both unrepresentable.

### 4.4.3 Table 4.4 — `certificates`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | uuid | PK, default `uuid4()` | Used in URLs and as the issued PDF's filename |
| `cert_number` | varchar(64) | **unique**, indexed, not null | Stored in normalized ID form so a lookup never has to guess separators |
| `institution_id` | integer | FK → `institutions.id` RESTRICT, indexed, not null | Issuer |
| `student_name` | varchar(255) | not null | Original casing preserved (`clean_text`) |
| `roll_number` | varchar(64) | indexed, not null | Normalized ID form |
| `programme` | varchar(255) | not null | Original casing preserved |
| `year_of_passing` | integer | not null | Validated 1950 ≤ y ≤ current year |
| `cgpa` | numeric(4,2) | nullable | 0–10 scale |
| `marks` | numeric(5,2) | nullable | Percentage, 0–100 |
| `issue_date` | date | not null | Not future, not before `year_of_passing` |
| `file_sha256` | varchar(64) | nullable | SHA-256 of the issued PDF; null until issued |
| `signature` | text | not null | Ed25519 over the canonical record, base64url unpadded |
| `status` | varchar(16) | not null, default `active` | `active` \| `revoked` |
| `revoked_at` | timestamptz | nullable | — |
| `created_at` | timestamptz | server default `now()` | — |

**Check constraints:**
```sql
ck_certificates_status      status IN ('active', 'revoked')
ck_certificates_grade       cgpa IS NOT NULL OR marks IS NOT NULL
ck_certificates_revoked_at  (status = 'revoked') = (revoked_at IS NOT NULL)
```

### 4.4.4 Table 4.5 — `verifications`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | uuid | PK | The result's own URL |
| `verifier_id` | integer | FK → `users.id` RESTRICT, indexed, not null | Who ran it |
| `method` | varchar(16) | not null, `ck_verifications_method` | `id` \| `qr` \| `upload` |
| `certificate_id` | uuid | FK → `certificates.id` RESTRICT, nullable | Null when the lookup found nothing |
| `upload_id` | uuid | FK → `uploads.id` `ON DELETE SET NULL`, nullable | The document this verification read |
| `result` | varchar(16) | not null, indexed, `ck_verifications_result` | `VERIFIED` \| `MISMATCH` \| `REVOKED` \| `MANUAL_REVIEW` |
| `checks` | jsonb | not null, default `[]` | The ordered evidence list — the explainability payload |
| `extracted_fields` | jsonb | nullable | What the request carried, or the upload summary |
| `created_at` | timestamptz | indexed, server default `now()` | — |

The enum vocabularies in both check constraints are generated from the
engine's `StrEnum`s at import time, so the database and the domain cannot
drift. `upload_id` uses `SET NULL` rather than `RESTRICT` because an upload is
legitimately deleted by retention while its verification is permanent.

### 4.4.5 Table 4.6 — `uploads`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | uuid | PK | Also the stored filename stem |
| `path` | varchar(512) | not null | Absolute path under `UPLOAD_DIR/verify/` |
| `sha256` | varchar(64) | **indexed**, not null | Lower-case hex; the file-hash check looks certificates up by it |
| `mime` | varchar(64) | not null | Decided by magic bytes, not by the client |
| `expires_at` | timestamptz | **indexed**, not null | `created_at + UPLOAD_RETENTION_DAYS` |
| `created_at` | timestamptz | server default `now()` | — |

The extracted text is deliberately **not** stored on this row. What the OCR
read goes into `verifications.extracted_fields` as *fields*, never as the
document.

### 4.4.6 Table 4.7 — `review_cases`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | uuid | PK | — |
| `verification_id` | uuid | FK → `verifications.id` RESTRICT, indexed, not null | What is being asked about |
| `institution_id` | integer | FK → `institutions.id` RESTRICT, indexed, not null | Who is being asked |
| `requested_by` | integer | FK → `users.id` RESTRICT, not null | The verifier |
| `status` | varchar(16) | not null, default `pending` | `pending` \| `needs_info` \| `closed` |
| `note` | text | nullable | The verifier's opening note — kept on the case, not as a message, because it is why the request exists and is never replied to |
| `decision` | varchar(16) | nullable | `confirmed` \| `confirmed_added` \| `not_issued` |
| `decision_note` | text | nullable | **Required** for `not_issued` |
| `decided_by` | integer | FK → `users.id` RESTRICT, nullable | — |
| `decided_at` | timestamptz | nullable | — |
| `created_at` | timestamptz | indexed, server default `now()` | Used for the overdue (>7 days) count |
| `updated_at` | timestamptz | indexed, server default `now()` | Touched by every message and the decision, so the list orders by last activity without reading the thread |

**Constraints and the partial unique index:**
```sql
ck_review_cases_status               status IN ('pending','needs_info','closed')
ck_review_cases_decision             decision IS NULL OR decision IN (...)
ck_review_cases_decided_when_closed  (status = 'closed') = (decision IS NOT NULL)

CREATE UNIQUE INDEX uq_review_cases_open_per_verification
    ON review_cases (verification_id) WHERE status <> 'closed';
```
The partial index is the mechanism for "at most one *open* case per
verification". It is in the database rather than in a service check so that two
browser tabs cannot both open one; `create_case()` catches the resulting
`IntegrityError` and returns `409 request_already_open`.

### 4.4.7 Table 4.8 — `review_messages`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | uuid | PK | — |
| `case_id` | uuid | FK → `review_cases.id` **`ON DELETE CASCADE`**, indexed, not null | Owning case |
| `author_id` | integer | FK → `users.id` RESTRICT, not null | Either party |
| `body` | text | not null | 1–2000 characters, trimmed, non-blank |
| `created_at` | timestamptz | indexed, server default `now()` | Thread order |

### 4.4.8 Table 4.9 — `audit_log`

| Column | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | bigint | PK | High volume |
| `actor_id` | integer | FK → `users.id` RESTRICT, nullable, indexed | Null for a failed login (no known actor) |
| `action` | varchar(64) | **indexed**, not null | Dotted vocabulary; filtered by prefix |
| `entity` | varchar(64) | not null | `user` \| `institution` \| `certificate` \| `upload` \| `verification` \| `review_case` |
| `entity_id` | varchar(64) | nullable | String, because ids are of mixed type |
| `meta` | jsonb | not null, default `{}` | Identifiers, counts, hashes — **never** personal data |
| `created_at` | timestamptz | **indexed**, server default `now()` | — |

**The append-only trigger.** `UPDATE` and `DELETE` both raise, so the trail
cannot be rewritten even by a database superuser acting through the
application's role. This has a testing consequence recorded in the code: audit
rows can never be backdated, so tests that need historical rows insert them
with explicit timestamps rather than updating them afterwards.

### 4.4.9 Table 4.10 — Alembic migration history

| Order | Revision | Down-revision | Creates / alters |
|---|---|---|---|
| 1 | `3531d1b198b8` | *(none)* | `institutions`, `users`, 3 indexes |
| 2 | `e6949de4f85b` | `3531d1b198b8` | `certificates`, `audit_log`, 6 indexes, and 2 `op.execute(...)` calls installing the append-only function and trigger |
| 3 | `99cc3f63914a` | `e6949de4f85b` | `verifications`, 3 indexes |
| 4 | `f684a63bf24c` | `99cc3f63914a` | `institutions.is_active` column |
| 5 | `dd54d936907f` | `f684a63bf24c` | `uploads`, 2 indexes |
| 6 | `f83a9f1d224e` | `dd54d936907f` | `review_cases`, `review_messages`, 6 indexes, the partial unique index, and `verifications.upload_id` |

Run with `alembic upgrade head`. `alembic/env.py` takes the URL from
`DATABASE_URL` rather than from `alembic.ini`, so the same migrations run
against the demo and test databases without editing a file.

### 4.4.10 Relationship loading strategy

A detail worth noting because it affects query counts. Most relationships use
`lazy="joined"` so that a single query returns the row with everything the
response needs — `Certificate.institution`, `Verification.certificate`,
`Verification.verifier`, `ReviewCase.verification/institution/requester/decider`,
`AuditLog.actor`. Two are deliberately `lazy="select"`:
`Verification.upload` (only a review case ever needs the document row, and
every history query would otherwise join a table it ignores) and
`Verification.cases`.

## 4.5 Complete folder and file structure

```
final project/
├── CLAUDE.md                    Project specification, status, and the standing decision log
├── PROJECT.md                   This document
├── docker-compose.yml           Five services, health checks, volumes
├── .env.example                 Every environment variable, documented
├── .env                         Local configuration (gitignored)
├── .gitattributes               * text=auto eol=lf — CRLF breaks files inside Linux containers
├── .gitignore                   Secrets, keys, caches, node_modules, uploads
├── db/init/01-extensions.sql    pg_trgm + uuid-ossp, run once on first boot
├── keys/                        Ed25519 private keys, one PEM per institution code (gitignored)
│   ├── .gitkeep
│   ├── NBIT.pem                 The demo institution
│   └── 2111.pem, MBU.pem, RVS.pem   Left from development
├── samples/
│   ├── certificates-nbit-valid.csv        6 clean rows for an import demo
│   ├── certificates-nbit-with-errors.csv  7 rows exercising every validation failure
│   └── photos/                            THE evaluation set — 12 real phone photos
│       ├── sample1–10.jpeg, sample11–12.png
│       └── Actual_data.txt                Ground truth for the two photographed certificates
├── backend/
│   ├── Dockerfile               python:3.12-slim + tesseract + libzbar; libgl1 deliberately absent
│   ├── .dockerignore
│   ├── requirements.txt         Every dependency pinned, with reasoning in comments
│   ├── pyproject.toml           ruff (E,F,I,UP,B,SIM, line 100) + pytest config
│   ├── alembic.ini              script_location only; URL comes from env
│   ├── alembic/
│   │   ├── env.py               Reads DATABASE_URL; target_metadata = Base.metadata
│   │   ├── script.py.mako
│   │   └── versions/            6 migrations (Table 4.10)
│   ├── app/
│   │   ├── main.py              FastAPI app, CORS, 3 exception handlers, /health, router mount
│   │   ├── core/
│   │   │   ├── config.py        pydantic-settings; every tunable, env-only
│   │   │   ├── db.py            Engine, SessionLocal, Base, get_db() generator
│   │   │   ├── security.py      argon2 hashing + JWT create/decode with type checking
│   │   │   ├── deps.py          DbSession, CurrentUser, require_role() factory
│   │   │   └── errors.py        AppError(status, code, message, **extra)
│   │   ├── models/              SQLAlchemy models — all imported in __init__ for Alembic
│   │   │   ├── institution.py   Institution
│   │   │   ├── user.py          Role enum + User + 2 check constraints
│   │   │   ├── certificate.py   CertificateStatus + Certificate + 3 check constraints
│   │   │   ├── verification.py  Verification; imports the result enums FROM the engine
│   │   │   ├── upload.py        Upload
│   │   │   ├── review.py        ReviewStatus, ReviewDecision, ReviewCase, ReviewMessage
│   │   │   └── audit.py         AuditLog + the append-only function and trigger DDL
│   │   ├── schemas/             Pydantic request/response models
│   │   │   ├── common.py        Page[T] generic (items, total, page, size)
│   │   │   ├── auth.py          LoginRequest, RefreshRequest, TokenPair, UserOut
│   │   │   ├── institutions.py  Create/Update/Out/Created/Option
│   │   │   ├── certificates.py  CertificateFields (all validation), Create, ImportRow,
│   │   │   │                    CSV_COLUMNS, Out, RevokeRequest, import error models
│   │   │   ├── verify.py        VerifyById/Qr, UploadAccepted, JobStatusOut, CheckOut,
│   │   │   │                    VerificationOut, ReviewSummary, VerificationListItem
│   │   │   ├── reviews.py       ReviewCreate, MessageCreate, the 3-variant discriminated
│   │   │   │                    DecisionRequest union, ReviewOut, ReviewCounts
│   │   │   └── admin.py         AuditOut, ResultCounts, RecentCounts, AdminStats
│   │   ├── api/v1/              Thin routers
│   │   │   ├── router.py        Mounts the six routers (+ a note that `share` is pending)
│   │   │   ├── auth.py          login, refresh, me
│   │   │   ├── institutions.py  CRUD + /options (declared before /{id} so it is not an id)
│   │   │   ├── certificates.py  create, import, list, get, revoke, pdf
│   │   │   ├── verify.py        id, qr, upload (chunked read), jobs/{id}; + verifications router
│   │   │   ├── reviews.py       create, list, counts, get, document, messages, needs-info, decision
│   │   │   └── admin.py         audit, stats
│   │   ├── services/            All business logic
│   │   │   ├── audit.py         record() — one function, adds a row to the caller's transaction
│   │   │   ├── auth.py          authenticate, login (audited), issue_tokens, refresh_tokens
│   │   │   ├── institutions.py  CRUD, key-pair creation, password generation, delete rules
│   │   │   ├── certificates.py  create, CSV import (all-or-nothing), list, get, revoke,
│   │   │   │                    PDF issuance orchestration, backfill
│   │   │   ├── verifications.py registry_record(), by-number, by-QR, list, get
│   │   │   ├── uploads.py       magic-byte sniffing, store, held_upload_ids, prune_expired
│   │   │   ├── upload_jobs.py   submit (store→commit→enqueue), status (RQ → 4 states)
│   │   │   ├── upload_verification.py  the OCR→engine orchestration and evidence summary
│   │   │   ├── reviews.py       the whole verification-request workflow
│   │   │   ├── admin.py         list_audit (prefix + date range), stats
│   │   │   ├── normalize.py     PURE — text/ID/decimal/year/date normalization, confusables
│   │   │   ├── signing.py       PURE canonical record + Ed25519; key-file helpers touch disk
│   │   │   ├── qr.py            PURE payload build/parse + PNG generation
│   │   │   ├── hashing.py       PURE SHA-256 of bytes and of a file in chunks
│   │   │   ├── pdf_issue.py     ReportLab certificate + atomic write/delete
│   │   │   ├── verification/
│   │   │   │   └── engine.py    THE RULE ENGINE — 533 lines, pure, no I/O
│   │   │   └── ocr/
│   │   │       ├── __init__.py       Public surface so callers never import the engine directly
│   │   │       ├── engines.py        OcrEngine protocol, OcrLine, TesseractEngine, get_engine()
│   │   │       ├── qr_scan.py        The two-reader three-scale ladder
│   │   │       ├── preprocess.py     PURE OpenCV steps + prepare() + mask_regions()
│   │   │       ├── extract_text.py   PDF-text-layer vs OCR dispatch; QR read first
│   │   │       ├── fields.py         Template loading, matching, label-anchored extraction
│   │   │       └── templates/nbit.yaml   The one layout description
│   │   ├── adapters/__init__.py  EMPTY — registry_local.py and digilocker_mock.py
│   │   │                         are named in the spec but do not exist
│   │   ├── workers/
│   │   │   ├── worker.py        RQ worker entrypoint, queue "ocr"
│   │   │   ├── queue.py         Redis connection, Queue, JobState, RQ-status mapping
│   │   │   └── ocr_job.py       verify_upload_job — thin; opens its own session
│   │   └── scripts/
│   │       ├── seed.py          Demo institution + 3 users + 20 synthetic certificates
│   │       ├── backfill_pdfs.py Issue PDFs for rows that have none; idempotent
│   │       └── prune_uploads.py Retention + orphan cleanup, with --dry-run
│   └── tests/                   19 files, 308 test functions → 373 collected cases
│       ├── conftest.py          Separate <db>_test database, per-test rolled-back transaction,
│       │                        temp KEYS_DIR and ISSUED_DIR, users and auth_headers fixtures
│       ├── ocr_fixtures.py      Test documents GENERATED from the project's own issuance code
│       └── test_*.py            See Table 5.1
└── frontend/
    ├── Dockerfile               node:22-alpine, npm ci, vite dev server
    ├── package.json             Pinned deps; scripts dev/build/preview/lint/gen:api
    ├── tsconfig.json            strict, noUnusedLocals/Parameters, types: ["vite/client"]
    ├── vite.config.ts           React plugin, @ alias, polling watcher, /api proxy
    ├── tailwind.config.js        Theme tokens, container, animations
    ├── postcss.config.js
    ├── components.json          shadcn/ui generator configuration
    ├── index.html               Single #root div
    ├── scripts/gen-api.mjs      openapi-typescript runner; reads API_URL / API_PROXY_TARGET
    └── src/
        ├── main.tsx             QueryClientProvider + BrowserRouter + StrictMode
        ├── App.tsx              Route tree with nested role guards; session-expired listener
        ├── index.css            Tailwind layers, CSS theme variables, @media print rules
        ├── api/
        │   ├── client.ts        axios instance, bearer + refresh interceptors,
        │   │                    apiErrorMessage(), apiFieldErrors()
        │   └── schema.ts        GENERATED from OpenAPI — 2,454 lines, never hand-edited
        ├── lib/
        │   ├── tokens.ts        localStorage token store, try/catch guarded
        │   ├── download.ts      saveBlob() with deferred URL revocation
        │   └── utils.ts         cn() — clsx + tailwind-merge
        ├── hooks/
        │   ├── useAuth.ts       useMe, useLogin, useLogout
        │   ├── useCertificates.ts  list, create, import, download PDF, revoke
        │   ├── useInstitutions.ts  list, create, update, delete
        │   ├── useVerify.ts     byId, byQr (unused by UI), detail, list, upload, job polling
        │   ├── useReviews.ts    list, detail, counts, options, create, message, needs-info,
        │   │                    decide, document-as-blob; STATUS_LABEL / DECISION_LABEL
        │   ├── useAdmin.ts      stats, audit log
        │   ├── useDebounced.ts  Generic debounce for search inputs
        │   └── use-toast.ts     Toast reducer and dispatcher
        ├── components/
        │   ├── AppLayout.tsx    Header, role-filtered nav with the request badge, logout
        │   ├── ProtectedRoute.tsx  Token + role gate rendering an <Outlet/>
        │   ├── AddCertificateDialog.tsx   8-field create form with per-field errors
        │   ├── RevokeCertificateDialog.tsx  Reason-required confirmation
        │   ├── UploadDropzone.tsx  Drag/drop, file picker, separate camera input, local checks
        │   ├── VerificationResult.tsx  Banner, evidence path, details, check list
        │   ├── DocumentMatch.tsx   Discrepancy box, unread notice, match count
        │   ├── ExtractedFieldsTable.tsx  4-column document-vs-registry table + confidence badges
        │   ├── VerificationRequests.tsx  The institution's answer and the "ask" button
        │   ├── RequestConfirmationDialog.tsx  Institution pre-selected or chosen, plus a note
        │   ├── ConfirmAndAddForm.tsx  Prefilled, fully editable create form
        │   ├── AdminStatsCards.tsx    Statistic tiles, request counts, results breakdown
        │   └── ui/               shadcn/ui primitives: badge, button, card, dialog, input,
        │                         label, table, tabs, toast, toaster
        └── pages/               One page per route
            ├── Login.tsx
            ├── Dashboard.tsx
            ├── Certificates.tsx
            ├── ImportCertificates.tsx
            ├── Verify.tsx
            ├── VerificationDetail.tsx
            ├── MyVerifications.tsx
            ├── Requests.tsx
            ├── RequestDetail.tsx
            ├── Institutions.tsx
            └── AuditLog.tsx
```

### 4.5.1 Table 4.11 — Backend file purposes (summary)

| File | Lines | Purpose |
|---|---|---|
| `services/verification/engine.py` | 533 | The rule engine: 6 checks, 4 statuses, 9 decision rules, 3 confidence bands. Pure. |
| `services/reviews.py` | 464 | The verification-request workflow: scoping, state machine, three decisions. |
| `services/certificates.py` | 419 | Create, all-or-nothing CSV import, list/search, revoke, PDF orchestration, backfill. |
| `services/ocr/fields.py` | 317 | YAML template loading, matching, label-anchored and pattern extraction, value normalization. |
| `services/ocr/extract_text.py` | 288 | PDF-text-layer versus OCR dispatch; QR read first; the `ExtractedPage` contract. |
| `services/ocr/preprocess.py` | 271 | Eight pure OpenCV operations plus `prepare()` and `mask_regions()`. |
| `services/upload_verification.py` | 215 | Orchestrates upload → OCR → candidate lookup → engine → persistence. |
| `services/institutions.py` | 205 | Institution CRUD, key-pair creation, one-time password, delete-or-deactivate rules. |
| `services/ocr/qr_scan.py` | 203 | The measured two-reader, three-scale decode ladder. |
| `api/v1/reviews.py` | 200 | Eight review endpoints; `_as_detail()` assembles the per-viewer payload. |
| `services/pdf_issue.py` | 194 | ReportLab certificate rendering plus atomic file write/delete. |
| `services/ocr/engines.py` | 176 | `OcrEngine` protocol, `OcrLine`, `TesseractEngine`, TSV→line grouping. |
| `services/uploads.py` | 175 | Magic-byte sniffing, storage, retention hold, pruning. |
| `services/verifications.py` | 143 | `registry_record()` mapping plus the by-number and by-QR paths. |
| `services/signing.py` | 137 | Canonical record, Ed25519 sign/verify, key-file helpers. |
| `models/review.py` | 137 | Review enums, both tables, and the partial unique index. |
| `services/admin.py` | 121 | Audit listing by prefix and date range; the statistics aggregation. |
| `api/v1/verify.py` | 115 | Five verify endpoints including the chunked upload read. |
| `services/upload_jobs.py` | 108 | Submit and the RQ-status-to-four-states translation. |
| `scripts/prune_uploads.py` | 108 | Retention command with `--dry-run`, holds and orphan detection. |
| `models/verification.py` | 103 | The verification row plus the `reviews` and `cert_number` presentation properties. |
| `scripts/seed.py` | 131 | Idempotent demo data: institution, three users, 20 certificates. |
| `services/normalize.py` | ~95 | All normalization and confusable collapsing. Pure. |
| `services/qr.py` | ~95 | Payload build/parse and PNG generation. Pure. |
| `core/security.py` | ~95 | argon2 context and JWT creation/decoding with type enforcement. |
| `main.py` | 62 | App construction, CORS, three exception handlers, `/health`. |
| `core/deps.py` | ~60 | `get_current_user`, `require_role` factory, `DbSession` alias. |
| `services/hashing.py` | ~25 | SHA-256 of bytes and of a file in 1 MB chunks. Pure. |
| `services/audit.py` | ~22 | The single `record()` helper. |
| `core/errors.py` | ~14 | `AppError`. |

### 4.5.2 Table 4.12 — Frontend file purposes (summary)

| File | Lines | Purpose |
|---|---|---|
| `api/schema.ts` | 2,454 | **Generated** OpenAPI types — the contract, never hand-edited. |
| `pages/RequestDetail.tsx` | 391 | One case for all three roles: document preview, fields, registry match, thread, four actions. |
| `pages/Institutions.tsx` | 338 | Institution table, create dialog, the one-time password with copy, activate/deactivate, delete confirm. |
| `components/VerificationResult.tsx` | 287 | Result banner with five wordings, evidence path, certificate details, check list. |
| `components/ExtractedFieldsTable.tsx` | 233 | Field / document / registry / result table with confidence badges and "not checked" rows. |
| `pages/AuditLog.tsx` | 213 | Quick filters, action prefix, date range, paginated table. |
| `pages/Certificates.tsx` | 207 | Debounced search, registry table, PDF download, revoke trigger. |
| `pages/ImportCertificates.tsx` | 181 | CSV upload, template download, per-row error table. |
| `pages/Requests.tsx` | 171 | One list, three headings, five status filters. |
| `components/UploadDropzone.tsx` | 166 | Drag/drop, picker, separate camera input, staged busy states, local pre-checks. |
| `hooks/use-toast.ts` | 191 | Toast state reducer. |
| `hooks/useReviews.ts` | 158 | Every review query and mutation, plus the blob document fetch. |
| `pages/Verify.tsx` | 146 | Two tabs, upload job polling, redirect on completion. |
| `components/RequestConfirmationDialog.tsx` | 146 | Institution pre-selected or chosen from options, plus the note. |
| `components/AddCertificateDialog.tsx` | 143 | The eight-field create form. |
| `pages/MyVerifications.tsx` | 137 | Paginated history with result badges. |
| `components/DocumentMatch.tsx` | 130 | Discrepancy box, unread notice, match count. No percentage. |
| `components/ConfirmAndAddForm.tsx` | 129 | Prefilled editable create form inside a decision. |
| `components/AdminStatsCards.tsx` | 127 | Four tiles, request counts, results breakdown. |
| `components/VerificationRequests.tsx` | 102 | The institution's answer and the escalation button. |
| `components/AppLayout.tsx` | 101 | Header, role-filtered navigation, request badge, logout. |
| `App.tsx` | ~80 | Route tree with nested guards; lazy `Verify`; session-expired handling. |
| `api/client.ts` | ~95 | axios instance, token attachment, single-flight refresh, error helpers. |
| `components/ProtectedRoute.tsx` | ~40 | Token and role gate. |

## 4.6 Module-wise implementation

### 4.6.1 Module: Configuration and infrastructure (`app/core/`)

**Logic.** All tunables arrive from the environment through a single
`pydantic-settings` class with `extra="ignore"`, instantiated once behind
`@lru_cache`. Nothing in the codebase reads `os.environ` directly.

**Key code — the thresholds that drive the central algorithm:**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # ...
    # At or above this, a field that disagrees with the registry is a
    # conflict (MISMATCH); between the two, a possible discrepancy that blocks
    # VERIFIED and asks for review; below the lower one, the field counts as
    # not read at all.
    ocr_min_field_confidence: float = 0.85
    ocr_discrepancy_confidence: float = 0.50
    name_match_threshold: int = 90      # declared; currently unused
    name_conflict_threshold: int = 75   # declared; currently unused
```

**Session handling.** `db.py` creates one `Engine` with `pool_pre_ping=True`
and a `SessionLocal` factory with `autoflush=False, expire_on_commit=False`.
`expire_on_commit=False` matters because services return ORM objects *after*
committing and the routers then serialise them — with the default, every
attribute access after commit would trigger a fresh query.

**The role dependency**, applied on every protected route:

```python
def require_role(*roles: Role) -> Callable[[User], User]:
    """Dependency factory: `Depends(require_role(Role.ADMIN))`."""
    allowed = {r.value for r in roles}

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden", "message": "Your role cannot access this resource."},
            )
        return user
    return checker
```

`get_current_user` re-loads the user from the database on every request and
re-checks `is_active`, which is what makes deactivation take effect
immediately even though tokens are not stored server-side.

### 4.6.2 Module: Authentication (`app/services/auth.py`)

**Logic.** Authenticate, audit the attempt either way, issue tokens. Four
distinct rejection reasons are collapsed into one response.

```python
# Verified against when the email is unknown, so response time doesn't reveal
# which emails exist.
_DUMMY_HASH = hash_password("not-a-real-password")

def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash) or not user.is_active:
        return None
    # A deactivated institution keeps its certificates verifiable, but its
    # people can no longer sign in.
    if user.institution is not None and not user.institution.is_active:
        return None
    return user
```

**Privacy in the audit trail.** A failed login records the email's *domain*
and nothing else:

```python
def _email_domain(email: str) -> str:
    """Only the domain of a failed attempt is kept: enough to spot a pattern,
    not enough to build a list of who tried to sign in."""
    _, _, domain = normalize_email(email).partition("@")
    return domain or "unknown"
```

### 4.6.3 Module: Normalization (`app/services/normalize.py`)

**Logic.** Six pure functions that make equivalent inputs identical. They are
used on *both* the storage/signing side and the comparison side, which is the
property that matters — when the two sides normalized differently, every name
and programme conflicted.

```python
def clean_text(value: str) -> str:
    """Trim and collapse internal whitespace; keep case. Used for display/storage."""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", value)).strip()

def normalize_text(value: str) -> str:
    """Trim, collapse spaces, uppercase. Used for names and programmes."""
    return clean_text(value).upper()

def normalize_id(value: str) -> str:
    """Uppercase and strip everything except A–Z/0–9. For cert/roll numbers and codes."""
    return _NON_ALNUM.sub("", normalize_text(value))
```

**Grades.** `normalize_decimal` goes through `str()` before `Decimal` so that a
float like `8.1` does not carry binary noise into the value, and quantises to
two places with `ROUND_HALF_UP`. `format_decimal` produces the canonical
`"8.50"` string form used in the signed record.

**Confusable collapsing** — the design and the mistake it corrects are in
§2.2.10. The function is comparison-only and symmetric.

### 4.6.4 Module: Signing (`app/services/signing.py`)

Covered in §2.2.1. The implementation point worth repeating here is the
separation of pure from impure: `canonical_dict`, `canonical_bytes`,
`sign_record` and `verify_record` touch no filesystem;
`private_key_path`, `load_private_key` and `load_or_create_private_key` are the
only functions that do, and the latter creates the key with mode `0600`:

```python
def load_or_create_private_key(institution_code: str) -> Ed25519PrivateKey:
    path = private_key_path(institution_code)
    if path.exists():
        return load_private_key(institution_code)
    key = Ed25519PrivateKey.generate()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    path.chmod(0o600)
    return key
```

### 4.6.5 Module: The QR payload (`app/services/qr.py`)

**Logic.** Build and parse `AVA1|<number>|<code>|<signature>`, and render a
PNG. Parsing is strict and raises rather than guessing:

```python
def parse_payload(text: str) -> QrPayload:
    """Parse a scanned payload. Raises `QrPayloadError` on anything malformed."""
    if not isinstance(text, str) or not text.strip():
        raise QrPayloadError("Payload is empty.")
    parts = text.strip().split(SEPARATOR)
    if len(parts) != _PART_COUNT:
        raise QrPayloadError(
            f"Payload must have {_PART_COUNT} parts separated by '{SEPARATOR}', got {len(parts)}.")
    prefix, number, code, signature = (p.strip() for p in parts)
    if prefix.upper() != PREFIX:
        raise QrPayloadError(f"Unknown payload prefix {prefix!r}; expected {PREFIX}.")
    # Reuse build_payload's validation, then return the normalized pieces.
    build_payload(number, code, signature)
    return QrPayload(cert_number=normalize_id(number),
                     institution_code=normalize_id(code), signature=signature)
```

Each part is `.strip()`ped because a scanner may introduce whitespace — a case
pinned by `test_payload_survives_scanner_whitespace`.

### 4.6.6 Module: Certificate issuance (`app/services/certificates.py` + `pdf_issue.py`)

**Logic.** Validate → sign → render the PDF → hash it → insert the row → audit
→ write the file → commit, with compensating cleanup on failure.

**The transactional core**, which is the part most worth reading:

```python
def _commit_with_pdfs(db, pdfs, *, on_conflict):
    """Write the issued PDFs, then commit. If either step fails, roll back and
    remove whatever was written, so a stored file never outlives its row."""
    written: list[uuid.UUID] = []
    try:
        for cert_id, pdf in pdfs:
            write_issued_pdf(cert_id, pdf)
            written.append(cert_id)
        db.commit()
    except IntegrityError as exc:          # lost a race with a concurrent insert
        db.rollback()
        for cert_id in written:
            delete_issued_pdf(cert_id)
        raise on_conflict() from exc
    except OSError as exc:
        db.rollback()
        for cert_id in written:
            delete_issued_pdf(cert_id)
        raise AppError(500, "pdf_write_failed", "Could not store the issued certificate PDF.") from exc
```

**Never regenerate.** The reason is stated in the code itself:

```python
def issued_pdf(cert: Certificate) -> Path:
    """Path of the stored PDF for this certificate. Never regenerates: if the
    file is gone, say so rather than serving bytes with a different hash."""
    path = issued_pdf_path(cert.id)
    if cert.file_sha256 is None or not path.is_file():
        raise AppError(404, "pdf_not_available", "No issued PDF is stored for this certificate.")
    return path
```

**The PDF layout** (Figure 4.20 should be drawn from these coordinates): A4
landscape 297 × 210 mm; watermark rotated 26° at grey 0.88; double border at
12 mm and 14 mm; institution name at 22 pt centred 32 mm from the top;
institution code at 9 pt; a rule; `DEGREE CERTIFICATE` at 13 pt; "This is to
certify that"; the student name at 26 pt; "has successfully completed the
programme"; the programme at 16 pt; year and grade on one line; three boxed
label-above-value fields at x = 24 mm and y = 58/42/26 mm; the QR at 34 mm
square with its lower-left corner at (width − 24 mm − 34 mm, 28 mm); the "Scan
to verify" caption 5 mm below it; the footer at 18 mm.

The template file `nbit.yaml` and `_draw_field()` must be kept in step — the
YAML's anchors are exactly the labels this function prints.

### 4.6.7 Module: CSV import (`app/services/certificates.py: import_csv`)

**Logic — a three-pass, all-or-nothing algorithm.**

*Pass 1, header.* Reject the file if it is over `IMPORT_MAX_MB`, is not valid
UTF-8 (decoded as `utf-8-sig` so a BOM is tolerated), or if its header has any
missing or unknown column. Order does not matter.

*Pass 2, rows.* For each row: reject extra cells (`None in raw`), skip a blank
line made of commas, enforce `IMPORT_MAX_ROWS`, validate through
`CertificateImportRow`, convert Pydantic errors into
`{row, field, message}` with friendlier wording for dates, reject a row naming
another institution, and detect duplicates *within* the file while remembering
the first line each number appeared on.

*Pass 3, registry.* One `IN` query checks every candidate number against
existing rows.

Only if `errors` is empty does anything get inserted — and then every
certificate is built, signed with one loaded key, rendered to a PDF, and
committed together:

```python
    if errors:
        errors.sort(key=lambda e: e["row"])
        bad_rows = len({e["row"] for e in errors})
        raise _csv_invalid(
            f"{bad_rows} row(s) have errors. Nothing was imported — fix them and upload again.",
            errors)
    if not valid:
        raise _csv_invalid("The file has no data rows.")

    key = _signing_key(institution)
    certs = [_build(institution, key, row) for _, row in valid]
    pdfs = [(cert.id, _issue_pdf(institution, cert)) for cert in certs]
    db.add_all(certs)
    audit.record(db, actor_id=user.id, action="certificate.import", entity="certificate",
                 meta={"count": len(valid), "filename": filename,
                       "institution_code": institution.code})
    _commit_with_pdfs(db, pdfs, on_conflict=lambda: AppError(
        409, "duplicate_cert_number", "Some certificates were added meanwhile; upload again."))
    return len(valid)
```

Note the single audit row with a count, rather than one row per certificate —
`test_import_ok_inserts_all_and_audits_once` pins that.

### 4.6.8 Module: The verification engine (`app/services/verification/engine.py`)

This is the heart of the project. 533 lines, no imports that touch the
database, the network or the clock.

**Structure.** Frozen dataclasses for every input and output
(`VerificationInput`, `RegistryRecord`, `UploadEvidence`,
`ExtractedFieldValue`, `Thresholds`, `Check`, `VerificationOutcome`); one
private function per check; one `_decide()`; one public `evaluate()`.

**Table 4.13 — the six checks**

| Check | `pass` when | `fail` when | `skipped` when | `uncertain` when |
|---|---|---|---|---|
| `registry_lookup` | A record was found | No record for that number | — | — |
| `revocation` | Record not revoked | Record is revoked | No record | — |
| `record_signature` | Stored signature verifies against the institution's key | It does not | No record | — |
| `qr_signature` | QR signature verifies and names the right institution | It does not verify, or names another institution | No QR, or no record to check against | — |
| `file_hash` | Uploaded bytes equal the stored `file_sha256` | *never* | No upload, no record, or no stored hash | The bytes differ (a scan or re-save legitimately differs) |
| `field_match.<f>` | The value agrees | It differs at confidence ≥ 0.85 | — | It differs at 0.50–0.85, or could not be read |

**Table 4.15 — the three confidence bands**, implemented in `_compare_field`:

```python
    agrees = ids_match(found, expected) if name in _ID_FIELDS else found == expected
    if agrees:
        return Check(check_name, CheckStatus.PASS,
                     f"{label} matches the registry: {expected}.", state=FieldState.MATCHES)

    if extracted.confidence >= thresholds.min_field_confidence:
        return Check(check_name, CheckStatus.FAIL,
            f"{label} on the document is {found!r}, but the registry has {expected!r} "
            f"(read with {extracted.confidence:.0%} confidence).", state=FieldState.DIFFERS)

    if extracted.confidence >= thresholds.min_discrepancy_confidence:
        return Check(check_name, CheckStatus.UNCERTAIN,
            f"{label} on the document reads {found!r}, but the registry has {expected!r}. "
            f"At {extracted.confidence:.0%} confidence that is not certain enough to call a "
            "conflict, so it is a possible discrepancy for a person to look at.",
            state=FieldState.DIFFERS)

    return Check(check_name, CheckStatus.UNCERTAIN,
        f"{label} could not be read from the document — what was read ({found!r}) is only "
        f"{extracted.confidence:.0%} confident, too unsure to compare against the registry's "
        f"{expected}.", state=FieldState.NOT_READ)
```

**Table 4.14 — the decision rules, in the order they are evaluated.** The
*order* is the contribution; `conflicting` is tested **above** a valid QR.

| # | Condition | Result | Why |
|---|---|---|---|
| 1 | No record found | `MANUAL_REVIEW` | Nothing to compare against; not a verdict on the document |
| 2 | Record is revoked | `REVOKED` | The institution's own stated position outranks everything, including a byte-perfect hash |
| 3 | `qr_signature` failed | `MISMATCH` | A presented signature that does not verify |
| 4 | `record_signature` failed | `MISMATCH` | The registry row no longer matches what was issued |
| 5 | `file_hash` passed | `VERIFIED` | The exact issued bytes; anything OCR "read" off them is a reading error, not evidence |
| 6 | Any field conflicts (≥0.85 and differs) | `MISMATCH` | Catches a document edited after issue while keeping its original QR |
| 7 | Any field differs (≥0.50) | `MANUAL_REVIEW` | Too unsure to accuse, far too clear to verify |
| 8 | `qr_signature` passed | `VERIFIED` | Valid Ed25519 over the record, and nothing on the page contradicts it |
| 9 | Upload path: the certificate number was read **and** matched, and a template matched | `VERIFIED` else `MANUAL_REVIEW` | Without a signature the page must identify itself |
| 10 | No upload (number or QR alone) and the number matched | `VERIFIED` | — |

```python
    if data.record is None:
        return VerificationResult.MANUAL_REVIEW
    if data.record.is_revoked:
        return VerificationResult.REVOKED
    if status[CHECK_QR_SIGNATURE] is CheckStatus.FAIL:
        return VerificationResult.MISMATCH
    if status[CHECK_RECORD_SIGNATURE] is CheckStatus.FAIL:
        return VerificationResult.MISMATCH
    if status[CHECK_FILE_HASH] is CheckStatus.PASS:
        return VerificationResult.VERIFIED
    if conflicting:
        return VerificationResult.MISMATCH
    if differing:
        return VerificationResult.MANUAL_REVIEW
    if status[CHECK_QR_SIGNATURE] is CheckStatus.PASS:
        return VerificationResult.VERIFIED
    if data.upload is not None:
        if number_matched and not unreadable:
            return VerificationResult.VERIFIED
        return VerificationResult.MANUAL_REVIEW
    if matched or not field_checks:
        return VerificationResult.VERIFIED
    return VerificationResult.MANUAL_REVIEW
```

**Figure 4.13 — the decision flowchart:**

```mermaid
flowchart TD
    A["evaluate(VerificationInput)"] --> B["Run 6 checks<br/>in stable order"]
    B --> C{"record found?"}
    C -- no --> MR1["MANUAL_REVIEW<br/>nothing to compare"]
    C -- yes --> D{"status = revoked?"}
    D -- yes --> RV["REVOKED"]
    D -- no --> E{"qr_signature<br/>= fail?"}
    E -- yes --> MM1["MISMATCH"]
    E -- no --> F{"record_signature<br/>= fail?"}
    F -- yes --> MM2["MISMATCH<br/>registry row altered"]
    F -- no --> G{"file_hash<br/>= pass?"}
    G -- yes --> V1["VERIFIED<br/>exact issued bytes"]
    G -- no --> H{"any field conflicts?<br/>differs AND c ≥ 0.85"}
    H -- yes --> MM3["MISMATCH<br/>+ field diff shown"]
    H -- no --> I{"any field differs?<br/>c ≥ 0.50"}
    I -- yes --> MR2["MANUAL_REVIEW<br/>'Possible discrepancy'"]
    I -- no --> J{"qr_signature<br/>= pass?"}
    J -- yes --> V2["VERIFIED<br/>unread fields listed, not blocking"]
    J -- no --> K{"was there an upload?"}
    K -- yes --> L{"cert_number read AND matched,<br/>and a template matched?"}
    L -- yes --> V3["VERIFIED"]
    L -- no --> MR3["MANUAL_REVIEW"]
    K -- no --> M{"the number matched?"}
    M -- yes --> V4["VERIFIED"]
    M -- no --> MR4["MANUAL_REVIEW"]
```

### 4.6.9 Module: The QR decode ladder (`app/services/ocr/qr_scan.py`)

**Logic.** Try two readers at three scales, stop at the first *AVA1* payload,
and translate any rectangle found on an upscaled copy back into the original
image's coordinates so the caller can mask the code on its own image.

```python
def scan(image: np.ndarray) -> list[QrSymbol]:
    fallback: list[QrSymbol] = []
    for reader, read in _READERS:               # zxing first, then pyzbar
        for scale in SCALES:                    # 1, 2, 3
            scaled = _upscaled(image, scale)    # None if > 40 MP
            if scaled is None:
                continue
            try:
                found = read(scaled)
            except Exception:
                logger.debug("%s failed at %dx", reader, scale, exc_info=True)
                continue
            if not found:
                continue
            symbols = [QrSymbol(payload=p, rect=_shrink(r, scale), reader=reader, scale=scale)
                       for p, r in found]
            if any(s.is_certificate_payload for s in symbols):
                logger.info("QR read by %s at %dx", reader, scale)
                return symbols
            if not fallback:
                fallback = symbols
    return fallback
```

**Figure 4.14 — the ladder:**

```mermaid
flowchart TD
    S["scan(original image)"] --> Z1["zxing-cpp @ 1x"]
    Z1 -->|AVA1 found| OUT["return symbols<br/>record reader + scale"]
    Z1 -->|nothing / other code| Z2["zxing-cpp @ 2x"]
    Z2 -->|AVA1| OUT
    Z2 --> Z3["zxing-cpp @ 3x"]
    Z3 -->|AVA1| OUT
    Z3 --> P1["pyzbar @ 1x"]
    P1 -->|AVA1| OUT
    P1 --> P2["pyzbar @ 2x"]
    P2 -->|AVA1| OUT
    P2 --> P3["pyzbar @ 3x"]
    P3 -->|AVA1| OUT
    P3 -->|nothing| FB["return the first non-AVA1<br/>codes found, if any —<br/>still worth masking before OCR"]
    Z2 -.->|"skip if h·w·s² > 40 MP"| Z3
```

**Table 4.18 — the measurement that fixed this order** (12 phone photographs
of 2 printed certificates):

| Reader | Read at 1× | Read at 2× | Failures | Time |
|---|---|---|---|---|
| zxing-cpp | 11 / 12 | 12 / 12 | none | 1–43 ms |
| pyzbar | 2 / 12 | 10 / 12 | never read `sample3` at any scale | 12–242 ms |

pyzbar is kept rather than removed because the two libraries do not fail on
the same images and it was already a dependency.

### 4.6.10 Module: Image preprocessing (`app/services/ocr/preprocess.py`)

**Figure 4.15 — the pipeline:**

```mermaid
flowchart LR
    IN["BGR image<br/>as uploaded"] --> M["mask_regions()<br/>paint QR white"]
    M --> P["correct_perspective()<br/>quad 35–98% of frame"]
    P --> G["to_grayscale()"]
    G --> D["denoise()<br/>fastNlMeansDenoising h=7"]
    D --> L["suppress_light()<br/>pixels ≥205 → 255<br/>removes SPECIMEN watermark"]
    L --> K["deskew()<br/>minAreaRect angle<br/>0.1° < |a| < 15°"]
    K --> U["upscale_if_small()<br/>to 1200 px wide, cubic"]
    U --> T["threshold()<br/>global Otsu"]
    T --> OUT["binary image<br/>→ Tesseract"]
```

**Guard rails, each with a stated reason in the code:**

```python
MAX_DESKEW_DEGREES = 15.0   # a larger estimate means the angle finder locked
                            # onto something that is not the text baseline
MIN_DESKEW_DEGREES = 0.1    # below this the angle is noise
MIN_PAGE_AREA_RATIO = 0.35  # a smaller quad is not the page outline
LIGHT_CUTOFF = 205          # the watermark sits at about 224
```

The masking function is the highest-value single step in the module:

```python
def mask_regions(image, regions, *, margin: int = 6) -> np.ndarray:
    """Paint rectangles white on a copy of the image.

    Used to take the QR code out of the page before OCR. A QR sits in the same
    horizontal band as the certificate's boxed fields, and a page-level
    segmentation reads its modules as glyphs on those baselines — appending
    noise like "rat a" to the value next to it and dragging the line's
    confidence down with it. The payload is decoded separately, so nothing is
    lost by blanking it here.
    """
```

Measured effect: mean line confidence rose from 0.77 to 0.92 and every field
was fixed.

### 4.6.11 Module: Text extraction (`app/services/ocr/extract_text.py`)

**Logic.** Two paths behind one `ExtractedPage` contract, with the QR read
before either.

```python
def extract(data: bytes, mime: str, *, engine: OcrEngine | None = None) -> ExtractedPage:
    """Extract text and QR payloads from an uploaded document.

    Never raises for an unreadable document: an empty `ExtractedPage` is a
    legitimate outcome that the engine turns into MANUAL_REVIEW.
    """
    try:
        if mime == MIME_PDF:
            return extract_from_pdf(data, engine=engine)
        return extract_from_image(data, engine=engine)
    except Exception:
        logger.exception("extraction failed for a %s upload of %d bytes", mime, len(data))
        return ExtractedPage(lines=[], source=TextSource.NONE)
```

**The image path**, showing the ordering that the whole design rests on:

```python
def extract_from_image_array(image, *, engine=None) -> ExtractedPage:
    ocr = engine or get_engine()
    symbols = decode_qr(image)          # FIRST, on the original pixels
    qr_payloads = [s.payload for s in symbols]
    won = _winning_symbol(symbols)
    if not ocr.is_available():
        logger.error("no OCR engine available; returning no text")
        return ExtractedPage(lines=[], source=TextSource.NONE, qr_payloads=qr_payloads, ...)
    # Blank the QR before OCR: its modules would otherwise be read as text on
    # the same baselines as the boxed fields beside it.
    regions = [s.rect for s in symbols if s.rect[2] > 0 and s.rect[3] > 0]
    prepared = prepare(mask_regions(image, regions))
    lines = ocr.recognise(prepared)
    return ExtractedPage(lines=lines, source=TextSource.OCR if lines else TextSource.NONE, ...)
```

**The PDF path** prefers the text layer, with a threshold that distinguishes a
real text layer from a scanner's stamp:

```python
MIN_TEXT_LAYER_CHARS = 120   # a scanned PDF often carries a handful of stray
                             # characters from the scanner's own stamp
TEXT_LAYER_CONFIDENCE = 1.0  # digital text is exact, not an estimate
RENDER_DPI = 300             # what Tesseract is tuned for
```

For the QR inside a PDF, embedded images are tried first — the code at the
resolution it was issued at, with no rasterising in between — and the rendered
page only if none of them carries a certificate payload.

### 4.6.12 Module: Field extraction (`app/services/ocr/fields.py`)

**Logic.** Match a template by its markers, then apply one rule per field.
Return nothing at all if no template matches.

```python
def extract_fields(lines, *, templates=None) -> ExtractionResult:
    text = "\n".join(line.text for line in lines)
    template = match_template(text, templates)
    if template is None:
        logger.info("no OCR template matched a document of %d lines", len(lines))
        return ExtractionResult(template=None, fields={})

    fields: dict[str, ExtractedField] = {}
    for rule in template.rules:
        found = (_apply_anchor_rule(lines, rule) if rule.anchor is not None
                 else _apply_pattern_rule(lines, rule))
        if found is None:
            continue
        raw, confidence = found
        value = normalize_value(raw, rule.normalize)
        if value is None:
            continue
        fields[rule.name] = ExtractedField(
            name=rule.name, value=value, raw=clean_text(raw), confidence=confidence)
    return ExtractionResult(template=template.name, fields=fields)
```

**The ID normalizer and why it takes one token:**

```python
        case Normalizer.ID:
            # First whitespace token only. OCR of our own certificates picks up
            # the diagonal watermark as trailing words on the same line
            # ("NBIT2024CS0001 rat a"), and an identifier never contains a space.
            value = normalize_id(text.split()[0]) if text.split() else ""
            return value or None
```

**Table 4.17 — the `nbit.yaml` rules**

| Field | Rule kind | Anchor / pattern | Normalizer |
|---|---|---|---|
| `cert_number` | anchor, next line | `CERTIFICATE NUMBER` | `id` |
| `roll_number` | anchor, next line | `ROLL NUMBER` | `id` |
| `student_name` | anchor, next line | `This is to certify that` | `text` |
| `programme` | anchor, next line | `has successfully completed the programme` | `text` |
| `issue_date` | pattern | `([0-9]{4}-[0-9]{2}-[0-9]{2})` | `date` |
| `institution_code` | pattern | `Institution code\s+([A-Za-z0-9]+)` | `id` |
| `year_of_passing` | pattern | `Year of passing\s+([0-9]{4})` | `year` |
| `cgpa` | pattern | `CGPA\s*([0-9]{1,2}(?:[.,][0-9]{1,2})?)` | `decimal` |
| `marks` | pattern | `Marks\s*([0-9]{1,3}(?:[.,][0-9]{1,2})?)\s*%` | `decimal` |

Template match requires `DEGREE CERTIFICATE` **and** at least one of
`Institution code`, `CERTIFICATE NUMBER`, `This is to certify that` — the
second condition rules out an unrelated page that happens to carry the
heading.

### 4.6.13 Module: Upload verification orchestration (`app/services/upload_verification.py`)

**Logic.** The I/O around the pure engine: read the file, run extraction, find
a candidate record by three successively weaker hints, evaluate, persist.

```python
    cert = None
    if qr is not None:
        cert = _by_number(db, qr.cert_number)
    if cert is None:
        cert = _by_file_hash(db, upload.sha256)
    if cert is None and (number := extraction.value("cert_number")):
        cert = _by_number(db, number)
```

All three are **untrusted hints about which record to compare against**. None
decides anything — the engine does that from the record it is given.

**What is persisted as evidence** — note what is absent:

```python
    summary: dict[str, object] = {
        "file_sha256": upload.sha256,
        "mime": upload.mime,
        "text_source": page.source.value,
        "template": extraction.template,
        "ocr_engine": page.engine,
        "line_count": len(page.lines),
        "mean_line_confidence": round(page.mean_confidence, 4),
        "fields": {name: f.as_dict() for name, f in extraction.fields.items()},
    }
    if qr is not None:
        summary["qr_present"] = True
        summary["cert_number"] = qr.cert_number
        summary["institution_code"] = qr.institution_code
        # How hard the code was to read: which of the two readers got it, and
        # at what upscale. A 3x hit means the photo was marginal.
        summary["qr_reader"] = page.qr_reader
        summary["qr_scale"] = page.qr_scale
```

The document's full text is never stored, and neither is the file content.

### 4.6.14 Module: Background jobs (`app/workers/`)

**The job is deliberately thin**, because it is the hardest code to test:

```python
def verify_upload_job(upload_id: str, verifier_id: int) -> str:
    """Verify an uploaded document; return the verification id as a string.

    Arguments are plain types because RQ pickles them into Redis: a UUID or an
    ORM object would couple the queue to this process's classes.

    Any exception propagates, which is what marks the RQ job failed — the API
    reports that as `{"status": "failed"}` rather than inventing a result.
    """
    db = SessionLocal()
    try:
        upload, verifier = upload_verification.load_for_job(db, uuid.UUID(upload_id), verifier_id)
        verification = upload_verification.verify_upload(db, upload, verifier)
        return str(verification.id)
    finally:
        db.close()
```

**The status mapping**, narrower than RQ's own vocabulary on purpose:

```python
_STATE_BY_RQ_STATUS = {
    "queued": JobState.QUEUED, "deferred": JobState.QUEUED, "scheduled": JobState.QUEUED,
    "started": JobState.RUNNING, "finished": JobState.DONE,
    "failed": JobState.FAILED, "canceled": JobState.FAILED, "stopped": JobState.FAILED,
}

def state_for(rq_status: str | None) -> JobState:
    if rq_status is None:
        return JobState.FAILED
    return _STATE_BY_RQ_STATUS.get(rq_status, JobState.FAILED)
```

An unmapped status becomes `failed` so a client can never poll for ever.

### 4.6.15 Module: Verification requests (`app/services/reviews.py`)

**Logic.** Scoping, a state machine, and three decisions. The scoping function
is one place and every query uses it:

```python
def _visible(case: ReviewCase, user: User) -> bool:
    if user.role == Role.ADMIN:
        return True
    if user.role == Role.INSTITUTION:
        return case.institution_id == user.institution_id
    return case.requested_by == user.id

def _may_write(case: ReviewCase, user: User) -> bool:
    """An admin reads; the two parties write."""
    if user.role == Role.ADMIN:
        return False
    return _visible(case, user)
```

**The needs-info round trip**, in one condition:

```python
    # A verifier answering a question puts the ball back in the institution's
    # court, which is what `needs_info -> pending` means.
    if case.status == ReviewStatus.NEEDS_INFO.value and user.role != Role.INSTITUTION:
        case.status = ReviewStatus.PENDING.value
```

**"Confirm & add" goes through the ordinary create service**, and the ordering
is a correctness property:

```python
def confirm_and_add(db, user, case_id, fields) -> tuple[ReviewCase, Certificate]:
    case = _institution_case(db, user, case_id)
    cert = certificates.create_certificate(db, user, fields)
    return (_close(db, user, case, ReviewDecision.CONFIRMED_ADDED, decision_note=None,
                   meta={"certificate_id": str(cert.id), "cert_number": cert.cert_number}), cert)
```

The certificate is created **first**: if it fails (a duplicate number, a
missing signing key) the case stays open and the institution can correct the
form, so a closed case can never exist without its record.

### 4.6.16 Module: Upload storage and retention (`app/services/uploads.py`)

**Magic-byte sniffing**, ordered longest-prefix-first so no signature can be
shadowed:

```python
_SIGNATURES: tuple[tuple[bytes, FileType], ...] = (
    (b"\x89PNG\r\n\x1a\n", FileType(MIME_PNG, ".png")),
    (b"%PDF-", FileType(MIME_PDF, ".pdf")),
    (b"\xff\xd8\xff", FileType(MIME_JPEG, ".jpg")),
)
SNIFF_BYTES = max(len(sig) for sig, _ in _SIGNATURES)
```

**The retention hold** for open review cases:

```python
def held_upload_ids(db: Session) -> set[uuid.UUID]:
    return set(db.scalars(
        select(Verification.upload_id)
        .join(ReviewCase, ReviewCase.verification_id == Verification.id)
        .where(Verification.upload_id.is_not(None),
               ReviewCase.status != ReviewStatus.CLOSED.value)))
```

### 4.6.17 Module: Frontend API client (`frontend/src/api/client.ts`)

**Single-flight refresh.** All concurrent 401s share one refresh promise, and
each request is retried at most once:

```typescript
let refreshing: Promise<string> | null = null;
// ...
      refreshing ??= refreshAccessToken().finally(() => { refreshing = null; });
      const token = await refreshing;
      config._retried = true;
      config.headers.Authorization = `Bearer ${token}`;
      return api(config);
```

The login and refresh endpoints are excluded from the interceptor, otherwise a
failed login would trigger a refresh attempt.

### 4.6.18 Module: The result page (`frontend/src/components/`)

**Deriving the evidence path from the checks** rather than sending it as its
own field — so it cannot contradict the verdict:

```typescript
function pathUsed(verification: Verification): string | null {
  if (verification.method !== 'upload') return null;
  const statusOf = (name: string) => verification.checks.find((c) => c.name === name)?.status;
  const compared = verification.checks.some(
    (c) => c.name.startsWith('field_match.') && c.status === 'pass');
  const verb = verification.result === 'VERIFIED' ? 'Verified' : 'Checked';

  if (statusOf('file_hash') === 'pass')
    return `${verb} by the file itself — these are the exact bytes the institution issued.`;
  if (statusOf('qr_signature') === 'pass')
    return `${verb} by the signed QR code on the document; its printed text was read as a cross-check.`;
  if (compared)
    return `${verb} by reading the printed text — no signed QR could be read from this document.`;
  return 'Neither a signed QR nor a known layout could be read from this document, so nothing was decided from it.';
}
```

**Reading `state` before `status`**, which is where the distinction earns its
keep:

```typescript
function outcomeOf(verification: Verification, name: string) {
  const check = verification.checks.find((c) => c.name === `field_match.${name}`);
  if (!check) return null;
  if (check.state === 'not_read') return 'not_read';
  if (check.state === 'differs') return check.status === 'fail' ? 'fail' : 'differs';
  if (check.state === 'matches') return 'pass';
  return (check.status as keyof typeof STATUS_STYLES) ?? null;
}
```

**No percentage**, stated in the component's own documentation:

```typescript
/**
 * How the document compares with the registry, field by field.
 *
 * Three things a verifier needs before anything else: what disagrees, what
 * could not be read, and the count. Deliberately no overall percentage — a
 * document is not 80% genuine, and a single differing CGPA matters more than
 * six fields that happen to match.
 */
```

## 4.7 Algorithms and concepts used

### 4.7.1 Algorithm 1 — Canonical record signing

**Purpose.** Produce a signature that depends on the *meaning* of a
certificate's fields and on nothing else — not on key order, whitespace,
letter case, punctuation in identifiers, or a platform's float formatting.

**Steps.**
1. Collect the nine fields into a `CertificateRecord`.
2. Normalize each: identifiers upper-cased with non-alphanumerics stripped;
   names and programmes upper-cased with whitespace collapsed; the year as an
   integer; grades as two-decimal **strings** or `null`; the date as ISO
   `YYYY-MM-DD`.
3. Serialise to JSON with `sort_keys=True`, `separators=(",", ":")`,
   `ensure_ascii=False`, encoded UTF-8.
4. Sign those exact bytes with the institution's Ed25519 private key.
5. Encode the 64-byte signature as base64url and strip `=` padding.

**Verification** repeats steps 1–3 from the *stored* row and checks the
signature against the institution's public key. Because step 2 is
deterministic, a row altered in any of the nine fields cannot produce the
stored signature.

### 4.7.2 Algorithm 2 — The QR decode ladder

**Purpose.** Recover the signature from a photograph as cheaply as possible.

**Steps.**
1. For each reader in (zxing-cpp, pyzbar) and each scale in (1, 2, 3):
   a. Skip the scale if height × width × scale² > 40,000,000 pixels.
   b. Upscale by cubic interpolation (a no-op at 1×).
   c. Decode; swallow any exception and continue.
   d. Convert each result's rectangle back to original coordinates by integer
      division by the scale.
   e. If any payload parses as a valid AVA1 payload, return immediately.
   f. Otherwise remember the first non-AVA1 codes found as a fallback.
2. Return the fallback (still worth masking before OCR) or an empty list.

**Why it stops at AVA1 rather than at any code:** a page may carry a library
sticker or a printer barcode, and climbing one more rung costs milliseconds
compared with losing the signature.

### 4.7.3 Algorithm 3 — Image preparation

**Purpose.** Give the recogniser the cleanest plausible version of the page,
without destroying it.

**Steps.** (All on numpy arrays; each step is individually testable.)
1. **Mask** the QR rectangles white, with a 6-pixel margin, clipped to the
   image.
2. **Perspective**: blur, Canny edge detection, dilate to close gaps, take the
   five largest contours, and accept the first that approximates to four points
   and covers 35–98 % of the frame; order its corners as TL/TR/BR/BL by
   coordinate sums and differences; warp onto a rectangle.
3. **Grayscale**.
4. **Denoise** by non-local means (h = 7) — not a Gaussian blur, which would
   smear JPEG artefacts into the strokes.
5. **Suppress light**: every pixel ≥ 205 becomes 255, removing the watermark.
6. **Deskew**: invert, Otsu-threshold, take the minimum-area rectangle around
   the non-zero pixels, map the angle onto the nearest axis, and rotate only if
   0.1° < |angle| < 15°, expanding the canvas and filling it white.
7. **Upscale** to at least 1200 px wide by cubic interpolation.
8. **Threshold** by global Otsu.

### 4.7.4 Algorithm 4 — Line grouping and confidence

**Purpose.** Turn Tesseract's per-word output into lines with a usable
confidence.

**Steps.**
1. For each word with non-blank text, form the key
   `(block_num, par_num, line_num)` and group indices by it, preserving first
   appearance order.
2. For each group: join the words with single spaces and collapse runs of
   whitespace.
3. Average only the words whose `conf` ≥ 0 (Tesseract uses −1 for words it
   declines to score), divide by 100, and clamp to [0, 1].
4. Compute the bounding box as the union of the words' boxes.

**Why the mean is per line, not per page:** a single unsure line scores itself
down rather than dragging the whole document's confidence with it — and it is
the *line's* confidence that becomes the field's confidence, and therefore
decides which band the field falls into.

### 4.7.5 Algorithm 5 — Label-anchored field extraction

**Purpose.** Read named values off a known layout without training anything.

**Steps.**
1. Join all line texts with newlines.
2. Find the first template whose `require_all` markers are all present
   (case-insensitively) and at least one `require_any` marker is present. If
   none matches, **return no fields**.
3. For each rule in that template:
   - *anchor, `next_line`*: find the first line containing the anchor; take the
     next non-empty line as the raw value.
   - *anchor, `same_line`*: take everything after the anchor on that line,
     stripped of `:•-` and whitespace.
   - *pattern*: search each line; take capture group 1 if there is one, else
     the whole match.
   - Record the **source line's** confidence as the field's confidence.
4. Normalize the raw value by the rule's normalizer (`id`, `text`, `year`,
   `decimal`, `date`); drop the field if normalization yields nothing.
5. Keep both `raw` (the document's own casing, for display) and `value` (the
   normalized comparison form).

### 4.7.6 Algorithm 6 — Confidence-banded field comparison

**Purpose.** Convert a reading plus a confidence into a verdict contribution,
without flattening two different kinds of uncertainty into one.

**Steps.** For each critical field the registry holds:
1. If the registry has no value for it (e.g. `marks` when the record uses
   `cgpa`), skip it entirely.
2. If extraction produced nothing for it, emit `uncertain` / `not_read` naming
   the registry value it was not checked against.
3. Otherwise compare: identifiers via `ids_match` (confusables collapsed on
   both sides), everything else by exact equality after normalization.
4. If they agree → `pass` / `matches`.
5. Else if *c* ≥ 0.85 → `fail` / `differs` (a conflict).
6. Else if *c* ≥ 0.50 → `uncertain` / `differs` (a possible discrepancy).
7. Else → `uncertain` / `not_read` (not a reading at all).

A threshold value belongs to the stricter band.

### 4.7.7 Algorithm 7 — All-or-nothing CSV import

Described with its code in §4.6.7. In brief: validate the header, validate
every row collecting errors rather than stopping, check for duplicates inside
the file and against the registry, and insert only if the error list is empty —
then build, sign and issue PDFs for all rows in one transaction.

**Figure 4.18 — the activity diagram:**

```mermaid
flowchart TD
    A["CSV uploaded"] --> B{"≤ IMPORT_MAX_MB?"}
    B -- no --> E1["422 csv_invalid"]
    B -- yes --> C{"valid UTF-8<br/>(BOM tolerated)?"}
    C -- no --> E1
    C -- yes --> D{"header exactly<br/>the 9 columns?"}
    D -- no --> E2["422 listing missing<br/>and unknown columns"]
    D -- yes --> F["For each row"]
    F --> G{"extra cells?"}
    G -- yes --> ERR["collect error"]
    G -- no --> H{"blank line?"}
    H -- yes --> F
    H -- no --> I{"≤ IMPORT_MAX_ROWS?"}
    I -- no --> E1
    I -- yes --> J{"Pydantic valid?"}
    J -- no --> ERR
    J -- yes --> K{"own institution?"}
    K -- no --> ERR
    K -- yes --> L{"duplicate in file?"}
    L -- yes --> ERR
    L -- no --> M["remember + keep"]
    ERR --> F
    M --> F
    F --> N["One IN query:<br/>already in registry?"]
    N --> O{"any errors at all?"}
    O -- yes --> P["422 with per-row table<br/><b>NOTHING inserted</b>"]
    O -- no --> Q{"any valid rows?"}
    Q -- no --> E1
    Q -- yes --> R["Load signing key once"]
    R --> S["Build + sign every certificate"]
    S --> T["Render every PDF, hash each"]
    T --> U["add_all + ONE audit row with a count"]
    U --> V["Write all PDFs, then COMMIT"]
    V -- IntegrityError/OSError --> W["ROLLBACK + delete written PDFs"]
    V -- ok --> X["200 {imported: n}"]
```

### 4.7.8 Concepts applied, named for the report

| Concept | Where it appears |
|---|---|
| **Strategy pattern** | `OcrEngine` protocol with `TesseractEngine` as the one implementation; `get_engine()` is the switch point |
| **Dependency injection** | FastAPI `Depends` for the session, the current user and role gates; `engine=` parameter on every extraction function for test substitution |
| **Repository-ish service layer** | Routers never query; services own all persistence |
| **Pure core / imperative shell** | `engine.py`, `normalize.py`, `signing.py`, `qr.py`, `hashing.py`, `preprocess.py` are pure; services do the I/O |
| **Value objects** | Frozen, slotted dataclasses throughout the domain (`CertificateRecord`, `Check`, `QrPayload`, `OcrLine`, `ExtractedField`) |
| **Discriminated union** | `DecisionRequest` — three Pydantic models keyed on a `decision` literal |
| **Template method / declarative configuration** | YAML OCR templates instead of per-layout code |
| **Producer–consumer** | RQ queue between the API and the worker |
| **Optimistic concurrency** | Duplicate detection by unique index with `IntegrityError` translated to 409, rather than by locking |
| **Partial unique index as an invariant** | One open review case per verification |
| **Database trigger as an invariant** | Append-only audit log |
| **Compensating transaction** | Delete written PDFs when the commit fails |
| **Idempotency** | `seed.py`, `backfill_pdfs.py`, and "a certificate whose file is present is skipped" |
| **Cache-as-state** | TanStack Query holds all server state; no client-side store |
| **Generated contract** | OpenAPI → `openapi-typescript` → `schema.ts` |
| **Fail-safe defaults** | Unknown RQ status → `failed`; unreadable document → empty page → `MANUAL_REVIEW`; malformed signature → `False`, never an exception |

## 4.8 API endpoints

Base prefix `/api/v1` (configurable as `API_V1_PREFIX`). Authentication is a
bearer token in the `Authorization` header on every route except `/health`,
the OpenAPI document and `/auth/login`.

### 4.8.1 Table 4.19 — Complete endpoint reference

| Method | URL | Roles | Request | Success response | Purpose |
|---|---|---|---|---|---|
| `GET` | `/health` | public | — | `200 {status, env}` | Container health check |
| `GET` | `/openapi.json`, `/docs` | public | — | `200` | OpenAPI schema and Swagger UI |
| `POST` | `/auth/login` | public | `{email, password}` | `200 {access_token, refresh_token, token_type, access_expires_in}` | Sign in; both outcomes audited |
| `POST` | `/auth/refresh` | public (token-bearing) | `{refresh_token}` | `200 TokenPair` | Exchange a refresh token for a new pair |
| `GET` | `/auth/me` | any | — | `200 {id, email, role, is_active, institution?}` | The current user |
| `POST` | `/institutions` | admin | `{name, code, admin_email}` | `201 {institution, user, password}` | Create institution + key pair + first user; password returned **once** |
| `GET` | `/institutions` | admin | `?page=&size=` | `200 Page[InstitutionOut]` | List with certificate and user counts |
| `GET` | `/institutions/options` | **any signed-in** | — | `200 [{id, name, code}]` | Active institutions as form choices |
| `GET` | `/institutions/{id}` | admin | — | `200 InstitutionOut` | One institution with counts |
| `PATCH` | `/institutions/{id}` | admin | `{name?, is_active?}` | `200 InstitutionOut` | Name and active flag **only** |
| `DELETE` | `/institutions/{id}` | admin | — | `204` | Only if it never issued; else `409` |
| `POST` | `/certificates` | institution | `CertificateFields` (9 fields) | `201 CertificateOut` | Sign, issue the PDF, store the hash |
| `POST` | `/certificates/import` | institution | multipart CSV | `200 {imported: n}` | All-or-nothing bulk import |
| `GET` | `/certificates` | institution, admin | `?q=&page=&size=` | `200 Page[CertificateOut]` | Search number / roll / name; institution-scoped |
| `GET` | `/certificates/{id}` | institution, admin | — | `200 CertificateOut` | 404 for another institution's row |
| `POST` | `/certificates/{id}/revoke` | institution | `{reason}` (≥3 chars) | `200 CertificateOut` | Revoke own certificate |
| `GET` | `/certificates/{id}/pdf` | institution, admin | — | `200 application/pdf` + `X-Certificate-SHA256` | Stream the stored PDF byte-for-byte |
| `POST` | `/verify/id` | verifier, admin | `{cert_number}` | `200 VerificationOut` | Verify by number |
| `POST` | `/verify/qr` | verifier, admin | `{payload}` | `200 VerificationOut` | Verify a QR payload; `422` if not AVA1 |
| `POST` | `/verify/upload` | verifier, admin | multipart file | `202 {job_id, upload_id}` | Queue document extraction |
| `GET` | `/verify/jobs/{job_id}` | verifier, admin (owner) | — | `200 {status, verification_id?, error?}` | Poll the job |
| `GET` | `/verifications` | verifier, admin | `?page=&size=` | `200 Page[VerificationListItem]` | History, newest first |
| `GET` | `/verifications/{id}` | verifier (owner), admin | — | `200 VerificationOut` | Full result with checks |
| `POST` | `/reviews` | verifier | `{verification_id, institution_id?, note?}` | `201 ReviewOut` | Escalate to the institution |
| `GET` | `/reviews` | any | `?status=&page=&size=` | `200 Page[ReviewListItem]` | Scoped request list |
| `GET` | `/reviews/counts` | any | — | `200 {open, open_over_7_days}` | Nav badge and admin card |
| `GET` | `/reviews/{id}` | scoped | — | `200 ReviewOut` | One case, with per-viewer flags |
| `GET` | `/reviews/{id}/document` | scoped | — | `200` file, inline | The uploaded document |
| `POST` | `/reviews/{id}/messages` | verifier, institution | `{body}` | `201 MessageOut` | Reply on the thread |
| `POST` | `/reviews/{id}/needs-info` | institution | `{body}` | `200 ReviewOut` | Ask the verifier for more |
| `POST` | `/reviews/{id}/decision` | institution | discriminated union (below) | `200 ReviewOut` | Answer and close |
| `GET` | `/admin/audit` | admin | `?action=&date_from=&date_to=&page=&size=` | `200 Page[AuditOut]` | Append-only trail, prefix-filtered |
| `GET` | `/admin/stats` | admin | — | `200 AdminStats` | Platform statistics |

### 4.8.2 Request and response shapes worth spelling out

**`POST /certificates` — `CertificateFields`:**

```json
{
  "cert_number": "NBIT2024CS0001",
  "student_name": "Aarav Mehta",
  "roll_number": "20CS001",
  "programme": "B.Tech Computer Science and Engineering",
  "year_of_passing": 2024,
  "cgpa": "8.72",
  "marks": null,
  "issue_date": "2024-07-20"
}
```

Validation applied: identifiers normalized; text whitespace-collapsed; grades
rounded to two decimals; CGPA 0–10; marks 0–100; at least one of the two;
1950 ≤ year ≤ current year; issue date not in the future and not before the
year of passing.

**`POST /reviews/{id}/decision` — a discriminated union on `decision`:**

```json
{"decision": "confirmed", "note": "Verified against our 2024 register."}
{"decision": "confirmed_added", "certificate": { ...CertificateFields... }}
{"decision": "not_issued", "reason": "This number is not in our 2022 register."}
```

`reason` is mandatory and non-blank for `not_issued`; `note` is optional for
`confirmed`.

**`VerificationOut` — the explainability payload:**

```json
{
  "id": "…uuid…",
  "method": "upload",
  "result": "VERIFIED",
  "checks": [
    {"name": "registry_lookup",  "status": "pass",      "detail": "Certificate NBIT2022CS0020 is registered to NBIT."},
    {"name": "revocation",       "status": "pass",      "detail": "The certificate is not revoked."},
    {"name": "record_signature", "status": "pass",      "detail": "The stored record matches the signature issued by NBIT."},
    {"name": "qr_signature",     "status": "pass",      "detail": "The QR signature matches the registry record and the public key of NBIT."},
    {"name": "file_hash",        "status": "uncertain", "detail": "The uploaded file is not the original issued PDF. That is expected for a scan or a re-saved copy, so the printed details are compared instead."},
    {"name": "field_match.cert_number",     "status": "uncertain", "state": "not_read", "detail": "The certificate number could not be read from the document, so it was not checked against the registry's NBIT2022CS0020."},
    {"name": "field_match.student_name",    "status": "pass",      "state": "matches",  "detail": "The student name matches the registry: NANDINI RAO."},
    {"name": "field_match.cgpa",            "status": "uncertain", "state": "differs",  "detail": "The CGPA on the document reads '8.00', but the registry has '8.56'. At 70% confidence that is not certain enough to call a conflict, so it is a possible discrepancy for a person to look at."}
  ],
  "certificate": { "...the registry record..." },
  "extracted_fields": {
    "file_sha256": "…", "mime": "image/jpeg", "text_source": "ocr",
    "template": "nbit", "ocr_engine": "tesseract",
    "line_count": 24, "mean_line_confidence": 0.9183,
    "qr_present": true, "cert_number": "NBIT2022CS0020",
    "institution_code": "NBIT", "qr_reader": "zxing", "qr_scale": 1,
    "fields": {"student_name": {"name": "student_name", "value": "NANDINI RAO", "raw": "Nandini Rao", "confidence": 0.94}}
  },
  "verifier": {"id": 3, "email": "verifier@ava.test"},
  "reviews": [],
  "created_at": "2026-11-19T10:12:04.511Z"
}
```

### 4.8.3 Error envelope and Table 4.22 — error codes

Every error has the same shape, produced by one handler:

```json
{"error": {"code": "duplicate_cert_number", "message": "A certificate with this number already exists."}}
```

Two variants add a key: `validation_error` adds `fields`
(`[{loc, msg}]`), and `csv_invalid` adds `rows`
(`[{row, field, message}]`).

| HTTP | Code | Raised when |
|---|---|---|
| 400 | `upload_empty` | The uploaded file has zero bytes |
| 401 | `invalid_credentials` | Unknown email, wrong password, inactive user, or inactive institution |
| 401 | `not_authenticated` | No bearer token |
| 401 | `invalid_token` | Malformed token, wrong token type, or user not found/inactive |
| 401 | `token_expired` | Expired token |
| 403 | `forbidden` | Role not permitted; an admin attempting a review action |
| 404 | `not_found` | Certificate, institution, verification or review case not visible to this user |
| 404 | `job_not_found` | Unknown job id, or another verifier's |
| 404 | `upload_not_found` | The upload row is gone |
| 404 | `pdf_not_available` | No stored PDF for this certificate |
| 404 | `document_unavailable` | The case's uploaded file is no longer stored |
| 409 | `duplicate_cert_number` | Certificate number already exists |
| 409 | `duplicate_code` / `duplicate_email` | Institution code or user email already exists |
| 409 | `already_revoked` | The certificate is already revoked |
| 409 | `institution_has_certificates` | Delete attempted on an institution that has issued |
| 409 | `institution_in_use` | Its users are referenced by the audit trail |
| 409 | `not_escalatable` | Result is `VERIFIED` or `REVOKED` |
| 409 | `request_already_open` | An open case already exists for that verification |
| 409 | `case_closed` | Reply or decision on a closed case |
| 413 | `upload_too_large` | Over `UPLOAD_MAX_MB` (adds `max_mb`) |
| 415 | `upload_unsupported_type` | Magic bytes are not PDF, PNG or JPEG |
| 422 | `validation_error` | Pydantic validation failure (adds `fields`) |
| 422 | `csv_invalid` | Header or row problems (adds `rows`) |
| 422 | `qr_payload_invalid` | Text is not an AVA1 payload — **nothing is recorded** |
| 422 | `institution_required` / `institution_invalid` | No institution identified, or an inactive one chosen |
| 422 | `message_empty` / `reason_required` / `invalid_status` | Review-workflow validation |
| 500 | `signing_key_missing` | No PEM for this institution code |
| 500 | `pdf_write_failed` | The uploads volume is not writable |
| 500 | `upload_unreadable` | The stored file could not be read back |

### 4.8.4 Table 4.20 — Audit action vocabulary

| Action | Entity | `meta` contents |
|---|---|---|
| `auth.login` | user | `{role}` |
| `auth.login_failed` | user | `{email_domain}` — **nothing else** |
| `institution.create` | institution | `{code, key_file}` |
| `institution.update` | institution | `{code, ...changed fields}` |
| `institution.delete` | institution | `{code, users_removed}` |
| `user.create` | user | `{role, institution_code}` |
| `certificate.create` | certificate | `{cert_number, institution_code, file_sha256}` |
| `certificate.import` | certificate | `{count, filename, institution_code}` — one row per import |
| `certificate.revoke` | certificate | `{cert_number, institution_code, reason}` |
| `certificate.pdf_backfill` | certificate | `{cert_number, reason, file_sha256}` |
| `upload.create` | upload | `{mime, sha256, bytes}` |
| `verification.create` | verification | `{method, result, cert_number \| upload_id, certificate_id, text_source, template}` |
| `review.create` | review_case | `{verification_id, institution_id, result, has_note}` |
| `review.message` | review_case | `{message_id, status}` |
| `review.needs_info` | review_case | `{verification_id, message_id}` |
| `review.confirmed` / `review.confirmed_added` / `review.not_issued` | review_case | `{verification_id, institution_id, …}` |

Filtering is by **prefix**, so `certificate.` covers create/import/revoke/
backfill and `auth.login` covers both successes and failures.

## 4.9 UI screens and user flow

### 4.9.1 Table 4.21 — Routes and guards

| Route | Component | Guard | Purpose |
|---|---|---|---|
| `/login` | `Login` | public | Email/password form; redirects to the attempted page |
| `/` | `Dashboard` | any signed-in | Account card; statistics cards for an admin |
| `/certificates` | `Certificates` | institution, admin | Registry table with search, PDF download, revoke |
| `/certificates/import` | `ImportCertificates` | institution | CSV upload with a per-row error report |
| `/verify` | `Verify` (**lazy**) | verifier, admin | Two tabs: Verify document, Certificate number |
| `/verifications` | `MyVerifications` | verifier, admin | Paginated history |
| `/verifications/:id` | `VerificationDetail` | verifier, admin | The full result; printable |
| `/requests` | `Requests` | any signed-in | One list, three headings, scoped by the API |
| `/requests/:id` | `RequestDetail` | any signed-in (scoped) | One case; actions depend on `can_decide` / `can_reply` |
| `/admin/institutions` | `Institutions` | admin | Institution management |
| `/admin/audit` | `AuditLog` | admin | Append-only trail with filters |
| `*` | — | — | Redirect to `/` |

### 4.9.2 Figure 4.21 — Route tree with guards

```mermaid
flowchart TD
    ROOT["BrowserRouter"] --> LOGIN["/login — public"]
    ROOT --> PR["ProtectedRoute<br/>token present AND /auth/me succeeds"]
    PR --> LAYOUT["AppLayout<br/>header + role-filtered nav + logout"]
    LAYOUT --> DASH["/ Dashboard — any role"]
    LAYOUT --> G1["roles: institution, admin"]
    G1 --> CERTS["/certificates"]
    LAYOUT --> G2["roles: institution"]
    G2 --> IMP["/certificates/import"]
    LAYOUT --> G3["roles: verifier, admin"]
    G3 --> VER["/verify — lazy + Suspense"]
    G3 --> HIST["/verifications"]
    G3 --> VDET["/verifications/:id"]
    LAYOUT --> REQ["/requests — all three roles"]
    LAYOUT --> RDET["/requests/:id — all three, API-scoped"]
    LAYOUT --> G4["roles: admin"]
    G4 --> AUD["/admin/audit"]
    G4 --> INST["/admin/institutions"]
```

### 4.9.3 Screen-by-screen description

**Login (`/login`).** A single card: email, password, submit. Errors render
from the API envelope through `apiErrorMessage()` with `role="alert"`. The
footer reads "Prototype — all data is synthetic." If a token is already
present the page redirects immediately to wherever the user was heading.

**Dashboard (`/`).** Every role sees an "Your account" card with email, a role
badge and, for an institution user, the institution name and code. An
administrator additionally sees `AdminStatsCards`: four tiles (institutions
with a user count, certificates with a revoked count, verifications with a
7-day count, logins in 7 days with a failed count), a **Verification requests**
card showing open and "open more than 7 days" (the latter coloured amber when
non-zero), and a **Verification results** card breaking down the four statuses
in their result colours.

**Certificates (`/certificates`).** A debounced search box (number, roll
number or name), then a table: certificate number, student, roll number,
programme, year, CGPA/marks, institution (admin only), status badge, and
actions. The actions are a download button for the issued PDF and — for an
institution user on an `active` row — a revoke button. The header offers
"Import CSV" and the "Add certificate" dialog to institution users only. Empty
and error states are explicit, and the empty state distinguishes "no
certificates yet" from "no certificates match *q*".

**Add certificate dialog.** Eight fields in a two-column grid
(certificate number, student name, roll number, programme, year of passing,
issue date, CGPA, marks), with `cgpa` and `marks` optional and the hint "CGPA
or marks, at least one". Per-field errors come from `apiFieldErrors()`, which
unpacks the 422 `fields` array by its last `loc` element.

**Revoke dialog.** Names the certificate and the student, states that the
record, signature and PDF stay as issued and that the reason goes to the audit
log, and requires a reason of at least three characters before enabling the
button. On success a toast reads "`NBIT2024CS0001` now verifies as REVOKED."

**Import certificates (`/certificates/import`).** Shows the exact nine-column
header, states the rules (UTF-8, any column order, `YYYY-MM-DD` dates, CGPA
and/or marks, `institution_code` must equal the user's own code), offers a
generated template download, and takes a `.csv` file. On success: a count and
a link to the registry. On failure: a bordered card titled "Nothing was
imported" with the API's summary message and a three-column table of line /
column / problem.

**Verify (`/verify`).** Two shadcn tabs.

*Verify document* — the `UploadDropzone`: a dashed drop area, a "choose a file"
link button, a separate "Take a photo" button, and the line "PDF, PNG or JPEG,
up to 10.0 MB. A PDF with a text layer is read directly; a photo or scan has
its QR code read first, then its printed text." Local pre-checks reject an
empty file, an oversized file and an obviously wrong MIME type — described in
the code as "a courtesy, not a control", since the server decides from the
bytes. While the job runs the area shows a spinner with staged labels:
"Uploading…" → "Queued for extraction…" → "Reading the document…". The camera
is a **second** input, because `capture` must not be set on the file picker —
on a phone it would hide the gallery, and on a desktop it is ignored anyway.

*Certificate number* — a single text input and a Verify button.

On completion the page navigates to the result's own URL. A failed job prints
"Nothing was decided about the document — try a clearer photo, or verify by
certificate number instead."

**Verification result (`/verifications/:id`).** Top to bottom:

1. **Banner** in one of five wordings — `VERIFIED`, `MISMATCH`, "Needs review",
   **"Possible discrepancy"** (chosen when the result is `MANUAL_REVIEW` *and*
   some field's `state` is `differs`), or `REVOKED` — each with an explanatory
   paragraph, plus the certificate number and a Print button.
2. **The evidence path**, one sentence derived from the checks.
3. **Certificate details** from the registry, or "No matching record is
   registered, so there are no certificate details to show."
4. **`DocumentMatch`** (uploads only): an amber discrepancy box listing each
   differing field as "CGPA — document shows 9.99, institution issued 9.32"; a
   muted box naming unread fields; and the count line, with no percentage.
5. **"What the document says"** — the four-column table, a sentence naming the
   text source and template, confidence badges (amber below 85 %), and
   "not checked" rows for critical fields the reader missed.
6. **"The issuing institution"** — any answer already given, and the
   "Request confirmation from issuing institution" button when the result is
   escalatable, the user is a verifier, and no request exists yet.
7. **Checks** — every check with an icon, label, `detail` sentence and status.
8. **"This verification"** — method, timestamp, verifier email, verification id.

**Request confirmation dialog.** If the document identified an institution it
is shown as a fact with the note "Taken from the certificate number on the
document, so it cannot be sent elsewhere"; otherwise a `<select>` of active
institutions appears. An optional note, then Send — which redirects to the new
request.

**My verifications (`/verifications`).** Heading switches between "My
verifications" and "All verifications" by role. Table of number, result badge,
method ("Number" / "QR" / "Upload"), timestamp and an Open link, with
pagination.

**Requests (`/requests`).** One component, three headings and blurbs. Five
filter buttons (Open, Waiting, Needs info, Answered, All). The table's second
column is "Asked by" for an institution and "Institution" for everyone else;
the action button reads "Answer" for an institution on an open case and "Open"
otherwise. Each row shows the certificate number with "read as needs review"
beneath it.

**Request detail (`/requests/:id`).** Heading, status or decision badge, and:
the decision card if answered (including who answered, when, and "The original
verification is unchanged"); the verifier's note; **the document preview** —
an `<iframe>` for a PDF, an `<img>` for an image, fetched as a blob because
the endpoint needs the bearer token, plus an "Open full size" link; the
extracted-fields table; "Your matching record" or "No record in your registry
matches this document…"; the message thread with a reply box when
`can_reply`; and, when `can_decide`, four actions — **Confirm genuine**,
**Confirm & add to registry**, **Not issued by us**, **Ask for more info**.

The "not issued" panel requires a reason and carries the warning "It says you
have no such record — not that the document is forged." The "confirm & add"
panel is `ConfirmAndAddForm`: eight prefilled but fully editable fields,
preceded by "Check every value against your own records before confirming.
This creates a signed registry record and issues its PDF, exactly as adding a
certificate does — the values below are only what was read off the document."

**Institutions (`/admin/institutions`).** Table with name, code, counts,
status and actions (activate/deactivate, delete). The create dialog takes
name, code and first-user email; on success a panel shows the generated
password **once**, with a copy button and a confirmation tick. Delete asks for
confirmation and surfaces the 409 explaining that an institution with
certificates must be deactivated instead.

**Audit log (`/admin/audit`).** Six quick-filter buttons (All, Logins, Failed
logins, Certificates, Verifications, Institutions), a free-text action-prefix
box, From/To date inputs and a Clear button. The table shows when, action
(monospace), actor email, entity and a truncated `key=value` rendering of
`meta`. The subtitle states the guarantee: "Append-only: rows can be added but
never changed or removed. Failed logins keep the email domain only."

### 4.9.4 Figure 4.22 — Screen flow by role

```mermaid
flowchart LR
    LOGIN["/login"] --> DASH["/"]

    subgraph INST["Institution user"]
        direction TB
        DASH_I["/"] --> C["/certificates"]
        C --> ADD["Add certificate dialog"]
        C --> REV["Revoke dialog"]
        C --> PDF["Download issued PDF"]
        DASH_I --> IMP["/certificates/import"]
        DASH_I --> RQ_I["/requests (inbox)"]
        RQ_I --> RD_I["/requests/:id"]
        RD_I --> DOC["Document preview"]
        RD_I --> CAF["Confirm & add form"]
        CAF -.->|"creates a signed record"| C
    end

    subgraph VERI["Verifier"]
        direction TB
        DASH_V["/"] --> V["/verify"]
        V --> VD["Verify document tab<br/>photo / image / PDF"]
        V --> VN["Certificate number tab"]
        VD --> RES["/verifications/:id"]
        VN --> RES
        RES --> ASK["Request confirmation dialog"]
        ASK --> RD_V["/requests/:id"]
        DASH_V --> H["/verifications (history)"]
        H --> RES
        RES --> PRINT["Print / Save as PDF"]
    end

    subgraph ADMIN["Administrator"]
        direction TB
        DASH_A["/ + statistics cards"] --> AI["/admin/institutions"]
        AI --> NEW["Create institution<br/>password shown once"]
        DASH_A --> AA["/admin/audit"]
        DASH_A --> RQ_A["/requests (read-only)"]
        DASH_A --> HA["/verifications (all)"]
    end

    DASH --> INST
    DASH --> VERI
    DASH --> ADMIN
```

## 4.10 Security, authentication, validation and error handling

### 4.10.1 Authentication

Covered in §2.2.3 and §4.6.2. The security-relevant summary:

- argon2 password hashing; `verify_password` returns `False` rather than
  raising on a malformed stored hash.
- JWT HS256 with `sub`, `role`, `type`, `iat`, `exp`; decoding *requires*
  `sub`, `type` and `exp` and rejects a token of the wrong type.
- Four distinct rejection reasons produce one identical 401, and an unknown
  email still pays the cost of a hash verification.
- The user is re-loaded and `is_active` re-checked on **every** request, which
  is what makes deactivation immediate despite stateless tokens.

**Stated weaknesses** (recorded as prototype decisions, not oversights):
refresh tokens are not stored server-side, so logout is browser-side only and
a stolen refresh token remains valid for up to seven days; and tokens live in
`localStorage` rather than an `httpOnly` cookie.

### 4.10.2 Authorisation — two layers

**Layer 1, the route gate.** `require_role(...)` on every protected endpoint.

**Layer 2, row scoping inside services** — which is where the interesting
rules live, because a role alone is not enough:

```python
def _scope(stmt, user: User):
    """Institution users only ever see their own institution's certificates."""
    if user.role == Role.INSTITUTION:
        return stmt.where(Certificate.institution_id == user.institution_id)
    return stmt
```

**404 rather than 403, deliberately and consistently.** Another institution's
certificate, another verifier's verification, another verifier's job, and a
review case addressed elsewhere all return `404 not_found` — identical to a
resource that does not exist. Whether a record exists is itself information,
and a 403 would leak it. The comments in the code say so at each site: "Same
answer for 'doesn't exist' and 'belongs to another institution'."

**The administrator's deliberate incapacity.** `_may_write()` returns `False`
for an admin, and `_institution_case()` rejects any non-institution user. The
reasoning recorded in the project: a platform operator adjudicating whether a
university issued a degree is exactly the authority this system should not
have.

### 4.10.3 Input validation — four layers

| Layer | Mechanism | Example |
|---|---|---|
| **Schema** | Pydantic field types, lengths, bounds | `cert_number` 1–64 chars; `cgpa` `ge=0, le=10` |
| **Field validators** | Normalization and emptiness | `normalize_id()` rejecting an identifier with no alphanumerics |
| **Model validators** | Cross-field rules | year range; at least one grade; issue date not future and not before the passing year |
| **Database** | Check constraints and unique indexes | `ck_certificates_grade`, `ck_users_institution_link`, the partial unique index |

**Content-based validation for uploads.** The type comes from the file's
leading bytes; the filename and the client's `Content-Type` are ignored
entirely. A disguised executable named `certificate.pdf` is a 415 before
anything is written — pinned by `test_upload_rejects_a_disguised_unsupported_file`
and `test_upload_trusts_bytes_not_the_filename`.

**SQL injection.** All queries go through SQLAlchemy's parameter binding.
Where user text reaches a `LIKE`/`ILIKE` pattern, wildcards are escaped
explicitly and the escape character is declared:

```python
def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
# ...
Certificate.student_name.ilike(f"%{_escape_like(q.strip())}%", escape="\\")
```

*(A minor defect exists in the copy of this helper in `services/admin.py`,
where the replacement strings are written without raw-string escaping and
Python emits a `SyntaxWarning: invalid escape sequence`. It is cosmetic — the
resulting characters are the same — and it is recorded in §5.3.)*

**Resource limits.** `UPLOAD_MAX_MB` 10 with chunked reading;
`IMPORT_MAX_MB` 2 and `IMPORT_MAX_ROWS` 5000; pagination `size` capped at 100;
QR upscales capped at 40 MP; RQ job timeout 300 s.

### 4.10.4 Cryptographic design summary

| Concern | Mechanism |
|---|---|
| Record authenticity | Ed25519 over canonical JSON of nine normalized fields |
| Signature encoding | base64url, unpadded |
| Private key storage | PKCS#8 PEM, unencrypted, mode 0600, on a volume outside the image |
| Public key storage | SPKI PEM in `institutions.public_key`, immutable |
| Document fingerprint | SHA-256 of the issued PDF, stored on the row |
| QR integrity | The signature *is* the integrity mechanism; the payload carries no personal data |
| Password storage | argon2 |
| Token integrity | HMAC-SHA256 with `JWT_SECRET` |
| Signature verification failure mode | Returns `False`; never raises, never leaks a reason |

### 4.10.5 Error handling

**Three handlers in `main.py`**, so no router builds an error body:

```python
@app.exception_handler(AppError)
def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, **exc.extra}})

@app.exception_handler(StarletteHTTPException)
def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    code = detail.get("code") if isinstance(detail, dict) else f"http_{exc.status_code}"
    message = detail.get("message") if isinstance(detail, dict) else str(detail)
    return JSONResponse(status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
        headers=getattr(exc, "headers", None))

@app.exception_handler(RequestValidationError)
def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": {
        "code": "validation_error",
        "message": "Request body or parameters are invalid.",
        "fields": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]}})
```

The third handler is what makes per-field messages possible in the frontend
forms, and `test_unknown_route_uses_error_envelope` confirms that even a 404
on an unknown path uses the envelope.

**Graceful degradation rather than failure**, at every point where an
exception would be the wrong answer:

| Situation | Behaviour |
|---|---|
| A QR reader throws | Logged at debug; the ladder continues |
| Extraction throws anything | Logged with a traceback; returns an empty `ExtractedPage` → `MANUAL_REVIEW` |
| No OCR engine available | Logged as an error; returns no text rather than crashing |
| A template file is unreadable | Logged; that template is skipped, the others still load |
| A malformed signature or key | `verify_record` returns `False` |
| A non-AVA1 code on an uploaded page | Ignored with a log line (unlike the scan endpoint, the verifier never claimed it was a certificate QR) |
| `localStorage` unavailable | `tokens.ts` reads and writes inside `try`/`catch` |
| An RQ status we do not recognise | Reported `failed`, never "still running" |
| A job that finishes with no id | Reported `failed` |
| A missing issued PDF | 404 `pdf_not_available`, never a rebuild |
| A file already deleted during pruning | Not an error; the row is still removed |

**Privacy in logging.** No log statement writes document contents, a password,
a token or a full email address. Uploads are logged by hash, MIME type and
size; failed logins by email domain; extraction by line counts and character
counts.

### 4.10.6 Residual security limitations (stated, not hidden)

1. Refresh tokens cannot be revoked before expiry.
2. Tokens are in `localStorage`, reachable by any script that achieves XSS.
3. Private keys are unencrypted on disk, with no HSM and no rotation path —
   the institution code and public key are immutable by design.
4. No rate limiting on login or on any other endpoint.
5. `JWT_SECRET` ships as a placeholder in `.env.example` and must be replaced.
6. CORS is an explicit allow-list, but the same-origin proxy means the browser
   never exercises it in the default configuration.
7. Trust is centralised: an attacker who can register an institution can issue
   signatures that verify.
8. **The white-box PDF overlay defect** (§5.3) — a filled rectangle drawn over
   a PDF's text can show a human one value while the text layer still reports
   the original. This is a known, deliberately unfixed trade-off.

---

# CHAPTER 5: TESTING AND DEPLOYMENT

## 5.1 Testing strategy

### 5.1.1 Result of the current run

The suite was executed against the running stack while this document was
prepared:

```
$ docker compose exec api pytest -p no:warnings
373 passed in 143.26s (0:02:23)
```

**373 test cases pass; none fail, none are skipped.** The 373 cases come from
308 `test_*` functions across 19 files — the difference is parametrised tests,
which pytest expands into one case per parameter set.

### 5.1.2 Figure 5.1 — The test pyramid as actually implemented

```mermaid
flowchart TB
    L1["<b>Level 1 — Pure unit tests</b><br/>No DB, no network, no files<br/>engine · normalize · signing · qr · preprocess · fields<br/>test_verification_engine · test_engine_upload · test_signing"]
    L2["<b>Level 2 — Service tests</b><br/>Real Postgres in a rolled-back transaction<br/>certificates · institutions · uploads · reviews · admin"]
    L3["<b>Level 3 — API tests</b><br/>FastAPI TestClient over httpx, real auth tokens<br/>test_auth · test_verify_api · test_certificates · test_reviews"]
    L4["<b>Level 4 — End-to-end</b><br/>Real Tesseract, real ReportLab, real PyMuPDF,<br/>real RQ job, real documents generated in-run<br/>test_ocr_pipeline · test_upload_verification_e2e · test_upload_job"]

    L1 --> L2 --> L3 --> L4
    style L1 fill:#dcfce7,stroke:#16a34a
    style L2 fill:#dbeafe,stroke:#2563eb
    style L3 fill:#fef3c7,stroke:#d97706
    style L4 fill:#fee2e2,stroke:#dc2626
```

### 5.1.3 Level 1 — Pure unit tests

The verification engine, normalization, signing, QR parsing, preprocessing and
field extraction are all pure functions, so they are tested by constructing
inputs directly and asserting on outputs — no database, no HTTP, no
filesystem. This is where the bulk of the *rule* coverage lives:
`test_engine_upload.py` alone contains 36 test functions walking every decision
rule, every confidence band and every band edge.

Representative assertions:

- `test_the_band_edges_are_the_thresholds_not_approximations` — a confidence of
  exactly 0.85 is a conflict and exactly 0.50 is a discrepancy, because a
  threshold value belongs to the stricter band.
- `test_the_thresholds_are_configurable` — the engine honours thresholds passed
  in `VerificationInput`, which is the property that keeps it pure.
- `test_a_confident_conflict_beats_a_valid_qr` — rule ordering: a differing
  field read confidently overrides a valid signature.
- `test_a_valid_qr_verifies_when_a_field_could_not_be_read` — an unread field
  blocks nothing.
- `test_an_unread_field_never_turns_a_difference_into_a_pass` — the two kinds
  of uncertainty stay separate.
- `test_identifiers_tolerate_ocr_confusables` and
  `test_a_genuinely_different_identifier_still_conflicts` — the confusable set
  is permissive enough to help and narrow enough to be safe.
- `test_equivalent_inputs_sign_the_same` — normalization makes the signature
  depend on meaning only.
- `test_malformed_signature_is_rejected_not_raised` and
  `test_bad_public_key_is_rejected_not_raised` — the fail-safe contract.
- `test_no_result_ever_says_fake` and `test_every_check_detail_is_a_sentence` —
  the vocabulary and explainability requirements are themselves tested.

### 5.1.4 Level 2 and 3 — Service and API tests, and the fixture design

`tests/conftest.py` establishes four safety properties that are worth
describing in the report, because each one exists in response to a real risk:

**A separate database.** The session-scoped `engine` fixture connects to
`postgres`, creates `<POSTGRES_DB>_test` (i.e. `ava_test`) if absent, then
drops and recreates the schema. The demo database is never touched.

**A rolled-back transaction per test.** Each test gets a session bound to a
connection inside an outer transaction, with
`join_transaction_mode="create_savepoint"` so that service code calling
`db.commit()` works normally while the outer transaction is still rolled back
afterwards. Tests are therefore order-independent and leave nothing behind.

**Temporary key and PDF directories, enforced automatically.** Two
`autouse=True` fixtures monkeypatch `settings.keys_dir` and
`settings.issued_dir` to per-test `tmp_path` subdirectories, so a test can
never write a signing key or an issued PDF into the real volume.

**Real tokens, not faked dependencies.** The `auth_headers` fixture logs each
of five seeded users in through `POST /auth/login` and returns real bearer
headers, so every authorisation test exercises the genuine token path.

A fifth property is enforced in the OCR job tests specifically, and the
project's decision log records why: **tests that exercise the RQ job patch
`SessionLocal`** to hand back the rolled-back test session. The job
legitimately opens its own session, but `SessionLocal` points at the *demo*
database — and a fixture that used it directly once deleted every certificate
and verification row there.

### 5.1.5 Level 4 — End-to-end tests with real documents

The highest-value and slowest tests. `tests/ocr_fixtures.py` **generates the
documents inside the test run** from the project's own `pdf_issue` and
`signing` code, so the artefacts under test are the real ones and cannot drift
from the production code path. The file's own docstring notes that this is not
the out-of-scope test-certificate generator: nothing is shipped and no document
is checked in.

The fixture helpers and the degradations they produce:

| Helper | What it produces |
|---|---|
| `make_certificate()` | A `SampleCertificate` with its signed PDF bytes and a `truth` dict of what perfect extraction would yield |
| `render_png(dpi=200)` | The PDF page rasterised |
| `to_jpeg(quality=90)` | Lossy compression |
| `rotate_image(degrees)` | Skew |
| `degrade(degrees=5, blur=3, jpeg_quality=60)` | Combined rotation, blur and compression — "the usual degraded scan" |
| `photo_of_certificate(margin=90)` | The page inset on a background, so perspective detection has something to crop |
| `noise_image()` | Random pixels — a document that should match no template |
| `edit_pdf_text(old, new)` | A **proper** edit: redact the original text, then draw the replacement |
| `cover_pdf_text(old, new)` | A **white-box overlay**: draw a filled rectangle over the text and print a new value on top, leaving the original glyphs in the content stream |

The last two are the interesting pair. `edit_pdf_text` simulates genuine
tampering and the system catches it (`test_an_edited_cgpa_is_a_mismatch_naming_the_field`,
`test_only_the_edited_field_fails`). `cover_pdf_text` simulates the overlay
attack and the system **does not** catch it on the PDF path — which is pinned
deliberately by two tests, one for each half of the behaviour (§5.3).

`test_ocr_pipeline.py` (53 functions) and `test_upload_verification_e2e.py`
(19 functions) run real Tesseract over real rendered pages. They account for
roughly two of the suite's two and a half minutes, which is why the project
documents a fast path for working on anything else:

```
docker compose exec api pytest -q \
  --ignore=tests/test_ocr_pipeline.py \
  --ignore=tests/test_upload_verification_e2e.py
```

### 5.1.6 Manual testing

Five scripted demonstration paths are documented in `CLAUDE.md` and were used
as the manual acceptance checklist; they are reproduced in §6.1. In addition,
the 12 photographs in `samples/photos/` were put through the **real upload
API** — login, `POST /verify/upload`, the worker, then reading the stored
verification — rather than through a test harness, which is what produced the
measurements in §6.2. `samples/photos/Actual_data.txt` holds the ground truth
for the two photographed certificates.

During the preparation of this document, one further manual verification was
run end to end through the single proxied port to confirm the stack as it
currently stands: login, `/auth/me`, `POST /verify/id` on `NBIT2024CS0001`
(→ `VERIFIED`, 6 checks), and `POST /verify/upload` with
`samples/photos/sample1.jpeg` (→ job finished, `VERIFIED`, method `upload`,
6 checks). A stray `samples/photos/Actual_data.txt` passed to the same endpoint
was correctly rejected by the magic-byte sniffing.

### 5.1.7 What is *not* tested

Stated plainly, because the report should not overclaim:

- **No frontend tests of any kind.** There is no Vitest, no React Testing
  Library, and no Playwright — despite the specification's stack table naming
  "Playwright (2–3 e2e flows)". The frontend's only automated check is
  `tsc --noEmit` (`npm run lint`), which catches type errors but no behaviour.
  End-to-end coverage is achieved at the API level in Python instead.
- **No load or performance testing.** The latency figures in §6.2 are
  measurements of individual operations, not of the system under concurrent
  load.
- **No security testing.** No penetration testing, no dependency
  vulnerability scanning, no fuzzing of the upload or QR paths.
- **The OCR-only path on a real photograph is untested end to end.** Every
  photograph in `samples/photos` carries a decodable QR, so the fallback path —
  a real photograph whose code is damaged or cropped away — is covered only by
  synthetic renders.
- **No migration test.** `alembic upgrade head` is not exercised by the suite;
  tests build the schema with `Base.metadata.create_all`, so a defect present
  in a migration but not in the models would not be caught.

## 5.2 Test cases

### 5.2.1 Table 5.1 — Test file inventory

| File | Functions | What it covers |
|---|---|---|
| `test_ocr_pipeline.py` | 53 | Preprocessing operations, TSV line grouping, template matching, field extraction, PDF text layer vs OCR, QR decode ladder, rotation, noise, masking |
| `test_engine_upload.py` | 36 | Every upload decision rule, all three confidence bands, band edges, configurability, confusables, "never accuses" |
| `test_uploads.py` | 29 | Magic-byte sniffing, size limits, storage, retention, pruning, orphans, RQ status mapping, job ownership |
| `test_reviews.py` | 28 | The whole request workflow: scoping, escalation rules, state machine, three decisions, prefill, retention hold, audit, counts, overdue |
| `test_certificates.py` | 25 | Create, duplicates, validation, scoping, search, pagination, CSV import (BOM/CRLF/reordering/all-or-nothing/limits), the append-only trigger |
| `test_auth.py` | 19 | Login paths, token types, expiry, garbage tokens, wrong signatures, role blocking |
| `test_upload_verification_e2e.py` | 19 | Whole-pipeline outcomes on real generated documents, including the overlay defect (both halves) |
| `test_verify_api.py` | 17 | Verify by number and QR over HTTP, normalization, tampering, scoping, history, pagination |
| `test_signing.py` | 14 | Normalization, canonical bytes, sign/verify, cross-key failure, equivalence, malformed input |
| `test_admin.py` | 13 | Login auditing (four failure kinds), audit filters by prefix and date, pagination, statistics, role gating |
| `test_issue_pdf.py` | 13 | Payload round-trip, PDF storage and hash stability, decodable QR, import issuance, backfill idempotency |
| `test_institutions.py` | 12 | Creation with key pair and password, auditing without the password, duplicates, counts, update, deactivation, delete rules |
| `test_verification_engine.py` | 13 | Non-upload rules: lookup, revocation, record signature, QR variants, serialisability, "never says fake" |
| `test_upload_job.py` | 7 | The RQ job: hash verification, unknown document, audit row, missing upload/verifier, revoked certificate |
| `test_revocation.py` | 6 | Revocation with reason, record/PDF untouched, reason required, double revoke, ownership, verification reports REVOKED |
| `test_health.py` | 3 | `/health`, OpenAPI served, unknown route uses the error envelope |
| `test_seed.py` | 1 | The 20 demo certificates are valid and unique |

### 5.2.2 Table 5.2 — Representative test cases

All of the following are real tests in the suite. "Actual output" is what the
current run produced; every case passed.

| ID | Test (file) | Input | Expected output | Actual output | Status |
|---|---|---|---|---|---|
| TC-01 | `test_login_ok_returns_tokens_and_me_works` (auth) | Valid email + password | 200, access + refresh tokens; `/auth/me` returns the user | As expected | Pass |
| TC-02 | `test_login_unknown_email_same_error` (auth) | Unregistered email | 401 `invalid_credentials`, identical to a wrong password | As expected | Pass |
| TC-03 | `test_failed_login_records_only_the_email_domain` (admin) | Failed login for `x@domain.test` | Audit row `auth.login_failed` with `meta = {email_domain: "domain.test"}` and no address | As expected | Pass |
| TC-04 | `test_me_rejects_refresh_token` (auth) | Refresh token sent as a bearer token | 401 `invalid_token` | As expected | Pass |
| TC-05 | `test_refresh_rejected_for_deactivated_user` (auth) | Valid refresh token, user set inactive | 401 | As expected | Pass |
| TC-06 | `test_verifier_blocked_from_admin_route` (auth) | Verifier token on an admin route | 403 `forbidden` | As expected | Pass |
| TC-07 | `test_create_normalizes_signs_stores_and_audits` (certificates) | `cert_number = "nbit-2024-cs-0009"` etc. | 201; number stored `NBIT2024CS0009`; signature verifies; audit row written | As expected | Pass |
| TC-08 | `test_create_duplicate_number_conflicts` (certificates) | An existing number | 409 `duplicate_cert_number` | As expected | Pass |
| TC-09 | `test_create_without_signing_key_fails_cleanly` (certificates) | Institution whose PEM is absent | 500 `signing_key_missing`, no partial row | As expected | Pass |
| TC-10 | `test_verifier_cannot_browse_registry` (certificates) | Verifier token on `GET /certificates` | 403 | As expected | Pass |
| TC-11 | `test_get_other_institutions_certificate_is_404` (certificates) | Institution A requesting B's certificate | **404** (not 403) | As expected | Pass |
| TC-12 | `test_import_ok_inserts_all_and_audits_once` (certificates) | Valid 6-row CSV | All 6 inserted, **one** audit row with `count: 6` | As expected | Pass |
| TC-13 | `test_import_is_all_or_nothing_with_per_row_errors` (certificates) | CSV with several bad rows | 422 `csv_invalid` with per-row errors; registry unchanged | As expected | Pass |
| TC-14 | `test_import_accepts_bom_crlf_and_reordered_columns` (certificates) | CSV with BOM, CRLF, shuffled columns | Imported successfully | As expected | Pass |
| TC-15 | `test_import_rejects_rows_for_another_institution` (certificates) | Row with `institution_code = OTHR` | 422 naming the row and column | As expected | Pass |
| TC-16 | `test_audit_log_rejects_update_and_delete` (certificates) | `UPDATE` / `DELETE` on `audit_log` | Database exception from the trigger | As expected | Pass |
| TC-17 | `test_create_makes_keypair_user_and_password` (institutions) | `{name, code, admin_email}` | 201; PEM written; user created; 16-char password returned once | As expected | Pass |
| TC-18 | `test_create_is_audited_without_the_password` (institutions) | Institution creation | Audit rows present; **no** password in any `meta` | As expected | Pass |
| TC-19 | `test_deactivating_blocks_its_users_from_signing_in` (institutions) | `is_active = false`, then login | 401; certificates still verifiable | As expected | Pass |
| TC-20 | `test_delete_is_refused_when_certificates_exist` (institutions) | Delete an institution that has issued | 409 `institution_has_certificates` | As expected | Pass |
| TC-21 | `test_payload_round_trips` (issue_pdf) | Build then parse an AVA1 payload | Identical number, code and signature | As expected | Pass |
| TC-22 | `test_payload_survives_scanner_whitespace` (issue_pdf) | Payload with stray whitespace | Parsed correctly | As expected | Pass |
| TC-23 | `test_payload_rejects_malformed` (issue_pdf) | Wrong prefix / part count / characters | `QrPayloadError` | As expected | Pass |
| TC-24 | `test_create_stores_pdf_once_with_matching_hash` (issue_pdf) | Create a certificate | File on disk; `sha256(file) == file_sha256` | As expected | Pass |
| TC-25 | `test_pdf_endpoint_serves_the_stored_bytes` (issue_pdf) | `GET /certificates/{id}/pdf` | Bytes identical to the stored file | As expected | Pass |
| TC-26 | `test_pdf_carries_a_decodable_qr_matching_the_record` (issue_pdf) | Decode the QR from the generated PDF | Payload matches the record and its signature verifies | As expected | Pass |
| TC-27 | `test_pdf_missing_on_disk_is_reported_not_regenerated` (issue_pdf) | Delete the file, then request it | 404 `pdf_not_available`; no rebuild | As expected | Pass |
| TC-28 | `test_backfill_issues_missing_pdfs_and_is_idempotent` (issue_pdf) | Run backfill twice | Issued on the first run, nothing on the second | As expected | Pass |
| TC-29 | `test_known_active_record_verifies` (engine) | Active record, by number | `VERIFIED` with 6 checks | As expected | Pass |
| TC-30 | `test_unknown_number_goes_to_manual_review` (engine) | Number not in the registry | `MANUAL_REVIEW`, never an accusation | As expected | Pass |
| TC-31 | `test_revoked_record_is_revoked` (engine) | Revoked record | `REVOKED` | As expected | Pass |
| TC-32 | `test_altered_registry_row_is_a_mismatch` (engine) | Row field changed after signing | `MISMATCH` via `record_signature` | As expected | Pass |
| TC-33 | `test_qr_signature_from_another_certificate_is_a_mismatch` (engine) | Valid signature, wrong record | `MISMATCH` | As expected | Pass |
| TC-34 | `test_qr_naming_a_different_institution_is_a_mismatch` (engine) | QR naming another institution | `MISMATCH` | As expected | Pass |
| TC-35 | `test_revocation_wins_over_a_bad_qr_signature` (engine) | Revoked record + invalid QR | `REVOKED` (rule precedence) | As expected | Pass |
| TC-36 | `test_no_result_ever_says_fake` (engine) | Every result path | No check detail contains "fake" or "forged" | As expected | Pass |
| TC-37 | `test_rule_3_exact_file_hash_verifies` (engine_upload) | Uploaded bytes equal `file_sha256` | `VERIFIED` | As expected | Pass |
| TC-38 | `test_rule_3_wins_even_when_a_field_was_misread` (engine_upload) | Exact hash + a misread field | `VERIFIED` — a misread of the exact bytes is a reading error | As expected | Pass |
| TC-39 | `test_a_different_file_hash_is_uncertain_not_a_failure` (engine_upload) | Different bytes | `file_hash` = `uncertain`, not `fail` | As expected | Pass |
| TC-40 | `test_rule_5_a_confident_conflict_is_a_mismatch` (engine_upload) | CGPA differs at *c* ≥ 0.85 | `MISMATCH` naming the field | As expected | Pass |
| TC-41 | `test_a_moderately_confident_difference_blocks_a_valid_qr` (engine_upload) | CGPA differs at *c* = 0.70, QR valid | `MANUAL_REVIEW` — **the bug this rule was added for** | As expected | Pass |
| TC-42 | `test_a_low_confidence_conflict_does_not_overturn_a_valid_qr` (engine_upload) | Field differs at *c* < 0.50, QR valid | `VERIFIED`; field reported `not_read` | As expected | Pass |
| TC-43 | `test_the_band_edges_are_the_thresholds_not_approximations` (engine_upload) | *c* exactly 0.85 and exactly 0.50 | Each belongs to the stricter band | As expected | Pass |
| TC-44 | `test_the_thresholds_are_configurable` (engine_upload) | Custom `Thresholds` | Engine honours them | As expected | Pass |
| TC-45 | `test_a_confident_conflict_beats_a_valid_qr` (engine_upload) | Confident conflict + valid QR | `MISMATCH` | As expected | Pass |
| TC-46 | `test_a_valid_qr_verifies_when_nothing_at_all_was_read` (engine_upload) | Valid QR, zero fields read | `VERIFIED` | As expected | Pass |
| TC-47 | `test_an_unread_field_is_reported_against_the_registry_value` (engine_upload) | Field not read | Check detail names the registry value it was not compared with | As expected | Pass |
| TC-48 | `test_identifiers_tolerate_ocr_confusables` (engine_upload) | `N81T2024C50001` vs `NBIT2024CS0001` | Match | As expected | Pass |
| TC-49 | `test_a_genuinely_different_identifier_still_conflicts` (engine_upload) | A genuinely different number | Conflict | As expected | Pass |
| TC-50 | `test_marks_are_not_compared_when_the_record_uses_cgpa` (engine_upload) | Record with CGPA only | No `field_match.marks` entry | As expected | Pass |
| TC-51 | `test_the_date_of_issue_is_compared_like_any_other_field` (engine_upload) | Differing issue date | Compared, not skipped | As expected | Pass |
| TC-52 | `test_a_name_must_match_exactly_for_now` (engine_upload) | A near-miss name | Conflict — **pins the absence of fuzzy matching** | As expected | Pass |
| TC-53 | `test_sniff_type_reads_magic_bytes` (uploads) | PNG / PDF / JPEG headers | Correct MIME and extension | As expected | Pass |
| TC-54 | `test_sniff_type_ignores_a_signature_that_is_not_at_the_start` (uploads) | `%PDF-` later in the file | Rejected | As expected | Pass |
| TC-55 | `test_upload_trusts_bytes_not_the_filename` (uploads) | A PNG named `.pdf` | Stored as `image/png` | As expected | Pass |
| TC-56 | `test_upload_rejects_a_disguised_unsupported_file` (uploads) | Arbitrary bytes named `.pdf` | 415, nothing written | As expected | Pass |
| TC-57 | `test_store_accepts_a_file_exactly_at_the_limit` (uploads) | Exactly `UPLOAD_MAX_MB` | Accepted | As expected | Pass |
| TC-58 | `test_store_rejects_a_file_over_the_limit` (uploads) | One byte over | 413 `upload_too_large` | As expected | Pass |
| TC-59 | `test_job_status_hides_another_verifiers_job` (uploads) | Verifier B polling A's job | 404, identical to an unknown id | As expected | Pass |
| TC-60 | `test_job_finished_without_an_id_is_reported_failed` (uploads) | Job returning no usable id | `failed`, never left pending | As expected | Pass |
| TC-61 | `test_state_for_treats_the_unknown_as_failed` (uploads) | An unmapped RQ status | `failed` | As expected | Pass |
| TC-62 | `test_prune_command_skips_recent_orphans` (uploads) | Orphan file < 1 h old | Kept | As expected | Pass |
| TC-63 | `test_prune_command_never_lists_a_referenced_file` (uploads) | A file with a row | Not reported as an orphan | As expected | Pass |
| TC-64 | `test_untouched_issued_pdf_verifies_by_file_hash` (e2e) | The original PDF uploaded unchanged | `VERIFIED` via `file_hash` | As expected | Pass |
| TC-65 | `test_rendered_png_verifies_through_the_qr_and_fields` (e2e) | PDF rendered to PNG | `VERIFIED` through the QR | As expected | Pass |
| TC-66 | `test_a_photographed_page_verifies` (e2e) | Page inset on a background | `VERIFIED` after perspective correction | As expected | Pass |
| TC-67 | `test_a_degraded_genuine_document_is_never_a_mismatch` (e2e) | Rotated, blurred, JPEG-compressed | Not `MISMATCH` | As expected | Pass |
| TC-68 | `test_an_edited_cgpa_is_a_mismatch_naming_the_field` (e2e) | CGPA properly edited in the PDF | `MISMATCH`; only that field fails | As expected | Pass |
| TC-69 | `test_only_the_edited_field_fails` (e2e) | One edited field | Exactly one `field_match.*` = `fail` | As expected | Pass |
| TC-70 | `test_a_random_image_is_manual_review` (e2e) | Random-pixel image | `MANUAL_REVIEW`; no template matched | As expected | Pass |
| TC-71 | `test_a_genuine_pdf_of_a_revoked_certificate_is_revoked` (e2e) | Genuine PDF, revoked record | `REVOKED` — outranks a byte-perfect hash | As expected | Pass |
| TC-72 | `test_the_stored_evidence_is_auditable_but_not_the_document` (e2e) | Any upload | `extracted_fields` has fields and metadata, **not** the document text | As expected | Pass |
| TC-73 | `test_a_white_box_overlay_is_not_detected_on_the_pdf_path` (e2e) | `cover_pdf_text` overlay | Pins the **known defect**: the PDF path misses it | As expected | Pass |
| TC-74 | `test_ocr_of_the_rendered_page_does_see_the_overlay` (e2e) | The same file rendered and OCRed | OCR *does* catch it — the other half of the trade-off | As expected | Pass |
| TC-75 | `test_decode_qr_records_which_reader_and_scale_read_it` (ocr) | A rendered page | `qr_reader` and `qr_scale` recorded | As expected | Pass |
| TC-76 | `test_the_ladder_stops_at_the_first_certificate_payload` (ocr) | Page with an AVA1 code and another code | Stops at the AVA1 one | As expected | Pass |
| TC-77 | `test_a_rect_found_on_an_upscaled_copy_comes_back_in_original_coordinates` (ocr) | Code read at 2× | Rect divided back to original coordinates | As expected | Pass |
| TC-78 | `test_an_upscale_that_would_be_enormous_is_skipped` (ocr) | Image > 40 MP at that scale | Scale skipped | As expected | Pass |
| TC-79 | `test_the_qr_is_read_from_the_original_photo_not_a_prepared_copy` (ocr) | A photograph | Decoded from the original pixels | As expected | Pass |
| TC-80 | `test_the_qr_is_masked_so_it_does_not_pollute_the_text` (ocr) | A rendered page | No QR-module noise in the extracted fields | As expected | Pass |
| TC-81 | `test_extract_fields_returns_nothing_for_an_unknown_layout` (ocr) | Unknown layout text | `template = None`, `fields = {}` | As expected | Pass |
| TC-82 | `test_id_normalizer_takes_only_the_first_token` (ocr) | `"NBIT2024CS0001 rat a"` | `NBIT2024CS0001` | As expected | Pass |
| TC-83 | `test_issued_pdf_is_read_from_its_text_layer_not_ocr` (ocr) | The issued PDF | `text_source = pdf_text_layer`, confidence 1.0 | As expected | Pass |
| TC-84 | `test_a_pdf_with_no_text_layer_falls_back_to_ocr` (ocr) | Image-only PDF | Rasterised and OCRed | As expected | Pass |
| TC-85 | `test_extract_never_raises_on_rubbish` (ocr) | Undecodable bytes | Empty `ExtractedPage`, no exception | As expected | Pass |
| TC-86 | `test_a_verified_result_cannot_be_escalated` (reviews) | Escalate a `VERIFIED` result | 409 `not_escalatable` | As expected | Pass |
| TC-87 | `test_only_one_request_may_be_open_per_verification` (reviews) | Two requests for one verification | Second is 409 `request_already_open` | As expected | Pass |
| TC-88 | `test_another_institution_cannot_see_the_case` (reviews) | Institution B reading A's case | 404 | As expected | Pass |
| TC-89 | `test_the_admin_may_read_but_not_decide` (reviews) | Admin attempting a decision | Reads fine; 403 on any action | As expected | Pass |
| TC-90 | `test_a_verifier_cannot_answer_their_own_request` (reviews) | Verifier posting a decision | 403 | As expected | Pass |
| TC-91 | `test_the_verifier_replying_puts_it_back_to_pending` (reviews) | Verifier replies on `needs_info` | Status → `pending` | As expected | Pass |
| TC-92 | `test_the_institution_replying_leaves_it_needing_info` (reviews) | Institution replies again | Stays `needs_info` | As expected | Pass |
| TC-93 | `test_not_issued_requires_a_reason` (reviews) | `not_issued` with a blank reason | 422 `reason_required` | As expected | Pass |
| TC-94 | `test_confirm_and_add_creates_a_signed_certificate_and_closes_the_case` (reviews) | A valid prefilled form | Signed certificate + PDF created; case `confirmed_added` | As expected | Pass |
| TC-95 | `test_a_failed_add_leaves_the_case_open_to_try_again` (reviews) | A duplicate number in the form | Create fails; case stays open | As expected | Pass |
| TC-96 | `test_a_decision_never_edits_the_verification` (reviews) | Any decision | The verification row is byte-identical afterwards | As expected | Pass |
| TC-97 | `test_an_open_request_holds_its_document_back_from_retention` (reviews) | Expired upload with an open case | Not pruned; reported as held | As expected | Pass |
| TC-98 | `test_a_case_counts_as_overdue_after_seven_days` (reviews) | Case created 8 days ago | Counted in `open_over_7_days` | As expected | Pass |
| TC-99 | `test_a_new_request_may_be_opened_once_the_last_one_closed` (reviews) | Closed case, then a new request | Allowed | As expected | Pass |
| TC-100 | `test_audit_log_filters_by_action_prefix` (admin) | `?action=certificate.` | Matches create, import, revoke and backfill | As expected | Pass |
| TC-101 | `test_audit_log_filters_by_date_range` (admin) | Inclusive UTC range | Correct subset | As expected | Pass |
| TC-102 | `test_stats_counts_the_registry_and_verifications` (admin) | Seeded data | All counts correct | As expected | Pass |
| TC-103 | `test_unreadable_payload_is_rejected_not_recorded` (verify_api) | `POST /verify/qr` with arbitrary text | 422 `qr_payload_invalid`; **no verification row** | As expected | Pass |
| TC-104 | `test_number_is_normalized_before_lookup` (verify_api) | `"nbit 2024 cs 0001"` | Found | As expected | Pass |
| TC-105 | `test_another_verifier_cannot_read_someone_elses_verification` (verify_api) | Verifier B reading A's result | 404 | As expected | Pass |
| TC-106 | `test_demo_certificates_are_valid_and_unique` (seed) | The 20 seed certificates | All validate; numbers unique | As expected | Pass |
| TC-107 | `test_unknown_route_uses_error_envelope` (health) | `GET /nope` | 404 in the `{"error": {...}}` envelope | As expected | Pass |

## 5.3 Bugs and issues

### 5.3.1 Table 5.3 — Known open issues

| # | Issue | Severity | Status |
|---|---|---|---|
| 1 | A white box drawn over a PDF's text can show a human one value while the text layer still reports the original | **High (security)** | **Open — deliberate trade-off**, pinned by two tests |
| 2 | OCR of a real phone photograph is weak; the certificate and roll numbers are unread on almost every image, and 4 of 12 match no template | **Medium** | Open — the acknowledged unsolved problem; the QR covers it |
| 3 | The OCR-only path on a real photograph (no readable QR) has never been tested end to end | Medium | Open — no such photograph exists in the evaluation set |
| 4 | Fuzzy name matching is unimplemented; `rapidfuzz` and both name thresholds are dead configuration | Medium | Open — the declared next task |
| 5 | Shareable time-limited verification links are unimplemented; only the TTL setting exists | Medium | Open — Tier 2 item 10 |
| 6 | `services/admin.py:37` emits `SyntaxWarning: invalid escape sequence '\%'` and `'\_'` | **Low (cosmetic)** | Open — the produced characters are correct; the string literals are not raw |
| 7 | The worker does not reload code, so changing anything the OCR job touches requires `docker compose restart worker` | Low (developer experience) | Open — by design (`--reload` on `api` only) |
| 8 | PDF issuance is synchronous inside create and import, so a very large CSV blocks the request | Low | Open — accepted at current scale |
| 9 | Nothing schedules `prune_uploads`; it must be run manually | Low | Open |
| 10 | No frontend tests exist, contrary to the specification's stack table | Medium (process) | Open |
| 11 | Demo-database leftovers: 13 `upload` verifications from measurement runs, two institutions with zero certificates, two throwaway users, ~27 orphaned issued PDFs from before a re-seed | Housekeeping | Known and documented |
| 12 | There is no ready-made `REVOKED` certificate after a re-seed; one must be revoked before a demonstration | Housekeeping | Documented in the demo script |

### 5.3.2 Issue 1 in detail — the white-box PDF overlay

**The defect.** The PDF path trusts the text layer. Covering text with a filled
rectangle and printing a different value on top leaves the *original* glyphs in
the content stream. The document therefore reads as `VERIFIED` — every field
matches the registry, because the text layer still contains the original
values — while displaying different values to a human.

**Why it is not fixed.** Fixing it means OCRing every PDF to cross-check the
text layer, which turns the 0.09 s fast path into seconds for every upload.
That cost is the whole value of the text-layer path.

**How it is handled instead.** The behaviour is pinned by **two** tests, one
for each half, so neither can change silently:

- `test_a_white_box_overlay_is_not_detected_on_the_pdf_path` — asserts the
  current (defective) behaviour, so a future change is visible.
- `test_ocr_of_the_rendered_page_does_see_the_overlay` — asserts that OCR of
  the rendered page *does* catch it, which is the available mitigation and the
  basis of any future fix.

**Practical mitigation available today.** A verifier who suspects an overlay can
photograph or screenshot the PDF and upload that instead, which routes the
document down the OCR path where the overlay is visible.

### 5.3.3 Issue 2 in detail — OCR on real photographs

`prepare()` is tuned for a clean render or a flat scan. Specifically:

- A **global** Otsu threshold floods a shadowed half of a page to solid black.
- Nothing corrects uneven illumination.
- Nothing rescales small text — `upscale_if_small` only triggers below 1200 px
  width, which a phone photo exceeds while its *text* is still too small.

Measured consequences on `samples/photos`: the certificate number and roll
number are unread on almost every photograph, and **no template matches at all
on 4 of 12**. This is survivable only while a QR decodes.

### 5.3.4 Bugs found and fixed during development

These are the instructive ones for the report, because each produced a design
change that is still in the code.

**Fixed bug 1 — a valid QR masked a differing printed value.** A CGPA printed
9.99, read at 76 % confidence against a registry value of 9.32, came back
`VERIFIED`, because 76 % was below the conflict threshold and a valid QR
carried the result. **Fix:** the three confidence bands, and the rule that
`VERIFIED` requires that nothing *differs*. **Cost, measured honestly:** two of
the twelve evaluation photographs moved from `VERIFIED` to `MANUAL_REVIEW` —
both genuine certificates whose OCR misread a value. Nothing genuine became a
`MISMATCH`.

**Fixed bug 2 — "not read" and "differs" were both `uncertain`.** This
flattened the one distinction that matters, and an unread field silently
blocked a verdict while reading to the verifier as though it had agreed.
**Fix:** `Check` gained a `state` (`matches` / `differs` / `not_read`) beside
its `status`; unread fields now block nothing and are named explicitly on the
result page.

**Fixed bug 3 — rewriting OCR confusables corrupted correct readings.** The
first implementation *rewrote* extracted identifiers to fix O/0 and S/5
confusions, which turned a **correct** reading of `NBIT2024CS0001` into
`N81T2024C50001`. **Fix:** collapse confusables on *both* sides at comparison
time only, never rewriting a stored or extracted value. The set was
deliberately not widened further, because collapsing more characters makes
genuinely different identifiers compare equal.

**Fixed bug 4 — `qr_signature` gated on the method.** The check originally ran
only when `method == QR`, which silently skipped it for every image upload —
precisely the case the whole QR-first design depends on. **Fix:** the check is
keyed on whether a payload is *present*.

**Fixed bug 5 — the QR polluted the OCR text.** The code sits in the same
horizontal band as the boxed fields, and page-level segmentation read its
modules as glyphs on those baselines, appending noise like `"rat a"` to
adjacent values. **Fix:** mask the QR white before OCR. Mean line confidence
rose from 0.77 to 0.92.

**Fixed bug 6 — the watermark was read as text.** The diagonal `SPECIMEN`
watermark sits at about grey 224 and Otsu kept it. **Fix:** `suppress_light()`
flattens everything at or above 205 to white.

**Fixed bug 7 — `issue_date` anchored on its label found the wrong line.** OCR
reflows the page so the line after `DATE OF ISSUE` is the QR's "Scan to verify"
caption. **Fix:** find the date by pattern instead; the ISO date is the only
`YYYY-MM-DD` on the page.

**Fixed bug 8 — a test deleted the demo database.** A fixture exercising the
RQ job used `SessionLocal` directly, which points at the *demo* database, and
deleted every certificate and verification row in it. **Fix:** tests that
exercise the job patch `SessionLocal` to return the rolled-back test session,
and the rule "never let a test open a real session" is recorded as a standing
decision.

### 5.3.5 The reverted optimisation — a documented negative result

Worth a section of its own in the report, because it is the project's clearest
methodological lesson.

A round of work added a **PP-OCRv5 ONNX engine** and a second preprocessing
pipeline (illumination correction by division, CLAHE, adaptive thresholding,
glare clipping, text-height rescaling, three variants OCRed with the best read
kept). Measured on eight **synthetically degraded** renders of the project's
own certificate, it read **48 of 48** critical fields against the existing
code's **31 of 48** — an apparently decisive win.

On **real phone photographs of printed certificates it read worse than the code
it replaced.** The whole round was reverted.

**The error was the test set, not the measurement.** A Gaussian gradient over a
crisp 300 DPI render is not a photograph, and tuning against it optimised for
an artefact that had been invented. Three things survive the revert:

1. `samples/photos/` is now the **only** evaluation set, and a change to OCR is
   not an improvement until it wins there.
2. Three specific technical lessons are recorded for a future attempt: measure
   *text height* rather than image width; flatten the watermark *before*
   lifting contrast; and gate junk uploads *before* OCR, because Tesseract
   spent 54 seconds reading 25,469 characters out of a random-pixel image.
3. The `OcrEngine` abstraction was validated for real: adding an entire second
   engine touched only `engines.py`, which is exactly the claim the design
   made.

## 5.4 Deployment, installation and configuration

### 5.4.1 Prerequisites

Docker Desktop (or Docker Engine with the Compose v2 plugin). Nothing else is
installed on the host — Python, Node, Postgres, Redis and Tesseract all live
inside containers.

### 5.4.2 First-time setup

```bash
# 1. Configuration
cp .env.example .env
#    Edit .env: set JWT_SECRET to a real random value.
#    POSTGRES_PASSWORD should also be changed outside local development.

# 2. Build and start all five services
docker compose up --build -d

# 3. Create the schema
docker compose exec api alembic upgrade head

# 4. Seed demo data (idempotent: safe to run twice)
docker compose exec api python -m app.scripts.seed

# 5. Issue PDFs for any rows created before issuance existed (idempotent)
docker compose exec api python -m app.scripts.backfill_pdfs
```

The seed script prints the demonstration logins. They are, from `seed.py`:

| Role | Email | Password |
|---|---|---|
| admin | `admin@ava.test` | `Admin@12345` |
| institution | `registrar@nbit.test` | `Inst@12345` |
| verifier | `verifier@ava.test` | `Verify@12345` |

It creates the fictional institution **NBIT** ("Northbridge Institute of
Technology (fictional)") and 20 synthetic certificates across six programmes,
with numbers of the form `NBIT<year><programme><nnnn>`.

### 5.4.3 Access points

| What | URL |
|---|---|
| Web application | `http://localhost:5173` |
| API (direct) | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| OpenAPI document | `http://localhost:8000/openapi.json` |
| Health check | `http://localhost:8000/health` |

### 5.4.4 Day-to-day commands

```bash
docker compose up -d                      # start
docker compose down                       # stop (volumes kept)
docker compose logs -f api worker         # follow logs
docker compose restart worker             # REQUIRED after changing OCR-path code or settings
docker compose exec api pytest -q         # the full suite (~2.5 min)

# Skip the slow OCR tests while working on something else
docker compose exec api pytest -q \
  --ignore=tests/test_ocr_pipeline.py \
  --ignore=tests/test_upload_verification_e2e.py

docker compose exec api alembic revision --autogenerate -m "message"
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.prune_uploads --dry-run
docker compose exec api python -m app.scripts.prune_uploads

# Regenerate the frontend's API types after any API change
docker compose exec web npm run gen:api
```

`npm run gen:api` resolves its base URL from `API_URL`, then
`VITE_API_BASE_URL`, then `API_PROXY_TARGET`. Because Compose sets
`API_PROXY_TARGET=http://api:8000` in the web container, the bare form works
without extra flags.

### 5.4.5 Table 5.4 — Environment variables (`.env.example`)

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_USER` | `ava` | Database user |
| `POSTGRES_PASSWORD` | `ava` | Database password — **change outside local development** |
| `POSTGRES_DB` | `ava` | Database name; tests use `<name>_test` |
| `POSTGRES_PORT` | `5432` | Published host port |
| `API_PORT` | `8000` | Published host port for the API |
| `WEB_PORT` | `5173` | Published host port for the SPA |
| `REDIS_PORT` | `6379` | Published host port for Redis |
| `DATABASE_URL` | `postgresql+psycopg://ava:ava@localhost:5432/ava` | Overridden inside Compose to point at the `db` service |
| `REDIS_URL` | `redis://localhost:6379/0` | Overridden inside Compose |
| `ENV` | `dev` | Reported by `/health` |
| `LOG_LEVEL` | `INFO` | Worker logging level |
| `API_V1_PREFIX` | `/api/v1` | Router prefix |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allow-list; not exercised in the default same-origin setup |
| `JWT_SECRET` | *placeholder* | **Must be replaced.** HS256 signing key |
| `JWT_ALGORITHM` | `HS256` | — |
| `ACCESS_TOKEN_MINUTES` | `15` | Access-token lifetime |
| `REFRESH_TOKEN_DAYS` | `7` | Refresh-token lifetime |
| `KEYS_DIR` | `/keys` | Ed25519 private keys, one PEM per institution code |
| `UPLOAD_DIR` | `/data/uploads` | Verifier uploads go to `<dir>/verify/` |
| `UPLOAD_MAX_MB` | `10` | Upload size limit |
| `UPLOAD_RETENTION_DAYS` | `7` | Upload expiry |
| `ISSUED_DIR` | `/data/uploads/certificates` | Issued PDFs — inside the uploads volume but never pruned |
| `IMPORT_MAX_ROWS` | `5000` | CSV row limit |
| `IMPORT_MAX_MB` | `2` | CSV size limit |
| `OCR_MIN_FIELD_CONFIDENCE` | `0.85` | At or above: a differing field is a conflict (`MISMATCH`) |
| `OCR_DISCREPANCY_CONFIDENCE` | `0.50` | At or above (and below the above): a possible discrepancy |
| `NAME_MATCH_THRESHOLD` | `90` | **Declared, currently unused** |
| `NAME_CONFLICT_THRESHOLD` | `75` | **Declared, currently unused** |
| `SHARE_LINK_TTL_HOURS` | `72` | **Declared, feature not implemented** |
| `API_PROXY_TARGET` | `http://api:8000` | Where the Vite dev server proxies `/api` |
| `VITE_API_BASE_URL` | *(commented out)* | Absolute-URL escape hatch; setting it re-introduces the CORS requirement |

### 5.4.6 Exposing the stack for a demonstration

Because the frontend calls the API at a relative path and Vite proxies `/api`,
**only port 5173 needs to be reachable**. Ports 8000, 5432 and 6379 are
published for local tooling and should not be forwarded. If `VITE_API_BASE_URL`
is set to an absolute URL instead, port 8000 must also be exposed and the web
origin must be added to `CORS_ORIGINS`.

### 5.4.7 Changes required before any real deployment

Stated as a checklist, since none of these is done:

1. Replace `JWT_SECRET` and `POSTGRES_PASSWORD`; move both into a secret store.
2. Terminate TLS in front of the stack.
3. Replace the Vite dev server with `npm run build` and a static file server or
   CDN; the current `web` service is a development server.
4. Run `uvicorn` without `--reload`, behind a process manager, with multiple
   workers.
5. Move the refresh token to an `httpOnly`, `Secure`, `SameSite` cookie.
6. Add rate limiting on `/auth/login` at minimum.
7. Encrypt the signing keys at rest, or move them to an HSM/KMS; define a
   custody and backup policy.
8. Schedule `prune_uploads` (cron or an RQ scheduled job).
9. Add database backups and test a restore.
10. Add structured logging, error reporting and uptime monitoring.
11. Complete a data-protection review and publish a retention policy.

## 5.5 Hosting / deployment platform

**No hosted deployment exists.** The project runs on a local Docker Compose
stack only; there is no cloud provider account, no CI/CD pipeline, no
Kubernetes manifest, no Terraform, and no public URL. The repository contains
no deployment configuration beyond `docker-compose.yml` and the two
Dockerfiles.

This is consistent with the project's status as a prototype, and the
deployment-readiness gap is listed honestly in §5.4.7 and §6.5. For the report,
the accurate statement is: *the system is container-ready and portable — the
same Compose definition runs unchanged on any Docker host — but it has not been
deployed to a server, and the `web` service in its current form is a
development server rather than a production build.*

---

# CHAPTER 6: ANALYSIS AND RESULTS

## 6.1 Working output of each feature

Each subsection describes what actually appears on screen, so the
corresponding screenshot (Figures 6.2–6.20) can be captioned directly from it.

### 6.1.1 Authentication (Figure 6.2)

A centred card headed "Sign in" with the subtitle "Authenticity Validator for
Academia", email and password fields, a submit button that reads "Signing in…"
while pending, and the footer "Prototype — all data is synthetic." A wrong
password produces the inline message "Email or password is incorrect." — the
same message an unknown email produces. On success the user lands on the
dashboard, or on whichever page they originally attempted.

### 6.1.2 Administrator dashboard (Figure 6.3)

Four statistic tiles across the top: **Institutions** (with "N users in
total"), **Certificates** (with "N revoked"), **Verifications** (with "N in the
last 7 days"), and **Logins (7 days)** (with "N failed"). Below them, a
**Verification requests** card showing *Open* and *Open more than 7 days* —
the second turning amber when non-zero — and a **Verification results** card
breaking the four statuses out in their own colours (green `VERIFIED`, red
`MISMATCH`, amber `MANUAL REVIEW`, grey `REVOKED`). An institution user or
verifier sees only the "Your account" card.

### 6.1.3 Registry and issuance (Figures 6.4, 6.5, 6.7)

The registry table lists the 20 seeded certificates with a debounced search
box; typing `nandini`, `NBIT2022CS0020` or `18CS020` all find the same row,
because the search covers student name, certificate number and roll number
with identifiers normalized before matching.

"Add certificate" opens an eight-field dialog. Submitting an invalid value
produces a per-field message under the offending input — for example a CGPA of
`11.2` yields "Input should be less than or equal to 10", and an issue date
before the year of passing yields "issue_date cannot be before the year of
passing".

The download button produces a one-page A4-landscape PDF (Figure 6.7): the
institution name at the top with its code beneath, `DEGREE CERTIFICATE`, "This
is to certify that", the student name in large type, the programme, the year
and grade, three boxed fields at the lower left (certificate number, roll
number, date of issue), the QR code bottom right with "Scan to verify", a
diagonal `SPECIMEN — NOT A REAL DOCUMENT` watermark across the page, and the
footer "Prototype issuance — synthetic data, not a real academic document."

### 6.1.4 CSV import (Figure 6.6)

Uploading `samples/certificates-nbit-valid.csv` reports "Imported 6
certificates." and offers a link to the registry; six signed records and six
PDFs now exist.

Uploading `samples/certificates-nbit-with-errors.csv` — which was built to
exercise every failure mode — produces a card headed **"Nothing was imported"**
with the message "5 row(s) have errors. Nothing was imported — fix them and
upload again." and a table:

| Line | Column | Problem |
|---|---|---|
| 3 | `cgpa` | Input should be less than or equal to 10 |
| 4 | `issue_date` | Use the format YYYY-MM-DD, e.g. 2024-07-20. |
| 5 | `institution_code` | Row is for institution OTHR; you can only import for NBIT. |
| 6 | `cert_number` | Duplicate of row 2 in this file. |
| 7 | `cert_number` | Already exists in the registry. |
| 8 | `cgpa` | At least one of cgpa or marks is required |

The registry is unchanged — this is the all-or-nothing guarantee visible on
screen.

### 6.1.5 The five verification demonstration paths

These are the project's own scripted demonstration cases, all reproducible.

**Path 1 — `VERIFIED` instantly, by file hash (Figure 6.9).** Download a
certificate's PDF from the registry and upload it unchanged. The file hash
matches, every field matches, and the banner's evidence line reads "Verified by
the file itself — these are the exact bytes the institution issued." The
extracted-fields table states that the values were "read directly from the
PDF's text layer (exact, not OCR)". Roughly 0.09 s.

**Path 2 — `VERIFIED` through the signed QR (Figure 6.10).** Photograph a
printout, or upload one of `samples/photos/`. The hash no longer matches, so
`file_hash` reports `uncertain` with the explanation that a scan or re-save is
expected. The QR carries the result, and the evidence line reads "Verified by
the signed QR code on the document; its printed text was read as a
cross-check." Fields the OCR could not read are listed as "Couldn't read on the
document: Roll number, Certificate number — compare with the issued details
below", and each appears in the table as "not checked" beside the registry's
value.

**Path 3 — `MISMATCH` with a field difference (Figure 6.11).** Edit one printed
value properly (with a redaction, as `tests/ocr_fixtures.edit_pdf_text` does)
and upload. The QR still verifies — which is exactly why the field check
matters — and only the edited row reads "conflicts", with the discrepancy box
naming it: "CGPA — document shows 9.99, institution issued 9.32". The banner
explains that this is not proof of forgery, since a reprint, a typo or an
edited copy can cause it.

**Path 4 — `MANUAL_REVIEW` (Figure 6.12).** Upload any unrelated image or PDF.
No template matches, so no field is compared and the single `field_match` entry
reads "The document's layout was not recognised, so no fields could be
compared." The evidence line reads "Neither a signed QR nor a known layout
could be read from this document, so nothing was decided from it." Nothing is
decided *about* the document.

**Path 5 — `REVOKED` (Figure 6.13).** Revoke a certificate, then upload its
genuine PDF. Revocation outranks even a byte-perfect hash match, and the banner
reads "The issuing institution has withdrawn this certificate. It was issued,
but the institution no longer stands behind it."

A sixth case appears in the measured data: **"Possible discrepancy"**, the
distinct wording used when a result is `MANUAL_REVIEW` *because* a printed value
differs but was not read confidently enough to call a conflict. Two of the
twelve evaluation photographs produce it.

### 6.1.6 The verification request workflow (Figures 6.15–6.17)

Reproducible end to end:

1. As the verifier, verify a number the registry does not have (e.g.
   `NBIT2099ZZ0001`) or upload a photograph of a certificate that is not in the
   registry. Result: `MANUAL_REVIEW`.
2. Click **Request confirmation from issuing institution**. Because nothing
   identified an institution, a dropdown of active institutions appears; pick
   NBIT, add a note, send. The page redirects to the new request.
3. Sign in as `registrar@nbit.test`. The navigation shows **Verification
   requests 1**. Opening it shows the uploaded document rendered inline, the
   fields read from it, "No record in your registry matches this document…",
   and the verifier's note.
4. **Ask for more info** ("which year was this issued?"). Back as the verifier,
   the request reads "The institution asked a question"; replying returns it to
   "Waiting for the institution".
5. As the institution, **Confirm & add to registry**. The form is prefilled
   from what the document said and fully editable; correcting and submitting
   closes the case as *Confirmed and added to the registry* and creates a
   signed certificate with its PDF.
6. As the verifier, the original result **still reads `MANUAL_REVIEW`**, with
   "Confirmed and added to the registry by NBIT" beside it. Verifying that
   number again produces a **new** `VERIFIED` verification. This is the design
   point made visible: a verification records what the system concluded at a
   time, and an institution's answer is a later, separate fact.
7. As the administrator, the dashboard shows the open and overdue counts and
   `/requests` lists every case — with no way to answer one.

### 6.1.7 Audit log (Figure 6.18)

Rows appear in reverse chronological order with the actor's email and a
`key=value` rendering of `meta`. Filtering by `certificate.` shows create,
import, revoke and backfill together. A failed login shows
`email_domain=nbit.test` and nothing more — no address, no password. Attempting
`UPDATE` or `DELETE` on the table raises
`audit_log is append-only (UPDATE not allowed)` from the trigger.

## 6.2 Performance observations

### 6.2.1 Table 6.1 — Measured results on the evaluation set

**Method:** 12 phone photographs of 2 printed certificates, each put through
the **real upload API** — login, `POST /verify/upload`, the RQ worker, then
reading the stored verification — not through a test harness. Ground truth is
in `samples/photos/Actual_data.txt`.

| Metric | Before the confidence bands | After (current) |
|---|---|---|
| QR decoded | 12 / 12 | **12 / 12** — 11 at 1×, `sample3` at 2×, all by zxing-cpp |
| `VERIFIED` | 12 | **10** |
| `MANUAL_REVIEW` | 0 | **2** (`sample6`, `sample11`) |
| `MISMATCH` | 0 | **0** |
| Median time per photograph | 1.6 s | **1.8 s** |

The two that moved are genuine certificates whose OCR misread a value:

| Photograph | Field | Printed | OCR read | Confidence | Outcome |
|---|---|---|---|---|---|
| `sample6` | CGPA | 8.56 | "8" | 70 % | Possible discrepancy → `MANUAL_REVIEW` |
| `sample11` | Date of issue | 2022-07-20 | "2072-01-20" | exactly 50 % | Possible discrepancy → `MANUAL_REVIEW` |

Field-level outcome across the set: of the 48 comparable critical fields, 28
were read and matched and 20 were uncertain; **not one produced a conflict**,
because every misread was also a low-confidence read. The certificate and roll
numbers remain unread on almost every photograph — unchanged by this work, and
now said out loud on the result page instead of being silently skipped.

### 6.2.2 Table 6.2 — Latency by verification path

| Path | Measured time | What dominates |
|---|---|---|
| Original PDF uploaded unchanged | **≈ 0.09 s** | PyMuPDF text-layer read; the hash check short-circuits the rest |
| Phone photograph (QR at 1×) | **median 1.8 s** | Tesseract on the prepared image |
| QR decode, zxing-cpp | **1–43 ms** | — |
| QR decode, pyzbar | 12–242 ms | Fallback only |
| Verify by number or QR payload | tens of milliseconds | One indexed query + two Ed25519 verifications |
| Ed25519 sign or verify | sub-millisecond | — |
| Full backend test suite | **143.26 s** for 373 cases | ~2 min of it is real Tesseract in the OCR tests |

### 6.2.3 Figure 6.1 — Outcome distribution on the evaluation set

```mermaid
pie showData
    title Verification outcomes — 12 real phone photographs
    "VERIFIED (10)" : 10
    "MANUAL_REVIEW — possible discrepancy (2)" : 2
    "MISMATCH (0)" : 0
    "REVOKED (0)" : 0
```

### 6.2.4 Other observations

- **The QR-first ordering is the single most consequential performance
  decision.** A hit at 1× costs 1–43 ms and settles the authenticity question
  cryptographically. Without it the system would depend on an OCR path that
  loses the certificate number on almost every photograph.
- **Masking the QR before OCR** raised mean line confidence from 0.77 to 0.92
  — a larger improvement than any thresholding change attempted.
- **Junk input is pathologically slow.** Tesseract spent **54 seconds** reading
  25,469 characters out of a random-pixel image. There is no gate in front of
  OCR for obviously non-document input, which is a recorded improvement for a
  future attempt.
- **The PDF fast path is ~20× faster than the OCR path**, which is precisely
  why the white-box overlay defect (§5.3.2) has not been fixed by OCRing every
  PDF.
- **Dependency cost was measured, not assumed.** Tesseract adds 3 packages;
  `paddleocr==3.0.3` would add 109 and `3.7.0` would add 55 plus a conflicting
  OpenCV build. `zxing-cpp` resolves to exactly one package with no
  dependencies — a 0.96 MB prebuilt wheel.
- **Bundle size.** The verify route is lazy-loaded; at the time that split was
  measured the main bundle was ~372 kB and the verify chunk ~352 kB. The
  352 kB chunk was dominated by `html5-qrcode`, which has since been removed,
  so the current verify chunk is substantially smaller — **this has not been
  re-measured**, and should be before the figure is quoted in the report.

## 6.3 Results and discussion

### 6.3.1 The objectives were met, with two documented exceptions

All five Tier 1 objectives and four of the five Tier 2 objectives are complete
and demonstrable. The exceptions are stated in §1.4.2: fuzzy name matching
(item 7's remaining half) and the shareable time-limited link (item 10's
remaining half). No Tier 3 objective was attempted. This is an honest 9.5 of
10 against the planned scope, with the Tier 3 stretch goals untouched.

### 6.3.2 The central result: a false-mismatch rate of zero on genuine documents

The most important number in the project is a **zero**. Across 12 real
photographs of genuine certificates — degraded by angle, lighting and JPEG
compression, with roughly 40 % of critical fields unreadable — **not one
produced a `MISMATCH`**. Two were routed to human review, which is the correct
and conservative outcome when a reader is moderately unsure.

This matters because the cost asymmetry is severe. Wrongly flagging a genuine
degree as a mismatch harms a real person's employment prospects and destroys
trust in the system; routing an uncertain case to a human costs a few minutes
of a registrar's time. The confidence-band design makes that trade deliberately
and measurably, rather than by accident of a single threshold.

### 6.3.3 The confidence bands cost two verifications and were worth it

Before the bands, all 12 photographs returned `VERIFIED`. After, 10 do. On its
face that is a 17 % regression; in substance it is a correction. Both documents
that moved contain a printed value that the system read as disagreeing with the
registry, and in both cases the honest answer is "a person should check this
against the paper". The alternative — the previous behaviour — was to report
`VERIFIED` for a document whose printed CGPA the system itself believed, at
70 % confidence, to differ from what the institution issued.

The measurement also demonstrates that the thresholds are tuned sensibly rather
than arbitrarily: `sample11` read its date at *exactly* 0.50, landing it in the
discrepancy band by the "a threshold value belongs to the stricter band" rule.
Had the lower threshold been 0.51 it would have passed as `VERIFIED`.

### 6.3.4 Cryptography carried what OCR could not

The clean separation of concerns is visible in the data. The QR decoded 12/12;
OCR read 28 of 48 comparable fields. Had the design depended on OCR, the
system would have been unusable on phone photographs. Because it depends on the
signature and uses OCR only as a cross-check, it is usable *and* it still
catches a document edited after issue — which a signature-only system would
not.

The honest corollary, stated in §5.3.3: this works **only** while a QR decodes.
A photograph with its code damaged or cropped away falls back to an OCR path
that is measurably weak, and that fallback has never been tested on a real
photograph.

### 6.3.5 Explainability turned out to be a design constraint, not a feature

Three findings support this.

First, **the result page's content is derived from the stored evidence rather
than sent alongside it** — the "which evidence carried this verdict" sentence
is computed from the checks, so it cannot contradict the verdict. This was a
deliberate response to the risk of a presentation layer drifting from the
engine.

Second, **the `state` / `status` split was forced by the user interface.** The
engine originally reported both "differs but unsure" and "could not read" as
`uncertain`, and the result page had no way to distinguish them without
re-deriving the comparison itself, including re-implementing normalization in
TypeScript. Separating what the document *said* from what the check *made of
it* resolved that at the source.

Third, **the decision to show no overall percentage** is vindicated by the
data. A `sample6` scored as a percentage would read something like "86 % of
fields match" — which is both true and dangerously misleading, since the one
field that does not match is the CGPA.

### 6.3.6 Methodology: the negative result was the most instructive one

The reverted PP-OCRv5 round (§5.3.5) measured 48/48 fields on synthetically
degraded renders and then performed *worse* than the code it replaced on real
photographs. The generalisable lesson — that an evaluation set invented to be
convenient will reward optimisation for its own artefacts — is worth more to
the report than a successful optimisation would have been, and it changed the
project's practice: `samples/photos` is now the only accepted evaluation set.

### 6.3.7 Where the design shows strain

- **One template.** `nbit.yaml` describes this project's own certificate. The
  template mechanism generalises; the template library does not exist.
- **The engine's `_decide()` is a 10-branch sequence.** It is correct, heavily
  tested and readable, but it is the function most likely to become unwieldy as
  rules accumulate.
- **Dead configuration is a smell.** Three settings
  (`NAME_MATCH_THRESHOLD`, `NAME_CONFLICT_THRESHOLD`, `SHARE_LINK_TTL_HOURS`)
  and one dependency (`rapidfuzz`) exist for features that were not built.
- **No frontend tests at all**, against a specification that called for
  Playwright flows. The generated API types prevent contract drift but test no
  behaviour.

## 6.4 Advantages

1. **Cryptographic rather than statistical.** A verdict rests on an Ed25519
   signature the institution produced, not on a model's opinion about a JPEG.
2. **Works on the document a verifier actually holds.** A phone photograph of a
   printed certificate verifies in under two seconds — the case that
   repository-based systems do not address.
3. **Robust where it needs to be.** 12/12 QR decode on real photographs, via a
   measured two-reader, three-scale ladder.
4. **A valid signature cannot mask an altered page.** The field comparison runs
   *before* a valid QR is accepted, so a document edited after issue is caught.
5. **Zero false mismatches on genuine documents**, measured.
6. **Every result is explained.** Six named checks with human-readable detail
   sentences, a field-by-field comparison, and an explicit statement of which
   evidence carried the verdict.
7. **Unreadable fields are reported, not hidden.** "Couldn't read on the
   document: Roll number, Certificate number" — with the registry's values
   beside them.
8. **No accusatory output is possible.** Four statuses, none of which means
   "fake"; the strongest institutional statement is "we have no such record",
   and it requires a written reason. Enforced by tests.
9. **Deliberate separation of authority.** The platform operator can read
   everything and adjudicate nothing.
10. **A tamper-evident audit trail.** Append-only by database trigger, not by
    convention.
11. **Privacy by construction.** The QR carries no personal data; uploads
    expire in 7 days; the document's text is never stored; failed logins keep
    only an email domain.
12. **Fast where it can be.** 0.09 s for the original PDF, via the text-layer
    path.
13. **Genuinely testable.** 373 passing test cases, with the business rules in
    pure functions and the evidence that the abstractions work (an entire
    second OCR engine was added by touching one file).
14. **Cheap to run.** No per-verification cost of any kind.
15. **Registry self-correction.** "Confirm & add" turns a verification failure
    into a permanent registry improvement, through the same code path as a
    normal create.
16. **Portable.** One `docker compose up --build` on any Docker host.
17. **Extensible at the right seams.** A new OCR engine is one class; a new
    certificate layout is one YAML file.
18. **Decisions are recorded with their reasoning**, including the failures —
    which is why this document could be written from the code.

## 6.5 Limitations

Stated without hedging; each is evidenced earlier in the document.

1. **OCR of real phone photographs is weak.** Global Otsu thresholding floods
   shadowed regions; no illumination correction; no text-height rescaling. The
   certificate and roll numbers are unread on almost every photograph and 4 of
   12 match no template. (§5.3.3)
2. **The system depends on the QR decoding.** A damaged or cropped code falls
   back to that weak OCR path, and **that path has never been tested on a real
   photograph** — only on synthetic renders. (§5.1.7)
3. **The white-box PDF overlay is undetected on the PDF path.** A filled
   rectangle over a PDF's text shows a human one value while the text layer
   reports the original, and the document reads as `VERIFIED`. Known,
   deliberately unfixed, pinned by two tests. (§5.3.2)
4. **Fuzzy name matching is not implemented.** "Aaravv Sharma" conflicts with
   "Aarav Sharma". `rapidfuzz` is installed but never imported.
5. **No shareable verification link.** A verifier cannot pass a result to
   someone without an account.
6. **No credential-holder role.** The graduate has no account, cannot see
   verifications of their own certificate, and cannot initiate sharing.
7. **Trust is centralised.** Anyone able to register an institution and its
   public key can issue signatures that verify.
8. **No key rotation.** The institution code and public key are immutable by
   design, so a compromised private key cannot be rotated for
   already-issued certificates. Keys are unencrypted PEM files with no HSM.
9. **Refresh tokens cannot be revoked** before their 7-day expiry; logout is
   browser-side only. Tokens live in `localStorage`.
10. **No rate limiting** anywhere, including on login.
11. **One layout template.** Each real institution would need its own.
12. **English only.** The Hindi traineddata is installed but no code requests
    it.
13. **No frontend tests**, and no Playwright flows despite the specification.
14. **Not deployed, and not deployment-ready.** No hosting, no CI/CD, no TLS;
    the `web` service is a Vite development server, and `api` runs with
    `--reload`. (§5.4.7)
15. **Synchronous PDF issuance** means a very large CSV import blocks its
    request.
16. **Nothing schedules upload pruning.**
17. **No load testing.** All latency figures are single-operation
    measurements.
18. **Junk input is pathologically slow** — 54 s of Tesseract on a
    random-pixel image, with no gate in front of OCR.
19. **The evaluation set is small**: 12 photographs of 2 certificates, taken by
    one team. It is real, which is what matters most, but it is not diverse in
    camera, lighting, layout or language.
20. **All data is synthetic.** The system has never been tested against a real
    institutional registry, real certificate layouts, or real fraudulent
    documents.

---

# CHAPTER 7: CONCLUSION AND FUTURE ENHANCEMENTS

## 7.1 Conclusion

This project set out to answer a narrow, practical question: given an academic
certificate presented by an unknown party, can a system determine whether the
named institution actually issued it — and explain its reasoning well enough
that a human can act on the answer? The implemented prototype answers yes, and
the way it gets there is the contribution.

The architecture rests on a single decision: put the institution's Ed25519
signature **on the document itself**, inside a QR code, and read that code
first — from the image exactly as uploaded, before any processing touches the
pixels. The measurement justifies it. On 12 real phone photographs of printed
certificates, the QR decoded 12 times out of 12 in 1–43 milliseconds, while the
OCR that reads the same page recovered only 28 of 48 comparable fields and
failed to match any layout at all on a third of the images. Had the design
depended on reading the printed text, it would not work. Because it depends on
cryptography and uses the text as a cross-check, it does.

The second decision is subtler and, on reflection, the more interesting one. A
valid signature proves what an institution *issued*; it proves nothing about
what is printed on the paper in a verifier's hand. The project encountered this
as a measured bug — a CGPA printed 9.99, read at 76 % confidence against a
registry value of 9.32, reported as `VERIFIED` because the QR was valid — and
the fix became the system's central algorithm. Fields are now compared in three
confidence bands, and `VERIFIED` requires that **nothing differs**: a
confidently-read difference is a `MISMATCH` even with a perfect signature, a
moderately-read difference blocks verification and asks for human review, and a
value nobody could read blocks nothing and is reported as unread rather than
silently omitted. Each compared field carries both what the check made of it
and what the document actually said, because those two things come apart
exactly where it matters most.

That rule has a measurable cost and a measurable benefit. Two of the twelve
photographs moved from `VERIFIED` to human review — both genuine certificates
whose OCR misread a value — and the honest reading of that is not a regression
but a correction: the previous behaviour was to verify a document the system
itself believed to be printed differently from the record. Against that cost,
**not one genuine document became a `MISMATCH`**. That zero is the most
important number the project produced, because the cost of wrongly flagging a
real degree falls on a real person.

Around this core the system implements what a working platform needs: three
separated roles with authorisation enforced at the route and scoped again at
the query; a registry with individual and all-or-nothing bulk entry; signed
PDF issuance whose stored hash is never invalidated because the file is never
regenerated; revocation that leaves the record and its signature exactly as
issued; an append-only audit log protected by a database trigger rather than by
convention; and a recorded, scoped conversation between a verifier and an
institution for the cases nothing automatic can settle — in which the platform
operator can read everything and adjudicate nothing, because deciding whether a
university issued a degree is not an authority this system should hold.

Two properties of the engineering are worth claiming. First, the rules are in
pure functions with no database, network or clock, which is why 373 test cases
can exercise every decision path, every confidence band and both band edges.
Second, the abstractions were tested by events rather than by assertion: an
entire second OCR engine was added during development by touching one file, and
then removed again when it proved worse on real photographs.

The project is equally clear about what it is not. The OCR path remains weak on
photographs and has never been tested on a real photograph lacking a readable
QR. A white rectangle drawn over a PDF's text defeats the fast text-layer path,
which is a known defect, deliberately unfixed because the alternative costs a
twentyfold slowdown on every upload, and pinned by two tests so it cannot
change silently. Fuzzy name matching and shareable links were specified and not
built. There is no credential-holder role, no key rotation, no rate limiting,
no frontend test, and no deployment. All data is synthetic, and the system has
never met a real registry or a real forgery.

What the work demonstrates, then, is not a finished product but a defensible
design: that credential verification should be grounded in the issuer's own
cryptographic attestation; that the attestation must be reconciled against the
artefact rather than trusted in place of it; that uncertainty deserves more than
two states; and that a verification system owes its user the evidence, not just
the verdict. The prototype shows each of those claims working, measured on real
documents, with its failures recorded as carefully as its successes.

## 7.2 Future enhancements

Each enhancement below names the code it would touch, and they are ordered by
the ratio of value to effort as the current codebase stands.

### 7.2.1 Immediate — completing what is already specified

**1. Fuzzy field matching (Tier 2 item 7, the declared next task).**
Replace the exact comparison for `student_name` and `programme` in
`engine._compare_field` with `rapidfuzz.fuzz.token_sort_ratio`, using the
thresholds that already exist in configuration: ≥ 90 is a match, < 75 a
conflict, in between uncertain. `rapidfuzz` is already installed and
`NAME_MATCH_THRESHOLD` / `NAME_CONFLICT_THRESHOLD` are already plumbed as far
as `Settings`. The work is to thread them into `Thresholds`, branch on
`_TEXT_FIELDS` in `_compare_field`, and replace
`test_a_name_must_match_exactly_for_now` with cases for each band. Roughly a
day, and it removes the project's most visible functional gap.

**2. Shareable time-limited verification links (Tier 2 item 10).**
`SHARE_LINK_TTL_HOURS` already exists; the data model for it is specified in
`CLAUDE.md` (`share_links`: token, certificate_id, created_by, expires_at) and
`api/v1/router.py` already carries the comment reserving the mount point. The
work is one model, one migration, one service, two endpoints
(`POST /share-links`, `GET /public/share/{token}`) and a public read-only
result page. The token must be 32+ random bytes, and the public page must show
the result without exposing the registry.

**3. Fix the `SyntaxWarning` in `services/admin.py:37`** by making the
replacement strings raw. A one-line change that removes noise from every test
run.

**4. Schedule `prune_uploads`.** RQ already runs `with_scheduler=True` in
`workers/worker.py`, so a daily scheduled job needs no new infrastructure.

### 7.2.2 Short term — closing the measured gaps

**5. Illumination-robust preprocessing, measured correctly this time.**
The specific lessons recorded from the reverted attempt are the starting point:
measure **text height** rather than image width when deciding to rescale;
flatten the watermark **before** lifting contrast; and replace the global Otsu
threshold with a local/adaptive one so a shadowed half-page is not flooded.
The binding constraint is methodological, not technical: **`samples/photos` is
the only acceptable evaluation set, and the set should first be expanded** —
more cameras, more lighting conditions, more certificate layouts, and crucially
some photographs whose QR is deliberately damaged or cropped away, since that
path is currently untested.

**6. Gate junk input before OCR.** Tesseract spends 54 seconds on a
random-pixel image. A cheap pre-check in `extract_from_image_array` — edge
density, connected-component statistics, or simply "no template-matching text
found in a fast low-resolution pass" — would bound the worst case.

**7. Test the OCR-only path on real photographs.** Produce a handful of
photographs with the QR obscured, add them to the evaluation set, and
characterise the fallback honestly. This is the single most important gap in
the current evidence base.

**8. Frontend tests.** Vitest plus React Testing Library for the components
carrying real logic — `DocumentMatch`, `ExtractedFieldsTable` and
`VerificationResult.pathUsed()` all transform engine output into user-facing
claims, and all are currently unverified. Then two or three Playwright flows as
the specification originally intended: login → verify by number → read the
result; upload → poll → result; escalate → institution answers.

**9. Re-measure the bundle.** The ~352 kB verify chunk was dominated by
`html5-qrcode`, which has been removed. The figure quoted in the project notes
is stale.

### 7.2.3 Medium term — capability

**10. A template library and a template editor.** The mechanism generalises
already; what is missing is templates. An administrator-facing tool that takes
a sample certificate, shows the OCR lines, and lets an operator pick anchors
interactively would make onboarding a new institution's layout a
non-engineering task.

**11. A credential-holder role.** The most significant missing actor. A
graduate should be able to see their own credentials and generate a share link,
which also supplies the consent mechanism that any real deployment needs for
data protection.

**12. Multi-page and multi-credential documents.** `extract_from_pdf` reads
only `doc[0]`. Transcripts and mark sheets are routinely multi-page.

**13. Hindi and other Indian-language OCR (Tier 3).** The `tesseract-ocr-hin`
traineddata is **already in the image**, so no rebuild is required. The work is
a `lang` parameter threaded from the template through
`OcrEngine.recognise(lang=...)`, a script-detection step, and Devanagari-aware
normalization — note that `normalize_id`'s `[^0-9A-Z]` strip and
`normalize_text`'s uppercasing are both Latin-centric and would need revisiting.

**14. W3C Verifiable Credential export (Tier 3).** The canonical nine-field
record is a clean mapping target. This would give the project the standards
interoperability it currently lacks (§2.3.2).

**15. Verifier API keys (Tier 3).** For background-verification agencies
integrating server-to-server rather than through the UI.

### 7.2.4 Longer term — hardening and trust

**16. Production deployment.** Work through the eleven-item checklist in
§5.4.7: real secrets, TLS, a built frontend rather than a dev server,
`uvicorn` without `--reload`, an `httpOnly` refresh cookie, rate limiting,
encrypted keys, scheduled pruning, backups with a tested restore, monitoring,
and a data-protection review.

**17. Key management and rotation.** The hardest open design problem, because
the institution code and public key are deliberately immutable. A credible
scheme needs key *versioning* — a `key_id` in the QR payload and a table of an
institution's historical keys — so that a compromised key can be retired
without invalidating correctly-issued certificates. This would be a breaking
change to the `AVA1` payload and should be designed as `AVA2`.

**18. Address the overlay defect properly.** Options, in increasing cost: OCR
only the *region* of each critical field rather than the whole page; compare
the text layer's glyph bounding boxes against drawn filled rectangles in the
content stream, which detects an overlay without OCR at all; or OCR every PDF
and accept the slowdown. The second option is the interesting one and is
tractable with PyMuPDF.

**19. Decentralise trust in the key registry.** The current single-registry
model means compromising the platform allows issuing verifiable signatures. A
federation model, a transparency log of institution-key registrations, or
publishing the key registry in an independently auditable form would all reduce
that exposure without adopting a blockchain.

**20. Horizontal scale and observability.** Workers already scale with
`--scale worker=N`; what is missing is the measurement to know when to. Queue
depth, job duration percentiles, OCR confidence distributions and
result-distribution drift are all worth instrumenting, and the last of these
would detect a degrading camera estate or a changed certificate layout before
users report it.

### 7.2.5 Table 7.1 — Enhancements mapped to the code

| # | Enhancement | Files affected | Effort | Value |
|---|---|---|---|---|
| 1 | Fuzzy name matching | `engine.py`, `upload_verification.py`, `test_engine_upload.py` | ~1 day | High |
| 2 | Shareable links | new model + migration + `services/share.py` + `api/v1/share.py` + a public page | ~3 days | High |
| 3 | Fix the `SyntaxWarning` | `services/admin.py` | minutes | Low |
| 4 | Schedule pruning | `workers/worker.py` | ~1 hour | Medium |
| 5 | Illumination-robust preprocessing | `ocr/preprocess.py` + an expanded `samples/photos` | ~1 week | High |
| 6 | Junk-input gate | `ocr/extract_text.py` | ~1 day | Medium |
| 7 | Test the OCR-only path | `samples/photos`, `test_upload_verification_e2e.py` | ~2 days | **High (evidence gap)** |
| 8 | Frontend tests | new `frontend/src/**/*.test.tsx`, Playwright config | ~1 week | High |
| 9 | Re-measure the bundle | — (measurement only) | minutes | Low |
| 10 | Template library + editor | `ocr/templates/`, `ocr/fields.py`, a new admin page | ~2 weeks | High |
| 11 | Credential-holder role | `models/user.py`, new endpoints, new pages | ~2 weeks | High |
| 12 | Multi-page documents | `ocr/extract_text.py`, `ocr/fields.py` | ~1 week | Medium |
| 13 | Hindi OCR | `ocr/engines.py`, `ocr/fields.py`, `normalize.py`, templates | ~1 week | Medium |
| 14 | W3C VC export | new `services/vc.py`, one endpoint | ~1 week | Medium |
| 15 | Verifier API keys | `models`, `core/deps.py`, new endpoints | ~4 days | Medium |
| 16 | Production deployment | `docker-compose.prod.yml`, `frontend/Dockerfile`, CI | ~1 week | **Required for use** |
| 17 | Key versioning and rotation | `services/qr.py` (AVA2), `signing.py`, `models/institution.py`, migration | ~2 weeks | High |
| 18 | Overlay detection without OCR | `ocr/extract_text.py` | ~1 week | **High (security)** |
| 19 | Decentralised key trust | architectural | research | High |
| 20 | Observability | `workers/`, `main.py`, new dashboards | ~1 week | Medium |

---

# CHAPTER 8: REFERENCES

Every item below corresponds to a dependency, standard or tool actually used in
this project. Access dates are given as 2026 where the documentation was
consulted during development. **No academic papers are cited, because none were
used in building the system**; §2.4.4 lists the search terms a literature
review should start from instead.

## 8.1 Standards and specifications

[1] S. Josefsson and I. Liusvaara, "Edwards-Curve Digital Signature Algorithm (EdDSA)," IETF RFC 8032, Jan. 2017. Available: https://www.rfc-editor.org/rfc/rfc8032

[2] National Institute of Standards and Technology, "Secure Hash Standard (SHS)," FIPS PUB 180-4, Aug. 2015. Available: https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf

[3] M. Jones, J. Bradley and N. Sakimura, "JSON Web Token (JWT)," IETF RFC 7519, May 2015. Available: https://www.rfc-editor.org/rfc/rfc7519

[4] S. Josefsson, "The Base16, Base32, and Base64 Data Encodings," IETF RFC 4648, Oct. 2006. Available: https://www.rfc-editor.org/rfc/rfc4648

[5] International Organization for Standardization, "Information technology — Automatic identification and data capture techniques — QR Code bar code symbology specification," ISO/IEC 18004:2015, 2015. Available: https://www.iso.org/standard/62021.html

[6] A. Biryukov, D. Dinu and D. Khovratovich, "Argon2: the memory-hard function for password hashing and other applications," Password Hashing Competition, 2015. Available: https://www.password-hashing.net/argon2-specs.pdf

[7] M. Nystrom and B. Kaliski, "PKCS #8: Private-Key Information Syntax Specification Version 1.2," IETF RFC 5208, May 2008. Available: https://www.rfc-editor.org/rfc/rfc5208

[8] D. Cooper et al., "Internet X.509 Public Key Infrastructure Certificate and CRL Profile," IETF RFC 5280, May 2008. (SubjectPublicKeyInfo structure.) Available: https://www.rfc-editor.org/rfc/rfc5280

[9] T. Bray, "The JavaScript Object Notation (JSON) Data Interchange Format," IETF RFC 8259, Dec. 2017. Available: https://www.rfc-editor.org/rfc/rfc8259

[10] A. Rundgren, B. Jordan and S. Erdtman, "JSON Canonicalization Scheme (JCS)," IETF RFC 8785, Jun. 2020. (Relevant to the canonical-record design; this project uses its own simpler sorted-key scheme.) Available: https://www.rfc-editor.org/rfc/rfc8785

[11] M. Sporny, D. Longley and D. Chadwick, "Verifiable Credentials Data Model v1.1," W3C Recommendation, Mar. 2022. (Listed as a Tier 3 goal; not implemented.) Available: https://www.w3.org/TR/vc-data-model/

[12] Fetch Standard / CORS, "Cross-Origin Resource Sharing," WHATWG Fetch Living Standard, 2026. Available: https://fetch.spec.whatwg.org/#http-cors-protocol

[13] World Wide Web Consortium, "Web Content Accessibility Guidelines (WCAG) 2.1," W3C Recommendation, Jun. 2018. Available: https://www.w3.org/TR/WCAG21/

## 8.2 Backend frameworks and libraries

[14] S. Ramírez, "FastAPI Documentation," version 0.115.6, 2026. Available: https://fastapi.tiangolo.com

[15] Pydantic Developers, "Pydantic Documentation," version 2.10.4, 2026. Available: https://docs.pydantic.dev

[16] Pydantic Developers, "Pydantic Settings Documentation," version 2.7.0, 2026. Available: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

[17] Encode, "Uvicorn: an ASGI web server for Python," version 0.34.0, 2026. Available: https://www.uvicorn.org

[18] Encode, "Starlette Documentation," 2026. Available: https://www.starlette.io

[19] M. Bayer, "SQLAlchemy 2.0 Documentation," version 2.0.36, 2026. Available: https://docs.sqlalchemy.org/en/20/

[20] M. Bayer, "Alembic Documentation," version 1.14.0, 2026. Available: https://alembic.sqlalchemy.org

[21] D. Varrazzo, "psycopg 3 Documentation," version 3.2.3, 2026. Available: https://www.psycopg.org/psycopg3/docs/

[22] PostgreSQL Global Development Group, "PostgreSQL 16 Documentation," 2026. Available: https://www.postgresql.org/docs/16/

[23] PostgreSQL Global Development Group, "pg_trgm — support for similarity of text using trigram matching," PostgreSQL 16 Documentation, 2026. Available: https://www.postgresql.org/docs/16/pgtrgm.html

[24] Redis Ltd., "Redis Documentation," version 7, 2026. Available: https://redis.io/docs/

[25] V. Driessen and RQ Contributors, "RQ: Simple job queues for Python," version 2.0.0, 2026. Available: https://python-rq.org

[26] Python Cryptographic Authority, "cryptography Documentation," version 44.0.0, 2026. Available: https://cryptography.io

[27] E. Collins and Passlib Contributors, "Passlib Documentation," version 1.7.4, 2026. Available: https://passlib.readthedocs.io

[28] Python Cryptographic Authority, "argon2-cffi Documentation," version 23.1.0, 2026. Available: https://argon2-cffi.readthedocs.io

[29] J. Lindsay and PyJWT Contributors, "PyJWT Documentation," version 2.10.1, 2026. Available: https://pyjwt.readthedocs.io

[30] L. Nussbaum and qrcode Contributors, "python-qrcode," version 8.0, 2026. Available: https://github.com/lincolnloop/python-qrcode

[31] L. Hudson and pyzbar Contributors, "pyzbar: Read one-dimensional barcodes and QR codes from Python," version 0.1.9, 2026. Available: https://github.com/NaturalHistoryMuseum/pyzbar

[32] ZXing-C++ Contributors, "zxing-cpp: C++ port of ZXing with Python bindings," version 2.3.0, 2026. Available: https://github.com/zxing-cpp/zxing-cpp

[33] Artifex Software, "PyMuPDF Documentation," version 1.25.1, 2026. Available: https://pymupdf.readthedocs.io

[34] ReportLab Ltd., "ReportLab PDF Library User Guide," version 4.2.5, 2026. Available: https://docs.reportlab.com

[35] R. Smith and Tesseract Contributors, "Tesseract OCR Documentation," version 5, 2026. Available: https://tesseract-ocr.github.io

[36] M. Lee and pytesseract Contributors, "pytesseract: Python-tesseract OCR tool," version 0.3.13, 2026. Available: https://github.com/madmaze/pytesseract

[37] OpenCV Team, "OpenCV 4.10 Documentation," 2026. Available: https://docs.opencv.org/4.10.0/

[38] C. Simpkins and PyYAML Contributors, "PyYAML Documentation," version 6.0.2, 2026. Available: https://pyyaml.org/wiki/PyYAMLDocumentation

[39] M. Bachmann and RapidFuzz Contributors, "RapidFuzz Documentation," version 3.11.0, 2026. (Installed for Tier 2 item 7; not yet used.) Available: https://rapidfuzz.github.io/RapidFuzz/

[40] H. Krekel et al., "pytest Documentation," version 8.3.4, 2026. Available: https://docs.pytest.org

[41] Encode, "HTTPX Documentation," version 0.28.1, 2026. Available: https://www.python-httpx.org

[42] Astral, "Ruff: An extremely fast Python linter and code formatter," version 0.8.4, 2026. Available: https://docs.astral.sh/ruff/

[43] Python Software Foundation, "Python 3.12 Documentation," 2026. Available: https://docs.python.org/3.12/

## 8.3 Frontend frameworks and libraries

[44] Meta Open Source, "React Documentation," version 18.3.1, 2026. Available: https://react.dev

[45] E. You and Vite Contributors, "Vite Documentation," version 6.0.7, 2026. Available: https://vite.dev

[46] Microsoft, "TypeScript Documentation," version 5.7.2, 2026. Available: https://www.typescriptlang.org/docs/

[47] Remix Software, "React Router Documentation," version 7.1.1, 2026. Available: https://reactrouter.com

[48] T. Dorfer (TanStack), "TanStack Query Documentation," version 5.62.11, 2026. Available: https://tanstack.com/query/latest

[49] M. Zabriskie and Axios Contributors, "Axios Documentation," version 1.7.9, 2026. Available: https://axios-http.com/docs/intro

[50] A. Wathan et al., "Tailwind CSS Documentation," version 3.4.17, 2026. Available: https://tailwindcss.com/docs

[51] WorkOS, "Radix UI Primitives Documentation," 2026. Available: https://www.radix-ui.com/primitives

[52] shadcn, "shadcn/ui Documentation," 2026. Available: https://ui.shadcn.com

[53] Lucide Contributors, "Lucide Icons," version 1.72.0, 2026. Available: https://lucide.dev

[54] D. Sherret and openapi-typescript Contributors, "openapi-typescript," version 7.5.0, 2026. Available: https://openapi-ts.dev

[55] PostCSS Contributors, "PostCSS Documentation," version 8.4.49, 2026. Available: https://postcss.org

[56] OpenJS Foundation, "Node.js 22 Documentation," 2026. Available: https://nodejs.org/docs/latest-v22/api/

## 8.4 Infrastructure and tooling

[57] Docker Inc., "Docker Compose Documentation," version 2, 2026. Available: https://docs.docker.com/compose/

[58] Docker Inc., "Dockerfile Reference," 2026. Available: https://docs.docker.com/reference/dockerfile/

[59] OpenAPI Initiative, "OpenAPI Specification v3.1.0," Feb. 2021. Available: https://spec.openapis.org/oas/v3.1.0

[60] Git Contributors, "gitattributes Documentation," 2026. Available: https://git-scm.com/docs/gitattributes

## 8.5 Context and problem statement

[61] Government of India, Ministry of Electronics and Information Technology, "Smart India Hackathon — Problem Statement SIH25029," 2025. (The problem statement this project addresses.)

[62] Government of India, Ministry of Electronics and Information Technology, "DigiLocker," 2026. Available: https://www.digilocker.gov.in

[63] University Grants Commission, Government of India, "National Academic Depository (NAD)," 2026. Available: https://nad.gov.in

[64] Learning Machine and MIT Media Lab, "Blockcerts: The Open Standard for Blockchain Credentials," 2026. Available: https://www.blockcerts.org

---

# CHAPTER 9: APPENDICES

## Appendix A — Canonical record and signing (full listing)

`backend/app/services/signing.py`, the cryptographic core. Reproduced in full
because the correctness of the entire system reduces to these functions.

```python
@dataclass(frozen=True)
class CertificateRecord:
    cert_number: str
    institution_code: str
    student_name: str
    roll_number: str
    programme: str
    year_of_passing: int
    cgpa: Decimal | float | str | None
    marks: Decimal | float | str | None
    issue_date: date


def canonical_dict(record: CertificateRecord) -> dict[str, str | int | None]:
    return {
        "cert_number": normalize_id(record.cert_number),
        "institution_code": normalize_id(record.institution_code),
        "student_name": normalize_text(record.student_name),
        "roll_number": normalize_id(record.roll_number),
        "programme": normalize_text(record.programme),
        "year_of_passing": normalize_year(record.year_of_passing),
        # Strings ("8.50"), not JSON floats, so the bytes never depend on float repr.
        "cgpa": format_decimal(record.cgpa),
        "marks": format_decimal(record.marks),
        "issue_date": format_date(record.issue_date),
    }


def canonical_bytes(record: CertificateRecord) -> bytes:
    return json.dumps(
        canonical_dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_record(private_key: Ed25519PrivateKey, record: CertificateRecord) -> str:
    return _b64url(private_key.sign(canonical_bytes(record)))


def verify_record(public_key_pem: str, record: CertificateRecord, signature: str) -> bool:
    """True only if `signature` is a valid signature of `record` by this key."""
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
        if not isinstance(public_key, Ed25519PublicKey):
            return False
        public_key.verify(_b64url_decode(signature), canonical_bytes(record))
        return True
    except (InvalidSignature, ValueError, binascii.Error, UnicodeEncodeError):
        return False
```

**Figure 4.19 — worked example of the canonical form.** For the seeded
certificate `NBIT2022CS0020`:

```json
{"cert_number":"NBIT2022CS0020","cgpa":"8.56","institution_code":"NBIT","issue_date":"2022-07-20","marks":null,"programme":"B.TECH COMPUTER SCIENCE AND ENGINEERING","roll_number":"18CS020","student_name":"NANDINI RAO","year_of_passing":2022}
```

Those exact bytes are signed. The QR payload is then:

```
AVA1|NBIT2022CS0020|NBIT|<86 base64url characters>
```

## Appendix B — The decision function (full listing)

`backend/app/services/verification/engine.py: _decide()`. The ordering of these
branches *is* the project's central contribution, so it is reproduced complete.

```python
def _decide(data: VerificationInput, checks: list[Check]) -> VerificationResult:
    """Decision rules from the project spec, first match wins.

    The one thing to understand here: **VERIFIED requires that nothing
    differs**. A valid signature proves the registry record was issued by the
    institution; it says nothing about what is printed on the paper in front
    of the verifier. So a field that disagrees blocks VERIFIED even when the
    recogniser was only moderately sure of it — confidently, that is a
    MISMATCH; less confidently, it is a MANUAL_REVIEW for a person to settle.
    A field nobody could read is not a disagreement and blocks nothing.
    """
    status = {c.name: c.status for c in checks}
    field_checks = [c for c in checks if c.name.startswith(f"{CHECK_FIELD_MATCH}.")]
    conflicting = [c for c in field_checks if c.status is CheckStatus.FAIL]
    differing = [c for c in field_checks if c.state is FieldState.DIFFERS]
    matched = [c for c in field_checks if c.state is FieldState.MATCHES]
    number_matched = any(c.name == f"{CHECK_FIELD_MATCH}.cert_number" for c in matched)
    unreadable = [c for c in checks if c.name == CHECK_FIELD_MATCH]

    if data.record is None:
        return VerificationResult.MANUAL_REVIEW
    if data.record.is_revoked:
        return VerificationResult.REVOKED
    if status[CHECK_QR_SIGNATURE] is CheckStatus.FAIL:
        return VerificationResult.MISMATCH
    if status[CHECK_RECORD_SIGNATURE] is CheckStatus.FAIL:
        return VerificationResult.MISMATCH
    if status[CHECK_FILE_HASH] is CheckStatus.PASS:
        return VerificationResult.VERIFIED
    if conflicting:
        return VerificationResult.MISMATCH
    if differing:
        return VerificationResult.MANUAL_REVIEW
    if status[CHECK_QR_SIGNATURE] is CheckStatus.PASS:
        return VerificationResult.VERIFIED
    if data.upload is not None:
        if number_matched and not unreadable:
            return VerificationResult.VERIFIED
        return VerificationResult.MANUAL_REVIEW
    if matched or not field_checks:
        return VerificationResult.VERIFIED
    return VerificationResult.MANUAL_REVIEW


def evaluate(data: VerificationInput) -> VerificationOutcome:
    """Run every applicable check and decide. The checks come back in a stable
    order so the result page always lists them the same way."""
    checks = [
        _registry_lookup(data),
        _revocation(data),
        _record_signature(data),
        _qr_signature(data),
        _file_hash(data),
        *_field_match(data),
    ]
    return VerificationOutcome(result=_decide(data, checks), checks=checks)
```

## Appendix C — The OCR field template

`backend/app/services/ocr/templates/nbit.yaml`, in full. This single file is
what makes a new certificate layout a configuration change rather than a code
change.

```yaml
name: nbit
description: >
  Prototype degree certificate issued by this platform (A4 landscape,
  label-above-value fields, signed QR bottom-right).

match:
  all:
    - "DEGREE CERTIFICATE"
  any:
    - "Institution code"
    - "CERTIFICATE NUMBER"
    - "This is to certify that"

fields:
  cert_number:
    anchor: "CERTIFICATE NUMBER"
    value: next_line
    normalize: id

  roll_number:
    anchor: "ROLL NUMBER"
    value: next_line
    normalize: id

  # By pattern, not by anchor: the line after "DATE OF ISSUE" is the QR's
  # "Scan to verify" caption once OCR reflows the page, and the ISO date is
  # the only YYYY-MM-DD on the certificate anyway.
  issue_date:
    pattern: "([0-9]{4}-[0-9]{2}-[0-9]{2})"
    normalize: date

  student_name:
    anchor: "This is to certify that"
    value: next_line
    normalize: text

  programme:
    anchor: "has successfully completed the programme"
    value: next_line
    normalize: text

  institution_code:
    pattern: "Institution code\\s+([A-Za-z0-9]+)"
    normalize: id

  year_of_passing:
    pattern: "Year of passing\\s+([0-9]{4})"
    normalize: year

  # The grade line renders as either "CGPA 8.72 / 10.00" or "Marks 72.50%", so
  # exactly one of these two matches a given certificate. `\s*` not `\s+`:
  # OCR routinely reads the label and value as one word, "CGPA8.72".
  cgpa:
    pattern: "CGPA\\s*([0-9]{1,2}(?:[.,][0-9]{1,2})?)"
    normalize: decimal

  marks:
    pattern: "Marks\\s*([0-9]{1,3}(?:[.,][0-9]{1,2})?)\\s*%"
    normalize: decimal
```

## Appendix D — Docker Compose configuration

```yaml
name: ava

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-ava}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ava}
      POSTGRES_DB: ${POSTGRES_DB:-ava}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-ava} -d ${POSTGRES_DB:-ava}"]
      interval: 5s
      timeout: 5s
      retries: 12

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redisdata:/data
    ports:
      - "${REDIS_PORT:-6379}:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 12

  api:
    build:
      context: ./backend
    restart: unless-stopped
    command: >
      uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-ava}:${POSTGRES_PASSWORD:-ava}@db:5432/${POSTGRES_DB:-ava}
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./keys:/keys
      - uploads:/data/uploads
    ports:
      - "${API_PORT:-8000}:8000"
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 10s
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build:
      context: ./backend
    restart: unless-stopped
    command: ["python", "-m", "app.workers.worker"]
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-ava}:${POSTGRES_PASSWORD:-ava}@db:5432/${POSTGRES_DB:-ava}
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./keys:/keys
      - uploads:/data/uploads
    healthcheck:
      test: ["CMD", "python", "-c", "import redis,os; redis.Redis.from_url(os.environ['REDIS_URL']).ping()"]
      interval: 15s
      timeout: 5s
      retries: 6
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  web:
    build:
      context: ./frontend
    restart: unless-stopped
    command: ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
    environment:
      API_PROXY_TARGET: ${API_PROXY_TARGET:-http://api:8000}
    volumes:
      - ./frontend:/app
      - web_node_modules:/app/node_modules
    ports:
      - "${WEB_PORT:-5173}:5173"
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:5173/"]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 15s
    depends_on:
      - api

volumes:
  pgdata:
  redisdata:
  uploads:
  web_node_modules:
```

## Appendix E — The backend container image

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libzbar0        -> pyzbar (QR decode)
# tesseract-ocr   -> pytesseract (OCR engine + English traineddata)
# tesseract-ocr-hin -> Hindi traineddata, for the Tier 3 Hindi OCR stretch goal
# libglib2.0-0    -> opencv-python-headless
# libgl1 is deliberately NOT installed: only the headless OpenCV build is used,
# which does not link libGL. It would be needed by opencv-contrib-python, which
# nothing may pull in.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libzbar0 \
        tesseract-ocr \
        tesseract-ocr-hin \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /data/uploads /keys

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Appendix F — Sample inputs

### F.1 Valid CSV for bulk import (`samples/certificates-nbit-valid.csv`)

```csv
cert_number,institution_code,student_name,roll_number,programme,year_of_passing,cgpa,marks,issue_date
NBIT2025CS0101,NBIT,Aditi Verma,21CS101,B.Tech Computer Science and Engineering,2025,8.64,,2025-07-25
NBIT2025CS0102,NBIT,Rahul Nair,21CS102,B.Tech Computer Science and Engineering,2025,7.92,,2025-07-25
NBIT2025EC0103,NBIT,Simran Gill,21EC103,B.Tech Electronics and Communication,2025,9.05,,2025-07-25
NBIT2025ME0104,NBIT,Farhan Ali,21ME104,B.Tech Mechanical Engineering,2025,6.88,,2025-07-25
NBIT2025MB0105,NBIT,Kavya Reddy,23MB105,MBA,2025,,79.40,2025-07-25
NBIT2025BC0106,NBIT,Manav Sethi,22BC106,BCA,2025,,84.10,2025-07-25
```

### F.2 Deliberately invalid CSV (`samples/certificates-nbit-with-errors.csv`)

Each row after the first exercises one validation rule; the expected per-row
error report is in §6.1.4.

```csv
cert_number,institution_code,student_name,roll_number,programme,year_of_passing,cgpa,marks,issue_date
NBIT2025CS0201,NBIT,Good Row One,21CS201,B.Tech Computer Science and Engineering,2025,8.10,,2025-07-25
NBIT2025CS0202,NBIT,Bad Grade,21CS202,B.Tech Computer Science and Engineering,2025,11.2,,2025-07-25
NBIT2025CS0203,NBIT,Bad Date,21CS203,B.Tech Computer Science and Engineering,2025,7.50,,25/07/2025
NBIT2025CS0204,OTHR,Wrong Institution,21CS204,B.Tech Computer Science and Engineering,2025,7.70,,2025-07-25
NBIT2025CS0201,NBIT,Duplicate Number,21CS205,B.Tech Computer Science and Engineering,2025,8.00,,2025-07-25
NBIT2024CS0001,NBIT,Already In Registry,21CS206,B.Tech Computer Science and Engineering,2024,8.00,,2024-07-20
NBIT2025CS0207,NBIT,No Grade,21CS207,B.Tech Computer Science and Engineering,2025,,,2025-07-25
```

### F.3 The evaluation set (`samples/photos/`)

Twelve photographs — `sample1`–`sample10` as JPEG, `sample11`–`sample12` as
PNG — of two printed certificates. The ground truth, from
`samples/photos/Actual_data.txt`:

```
certificate1: Nandini Rao, CGPA 8.56/10.00, NBIT2022CS0020, 18CS020, 2022-07-20,
Year of passing 2022, B.Tech Computer Science and Engineering,
Northbridge Institute of Technology(fictional)

certificate2: Yash Thakur, Marks 69.75%, NBIT2022BC0019, 18BC019, 2022-07-20,
Year of passing 2022, BCA, Northbridge Institute of Technology(fictional)
```

## Appendix G — Sample outputs

### G.1 A `VERIFIED` result through the signed QR (abridged)

```json
{
  "method": "upload",
  "result": "VERIFIED",
  "checks": [
    {"name": "registry_lookup",  "status": "pass",      "detail": "Certificate NBIT2022CS0020 is registered to NBIT."},
    {"name": "revocation",       "status": "pass",      "detail": "The certificate is not revoked."},
    {"name": "record_signature", "status": "pass",      "detail": "The stored record matches the signature issued by NBIT."},
    {"name": "qr_signature",     "status": "pass",      "detail": "The QR signature matches the registry record and the public key of NBIT."},
    {"name": "file_hash",        "status": "uncertain", "detail": "The uploaded file is not the original issued PDF. That is expected for a scan or a re-saved copy, so the printed details are compared instead."},
    {"name": "field_match.cert_number",  "status": "uncertain", "state": "not_read", "detail": "The certificate number could not be read from the document, so it was not checked against the registry's NBIT2022CS0020."},
    {"name": "field_match.student_name", "status": "pass", "state": "matches", "detail": "The student name matches the registry: NANDINI RAO."},
    {"name": "field_match.programme",    "status": "pass", "state": "matches", "detail": "The programme matches the registry: B.TECH COMPUTER SCIENCE AND ENGINEERING."},
    {"name": "field_match.year_of_passing", "status": "pass", "state": "matches", "detail": "The year of passing matches the registry: 2022."}
  ],
  "extracted_fields": {
    "text_source": "ocr", "template": "nbit", "ocr_engine": "tesseract",
    "qr_present": true, "qr_reader": "zxing", "qr_scale": 1,
    "mean_line_confidence": 0.9183
  }
}
```

### G.2 A "Possible discrepancy" result (`sample6`, abridged)

```json
{
  "result": "MANUAL_REVIEW",
  "checks": [
    {"name": "qr_signature", "status": "pass", "detail": "The QR signature matches the registry record and the public key of NBIT."},
    {"name": "field_match.cgpa", "status": "uncertain", "state": "differs",
     "detail": "The CGPA on the document reads '8.00', but the registry has '8.56'. At 70% confidence that is not certain enough to call a conflict, so it is a possible discrepancy for a person to look at."}
  ]
}
```

The result page renders this as the banner "Possible discrepancy", the
discrepancy box "CGPA — document shows 8, institution issued 8.56", and the
summary line "Document match: 3 of 6 fields match · 1 differ · 2 not read".

### G.3 A `MISMATCH` on an edited document (abridged)

```json
{
  "result": "MISMATCH",
  "checks": [
    {"name": "qr_signature", "status": "pass", "detail": "The QR signature matches the registry record and the public key of NBIT."},
    {"name": "field_match.cgpa", "status": "fail", "state": "differs",
     "detail": "The CGPA on the document is '9.99', but the registry has '9.32' (read with 100% confidence)."}
  ]
}
```

The QR verifies and the result is still `MISMATCH` — which is the behaviour the
whole three-band design exists to produce.

### G.4 Error envelope examples

```json
{"error": {"code": "invalid_credentials", "message": "Email or password is incorrect."}}

{"error": {"code": "qr_payload_invalid",
           "message": "This is not a certificate QR code: Unknown payload prefix 'HTTP'; expected AVA1."}}

{"error": {"code": "csv_invalid",
           "message": "5 row(s) have errors. Nothing was imported — fix them and upload again.",
           "rows": [{"row": 3, "field": "cgpa", "message": "Input should be less than or equal to 10"}]}}

{"error": {"code": "upload_unsupported_type",
           "message": "Only PDF, PNG or JPEG files can be verified. The file's contents are not any of those, whatever its name says."}}
```

## Appendix H — Demonstration credentials and seeded data

From `backend/app/scripts/seed.py`. **All data is synthetic.**

| Role | Email | Password |
|---|---|---|
| admin | `admin@ava.test` | `Admin@12345` |
| institution | `registrar@nbit.test` | `Inst@12345` |
| verifier | `verifier@ava.test` | `Verify@12345` |

Institution: **NBIT** — "Northbridge Institute of Technology (fictional)".

Twenty certificates are seeded across six programmes (B.Tech CSE, B.Tech ECE,
B.Tech Mechanical, MBA, M.Tech Data Science, BCA) and the years 2022–2024, with
numbers of the form `NBIT<year><programme><nnnn>` and roll numbers
`<yy><programme><nnn>`. Fourteen carry a CGPA, five carry marks, and one
(`Aditya Joshi`) carries both — which exercises the engine's rule that both
grade fields are compared when the registry holds both.

Two of the seeded certificates are the ones photographed for the evaluation
set: `NBIT2022CS0020` (Nandini Rao, CGPA 8.56) and `NBIT2022BC0019`
(Yash Thakur, 69.75 %).

## Appendix I — Screenshot placeholders

To be captured and inserted; captions are given in §A.4.

| Figure | Screen | Capture instructions |
|---|---|---|
| 6.2 | Login | Show the inline error after a wrong password |
| 6.3 | Admin dashboard | Sign in as `admin@ava.test`; capture all cards |
| 6.4 | Registry | As `registrar@nbit.test`, with `nandini` typed in the search box |
| 6.5 | Add certificate dialog | Show a per-field validation error (CGPA 11.2) |
| 6.6 | CSV import errors | Upload `samples/certificates-nbit-with-errors.csv` |
| 6.7 | Issued PDF | Open a downloaded PDF; show the watermark and QR |
| 6.8 | Verify screen | The "Verify document" tab with the dropzone |
| 6.9 | `VERIFIED` by hash | Upload a registry PDF unchanged |
| 6.10 | `VERIFIED` by QR | Upload `samples/photos/sample1.jpeg`; include the unread-field notice |
| 6.11 | `MISMATCH` | Upload an edited PDF; capture the discrepancy box |
| 6.12 | Possible discrepancy | Upload `samples/photos/sample6.jpeg` |
| 6.13 | `REVOKED` | Revoke a certificate, then upload its genuine PDF |
| 6.14 | Extracted fields table | Scroll to "What the document says"; show confidence badges |
| 6.15 | Institution's case view | As `registrar@nbit.test`, open a pending request |
| 6.16 | Confirm & add form | Click "Confirm & add to registry"; show the prefilled fields |
| 6.17 | Requests list | The institution inbox with one open case |
| 6.18 | Audit log | Filter by `certificate.`; include a failed-login row |
| 6.19 | Institutions | Capture the one-time generated password panel |
| 6.20 | Printed result | Use Print / Save as PDF on a result page |

## Appendix J — Team ownership

Recorded in `CLAUDE.md` for context on review responsibility.

| Member | Area |
|---|---|
| Nikhil Kataria | Backend core, authentication, database, Docker, deployment |
| Nikhil | Frontend, dashboards, result page |
| Mohit | OCR pipeline, preprocessing, field extraction, QR |
| Sarthak Sahni | Verification engine, matching, audit, test evaluation |

---

*End of document. Every claim above was taken from the repository as it stands;
items specified but not implemented are marked as such throughout, and the
measured figures are those recorded by the project's own evaluation runs.*
