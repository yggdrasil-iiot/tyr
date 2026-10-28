# SI11 — Review transfer across snapshot revisions (phase A rules specification)

Status: approved design, phase A (contracts, pure computation, checker, fixtures). No storage, no UI. This document is the single source for the implementer and the independent oracle writer. Every rule is decidable from document fields; where the endpoint closure is needed, it is the closure defined in `docs/P4-F-CLOSURE.md` §1–§3 and §7 (the definition `endpoint-assessment` is already checked against), restated here only as far as its output fields are used.

Vocabulary: **S1** old snapshot, **S2** new snapshot, **P1/P2** their profiles, **B1/B2** their bundles. "Document" = a Tyr editor 2.0.0 document (`review-decision`, `endpoint-assessment`, `conversion-plan`) pinned to S1. "Item" = a native node, reference edge, claim or unresolved item inside a snapshot. JCS = RFC 8785 serialization; `fp(x)` = lowercase hex SHA-256 of the UTF-8 JCS bytes of object `x`.

---

## 0. Preconditions (refusals, not verdicts)

1. S1 with B1/P1 and S2 with B2/P2 each pass the receive check (schema, digest, pins, internal references).
2. `S1.contractVersion == S2.contractVersion` (1.0.0 or 1.1.0). Fields that exist only in 1.1.0 (`access`, `state`, `stateKinds`) are treated as absent (`null`) in 1.0.0 on both sides.
3. All S1 documents pass the existing 2.0.0 checks against S1/P1: decisions form one valid chain, assessments match the recomputed closure, plans pin their assessment.
4. A source-continuity declaration exists (§5). Nothing in the Mimir contracts says S2 is a revision of S1's source; the reviewer says it.

---

## 1. Pure function

`transfer(S1, B1, P1, S2, B2, P2, D1, A1, C1, declaration) → (body, carriedDecisions)`

Inputs
- `D1`: S1 review-decisions in chain order (first has `previousDecisionDigest: null`).
- `A1`: S1 endpoint-assessments. `C1`: S1 conversion-plans.
- `declaration`: the reviewer-authored part of the `review-transfer` body: `sourceContinuity`, `mappings[]`, `retired[]`, `workspace` (required when `C1` is non-empty).

Outputs
- `body`: the complete `review-transfer` body (§5). Everything in it except the declaration fields is computed, so the checker can recompute and compare.
- `carriedDecisions`: new `review-decision` 2.0.0 documents on S2 (§4.6), one per verdict `carried`.

Determinism: output is independent of the order of `nativeNodes`, `referenceEdges`, `claims`, `unresolved`, `A1`, `C1` and of snapshot-local id values. `transfer(S1…S1…)` with an empty declaration yields every verdict `carried`/`reusable` with no reasons.

---

## 2. Identity

### 2.1 Keys (within one snapshot)

- `nodeKey(n) = [namespace, nativeId]`.
- `edgeBase(e) = [nodeKey(owner node), owner.field, relation]`.
- `claimBase(c) = [nodeKey(subject node), subject.field]`.
- `issueKey(u)`: if `nodeId` present → `[code, "node", nodeKey(node), field|null]`; else if `edgeId` present → `[code, "edge", edgeKey(edge), field|null]` where `edgeKey` is `edgeBase` extended by `targetText` iff the base is not unique in that snapshot; else (locator only) → **no key**.
- `nodeId`, `edgeId`, `claimId`, `issueId`, `stateClaimId`, `locator`, `payload`, `envelope` are never identity.

### 2.2 Substitution from mappings

`σ(k)` = `mappings[i].to` if some mapping has `from == k`, else `k`. `σ` is applied to every node key that occurs in an S1 key or fingerprint before comparison with S2. Mappings are node-level only.

### 2.3 Correspondence of an S1 item (outcome ∈ `same | changed | absent | ambiguous`)

Node `n`:
- `N1` = S1 nodes with `σ(nodeKey) == σ(nodeKey(n))`; `N2` = S2 nodes with `nodeKey == σ(nodeKey(n))`.
- `|N1| > 1` or `|N2| > 1` → `ambiguous`. `|N2| == 0` → `absent`. Else matched to the single S2 node.

Edge `e` (owner node must be matched; otherwise the edge takes the owner's `absent`/`ambiguous` outcome):
- `B1` = S1 edges with `edgeBase == edgeBase(e)`; `B2` = S2 edges with `edgeBase == σ(edgeBase(e))`.
- If `|B1| == 1` and `|B2| == 1` → matched. If `|B1| == 1` and `|B2| == 0` → `absent`.
- Otherwise refine: `T1` = members of `B1` with `targetText == e.targetText`; `T2` likewise in `B2`. `|T1| == 1 && |T2| == 1` → matched; `|T1| == 1 && |T2| == 0` → `absent`; else `ambiguous`.

Claim `c`: identical procedure with `claimBase` and refinement by `evidenceBasis`.

Issue `u`: no key → `unkeyed` (reported as outcome `absent` with reason `target-unkeyed`). With key: `U1`/`U2` by equal key (after `σ`); `|U1| == 1 && |U2| == 1` → matched; `|U2| == 0` → `absent`; else `ambiguous`.

Matched items are `same` if the item fingerprint (§3.1) is equal on both sides, else `changed`.

Reporting only: for every S1 node with outcome `absent`, `candidates` = S2 nodes that are matched by no S1 node and whose `nodeContent` fingerprint equals the S1 node's. Nothing is selected from candidates.

### 2.4 Mappings and retirements

- A mapping overrides key matching for its `from` node; the S2 node that carries the unmapped key, if any, stays unmatched (and may appear as a candidate elsewhere).
- `retired[]` acknowledges that a key is absent in S2; it does not change any verdict (the documents on it remain `orphaned`).

---

## 3. Fingerprints

All objects below use S2-side vocabulary: every node key is written after `σ`; every S2 object is written as-is. Lists marked *sorted* are sorted by the JCS string of their elements. Excluded everywhere: `nodeId`/`edgeId`/`claimId`/`issueId`, `stateClaimId`, `locator`, `locators`, `payload`, `nativePath`, `envelope`, `digest`.

```
nodeContent(n)  = { kind, state|null, stateKinds(sorted)|null, outputs: sorted [{name, value}] }
edgeContent(e)  = { field: owner.field, relation, access|null, targetText, resolution, basis,
                    target: nodeKey(targetNodeId)|null, candidates: sorted nodeKeys|null }
claimContent(c) = { field: subject.field, value, evidenceBasis, status, rule: {ruleId, version}|null,
                    dependsOn: { claims: sorted claimKeys, edges: sorted edgeKeys } }
issueContent(u) = { code, field|null, reason, anchor: ["node", nodeKey] | ["edge", edgeKey],
                    affected: sorted nodeKeys }
```
`claimKey`/`edgeKey` inside `claimContent` are the keys of §2.1 as actually used (extended or not) in that snapshot. If any referenced dependency item is `ambiguous`/unkeyed, the fingerprint is undefined and the enclosing document gets `scope-item-ambiguous`.

### 3.1 Item fingerprints (for `same`/`changed`)
`fp(nodeContent)`, `fp(edgeContent)`, `fp(claimContent)`, `fp(issueContent)`.

### 3.2 Keep-scope fingerprints (per decision kind)

- **Claim decision** — `fp({ claim: claimContent(c), deps: { claims: sorted claimContent of every claim reachable through dependsOn.claimIds (transitively, visited-set), edges: sorted edgeContent of every edge named by dependsOn.edgeIds of c or of any reachable claim } })`.
- **Edge decision** — `fp(edgeContent(e))` (owner key is in the edge key; target key is in the content).
- **Node decision, `declared-by-reviewer`** — `oneHop(n) = { node: nodeContent(n), claims: sorted claimContent of claims with subject n, edges: sorted edgeContent of edges owned by n, issues: sorted issueContent of issues with nodeId == n or edgeId owned by n }`; fingerprint `fp(oneHop(n))`.
- **Node decision, `verified-by-virtual-case`** — `fp({ hop: oneHop(n), closure: closureView(n) })` with
  ```
  closureView(n) = { members: sorted [ [nodeKey(m), fp(oneHop(m))] for m in closure.nodeIds ],
                     edges: sorted edgeContent for closure.edgeIds,
                     completeness,
                     reasons: sorted [ {code, ref} ] with ref translated: node → nodeKey, edge → edgeKey,
                              issue → issueKey, evaluation-cycle → sorted nodeKeys,
                     captureScope,
                     stateful: sorted nodeKeys, stateUnknown: sorted nodeKeys (1.1.0, else []),
                     events: sorted edgeKeys (1.1.0, else []),
                     writes: sorted [{edge: edgeKey, targetText, resolution, target: nodeKey|null}] (1.1.0, else []) }
  ```
  computed on the snapshot's own profile depth (`P1.limits.maxReferenceDepth` for S1, `P2…` for S2). `structuralCycles` and `outsideUnresolved` are excluded.
- **Issue decision** — `fp({ issue: issueContent(u), anchor: nodeContent(anchor node) | edgeContent(anchor edge) })`.

### 3.3 Globals
- `profileChanged = P1.digest != P2.digest`.
- `contextChanged = fp(sorted S1.body.context) != fp(sorted S2.body.context)`.
- `captureChanged = S1.body.coverage.capture != S2.body.coverage.capture`.
- `workspaceChanged` (plans only) = plan `body.workspace != declaration.workspace`.

---

## 4. Verdicts

### 4.1 Reason codes (closed list)

| code | ref | applies to |
|---|---|---|
| `target-absent` | S1 id of the target | target outcome `absent` |
| `target-ambiguous` | S1 id of the target | target outcome `ambiguous` |
| `target-unkeyed` | S1 issue id | issue with locator-only anchor |
| `scope-item-absent` | S1 id of the scope item | a keep-scope item (dependency, one-hop member, closure member, plan mapping node) is `absent` |
| `scope-item-ambiguous` | S1 id of the scope item | such an item is `ambiguous` or unkeyed |
| `evidence-changed` | S1 id of the item whose §3.1 fingerprint differs (target or scope item) | matched items, one reason per changed item |
| `closure-changed` | S1 endpoint node id | `closureView` differs after removing `members` (membership, edges, completeness, reasons, capture, state/event/write lists) |
| `profile-changed` | `profile` | all documents when `profileChanged` |
| `context-changed` | `context` | all documents when `contextChanged` |
| `capture-changed` | `capture` | assessments and plans when `captureChanged` |
| `decision-not-carried` | S1 decision id | assessment/plan `decisionRefs` entry whose decision is superseded or whose verdict ≠ `carried` |
| `assessment-not-reusable` | S1 assessment id | plan whose assessment verdict ≠ `reusable` |
| `workspace-changed` | `workspace` | plan when `workspaceChanged` |

`reasons` lists **every** applicable code, sorted by `(code, ref)`. Fingerprint comparison is skipped only when the target itself is `absent`/`ambiguous`/unkeyed; scope items are still classified for absence/ambiguity. A `carried`/`reusable` verdict has `reasons: []`.

### 4.2 Superseded decisions

In the S1 chain, decision `d` is **superseded** iff a later decision in the same chain has the same `target.type` and `target.id`. The last decision per target is its **head**. Only heads receive verdicts; superseded decisions are listed in `superseded[]` and are never carried, even if their head is `re-review`.

### 4.3 Decision verdict (heads only)

Precedence: `orphaned` > `needs-mapping` > `re-review` > `carried`.
- `orphaned` iff `target-absent` or `target-unkeyed`.
- else `needs-mapping` iff `target-ambiguous` or any `scope-item-ambiguous`.
- else `re-review` iff any of `scope-item-absent`, `evidence-changed`, `closure-changed`, `profile-changed`, `context-changed`.
- else `carried`.

Scope per `evidenceBasis`/target type is §3.2. For a `verified-by-virtual-case` node decision, the S2 closure is recomputed from the matched S2 node under `P2`.

### 4.4 Assessment verdict

Endpoint node `x = body.endpoint.nodeId`; scope = closure members of the S1 closure (`body.closure.nodeIds`, `edgeIds`) plus the recomputed S2 closure from `σ`-matched `x` under `P2`.
- `orphaned` iff endpoint outcome `absent`.
- else `needs-mapping` iff endpoint `ambiguous` or any closure member (either side) `ambiguous`/unkeyed.
- else `stale` iff any of: `profile-changed`, `context-changed`, `capture-changed`, `closure-changed`, `scope-item-absent`, `evidence-changed` (any member's `oneHop` or edge content), `decision-not-carried`.
- else `reusable`: an S2 assessment with the same `axes`, the closure translated to S2 ids, and `decisionRefs` replaced by the carried copies would pass the existing checks.

### 4.5 Plan verdict

- `orphaned` iff its assessment is `orphaned`.
- else `needs-mapping` iff assessment `needs-mapping` or any `mappings[].nativeNodeId` outcome `ambiguous`.
- else `stale` iff any of: `assessment-not-reusable`, `workspace-changed`, `profile-changed`, `context-changed`, `capture-changed`, `scope-item-absent`/`evidence-changed` for any `mappings[].nativeNodeId` (fingerprint `oneHop`), `decision-not-carried` for its own `decisionRefs`.
- else `reusable`.

### 4.6 Carried copies

For each head with verdict `carried`, in S1 chain order, a new `review-decision` 2.0.0:
- `id` = `<S1 id>.carried.<first 12 hex of S2.digest>`; `version` = `"1.0.0"`.
- `body.snapshotRef` = S2 pin; `body.target.id` = matched S2 id (same `type`).
- `body.previousDecisionDigest` = digest of the preceding carried copy, `null` for the first. The carried copies are the head of the S2 chain; any later S2 decisions chain after them.
- `body.evidenceRefs` = original list followed by exactly one string `carried-from:review-decision:<S1 id>@<S1 digest>`.
- Every other body field (`decision`, `proposedCorrection`, `evidenceBasis`, `virtualCase`, `reviewer`, `reason`, `decidedAt`) byte-equal to the S1 decision. `digest` recomputed.

### 4.7 Verdict record

```
{ document: {kind, id, version, digest},
  verdict: "carried"|"re-review"|"needs-mapping"|"orphaned" | "reusable"|"stale"|"needs-mapping"|"orphaned",
  target: { type, fromId, toId|null },          // decisions: the target; assessments: endpoint; plans: assessmentRef id
  reasons: sorted [ {code, ref} ],
  candidates: sorted [S2 ids] }                  // only when the target node is absent; else []
```

---

## 5. `review-transfer` (editor contract 2.1.0)

Directory `editor-contracts/2.1.0/` with its own `common.schema.json` (2.0.0 `$defs` plus `bundleRef`, `nodeKey`, `transferRef`) and `review-transfer.schema.json`. 2.0.0 files stay byte-identical. Digest: SHA-256 over JCS of the document without top-level `digest` and `envelope`. All objects `additionalProperties: false`.

| field | type | req | note |
|---|---|---|---|
| `kind` | const `review-transfer` | ✓ | |
| `contractVersion` | const `2.1.0` | ✓ | |
| `id`, `version` | id, version | ✓ | |
| `body.identityRule` | const `si11-1` | ✓ | this specification |
| `body.snapshotContractVersion` | enum `1.0.0`,`1.1.0` | ✓ | shared by S1/S2 |
| `body.from` / `body.to` | `{snapshot: snapshotRef, bundle: bundleRef, profile: profileRef, artifactPins: [artifactPin]}` | ✓ | `artifactPins` = `inputManifest` copied; provenance only |
| `body.sourceContinuity` | `{evidenceBasis: const declared-by-reviewer, reviewer: text, reason: text, evidenceRefs: [text], declaredAt: timestamp}` | ✓ | |
| `body.workspace` | `{revision: int≥0, sha256}` or `null` | ✓ | non-null whenever any plan is listed |
| `body.mappings` | `[{from: nodeKey, to: nodeKey, evidenceBasis: const declared-by-reviewer, reviewer, reason, evidenceRefs, declaredAt}]` | ✓ | may be empty |
| `body.retired` | `[{key: nodeKey, reviewer, reason, declaredAt}]` | ✓ | may be empty |
| `body.globals` | `{profileChanged, contextChanged, captureChanged: boolean}` | ✓ | computed |
| `body.correspondence` | `[{type: node|edge|claim|issue, fromId, toId|null, outcome: same|changed|absent|ambiguous, candidates: [id]}]` | ✓ | one entry per S1 item, sorted by (type, fromId) |
| `body.fromDecisionChainHead` | decisionRef or `null` | ✓ | last S1 decision |
| `body.superseded` | `[{decision: decisionRef, supersededBy: decisionRef}]` | ✓ | |
| `body.verdicts` | `[verdict record]` | ✓ | sorted by (kind, id) |
| `body.carried` | `[{from: decisionRef, to: decisionRef}]` | ✓ | S1 chain order |
| `digest` | sha256 | ✓ | |
| `envelope` | `{createdAt?, note?}` | | outside digest |

`nodeKey` = `{namespace: id, nativeId: string}`; `bundleRef` like `snapshotRef` with kind `source-bundle`.

---

## 6. Checker (`check_transfer(transfer, S1,B1,P1, S2,B2,P2, D1, A1, C1, D2, carriedDecisions)`)

Violation codes, in check order:

| code | condition |
|---|---|
| `transfer.contract-version-mixed` | S1 and S2 contract versions differ |
| `transfer.snapshot-mismatch` | `from.snapshot`/`to.snapshot` (or bundle/profile) pins do not equal the given documents |
| `transfer.artifact-pins-mismatch` | `artifactPins` ≠ the snapshot's `inputManifest` |
| `transfer.continuity-missing` | `sourceContinuity` absent or its `evidenceBasis` not `declared-by-reviewer` |
| `transfer.mapping-evidence-not-owned` | a mapping with another `evidenceBasis` |
| `transfer.mapping-source-missing` | `from` key not in S1 |
| `transfer.mapping-target-missing` | `to` key not in S2 |
| `transfer.mapping-target-ambiguous` | `to` key held by more than one S2 node |
| `transfer.mapping-conflict` | two mappings share `from`, two `from` share one `to`, or a `to` is the key of another S1 node that no mapping moves |
| `transfer.retired-key-present` | a retired key exists in S2 |
| `transfer.workspace-missing` | plans listed and `workspace` null |
| `transfer.decision-chain-invalid` | two D1 decisions share an `id`, D1 fails the 2.0.0 chain check against S1, or `fromDecisionChainHead` ≠ last of D1 |
| `transfer.input-document-invalid` | an A1/C1 document fails its 2.0.0 check against S1/P1 |
| `transfer.globals-mismatch` / `transfer.correspondence-mismatch` / `transfer.superseded-mismatch` / `transfer.verdict-mismatch` | recomputation per §2–§4 differs from the recorded value (ref = first differing entry) |
| `transfer.carried-source-missing` | `carried[].from` not in D1 |
| `transfer.carried-source-superseded` | `carried[].from` is superseded |
| `transfer.carried-verdict-not-carried` | `carried[].from` has a verdict other than `carried`, or a `carried` verdict has no entry |
| `transfer.carried-copy-missing` | `carried[].to` is not among `carriedDecisions` / not at the head of D2 |
| `transfer.carried-copy-order` | copies are not the first entries of D2 in S1 chain order |
| `transfer.carried-copy-differs` | a copy violates §4.6 (any field, target mapping, or chain link) |
| `transfer.carried-evidence-ref-missing` | the appended `carried-from:…` string is absent or not last |
| `digest.mismatch` | transfer digest (existing code reused) |

All existing receive and editor checks remain in force; in particular a decision pinned to S1 inside D2 is already `pin.snapshot-mismatch`.

---

## 7. Fixtures (`fixtures/solution-intake/revision-1.1.0/`)

S1 for pairs 1–7 and 10 = `mimir-1.1.0/valid/pio-like` with the editor set `editor-2.0.0/valid` (decision-1 confirm claim `c.temp-scale`; decision-2 needs-evidence issue `u.count-source`; decision-3 confirm node `n.line1-temp` by virtual case; assessment/plan line1-temp candidate; assessment/plan line1-count blocked). Every S2: snapshot `version` `2.0.0`, **all snapshot-local ids renumbered** (e.g. `n2.…`), every locator line shifted, `config.txt` edited so its SHA-256 and the bundle digest change; profile and `context` unchanged unless stated. Each pair holds `s2/`, `transfer-input.json` (declaration), `oracle.json` (globals, correspondence, superseded, verdicts, carried) written by an independent reviewer from this document and the fixture files only.

| # | pair | change from S1 | expected |
|---|---|---|---|
| 1 | `reorder` | sections reordered; lists shuffled; nothing else | all `carried`/`reusable`, `reasons: []`; every correspondence `same` |
| 2 | `address-change` | `c.temp-address` value `D100`→`D101`; `e.temp-source.targetText` `plc1:D101` | decision-1, -2 carried; decision-3 re-review (`evidence-changed` n.line1-temp, e.temp-source; `closure-changed`); assessment-temp stale (+`decision-not-carried` decision-3); plan-temp stale; count assessment/plan reusable |
| 3 | `rename` | `nativeId` `Line1.Temp`→`Line1.Temperature`, `nativePath` accordingly; `e.avg-input.targetText` updated | input **a** (no mapping): decision-1, -3, assessment-temp, plan-temp orphaned, node candidate = the renamed node; others carried/reusable. Input **b** (mapping Temp→Temperature): all carried/reusable; `e.avg-input` correspondence `changed` |
| 4 | `deletion` | `[map Line1.Count]` removed (node, `e.count-source`, `u.count-source` gone); `e.reset-trigger` becomes `missing` with a new issue affecting `n.line1-reset.script`; `retired` declares Line1.Count | decision-2, assessment-count, plan-count orphaned; others carried/reusable |
| 5 | `twins` | `Line1.Temp` removed; `Line1.TempA`, `Line1.TempB` added with identical claims/edges; `e.avg-input` → TempA; a second `connection` node with `nativeId plc1` added | input **a**: decision-1, -3, assessment-temp, plan-temp orphaned with `candidates` = both twins; input **b** (mapping Temp→TempA): decision-1 carried; decision-3, assessment-temp, plan-temp needs-mapping (`scope-item-ambiguous` n.plc1); count documents reusable |
| 6 | `retarget-capture` | `e.temp-source` → `plc2:D100`, `missing`, new issue on `n.line1-temp`; bundle `captureScope` and snapshot `coverage.capture` → `declared-complete`, `artifactsSkipped` 0 | decision-1, -2 carried; decision-3 re-review; assessment-temp stale; assessment-count stale with only `capture-changed`; both plans stale |
| 7 | `profile-change` | profile: rule `synthetic-pio-like.scale` version `1.1.0`, `interpreter.implementationDigest` changed; `c.temp-engineering.rule.version` `1.1.0`; values unchanged | `profileChanged: true`; every decision re-review, every assessment and plan stale, each with `profile-changed` (plus `evidence-changed c.temp-engineering` nowhere, since no document scopes it) |
| 8 | `closure-c/state-access` | S1 = closure-c with an S1 editor set the fixture must include: d-c1 confirm node `n.c-read` (declared), d-c2 confirm node `n.c-read` (virtual case), d-c3 confirm claim `c.c-scale-state`, d-c4 confirm node `n.c-chain` (declared); assessments a-read (complete, refs d-c1,d-c2), a-chain (refs d-c4); plans p-read `candidate`, p-chain `blocked`; workspace given. S2: `n.c-scale` `state`→`stateful` (`stateKinds [accumulator]`, claim value `stateful`); `e.chain-total.access` `read`→`write` | d-c1 carried; d-c2 re-review (`evidence-changed n.c-scale`, `closure-changed`); d-c3 re-review; d-c4 re-review (`evidence-changed n.c-chain`); a-read, a-chain, p-read, p-chain stale |
| 9 | `closure-c/context` | same S1 set as 8; S2 identical to S1 except `context` `[]`→`[{site, b}]` (ids renumbered) | `contextChanged: true`; everything re-review/stale with `context-changed` only |
| 10 | `superseded-and-rejections` | S1 chain extended by decision-4 (`hold` on claim `c.temp-scale`, after decision-3); S2 = pair 1's S2. Transfer variants: valid; mapping to unknown key; mapping with `observed-in-artifact`; a carried copy whose `reason` differs; a carried copy of decision-1 | valid: decision-1 in `superseded[]`, decision-4 carried, decision-2, -3 carried; invalid variants → `transfer.mapping-target-missing`, `transfer.mapping-evidence-not-owned`, `transfer.carried-copy-differs`, `transfer.carried-source-superseded` |

Property tests beyond the oracle: S1→S1 all carried; shuffling S1/S2 lists and renumbering S2 ids leaves `body` unchanged; no mapping is ever inferred from `candidates`; S2 documents are never modified by the function.

---

## 8. Left to phase B

Sidecar persistence of transfers and carried copies, CAS, UI for mapping/re-review, composition of transfers across S1→S2→S3, tombstone reappearance linking, Mimir-side stable-id hints, computed evidence transfer (phase A only classifies), Bifrost submission effects.
