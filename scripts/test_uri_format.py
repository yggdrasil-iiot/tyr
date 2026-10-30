"""semanticId "format": "uri" is asserted the way Bifrost asserts it, so Tyr cannot pass what Bifrost refuses."""
import copy,json,sys,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'backend'),str(R/'scripts')]
from jsonschema import Draft202012Validator,FormatChecker
import validate_contracts as vc,p3a_contracts as p3a

VECTOR_FILE=R/'fixtures/uri-format/bifrost-vectors.json'
VECTORS=vc.load(VECTOR_FILE)['cases']
# Bifrost's copy (yggdrasil-iiot/bifrost#32), run by its UriFormatVectorsTest. Git may check it out with CRLF.
BIFROST_COPY=R.parent/'bifrost/core/src/test/resources/uri-format/vectors.json'
URI=Draft202012Validator({'type':'string','format':'uri'},format_checker=FormatChecker())
def model():return copy.deepcopy(vc.load(R/'fixtures/p3eb/nested-model.json'))
def formats(errors):return [e for x in errors for e in [x,*formats(getattr(x,'context',None) or [])] if getattr(e,'validator',None)=='format']

class UriFormat(unittest.TestCase):
 def test_every_contract_format_has_a_checker(self):
  self.assertIn('uri',vc.CONTRACT_FORMATS)
  self.assertEqual(vc.CONTRACT_FORMATS-set(FormatChecker.checkers),set())
 def test_same_verdict_as_bifrost(self):
  self.assertGreaterEqual(len(VECTORS),19)
  for c in VECTORS:
   with self.subTest(value=c['value']):
    self.assertEqual('accept' if URI.is_valid(c['value']) else 'reject',c['bifrost'])
 def test_bifrost_tests_the_same_vectors(self):
  lf=lambda p:p.read_bytes().replace(b'\r\n',b'\n')
  self.assertEqual(lf(BIFROST_COPY),lf(VECTOR_FILE))
 def test_semantic_definition_accepts_urn(self):
  self.assertEqual(p3a.schema_errors('semantic-definition',model()),[])
 def test_semantic_definition_refuses_non_uri(self):
  for bad in ('0173-1#02-AAO677#002','0112/2///61360_4#AAA123#001','nsu=http://opcfoundation.org/UA/;i=85','not a uri'):
   with self.subTest(semanticId=bad):
    d=model();d['members'][0]['semanticId']=bad
    self.assertIn(bad,[e.instance for e in formats(p3a.schema_errors('semantic-definition',d))])

if __name__=='__main__':unittest.main()
