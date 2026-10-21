# A07 explicit source views

Synthetic, offline-only. Four PLC representations share literal 0x8005 = 32773 (32768 + 4 + 1).
20 source definitions (4 direct words, 4 word aliases, 8 bit views, 4 aliases of bits),
4 objects, 4 identity graphs and 20 semantic bindings.

workspace.json is the authoring fixture; wire/ is an immutable exported proposal with complete parent/evidence closure.
oracles.json contains independent literal values, not generated preview results.
cases.json has 12 resealed negative mutations checked independently by Python and Java.
The old mapping-patterns cases retain their 1.x/P2 baseline classification.

Run scripts/test_a07.py. Receiver: Maven offline MappingPublicationTest and MappingGateTest.
Read ../../docs/A07-SOURCE-VIEWS.md and ../../docs/verification/A07-RESULTS.md.
Device communication, external SQL, write execution and activation are excluded.
