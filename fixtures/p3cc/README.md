# P3-C C bounded arithmetic fixtures

workspace.json: four PLC profiles, 12 sources, four objects and 16 property bindings. Each graph has add, dimensionless-gain multiply, unit-preserving divide and same-unit ratio. Existing synthetic access coordinates are reused; the gain word is an explicitly declared synthetic coefficient, not a verified field meaning of a vendor symbol/register.

samples.json and expected.json are independent specified oracles: actual 150 kPa, target 50 kPa, gain 2 -> sum 200 kPa, scaled 400 kPa, quotient 200 kPa, ratio 3. For 1/3, graph division is 0.3333333333333333333333333333333333; binary64 final cast is exactly 0.333333333333333314829616256247390992939472198486328125.

The same literal double oracle is recorded in expected.json. Graph approximation and final cast each emit loss.precision. Denominator zero emits value.divide-zero and no fabricated result.

Tests cover named input order, unit/type/output/policy failures, old-version refusal, cycles/evidence closure, lazy selector and temporal propagation, SQLite roundtrip/CAS/atomic refusal and publication closure. Java receives a separately copied data-only wire package and validates without importing Python.

No device communication, external SQL or write execution. Logical arithmetic support is not physical meaning/native vendor validation or field PoV.
