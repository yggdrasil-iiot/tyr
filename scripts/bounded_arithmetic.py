"""Finite scalar arithmetic policy; no expression parser or dimensional inference."""
from decimal import Decimal,Inexact,localcontext,ROUND_HALF_EVEN
OPS={"add","multiply","divide"}
LINEAR_UNITS={"1","Pa","kPa","bar","rpm","1/s","N.m","mN.m"}
def unit_for(op,left,right):
    if op not in OPS or any(u.get("status")!="known" or u.get("code") not in LINEAR_UNITS for u in (left,right)):raise ValueError("graph.input-unit")
    l,r=left["code"],right["code"]
    if op=="add" and l==r:code=l
    elif op=="multiply" and (l=="1" or r=="1"):code=r if l=="1" else l
    elif op=="divide" and r=="1":code=l
    elif op=="divide" and l==r:code="1"
    else:raise ValueError("graph.input-unit")
    return {"status":"known","code":code}
def calculate(op,left,right,precision=None,rounding=None):
    if not isinstance(left,Decimal) or not isinstance(right,Decimal) or not left.is_finite() or not right.is_finite():raise ValueError("graph.input-type")
    if op=="divide" and (precision!=34 or rounding!="half-even"):raise ValueError("arithmetic.divide-policy")
    if op=="divide" and right==0:raise ValueError("value.divide-zero")
    if op not in OPS:raise ValueError("operation.unsupported")
    with localcontext() as ctx:
        ctx.prec=34 if op=="divide" else 4096;ctx.rounding=ROUND_HALF_EVEN;ctx.clear_flags()
        value=left+right if op=="add" else left*right if op=="multiply" else left/right
        approximate=ctx.flags[Inexact]
        if op!="divide" and approximate:raise ValueError("value.numeric-limit")
        if not value.is_finite():raise ValueError("value.nonfinite")
        return value,approximate
