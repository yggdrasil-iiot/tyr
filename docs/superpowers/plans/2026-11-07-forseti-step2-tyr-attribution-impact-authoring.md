# Forseti Step 2: Tyr Authoring of Attribution and Impact Rules Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tyr authors the two forseti rule kinds of mapping contract 2.27.0 (`attribution-rule`, `impact-rule`) and the two binding profiles they reference (`occupancy-binding`, `incident-binding` 0.1.0, each the file of an evidence-artifact 1.1.0). Its PLC source form authors the 2.27.0 typed `String` sources a `plc-stamped` rule needs. Tyr pre-checks everything with the spec's refusal codes the way `command_binding.validate()` mirrors Bifrost. It publishes rules in a 2.27.0 proposal together with the mapping sets they read. Tyr carries two fixture workspaces (`occupancy-join` and `plc-stamped`, the shapes of Bifrost's step-1 fixtures); Bifrost's `gates mapping approve` re-proves their committed bundles byte for byte and approves them, both at the command line and in Tyr's CI. For every refusal code of the attribution, impact and binding-profile tables, Tyr proves that Tyr's pre-check and Bifrost's jar refuse the same mutated bundle with the same code. Tyr documents the step as `docs/P4-J-ATTRIBUTION-RULE.md`. A small forseti spec correction (tool level `WORKUNIT_11`; Bifrost's two extra pattern limits) goes in its own PR first. Tyr keeps no approval authority: it submits files to Bifrost's `mapping` gate.

**Architecture:** The architecture follows PR #19/#20 (`command-binding`, contract 2.25.0/2.26.0) and PR #17 (`equipment-hierarchy`, 2.23.0). Contract 2.27.0 is a byte copy of Bifrost's five schema files under `contracts/2.27.0/` (`test_p6.Receiver.test_shared_schema_copies` already proves the bytes against `../bifrost`). Two per-kind modules under `scripts/` (`attribution_rule.py`, `impact_rule.py`) hold the constants, the two profile parsers (strictness of Bifrost's `OccupancyBindingProfile` and `IncidentBindingProfile`, including the `identity.pattern` syntax subset with Java's quantifier bounds), and `validate(docs, read)`. `p3a_contracts.validate_package` runs `validate(docs, read)` after `command_binding.validate` and only when the hierarchy validated, so the same rules apply to the workspace check and to a package on its own. Two new workspace sections per kind (`attributionRules`, `impactRules`) are documents written as files, like `commandBindings`. Two sections for the authored profiles (`occupancyBindings`, `incidentBindings`) are records; `backend/binding_profiles.py` serializes their `profile` object to `data/occupancy-binding-<n>.json` / `data/incident-binding-<n>.json` and wraps it as evidence-artifact 1.1.0 with the spec's id prefix and media type, the way `hierarchy_evidence.py` wraps a plant register. The PLC source form (`frontend/app.js` `accessFields`, `frontend/mixed.js` `draftSource`) offers `String` for typed access and writes such a source at `schemaVersion` 2.27.0. The backend accepts it through `validate_schema`, `source_rules` and the legacy-workspace guard. `workspace_v2.build` sets the proposal to 2.27.0 when a rule or a 2.27.0 source is present. `publication.build` carries an attribution rule only when every mapping set its members read is selected, and an impact rule with its attribution rule. A screen (`backend/attribution_authoring.py`, `frontend/attribution-rule.js`, tab `attributionRules` in the connect stage) offers listing, plan and apply under revision CAS. No Bifrost or forseti code is imported. The seam tests run Bifrost's gates CLI (`mapping validate`, `identity keygen`, `mapping approve`) on the committed bundles and on a data-driven set of mutated bundles, one per refusal code.

**Tech Stack:** Python 3.13 (stdlib `unittest`, `jsonschema` 4.26.0 pinned in `requirements-contracts.txt`), the repository's own `validate_contracts` helpers (`load`, `save`, `hashed`, `safe`, `schema_validator`), SQLite workspace store, vanilla JS frontend. GitHub Actions (`.github/workflows/ci.yml` checks out Bifrost as `../bifrost`, builds `gates/target/bifrost-gates.jar` with Maven/JDK 17 and runs `python -B scripts/ci_run.py`). Tyr branch `feat/attribution-rule-authoring` off `main` (`da764c0`); forseti branch `docs/step2-decisions` off `main` (`4e6aea1` + #2). Files use LF (`vc.save` writes `newline="\n"`; `.gitattributes` is `* -text`, so bytes are kept as written). Product names in prose are ASCII (Mimir, Tyr); `scripts/check-ascii-names.sh` enforces it.

---

## Spec and rules applied

- Spec: `yggdrasil-iiot/forseti`, `docs/superpowers/specs/2026-11-05-forseti-design.md` (merged, as corrected by forseti #2; every "spec line N" below is a line of that file). Delivery plan row 2 (line 712): target Tyr, scope "authoring for both kinds and both profiles, fixtures, Bifrost acceptance test in CI", gate "Bifrost approves a bundle Tyr produced". Contracts (lines 115-226): attribution rule (119-154), impact rule (156-188), binding profiles (190-226). Decisions: 3 (lines 37-39, two kinds in one version, no SQL or scripts), 4 (41-44, profiles as evidence-artifact files), 15 (87-90, tools are children of their station), and 17 (96-99, EPCIS error declarations). Step-4 row (line 714) provides the sim `Line2` member names (`Running`, `UnitId`, `VisitId`, `VisitPresent`, `Torque`); fixtures use them as OPC UA node identifiers and Sparkplug metric names so steps 4 and 5 can reuse them.
- Owner decisions for step 2 (`DECISIONS-P2.md`, 2026-11-07): Q1: The completion gate is the committed bundle built by `publication.build` from the fixture workspace, re-proved byte for byte, and approved by `gates mapping approve` locally and in CI. Q2: The PLC source form authors `String` / 2.27.0 in step 2. Q3: Receiver parity for every refusal code of the attribution, impact, and both binding-profile tables. Q4: Only the tool level (`WORKUNIT_11`) is decided, recorded by a spec correction PR together with Bifrost's two extra pattern limits (group nesting deeper than 32; surrogate characters written in the pattern). `enter == leave`, the scope of typed `String`, `/` in ids, pattern length, and backtracking stay open and unchanged in Tyr.
- Rules the plan applies, as the spec states them. Line 117: All fields required, no additional properties. Bifrost validates independently with byte-identical schema copies; each refusal has a code. Line 131: `stations[]` are root-first, `:`-joined hierarchy paths. Line 132: Member references are `mappingId`s of the rule's own `members[]`. `metric` equals the semantic leaf's `name` byte for byte. Each requires one `member` step, per-definition leaf-name distinctness, and an `opcua-node` identifier ending with `.` + `metric`. The rule requires a non-empty list, each `mappingId` once, and one entry per (equipment path, metric); violations are `attribution.member-unresolved`. Each entry allows one role. Role overlaps are `attribution.identity-member` (activity + identity, two identity references) or `attribution.activity-member` (two activity references). Line 133: `activity[]` failures, including two entries for one equipment, are `attribution.activity-member`; an equipment without an activity entry is allowed. Line 135: Identity coverage is `attribution.identity-equipment`; identity member types are `attribution.identity-member`. `namespace` is optional under `occupancy-join` and required under `plc-stamped`. Both modes require `crossCheck: occupancy`. Line 136: `outOfOrdernessMs <= allowedLatenessMs <= horizonMs`, else `attribution.temporal-order`. Lines 167-172: `impact.attribution-missing`, `impact.scope-containment` (in the hierarchy and descendant-or-self of an attribution station), `impact.binding-unresolved`, `impact.binding-profile`, and `impact.retention-order` (`horizonMs <= workRecordsMs`). Lines 192-204: Profiles are evidence-artifact 1.1.0 files with id prefix `occupancy-binding-` / `incident-binding-`, media type `application/vnd.forseti.occupancy-binding+json` / `application/vnd.forseti.incident-binding+json`, and profile version `0.1.0`. A wrong prefix or media type is `*.binding-profile`. A reference that is not an evidence artifact 1.1.0 of the bundle is `*.binding-unresolved`. `scope` is not compared; `schemaSha256` is checked for its form only. Lines 206-226: The field sets of both profiles: `reasons` must be a non-empty distinct subset of the two EPCIS CBV reasons; `sources[]` and `kinds[]` must be non-empty and unique; patterns must use the `identity.pattern` syntax subset. Additional fields and empty values are `*.binding-profile`. Row 1 (line 711): Any document whose `schemaVersion` is 2.27.0, a 2.27.0 source definition included, needs a 2.27.0 proposal (`rule.envelope`). The 2.27.0 common schema adds `String` to the typed source value types. Command bindings 2.26.0 ride in a 2.27.0 proposal. Line 130: An invalid hierarchy keeps its own `hierarchy.*` refusal.
- Bifrost step 1 (read-only reference that Tyr mirrors; `main` = `33e864c`, PR #55, which the sibling checkout is on): `core/src/main/java/dev/krillin/bifrost/core/mapping/{AttributionRules,ImpactRules,OccupancyBindingProfile,IncidentBindingProfile}.java`, `MappingBundle.java` lines 38, 48, 63, 103-110 (sets and `rule.envelope`), schemas under `core/src/main/resources/mapping-contracts/2.27.0/`, fixtures `core/src/test/resources/mapping-fixtures/{attribution-impact,attribution-plc-stamped}`, `gates/src/test/java/dev/krillin/bifrost/gates/MappingGateTest.java` (`staged()` / `approves()`), `docs/MAPPING-PUBLICATION.md` "Attribution and impact rules 2.27", and plan `docs/superpowers/plans/2026-11-07-forseti-step1-mapping-contract-2.27.0.md`.
- Bifrost's pattern checker, as pinned for parity (`OccupancyBindingProfile.BindingPattern`): The subset parser refuses syntax outside spec line 225, any UTF-16 surrogate code unit (so every supplementary character), `(?:` nesting deeper than 32, and any `{m,n}` whose `m` or `n` does not parse as a `long` or has `m > n`. `Pattern.compile` runs last and refuses repetition bounds above `Integer.MAX_VALUE` (2147483647) with `Illegal repetition range` (JDK `Pattern.closure` uses `Math.addExact`/`multiplyExact`; checked on JDK 25, the same code since JDK 9) and an inverted class range (`[z-a]`). Bifrost does not parse the number of a `{m}` or `{m,}` itself, and `Pattern.compile` accumulates leading zeros, so `a{` + 4,500 zeros + `1}` is accepted (checked on JDK 25). A `{m,n}` whose number does not fit a `long` throws `NumberFormatException` inside `BindingPattern.accepted`, which catches every `RuntimeException` and returns false; it therefore surfaces as `attribution.binding-profile` like every other pattern refusal (consistent; no Bifrost follow-up). `MappingJson.JSON` (Jackson 2.17.2) reads every profile from its bytes with `STRICT_DUPLICATE_DETECTION`, so a duplicate JSON key is `*.binding-profile` (the parse exception is caught by `parse()`). Its byte reader skips a UTF-8 BOM (a BOM-prefixed profile is accepted), and its default nesting limit of 1,000 makes `[` x 10,000 (or x 1,500) `0` `]`... a reader exception, so a deeply nested file is `*.binding-profile` as well (all three checked with the jar on mutated copies of Bifrost's `attribution-impact` fixture). Python's `re` accepts bounds up to 4294967295 and raises `OverflowError` above; `int()` refuses more than 4,300 digits; `json.loads` on a `str` refuses a BOM, but on `bytes` detects `utf-8-sig`, keeps the last duplicate key, and raises `RecursionError` past about 1,000 levels (checked on 3.13.5). Tyr's port strips leading zeros before bounding the counts, compiles the normalised text, catches `OverflowError`, parses the profile **bytes** with `validate_contracts.pairs` (duplicate keys refused), and maps `RecursionError` to the profile code; the jar parity cases pin all of it.
- Tyr precedents: PR #19 (`39953a4`: `scripts/command_binding.py`, `scripts/test_command_binding.py`, `backend/{read_bindings,command_binding_authoring}.py`, `frontend/command-binding.js`, `docs/P4-I-COMMAND-BINDING.md`, `fixtures/command-binding/{workspace.json,bundle/}`), PR #20 (`da764c0`: 2.26.0 copy, `backend/server_certificates.py`, `scripts/server_certificate.py`), PR #18 (`334ffb2`, `scripts/metric_definition.py`), PR #17 (`backend/hierarchy_evidence.py`: a Tyr-side artifact with a data file, id prefix `hierarchy-`), `scripts/p6r/accept.py` lines 109-114 (keygen + approve through the jar), and `scripts/test_workflow.py` line 66 (a test that reads a frontend file as text).
## File Structure

| File | Responsibility |
|---|---|
| forseti `docs/superpowers/specs/2026-11-05-forseti-design.md` | **separate PR** - Decision 15 gains the fixture level sentence; "Binding profiles" gains Bifrost's two extra pattern limits (Task 1) |
| `contracts/2.27.0/attribution-rule.schema.json` | **new** - byte copy of Bifrost's |
| `contracts/2.27.0/impact-rule.schema.json` | **new** - byte copy of Bifrost's |
| `contracts/2.27.0/source-definition.schema.json` | **new** - byte copy of Bifrost's (the 2.7.0 `plc` source re-issued at 2.27.0 so a typed `String` source can be published) |
| `contracts/2.27.0/common.schema.json` | **new** - byte copy of Bifrost's (2.26.0 common + `$id`, two kinds in `fileEntry.kind`, `String` in the typed value types) |
| `contracts/2.27.0/mapping-proposal.schema.json` | **new** - byte copy of Bifrost's (2.26.0 with both constants at 2.27.0) |
| `editor-contracts/1.0.0/occupancy-binding.schema.json` | **new** - the workspace record of an authored occupancy binding profile (`profile` object + artifact metadata), id prefix `occupancy-binding-` |
| `editor-contracts/1.0.0/incident-binding.schema.json` | **new** - the workspace record of an authored incident binding profile, id prefix `incident-binding-` |
| `scripts/attribution_rule.py` | **new** - `KIND`, `VERSION`, profile constants, `occupancy_profile(raw, code)`, `pattern_accepted()` (Java-bounded), hierarchy path and member helpers, `validate(docs, read)` with the eleven `attribution.*` codes |
| `scripts/impact_rule.py` | **new** - `incident_profile(raw, code)`, `validate(docs, read)` with the five `impact.*` codes |
| `scripts/test_attribution_rule.py` | **new** - contract diff, 2.27.0 String source and the PLC form, profile and pattern refusals, every `attribution.*` code, hierarchy robustness, publication closure, fixture bundle equality, receiver parity matrix, Bifrost approval, authoring API and HTTP routes |
| `scripts/test_impact_rule.py` | **new** - incident profile refusals, every `impact.*` code, closure with the attribution rule |
| `scripts/p3a_contracts.py` | `schema_errors` dispatch for 2.27.0 (`mapping-proposal`, `attribution-rule`, `impact-rule`, `source-definition`); envelope tuples gain 2.27.0; `command-binding.envelope` accepts 2.26.0 and 2.27.0; `rule.envelope`; hierarchy gate flag; two validator calls after `command_binding.validate` |
| `scripts/validate_contracts.py` | `validate_schema` accepts `source-definition` 2.27.0; `source_rules` treats 2.27.0 as 2.7.0 (as it treats 2.10.0 and 2.21.0) |
| `frontend/app.js` | `accessFields` (line 56): `String` offered for typed access only |
| `frontend/mixed.js` | `draftSource` plc branch (line 27): `schemaVersion` 2.27.0 when the raw value type is `String`, 2.7.0 otherwise |
| `backend/binding_profiles.py` | **new** - check, transition and build of `occupancyBindings` / `incidentBindings` records; writes `data/<name>-<n>.json` and `evidence/<name>-<n>.json` |
| `backend/workspace_v2.py` | new sections allowed; schema, limit and duplicate-id checks for the rules; `binding_profiles.check`; `binding_profiles.build`; `attribution-rules/<n>.json`, `impact-rules/<n>.json`; proposal 2.27.0 for rules and 2.27.0 sources |
| `backend/publication.py` | closure: attribution rule with all its mapping sets, impact rule with its attribution rule; `refs` gains `occupancyBindingRef`, `incidentBindingRef`, `attributionRuleRef` |
| `backend/attribution_authoring.py` | **new** - listing, plan and apply under revision CAS for both kinds and both profiles |
| `backend/server.py` | `binding_profiles.transition` in `Store.save`; legacy (1.x) workspace refuses 2.27.0 sources like 2.7.0/2.10.0 (line 186); routes `GET /api/attribution-rule`, `POST /api/attribution-rule-plan`, `POST /api/attribution-rule-apply`; asset `/attribution-rule.js` |
| `frontend/attribution-rule.js` | **new** - the screen: profiles and rules edited as JSON blocks beside the member catalog Tyr derives, validate (plan) and save (apply) |
| `frontend/index.html`, `frontend/workflow.js` | tab `attributionRules` in the connect group; script tag |
| `scripts/test_workflow.py` | tab count 25 -> 26 |
| `fixtures/attribution-rule/workspace.json` | **new** - the `occupancy-join` workspace (6 equipment, 4 connections, 6 sources, 2 semantic models, 4 targets, 4 mapping sets, hierarchy + plant register, both profiles, one attribution rule, one impact rule) |
| `fixtures/attribution-rule/bundle/**` | **new** - its publication for stream `line2` (built by `publication.build`, committed, compared byte for byte by a test): 39 files |
| `fixtures/attribution-rule/plc-stamped-workspace.json` | **new** - the `plc-stamped` workspace: six more 2.27.0 sources (String unit and visit ids, Boolean present) in the shape the PLC form writes, two stamped semantic models for station1 and nutrunner1, the `plc-stamped` rule |
| `fixtures/attribution-rule/plc-stamped-bundle/**` | **new** - its publication for stream `line2`: 59 files |
| `docs/P4-J-ATTRIBUTION-RULE.md` | **new** - the step document, in the form of `docs/P4-I-COMMAND-BINDING.md` (Korean, prose pipeline) |

Nothing else changes. `.github/workflows/ci.yml` is untouched: it already checks out Bifrost's default branch (`33e864c` carries step 1), builds the gates jar and runs every `scripts/test_*.py`; `scripts/ci_bifrost_seam_tests.txt` stays empty, so the seam and parity tests run in CI (about 30 extra JVM starts per job, accepted by the owner). `contracts/README.md` and `fixtures/README.md` were not touched by PR #17-#20 and are not touched here. The Bifrost repository is not modified by this step (its copy of the Tyr bundles is the closing Follow-up).

## Conventions the tasks follow

- **Refusal codes** follow the spec. A Tyr check raises `ValueError(code)` through `semantic_lifecycle.require` and stops at the first failure per rule (as `command_binding.validate` and Bifrost's validators do). `p3a_contracts.validate_package` turns it into one finding `{"ruleCode": code, "path": kind}`. Tyr's own workspace-record codes follow the precedent family of `read_bindings.py` / `server_certificates.py` / `hierarchy_evidence.py` (`<name>.{limit,schema,duplicate,scope,version-required}`, authoring `<name>.plan-{request,required,changed}`). They never reuse a spec code for another condition and are listed in the step document as Tyr's.
- **What Tyr mirrors.** Every code of the spec's three tables plus `rule.envelope`; the two profile parsers (field set, constants, non-empty values, digest form, reasons subset, distinct lists, and the pattern subset with Bifrost's surrogate and depth-32 refusals and Java's repetition bounds); the schemas (byte copies); and the envelope compatibility tuples. **What Bifrost alone decides:** approval (two-key receipt), the in-toto/DSSE attestation, release files and head signing, the activation policy, the submission context checks (`hierarchy.context-equipment` against `submission.json`), and its own verdict on digests (`bundle.digest` and `evidence.digest` exist on both sides). **What Tyr does not claim to verify** (forseti's own checks at job start or at run time): that `format.schemaSha256` equals forseti's built-in schema (`binding.schema-mismatch`, spec line 192), that the incident schema supports each `kinds[]` entry (line 224), that telemetry carries identity and measurements in one message, that the topics exist or producers honour the vocabulary, that the scan period equals `coverage.expectedPeriodMs`, or any Bad-quality, visit, correction or impact behaviour. Profile `scope` is never compared with a rule's stations (line 204).
- **Document references** `{id, version}` resolve inside the package by `(kind, id, version)` (`attribution_rule.find`).
- **Hierarchy paths** start at the root and join with `:` (`attribution_rule.paths`, following `command_binding.path` and Bifrost's `CommandBindings.path`). Because ids carry no `:`, `startswith(station + ":")` is an exact descendant test (`attribution_rule.within`). `paths()` first runs `equipment_hierarchy.check` (duplicate node, missing parent, cycle, depth), so a broken hierarchy raises its own `hierarchy.*` code and never loops. Additionally, `validate_package` runs the rule validators only when the hierarchy validated, as Bifrost's fail-first bundle check implies (spec line 130).
- **Members** resolve by `mappingSetRef` + `mappingId` to one mapping of the package (`mappingId` is package-unique: `mapping.duplicate-id`). The mapping set's `equipmentInstanceId` gives the hierarchy path. `logical_structures.resolve(semantic, memberPath)` gives the leaf (`name`, `semanticId`, `valueType`), and `logical_structures.layout(semantic)["definitions"]` minus containers gives the leaf names of one definition.
- **Profiles are authored, not imported.** Unlike read bindings and server certificates (bytes kept as imported), the two forseti profiles are Tyr's own output. The workspace record holds a `profile` object, `vc.save` writes it (`json.dumps(indent=2, ensure_ascii=False) + "\n"`, LF), and the artifact wrapper pins the SHA-256 of those bytes. Bifrost re-reads the bytes with its own parser. Tyr's parser runs on the same bytes at workspace check (`binding_profiles.check`) and at package validation (`attribution_rule.validate` / `impact_rule.validate`).
- **Typed String sources** are ordinary PLC source records (`sources[].definition`) whose `schemaVersion` is 2.27.0 and whose `rawRepresentation` is `{"mode": "typed", "valueType": "String"}`. The form writes them. The backend path that stores them is `PUT /api/workspace` -> `server.check_state` -> `legacy_check_state.schema()` + `workspace_v2.findings()` -> `p3a_contracts.validate_package` -> `vc.source_rules`. Fixture sources are written in exactly the shape the form produces (same keys, same `evidenceRefs`, `capturedAt` fixed).
- **Tests** mirror `test_command_binding.py`. `refused(state, code)` asserts `server.check_state` raises `ValueError` matching the code. Mutation helpers copy the fixture workspace and change one thing. Package-only tests build into a `TemporaryDirectory`, change a file, re-pin with `repinned(root)` (which recomputes every evidence `file.sha256`, every `proposal.files[].sha256` and `submission.proposalSha256`), and read `validate_package(root)[0]`. Seam tests use `publication.Adapter(JAR, registry).call('validate', bundle)` and a `java()` helper for `identity keygen` and `mapping approve` (`scripts/p6r/accept.py` lines 109-114). Each task's red step fails for the reason stated (a missing module or helper, a missing refusal, a missing file), with no temporary edits: the test module's import lines grow with the tasks that create the modules.
- **Commands.** One module: `python -B scripts/test_attribution_rule.py` (prints `Ran N tests ... OK`). One class or test: `python -B scripts/test_attribution_rule.py Pattern` / `... Pattern.test_accepted` (the module inserts `backend` and `scripts` on `sys.path` itself and must run as a file, not with `-m unittest`). Everything: `python -B scripts/ci_run.py`. The jar: `mvn -B -ntp -pl gates -am package -DskipTests` in `../bifrost` (CI step "Build Bifrost's gates CLI"). Parity and approval tests fail without the jar, as the existing seam tests do.
- **Commits.** Use one commit per task with conventional subjects as in the repository (`feat(contracts): ...`, `feat(attribution-rule): ...`, `test(attribution-rule): ...`, `docs: ...`). Bodies and the PR description go through the repository's prose pipeline (the pre-commit hook enforces it). Never commit on `main`. Ensure `git diff --check` is clean before each commit.

---

## Chunk 1: Spec correction, contract 2.27.0 copies, the typed String source and its form

### Task 0: Branch and the Bifrost reference

**Files:** none

- [ ] `git -C tyr status --short` is empty; `git -C tyr log -1 --format=%h main` prints `da764c0`.
- [ ] `git -C tyr switch -c feat/attribution-rule-authoring main`.
- [ ] `git -C bifrost rev-parse --short HEAD` prints `33e864c` and `git -C bifrost status --short` is empty (the sibling checkout `test_p6.Receiver.test_shared_schema_copies` and the seam tests read). Build the jar once: `cd bifrost && mvn -B -ntp -pl gates -am package -DskipTests` -> `gates/target/bifrost-gates.jar` exists. CI does this on its own checkout.
- [ ] `git -C forseti status --short` is empty; `git -C forseti log -1 --format=%h main` is the merged head (`4e6aea1` + forseti #2 `d3d61e1`).

### Task 1: forseti spec correction (separate PR, opened first)

**Files:**
- Modify (forseti repository): `docs/superpowers/specs/2026-11-05-forseti-design.md`

This is a documentation PR in `yggdrasil-iiot/forseti` on branch `docs/step2-decisions`; it records the owner's Q4 decisions and nothing else, and it is opened before Tyr Task 2 so the Tyr PR body and `docs/P4-J-ATTRIBUTION-RULE.md` can cite it. It can merge independently of the Tyr PR; the Tyr PR must not merge before it.

- [ ] **Step 1.1** Decision 15 (spec lines 87-90): append to the `Decision:` bullet the sentence: "In the fixtures of delivery steps 1 and 2 a station is authored at ISA-95 level `WORKCELL_6` and a tool under it at `WORKUNIT_11` (OPC 10030 Table 36: a Work Unit is the lowest level of equipment doing work within a Work Cell); Bifrost checks the hierarchy's structure only, not a level pair matrix."
- [ ] **Step 1.2** "Binding profiles", after the pattern-syntax bullet (line 225) and before the `Additional fields` bullet (line 226), add one bullet: "Bifrost's checker additionally refuses a non-capturing group nesting deeper than 32 levels (a bound on its recursive parser, far above what a unit-id pattern needs) and any UTF-16 surrogate code unit written in the pattern, which refuses every supplementary character (Java reads a surrogate pair as one code point and ECMA-262 without the `u` flag as two, so a quantifier would repeat different things); its last step is a Java `Pattern.compile`, so a repetition bound above 2147483647 and an inverted class range are refused as well. Tyr mirrors these refusals."
- [ ] **Step 1.3** `git -C forseti diff --check` clean; the two edits are the whole diff. Commit on `docs/step2-decisions` (`docs(spec): record the fixture tool level and Bifrost's pattern limits`), push, open the forseti PR titled `docs(spec): step-2 decisions: tool level WORKUNIT_11, Bifrost pattern limits`. Record its number for the Tyr PR body. The other open questions (Open points 1-4 below) are not touched.

### Task 2: Contract 2.27.0 under `contracts/2.27.0/` and the schema dispatch

**Files:**
- Create: `contracts/2.27.0/attribution-rule.schema.json`, `contracts/2.27.0/impact-rule.schema.json`, `contracts/2.27.0/source-definition.schema.json`, `contracts/2.27.0/common.schema.json`, `contracts/2.27.0/mapping-proposal.schema.json`
- Modify: `scripts/p3a_contracts.py` (`schema_errors`, line 27 area), `scripts/validate_contracts.py` (line 55)
- Create: `scripts/test_attribution_rule.py` (module header and class `Contract`)

- [ ] **Step 2.1** Create `scripts/test_attribution_rule.py` (the header imports only modules that exist; later tasks add their own import lines):

```python
"""2.27 attribution and impact rules: byte-identical contract copies, the typed String source and the PLC form, authored
binding profiles, every attribution.* refusal, publication closure, receiver parity per refusal code, Bifrost approval."""
import sys,copy,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication
FIX=R/'fixtures/attribution-rule'
BUNDLE=FIX/'bundle'
PLC_BUNDLE=FIX/'plc-stamped-bundle'
JAR=R.parent/'bifrost/gates/target/bifrost-gates.jar'
SETS=('station1-mapping','station2-mapping','nutrunner1-mapping','nutrunner2-mapping')
def load(p):return server.contracts.load(R/p)
def w():return load('fixtures/attribution-rule/workspace.json')
def plc():return load('fixtures/attribution-rule/plc-stamped-workspace.json')
def ruled(f,state=None):
 state=w() if state is None else state;f(state['attributionRules'][0]);return state
def profiled(f,section='occupancyBindings',state=None):
 state=w() if state is None else state;f(state[section][0]);return state
def package(state,folder):
 server.build_package(state,folder);return load(folder/'proposal.json')
def publish(state,folder,sets=SETS,stream='line2',id='attribution-fixture'):
 _,_,findings=publication.build(state,folder,id,stream,'proposer',None,list(sets),False,server.build_package)
 return load(folder/'proposal.json'),findings
def tree(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
def repinned(root):
 """Re-pin a mutated package: every evidence file digest, every proposal entry digest, the submission's proposal digest."""
 p=load(root/'proposal.json')
 for e in p['files']:
  if e['kind']=='evidence-artifact':
   a=load(root/e['path']);a['file']['sha256']=server.contracts.hashed(root/a['file']['path']);server.contracts.save(root/e['path'],a)
  e['sha256']=server.contracts.hashed(root/e['path'])
 server.contracts.save(root/'proposal.json',p)
 if (root/'submission.json').is_file():
  s=load(root/'submission.json');s['proposalSha256']=server.contracts.hashed(root/'proposal.json');server.contracts.save(root/'submission.json',s)
 return root
class Contract(unittest.TestCase):
 """Contract 2.27.0 is Bifrost's, byte for byte (test_p6 proves the bytes); here: what it adds to 2.26.0."""
 def test_2_27_schemas_extend_2_26_only_where_intended(self):
  old,new=((R/'contracts'/v/'mapping-proposal.schema.json').read_text(encoding='utf-8') for v in ('2.26.0','2.27.0'))
  self.assertEqual(old.replace('2.26.0','2.27.0'),new)
  old,new=(load('contracts/'+v+'/common.schema.json')['$defs'] for v in ('2.26.0','2.27.0'))
  self.assertEqual(new['fileEntry']['properties']['kind']['enum'],old['fileEntry']['properties']['kind']['enum']+['attribution-rule','impact-rule'])
  typed=lambda d:next(b for b in d['rawRepresentation']['oneOf'] if b['properties']['mode']['const']=='typed')['properties']['valueType']['anyOf'][0]['enum']
  self.assertEqual(typed(new),typed(old)+['String'])
  self.assertEqual({k for k in old if old[k]!=new[k]},{'fileEntry','rawRepresentation'})
  for kind in ('attribution-rule','impact-rule'):
   s=load('contracts/2.27.0/'+kind+'.schema.json');self.assertEqual(s['properties']['kind']['const'],kind);self.assertEqual(s['properties']['schemaVersion']['const'],'2.27.0');self.assertFalse(s['additionalProperties'])
 def test_2_27_source_definition_is_the_2_7_plc_source(self):
  old=next(b for b in load('contracts/2.7.0/source-definition.schema.json')['oneOf'] if b['properties']['sourceKind']['const']=='plc');new=load('contracts/2.27.0/source-definition.schema.json')
  self.assertEqual(new['properties']['schemaVersion'],{'const':'2.27.0'});self.assertEqual(set(new['properties']),set(old['properties']));self.assertEqual(new['required'],old['required'])
  base=load('fixtures/command-binding/bundle/sources/0.json')   # a 2.7.0 plc OPC UA source
  string=dict(base,schemaVersion='2.27.0',rawRepresentation={'mode':'typed','valueType':'String'})
  self.assertEqual(server.v2.p3.schema_errors('source-definition',string),[])
  self.assertNotEqual(server.v2.p3.schema_errors('source-definition',dict(base,rawRepresentation={'mode':'typed','valueType':'String'})),[])   # 2.7.0 still cannot declare String
  self.assertEqual(server.contracts.validate_schema('source-definition',string),[])
if __name__=='__main__':unittest.main()
```

- [ ] **Step 2.2** Run: `python -B scripts/test_attribution_rule.py Contract` -> 2 failures: `FileNotFoundError: ... contracts/2.27.0/mapping-proposal.schema.json` and `... contracts/2.27.0/source-definition.schema.json`. Expected.
- [ ] **Step 2.3** Copy the five files from the Bifrost checkout, bytes unchanged (no editor, no re-serialization):

```bash
mkdir -p contracts/2.27.0
for f in attribution-rule impact-rule source-definition common mapping-proposal; do
  cp ../bifrost/core/src/main/resources/mapping-contracts/2.27.0/$f.schema.json contracts/2.27.0/$f.schema.json
  cmp contracts/2.27.0/$f.schema.json ../bifrost/core/src/main/resources/mapping-contracts/2.27.0/$f.schema.json && echo same $f
done
```

- [ ] **Step 2.4** `scripts/p3a_contracts.py`, `schema_errors`: insert before the 2.25/2.26 line:

```python
    if v=='2.27.0' and kind in ('mapping-proposal','attribution-rule','impact-rule','source-definition'):return list(vc.schema_validator(kind,v).iter_errors(doc))
```

- [ ] **Step 2.5** `scripts/validate_contracts.py` line 55: the tuple `("2.4.0","2.7.0","2.10.0","2.21.0")` becomes `("2.4.0","2.7.0","2.10.0","2.21.0","2.27.0")` (so `server.schema(d, "source-definition")` and the legacy check accept a 2.27.0 source).
- [ ] **Step 2.6** Run: `python -B scripts/test_attribution_rule.py Contract` -> `Ran 2 tests ... OK`. `python -B scripts/test_p6.py Receiver.test_shared_schema_copies` -> `OK`. `python -B scripts/validate_contracts.py --deny-network` -> `"failed": []` (the registry loads every `contracts/*/*.schema.json`; the `uri` format checker is installed).
- [ ] **Step 2.7** Commit: `feat(contracts): add attribution-rule and impact-rule kinds for contract 2.27.0`.

### Task 3: A typed `String` source at 2.27.0 is accepted, checked and packaged at 2.27.0

**Files:**
- Modify: `scripts/validate_contracts.py` (`source_rules`, lines 64-70), `backend/workspace_v2.py` (`build`, after line 80), `backend/server.py` (line 186), `scripts/p3a_contracts.py` (`validate_package`, lines 65-73)
- Modify: `scripts/test_attribution_rule.py` (helper `string_source`, class `StringSource`)

Context: a `plc-stamped` rule needs String `UnitId` and `VisitId` members. A source document carries its own `schemaVersion`; a 2.27.0 String source must pass `server.check_state` (legacy `schema()` + `source_rules`), be built into `sources/<n>.json` unchanged, force the proposal to 2.27.0 (`rule.envelope`, spec row 1), and be refused by a 1.x workspace as 2.7.0/2.10.0 sources are (`server.py` line 186).

- [ ] **Step 3.1** Add to `scripts/test_attribution_rule.py` (before `if __name__`):

```python
def string_source(state,id='station1-unit',equipment='station1',connection='sim-opcua-station1',node='Line2/Station1.UnitId',value_type='String',note=None):
 """A typed OPC UA source record exactly as the PLC form writes it (app.js draftSource + mixed.js plc branch, Task 4): 2.27.0 for a
 String raw type, 2.7.0 for every other raw type; capturedAt fixed."""
 d={'kind':'source-definition','schemaVersion':'2.27.0' if value_type=='String' else '2.7.0','id':id,'version':'1.0.0','equipmentInstanceId':equipment,'connectionProfileRef':connection,'accessProfileRef':'s7-1500-opcua-v1','status':'ready',
    'rawAddressText':'nsu=urn:bifrost:opcua:sim;s='+node,'addressRadix':None,'access':{'kind':'opcua-node','namespaceUri':'urn:bifrost:opcua:sim','identifierType':'string','identifier':node},
    'rawRepresentation':{'mode':'typed','valueType':value_type},'inputStage':'already-engineered','unit':{'status':'not-applicable'},'evidenceRefs':[{'artifactId':'manual-'+id,'locator':{'kind':'text-line','line':1}}],'viewOf':None,'sourceKind':'plc','accessMode':'read'}
 state['sources'].append({'definition':d,'label':id,'note':note or (node+', '+value_type),'origin':'synthetic','capturedAt':'2026-11-07T00:00:00Z'});return state
class StringSource(unittest.TestCase):
 """Spec row 1: the 2.27.0 common schema adds String to typed sources; a 2.27.0 document travels only in a 2.27.0 proposal."""
 def base(self):
  state=load('fixtures/command-binding/workspace.json');del state['commandBindings'],state['readBindings'],state['serverCertificates'];return state
 def test_a_2_27_string_source_is_accepted_and_packaged_at_2_27(self):
  state=string_source(self.base(),'mixer1-unit','mixer1','sim-opcua','Line1/Mixer1.UnitId');server.check_state(state)
  self.assertEqual([f for f in server.findings_for(state) if f['ruleCode']!='mapping.incomplete-object'],[])
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));self.assertEqual(p['schemaVersion'],'2.27.0')
   src=next(load(Path(t)/e['path']) for e in p['files'] if e['id']=='mixer1-unit');self.assertEqual((src['schemaVersion'],src['rawRepresentation']),('2.27.0',{'mode':'typed','valueType':'String'}))
 def test_a_2_7_source_cannot_declare_string(self):
  state=string_source(self.base(),'mixer1-unit','mixer1','sim-opcua','Line1/Mixer1.UnitId');state['sources'][-1]['definition']['schemaVersion']='2.7.0'
  self.assertRaisesRegex(ValueError,'source-definition',server.check_state,state)
 def test_a_2_27_source_needs_a_2_27_proposal(self):
  state=string_source(self.base(),'mixer1-unit','mixer1','sim-opcua','Line1/Mixer1.UnitId')
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(state,root);p=load(root/'proposal.json');p['schemaVersion']='2.26.0';server.contracts.save(root/'proposal.json',p)
   self.assertEqual([e['ruleCode'] for e in server.v2.p3.validate_package(root)[0]],['rule.envelope'])
 def test_a_2_26_command_binding_rides_in_a_2_27_proposal(self):
  state=string_source(load('fixtures/command-binding/workspace.json'),'mixer1-unit','mixer1','sim-opcua','Line1/Mixer1.UnitId');server.check_state(state)
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));self.assertEqual(p['schemaVersion'],'2.27.0');self.assertEqual(server.v2.p3.validate_package(Path(t))[0],[])
 def test_legacy_workspace_refuses_a_2_27_source(self):
  state=load('fixtures/realistic/workspace.json');self.assertNotIn('workspaceVersion',state)   # the committed 1.x workspace with an OPC UA connection (logical-ua)
  string_source(state,'line-a-unit','line-a-motor-ua','logical-ua','LineA/Motor.UnitId')
  self.assertRaisesRegex(ValueError,'2.0 authoring workspace',server.check_state,state)
```

- [ ] **Step 3.2** Run: `python -B scripts/test_attribution_rule.py StringSource` -> 4 failures: `test_a_2_27_string_source_is_accepted_and_packaged_at_2_27` (`'2.26.0' != '2.27.0'`), `test_a_2_27_source_needs_a_2_27_proposal` (`[] != ['rule.envelope']`), `test_a_2_26_command_binding_rides_in_a_2_27_proposal` (version), `test_legacy_workspace_refuses_a_2_27_source` (no raise: the message of line 186 is "Mixed/access-mode sources require the 2.0 authoring workspace"); `test_a_2_7_source_cannot_declare_string` passes already (schema). Expected.
- [ ] **Step 3.3** `scripts/validate_contracts.py`, `source_rules`: add as the first branch (before the 2.21.0 one):

```python
    if s.get("schemaVersion")=="2.27.0":
        d=copy.deepcopy(s);d["schemaVersion"]="2.7.0";return source_rules(d)
```

- [ ] **Step 3.4** `backend/server.py` line 186: `("2.7.0","2.10.0")` becomes `("2.7.0","2.10.0","2.27.0")`.
- [ ] **Step 3.5** `backend/workspace_v2.py`, `build`: after the `commandBindings` block (line 80) and before `vc.save(folder/"proposal.json",p)` add:

```python
    # Spec 2.27 row 1 (rule.envelope): a 2.27.0 document, a typed String source included, travels only in a 2.27.0 proposal.
    if any(r["definition"].get("schemaVersion")=="2.27.0" for r in state["sources"]):p["schemaVersion"]="2.27.0"
```
(Task 8 adds the rule sections in front of this line.)

- [ ] **Step 3.6** `scripts/p3a_contracts.py`, `validate_package` lines 65-73: the two tuples `('2.21.0', ... ,'2.26.0')` and `('2.22.0', ... ,'2.26.0')` gain `'2.27.0'`; the command-binding envelope becomes `proposal['schemaVersion'] not in ('2.26.0','2.27.0')`; add after it:

```python
    # As Bifrost (rule.envelope): a 2.27.0 document, rule or source definition, travels only in a 2.27.0 proposal.
    if any(d.get('schemaVersion')=='2.27.0' for d in docs.values()) and proposal['schemaVersion']!='2.27.0':add('rule.envelope','proposal.json')
```

- [ ] **Step 3.7** Run: `python -B scripts/test_attribution_rule.py StringSource` -> `Ran 5 tests ... OK`. `python -B scripts/test_command_binding.py` -> `Ran 52 tests ... OK` (unchanged: `test_older_envelope_refused` still sees `['command-binding.envelope']` at 2.25.0). `python -B scripts/test_p3a.py --report "$TMP/p3a.json"` -> exit 0.
- [ ] **Step 3.8** Commit: `feat(sources): accept typed String sources at contract 2.27.0`.

### Task 4: The PLC source form authors a `String` source at 2.27.0

**Files:**
- Modify: `frontend/app.js` (line 56), `frontend/mixed.js` (line 27)
- Modify: `scripts/test_attribution_rule.py` (class `StringSource`, one test)

Owner decision Q2. The form's draft chain is `app.js` `draftSource` (line 172, builds `rawRepresentation` from `rawType`) -> `arrays.js` override (line 35, fixed arrays) -> `mixed.js` override (line 27, the `plc` branch sets `schemaVersion:'2.7.0'`, `sourceKind`, `accessMode`). `String` belongs to typed access only (`rawRepresentation.mode` `typed`: symbol and OPC UA profiles; the bytes profiles keep their list), and a String source is written at 2.27.0 because 2.7.0 cannot declare it (Task 2). There is no JS test runner in the repository; the precedent for asserting frontend content is `test_workflow.py` line 66 (regex over `index.html`) and `test_http_routes` (served asset text), so the test reads the two files as text; the record the form produces is `string_source()` of Task 3, which the backend tests already accept.

- [ ] **Step 4.1** Add to class `StringSource`:

```python
 def test_plc_source_form_offers_string_for_typed_access_and_writes_2_27(self):
  app=(R/'frontend/app.js').read_text(encoding='utf-8');mixed=(R/'frontend/mixed.js').read_text(encoding='utf-8')
  line=next(l for l in app.splitlines() if 'select("rawType"' in l)
  self.assertIn('bytes?["Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Boolean"]:["Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Boolean","String"]',line)
  plc=next(l for l in mixed.splitlines() if "if(kind==='plc')" in l)
  self.assertIn("schemaVersion:r.definition.rawRepresentation?.valueType==='String'?'2.27.0':'2.7.0'",plc)
  with urllib_served(self) as get:self.assertIn(b'"String"]',get('/app.js'));self.assertIn(b"'2.27.0':'2.7.0'",get('/mixed.js'))
```
  and the helper, next to `tree()`:

```python
import contextlib
@contextlib.contextmanager
def urllib_served(case):
 """The frontend as the server serves it (test_http_routes precedent): yields get(path) -> bytes."""
 import threading,urllib.request
 tmp=tempfile.TemporaryDirectory();store=server.Store(Path(tmp.name)/'db.sqlite3');store.migrate(0,{})
 http=server.make_server(store,0);threading.Thread(target=http.serve_forever,daemon=True).start()
 try:
  base='http://127.0.0.1:'+str(http.server_address[1])
  def get(path):
   with urllib.request.urlopen(base+path) as r:return r.read()
  yield get
 finally:http.shutdown();http.server_close();tmp.cleanup()
```

- [ ] **Step 4.2** Run: `python -B scripts/test_attribution_rule.py StringSource.test_plc_source_form_offers_string_for_typed_access_and_writes_2_27` -> fails on the first `assertIn` (the current line offers one list without `String`). Expected.
- [ ] **Step 4.3** `frontend/app.js` line 56 becomes:

```javascript
 html+=select("rawType","원시 값 타입",(bytes?["Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Boolean"]:["Int16","UInt16","Int32","UInt32","Int64","Float32","Float64","Boolean","String"]).map(x=>[x,x]),raw.valueType,false);
```
  and `frontend/mixed.js` line 27 becomes:

```javascript
 if(kind==='plc'){const r=draftBeforeMixed();r.definition={...r.definition,schemaVersion:r.definition.rawRepresentation?.valueType==='String'?'2.27.0':'2.7.0',sourceKind:'plc',accessMode:val('mixed-source-mode')||'read'};return r;}
```
(`bytes` is already in scope at line 54. A String source with a fixed array, or a 2.10.0 view of a String source (`views.js` line 31), is not offered in step 2 and stays a schema refusal; the step document names both.)

- [ ] **Step 4.4** Run: `python -B scripts/test_attribution_rule.py StringSource` -> `Ran 6 tests ... OK`. Open the form once by hand (`python backend/server.py`, tab "PLC 소스", profile `s7-1500-opcua-v1`): "원시 값 타입" lists `String`; saving a String source with the fixture-like node `Line2/Station1.UnitId` stores `schemaVersion` `2.27.0` (check in the 저장본 JSON of `/api/workspace`); choosing a bytes profile hides `String`.
- [ ] **Step 4.5** Commit: `feat(sources): offer String in the PLC source form and write it at 2.27.0`.

## Chunk 2: Binding profiles (parsers, authored records, evidence-artifact files)

### Task 5: `scripts/attribution_rule.py`, part 1: the occupancy binding profile and the pattern subset

**Files:**
- Create: `scripts/attribution_rule.py` (constants, helpers, `occupancy_profile`, `pattern_accepted`; `validate` comes in Task 8)
- Modify: `scripts/test_attribution_rule.py` (import line; classes `OccupancyProfile`, `Pattern`)

Spec lines 192-215, 224-226; Bifrost `OccupancyBindingProfile.java` (field set, constants, `strings()`, `BindingPattern`, `MAX_DEPTH` 32, surrogate refusal) and the pinned engine behaviour (see "Spec and rules applied"): Bifrost refuses any repetition bound above 2147483647; Python alone would accept up to 4294967295 and raise `OverflowError` above, so the port bounds the counts and catches the exception.

- [ ] **Step 5.1** Add `import attribution_rule as ar` to the import line of `scripts/test_attribution_rule.py` (`import server,publication,attribution_rule as ar`) and add:

```python
PROFILE={'profileVersion':'0.1.0','topic':'mfg.occupancy','format':{'schemaId':'urn:forseti:schema:occupancy:1.0.0','schemaSha256':'0'*63+'1'},
         'identity':{'scheme':'mes-unit-id','pattern':'[A-Z0-9]{17}'},'enter':{'bizStep':'urn:epcglobal:cbv:bizstep:arriving'},'leave':{'bizStep':'urn:epcglobal:cbv:bizstep:departing'},
         'correction':{'errorDeclaration':'reissue-same-event-id','reasons':['urn:epcglobal:cbv:er:did_not_occur','urn:epcglobal:cbv:er:incorrect_data']},'timestampBasis':'eventTime','sources':['mes-line2']}
def raw(profile):return (json.dumps(profile,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def changed(f):
 p=copy.deepcopy(PROFILE);f(p);return raw(p)
class OccupancyProfile(unittest.TestCase):
 """Spec 206-215, 224-226 read with Tyr's own parser at the strictness of Bifrost's OccupancyBindingProfile."""
 def test_accepted(self):self.assertEqual(ar.occupancy_profile(raw(PROFILE))['topic'],'mfg.occupancy')
 def refused(self,raw_bytes,code='attribution.binding-profile'):self.assertRaisesRegex(ValueError,code,ar.occupancy_profile,raw_bytes)
 def test_field_set(self):
  self.refused(changed(lambda p:p.update(note='x')));self.refused(changed(lambda p:p.pop('sources')));self.refused(b'not json');self.refused(b'[]')
  self.refused(changed(lambda p:p['format'].update(extra=1)));self.refused(changed(lambda p:p['identity'].pop('pattern')));self.refused(changed(lambda p:p['enter'].update(disposition='x')))
 def test_constants_and_empty_values(self):
  self.refused(changed(lambda p:p.update(profileVersion='0.2.0')));self.refused(changed(lambda p:p.update(timestampBasis='recordTime')));self.refused(changed(lambda p:p.update(topic='')))
  self.refused(changed(lambda p:p['format'].update(schemaId='urn:forseti:schema:occupancy:1.1.0')));self.refused(changed(lambda p:p['identity'].update(scheme='gs1-sgtin')))
  self.refused(changed(lambda p:p['enter'].update(bizStep='')));self.refused(changed(lambda p:p['correction'].update(errorDeclaration='new-event-id')))
 def test_digest_form(self):
  self.refused(changed(lambda p:p['format'].update(schemaSha256='0'*64+'0')));self.refused(changed(lambda p:p['format'].update(schemaSha256='A'*64)));self.refused(changed(lambda p:p['format'].update(schemaSha256=1)))
 def test_reasons_and_sources(self):
  self.refused(changed(lambda p:p['correction'].update(reasons=[])));self.refused(changed(lambda p:p['correction'].update(reasons=['urn:epcglobal:cbv:er:did_not_occur']*2)))
  self.refused(changed(lambda p:p['correction'].update(reasons=['urn:epcglobal:cbv:er:other'])));ar.occupancy_profile(changed(lambda p:p['correction'].update(reasons=['urn:epcglobal:cbv:er:incorrect_data'])))
  self.refused(changed(lambda p:p.update(sources=[])));self.refused(changed(lambda p:p.update(sources=['a','a'])));self.refused(changed(lambda p:p.update(sources=['a',''])));self.refused(changed(lambda p:p.update(sources='mes')))
 def test_other_code_is_the_callers(self):self.assertRaisesRegex(ValueError,'occupancy-binding.profile',ar.occupancy_profile,b'{}','occupancy-binding.profile')
 def test_duplicate_json_keys_are_refused(self):   # Bifrost's MappingJson reads with STRICT_DUPLICATE_DETECTION; Python's json would keep the last value
  self.refused(raw(PROFILE).replace(b'"topic": "mfg.occupancy"',b'"topic": "ignored", "topic": "mfg.occupancy"'))
 def test_utf8_bom_is_accepted_as_bifrost_accepts_it(self):self.assertEqual(ar.occupancy_profile(b'\xef\xbb\xbf'+raw(PROFILE))['topic'],'mfg.occupancy')   # Jackson's byte reader skips it; json.loads on bytes detects utf-8-sig
 def test_deep_nesting_is_refused_not_a_crash(self):   # Jackson's 1,000-level limit makes it a reader exception in Bifrost; Python raises RecursionError, mapped to the code
  self.refused(b'['*10000+b'0'+b']'*10000);self.refused(b'['*1500+b'0'+b']'*1500)
 def test_enter_equal_to_leave_is_accepted_as_bifrost_accepts_it(self):ar.occupancy_profile(changed(lambda p:p['leave'].update(bizStep=p['enter']['bizStep'])))   # Open point 1
class Pattern(unittest.TestCase):
 """Spec 225 plus Bifrost's extra limits (forseti spec PR of Task 1): the syntax common to Java and ECMA-262, nothing else."""
 def test_accepted(self):
  for p in ('[A-Z0-9]{17}','VIN-[0-9]{6}','(?:A|B)[0-9]+','a.c','x*y+z?','[^-]{1,3}','\\-\\.\\+','[a\\]b]','(?:(?:a))','a{2}','a{2,}','[0-9A-Fa-f]{32}','(?:a+)+'):self.assertTrue(ar.pattern_accepted(p),p)
 def test_refused(self):
  for p in ('','^A$','(A)','(?<n>A)','(?=A)','(?!A)','\\d+','\\w','\\p{Lu}','[[:alpha:]]','A*?','A++','A{','A{2,1}','A{,3}','\\1','(?i)A','[a&&[b]]','[]','[a','a)','(?:a','\\','\\A','a{2}{3}','a**','[z-a]'):self.assertFalse(ar.pattern_accepted(p),p)
 def test_surrogates_and_supplementary_characters_are_refused(self):
  self.assertFalse(ar.pattern_accepted('A\U0001F600'));self.assertFalse(ar.pattern_accepted('A\ud83d'))   # Java reads a pair as one code point, ECMA-262 as two
 def test_group_depth_is_bounded(self):
  self.assertTrue(ar.pattern_accepted('(?:'*ar.MAX_DEPTH+'a'+')'*ar.MAX_DEPTH));self.assertFalse(ar.pattern_accepted('(?:'*(ar.MAX_DEPTH+1)+'a'+')'*(ar.MAX_DEPTH+1)))
 def test_quantifier_bounds_follow_java(self):
  for p in ('a{2147483647}','a{0,2147483647}','a{2147483647,}'):self.assertTrue(ar.pattern_accepted(p),p)
  # Java Pattern.compile: "Illegal repetition range" above Integer.MAX_VALUE; Python's re alone would accept the first and fourth and raise OverflowError on the others
  for p in ('a{2147483648}','a{4294967296}','a{99999999999999999999}','a{1,2147483648}','a{2147483648,}','a{1,99999999999999999999}','a{99999999999999999999,1}'):self.assertFalse(ar.pattern_accepted(p),p)
 def test_leading_zeros_are_javas_value(self):
  # Bifrost does not parse {m}; Pattern.compile accumulates leading zeros, so 4,500 zeros before a 1 are a valid repetition of 1;
  # Python's int() and re would refuse more than 4,300 digits, so Tyr strips the zeros first (no new length cap: Open point 4)
  for p in ('a{0001}','a{00,0002}','a{'+'0'*4500+'1}','a{'+'0'*4500+'1,'+'0'*4500+'2}'):self.assertTrue(ar.pattern_accepted(p),p[:24])
  for p in ('a{'+'0'*4500+'1,0}','a{'+'9'*4500+'}'):self.assertFalse(ar.pattern_accepted(p),p[:24])   # inverted range; a bound no engine holds
 def test_profile_with_a_refused_pattern(self):self.assertRaisesRegex(ValueError,'attribution.binding-profile',ar.occupancy_profile,changed(lambda p:p['identity'].update(pattern='^[A-Z]+$')))
```

- [ ] **Step 5.2** Run: `python -B scripts/test_attribution_rule.py` -> `ModuleNotFoundError: No module named 'attribution_rule'` (the import line). Expected.
- [ ] **Step 5.3** Create `scripts/attribution_rule.py`:

```python
"""2.27 attribution rule: the forseti stage-1 rule that joins governed process members with MES occupancy per station and tool.

Tyr authors the rule and the occupancy binding profile it names and checks both before export with the codes Bifrost's
AttributionRules and OccupancyBindingProfile use (spec "Attribution rule (mapping contract 2.27.0)" and "Binding profiles").
Everything resolves inside the package: the ISA-95 hierarchy, the stations (paths that do not nest), the members (one mapping
each, named by the metric Muninn publishes and the semantic id of the leaf it maps), one Boolean activity member per equipment,
the profile carried by an evidence-artifact 1.1.0, the plc-stamped identity members and the temporal order. The first failure
stops the rule. Approval stays with Bifrost; whether format.schemaSha256 equals forseti's built-in schema is forseti's start-up
check (binding.schema-mismatch), not Tyr's or Bifrost's. No Bifrost or forseti code is read.
"""
import json,re
from semantic_lifecycle import require
import validate_contracts as vc
import logical_structures as ls
import equipment_hierarchy as eh
KIND='attribution-rule'
VERSION='2.27.0'
PROFILE='0.1.0'
PREFIX='occupancy-binding-'
MEDIA='application/vnd.forseti.occupancy-binding+json'
SCHEMA_ID='urn:forseti:schema:occupancy:1.0.0'
REASONS={'urn:epcglobal:cbv:er:did_not_occur','urn:epcglobal:cbv:er:incorrect_data'}
FIELDS={'profileVersion','topic','format','identity','enter','leave','correction','timestampBasis','sources'}
MAX_DEPTH=32
MAX_REPEAT=2147483647   # Java Pattern: a repetition bound above Integer.MAX_VALUE is "Illegal repetition range"; Python's re would accept up to 4294967295
DIGEST=re.compile('[0-9a-f]{64}')

def text(d,k):return isinstance(d,dict) and isinstance(d.get(k),str) and d[k]!=''
def names(d):return set(d) if isinstance(d,dict) else None
def strings(a,code):
 """A non-empty list of distinct non-empty strings."""
 require(isinstance(a,list) and len(a)>0,code);out=[]
 for x in a:require(isinstance(x,str) and x!='' and x not in out,code);out.append(x)
 return out
def digest_form(v):return isinstance(v,str) and DIGEST.fullmatch(v) is not None

def occupancy_profile(raw,code='attribution.binding-profile'):
 """Profile 0.1.0 from its bytes: exactly the nine fields, the constants, non-empty values, the reasons subset, the pattern subset.
 Read from the bytes as Bifrost's MappingJson reader reads them: a UTF-8 BOM is skipped (json.loads detects utf-8-sig on bytes),
 duplicate JSON keys are refused (vc.pairs), and any decoder failure, nesting past Python's recursion limit included, is the code."""
 try:b=json.loads(raw,object_pairs_hook=vc.pairs)
 except (UnicodeDecodeError,ValueError,RecursionError) as e:raise ValueError(code) from e
 require(names(b)==FIELDS and b['profileVersion']==PROFILE and text(b,'topic') and b['timestampBasis']=='eventTime',code)
 f,i,enter,leave,c=b['format'],b['identity'],b['enter'],b['leave'],b['correction']
 require(names(f)=={'schemaId','schemaSha256'} and f['schemaId']==SCHEMA_ID and digest_form(f['schemaSha256']),code)
 require(names(i)=={'scheme','pattern'} and i['scheme']=='mes-unit-id' and text(i,'pattern'),code)
 require(names(enter)=={'bizStep'} and text(enter,'bizStep') and names(leave)=={'bizStep'} and text(leave,'bizStep'),code)
 require(names(c)=={'errorDeclaration','reasons'} and c['errorDeclaration']=='reissue-same-event-id',code)
 reasons=strings(c['reasons'],code);strings(b['sources'],code)
 require(set(reasons)<=REASONS,code)
 require(pattern_accepted(i['pattern']),code)
 return b

class _Pattern:
 """Spec 225: literals, '.', bracket classes with ranges and negation, a backslash before a non-alphanumeric ASCII character, the
 quantifiers * + ? {m} {m,} {m,n}, alternation and non-capturing groups. Anchors, lookaround, backreferences, flags, named or
 capturing groups, shorthand, property or POSIX classes, lazy or possessive quantifiers, Java's '&&', a bare '{', nesting deeper
 than MAX_DEPTH, a repetition bound above MAX_REPEAT and any surrogate or supplementary character (one code point in Java, two
 code units in ECMA-262) are refused, as Bifrost's BindingPattern refuses them."""
 def __init__(s,p):s.s=p;s.i=0;s.depth=0;s.mark=0;s.out=[]
 def at(s,c):return s.i<len(s.s) and s.s[s.i]==c
 def alternation(s):
  s.sequence()
  while s.at('|'):s.i+=1;s.sequence()
 def sequence(s):
  while s.i<len(s.s) and not s.at('|') and not s.at(')'):s.atom();s.quantifier()
 def atom(s):
  c=s.s[s.i]
  if c=='(':
   require(s.s.startswith('(?:',s.i) and s.depth<MAX_DEPTH,'group');s.i+=3;s.depth+=1;s.alternation();s.depth-=1;require(s.at(')'),'group');s.i+=1
  elif c=='[':s.char_class()
  elif c=='\\':s.escape()
  elif c=='.':s.i+=1
  elif c in '^$)*+?{}|]':raise ValueError('meta')
  else:s.i+=1
 def escape(s):
  require(s.i+1<len(s.s),'escape');n=s.s[s.i+1];require(ord(n)<128 and not n.isalnum(),'escape');s.i+=2
 def char_class(s):
  s.i+=1
  if s.at('^'):s.i+=1
  require(not s.at(']'),'class')
  while not s.at(']'):
   require(s.i<len(s.s),'class');s.class_char()
   if s.at('-') and s.i+1<len(s.s) and s.s[s.i+1]!=']':s.i+=1;s.class_char()
  s.i+=1
 def class_char(s):
  c=s.s[s.i]
  if c=='\\':s.escape()
  else:require(c!='[' and c!=']' and not (c=='&' and s.i+1<len(s.s) and s.s[s.i+1]=='&'),'class');s.i+=1
 def quantifier(s):
  if s.i>=len(s.s):return
  c=s.s[s.i]
  if c in '*+?':s.i+=1
  elif c=='{':
   close=s.s.find('}',s.i);require(close>s.i,'quantifier');q=s.s[s.i+1:close]
   require(re.fullmatch('[0-9]+|[0-9]+,|[0-9]+,[0-9]+',q) is not None,'quantifier')
   # Java accumulates leading zeros ({000...01} is 1) and Python's int() refuses more than 4,300 digits: strip them first, then
   # bound as Pattern.compile does (above Integer.MAX_VALUE: Illegal repetition range) and compile the normalised text later
   parts=[(x.lstrip('0') or '0') if x else '' for x in q.split(',')];bounds=[int(x) for x in parts if x]
   require(all(b<=MAX_REPEAT for b in bounds) and bounds[0]<=bounds[-1],'quantifier')
   s.out.append(s.s[s.mark:s.i]+'{'+','.join(parts)+'}');s.i=close+1;s.mark=s.i
  else:return
  require(not (s.at('?') or s.at('+') or s.at('*') or s.at('{')),'quantifier')
 def normalised(s):
  """The pattern with every quantifier's leading zeros stripped: what Python's re is asked to compile (same syntax, Java's values)."""
  return ''.join(s.out)+s.s[s.mark:]

def pattern_accepted(p):
 """True when p is inside the subset and compiles; Python's re is a syntax check here, the job's engine is Java's."""
 if not isinstance(p,str) or p=='':return False
 if any(0xD800<=ord(c)<=0xDFFF or ord(c)>0xFFFF for c in p):return False
 b=_Pattern(p)
 try:
  b.alternation()
  if b.i!=len(p):return False
  re.compile(b.normalised());return True
 except (ValueError,re.error,OverflowError):return False
```

- [ ] **Step 5.4** Run: `python -B scripts/test_attribution_rule.py OccupancyProfile Pattern` -> `Ran 17 tests ... OK`; whole module -> `Ran 25 tests ... OK` (Contract 2, StringSource 6, OccupancyProfile 10, Pattern 7; `Contract`'s two tests do not use `ar` on purpose, so the module imported before this task).
- [ ] **Step 5.5** Commit: `feat(attribution-rule): read the occupancy binding profile 0.1.0`.

### Task 6: `scripts/impact_rule.py`, part 1: the incident binding profile

**Files:**
- Create: `scripts/impact_rule.py` (constants, `incident_profile`; `validate` comes in Task 9)
- Create: `scripts/test_impact_rule.py` (module header and class `IncidentProfile`)

Spec lines 217-224; Bifrost `IncidentBindingProfile.java`.

- [ ] **Step 6.1** Create `scripts/test_impact_rule.py`:

```python
"""2.27 impact rule: the incident binding profile, every impact.* refusal, closure with the attribution rule."""
import sys,copy,json,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication,attribution_rule as ar,impact_rule as ir
from test_attribution_rule import load,w,package,publish,repinned,SETS
PROFILE={'profileVersion':'0.1.0','topic':'mfg.incidents','format':{'schemaId':'urn:forseti:schema:incident:1.0.0','schemaSha256':'0'*63+'2'},'kinds':['tool-check-failed','gauge-drift'],'equipmentRefBasis':'isa95-path'}
def raw(profile):return (json.dumps(profile,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def changed(f):
 p=copy.deepcopy(PROFILE);f(p);return raw(p)
def impacted(f,state=None):
 state=w() if state is None else state;f(state['impactRules'][0]);return state
class IncidentProfile(unittest.TestCase):
 """Spec 217-224 read with Tyr's own parser at the strictness of Bifrost's IncidentBindingProfile."""
 def test_accepted(self):self.assertEqual(ir.incident_profile(raw(PROFILE))['kinds'],['tool-check-failed','gauge-drift'])
 def refused(self,raw_bytes,code='impact.binding-profile'):self.assertRaisesRegex(ValueError,code,ir.incident_profile,raw_bytes)
 def test_field_set(self):
  self.refused(changed(lambda p:p.update(note='x')));self.refused(changed(lambda p:p.pop('kinds')));self.refused(b'not json');self.refused(b'null');self.refused(changed(lambda p:p['format'].update(extra=1)))
 def test_constants_and_empty_values(self):
  self.refused(changed(lambda p:p.update(profileVersion='0.2.0')));self.refused(changed(lambda p:p.update(topic='')));self.refused(changed(lambda p:p.update(equipmentRefBasis='sparkplug-device')))
  self.refused(changed(lambda p:p['format'].update(schemaId='urn:forseti:schema:occupancy:1.0.0')))
 def test_digest_form(self):
  self.refused(changed(lambda p:p['format'].update(schemaSha256='0'*63)));self.refused(changed(lambda p:p['format'].update(schemaSha256='G'*64)));self.refused(changed(lambda p:p['format'].update(schemaSha256=2)))
 def test_kinds(self):
  self.refused(changed(lambda p:p.update(kinds=[])));self.refused(changed(lambda p:p.update(kinds=['gauge-drift','gauge-drift'])));self.refused(changed(lambda p:p.update(kinds=['gauge-drift',''])));self.refused(changed(lambda p:p.update(kinds='gauge-drift')))
  ir.incident_profile(changed(lambda p:p.update(kinds=['any-name-the-job-may-refuse-later'])))   # spec 224: Bifrost checks distinct non-empty names only
 def test_other_code_is_the_callers(self):self.assertRaisesRegex(ValueError,'incident-binding.profile',ir.incident_profile,b'{}','incident-binding.profile')
 def test_duplicate_json_keys_are_refused(self):   # Bifrost's MappingJson reads with STRICT_DUPLICATE_DETECTION
  self.refused(raw(PROFILE).replace(b'"topic": "mfg.incidents"',b'"topic": "ignored", "topic": "mfg.incidents"'))
 def test_utf8_bom_is_accepted_as_bifrost_accepts_it(self):self.assertEqual(ir.incident_profile(b'\xef\xbb\xbf'+raw(PROFILE))['topic'],'mfg.incidents')
 def test_deep_nesting_is_refused_not_a_crash(self):self.refused(b'['*10000+b'0'+b']'*10000);self.refused(b'['*1500+b'0'+b']'*1500)
if __name__=='__main__':unittest.main()
```

- [ ] **Step 6.2** Run: `python -B scripts/test_impact_rule.py` -> `ModuleNotFoundError: No module named 'impact_rule'`. Expected.
- [ ] **Step 6.3** Create `scripts/impact_rule.py`:

```python
"""2.27 impact rule: the forseti stage-2 rule that judges quality incidents against the visits an attribution rule of the same
package produces.

Tyr authors the rule and the incident binding profile it names and checks both before export with the codes Bifrost's
ImpactRules and IncidentBindingProfile use: the attribution rule resolves, every incident scope path is a hierarchy node that
is a station of that rule or below one, the profile is an evidence-artifact 1.1.0 Tyr can read, and work-record retention is
at least the attribution horizon. Whether the incident schema supports each kind is the job's check. Approval stays with Bifrost.
"""
import json
from semantic_lifecycle import require
import validate_contracts as vc
import attribution_rule as ar
KIND='impact-rule'
VERSION='2.27.0'
PROFILE='0.1.0'
PREFIX='incident-binding-'
MEDIA='application/vnd.forseti.incident-binding+json'
SCHEMA_ID='urn:forseti:schema:incident:1.0.0'
FIELDS={'profileVersion','topic','format','kinds','equipmentRefBasis'}

def incident_profile(raw,code='impact.binding-profile'):
 """Profile 0.1.0 from its bytes: exactly the five fields, the constants, a non-empty topic, distinct non-empty kinds. Read as
 Bifrost's reader reads it: a UTF-8 BOM is skipped, duplicate keys and any decoder failure (deep nesting included) are the code."""
 try:b=json.loads(raw,object_pairs_hook=vc.pairs)
 except (UnicodeDecodeError,ValueError,RecursionError) as e:raise ValueError(code) from e
 require(ar.names(b)==FIELDS and b['profileVersion']==PROFILE and ar.text(b,'topic') and b['equipmentRefBasis']=='isa95-path',code)
 f=b['format'];require(ar.names(f)=={'schemaId','schemaSha256'} and f['schemaId']==SCHEMA_ID and ar.digest_form(f['schemaSha256']),code)
 ar.strings(b['kinds'],code)
 return b
```

- [ ] **Step 6.4** Run: `python -B scripts/test_impact_rule.py` -> `Ran 9 tests ... OK`.
- [ ] **Step 6.5** Commit: `feat(impact-rule): read the incident binding profile 0.1.0`.

### Task 7: Authored binding profiles as workspace records and evidence-artifact files

**Files:**
- Create: `editor-contracts/1.0.0/occupancy-binding.schema.json`, `editor-contracts/1.0.0/incident-binding.schema.json`
- Create: `backend/binding_profiles.py`
- Modify: `backend/workspace_v2.py` (line 91 key set; `check` after the `serverCertificates` block; `build` after line 62), `backend/server.py` (line 239: transition)
- Modify: `scripts/test_attribution_rule.py` (import line; class `BindingProfiles`)

Decision 4 (spec 41-44): profiles are the file of an evidence-artifact 1.1.0 in the bundle; spec 194-199: id prefix, `file.mediaType`, `scope` = station ids (equipment instance ids). Precedent: `hierarchy_evidence.py` (a Tyr-side artifact with a data file; record fields incl. `reviewer`), `server_certificates.py` (`scope` checked against workspace equipment), and the `<name>.{limit,schema,duplicate,scope,version-required}` code family; `Store.save` runs each module's `transition` (`server.py` 237-239).

- [ ] **Step 7.1** The import line of `scripts/test_attribution_rule.py` becomes `import server,publication,binding_profiles as bp,attribution_rule as ar,impact_rule as ir`; add (this class builds on the command-binding workspace, so it runs before the fixture of Task 8 exists):

```python
def record(profile,id='line2',scope=('mixer1','mixer2'),version='1.0.0'):
 return {'id':id,'version':version,'label':'Line 2 binding','origin':'synthetic','capturedAt':'2026-11-07T00:00:00Z','reviewer':'fixture-reviewer','product':None,'scope':list(scope),'profile':copy.deepcopy(profile)}
class BindingProfiles(unittest.TestCase):
 """Authored profiles: a workspace record whose profile object Tyr serializes; the artifact wrapper pins those bytes."""
 def base(self):
  state=load('fixtures/command-binding/workspace.json');del state['commandBindings'],state['readBindings'],state['serverCertificates']
  state['occupancyBindings']=[record(PROFILE)];state['incidentBindings']=[record({'profileVersion':'0.1.0','topic':'mfg.incidents','format':{'schemaId':'urn:forseti:schema:incident:1.0.0','schemaSha256':'0'*63+'2'},'kinds':['tool-check-failed'],'equipmentRefBasis':'isa95-path'})];return state
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_packaged_as_evidence_artifacts_with_the_spec_prefix_and_media_type(self):
  state=self.base();server.check_state(state)
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=package(state,root)
   for prefix,media,data in ((ar.PREFIX,ar.MEDIA,'data/occupancy-binding-0.json'),(ir.PREFIX,ir.MEDIA,'data/incident-binding-0.json')):
    art=next(load(root/e['path']) for e in p['files'] if e['id']==prefix+'line2')
    self.assertEqual((art['schemaVersion'],art['file']['path'],art['file']['mediaType'],art['scope'],art['origin']),('1.1.0',data,media,['mixer1','mixer2'],'synthetic'))
    self.assertEqual(art['file']['sha256'],server.contracts.hashed(root/data))
   self.assertEqual((root/'data/occupancy-binding-0.json').read_bytes(),raw(PROFILE))   # vc.save bytes: indent 2, LF, final newline
   self.assertEqual(p['schemaVersion'],'2.23.0')   # a profile alone is an evidence artifact and raises no envelope: base() dropped the links, so the hierarchy's 2.23.0 (workspace_v2.build lines 63-68) stands
 def test_record_refusals(self):
  self.refused(profiled(lambda r:r.update(note='x'),state=self.base()),'occupancy-binding.schema')
  self.refused(profiled(lambda r:r.update(scope=[]),state=self.base()),'occupancy-binding.schema')
  self.refused(profiled(lambda r:r.update(scope=['mixer9']),state=self.base()),'occupancy-binding.scope')
  state=self.base();state['occupancyBindings'].append(record(PROFILE));self.refused(state,'occupancy-binding.duplicate')
  state=self.base();state['incidentBindings'].append(record(state['incidentBindings'][0]['profile']));self.refused(state,'incident-binding.duplicate')
  self.refused(profiled(lambda r:r['profile'].update(timestampBasis='recordTime'),state=self.base()),'attribution.binding-profile')
  self.refused(profiled(lambda r:r['profile']['identity'].update(pattern='^A$'),state=self.base()),'attribution.binding-profile')
  self.refused(profiled(lambda r:r['profile'].update(kinds=[]),'incidentBindings',self.base()),'impact.binding-profile')
  state=self.base();state['occupancyBindings']='x';self.refused(state,'occupancy-binding.limit')
 def test_changed_profile_needs_a_new_version(self):
  before=self.base();after=profiled(lambda r:r['profile'].update(topic='mfg.occupancy.v2'),state=self.base())
  self.assertRaisesRegex(ValueError,'occupancy-binding.version-required',bp.transition,before,after)
  after['occupancyBindings'][0]['version']='1.1.0';bp.transition(before,after)
  after=profiled(lambda r:r.update(scope=['mixer1']),'incidentBindings',self.base());self.assertRaisesRegex(ValueError,'incident-binding.version-required',bp.transition,before,after)
 def test_without_profiles_unchanged(self):
  state=self.base();del state['occupancyBindings'],state['incidentBindings'];server.check_state(state)
  with tempfile.TemporaryDirectory() as t:self.assertFalse(any(e['id'].startswith((ar.PREFIX,ir.PREFIX)) for e in package(state,Path(t))['files']))
```

- [ ] **Step 7.2** Run: `python -B scripts/test_attribution_rule.py` -> `ModuleNotFoundError: No module named 'binding_profiles'`. Expected.
- [ ] **Step 7.3** Create `editor-contracts/1.0.0/occupancy-binding.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:tyr:editor:occupancy-binding:1.0.0",
  "description": "An authored forseti occupancy binding profile (0.1.0): Tyr serializes 'profile' as the data file of an evidence-artifact with id 'occupancy-binding-' + id and media type application/vnd.forseti.occupancy-binding+json. The profile's own fields are checked by scripts/attribution_rule.py at the strictness of Bifrost's reader.",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9._-]{0,63}$"
    },
    "version": {
      "$ref": "#/$defs/version"
    },
    "label": {
      "type": "string",
      "minLength": 1,
      "maxLength": 256
    },
    "origin": {
      "enum": [
        "synthetic",
        "field"
      ]
    },
    "capturedAt": {
      "type": "string",
      "format": "date-time"
    },
    "reviewer": {
      "type": "string",
      "minLength": 1,
      "maxLength": 128
    },
    "product": {
      "anyOf": [
        {
          "type": "null"
        },
        {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "minLength": 1,
              "maxLength": 256
            },
            "version": {
              "type": "string",
              "minLength": 1,
              "maxLength": 64
            }
          },
          "required": [
            "name",
            "version"
          ],
          "additionalProperties": false
        }
      ]
    },
    "scope": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[a-z][a-z0-9._/-]*$",
        "maxLength": 256
      },
      "minItems": 1,
      "maxItems": 2048,
      "uniqueItems": true
    },
    "profile": {
      "type": "object"
    }
  },
  "required": [
    "id",
    "version",
    "label",
    "origin",
    "capturedAt",
    "reviewer",
    "product",
    "scope",
    "profile"
  ],
  "additionalProperties": false,
  "$defs": {
    "version": {
      "type": "string",
      "pattern": "^(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)$"
    }
  }
}
```
`editor-contracts/1.0.0/incident-binding.schema.json` is the same file with `$id` `urn:tyr:editor:incident-binding:1.0.0` and the description naming `incident-binding-`, `application/vnd.forseti.incident-binding+json` and `scripts/impact_rule.py`. (The `profile` object is `type: object` on purpose: the field rules live in one place, the parser, so the editor schema cannot drift from Bifrost's reader.)

- [ ] **Step 7.4** Create `backend/binding_profiles.py`:

```python
"""Authored forseti binding profiles: occupancy-binding and incident-binding 0.1.0, shipped as evidence-artifact 1.1.0 files.

Unlike read bindings and server certificates, these bytes are Tyr's own output: the workspace record holds the profile object,
vc.save writes it as the artifact's data file, and the wrapper pins the SHA-256 of those bytes. Bifrost re-reads the file with its
own parser (OccupancyBindingProfile, IncidentBindingProfile); Tyr's parsers run on the same bytes here and at package validation.
scope lists the stations the profile covers, as equipment instance ids (spec "Binding profiles"); Bifrost does not compare it
with a rule's stations, Tyr requires it to name workspace equipment.
"""
import json
from jsonschema import Draft202012Validator,FormatChecker
import validate_contracts as vc
import attribution_rule as ar
import impact_rule as ir
SECTIONS={'occupancyBindings':('occupancy-binding',ar.PREFIX,ar.MEDIA,ar.occupancy_profile,'attribution.binding-profile'),
          'incidentBindings':('incident-binding',ir.PREFIX,ir.MEDIA,ir.incident_profile,'impact.binding-profile')}
VALIDATORS={k:Draft202012Validator(vc.load(vc.ROOT/'editor-contracts/1.0.0'/(v[0]+'.schema.json')),format_checker=FormatChecker()) for k,v in SECTIONS.items()}
LIMIT=64
def require(ok,code):
    if not ok:raise ValueError(code)
def bytes_of(r):
    """The data file bytes: what vc.save writes (indent 2, ensure_ascii False, LF, final newline)."""
    return (json.dumps(r['profile'],ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def check(w,equipment):
    for section,(name,prefix,media,parse,code) in SECTIONS.items():
        docs=w.get(section,[])
        require(isinstance(docs,list) and len(docs)<=LIMIT,name+'.limit')
        ids=set()
        for r in docs:
            require(not list(VALIDATORS[section].iter_errors(r)),name+'.schema')
            require(r['id'] not in ids,name+'.duplicate');ids.add(r['id'])
            parse(bytes_of(r),code)   # the spec's code, as Bifrost will report it on the same bytes
            require(set(r['scope'])<=set(equipment),name+'.scope')
def transition(before,after):
    for section,(name,*_) in SECTIONS.items():
        new={r['id']:r for r in after.get(section,[])}
        for r in before.get(section,[]):
            n=new.get(r['id'])
            if n is not None and n!=r:require(n['version']!=r['version'],name+'.version-required')
def build(w,folder,proposal):
    for section,(name,prefix,media,parse,code) in SECTIONS.items():
        docs=w.get(section,[])
        if not docs:continue
        (folder/'data').mkdir(exist_ok=True);(folder/'evidence').mkdir(exist_ok=True)
        for i,r in enumerate(docs):
            path='data/'+name+'-'+str(i)+'.json';vc.save(folder/path,r['profile'])
            art={'kind':'evidence-artifact','schemaVersion':'1.1.0','id':prefix+r['id'],'version':r['version'],'origin':r['origin'],'file':{'path':path,'sha256':vc.hashed(folder/path),'mediaType':media},'capturedAt':r['capturedAt'],'product':r['product'],'scope':list(r['scope'])}
            rel='evidence/'+name+'-'+str(i)+'.json';vc.save(folder/rel,art)
            proposal['files'].append({'path':rel,'kind':art['kind'],'id':art['id'],'version':art['version'],'sha256':vc.hashed(folder/rel)})
```

- [ ] **Step 7.5** `backend/workspace_v2.py`:
  - line 91: add `"occupancyBindings","incidentBindings","attributionRules","impactRules"` to the allowed-keys set (the rule sections are allowed now and checked in Task 8);
  - `check`, after the `serverCertificates` block (line 150):

```python
    if "occupancyBindings" in state or "incidentBindings" in state:
        import binding_profiles
        binding_profiles.check(state,equip)
```
  - `build`, after `server_certificates.build(state,folder,p)` (line 62):

```python
    import binding_profiles
    binding_profiles.build(state,folder,p)
```

- [ ] **Step 7.6** `backend/server.py` line 239, after the `server_certificates` transition: `__import__("binding_profiles").transition(json.loads(current_body),state)`.
- [ ] **Step 7.7** Run: `python -B scripts/test_attribution_rule.py BindingProfiles` -> `Ran 4 tests ... OK`; whole module -> `Ran 29 tests ... OK` (Contract 2, StringSource 6, OccupancyProfile 10, Pattern 7, BindingProfiles 4). `python -B scripts/test_impact_rule.py` -> 9 OK. `python -B scripts/test_command_binding.py` -> 52 OK; `python -B scripts/test_equipment_hierarchy.py` -> OK (the key set change admits nothing that was there before).
- [ ] **Step 7.8** Commit: `feat(binding-profiles): author occupancy and incident binding profiles as evidence artifacts`.

## Chunk 3: The `occupancy-join` fixture workspace and the attribution validator

### Task 8: `fixtures/attribution-rule/workspace.json`, `attribution_rule.validate`, the rule sections of the workspace

**Files:**
- Create: `fixtures/attribution-rule/workspace.json`
- Modify: `scripts/attribution_rule.py` (helpers and `validate`; the `plc-stamped` identity block comes in Task 11)
- Modify: `backend/workspace_v2.py` (`check`: rule sections; `build`: `attribution-rules/`, `impact-rules/`, proposal 2.27.0)
- Modify: `scripts/p3a_contracts.py` (imports, hierarchy gate flag, validator call)
- Modify: `scripts/test_attribution_rule.py` (class `AttributionRule`)

The workspace is the Tyr authoring of Bifrost's `attribution-impact` fixture: the same plant, members, profiles and rules, written the way Tyr writes them (source evidence is one `manual-<sourceId>` artifact per source, line 1; hierarchy evidence is the plant register CSV; profiles are authored records). Equipment: `synthetic-site` (SITE_1) > `line2` (PRODUCTIONLINE_5) > `station1`, `station2` (WORKCELL_6); `nutrunner1`, `nutrunner2` (WORKUNIT_11, decided; spec PR of Task 1) under `station1`. OPC UA node identifiers are the step-4 sim names (`Line2/Station1.Running`, `Line2/Station1/Nutrunner1.Torque`, ...), namespace `urn:bifrost:opcua:sim`. Equipment ids are slash-free (Open point 3). Stream `line2`.

- [ ] **Step 8.1** Create `fixtures/attribution-rule/workspace.json`. Top-level shape and the complete documents follow; `capturedAt` is `2026-11-07T00:00:00Z` everywhere.

```json
{
  "workspaceVersion": "2.0.0",
  "equipment": [
    {"id": "synthetic-site", "label": "Synthetic site"},
    {"id": "line2", "label": "Line 2"},
    {"id": "station1", "label": "Station 1"},
    {"id": "station2", "label": "Station 2"},
    {"id": "nutrunner1", "label": "Nutrunner 1"},
    {"id": "nutrunner2", "label": "Nutrunner 2"}
  ],
  "connections": [
    {"id": "sim-opcua-station1", "label": "Bifrost OPC-UA sim", "equipmentInstanceId": "station1", "accessProfileRef": "s7-1500-opcua-v1"},
    {"id": "sim-opcua-station2", "label": "Bifrost OPC-UA sim", "equipmentInstanceId": "station2", "accessProfileRef": "s7-1500-opcua-v1"},
    {"id": "sim-opcua-nutrunner1", "label": "Bifrost OPC-UA sim", "equipmentInstanceId": "nutrunner1", "accessProfileRef": "s7-1500-opcua-v1"},
    {"id": "sim-opcua-nutrunner2", "label": "Bifrost OPC-UA sim", "equipmentInstanceId": "nutrunner2", "accessProfileRef": "s7-1500-opcua-v1"}
  ],
  "sources": ["... six records, see the table ..."],
  "semantics": ["... station-model, tool-model ..."],
  "targets": ["... station1, station2, nutrunner1, nutrunner2 ..."],
  "graphs": [],
  "mappings": ["... station1-mapping, station2-mapping, nutrunner1-mapping, nutrunner2-mapping ..."],
  "equipmentHierarchies": ["... line2-plant ..."],
  "hierarchyEvidence": ["... plant-register ..."],
  "occupancyBindings": ["... line2 ..."],
  "incidentBindings": ["... line2 ..."],
  "attributionRules": ["... line2-attribution ..."],
  "impactRules": ["... line2-impact ..."]
}
```

Source record (first of six, complete; the five others differ only in the table's columns; every record has the key set `definition`, `label`, `note`, `origin`, `capturedAt`, the shape the PLC form writes):

```json
{
  "definition": {
    "kind": "source-definition", "schemaVersion": "2.7.0", "id": "station1-running", "version": "1.0.0",
    "equipmentInstanceId": "station1", "connectionProfileRef": "sim-opcua-station1", "accessProfileRef": "s7-1500-opcua-v1", "status": "ready",
    "rawAddressText": "nsu=urn:bifrost:opcua:sim;s=Line2/Station1.Running", "addressRadix": null,
    "access": {"kind": "opcua-node", "namespaceUri": "urn:bifrost:opcua:sim", "identifierType": "string", "identifier": "Line2/Station1.Running"},
    "rawRepresentation": {"mode": "typed", "valueType": "Boolean"}, "inputStage": "already-engineered", "unit": {"status": "not-applicable"},
    "evidenceRefs": [{"artifactId": "manual-station1-running", "locator": {"kind": "text-line", "line": 1}}],
    "viewOf": null, "sourceKind": "plc", "accessMode": "read"
  },
  "label": "station1-running",
  "note": "Station1 running: nsu=urn:bifrost:opcua:sim;s=Line2/Station1.Running, Boolean",
  "origin": "synthetic",
  "capturedAt": "2026-11-07T00:00:00Z"
}
```

| `id` (= `label`) | `equipmentInstanceId` | `connectionProfileRef` | `identifier` (`rawAddressText` = `nsu=urn:bifrost:opcua:sim;s=` + identifier) | `valueType` | `unit` | `note` |
|---|---|---|---|---|---|---|
| `station1-running` | `station1` | `sim-opcua-station1` | `Line2/Station1.Running` | `Boolean` | `{"status":"not-applicable"}` | `Station1 running: <rawAddressText>, Boolean` |
| `station2-running` | `station2` | `sim-opcua-station2` | `Line2/Station2.Running` | `Boolean` | not-applicable | `Station2 running: <rawAddressText>, Boolean` |
| `nutrunner1-torque` | `nutrunner1` | `sim-opcua-nutrunner1` | `Line2/Station1/Nutrunner1.Torque` | `Float64` | `{"status":"known","code":"N.m"}` | `Nutrunner1 torque: <rawAddressText>, Double, N.m` |
| `nutrunner1-running` | `nutrunner1` | `sim-opcua-nutrunner1` | `Line2/Station1/Nutrunner1.Running` | `Boolean` | not-applicable | `Nutrunner1 running: <rawAddressText>, Boolean` |
| `nutrunner2-torque` | `nutrunner2` | `sim-opcua-nutrunner2` | `Line2/Station1/Nutrunner2.Torque` | `Float64` | known `N.m` | `Nutrunner2 torque: <rawAddressText>, Double, N.m` |
| `nutrunner2-running` | `nutrunner2` | `sim-opcua-nutrunner2` | `Line2/Station1/Nutrunner2.Running` | `Boolean` | not-applicable | `Nutrunner2 running: <rawAddressText>, Boolean` |

(`Float64` is the typed source value type of the 2.x common schema; `Double` exists only as a semantic result type and as the `cast` target, as in Bifrost's fixtures.) Each `evidenceRefs` is `[{"artifactId": "manual-<id>", "locator": {"kind": "text-line", "line": 1}}]` (Tyr's legacy check requires exactly this).

Semantic definitions (complete):

```json
{"kind": "semantic-definition", "schemaVersion": "2.12.0", "id": "station-model", "version": "1.0.0", "members": [
  {"memberId": "running", "name": "Running", "semanticId": "urn:bifrost:sem:Station/Running", "description": "Station is working", "valueType": "Boolean", "unit": {"status": "not-applicable"}, "role": "status", "range": null}
]}
```
```json
{"kind": "semantic-definition", "schemaVersion": "2.12.0", "id": "tool-model", "version": "1.0.0", "members": [
  {"memberId": "torque", "name": "Torque", "semanticId": "urn:bifrost:sem:Tool/Torque", "description": "Tightening torque", "valueType": "Double", "unit": {"status": "known", "code": "N.m"}, "role": "measurement", "range": {"low": "0", "high": "100"}},
  {"memberId": "running", "name": "Running", "semanticId": "urn:bifrost:sem:Tool/Running", "description": "Tool is working", "valueType": "Boolean", "unit": {"status": "not-applicable"}, "role": "status", "range": null}
]}
```
(`station-model` and `tool-model` both carry a leaf named `Running`: spec line 132 allows it across definitions because Sparkplug metric names are scoped to one device; `semanticId`s differ, so `semantic.identity-conflict` does not fire.)

Target instances (first complete; `station2` cites `manual-station2-running`, `nutrunner1`/`nutrunner2` use `tool-model` and cite `manual-nutrunner<n>-torque`):

```json
{"kind": "target-instance", "schemaVersion": "2.0.0", "id": "station1", "version": "1.0.0", "equipmentInstanceId": "station1", "label": "Station 1",
 "semanticDefinitionRef": {"id": "station-model", "version": "1.0.0"},
 "evidenceRefs": [{"artifactId": "manual-station1-running", "locator": {"kind": "text-line", "line": 1}}]}
```

Mapping sets (`station1-mapping` and `nutrunner1-mapping` complete; `station2-mapping` and `nutrunner2-mapping` are the same with `1` -> `2` in ids, equipment, target and source references; `mappingId`s equal the source ids):

```json
{"kind": "mapping-set", "schemaVersion": "2.12.0", "id": "station1-mapping", "version": "1.0.0", "equipmentInstanceId": "station1",
 "targetInstanceRef": {"id": "station1", "version": "1.0.0"},
 "mappings": [
  {"mappingId": "station1-running", "valueRef": {"kind": "source", "sourceRef": {"id": "station1-running", "version": "1.0.0"}},
   "memberPath": [{"kind": "member", "memberId": "running"}], "transform": [], "outputUnit": {"status": "not-applicable"}, "invalidValuePolicy": "bad-quality",
   "evidenceRefs": [{"artifactId": "manual-station1-running", "locator": {"kind": "text-line", "line": 1}}],
   "temporalPolicy": {"timestampBasis": "source", "maxAgeMs": 5000, "maxSkewMs": 0, "uncertainInput": "reject", "missingInput": "reject", "badInput": "propagate", "assembly": "latest"}}
 ]}
```
```json
{"kind": "mapping-set", "schemaVersion": "2.12.0", "id": "nutrunner1-mapping", "version": "1.0.0", "equipmentInstanceId": "nutrunner1",
 "targetInstanceRef": {"id": "nutrunner1", "version": "1.0.0"},
 "mappings": [
  {"mappingId": "nutrunner1-torque", "valueRef": {"kind": "source", "sourceRef": {"id": "nutrunner1-torque", "version": "1.0.0"}},
   "memberPath": [{"kind": "member", "memberId": "torque"}],
   "transform": [{"op": "cast", "to": "Double", "rounding": "exact", "overflow": "error"}], "outputUnit": {"status": "known", "code": "N.m"}, "invalidValuePolicy": "bad-quality",
   "evidenceRefs": [{"artifactId": "manual-nutrunner1-torque", "locator": {"kind": "text-line", "line": 1}}],
   "temporalPolicy": {"timestampBasis": "source", "maxAgeMs": 5000, "maxSkewMs": 0, "uncertainInput": "reject", "missingInput": "reject", "badInput": "propagate", "assembly": "latest"}},
  {"mappingId": "nutrunner1-running", "valueRef": {"kind": "source", "sourceRef": {"id": "nutrunner1-running", "version": "1.0.0"}},
   "memberPath": [{"kind": "member", "memberId": "running"}], "transform": [], "outputUnit": {"status": "not-applicable"}, "invalidValuePolicy": "bad-quality",
   "evidenceRefs": [{"artifactId": "manual-nutrunner1-running", "locator": {"kind": "text-line", "line": 1}}],
   "temporalPolicy": {"timestampBasis": "source", "maxAgeMs": 5000, "maxSkewMs": 0, "uncertainInput": "reject", "missingInput": "reject", "badInput": "propagate", "assembly": "latest"}}
 ]}
```

Equipment hierarchy (complete; node evidence cites the register's data lines 2-7):

```json
{"kind": "equipment-hierarchy", "schemaVersion": "2.23.0", "id": "line2-plant", "version": "1.0.0", "label": "Synthetic plant, line 2",
 "levelVocabulary": "opc-10030-1.00-isa95-equipment-element-level-enum",
 "nodes": [
  {"equipmentInstanceId": "synthetic-site", "label": "Synthetic site", "equipmentLevel": "SITE_1", "parentEquipmentInstanceId": null, "evidenceRefs": [{"artifactId": "hierarchy-plant-register", "locator": {"kind": "text-line", "line": 2}}]},
  {"equipmentInstanceId": "line2", "label": "Line 2", "equipmentLevel": "PRODUCTIONLINE_5", "parentEquipmentInstanceId": "synthetic-site", "evidenceRefs": [{"artifactId": "hierarchy-plant-register", "locator": {"kind": "text-line", "line": 3}}]},
  {"equipmentInstanceId": "station1", "label": "Station 1", "equipmentLevel": "WORKCELL_6", "parentEquipmentInstanceId": "line2", "evidenceRefs": [{"artifactId": "hierarchy-plant-register", "locator": {"kind": "text-line", "line": 4}}]},
  {"equipmentInstanceId": "station2", "label": "Station 2", "equipmentLevel": "WORKCELL_6", "parentEquipmentInstanceId": "line2", "evidenceRefs": [{"artifactId": "hierarchy-plant-register", "locator": {"kind": "text-line", "line": 5}}]},
  {"equipmentInstanceId": "nutrunner1", "label": "Nutrunner 1", "equipmentLevel": "WORKUNIT_11", "parentEquipmentInstanceId": "station1", "evidenceRefs": [{"artifactId": "hierarchy-plant-register", "locator": {"kind": "text-line", "line": 6}}]},
  {"equipmentInstanceId": "nutrunner2", "label": "Nutrunner 2", "equipmentLevel": "WORKUNIT_11", "parentEquipmentInstanceId": "station1", "evidenceRefs": [{"artifactId": "hierarchy-plant-register", "locator": {"kind": "text-line", "line": 7}}]}
 ],
 "evidenceRefs": []}
```

Hierarchy evidence record (the CSV is byte-identical to Bifrost's `attribution-impact/data/hierarchy-0.csv`, 7 LF lines; the base64 and digest below were computed from those bytes):

```json
{"id": "plant-register", "version": "1.0.0", "label": "Synthetic plant register, line 2", "format": "csv",
 "bytesBase64": "ZXF1aXBtZW50SW5zdGFuY2VJZCxsYWJlbCxlcXVpcG1lbnRMZXZlbCxwYXJlbnQKc3ludGhldGljLXNpdGUsU3ludGhldGljIHNpdGUsU0lURV8xLApsaW5lMixMaW5lIDIsUFJPRFVDVElPTkxJTkVfNSxzeW50aGV0aWMtc2l0ZQpzdGF0aW9uMSxTdGF0aW9uIDEsV09SS0NFTExfNixsaW5lMgpzdGF0aW9uMixTdGF0aW9uIDIsV09SS0NFTExfNixsaW5lMgpudXRydW5uZXIxLE51dHJ1bm5lciAxLFdPUktVTklUXzExLHN0YXRpb24xCm51dHJ1bm5lcjIsTnV0cnVubmVyIDIsV09SS1VOSVRfMTEsc3RhdGlvbjEK",
 "sha256": "afb8a6ddc0e9a8eb8c703ba83bb354b66259b904c86e07666a343822035b3aa3",
 "origin": "synthetic", "capturedAt": "2026-11-07T00:00:00Z", "reviewer": "fixture-reviewer", "product": null,
 "scope": ["synthetic-site", "line2", "station1", "station2", "nutrunner1", "nutrunner2"]}
```
(CSV text: `equipmentInstanceId,label,equipmentLevel,parent` / `synthetic-site,Synthetic site,SITE_1,` / `line2,Line 2,PRODUCTIONLINE_5,synthetic-site` / `station1,Station 1,WORKCELL_6,line2` / `station2,Station 2,WORKCELL_6,line2` / `nutrunner1,Nutrunner 1,WORKUNIT_11,station1` / `nutrunner2,Nutrunner 2,WORKUNIT_11,station1`, each line LF-terminated. Verify: `python -I -c "import base64,hashlib,json;r=json.load(open('fixtures/attribution-rule/workspace.json',encoding='utf-8'))['hierarchyEvidence'][0];print(hashlib.sha256(base64.b64decode(r['bytesBase64'])).hexdigest()==r['sha256'])"` prints `True`.)

Binding profile records (complete; `schemaSha256` are the step-1 placeholders, Open point 5):

```json
{"id": "line2", "version": "1.0.0", "label": "Line 2 MES occupancy", "origin": "synthetic", "capturedAt": "2026-11-07T00:00:00Z", "reviewer": "fixture-reviewer", "product": null,
 "scope": ["station1", "station2"],
 "profile": {
  "profileVersion": "0.1.0", "topic": "mfg.occupancy",
  "format": {"schemaId": "urn:forseti:schema:occupancy:1.0.0", "schemaSha256": "0000000000000000000000000000000000000000000000000000000000000001"},
  "identity": {"scheme": "mes-unit-id", "pattern": "[A-Z0-9]{17}"},
  "enter": {"bizStep": "urn:epcglobal:cbv:bizstep:arriving"}, "leave": {"bizStep": "urn:epcglobal:cbv:bizstep:departing"},
  "correction": {"errorDeclaration": "reissue-same-event-id", "reasons": ["urn:epcglobal:cbv:er:did_not_occur", "urn:epcglobal:cbv:er:incorrect_data"]},
  "timestampBasis": "eventTime", "sources": ["mes-line2"]}}
```
```json
{"id": "line2", "version": "1.0.0", "label": "Line 2 quality incidents", "origin": "synthetic", "capturedAt": "2026-11-07T00:00:00Z", "reviewer": "fixture-reviewer", "product": null,
 "scope": ["station1", "station2"],
 "profile": {
  "profileVersion": "0.1.0", "topic": "mfg.incidents",
  "format": {"schemaId": "urn:forseti:schema:incident:1.0.0", "schemaSha256": "0000000000000000000000000000000000000000000000000000000000000002"},
  "kinds": ["tool-check-failed", "gauge-drift"], "equipmentRefBasis": "isa95-path"}}
```

Attribution rule (complete; spec lines 119-140, the `occupancy-join` shape of Bifrost's fixture with Tyr's evidence):

```json
{"kind": "attribution-rule", "schemaVersion": "2.27.0", "id": "line2-attribution", "version": "1.0.0",
 "label": "Line 2 occupancy-join attribution",
 "description": "Joins nutrunner torque samples with MES occupancy at station 1 and station 2 by event time.",
 "equipmentRef": {"id": "line2-plant", "version": "1.0.0"},
 "stations": ["synthetic-site:line2:station1", "synthetic-site:line2:station2"],
 "members": [
  {"mappingSetRef": {"id": "nutrunner1-mapping", "version": "1.0.0"}, "mappingId": "nutrunner1-torque", "semanticId": "urn:bifrost:sem:Tool/Torque", "metric": "Torque"},
  {"mappingSetRef": {"id": "nutrunner2-mapping", "version": "1.0.0"}, "mappingId": "nutrunner2-torque", "semanticId": "urn:bifrost:sem:Tool/Torque", "metric": "Torque"},
  {"mappingSetRef": {"id": "station1-mapping", "version": "1.0.0"}, "mappingId": "station1-running", "semanticId": "urn:bifrost:sem:Station/Running", "metric": "Running"},
  {"mappingSetRef": {"id": "station2-mapping", "version": "1.0.0"}, "mappingId": "station2-running", "semanticId": "urn:bifrost:sem:Station/Running", "metric": "Running"},
  {"mappingSetRef": {"id": "nutrunner1-mapping", "version": "1.0.0"}, "mappingId": "nutrunner1-running", "semanticId": "urn:bifrost:sem:Tool/Running", "metric": "Running"},
  {"mappingSetRef": {"id": "nutrunner2-mapping", "version": "1.0.0"}, "mappingId": "nutrunner2-running", "semanticId": "urn:bifrost:sem:Tool/Running", "metric": "Running"}
 ],
 "activity": [
  {"equipmentPath": "synthetic-site:line2:station1", "memberRef": "station1-running", "activeWhen": true},
  {"equipmentPath": "synthetic-site:line2:station2", "memberRef": "station2-running", "activeWhen": true},
  {"equipmentPath": "synthetic-site:line2:station1:nutrunner1", "memberRef": "nutrunner1-running", "activeWhen": true},
  {"equipmentPath": "synthetic-site:line2:station1:nutrunner2", "memberRef": "nutrunner2-running", "activeWhen": true}
 ],
 "occupancyBindingRef": {"id": "occupancy-binding-line2", "version": "1.0.0"},
 "identity": {"mode": "occupancy-join", "crossCheck": "none"},
 "temporal": {"timestampBasis": "source", "outOfOrdernessMs": 30000, "allowedLatenessMs": 720000, "horizonMs": 86400000, "enterToleranceMs": 45000, "leaveToleranceMs": 45000},
 "quality": {"uncertainInput": "reject", "maxBadShare": 0.1},
 "coverage": {"expectedPeriodMs": 1000, "maxMissingPeriods": 3},
 "overlap": {"policy": "reject-ambiguous"},
 "evidenceRefs": [{"artifactId": "manual-nutrunner1-torque", "locator": {"kind": "text-line", "line": 1}}]}
```

Impact rule (complete; spec lines 156-173):

```json
{"kind": "impact-rule", "schemaVersion": "2.27.0", "id": "line2-impact", "version": "1.0.0",
 "label": "Line 2 tool incident impact",
 "description": "Marks visits in which a nutrunner shows activity inside an incident's suspect interval.",
 "attributionRuleRef": {"id": "line2-attribution", "version": "1.0.0"},
 "incidentScope": ["synthetic-site:line2:station1:nutrunner1", "synthetic-site:line2:station1:nutrunner2"],
 "incidentBindingRef": {"id": "incident-binding-line2", "version": "1.0.0"},
 "interval": {"start": "suspectFrom", "overlap": "any-overlap", "openEnd": "provisional-until-closed"},
 "evidence": {"match": "equipment-evidence", "onBasisRetracted": "by-cause", "onWithdrawn": "not-affected"},
 "retention": {"workRecordsMs": 604800000},
 "evidenceRefs": [{"artifactId": "manual-nutrunner1-torque", "locator": {"kind": "text-line", "line": 1}}]}
```

Write the file with 2-space indentation and LF (`python -I -c "import json,sys;d=json.load(open(sys.argv[1],encoding='utf-8'));open(sys.argv[1],'w',encoding='utf-8',newline='\n').write(json.dumps(d,ensure_ascii=False,indent=2)+'\n')" fixtures/attribution-rule/workspace.json` normalizes it once it parses).

- [ ] **Step 8.2** Add to `scripts/test_attribution_rule.py`:

```python
class AttributionRule(unittest.TestCase):
 """Spec 119-154 on the occupancy-join workspace: acceptance, packaging at 2.27.0, every attribution.* code reachable here."""
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_accepted_and_packaged_at_2_27(self):
  state=w();server.check_state(state);self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:
   p=package(state,Path(t));self.assertEqual(p['schemaVersion'],'2.27.0')
   self.assertEqual([e['path'] for e in p['files'] if e['kind']==ar.KIND],['attribution-rules/0.json']);self.assertEqual([e['path'] for e in p['files'] if e['kind']==ir.KIND],['impact-rules/0.json'])
   self.assertEqual(server.v2.p3.validate_package(Path(t))[0],[])
 def test_without_rules_and_profiles_2_23_unchanged(self):
  state=w();del state['attributionRules'],state['impactRules'],state['occupancyBindings'],state['incidentBindings'];self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:self.assertEqual(package(state,Path(t))['schemaVersion'],'2.23.0')
 # spec 130-131
 def test_hierarchy_missing(self):self.refused(ruled(lambda r:r['equipmentRef'].update(version='9.9.9')),'attribution.hierarchy-missing')
 def test_an_invalid_hierarchy_keeps_its_own_refusal_and_runs_no_rule_check(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);h=load(root/'hierarchy/0.json');next(n for n in h['nodes'] if n['equipmentInstanceId']=='station1')['parentEquipmentInstanceId']='nutrunner1'
   server.contracts.save(root/'hierarchy/0.json',h);repinned(root);codes=[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]]
   self.assertIn('hierarchy.cycle',codes);self.assertEqual([c for c in codes if c.startswith(('attribution.','impact.'))],[])
   self.assertRaisesRegex(ValueError,'hierarchy.cycle',ar.paths,h)   # never a loop or a KeyError
 def test_station_unresolved(self):self.refused(ruled(lambda r:r['stations'].__setitem__(1,'synthetic-site:line2:station9')),'attribution.station-unresolved')
 def test_station_nested(self):self.refused(ruled(lambda r:r['stations'].append('synthetic-site:line2:station1:nutrunner1')),'attribution.station-nested')
 def test_duplicate_or_empty_stations_are_schema_refusals(self):
  self.refused(ruled(lambda r:r['stations'].append(r['stations'][0])),'attribution-rule: schema validation failed');self.refused(ruled(lambda r:r.update(stations=[])),'attribution-rule: schema validation failed')
 # spec 132
 def test_empty_members(self):self.refused(ruled(lambda r:r.update(members=[])),'attribution.member-unresolved')
 def test_member_set_unresolved(self):self.refused(ruled(lambda r:r['members'][0]['mappingSetRef'].update(version='9.9.9')),'attribution.member-unresolved')
 def test_member_mapping_unresolved(self):self.refused(ruled(lambda r:r['members'][0].update(mappingId='nutrunner1-angle')),'attribution.member-unresolved')
 def test_member_of_another_set(self):self.refused(ruled(lambda r:r['members'][0]['mappingSetRef'].update(id='station1-mapping')),'attribution.member-unresolved')
 def test_member_metric_must_equal_the_leaf_name(self):self.refused(ruled(lambda r:r['members'][0].update(metric='torque')),'attribution.member-unresolved')
 def test_member_semantic_id_must_equal_the_leaf(self):self.refused(ruled(lambda r:r['members'][0].update(semanticId='urn:bifrost:sem:Tool/Angle')),'attribution.member-unresolved')
 def test_member_listed_twice(self):self.refused(ruled(lambda r:r['members'].append(copy.deepcopy(r['members'][0]))),'attribution.member-unresolved')
 def test_member_source_identifier_must_end_with_the_metric(self):
  state=w();next(s for s in state['sources'] if s['definition']['id']=='nutrunner1-torque')['definition']['access']['identifier']='Line2/Station1/Nutrunner1.TorqueValue';self.refused(state,'attribution.member-unresolved')
 def test_duplicate_leaf_names_in_one_definition_are_refused(self):
  state=w();next(s for s in state['semantics'] if s['id']=='tool-model')['members'][1]['name']='Torque';self.refused(state,'attribution.member-unresolved')
 def test_a_station_and_a_tool_may_each_have_a_member_named_running(self):server.check_state(w())
 def test_member_equipment_outside_the_stations(self):self.refused(ruled(lambda r:(r.update(stations=['synthetic-site:line2:station2']),r['activity'].__delitem__(slice(0,4)),r['activity'].append({'equipmentPath':'synthetic-site:line2:station2','memberRef':'station2-running','activeWhen':True}))),'attribution.member-equipment')
 # spec 133
 def test_activity_member_unresolved(self):self.refused(ruled(lambda r:r['activity'][0].update(memberRef='station1-torque')),'attribution.activity-member')
 def test_activity_member_must_be_boolean(self):self.refused(ruled(lambda r:r['activity'][2].update(memberRef='nutrunner1-torque')),'attribution.activity-member')
 def test_activity_member_must_belong_to_its_equipment(self):self.refused(ruled(lambda r:r['activity'][0].update(memberRef='nutrunner1-running')),'attribution.activity-member')
 def test_activity_equipment_must_be_a_station_or_below(self):self.refused(ruled(lambda r:r['activity'][0].update(equipmentPath='synthetic-site:line2')),'attribution.activity-member')
 def test_two_activity_entries_for_one_equipment(self):self.refused(ruled(lambda r:r['activity'].append(copy.deepcopy(r['activity'][0]))),'attribution.activity-member')
 def test_an_equipment_without_an_activity_entry_is_accepted(self):server.check_state(ruled(lambda r:r['activity'].pop(3)))
 def test_empty_activity_is_a_schema_refusal(self):self.refused(ruled(lambda r:r.update(activity=[])),'attribution-rule: schema validation failed')
 # spec 134, 192, 204
 def test_binding_unresolved(self):self.refused(ruled(lambda r:r['occupancyBindingRef'].update(version='9.9.9')),'attribution.binding-unresolved')
 def test_binding_must_be_an_artifact_1_1_0(self):self.refused(ruled(lambda r:r['occupancyBindingRef'].update(id='manual-nutrunner1-torque')),'attribution.binding-unresolved')
 def test_binding_artifact_must_carry_the_prefix_and_media_type(self):self.refused(ruled(lambda r:r['occupancyBindingRef'].update(id='hierarchy-plant-register')),'attribution.binding-profile')
 def test_binding_scope_is_not_compared_with_the_stations(self):server.check_state(profiled(lambda r:r.update(scope=['station1'])))
 def test_binding_profile_refused_on_the_package_alone(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);(root/'data/occupancy-binding-0.json').write_bytes(b'{}\n');repinned(root)
   self.assertIn('attribution.binding-profile',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
 # spec 135 under occupancy-join
 def test_identity_entries_are_schema_bound_to_plc_stamped(self):self.refused(ruled(lambda r:r['identity'].update(members=[])),'attribution-rule: schema validation failed')
 def test_a_namespace_and_cross_check_occupancy_are_allowed_under_occupancy_join(self):server.check_state(ruled(lambda r:r['identity'].update(namespace='urn:line2:visits',crossCheck='occupancy')))
 # spec 136-138
 def test_temporal_order(self):
  self.refused(ruled(lambda r:r['temporal'].update(outOfOrdernessMs=800000)),'attribution.temporal-order');self.refused(ruled(lambda r:r['temporal'].update(horizonMs=600000)),'attribution.temporal-order')
  server.check_state(ruled(lambda r:r['temporal'].update(outOfOrdernessMs=720000,horizonMs=720000)))
 def test_expected_period_zero_is_a_schema_refusal(self):self.refused(ruled(lambda r:r['coverage'].update(expectedPeriodMs=0)),'attribution-rule: schema validation failed')
 # workspace record rules
 def test_duplicate_id(self):
  state=w();state['attributionRules'].append(copy.deepcopy(state['attributionRules'][0]));self.refused(state,'attribution-rule: duplicate id')
 def test_older_version_is_not_written(self):self.refused(ruled(lambda r:r.update(schemaVersion='2.26.0')),'attribution-rule: schema validation failed')
 def test_older_envelope_refused(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);p=load(root/'proposal.json');p['schemaVersion']='2.26.0';server.contracts.save(root/'proposal.json',p)
   self.assertEqual([e['ruleCode'] for e in server.v2.p3.validate_package(root)[0]],['schema'])   # 2.26.0 cannot list the kinds
 def test_package_checks_without_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);r=load(root/'attribution-rules/0.json');r['stations'][1]='synthetic-site:line2:station9';server.contracts.save(root/'attribution-rules/0.json',r);repinned(root)
   self.assertIn('attribution.station-unresolved',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
```

- [ ] **Step 8.3** Run: `python -B scripts/test_attribution_rule.py AttributionRule` -> failures: `test_accepted_and_packaged_at_2_27` (`'2.23.0' != '2.27.0'`), every `refused` test for an `attribution.*` code fails with "ValueError not raised", the schema and duplicate-id tests fail with "ValueError not raised" (the sections are allowed since Task 7 but not yet checked), `test_an_invalid_hierarchy_...` fails on `ar.paths` (`AttributeError`), `test_older_envelope_refused` and `test_package_checks_without_workspace` fail on missing files. `test_without_rules_and_profiles_2_23_unchanged`, `test_a_station_and_a_tool_may_each_have_a_member_named_running`, `test_an_equipment_without_an_activity_entry_is_accepted` and the other "accepted" tests pass already. Expected.
- [ ] **Step 8.4** Append to `scripts/attribution_rule.py` (the `plc-stamped` identity block is added in Task 11 at the marked place):

```python
def find(docs,kind,ref):
 return next((d for d in docs if d.get('kind')==kind and d.get('id')==ref.get('id') and d.get('version')==ref.get('version')),None)
def key(ref):return ref['id']+'@'+ref['version']
def paths(h):
 """Each node's hierarchy path, root first, joined with ':': the string Muninn publishes as the Sparkplug device id and the
 occupancy readPoint carries (the rule of command_binding.path). equipment_hierarchy.check runs first, so a duplicate node, a
 missing parent, a cycle or an over-deep chain raises the hierarchy's own code (spec 130) instead of looping or failing on a key."""
 by=eh.check(h);out={}
 for i in by:
  p=[];c=i
  while c is not None:p.insert(0,c);c=by[c]['parentEquipmentInstanceId']
  out[i]=':'.join(p)
 return out
def within(stations,path):
 """A path is a station of the rule or a descendant of one (a tool). Ids carry no ':', so the prefix test is exact."""
 return any(path==s or path.startswith(s+':') for s in stations)
def distinct_names(sem):
 """Spec 132: within one semantic definition no two leaf members share a name (a station and a tool may, across definitions)."""
 try:nodes=ls.layout(sem)['definitions']
 except ls.StructureError:return False
 seen=set()
 for m in nodes:
  if m['valueType'] in ls.CONTAINERS:continue
  if m['name'] in seen:return False
  seen.add(m['name'])
 return True
def members(docs,paths_):
 """Every mapping of the package by mappingId: its set key, its equipment's hierarchy path, the semantic leaf it maps, whether
 its memberPath is one step, whether its definition's leaf names are distinct, and its OPC UA node identifier (None unless
 the source is an opcua-node). A mapping whose target, definition, equipment or member path does not resolve is left out and
 is then attribution.member-unresolved; p3a_contracts reports its own code for it as well."""
 out={};distinct={}
 for s in docs:
  if s.get('kind')!='mapping-set':continue
  t=find(docs,'target-instance',s['targetInstanceRef'] or {});sem=find(docs,'semantic-definition',t['semanticDefinitionRef']) if t else None;path=paths_.get(s['equipmentInstanceId'])
  if sem is None or path is None:continue
  names_ok=distinct.setdefault(key(sem),distinct_names(sem))
  for m in s['mappings']:
   try:leaf=ls.resolve(sem,m['memberPath'])
   except ls.StructureError:continue
   v=m['valueRef'];src=find(docs,'source-definition',v.get('sourceRef') or {}) if v['kind']=='source' else None
   a=(src or {}).get('access') or {};ident=a.get('identifier') if a.get('kind')=='opcua-node' else None
   require(m['mappingId'] not in out,'mapping.duplicate-id')
   out[m['mappingId']]={'set':key(s),'path':path,'leaf':leaf,'one':len(m['memberPath'])==1,'distinct':names_ok,'identifier':None if ident is None else str(ident)}
 return out
def typed(rule,ref,path,value_type):
 x=rule.get(ref);return x is not None and x['path']==path and x['leaf']['valueType']==value_type
def check(r,docs,read):
 """One rule, the spec's attribution.* codes in Bifrost's order; the first failure stops it."""
 h=find(docs,'equipment-hierarchy',r['equipmentRef']);require(h is not None,'attribution.hierarchy-missing')
 paths_=paths(h);known=set(paths_.values());stations=list(r['stations'])
 for s in stations:require(s in known,'attribution.station-unresolved')
 for a in stations:
  for b in stations:require(not b.startswith(a+':'),'attribution.station-nested')
 bundle=members(docs,paths_);rule={};slots=set()
 require(len(r['members'])>0,'attribution.member-unresolved')
 for m in r['members']:
  x=bundle.get(m['mappingId']);metric=m['metric']
  require(x is not None and x['set']==key(m['mappingSetRef']) and x['one'] and x['distinct'] and x['leaf']['name']==metric and x['leaf']['semanticId']==m['semanticId']
          and (x['identifier'] is None or x['identifier'].endswith('.'+metric)) and m['mappingId'] not in rule and (x['path'],metric) not in slots,'attribution.member-unresolved')
  rule[m['mappingId']]=x;slots.add((x['path'],metric))
  require(within(stations,x['path']),'attribution.member-equipment')
 active=set()
 for a in r['activity']:
  x=rule.get(a['memberRef']);p=a['equipmentPath']
  require(x is not None and x['path']==p and within(stations,p) and x['leaf']['valueType']=='Boolean' and p not in active,'attribution.activity-member');active.add(p)
 e=find(docs,'evidence-artifact',r['occupancyBindingRef'])
 require(e is not None and e['schemaVersion']=='1.1.0','attribution.binding-unresolved')
 require(e['id'].startswith(PREFIX) and e['file']['mediaType']==MEDIA,'attribution.binding-profile')
 occupancy_profile(read(e['file']['path']),'attribution.binding-profile')
 # Task 11 inserts the plc-stamped identity checks here (spec 132 roles, 135 coverage and member types).
 t=r['temporal'];require(t['outOfOrdernessMs']<=t['allowedLatenessMs']<=t['horizonMs'],'attribution.temporal-order')
def validate(docs,read):
 """docs: every document in one package; read(path) returns a data file's bytes."""
 docs=list(docs)
 for r in docs:
  if r.get('kind')==KIND:check(r,docs,read)
```

- [ ] **Step 8.5** `backend/workspace_v2.py`:
  - `check`, after the `binding_profiles` block of Task 7:

```python
    for section,module in (("attributionRules","attribution_rule"),("impactRules","impact_rule")):
        if section in state:
            mod=__import__(module);docs=state[section]
            if not isinstance(docs,list) or len(docs)>64:raise ValueError(mod.KIND+".limit")
            ids=set()
            for d in docs:
                # Tyr writes 2.27.0 rules only; the schema is Bifrost's byte copy.
                if d.get("schemaVersion")!=mod.VERSION or p3.schema_errors(mod.KIND,d):raise ValueError(mod.KIND+": schema validation failed")
                if d["id"] in ids:raise ValueError(mod.KIND+": duplicate id")
                ids.add(d["id"])
```
  - `build`, before the `2.27.0` source line of Task 3:

```python
    for section,directory in (("attributionRules","attribution-rules"),("impactRules","impact-rules")):
        if state.get(section):
            (folder/directory).mkdir(exist_ok=True)
            p["schemaVersion"]="2.27.0"
            for i,d in enumerate(state[section]):
                rel=directory+"/"+str(i)+".json";vc.save(folder/rel,d)
                p["files"].append({"path":rel,"kind":d["kind"],"id":d["id"],"version":d["version"],"sha256":vc.hashed(folder/rel)})
```

- [ ] **Step 8.6** `scripts/p3a_contracts.py`: `import attribution_rule` and `import impact_rule` after `import command_binding`; lines 113-114 become a gate, and the attribution call follows the `command_binding.validate` call (line 118):

```python
    try:equipment_hierarchy.validate(docs.values());hierarchy_ok=True
    except ValueError as e:add(str(e),equipment_hierarchy.KIND);hierarchy_ok=False
```
```python
    # Spec 130: an invalid hierarchy keeps its own refusal; the rule validators run on a hierarchy that passed, as Bifrost's
    # fail-first bundle check implies.
    if hierarchy_ok:
        try:attribution_rule.validate(docs.values(),lambda p:vc.safe(root,p).read_bytes())
        except (OSError,ValueError) as e:add(str(e) if isinstance(e,ValueError) else "attribution.binding-profile",attribution_rule.KIND)
```
(Task 9 adds the impact call inside the same `if`.)

- [ ] **Step 8.7** Run: `python -B scripts/test_attribution_rule.py AttributionRule` -> `Ran 38 tests ... OK`. If `test_duplicate_leaf_names_in_one_definition_are_refused` reports another code first (a `structure.*` or `semantic.*` finding from `logical_structures.preflight`), the joined message of `check_state` still contains `attribution.member-unresolved` as long as the rule check ran; should `preflight` refuse the document before `validate_package` reaches the rules, keep the test and change the expectation to that code with a comment. Whole file: `python -B scripts/test_attribution_rule.py` -> `Ran 67 tests ... OK`. `python -B scripts/test_impact_rule.py` -> 9 OK (the fixture's impact rule is accepted by the schema; its checks come next).
- [ ] **Step 8.8** Commit: `feat(attribution-rule): validate attribution rules (2.27.0)`.

## Chunk 4: Impact validator, publication closure, the built fixture bundle

### Task 9: `impact_rule.validate`: the five `impact.*` codes

**Files:**
- Modify: `scripts/impact_rule.py` (`check`, `validate`)
- Modify: `scripts/p3a_contracts.py` (impact call inside the hierarchy gate)
- Modify: `scripts/test_impact_rule.py` (class `ImpactRule`)

Spec lines 156-188; Bifrost `ImpactRules.java`. Bifrost runs `AttributionRules` first and stops at the first failure of the bundle, so `ImpactRules` always sees a resolvable attribution rule; Tyr's `validate_package` keeps every validator's finding, so `impact_rule.check` must not crash when the attribution rule it finds has an unresolvable hierarchy (it then reports `impact.scope-containment`, the spec's code for a scope path that is not in the hierarchy).

- [ ] **Step 9.1** Add to `scripts/test_impact_rule.py`:

```python
class ImpactRule(unittest.TestCase):
 """Spec 156-188 on the occupancy-join workspace."""
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_accepted_with_its_attribution_rule(self):
  state=w();server.check_state(state);self.assertEqual(server.findings_for(state),[])
 def test_attribution_missing(self):self.refused(impacted(lambda r:r['attributionRuleRef'].update(version='9.9.9')),'impact.attribution-missing')
 def test_scope_must_be_in_the_hierarchy(self):self.refused(impacted(lambda r:r['incidentScope'].__setitem__(0,'synthetic-site:line2:station1:nutrunner9')),'impact.scope-containment')
 def test_scope_must_be_under_an_attribution_station(self):self.refused(impacted(lambda r:r['incidentScope'].__setitem__(0,'synthetic-site:line2')),'impact.scope-containment')
 def test_a_station_itself_is_in_scope(self):server.check_state(impacted(lambda r:r.update(incidentScope=['synthetic-site:line2:station1'])))
 def test_duplicate_or_empty_scope_is_a_schema_refusal(self):
  self.refused(impacted(lambda r:r['incidentScope'].append(r['incidentScope'][0])),'impact-rule: schema validation failed');self.refused(impacted(lambda r:r.update(incidentScope=[])),'impact-rule: schema validation failed')
 def test_binding_unresolved(self):
  self.refused(impacted(lambda r:r['incidentBindingRef'].update(version='9.9.9')),'impact.binding-unresolved')
  self.refused(impacted(lambda r:r['incidentBindingRef'].update(id='manual-nutrunner1-torque')),'impact.binding-unresolved')   # an artifact, but 1.0.0
 def test_binding_artifact_must_carry_the_prefix_and_media_type(self):self.refused(impacted(lambda r:r['incidentBindingRef'].update(id='occupancy-binding-line2')),'impact.binding-profile')
 def test_binding_profile_refused_on_the_package_alone(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);package(w(),root);(root/'data/incident-binding-0.json').write_bytes(b'{}\n');repinned(root)
   self.assertIn('impact.binding-profile',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
 def test_retention_order(self):
  self.refused(impacted(lambda r:r['retention'].update(workRecordsMs=3600000)),'impact.retention-order')
  server.check_state(impacted(lambda r:r['retention'].update(workRecordsMs=86400000)))   # equal to the horizon is accepted
 def test_retention_above_90_days_is_a_schema_refusal(self):self.refused(impacted(lambda r:r['retention'].update(workRecordsMs=7776000001)),'impact-rule: schema validation failed')
 def test_duplicate_id(self):
  state=w();state['impactRules'].append(copy.deepcopy(state['impactRules'][0]));self.refused(state,'impact-rule: duplicate id')
 def test_older_version_is_not_written(self):self.refused(impacted(lambda r:r.update(schemaVersion='2.26.0')),'impact-rule: schema validation failed')
 def test_package_without_the_attribution_rule(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=package(w(),root);p['files']=[e for e in p['files'] if e['kind']!=ar.KIND];server.contracts.save(root/'proposal.json',p)
   self.assertIn('impact.attribution-missing',[x['ruleCode'] for x in server.v2.p3.validate_package(root)[0]])
```

- [ ] **Step 9.2** Run: `python -B scripts/test_impact_rule.py ImpactRule` -> the `impact.*` tests fail with "ValueError not raised" / missing code; the schema, duplicate-id and accepted tests pass. Expected.
- [ ] **Step 9.3** Append to `scripts/impact_rule.py`:

```python
def check(r,docs,read):
 """One rule, the spec's impact.* codes in Bifrost's order; the first failure stops it."""
 a=ar.find(docs,ar.KIND,r['attributionRuleRef']);require(a is not None,'impact.attribution-missing')
 h=ar.find(docs,'equipment-hierarchy',a['equipmentRef']);known=set(ar.paths(h).values()) if h is not None else set();stations=list(a['stations'])
 for s in r['incidentScope']:require(s in known and ar.within(stations,s),'impact.scope-containment')
 e=ar.find(docs,'evidence-artifact',r['incidentBindingRef']);require(e is not None and e['schemaVersion']=='1.1.0','impact.binding-unresolved')
 require(e['id'].startswith(PREFIX) and e['file']['mediaType']==MEDIA,'impact.binding-profile')
 incident_profile(read(e['file']['path']),'impact.binding-profile')
 require(a['temporal']['horizonMs']<=r['retention']['workRecordsMs'],'impact.retention-order')
def validate(docs,read):
 """docs: every document in one package; read(path) returns a data file's bytes. Attribution rules are validated first."""
 docs=list(docs)
 for r in docs:
  if r.get('kind')==KIND:check(r,docs,read)
```

- [ ] **Step 9.4** `scripts/p3a_contracts.py`: inside the `if hierarchy_ok:` block of Task 8, after the attribution call:

```python
        try:impact_rule.validate(docs.values(),lambda p:vc.safe(root,p).read_bytes())
        except (OSError,ValueError) as e:add(str(e) if isinstance(e,ValueError) else "impact.binding-profile",impact_rule.KIND)
```

- [ ] **Step 9.5** Run: `python -B scripts/test_impact_rule.py` -> `Ran 23 tests ... OK` (IncidentProfile 9, ImpactRule 14). `python -B scripts/test_attribution_rule.py` -> 67 OK.
- [ ] **Step 9.6** Commit: `feat(impact-rule): validate impact rules (2.27.0)`.

### Task 10: Publication closure, the built `bundle/`, Bifrost `mapping validate`

**Files:**
- Modify: `backend/publication.py` (closure after line 70; `refs` line 78)
- Create: `fixtures/attribution-rule/bundle/**` (built, 39 files)
- Modify: `scripts/test_attribution_rule.py` (class `Publication`)

Closure rule (the precedent is the metric and command-link lines of `publication.build`): an attribution rule travels only when every mapping set its `members[]` read is selected (otherwise Bifrost would refuse it with `attribution.member-unresolved`); its `occupancyBindingRef` then brings the profile artifact and data file; an impact rule travels with its attribution rule and brings its `incidentBindingRef`. The hierarchy is always carried (line 47). Owner decision Q1: the bundle is built once by `publication.build` from the fixture workspace, committed, and re-proved byte for byte by a test.

- [ ] **Step 10.1** Add to `scripts/test_attribution_rule.py`:

```python
class Publication(unittest.TestCase):
 """Rules travel with every mapping set they read; the impact rule with its attribution rule; profiles follow their references."""
 def test_publication_carries_both_rules_both_profiles_and_the_hierarchy(self):
  with tempfile.TemporaryDirectory() as t:
   p,findings=publish(w(),Path(t)/'b');self.assertEqual(findings,[]);self.assertEqual(p['schemaVersion'],'2.27.0')
   ids={(e['kind'],e['id']) for e in p['files']}
   for k in ((ar.KIND,'line2-attribution'),(ir.KIND,'line2-impact'),('evidence-artifact','occupancy-binding-line2'),('evidence-artifact','incident-binding-line2'),('equipment-hierarchy','line2-plant'),('evidence-artifact','hierarchy-plant-register')):self.assertIn(k,ids)
   for f in ('data/occupancy-binding-0.json','data/incident-binding-0.json','attribution-rules/0.json','impact-rules/0.json','submission.json'):self.assertTrue((Path(t)/'b'/f).is_file(),f)
   self.assertEqual(load(Path(t)/'b/submission.json')['streamId'],'line2');self.assertEqual(len(tree(Path(t)/'b')),39)
 def test_rule_stays_out_when_one_of_its_mapping_sets_is_not_published(self):
  with tempfile.TemporaryDirectory() as t:
   p,findings=publish(w(),Path(t)/'b',SETS[:3]);self.assertEqual(findings,[])
   kinds={e['kind'] for e in p['files']};self.assertNotIn(ar.KIND,kinds);self.assertNotIn(ir.KIND,kinds)
   self.assertFalse(any(e['id'].startswith((ar.PREFIX,ir.PREFIX)) for e in p['files']))
 def test_impact_rule_stays_out_without_its_attribution_rule(self):
  state=w();del state['attributionRules']
  with tempfile.TemporaryDirectory() as t:
   p,findings=publish(state,Path(t)/'b');self.assertEqual(findings,[]);self.assertNotIn(ir.KIND,{e['kind'] for e in p['files']})
 def test_fixture_bundle_is_the_build_of_the_fixture_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   publish(w(),Path(t)/'b');self.assertEqual(tree(Path(t)/'b'),tree(BUNDLE))
 def test_bifrost_receiver_validates_the_bundle(self):
  with tempfile.TemporaryDirectory() as t:
   v=publication.Adapter(JAR,Path(t)/'registry').call('validate',BUNDLE);self.assertTrue(v['accepted'],v);self.assertEqual(v['findings'],[])
```

- [ ] **Step 10.2** Run: `python -B scripts/test_attribution_rule.py Publication` -> `test_publication_carries_...` fails (`(attribution-rule, line2-attribution)` not in ids: nothing selects a rule yet), `test_fixture_bundle_...` fails (`tree(BUNDLE)` is empty: no bundle), `test_bifrost_receiver_...` fails (no bundle); the two "stays out" tests pass vacuously. Expected.
- [ ] **Step 10.3** `backend/publication.py`: add `import attribution_rule as ar` and `import impact_rule as ir` after `import command_binding as cb`; after line 70 (`selected|={... cb.KIND ...}`):

```python
        # An attribution rule travels only when every mapping set its members read is selected (Bifrost resolves each member in
        # the bundle); occupancyBindingRef then brings its profile. An impact rule travels with its attribution rule.
        selected|={k for k,d in docs.items() if k[0]==ar.KIND and all(("mapping-set",m["mappingSetRef"]["id"],m["mappingSetRef"]["version"]) in selected for m in d["members"])}
        selected|={k for k,d in docs.items() if k[0]==ir.KIND and (ar.KIND,d["attributionRuleRef"]["id"],d["attributionRuleRef"]["version"]) in selected}
```
  and in `refs` (line 78) append `"occupancyBindingRef":"evidence-artifact","incidentBindingRef":"evidence-artifact","attributionRuleRef":"attribution-rule"`. (`equipmentRef` is not added: `command-binding` 2.26.0 has its own `equipmentRef` with a third field, and the hierarchy is always selected at line 47.)

- [ ] **Step 10.4** Build the fixture bundle (from the repository root; `publication.build` refuses an existing folder):

```bash
rm -rf fixtures/attribution-rule/bundle && python -B - <<'PY'
import sys;from pathlib import Path
R=Path('.').resolve();sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication
state=server.contracts.load(R/'fixtures/attribution-rule/workspace.json')
_,_,findings=publication.build(state,R/'fixtures/attribution-rule/bundle','attribution-fixture','line2','proposer',None,['station1-mapping','station2-mapping','nutrunner1-mapping','nutrunner2-mapping'],False,server.build_package)
print(findings)
PY
find fixtures/attribution-rule/bundle -type f | wc -l
```
-> prints `[]` and `39`: `proposal.json`, `submission.json`, `attribution-rules/0.json`, `impact-rules/0.json`, `hierarchy/0.json`, `data/hierarchy-0.csv`, `evidence/hierarchy-0.json`, `data/occupancy-binding-0.json`, `evidence/occupancy-binding-0.json`, `data/incident-binding-0.json`, `evidence/incident-binding-0.json` (11), six `data/manual-<n>.txt`, six `evidence/<n>.json`, six `sources/<n>.json` (18), `semantics/0.json`, `semantics/1.json` (2), four `targets/<n>.json`, four `mappings/<n>.json` (8). `git diff --check` is clean (`vc.save` writes LF). The bundle is committed as data.

- [ ] **Step 10.5** Run: `python -B scripts/test_attribution_rule.py Publication` -> `Ran 5 tests ... OK` (the last needs the jar of Task 0). Whole module -> `Ran 72 tests ... OK`; `python -B scripts/test_impact_rule.py` -> 23 OK; `python -B scripts/test_command_binding.py`, `test_metric_definition.py` and `test_equipment_hierarchy.py` unchanged OK (their closures are untouched).
- [ ] **Step 10.6** Commit: `feat(publication): carry attribution and impact rules with their mapping sets` (includes `fixtures/attribution-rule/bundle/**`).

## Chunk 5: The `plc-stamped` fixture, receiver parity per code, the completion gate

### Task 11: `plc-stamped-workspace.json`, the identity checks, `plc-stamped-bundle/`

**Files:**
- Create: `fixtures/attribution-rule/plc-stamped-workspace.json`
- Modify: `scripts/attribution_rule.py` (`check`: the `plc-stamped` identity block)
- Create: `fixtures/attribution-rule/plc-stamped-bundle/**` (built, 59 files)
- Modify: `scripts/test_attribution_rule.py` (class `PlcStamped`)

Spec lines 132 (roles), 135 (identity), 711 (typed String at 2.27.0); Bifrost's `attribution-plc-stamped` fixture and `e0f25ce`. The identity checks are implemented in this task so that their tests are red first. The workspace is `workspace.json` with these changes (everything else, including the impact rule and both profiles, is identical):

- [ ] **Step 11.1** Create `fixtures/attribution-rule/plc-stamped-workspace.json`:

(1) six more source records, in exactly the shape the PLC form writes for the OPC UA profile: the four String ones at `schemaVersion` `2.27.0`, the two Boolean ones at `2.7.0` (= `string_source()` of Task 3; `sourceKind` `plc`, `accessMode` `read`, `viewOf` null, `inputStage` `already-engineered`, unit not-applicable, `evidenceRefs` `manual-<id>` line 1; the form's `capturedAt` is replaced by the fixed `2026-11-07T00:00:00Z`):

| `id` (= `label`) | `equipmentInstanceId` | `connectionProfileRef` | `identifier` | `valueType` | `note` |
|---|---|---|---|---|---|
| `station1-unit` | `station1` | `sim-opcua-station1` | `Line2/Station1.UnitId` | `String` | `Line2/Station1.UnitId, String` |
| `station1-visit` | `station1` | `sim-opcua-station1` | `Line2/Station1.VisitId` | `String` | `Line2/Station1.VisitId, String` |
| `station1-present` | `station1` | `sim-opcua-station1` | `Line2/Station1.VisitPresent` | `Boolean` | `Line2/Station1.VisitPresent, Boolean` |
| `nutrunner1-unit` | `nutrunner1` | `sim-opcua-nutrunner1` | `Line2/Station1/Nutrunner1.UnitId` | `String` | `Line2/Station1/Nutrunner1.UnitId, String` |
| `nutrunner1-visit` | `nutrunner1` | `sim-opcua-nutrunner1` | `Line2/Station1/Nutrunner1.VisitId` | `String` | `Line2/Station1/Nutrunner1.VisitId, String` |
| `nutrunner1-present` | `nutrunner1` | `sim-opcua-nutrunner1` | `Line2/Station1/Nutrunner1.VisitPresent` | `Boolean` | `Line2/Station1/Nutrunner1.VisitPresent, Boolean` |

(`station1-present` and `nutrunner1-present` are Boolean, so the form writes them at **2.7.0** (`mixed.js` chooses the version by raw type: 2.27.0 for String only) and the fixture carries them at 2.7.0, unlike Bifrost's hand-written fixture, which has them at 2.27.0. Both are valid for Bifrost: a 2.7.0 typed Boolean OPC UA source is an ordinary `plc` source, `AttributionRules` reads the member's type from the semantic leaf, and `rule.envelope` is raised by the four String sources anyway. Choosing 2.7.0 keeps the claim "the fixture's identity sources are what the form writes" true for all six records.)

(2) two more semantic definitions (complete), the stamped models of Bifrost's fixture:

```json
{"kind": "semantic-definition", "schemaVersion": "2.12.0", "id": "station-stamped-model", "version": "1.0.0", "members": [
  {"memberId": "running", "name": "Running", "semanticId": "urn:bifrost:sem:Station/Running", "description": "Station is working", "valueType": "Boolean", "unit": {"status": "not-applicable"}, "role": "status", "range": null},
  {"memberId": "unit", "name": "UnitId", "semanticId": "urn:bifrost:sem:Station/UnitId", "description": "Unit present at the station, as the controller stamps it", "valueType": "String", "unit": {"status": "not-applicable"}, "role": "status", "range": null},
  {"memberId": "visit", "name": "VisitId", "semanticId": "urn:bifrost:sem:Station/VisitId", "description": "Producer visit id of the present unit", "valueType": "String", "unit": {"status": "not-applicable"}, "role": "status", "range": null},
  {"memberId": "present", "name": "VisitPresent", "semanticId": "urn:bifrost:sem:Station/VisitPresent", "description": "True while a unit is present", "valueType": "Boolean", "unit": {"status": "not-applicable"}, "role": "status", "range": null}
]}
```
```json
{"kind": "semantic-definition", "schemaVersion": "2.12.0", "id": "tool-stamped-model", "version": "1.0.0", "members": [
  {"memberId": "torque", "name": "Torque", "semanticId": "urn:bifrost:sem:Tool/Torque", "description": "Tightening torque", "valueType": "Double", "unit": {"status": "known", "code": "N.m"}, "role": "measurement", "range": {"low": "0", "high": "100"}},
  {"memberId": "running", "name": "Running", "semanticId": "urn:bifrost:sem:Tool/Running", "description": "Tool is working", "valueType": "Boolean", "unit": {"status": "not-applicable"}, "role": "status", "range": null},
  {"memberId": "unit", "name": "UnitId", "semanticId": "urn:bifrost:sem:Tool/UnitId", "description": "Unit present at the tool, as the controller stamps it", "valueType": "String", "unit": {"status": "not-applicable"}, "role": "status", "range": null},
  {"memberId": "visit", "name": "VisitId", "semanticId": "urn:bifrost:sem:Tool/VisitId", "description": "Producer visit id of the present unit", "valueType": "String", "unit": {"status": "not-applicable"}, "role": "status", "range": null},
  {"memberId": "present", "name": "VisitPresent", "semanticId": "urn:bifrost:sem:Tool/VisitPresent", "description": "True while a unit is present", "valueType": "Boolean", "unit": {"status": "not-applicable"}, "role": "status", "range": null}
]}
```
(`station-model` and `tool-model` stay for `station2` and `nutrunner2`, so the bundle carries four semantic definitions; the shared `semanticId`s carry identical member signatures, so `semantic.identity-conflict` does not fire. Extending the shared models instead would force `station2`/`nutrunner2` to map identity members: `mapping.incomplete-object`.)

(3) targets: `station1.semanticDefinitionRef` -> `station-stamped-model`, `nutrunner1.semanticDefinitionRef` -> `tool-stamped-model`.

(4) mapping sets: `station1-mapping` gains three mappings `station1-unit` (member `unit`), `station1-visit` (member `visit`), `station1-present` (member `present`); `nutrunner1-mapping` gains `nutrunner1-unit`, `nutrunner1-visit`, `nutrunner1-present`. Each is the `station1-running` entry of Step 8.1 with `mappingId`, `sourceRef.id`, `memberId` and `evidenceRefs[0].artifactId` (`manual-<id>`) replaced: `transform` `[]`, `outputUnit` not-applicable, `invalidValuePolicy` `bad-quality`, the same `temporalPolicy`. (Every member of a target's model must be mapped: `mapping.incomplete-object`.)

(5) `attributionRules[0]` (complete; Bifrost's `plc-stamped` rule with Tyr's evidence):

```json
{"kind": "attribution-rule", "schemaVersion": "2.27.0", "id": "line2-attribution", "version": "1.0.0",
 "label": "Line 2 plc-stamped attribution",
 "description": "Attributes nutrunner torque samples to the visit the station controller stamps in the same message.",
 "equipmentRef": {"id": "line2-plant", "version": "1.0.0"},
 "stations": ["synthetic-site:line2:station1", "synthetic-site:line2:station2"],
 "members": [
  {"mappingSetRef": {"id": "nutrunner1-mapping", "version": "1.0.0"}, "mappingId": "nutrunner1-torque", "semanticId": "urn:bifrost:sem:Tool/Torque", "metric": "Torque"},
  {"mappingSetRef": {"id": "station1-mapping", "version": "1.0.0"}, "mappingId": "station1-running", "semanticId": "urn:bifrost:sem:Station/Running", "metric": "Running"},
  {"mappingSetRef": {"id": "nutrunner1-mapping", "version": "1.0.0"}, "mappingId": "nutrunner1-running", "semanticId": "urn:bifrost:sem:Tool/Running", "metric": "Running"},
  {"mappingSetRef": {"id": "station1-mapping", "version": "1.0.0"}, "mappingId": "station1-unit", "semanticId": "urn:bifrost:sem:Station/UnitId", "metric": "UnitId"},
  {"mappingSetRef": {"id": "station1-mapping", "version": "1.0.0"}, "mappingId": "station1-visit", "semanticId": "urn:bifrost:sem:Station/VisitId", "metric": "VisitId"},
  {"mappingSetRef": {"id": "station1-mapping", "version": "1.0.0"}, "mappingId": "station1-present", "semanticId": "urn:bifrost:sem:Station/VisitPresent", "metric": "VisitPresent"},
  {"mappingSetRef": {"id": "nutrunner1-mapping", "version": "1.0.0"}, "mappingId": "nutrunner1-unit", "semanticId": "urn:bifrost:sem:Tool/UnitId", "metric": "UnitId"},
  {"mappingSetRef": {"id": "nutrunner1-mapping", "version": "1.0.0"}, "mappingId": "nutrunner1-visit", "semanticId": "urn:bifrost:sem:Tool/VisitId", "metric": "VisitId"},
  {"mappingSetRef": {"id": "nutrunner1-mapping", "version": "1.0.0"}, "mappingId": "nutrunner1-present", "semanticId": "urn:bifrost:sem:Tool/VisitPresent", "metric": "VisitPresent"}
 ],
 "activity": [
  {"equipmentPath": "synthetic-site:line2:station1", "memberRef": "station1-running", "activeWhen": true},
  {"equipmentPath": "synthetic-site:line2:station1:nutrunner1", "memberRef": "nutrunner1-running", "activeWhen": true}
 ],
 "occupancyBindingRef": {"id": "occupancy-binding-line2", "version": "1.0.0"},
 "identity": {"mode": "plc-stamped", "namespace": "urn:line2:visits",
  "members": [
   {"equipmentPath": "synthetic-site:line2:station1", "unitMemberRef": "station1-unit", "visitMemberRef": "station1-visit", "presentMemberRef": "station1-present"},
   {"equipmentPath": "synthetic-site:line2:station1:nutrunner1", "unitMemberRef": "nutrunner1-unit", "visitMemberRef": "nutrunner1-visit", "presentMemberRef": "nutrunner1-present"}
  ],
  "crossCheck": "occupancy"},
 "temporal": {"timestampBasis": "source", "outOfOrdernessMs": 30000, "allowedLatenessMs": 720000, "horizonMs": 86400000, "enterToleranceMs": 45000, "leaveToleranceMs": 45000},
 "quality": {"uncertainInput": "reject", "maxBadShare": 0.1},
 "coverage": {"expectedPeriodMs": 1000, "maxMissingPeriods": 3},
 "overlap": {"policy": "reject-ambiguous"},
 "evidenceRefs": [{"artifactId": "manual-nutrunner1-torque", "locator": {"kind": "text-line", "line": 1}}]}
```

- [ ] **Step 11.2** Add to `scripts/test_attribution_rule.py`:

```python
def stamped(f):
 state=plc();f(state['attributionRules'][0]);return state
IDENTITY_SOURCES=(('station1-unit','station1','sim-opcua-station1','Line2/Station1.UnitId','String'),('station1-visit','station1','sim-opcua-station1','Line2/Station1.VisitId','String'),('station1-present','station1','sim-opcua-station1','Line2/Station1.VisitPresent','Boolean'),
                  ('nutrunner1-unit','nutrunner1','sim-opcua-nutrunner1','Line2/Station1/Nutrunner1.UnitId','String'),('nutrunner1-visit','nutrunner1','sim-opcua-nutrunner1','Line2/Station1/Nutrunner1.VisitId','String'),('nutrunner1-present','nutrunner1','sim-opcua-nutrunner1','Line2/Station1/Nutrunner1.VisitPresent','Boolean'))
class PlcStamped(unittest.TestCase):
 """Spec 132 and 135 under plc-stamped: coverage (identity-equipment), one role per mappingId and member types (identity-member)."""
 def refused(self,state,code):self.assertRaisesRegex(ValueError,code,server.check_state,state)
 def test_accepted_and_packaged_with_typed_string_sources(self):
  state=plc();server.check_state(state);self.assertEqual(server.findings_for(state),[])
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);p=package(state,root);self.assertEqual(p['schemaVersion'],'2.27.0');self.assertEqual(server.v2.p3.validate_package(root)[0],[])
   strings=[load(root/e['path']) for e in p['files'] if e['kind']=='source-definition' and load(root/e['path'])['rawRepresentation']['valueType']=='String']
   self.assertEqual(sorted(s['id'] for s in strings),['nutrunner1-unit','nutrunner1-visit','station1-unit','station1-visit']);self.assertTrue(all(s['schemaVersion']=='2.27.0' for s in strings))
   self.assertEqual(sorted(e['id'] for e in p['files'] if e['kind']=='semantic-definition'),['station-model','station-stamped-model','tool-model','tool-stamped-model'])
 def test_identity_sources_are_what_the_plc_form_writes(self):
  state=plc()
  for id,eq,con,node,vt in IDENTITY_SOURCES:
   expected=string_source({'sources':[]},id,eq,con,node,vt)['sources'][0];actual=next(s for s in state['sources'] if s['definition']['id']==id)
   self.assertEqual(actual['definition'],expected['definition']);self.assertEqual(set(actual),set(expected))
 def test_identity_equipment_missing(self):self.refused(stamped(lambda r:r['identity']['members'].pop(1)),'attribution.identity-equipment')
 def test_identity_equipment_duplicate(self):self.refused(stamped(lambda r:r['identity']['members'].append(copy.deepcopy(r['identity']['members'][0]))),'attribution.identity-equipment')
 def test_identity_entry_for_an_equipment_without_members_is_refused(self):
  self.refused(stamped(lambda r:r['identity']['members'].append(dict(r['identity']['members'][0],equipmentPath='synthetic-site:line2:station2'))),'attribution.identity-equipment')
 def test_identity_only_equipment_may_not_carry_an_identity_entry(self):
  def f(r):
   r['members']=[m for m in r['members'] if m['mappingId'] not in ('nutrunner1-torque','nutrunner1-running')];r['activity']=[a for a in r['activity'] if a['memberRef']!='nutrunner1-running']
  self.refused(stamped(f),'attribution.identity-equipment')
 def test_identity_unit_member_must_be_string(self):self.refused(stamped(lambda r:r['identity']['members'][0].update(unitMemberRef='station1-present')),'attribution.identity-member')
 def test_identity_present_member_must_be_boolean(self):self.refused(stamped(lambda r:r['identity']['members'][0].update(presentMemberRef='station1-visit')),'attribution.identity-member')
 def test_identity_member_unresolved(self):self.refused(stamped(lambda r:r['identity']['members'][0].update(unitMemberRef='station1-angle')),'attribution.identity-member')
 def test_identity_member_must_belong_to_the_entrys_equipment(self):
  def f(r):
   r['identity']['members'][0].update(unitMemberRef='nutrunner1-unit');r['identity']['members'][1].update(unitMemberRef='station1-unit')
  self.refused(stamped(f),'attribution.identity-member')
 def test_identity_present_ref_naming_the_activity_member_is_refused(self):self.refused(stamped(lambda r:r['identity']['members'][0].update(presentMemberRef='station1-running')),'attribution.identity-member')
 def test_identity_ref_shared_across_two_entries_is_refused(self):self.refused(stamped(lambda r:r['identity']['members'][1].update(visitMemberRef='station1-visit')),'attribution.identity-member')
 def test_identity_entry_order_does_not_matter(self):server.check_state(stamped(lambda r:r['identity']['members'].reverse()))
 def test_cross_check_none_is_allowed_under_plc_stamped(self):server.check_state(stamped(lambda r:r['identity'].update(crossCheck='none')))
 def test_plc_stamped_needs_a_namespace_and_entries(self):
  self.refused(stamped(lambda r:r['identity'].pop('namespace')),'attribution-rule: schema validation failed');self.refused(stamped(lambda r:r['identity'].update(members=[])),'attribution-rule: schema validation failed')
 def test_two_activity_entries_with_different_members_for_one_equipment(self):
  self.refused(stamped(lambda r:r['activity'].append({'equipmentPath':'synthetic-site:line2:station1','memberRef':'station1-present','activeWhen':True})),'attribution.activity-member')
 def test_fixture_bundle_is_the_build_of_the_fixture_workspace(self):
  with tempfile.TemporaryDirectory() as t:
   publish(plc(),Path(t)/'b',id='attribution-plc-stamped-fixture');self.assertEqual(tree(Path(t)/'b'),tree(PLC_BUNDLE));self.assertEqual(len(tree(PLC_BUNDLE)),59)
 def test_bifrost_receiver_validates_the_bundle(self):
  with tempfile.TemporaryDirectory() as t:
   v=publication.Adapter(JAR,Path(t)/'registry').call('validate',PLC_BUNDLE);self.assertTrue(v['accepted'],v)
```

- [ ] **Step 11.3** Run: `python -B scripts/test_attribution_rule.py PlcStamped` (after Step 11.1 is written) -> failures: the nine `identity-equipment` / `identity-member` tests fail with "ValueError not raised" (the identity block does not exist yet), the two bundle tests fail (no `plc-stamped-bundle/`); the acceptance, form-shape, order, crossCheck, schema and activity tests pass. Expected.
- [ ] **Step 11.4** Insert in `scripts/attribution_rule.py`, `check()`, at the marked place (after the profile parse, before the temporal check):

```python
 ident=r['identity']
 if ident['mode']=='plc-stamped':
  # roles by reference (spec 132): named by activity = activity member, named by an identity entry = identity member, every other
  # entry = measurement member; the equipment with measurement or activity members are the activity entries' paths plus the
  # paths of every members[] entry no identity entry names (an identity-only equipment is not covered: spec 135).
  refs=('unitMemberRef','visitMemberRef','presentMemberRef')
  named={x[k] for x in ident['members'] for k in refs}
  involved={a['equipmentPath'] for a in r['activity']}|{x['path'] for i,x in rule.items() if i not in named}
  covered=set()
  for x in ident['members']:require(x['equipmentPath'] not in covered,'attribution.identity-equipment');covered.add(x['equipmentPath'])
  require(covered==involved,'attribution.identity-equipment')
  roles={a['memberRef'] for a in r['activity']}
  for x in ident['members']:
   for k in refs:require(x[k] not in roles,'attribution.identity-member');roles.add(x[k])
  for x in ident['members']:
   p=x['equipmentPath'];require(typed(rule,x['unitMemberRef'],p,'String') and typed(rule,x['visitMemberRef'],p,'String') and typed(rule,x['presentMemberRef'],p,'Boolean'),'attribution.identity-member')
```

- [ ] **Step 11.5** Build `plc-stamped-bundle/` (the script of Step 10.4 with `plc-stamped-workspace.json`, destination `fixtures/attribution-rule/plc-stamped-bundle`, submission id `attribution-plc-stamped-fixture`) -> prints `[]`; `find fixtures/attribution-rule/plc-stamped-bundle -type f | wc -l` -> `59` (39 + six sources + six `data/manual-<n>.txt` + six `evidence/<n>.json` + `semantics/2.json`, `semantics/3.json`).
- [ ] **Step 11.6** Run: `python -B scripts/test_attribution_rule.py PlcStamped` -> `Ran 18 tests ... OK`; whole module -> `Ran 90 tests ... OK`; `python -B scripts/test_impact_rule.py` -> 23 OK.
- [ ] **Step 11.7** Commit: `feat(attribution-rule): validate plc-stamped identity members and add the plc-stamped fixture`.

### Task 12: Receiver parity per refusal code and the completion gate

**Files:**
- Modify: `scripts/test_attribution_rule.py` (helpers `java`, `approved`, `case_bundle`; classes `Parity`, `Approval`)

Owner decisions Q1 and Q3. Spec row 2: "Bifrost approves a bundle Tyr produced". `MappingGateTest.staged()`/`approves()` is the Bifrost side of the same gate; `scripts/p6r/accept.py` lines 109-114 is the Tyr precedent for `identity keygen` + `mapping approve` through the jar (`publication.Adapter.call` prefixes `mapping`, so keygen goes through a direct `java()` call). Parity is data-driven: one table row per refusal code of the spec's attribution and impact tables, each `*.binding-profile` code through the artifact wrapper, through the profile file's content, through a duplicate JSON key in the file and through a file nested 10,000 levels deep (Jackson's nesting limit on Bifrost's side, Python's recursion limit on Tyr's), plus the pattern bounds Bifrost's `Pattern.compile` decides and `rule.envelope`; every row mutates one committed bundle, re-pins it, and expects the same code from `validate_package` (Tyr) and from `mapping validate` (Bifrost, fail-first: exactly one finding); a second test holds the accepted cases (`rule.envelope` on a Tyr-published bundle, the largest Java bound, a bound written with 4,500 leading zeros, a UTF-8 BOM before either profile file). Cost: 31 JVM starts for parity (26 rows + 5) plus 10 for approval (2 x (2 keygen + 1 approve) + 2 keygen + 1 approve + the two `validate` calls of Tasks 10/11 are counted there), about one to two minutes on the CI runner.

- [ ] **Step 12.1** Add to `scripts/test_attribution_rule.py`:

```python
def java(*args):
 p=subprocess.run(['java','-jar',str(JAR),*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=120)
 assert p.returncode in (0,1),p.stderr;return json.loads(p.stdout)
def approved(bundle,tmp,stream='line2'):
 """A two-key registry whose activation policy names the stream, then Bifrost's approve: the step-2 completion gate."""
 reg=tmp/'registry';keys=tmp/'keys';(reg/'identity').mkdir(parents=True)
 lines=[java('identity','keygen',who,'--out',keys) for who in ('proposer','approver')]
 (reg/'identity/authorized-keys.jsonl').write_text(''.join(json.dumps(v)+'\n' for v in lines),encoding='utf-8')
 policy={'version':'1.0.0','default':'deny','rules':[{'id':'p','principal':'proposer','action':'publish','target':'mapping-publication','kind':'mapping-release','ref':stream},{'id':'a','principal':'approver','action':'approve','target':'mapping-publication','kind':'mapping-release','ref':stream}]}
 (reg/'identity/activation-policy.json').write_text(json.dumps(policy),encoding='utf-8')
 return reg,java('mapping','approve',reg,bundle,'approval-1','--by','proposer','--by-key',keys/'proposer.key','--approved-by','approver','--approved-by-key',keys/'approver.key')
def edit(rel,f):
 """A parity mutation: load one file of the bundle, change it, save it (re-pinning is the caller's)."""
 def apply(root):
  d=load(root/rel);f(d);server.contracts.save(root/rel,d)
 return apply
def profile_edit(rel,f):return edit(rel,f)
def raw_edit(rel,f):
 """A parity mutation on the bytes of a data file: what a JSON load/save would normalise away (a duplicate key)."""
 def apply(root):(root/rel).write_bytes(f((root/rel).read_bytes()))
 return apply
RULE,IMPACT,OCC,INC='attribution-rules/0.json','impact-rules/0.json','data/occupancy-binding-0.json','data/incident-binding-0.json'
PARITY=[
 # name, bundle, mutation, code expected from Tyr's pre-check and from Bifrost's jar
 ('hierarchy-missing',BUNDLE,edit(RULE,lambda r:r['equipmentRef'].update(version='9.9.9')),'attribution.hierarchy-missing'),
 ('station-unresolved',BUNDLE,edit(RULE,lambda r:r['stations'].__setitem__(1,'synthetic-site:line2:station9')),'attribution.station-unresolved'),
 ('station-nested',BUNDLE,edit(RULE,lambda r:r['stations'].append('synthetic-site:line2:station1:nutrunner1')),'attribution.station-nested'),
 ('member-unresolved',BUNDLE,edit(RULE,lambda r:r['members'][0].update(metric='torque')),'attribution.member-unresolved'),
 ('member-equipment',BUNDLE,edit(RULE,lambda r:(r.update(stations=['synthetic-site:line2:station2']),r.update(activity=[{'equipmentPath':'synthetic-site:line2:station2','memberRef':'station2-running','activeWhen':True}]))),'attribution.member-equipment'),
 ('activity-member',BUNDLE,edit(RULE,lambda r:r['activity'][2].update(memberRef='nutrunner1-torque')),'attribution.activity-member'),
 ('binding-unresolved',BUNDLE,edit(RULE,lambda r:r['occupancyBindingRef'].update(version='9.9.9')),'attribution.binding-unresolved'),
 ('binding-profile-artifact',BUNDLE,edit(RULE,lambda r:r['occupancyBindingRef'].update(id='hierarchy-plant-register')),'attribution.binding-profile'),
 ('binding-profile-pattern',BUNDLE,profile_edit(OCC,lambda p:p['identity'].update(pattern='^A$')),'attribution.binding-profile'),
 ('binding-profile-extra-field',BUNDLE,profile_edit(OCC,lambda p:p.update(note='x')),'attribution.binding-profile'),
 ('binding-profile-bound-above-int',BUNDLE,profile_edit(OCC,lambda p:p['identity'].update(pattern='a{2147483648}')),'attribution.binding-profile'),
 ('binding-profile-bound-above-uint',BUNDLE,profile_edit(OCC,lambda p:p['identity'].update(pattern='a{4294967296}')),'attribution.binding-profile'),
 ('binding-profile-bound-above-long',BUNDLE,profile_edit(OCC,lambda p:p['identity'].update(pattern='a{1,99999999999999999999}')),'attribution.binding-profile'),
 ('binding-profile-duplicate-key',BUNDLE,raw_edit(OCC,lambda b:b.replace(b'"topic": "mfg.occupancy"',b'"topic": "ignored",\n  "topic": "mfg.occupancy"')),'attribution.binding-profile'),
 ('binding-profile-deep-json',BUNDLE,raw_edit(OCC,lambda b:b'['*10000+b'0'+b']'*10000),'attribution.binding-profile'),
 ('identity-member',PLC_BUNDLE,edit(RULE,lambda r:r['identity']['members'][0].update(presentMemberRef='station1-running')),'attribution.identity-member'),
 ('identity-equipment',PLC_BUNDLE,edit(RULE,lambda r:r['identity']['members'].pop(1)),'attribution.identity-equipment'),
 ('temporal-order',BUNDLE,edit(RULE,lambda r:r['temporal'].update(outOfOrdernessMs=800000)),'attribution.temporal-order'),
 ('impact.attribution-missing',BUNDLE,edit(IMPACT,lambda r:r['attributionRuleRef'].update(version='9.9.9')),'impact.attribution-missing'),
 ('impact.scope-containment',BUNDLE,edit(IMPACT,lambda r:r['incidentScope'].__setitem__(0,'synthetic-site:line2')),'impact.scope-containment'),
 ('impact.binding-unresolved',BUNDLE,edit(IMPACT,lambda r:r['incidentBindingRef'].update(version='9.9.9')),'impact.binding-unresolved'),
 ('impact.binding-profile-artifact',BUNDLE,edit(IMPACT,lambda r:r['incidentBindingRef'].update(id='occupancy-binding-line2')),'impact.binding-profile'),
 ('impact.binding-profile-kinds',BUNDLE,profile_edit(INC,lambda p:p.update(kinds=[])),'impact.binding-profile'),
 ('impact.binding-profile-duplicate-key',BUNDLE,raw_edit(INC,lambda b:b.replace(b'"topic": "mfg.incidents"',b'"topic": "ignored",\n  "topic": "mfg.incidents"')),'impact.binding-profile'),
 ('impact.binding-profile-deep-json',BUNDLE,raw_edit(INC,lambda b:b'['*10000+b'0'+b']'*10000),'impact.binding-profile'),
 ('impact.retention-order',BUNDLE,edit(IMPACT,lambda r:r['retention'].update(workRecordsMs=3600000)),'impact.retention-order'),
]
def case_bundle(tmp,bundle,mutate):
 b=tmp/'bundle';shutil.copytree(bundle,b);mutate(b);return repinned(b)
class Parity(unittest.TestCase):
 """Owner decision Q3: for every refusal code of the attribution, impact and binding-profile tables, Tyr's pre-check and Bifrost's
 jar refuse the same mutated bundle with the same code (Bifrost fail-first: exactly one finding; Tyr: the code is among its findings)."""
 def test_every_refusal_code_agrees_with_bifrost(self):
  for name,bundle,mutate,code in PARITY:
   with self.subTest(name):
    with tempfile.TemporaryDirectory() as t:
     b=case_bundle(Path(t),bundle,mutate)
     self.assertIn(code,[x['ruleCode'] for x in server.v2.p3.validate_package(b)[0]],name)
     v=publication.Adapter(JAR,Path(t)/'registry').call('validate',b);self.assertFalse(v['accepted'],name);self.assertEqual([x['ruleCode'] for x in v['findings']],[code],name)
 def test_rule_envelope_and_the_accepted_patterns_agree_with_bifrost(self):
  # rule.envelope: a Tyr-published bundle whose 2.27.0 documents are the four String sources and nothing else (the plc-stamped
  # workspace minus its rules; publish() carries only the selected mapping sets' closure, and these sources are mapped), in a
  # 2.26.0 proposal. The presence of a 2.27.0 source in the published proposal is asserted before the version is lowered.
  state=plc();del state['attributionRules'],state['impactRules']
  with tempfile.TemporaryDirectory() as t:
   b=Path(t)/'b';p,findings=publish(state,b,id='envelope-case');self.assertEqual(findings,[])
   self.assertEqual(sorted(e['id'] for e in p['files'] if e['kind']=='source-definition' and load(b/e['path'])['schemaVersion']=='2.27.0'),['nutrunner1-unit','nutrunner1-visit','station1-unit','station1-visit'])
   p['schemaVersion']='2.26.0';server.contracts.save(b/'proposal.json',p);repinned(b)
   self.assertEqual([x['ruleCode'] for x in server.v2.p3.validate_package(b)[0]],['rule.envelope'])
   v=publication.Adapter(JAR,Path(t)/'registry').call('validate',b);self.assertEqual([x['ruleCode'] for x in v['findings']],['rule.envelope'])
  # accepted by both: the largest bound Java accepts (the rows above cover the first one it refuses), and a bound written with
  # 4,500 leading zeros (Bifrost does not parse {m}; Pattern.compile accumulates the zeros; Python's int() alone would refuse the digits)
  for pattern in ('[A-Z]{1,2147483647}','[A-Z]{'+'0'*4500+'17}'):
   with tempfile.TemporaryDirectory() as t:
    b=case_bundle(Path(t),BUNDLE,profile_edit(OCC,lambda p,pattern=pattern:p['identity'].update(pattern=pattern)))
    self.assertEqual(server.v2.p3.validate_package(b)[0],[],pattern[:24]);v=publication.Adapter(JAR,Path(t)/'registry').call('validate',b);self.assertTrue(v['accepted'],pattern[:24])
  # accepted by both: a UTF-8 BOM before either profile file (Jackson's byte reader skips it; json.loads on bytes detects utf-8-sig)
  for rel in (OCC,INC):
   with tempfile.TemporaryDirectory() as t:
    b=case_bundle(Path(t),BUNDLE,raw_edit(rel,lambda x:b'\xef\xbb\xbf'+x))
    self.assertEqual(server.v2.p3.validate_package(b)[0],[],rel);v=publication.Adapter(JAR,Path(t)/'registry').call('validate',b);self.assertTrue(v['accepted'],rel)
class Approval(unittest.TestCase):
 """Owner decision Q1 / spec row 2: Bifrost's two-key approval of the committed bundles Tyr built, through the CLI Tyr's CI builds."""
 def approves(self,bundle):
  with tempfile.TemporaryDirectory() as t:
   reg,receipt=approved(bundle,Path(t))
   self.assertEqual(receipt.get('kind'),'mapping-approval',receipt);self.assertEqual((receipt['payload']['streamId'],receipt['payload']['execution']),('line2','excluded'))
   self.assertTrue((reg/'mappings/approvals/approval-1.json').is_file());self.assertTrue((reg/'mappings/attestations/approval-1.dsse.json').is_file())
 def test_bifrost_approves_the_occupancy_join_bundle(self):self.approves(BUNDLE)
 def test_bifrost_approves_the_plc_stamped_bundle(self):self.approves(PLC_BUNDLE)
 def test_a_refused_bundle_leaves_no_receipt(self):
  with tempfile.TemporaryDirectory() as t:
   b=case_bundle(Path(t),BUNDLE,edit(IMPACT,lambda r:r['retention'].update(workRecordsMs=3600000)))
   reg,refused=approved(b,Path(t)/'r');self.assertTrue(str(refused.get('error','')).startswith('mapping.validation-refused:') and 'impact.retention-order' in refused['error'],refused)
   self.assertFalse((reg/'mappings/approvals/approval-1.json').exists())
```

- [ ] **Step 12.2** Run: `python -B scripts/test_attribution_rule.py Parity Approval` before adding the helpers (write the two classes first, the helpers after the red run) -> `NameError: name 'PARITY' is not defined` / `name 'approved' is not defined`: the red reason is the missing parity table and gate helpers, nothing in production code (the committed bundles and the jar are the artifacts under test). Expected. Then add `java`, `approved`, `edit`, `profile_edit`, `PARITY`, `case_bundle` above the two classes.
- [ ] **Step 12.3** Run: `python -B scripts/test_attribution_rule.py Parity Approval` -> `Ran 5 tests ... OK` (the parity test prints nothing per row; on a disagreement the `subTest` name says which code). A disagreement is a real finding and is fixed in the fixture, the closure or Tyr's mirror, never by relaxing a row; if Bifrost returns a second finding for some row, the row's mutation is narrowed until it fails one check only (its purpose is one code per row). The same gate at the shell, outside unittest, is Verification step 3.
- [ ] **Step 12.4** Whole module: `python -B scripts/test_attribution_rule.py` -> `Ran 95 tests ... OK`.
- [ ] **Step 12.5** Commit: `test(attribution-rule): receiver parity per refusal code and Bifrost approval of both bundles`.

## Chunk 6: Authoring screen, documentation, pull request

### Task 13: Authoring API and screen

**Files:**
- Create: `backend/attribution_authoring.py`
- Create: `frontend/attribution-rule.js`
- Modify: `backend/server.py` (import; GET route after line 326; asset map line 341; PUT allow-list line 351; dispatch after line 362)
- Modify: `frontend/index.html` (tab and script tag), `frontend/workflow.js` (membership), `scripts/test_workflow.py` line 66 (25 -> 26)
- Modify: `scripts/test_attribution_rule.py` (import line; class `Authoring`)

Precedent: `backend/command_binding_authoring.py` + `frontend/command-binding.js` (listing, plan with `planSha256`, apply under revision CAS, `approvalAuthority: 'bifrost'`). The rule documents are nested enough that the screen edits each record as a JSON block beside a member catalog Tyr derives (mapping set, mapping id, equipment path, metric, semantic id, value type) and the hierarchy paths; the fields themselves are validated by the same checks as the workspace. (A per-field form, the style of `command-binding.js`, is a possible follow-up; the owner chose the base plan's screen for step 2.)

- [ ] **Step 13.1** The import line of `scripts/test_attribution_rule.py` gains `attribution_authoring as aa`; add:

```python
class Authoring(unittest.TestCase):
 """The screen's API: the member catalog and paths Tyr derives, plan and apply under revision CAS, HTTP routes."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=server.Store(Path(self.tmp.name)/'db.sqlite3');self.store.migrate(0,{})
  state=w();self.body={k:state.pop(k) for k in ('occupancyBindings','incidentBindings','attributionRules','impactRules')};self.store.save(1,state)
 def tearDown(self):self.tmp.cleanup()
 def rev(self):return self.store.read()['revision']
 def req(self,body=None,revision=None):
  body=self.body if body is None else body   # {} means "delete every section" and must not fall back to the fixture body
  return {'revision':self.rev() if revision is None else revision,**{k:body.get(k,[]) for k in ('occupancyBindings','incidentBindings','attributionRules','impactRules')}}
 def plan(self,body=None,revision=None):return aa.plan(self.store,self.req(body,revision),server.Conflict,server.check_state)[0]
 def apply(self,body=None):
  p=self.plan(body);return aa.apply(self.store,{**self.req(body),'planSha256':p['planSha256']},server.Conflict)
 def test_listing_offers_members_paths_profiles_and_citable_evidence(self):
  self.apply();l=aa.listing(self.store,server.build_package)
  self.assertEqual(l['hierarchy']['paths']['nutrunner1'],'synthetic-site:line2:station1:nutrunner1')
  torque=next(m for m in l['members'] if m['mappingId']=='nutrunner1-torque');self.assertEqual((torque['equipmentPath'],torque['metric'],torque['semanticId'],torque['valueType'],torque['mappingSetRef']),('synthetic-site:line2:station1:nutrunner1','Torque','urn:bifrost:sem:Tool/Torque','Double',{'id':'nutrunner1-mapping','version':'1.0.0'}))
  self.assertEqual([r['id'] for r in l['attributionRules']],['line2-attribution']);self.assertEqual([r['id'] for r in l['impactRules']],['line2-impact'])
  self.assertEqual(l['occupancyBindings'][0]['artifactId'],'occupancy-binding-line2');self.assertIn('manual-nutrunner1-torque',l['citable']);self.assertEqual(l['findings'],[]);self.assertEqual(l['approvalAuthority'],'bifrost')
 def test_plan_refuses_with_the_spec_code(self):
  body=copy.deepcopy(self.body);body['attributionRules'][0]['stations'][1]='synthetic-site:line2:station9'
  self.assertRaisesRegex(ValueError,'attribution.station-unresolved',self.plan,body)
 def test_apply_saves_and_clears(self):
  r=self.apply();saved=r['saved']['workspace'];self.assertEqual([x['id'] for x in saved['attributionRules']],['line2-attribution']);self.assertEqual(len(saved['occupancyBindings']),1)
  r=self.apply({});self.assertFalse(any(k in r['saved']['workspace'] for k in ('occupancyBindings','incidentBindings','attributionRules','impactRules')))
 def test_stale_revision_changed_plan_and_unversioned_change(self):
  p=self.plan();self.assertRaises(server.Conflict,self.plan,None,self.rev()-1)
  other=copy.deepcopy(self.body);other['impactRules'][0]['label']='Other'
  self.assertRaisesRegex(ValueError,'attribution-rule.plan-changed',aa.apply,self.store,{**self.req(other),'planSha256':p['planSha256']},server.Conflict)
  self.apply();changed=copy.deepcopy(self.body);changed['occupancyBindings'][0]['profile']['topic']='mfg.occupancy.v2'
  self.assertRaisesRegex(ValueError,'occupancy-binding.version-required',self.plan,changed)
 def test_http_routes(self):
  import threading,urllib.request
  http=server.make_server(self.store,0);threading.Thread(target=http.serve_forever,daemon=True).start()
  try:
   base_url='http://127.0.0.1:'+str(http.server_address[1])
   def call(path,body=None):
    req=urllib.request.Request(base_url+path,data=None if body is None else json.dumps(body).encode(),method='GET' if body is None else 'POST',headers={'Content-Type':'application/json','X-Tyr-Editor':'1','Origin':base_url})
    with urllib.request.urlopen(req) as r:return json.loads(r.read())
   self.assertEqual(call('/api/attribution-rule')['attributionRules'],[])
   p=call('/api/attribution-rule-plan',self.req());s=call('/api/attribution-rule-apply',{**self.req(),'planSha256':p['planSha256']})
   self.assertEqual(s['saved']['findings'],[]);self.assertEqual([r['id'] for r in call('/api/attribution-rule')['attributionRules']],['line2-attribution'])
   with urllib.request.urlopen(base_url+'/attribution-rule.js') as r:self.assertIn(b'attributionRuleView',r.read())
   with urllib.request.urlopen(base_url+'/') as r:self.assertIn(b'data-tab="attributionRules"',r.read())
  finally:http.shutdown();http.server_close()
```

- [ ] **Step 13.2** Run: `python -B scripts/test_attribution_rule.py` -> `ModuleNotFoundError: No module named 'attribution_authoring'`. Expected.
- [ ] **Step 13.3** Create `backend/attribution_authoring.py`:

```python
"""Attribution and impact rule authoring API: listing, plan and apply under revision CAS. Approval stays with Bifrost.

The listing shows what a rule can name: the hierarchy paths of the workspace equipment and every mapping of every mapping set
with its equipment path, metric (the semantic leaf's name), semantic id and value type, plus the authored profiles as the
evidence-artifact ids their references use and the citable evidence ids. Rules and profiles are written here; the checks are
the workspace's (workspace_v2.check -> binding_profiles, attribution_rule, impact_rule).
"""
import copy
import attribution_rule as ar
import impact_rule as ir
import logical_structures as ls
from semantic_lifecycle import digest
from template_authoring import snapshot
SECTIONS=('occupancyBindings','incidentBindings','attributionRules','impactRules')
def require(ok,code):
    if not ok:raise ValueError(code)
def catalog(w):
    """Every mapping of the workspace as a rule member candidate; mappings whose target, model or member does not resolve are left out."""
    hs=w.get('equipmentHierarchies',[])
    try:paths=ar.paths(hs[0]) if hs else {}
    except ValueError:paths={}   # a hierarchy the hierarchy check refuses: the catalog shows no paths, the findings show the hierarchy.* code
    targets={(t['id'],t['version']):t for t in w['targets']};models={(m['id'],m['version']):m for m in w['semantics']};out=[]
    for s in w['mappings']:
        t=targets.get((s['targetInstanceRef']['id'],s['targetInstanceRef']['version']));sem=models.get((t['semanticDefinitionRef']['id'],t['semanticDefinitionRef']['version'])) if t else None
        if sem is None:continue
        for m in s['mappings']:
            try:leaf=ls.resolve(sem,m['memberPath'])
            except ls.StructureError:continue
            out.append({'mappingSetRef':{'id':s['id'],'version':s['version']},'mappingId':m['mappingId'],'equipmentInstanceId':s['equipmentInstanceId'],'equipmentPath':paths.get(s['equipmentInstanceId']),'metric':leaf['name'],'semanticId':leaf['semanticId'],'valueType':leaf['valueType']})
    return out,paths,hs[0] if hs else None
def listing(store,build_package):
    snap=store.read();w=snap['workspace']
    require(w.get('workspaceVersion')=='2.0.0','먼저 객체 식별 마이그레이션을 완료하세요.')
    members,paths,h=catalog(w)
    profiles=lambda section,prefix:[dict(r,artifactId=prefix+r['id']) for r in w.get(section,[])]
    citable=sorted({'manual-'+s['definition']['id'] for s in w['sources']}|{'hierarchy-'+r['id'] for r in w.get('hierarchyEvidence',[])})
    return {'revision':snap['revision'],'hierarchy':{'id':h['id'],'version':h['version'],'paths':paths} if h else None,'members':members,
            'occupancyBindings':profiles('occupancyBindings',ar.PREFIX),'incidentBindings':profiles('incidentBindings',ir.PREFIX),
            'attributionRules':w.get('attributionRules',[]),'impactRules':w.get('impactRules',[]),'citable':citable,
            'findings':[f for f in snap['findings'] if f['ruleCode'].startswith(('attribution','impact','occupancy-binding','incident-binding','rule.envelope'))],'approvalAuthority':'bifrost'}
def candidate(w,req):
    w=copy.deepcopy(w)
    for key in SECTIONS:
        if req[key]:w[key]=copy.deepcopy(req[key])
        else:w.pop(key,None)
    return w
def request(store,req,Conflict):
    require(isinstance(req,dict) and set(req) in ({'revision',*SECTIONS},{'revision',*SECTIONS,'planSha256'}),'attribution-rule.plan-request')
    require(all(isinstance(req[k],list) for k in SECTIONS),'attribution-rule.limit')
    before=snapshot(store,req['revision'],Conflict)['workspace']
    return before,candidate(before,req),digest({'revision':req['revision'],**{k:req[k] for k in SECTIONS}})
def plan(store,req,Conflict,check_state):
    before,w,sha=request(store,req,Conflict)
    check_state(w);__import__('binding_profiles').transition(before,w)
    return {'revision':req['revision'],'planSha256':sha,'valid':True},w
def apply(store,req,Conflict):
    """store.save runs the same state check and every transition rule, so the plan is not re-run here."""
    require('planSha256' in req,'attribution-rule.plan-required')
    _,w,sha=request(store,req,Conflict);require(req['planSha256']==sha,'attribution-rule.plan-changed')
    return {'saved':store.save(req['revision'],w),'planSha256':sha}
```

- [ ] **Step 13.4** `backend/server.py`:
  - after `import command_binding_authoring` (line 37): `import attribution_authoring`;
  - `do_GET`, after the `/api/command-binding` line (326): `if self.path == "/api/attribution-rule":return self.reply(200,attribution_authoring.listing(store,build_package))`;
  - the `assets` dict (line 341): add `"/attribution-rule.js": ("attribution-rule.js","text/javascript; charset=utf-8"),` after the `/command-binding.js` entry;
  - the `do_PUT` allow-list (line 351): add `"/api/attribution-rule-plan","/api/attribution-rule-apply",` after `"/api/command-binding-apply",`;
  - the dispatch (after line 362):

```python
                if self.path == "/api/attribution-rule-plan":return self.reply(200,attribution_authoring.plan(store,value,Conflict,check_state)[0])
                if self.path == "/api/attribution-rule-apply":return self.reply(200,attribution_authoring.apply(store,value,Conflict))
```

- [ ] **Step 13.5** Create `frontend/attribution-rule.js` (the screen; `$`, `esc`, `val`, `message`, `display`, `expressionApi`, `recordTask`, `v2Mode`, `migrationView`, `render`, `tab`, `revision`, `dirty` come from the loaded scripts, as in `command-binding.js`):

```javascript
/* Attribution and impact rules (forseti, contract 2.27.0): profiles and rules edited as JSON beside the members Tyr derives. Approval stays with Bifrost. */
let arData=null,arBlocks={occupancyBindings:[],incidentBindings:[],attributionRules:[],impactRules:[]},arPlan=null,arRequest=null;
const arTitles={occupancyBindings:'occupancy binding 프로필 (evidence-artifact occupancy-binding-<id>)',incidentBindings:'incident binding 프로필 (evidence-artifact incident-binding-<id>)',attributionRules:'귀속 규칙 (attribution-rule 2.27.0)',impactRules:'영향 규칙 (impact-rule 2.27.0)'};
function arInvalidate(){arPlan=null;dirty=true;if($('ar-save'))$('ar-save').disabled=true;if($('ar-plan'))$('ar-plan').innerHTML='';}
function arRead(){const out={};for(const k of Object.keys(arBlocks)){out[k]=[...document.querySelectorAll('[data-ar-block="'+k+'"]')].map(t=>{try{return JSON.parse(t.value);}catch(e){throw Error(arTitles[k]+': JSON을 읽을 수 없습니다. '+e.message);}});}return out;}
function arTemplate(k){const h=arData.hierarchy,st=h?Object.values(h.paths).filter(p=>p.split(':').length===3):[];
 if(k==='occupancyBindings')return {id:'',version:'1.0.0',label:'',origin:'synthetic',capturedAt:new Date().toISOString().replace(/\.\d+Z$/,'Z'),reviewer:'',product:null,scope:[],profile:{profileVersion:'0.1.0',topic:'mfg.occupancy',format:{schemaId:'urn:forseti:schema:occupancy:1.0.0',schemaSha256:'0'.repeat(64)},identity:{scheme:'mes-unit-id',pattern:'[A-Z0-9]{17}'},enter:{bizStep:'urn:epcglobal:cbv:bizstep:arriving'},leave:{bizStep:'urn:epcglobal:cbv:bizstep:departing'},correction:{errorDeclaration:'reissue-same-event-id',reasons:['urn:epcglobal:cbv:er:did_not_occur','urn:epcglobal:cbv:er:incorrect_data']},timestampBasis:'eventTime',sources:[]}};
 if(k==='incidentBindings')return {id:'',version:'1.0.0',label:'',origin:'synthetic',capturedAt:new Date().toISOString().replace(/\.\d+Z$/,'Z'),reviewer:'',product:null,scope:[],profile:{profileVersion:'0.1.0',topic:'mfg.incidents',format:{schemaId:'urn:forseti:schema:incident:1.0.0',schemaSha256:'0'.repeat(64)},kinds:['tool-check-failed'],equipmentRefBasis:'isa95-path'}};
 if(k==='attributionRules')return {kind:'attribution-rule',schemaVersion:'2.27.0',id:'',version:'1.0.0',label:'',description:'',equipmentRef:{id:h?.id||'',version:h?.version||''},stations:st,members:[],activity:[],occupancyBindingRef:{id:'',version:'1.0.0'},identity:{mode:'occupancy-join',crossCheck:'none'},temporal:{timestampBasis:'source',outOfOrdernessMs:30000,allowedLatenessMs:720000,horizonMs:86400000,enterToleranceMs:45000,leaveToleranceMs:45000},quality:{uncertainInput:'reject',maxBadShare:0.1},coverage:{expectedPeriodMs:1000,maxMissingPeriods:3},overlap:{policy:'reject-ambiguous'},evidenceRefs:[{artifactId:arData.citable[0]||'',locator:{kind:'text-line',line:1}}]};
 return {kind:'impact-rule',schemaVersion:'2.27.0',id:'',version:'1.0.0',label:'',description:'',attributionRuleRef:{id:'',version:'1.0.0'},incidentScope:[],incidentBindingRef:{id:'',version:'1.0.0'},interval:{start:'suspectFrom',overlap:'any-overlap',openEnd:'provisional-until-closed'},evidence:{match:'equipment-evidence',onBasisRetracted:'by-cause',onWithdrawn:'not-affected'},retention:{workRecordsMs:604800000},evidenceRefs:[{artifactId:arData.citable[0]||'',locator:{kind:'text-line',line:1}}]};}
function arBlockList(){for(const k of Object.keys(arBlocks)){$('ar-'+k).innerHTML=arBlocks[k].length?arBlocks[k].map((d,i)=>'<article class="template-slot"><p><code>'+esc(d.id||'(id 없음)')+'</code> @ '+esc(d.version||'')+'</p><textarea data-ar-block="'+k+'" rows="14" spellcheck="false">'+esc(JSON.stringify(d,null,2))+'</textarea><button type="button" class="secondary" data-ar-remove="'+k+'-'+i+'">삭제</button></article>').join(''):'<p class="hint">없습니다.</p>';}
 document.querySelectorAll('[data-ar-remove]').forEach(b=>b.onclick=()=>{const [k,i]=b.dataset.arRemove.split(/-(?=\d+$)/);arBlocks=arRead();arBlocks[k].splice(Number(i),1);arBlockList();arInvalidate();});}
function arCatalog(){return '<div class="record-table"><table><thead><tr><th>mappingSetRef</th><th>mappingId</th><th>equipmentPath</th><th>metric</th><th>semanticId</th><th>type</th></tr></thead><tbody>'+arData.members.map(m=>'<tr><td><code>'+esc(m.mappingSetRef.id+' @ '+m.mappingSetRef.version)+'</code></td><td><code>'+esc(m.mappingId)+'</code></td><td><code>'+esc(m.equipmentPath||'(계층 없음)')+'</code></td><td>'+esc(m.metric)+'</td><td><code>'+esc(m.semanticId)+'</code></td><td>'+esc(m.valueType)+'</td></tr>').join('')+'</tbody></table></div>';}
function arRecipe(){return {revision,...arRead()};}
async function arCompose(){const req=arRecipe(),p=await expressionApi('/api/attribution-rule-plan',req);if(tab!=='attributionRules'||JSON.stringify(req)!==JSON.stringify(arRecipe()))throw Error('입력이 바뀌었습니다. 다시 검증하세요.');arPlan=p;arRequest=req;$('ar-save').disabled=false;$('ar-plan').innerHTML='<h3>검증 완료</h3><p>occupancy 프로필 '+req.occupancyBindings.length+'개 · incident 프로필 '+req.incidentBindings.length+'개 · 귀속 규칙 '+req.attributionRules.length+'개 · 영향 규칙 '+req.impactRules.length+'개. 저장한 규칙은 매핑 제안(2.27.0)에 실려 Bifrost에서 승인받습니다.</p>';message('확인한 뒤 저장하세요.');}
async function arSave(){if(!arPlan||JSON.stringify(arRequest)!==JSON.stringify(arRecipe()))throw Error('다시 검증하세요.');const r=await expressionApi('/api/attribution-rule-apply',{...arRequest,planSha256:arPlan.planSha256});display(r.saved);dirty=false;await attributionRuleView();message('규칙을 저장했습니다. 승인은 Bifrost가 합니다.');}
async function attributionRuleView(){if(!v2Mode())return migrationView();$('view').innerHTML='<p>귀속·영향 규칙을 읽고 있습니다…</p>';arData=await expressionApi('/api/attribution-rule');if(tab!=='attributionRules')return;arPlan=null;for(const k of Object.keys(arBlocks))arBlocks[k]=structuredClone(arData[k]).map(d=>{const {artifactId,...rest}=d;return rest;});
 $('view').innerHTML='<p class="step">연결 / 귀속·영향 규칙</p><h2>공정 측정값을 방문에 귀속하는 규칙과 사고 영향 규칙을 적으세요</h2><p>forseti가 읽는 두 문서 종류(계약 2.27.0)와 두 바인딩 프로필(evidence-artifact 1.1.0의 파일)입니다. 멤버는 아래 목록의 <code>mappingSetRef</code>·<code>mappingId</code>·<code>metric</code>·<code>semanticId</code>를 그대로 적고, 스테이션과 설비 경로는 계층 경로(<code>:</code>로 이은 루트부터의 경로)로 적습니다. Tyr는 Bifrost와 같은 거절 코드로 미리 검사하며, 승인은 Bifrost가 합니다.</p>'+(arData.findings.length?'<section class="validation"><p>현재 검사 결과</p><ul>'+arData.findings.map(f=>'<li>'+esc(f.ruleCode+' · '+(f.message||''))+'</li>').join('')+'</ul></section>':'')
 +'<section class="card"><h3>규칙이 이름 붙일 수 있는 멤버</h3><p class="hint">계층: '+esc(arData.hierarchy?arData.hierarchy.id+' @ '+arData.hierarchy.version:'(없음 — 설비 계층을 먼저 작성하세요)')+' · 인용 가능한 근거: '+esc(arData.citable.join(', '))+'</p>'+arCatalog()+'</section>'
 +'<form id="ar-author">'+Object.keys(arBlocks).map(k=>'<section class="card"><h3>'+esc(arTitles[k])+'</h3><div id="ar-'+k+'"></div><button type="button" class="secondary" data-ar-add="'+k+'">추가</button></section>').join('')+'<div class="actions"><button type="submit">검증</button><button type="button" id="ar-save" disabled>저장</button></div><div id="ar-plan"></div></form>';
 arBlockList();document.querySelectorAll('[data-ar-add]').forEach(b=>b.onclick=()=>{arBlocks=arRead();arBlocks[b.dataset.arAdd].push(arTemplate(b.dataset.arAdd));arBlockList();arInvalidate();});
 $('ar-save').onclick=()=>recordTask(arSave);$('ar-author').addEventListener('input',arInvalidate);$('ar-author').addEventListener('change',arInvalidate);dirty=false;}
const beforeAttributionRule=render;render=function(){if(tab==='attributionRules'){document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));attributionRuleView().catch(e=>message(e.message,true));}else beforeAttributionRule();};
document.addEventListener('submit',e=>{if(e.target.id==='ar-author'){e.preventDefault();recordTask(arCompose);}});
```

- [ ] **Step 13.6** `frontend/index.html`: after `<button data-tab="commandBindings">명령 링크</button>` insert `<button data-tab="attributionRules">귀속·영향 규칙</button>`; after `<script src="/command-binding.js"></script>` insert `<script src="/attribution-rule.js"></script>`. `frontend/workflow.js` line 3: `connect` membership gains `'attributionRules'` after `'commandBindings'`. `scripts/test_workflow.py` line 66: both `25` become `26`.
- [ ] **Step 13.7** Run: `python -B scripts/test_attribution_rule.py Authoring` -> `Ran 5 tests ... OK`; whole module -> `Ran 100 tests ... OK`; `python -B scripts/test_workflow.py` -> OK (tab count 26, baseline pins unchanged: `docs/verification/workflow-baseline-pins.json` pins no frontend file). Open the screen once by hand (`python backend/server.py` per `README.md`, tab "귀속·영향 규칙"): the member table lists the fixture's mappings after the fixture workspace is loaded through `PUT /api/workspace`; "검증" then "저장" round-trips the fixture's four blocks.
- [ ] **Step 13.8** Commit: `feat(attribution-rule): authoring screen for rules and binding profiles`.

### Task 14: `docs/P4-J-ATTRIBUTION-RULE.md`

**Files:**
- Create: `docs/P4-J-ATTRIBUTION-RULE.md`

The step documents of this repository are Korean (`docs/P4-I-COMMAND-BINDING.md` is the form to follow: `## 범위`, `## 계약 <version>`, `## Tyr 검사`, `## 발행`, `## 작성 화면`, `## Bifrost와의 경계`, `## 시험`); terminology follows the organization glossary (`yggdrasil-iiot/.github` `profile/GLOSSARY.md`); product names in ASCII (Mimir, Tyr; `scripts/check-ascii-names.sh`). The facts each section states are fixed here, so the prose can be checked against this list.

- [ ] **Step 14.1** Sections and the facts each must carry:
  - `# P4-J 귀속·영향 규칙(attribution rule, impact rule)`
  - `## 범위`: forseti step 2 (spec row 2; the spec PR of Task 1 and its number); two kinds in one contract version (Decision 3); Tyr authors both kinds, both profiles and the typed String sources a `plc-stamped` rule needs, Bifrost approves (two-key mapping release); no SQL or scripts; forseti is the consumer and holds the event schemas; `format.schemaSha256` is forseti's start-up check (`binding.schema-mismatch`), neither Tyr's nor Bifrost's; the list of what Tyr does not claim to verify (Conventions).
  - `## 계약 2.27.0`: five byte copies under `contracts/2.27.0/`; what `common` adds (`$id`, two kinds, `String` in typed value types); `mapping-proposal` constants; `source-definition` 2.27.0 = the 2.7.0 `plc` source so a controller's unit id and visit id publish as String (a 2.7.0 source still cannot); `rule.envelope`; a 2.26.0 command link rides in a 2.27.0 proposal; `test_p6` proves the bytes against `../bifrost`.
  - `## 문자열 소스와 PLC 소스 폼`: the form offers `String` for typed access (symbol, OPC UA) and writes such a source at 2.27.0 (`app.js` `accessFields`, `mixed.js` `draftSource`); the backend path (`PUT /api/workspace` -> `check_state` -> `validate_schema` / `source_rules`); a 1.x workspace refuses a 2.27.0 source as it refuses 2.7.0; not offered in step 2: a fixed-array String source and a 2.10.0 view of a String source (both stay schema refusals); the fixture identity sources are the form's output shape.
  - `## 바인딩 프로필`: Decision 4; evidence-artifact 1.1.0, id prefixes, media types, `profileVersion` 0.1.0, `scope` = station ids; the two field sets (spec 206-222); `reasons` subset; `identity.pattern` subset (spec 225) and Bifrost's extra refusals (surrogates, group depth 32, repetition bounds above 2147483647, inverted class ranges) as the spec PR records them; Tyr authors the profile (workspace records `occupancyBindings`, `incidentBindings`, editor schemas with `reviewer`, limit 64, `profile` object serialized by `vc.save`, SHA-256 pinned by the wrapper); the workspace codes `occupancy-binding.schema|duplicate|scope|limit|version-required` and the same for `incident-binding`, named as Tyr's own; `schemaSha256` placeholders until step 3 (Open point 5).
  - `## Tyr 검사`: the eleven `attribution.*` codes and the five `impact.*` codes with their conditions as the spec tables state them (lines 142-154, 182-188), the member resolution rule (line 132), the one-role rule, the coverage rule under `plc-stamped` (line 135), `rule.envelope`; a broken hierarchy keeps its own `hierarchy.*` code and no rule check runs (spec 130); what Tyr leaves to Bifrost (approval, attestation, release, context checks) and to forseti (`binding.schema-mismatch`, incident kinds); `attribution-rule: schema validation failed` / `duplicate id` / `attribution-rule.limit` and the impact counterparts at the workspace level; Tyr writes 2.27.0 rules only.
  - `## 발행`: `attribution-rules/<n>.json`, `impact-rules/<n>.json`, proposal 2.27.0 (also for a 2.27.0 source without rules); closure (rule with every mapping set it reads, impact with its attribution rule, profiles through their references, hierarchy always); stream `line2` in the fixtures; the committed bundles (39 and 59 files) are the build of the workspaces and a test re-proves the bytes.
  - `## 작성 화면`: `GET /api/attribution-rule`, `POST /api/attribution-rule-plan`, `POST /api/attribution-rule-apply`; the member catalog and paths; JSON blocks; `attribution-rule.plan-changed`; approval by Bifrost.
  - `## Bifrost와의 경계`: zero shared code; Bifrost's `AttributionRules`, `ImpactRules`, `OccupancyBindingProfile`, `IncidentBindingProfile` validate independently; `gates mapping approve` is the completion gate; the parity matrix (one mutated bundle per refusal code, same code from both sides; the 26 rows incl. duplicate JSON keys and 10,000-deep nesting in both profiles, then the accepted cases: `rule.envelope` on a Tyr-published bundle, the Java boundary bound, the 4,500-leading-zeros bound, a UTF-8 BOM before either profile); Bifrost's own fixtures (`attribution-impact`, `attribution-plc-stamped`) are the same two shapes written by hand in step 1; a Bifrost copy of Tyr's bundles is the Follow-up.
  - `## 시험`: `scripts/test_attribution_rule.py` (100 by class as the run prints them), `scripts/test_impact_rule.py` (23), the two fixture workspaces and bundles, what each class proves, the approval seam, the fault injections run (remove the closure line -> the publication tests fail; remove `rule.envelope` -> the envelope tests fail; remove the identity block -> nine `PlcStamped` tests fail; remove the bound check in `quantifier()` -> `Pattern.test_quantifier_bounds_follow_java` and the `binding-profile-bound-above-int` parity row fail, while the `-above-uint` and `-above-long` rows still refuse through Python's `OverflowError` at compile time; drop `object_pairs_hook=vc.pairs` -> the two duplicate-key unit tests and two parity rows fail; drop `RecursionError` from the parsers' except clause -> the two deep-nesting unit tests and two parity rows crash instead of refusing; parse `raw.decode('utf-8')` instead of the bytes -> the two BOM unit tests and two accepted parity cases fail; drop the leading-zero strip -> `Pattern.test_leading_zeros_are_javas_value` and the accepted-pattern parity case fail), each recorded with the number that failed.
- [ ] **Step 14.2** `bash scripts/check-ascii-names.sh` -> `product names: ASCII only`. `git diff --check` clean.
- [ ] **Step 14.3** Commit: `docs: describe attribution and impact rule authoring (P4-J)`.

### Task 15: Full run, CI, pull request

**Files:** none

- [ ] **Step 15.1** Bifrost checkout at `33e864c`, jar built (Task 0). Run the Verification block below from the Tyr root; every command ends as stated.
- [ ] **Step 15.2** `git log --oneline main..` shows 13 commits (Tasks 2-14). `git status --short` empty.
- [ ] **Step 15.3** Push the branch; open the PR against `main` with the title `feat: author attribution and impact rules for forseti (contract 2.27.0)`. The body (prose pipeline) states: the spec row and the forseti spec PR (Task 1, must merge first), the owner decisions Q1-Q4, the two kinds, two profiles and the String source form, the mirrored codes and what Bifrost alone decides, the two fixture workspaces and that Bifrost's CLI approves both committed bundles in CI, the parity matrix count (26 rows + 5 accepted cases), the Open points below that still need a decision, and the Follow-up. Do not merge; merge and push to `main` are the user's call.
- [ ] **Step 15.4** CI: the `contracts + tests (with Bifrost)` job is green; its log shows `test_attribution_rule: ok ran=100 failures=0 errors=0 skipped=0 excluded=0`, `test_impact_rule: ok ran=23 ...`, `excluded_bifrost_seam=0`, `failed_modules=0` (record the actual counts in the PR body if they differ from the plan's arithmetic).

## Open points

The plan applies everything settled by the spec and the owner's decisions (tool level `WORKUNIT_11`, the spec PR, the parity breadth, the form, the committed bundles). The following items stay open for step 2 by the owner's Q4 decision or were found while reading the code. Each carries a recommendation and its reason; none is decided here, and none changes Tyr in this step.

1. **`enter.bizStep` equal to `leave.bizStep`.** Bifrost accepts it (spec 211-212 only require non-empty values); Tyr's parser mirrors Bifrost (`test_enter_equal_to_leave_is_accepted_as_bifrost_accepts_it`). Recommendation: apply a later spec change ("`enter.bizStep` and `leave.bizStep` are distinct, else `attribution.binding-profile`") to Bifrost and Tyr in one contract or profile revision, not as a Tyr-only refusal. Reason: forseti tells an arrival from a departure by `bizStep` (spec "Input events"). Equal values make every event both, which no job can process, so it is a validity rule and belongs in the spec. A Tyr-only refusal would make Tyr stricter than the approver and could not be verified by the parity matrix.
2. **The 2.27.0 typed `String` value type is open to every typed access kind.** The 2.27.0 common adds `String` to the typed branch of `rawRepresentation`. Every `plc` access kind with `mode: typed` uses this branch (symbol and OPC UA), not only `opcua-node`. The form of Task 4 offers it for both typed profiles, as the published contract does, and the fixtures use `opcua-node` only. Recommendation: leave the schema as it is and state in the spec that forseti reads String members only from OPC UA sources published by Muninn; do not add a Tyr-only refusal. Reason: the restriction is a consumer fact (Muninn publishes OPC UA; forseti reads Sparkplug), not a contract fact. Other typed kinds carrying String may serve other consumers later, and a Tyr-only rule would diverge from Bifrost.
3. **Equipment ids and paths may contain `/`.** The contract `id` pattern `^[a-z][a-z0-9._/-]*$` allows `/`, which is not legal in a Sparkplug `device_id` (nor `+`, `#`). Tyr's workspace equipment id regex (`backend/server.py` line 46, `ID = ^[a-z][a-z0-9._/-]*$`) allows it as well, so a Tyr-authored hierarchy can carry `/` (the submission, stream and principal ids of `publication.py` line 9 are the stricter ones). The fixtures use slash-free ids. Recommendation: tighten the governed device-id contract separately (a Bifrost check on hierarchy node ids, and therefore station paths, recorded in the spec), rather than a Tyr-only refusal or a silent escape in Tyr. Reason: the gap is in the wire-name policy that two receivers share (Muninn's device id, forseti's `readPoint`), so it belongs to the contract both read. A Tyr-only rule would not protect a hand-made bundle.
4. **`identity.pattern` has no length cap and accepts catastrophic-backtracking shapes.** The subset allows nested quantifiers such as `(?:a+)+` and any length. Tyr's parser mirrors Bifrost's, including the bounds Bifrost's `Pattern.compile` applies (now pinned by parity). Recommendation: a later spec amendment with a length cap (for example 256) and a refusal of a quantified group whose body ends in a quantifier, applied to Bifrost and Tyr together. Reason: the pattern is governance-approved input that forseti compiles with Java's backtracking engine. A cap in Tyr alone would not protect the job (a hand-made bundle bypasses Tyr) and would make Tyr stricter than the approver.
5. **`format.schemaSha256` of the fixtures.** Forseti's occupancy and incident schemas do not exist until step 3, so both fixtures carry the step-1 placeholders (`...0001`, `...0002`), which Bifrost checks for form only (spec 204). Recommendation: when step 3 publishes the schemas, re-author both profile records with the real digests, rebuild and re-pin the bundles (and Bifrost's fixtures) in one commit, and let forseti's `binding.schema-mismatch` test cite them. Reason: the job refuses to start on a stale digest, so a placeholder can never leak into a run; carrying it now keeps step 2 independent of step 3's timing.
6. **Schema versus code on `members[]` cardinality.** Spec line 132 makes an empty `members[]` `attribution.member-unresolved`. The 2.27.0 schema has no `minItems` on `members` (it has `minItems: 1` on `stations` and `activity`), so Bifrost and Tyr both check it in code (parity row `member-unresolved` and `test_empty_members`). This is not a defect; it is recorded so a later schema revision does not add `minItems` and silently move the code to `mapping.schema:...`, which would break byte identity. No recommendation needed.
7. **Two-station fixtures versus the three-station sim of step 4.** Spec line 714 names three stations and two nutrunners. The step-1 and step-2 fixtures carry two stations, and the `plc-stamped` rule reads identity from `station1` and `nutrunner1` only. Recommendation: keep the two contract-test shapes for step 2 and do not claim sim coverage. Extend the fixtures in step 4 or 5 when the sim exists, with names and member types consistent with `Line2` (the fixtures already use its node identifiers). Reason: the fixtures prove the contract, not the scenario; a third station today would be an unverified guess at the sim.
8. **Version-change policy for authored profiles and rules.** The plan implements `occupancy-binding.version-required` / `incident-binding.version-required` for changed profile records. This is the transition every other Tyr evidence record has (`read_bindings.py`, `server_certificates.py`, `hierarchy_evidence.py`; `Store.save` runs each `transition`). The plan adds no transition for the rule documents, which, like `commandBindings` and `metricDefinitions`, are plain documents whose references carry versions and whose publication is immutable. Precedent decided it here. No recommendation needed unless the owner wants rules versioned on change as well.

## Follow-up (after the Tyr PR merges)

- **Bifrost copy of the Tyr bundles.** PR #19's `test_bifrost_receiver_accepts_the_same_bundle` compares the Tyr bundle with a copy under Bifrost `core/src/test/resources/mapping-fixtures/command-binding` that Bifrost PR #53 added (`MappingTyrCommandBindingTest`). Step 2 is Tyr-only, so this plan proves acceptance through the CLI and adds no `BIFROST_COPY` assertion (it would fail until the copy exists). The follow-up is a Bifrost PR copying `fixtures/attribution-rule/bundle` and `plc-stamped-bundle` under `mapping-fixtures/tyr-attribution-impact` and `tyr-attribution-plc-stamped` with a `MappingTyrAttributionRuleTest` (acceptance at 2.27.0; release and attestation carry both rules and both profile files, the way `MappingTyrCommandBindingTest.releaseAndAttestationCarryEachLinkAndItsReadBinding` does). A one-line Tyr PR then adds `self.assertEqual(tree(BIFROST_COPY),tree(BUNDLE))` (and the plc counterpart) to the two `test_fixture_bundle_is_the_build_of_the_fixture_workspace` tests. This is how the two repositories have pinned Tyr-built bundles since 2.23.
## Verification

Run from the Tyr repository root on `feat/attribution-rule-authoring` after Task 14, with the sibling Bifrost checkout at `33e864c` and its jar built; every command must end as stated.

```bash
git status --short                                             # empty
git log --oneline main..                                       # 13 commits, Tasks 2-14
git diff --check da764c0...HEAD                                # nothing
bash scripts/check-ascii-names.sh                              # product names: ASCII only
git -C ../forseti log --oneline main..docs/step2-decisions     # 1 commit (Task 1), its PR open or merged

# 0. the Bifrost side this step runs against
git -C ../bifrost rev-parse --short HEAD                       # 33e864c
ls ../bifrost/gates/target/bifrost-gates.jar                   # exists (mvn -B -ntp -pl gates -am package -DskipTests)

# 1. the new modules
python -B scripts/test_attribution_rule.py                     # Ran 100 tests ... OK  (Contract 2, StringSource 6, OccupancyProfile 10, Pattern 7,
                                                               #   BindingProfiles 4, AttributionRule 38, Publication 5, PlcStamped 18, Parity 2, Approval 3, Authoring 5)
python -B scripts/test_impact_rule.py                          # Ran 23 tests ... OK  (IncidentProfile 9, ImpactRule 14)

# 2. what CI runs
python -B scripts/validate_contracts.py --deny-network --report build/p1-validation.json   # "failed": []
python -B scripts/test_p3a.py --report build/p3a.json          # exit 0
python -B scripts/ci_run.py                                    # every module ok; test_attribution_rule ran=100, test_impact_rule ran=23,
                                                               #   test_command_binding ran=52, test_workflow ok (26 tabs), test_p6 ok (shared schema copies);
                                                               #   excluded_bifrost_seam=0 failed_modules=0

# 3. the step-2 completion gate at the CLI, outside unittest, for both committed bundles
#    (identity keygen prints the authorized-keys line on stdout; the policy names stream line2, the fixtures' submission stream)
JAR=../bifrost/gates/target/bifrost-gates.jar
for F in bundle plc-stamped-bundle; do
  W=build/step2/$F; rm -rf "$W" && mkdir -p "$W/keys" "$W/reg/identity"
  for who in proposer approver; do java -jar "$JAR" identity keygen "$who" --out "$W/keys" >> "$W/reg/identity/authorized-keys.jsonl"; done
  cat > "$W/reg/identity/activation-policy.json" <<'JSON'
{"version":"1.0.0","default":"deny","rules":[
 {"id":"p","principal":"proposer","action":"publish","target":"mapping-publication","kind":"mapping-release","ref":"line2"},
 {"id":"a","principal":"approver","action":"approve","target":"mapping-publication","kind":"mapping-release","ref":"line2"}]}
JSON
  B=fixtures/attribution-rule/$F
  find "$B" -type f | wc -l                                    # 39 for bundle, 59 for plc-stamped-bundle
  java -jar "$JAR" mapping validate "$B"
  #   -> {"kind":"mapping-validation",...,"accepted":true,"findings":[],...}  exit 0
  java -jar "$JAR" mapping approve "$W/reg" "$B" approval-1 \
    --by proposer --by-key "$W/keys/proposer.key" --approved-by approver --approved-by-key "$W/keys/approver.key"
  #   -> {"kind":"mapping-approval","schemaVersion":"2.9.0","payload":{"streamId":"line2",...,"execution":"excluded"},...}  exit 0
  ls "$W/reg/mappings/approvals/approval-1.json" "$W/reg/mappings/attestations/approval-1.dsse.json"   # both exist
done

# 4. the bundles are the build of the workspaces (also a test; here by hand)
rm -rf build/step2/rebuilt && python -B - <<'PY'
import sys;from pathlib import Path
R=Path('.').resolve();sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server,publication
from test_attribution_rule import tree   # recursive {relative path: bytes}, the comparison the unittest uses (filecmp.dircmp would compare the top level only)
for ws,out,sid in (('workspace.json','bundle','attribution-fixture'),('plc-stamped-workspace.json','plc-stamped-bundle','attribution-plc-stamped-fixture')):
    dest=R/'build/step2/rebuilt'/out
    publication.build(server.contracts.load(R/'fixtures/attribution-rule'/ws),dest,sid,'line2','proposer',None,['station1-mapping','station2-mapping','nutrunner1-mapping','nutrunner2-mapping'],False,server.build_package)
    assert tree(dest)==tree(R/'fixtures/attribution-rule'/out),out;print(out,'byte-identical,',len(tree(dest)),'files')   # -> bundle byte-identical, 39 files / plc-stamped-bundle byte-identical, 59 files
PY

# 5. parity, one row at the CLI by hand (the test runs all 22 + 2): the impact retention row
rm -rf build/step2/row && cp -r fixtures/attribution-rule/bundle build/step2/row && python -B - <<'PY'
import sys;from pathlib import Path
R=Path('.').resolve();sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
import server
from test_attribution_rule import repinned
b=R/'build/step2/row';r=server.contracts.load(b/'impact-rules/0.json');r['retention']['workRecordsMs']=3600000;server.contracts.save(b/'impact-rules/0.json',r);repinned(b)
PY
python -B scripts/p3a_contracts.py --package build/step2/row    # "valid": false, findings include {"ruleCode":"impact.retention-order",...}
java -jar "$JAR" mapping validate build/step2/row
#   -> "accepted":false, findings [{"ruleCode":"impact.retention-order",...}]  exit 1

# 6. a 2.26.0 proposal cannot carry the kinds (a test; here at the CLI)
rm -rf build/step2/old && cp -r fixtures/attribution-rule/bundle build/step2/old && python -I - <<'PY'
import hashlib,json;from pathlib import Path
r=Path('build/step2/old');p=json.loads((r/'proposal.json').read_bytes());p['schemaVersion']='2.26.0'
(r/'proposal.json').write_bytes((json.dumps(p,indent=2)+'\n').encode())
s=json.loads((r/'submission.json').read_bytes());s['proposalSha256']=hashlib.sha256((r/'proposal.json').read_bytes()).hexdigest()
(r/'submission.json').write_bytes((json.dumps(s,indent=2)+'\n').encode())
PY
java -jar "$JAR" mapping validate build/step2/old
#   -> "accepted":false, one finding "ruleCode":"mapping.schema:2.26.0/mapping-proposal"  exit 1
python -B scripts/p3a_contracts.py --package build/step2/old     # "valid": false, findings [{"ruleCode":"schema","path":"proposal.json"}]

# 7. on GitHub: the forseti spec PR (Task 1) merged or open; the Tyr CI job green on the PR with the counts above; main unchanged until the user says merge
```

(On Windows under Git Bash, pass the jar, registry, bundle and key paths through `cygpath -m` if `java` cannot open them, as Bifrost's gate scripts do.)

### Refusal-code coverage

Every code of the spec's three tables has at least one test through `server.check_state` (workspace) or `validate_package` (package) and one parity row against Bifrost's jar; the gate's own verdict is checked for both committed bundles and for a refused bundle.

| Code | Tyr test(s) | Parity row(s) |
|---|---|---|
| `attribution.hierarchy-missing` | `test_hierarchy_missing` | `hierarchy-missing` |
| `attribution.station-unresolved` | `test_station_unresolved`, `test_package_checks_without_workspace`, `Authoring.test_plan_refuses_with_the_spec_code` | `station-unresolved` |
| `attribution.station-nested` | `test_station_nested` | `station-nested` |
| `attribution.member-unresolved` | `test_empty_members`, `test_member_set_unresolved`, `test_member_mapping_unresolved`, `test_member_of_another_set`, `test_member_metric_must_equal_the_leaf_name`, `test_member_semantic_id_must_equal_the_leaf`, `test_member_listed_twice`, `test_member_source_identifier_must_end_with_the_metric`, `test_duplicate_leaf_names_in_one_definition_are_refused`; allowed across definitions: `test_a_station_and_a_tool_may_each_have_a_member_named_running` | `member-unresolved` |
| `attribution.member-equipment` | `test_member_equipment_outside_the_stations` | `member-equipment` |
| `attribution.activity-member` | `test_activity_member_unresolved`, `test_activity_member_must_be_boolean`, `test_activity_member_must_belong_to_its_equipment`, `test_activity_equipment_must_be_a_station_or_below`, `test_two_activity_entries_for_one_equipment`, `PlcStamped.test_two_activity_entries_with_different_members_for_one_equipment`; allowed: `test_an_equipment_without_an_activity_entry_is_accepted` | `activity-member` |
| `attribution.binding-unresolved` | `test_binding_unresolved`, `test_binding_must_be_an_artifact_1_1_0` | `binding-unresolved` |
| `attribution.binding-profile` | `test_binding_artifact_must_carry_the_prefix_and_media_type`, `test_binding_profile_refused_on_the_package_alone`, `BindingProfiles.test_record_refusals`, the `OccupancyProfile` and `Pattern` classes; scope not compared: `test_binding_scope_is_not_compared_with_the_stations` | `binding-profile-artifact`, `binding-profile-pattern`, `binding-profile-extra-field`, `binding-profile-bound-above-int`, `-above-uint`, `-above-long`, `binding-profile-duplicate-key`, `binding-profile-deep-json`; accepted boundary bound, leading-zeros bound and BOM-prefixed file in `test_rule_envelope_and_the_accepted_patterns_agree_with_bifrost` |
| `attribution.identity-member` | `PlcStamped.test_identity_unit_member_must_be_string`, `..._present_member_must_be_boolean`, `..._member_unresolved`, `..._member_must_belong_to_the_entrys_equipment`, `..._present_ref_naming_the_activity_member_is_refused`, `..._ref_shared_across_two_entries_is_refused`; order independence: `..._entry_order_does_not_matter` | `identity-member` |
| `attribution.identity-equipment` | `PlcStamped.test_identity_equipment_missing`, `..._equipment_duplicate`, `..._entry_for_an_equipment_without_members_is_refused`, `..._only_equipment_may_not_carry_an_identity_entry` | `identity-equipment` |
| `attribution.temporal-order` | `test_temporal_order` (both orders and the equal-bounds acceptance) | `temporal-order` |
| `hierarchy.*` kept on an invalid hierarchy (spec 130) | `test_an_invalid_hierarchy_keeps_its_own_refusal_and_runs_no_rule_check` | (Bifrost's own `hierarchy.cycle`; not a 2.27 code) |
| schema refusals the spec names no code for | `test_duplicate_or_empty_stations_are_schema_refusals`, `test_empty_activity_is_a_schema_refusal`, `test_expected_period_zero_is_a_schema_refusal`, `test_identity_entries_are_schema_bound_to_plc_stamped`, `PlcStamped.test_plc_stamped_needs_a_namespace_and_entries`, `test_older_version_is_not_written` | - |
| optional `namespace`, `crossCheck: occupancy` under both modes | `test_a_namespace_and_cross_check_occupancy_are_allowed_under_occupancy_join`, `PlcStamped.test_cross_check_none_is_allowed_under_plc_stamped`, the plc fixture itself (`crossCheck: occupancy`) | - |
| `impact.attribution-missing` | `test_attribution_missing`, `test_package_without_the_attribution_rule` | `impact.attribution-missing` |
| `impact.scope-containment` | `test_scope_must_be_in_the_hierarchy`, `test_scope_must_be_under_an_attribution_station`; allowed: `test_a_station_itself_is_in_scope` | `impact.scope-containment` |
| `impact.binding-unresolved` | `test_binding_unresolved` (impact class, both forms) | `impact.binding-unresolved` |
| `impact.binding-profile` | `test_binding_artifact_must_carry_the_prefix_and_media_type` (impact class), `test_binding_profile_refused_on_the_package_alone` (impact class), `BindingProfiles.test_record_refusals`, the `IncidentProfile` class | `impact.binding-profile-artifact`, `impact.binding-profile-kinds`, `impact.binding-profile-duplicate-key`, `impact.binding-profile-deep-json`; BOM-prefixed file accepted in `test_rule_envelope_and_the_accepted_patterns_agree_with_bifrost` |
| `impact.retention-order` | `test_retention_order` (and the equal-to-horizon acceptance) | `impact.retention-order`; refusal through approve: `Approval.test_a_refused_bundle_leaves_no_receipt` |
| impact schema refusals | `test_duplicate_or_empty_scope_is_a_schema_refusal`, `test_retention_above_90_days_is_a_schema_refusal`, `test_older_version_is_not_written` (impact class) | - |
| typed `String` at 2.27.0 (row 1) and the form | `Contract.test_2_27_source_definition_is_the_2_7_plc_source`, `StringSource.*` (incl. `test_plc_source_form_offers_string_for_typed_access_and_writes_2_27`), `PlcStamped.test_accepted_and_packaged_with_typed_string_sources`, `PlcStamped.test_identity_sources_are_what_the_plc_form_writes` | the plc bundle's `validate` and `approve` |
| `rule.envelope` (row 1) | `StringSource.test_a_2_27_source_needs_a_2_27_proposal`; the kinds in a 2.26.0 proposal are a schema refusal: `AttributionRule.test_older_envelope_refused`; a 2.26.0 link in a 2.27.0 proposal: `StringSource.test_a_2_26_command_binding_rides_in_a_2_27_proposal` | `test_rule_envelope_and_the_accepted_patterns_agree_with_bifrost` (a Tyr-published bundle with mapped 2.27.0 String sources and no rules) |
| byte-identical contract copies | `test_p6.Receiver.test_shared_schema_copies`, `Contract.test_2_27_schemas_extend_2_26_only_where_intended` | - |
| authored profile files | `BindingProfiles.test_packaged_as_evidence_artifacts_with_the_spec_prefix_and_media_type`, `test_changed_profile_needs_a_new_version`, `test_without_profiles_unchanged` | - |
| publication closure | `Publication.*`, `PlcStamped.test_fixture_bundle_is_the_build_of_the_fixture_workspace` | - |
| completion gate | `Approval.test_bifrost_approves_the_occupancy_join_bundle`, `test_bifrost_approves_the_plc_stamped_bundle`, Verification step 3 | - |
