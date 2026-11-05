"""2.26 server certificates: the DER a command link's endpointRef names, read with Tyr's own parser (`cryptography`).

Tyr derives the same two values Bifrost re-derives at publish and Heimdall compares with the live session: the SHA-1
of the DER in lowercase hex and the certificate's single subjectAltName URI. The DER is never re-encoded. A PEM file
is accepted only at import, as exactly one CERTIFICATE block whose base64 body is the DER.
"""
import base64,binascii,hashlib,re
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
PREFIX='server-certificate-'
MEDIA='application/pkix-cert'
PEM=re.compile(rb'\A\s*-----BEGIN CERTIFICATE-----\r?\n([A-Za-z0-9+/=\r\n]+)-----END CERTIFICATE-----\s*\Z')

def parse(der):
 """(thumbprintSha1, applicationUri), or ValueError 'certificate' (not exactly one X.509 DER) / 'san-uri' (not exactly one URI)."""
 try:c=x509.load_der_x509_certificate(der)
 except ValueError as e:raise ValueError('certificate') from e
 if c.public_bytes(Encoding.DER)!=der:raise ValueError('certificate')
 try:uris=c.extensions.get_extension_for_class(x509.SubjectAlternativeName).value.get_values_for_type(x509.UniformResourceIdentifier)
 except x509.ExtensionNotFound:uris=[]
 except ValueError as e:raise ValueError('san-uri') from e
 if len(uris)!=1:raise ValueError('san-uri')
 return hashlib.sha1(der).hexdigest(),uris[0]

def der(raw):
 """The certificate's DER from an imported file: the bytes themselves, or the body of a single PEM CERTIFICATE block."""
 m=PEM.match(raw)
 if m is None:
  if raw.lstrip().startswith(b'-----'):raise ValueError('certificate')
  return raw
 try:return base64.b64decode(re.sub(rb'\s',b'',m.group(1)),validate=True)
 except (binascii.Error,ValueError) as e:raise ValueError('certificate') from e
