"""Offline acceptance: execute existing oracles, retain individual outcomes and input pins.
Allows numeric loopback only for local editor tests; this is not an OS firewall.
No contract/product/fixture mutation. All test writes use disposable SQLite.
"""
import argparse,datetime,hashlib,importlib,io,json,platform,socket,sys,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(R/"backend"),str(R/"scripts")]
MODULES=["test_p2","test_p3a","test_p3a_workspace","test_p3b","test_p3c","test_p3d","test_p3e","test_p3f","test_p4a","test_p4b","test_p5","test_p6"]
def pins():
    paths=[* (R/"contracts").rglob("*.json"),*(R/"fixtures").rglob("*"),*(R/"backend").glob("*.py"),*(R/"frontend").glob("*"),*(R/"scripts").glob("*.py")]
    return {p.relative_to(R).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file() and "__pycache__" not in p.parts}
class Results(unittest.TextTestResult):
    def __init__(self,*a,**k):super().__init__(*a,**k);self.rows=[]
    def addSuccess(self,t):super().addSuccess(t);self.rows.append({"id":t.id(),"passed":True})
    def addFailure(self,t,e):super().addFailure(t,e);self.rows.append({"id":t.id(),"passed":False,"reason":self._exc_info_to_string(e,t)})
    def addError(self,t,e):super().addError(t,e);self.rows.append({"id":t.id(),"passed":False,"reason":self._exc_info_to_string(e,t)})
    def addSkip(self,t,reason):super().addSkip(t,reason);self.rows.append({"id":t.id(),"passed":False,"skip":reason})
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--report",type=Path,default=R/"docs/verification/p7-validation.json");parser.add_argument("--resume",type=Path);args=parser.parse_args()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    before=pins();network=[];prior=None;retry=None
    if args.resume:
        prior=json.loads(args.resume.read_text(encoding="utf-8"))
        old=prior["sha256"]
        changed=[p for p in set(old)|set(before) if old.get(p)!=before.get(p)]
        assert changed==["scripts/test_p7.py"] or not changed,changed
        retry=[x["id"] for x in prior["failed"]]
        assert retry and all(x.startswith("test_") for x in retry)

    connect=socket.socket.connect;connect_ex=socket.socket.connect_ex;resolve=socket.getaddrinfo
    def allow(addr):
        if not isinstance(addr,tuple) or addr[0] not in ("127.0.0.1","::1"):
            network.append(repr(addr));raise RuntimeError("P7 outbound network denied")
    def guarded(s,a):allow(a);return connect(s,a)
    def guarded_ex(s,a):allow(a);return connect_ex(s,a)
    def dns(host,*a,**k):
        if host not in ("127.0.0.1","::1",None):allow((host,0))
        return resolve(host,*a,**k)
    # Prove the guard independently before executing the same guarded code paths.
    with patch.object(socket.socket,"connect",guarded),patch.object(socket.socket,"connect_ex",guarded_ex),patch.object(socket,"getaddrinfo",dns):
        try:socket.create_connection(("192.0.2.1",102),timeout=.1)
        except RuntimeError:pass
        else:raise AssertionError("Outbound guard did not reject probe")
        network.clear()
        suite=(unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(id) for id in retry) if retry else unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(m)) for m in MODULES))
        with args.report.with_suffix(".log").open("w",encoding="utf-8") as log:
            result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Results).run(suite)
        import validate_contracts
        contract=validate_contracts.gate()
    cli_report=args.report.with_name("p7-p3a.json" if args.report.name=="p7-validation.json" else args.report.stem+"-p3a.json")
    cli=subprocess.run([sys.executable,"-B",str(R/"scripts/test_p3a.py"),"--report",str(cli_report)],capture_output=True,timeout=240)
    cli_report.with_suffix(".log").write_bytes(cli.stdout+cli.stderr)
    if cli.returncode:raise RuntimeError("P3-A CLI failed; see p7-p3a.log")
    p3a=json.loads(cli_report.read_text(encoding="utf-8"))
    assert p3a["networkDenied"] and not p3a["failed"]
    retained=[x for x in prior["results"] if x["id"].startswith("test_") and x["passed"]] if prior else []
    rows=retained+result.rows+contract["results"]+[dict(x,id="p3a:"+x["id"]) for x in p3a["results"]]
    assert len({x["id"] for x in rows})==len(rows)

    report={"generatedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"python":platform.python_version(),"total":len(rows),"passed":sum(x["passed"] for x in rows),"failed":[x for x in rows if not x["passed"]],"results":rows,
    "network":{"pythonOutboundBlocked":True,"guardNegativeControlPassed":True,"unexpectedAttempts":network,"loopbackAllowed":True,"javaAndBrowserOSIsolation":"not-performed"},
    "excluded":["device-communication","external-sql-execution","write-execution","runtime-activation","field-PoV"],
    "inputsUnchanged":before==pins(),"sha256":before,
    "p1GovernanceAssessment":contract["governanceAssessment"],
    "execution":{"mode":"resume-failed-plus-P1-P3A" if prior else "full","retainedPassedTests":len(retained),"rerunTestIds":retry or [],"priorReportSha256":hashlib.sha256(args.resume.read_bytes()).hexdigest() if prior else None,"initialFailures":prior["failed"] if prior else [],"orchestrationChangesSincePrior":changed if prior else []},
    "p3aCliReportSha256":hashlib.sha256(cli_report.read_bytes()).hexdigest()}
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("total","passed","inputsUnchanged","network")}))
    return bool(report["failed"] or network or not report["inputsUnchanged"])
if __name__=="__main__":sys.exit(main())
