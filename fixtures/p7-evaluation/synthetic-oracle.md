# Synthetic independent numeric/meaning oracle

These are explicit synthetic expectations, not observed field truth. Definition hashes in oracle.json pin the existing regression workspace and do not independently prove correct source meaning. Values below were specified separately from the evaluator/preview outputs.

## actual

Canonical urn:tyr:concept:pressure.actual, Double, kPa, measurement. Process actual = 150. Structure array module index 1 actual = 100, index 2 actual = 220. All four profiles must converge on these values while retaining distinct equipment/object/member identities.

## target

Canonical urn:tyr:concept:pressure.target, Double, kPa, setpoint. Process target = 180. Module index 1 target = 110, index 2 target = 210. Actual and target are different meanings even if source names are alike.

## deviation

Canonical urn:tyr:concept:pressure.deviation, Double, kPa, measurement. Process actual minus target = -30.

## running

Canonical urn:tyr:concept:equipment.running, Boolean, unit not-applicable, status. Flag word 3 has bit 2 false, bits 0 and 1 true. Process running is false; both module states are true.

## precision loss

150 multiplied by 0.001 yields decimal 0.15. Its binary64 cast is exactly 0.1499999999999999944488848768742172978818416595458984375. The expected quality is uncertain and both issue/loss code sets contain loss.precision. This is a synthetic numeric oracle, not a production tolerance agreement.
