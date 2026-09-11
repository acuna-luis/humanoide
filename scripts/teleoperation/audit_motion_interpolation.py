#!/usr/bin/env python3
"""Offline emulation of a pinned Motion numeric routine; no robot connection."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists')
    import numpy as np
    from general_home.native_spline import NativeSplineEmulator,cubic_hermite,SHA256
    native=NativeSplineEmulator(args.binary)
    rng=np.random.default_rng(20260910);maximum=0.;count=0
    for n in (1,2,7,20):
        for duration in (.1,1.,3.75,10.):
            q0,q1=rng.uniform(-2,2,(2,n))
            for moving_ends in (False,True):
                v0,v1=rng.uniform(-.2,.2,(2,n)) if moving_ends else np.zeros((2,n))
                for elapsed in np.linspace(0,duration,41):
                    actual=native.evaluate(q0,q1,v0,v1,duration,elapsed)
                    expected=cubic_hermite(q0,q1,v0,v1,duration,elapsed)
                    maximum=max(maximum,float(abs(actual-expected).max()));count+=1
    if maximum > 1e-11:raise ValueError('Native arithmetic does not match cubic Hermite')
    if hashlib.sha256(args.binary.read_bytes()).hexdigest()!=SHA256:raise ValueError('Binary changed')
    result=dict(schema='cruzr-motion-numeric-interpolation-audit-v1',
        status='VERIFIED_BINARY_MATH_ONLY',samples=count,maximum_absolute_error=maximum,
        binary_sha256=SHA256,function_offset='0x37c0',
        zero_endpoint_velocity_law='q0+(q1-q0)*(3*u^2-2*u^3)',
        scope='Emulated numeric template; not full MetaMove/controller execution',
        limitations=['group dispatch/synchronization not exercised','tracking not measured',
                     'stopping not measured','cubic endpoint acceleration need not be zero'],
        emulator='unicorn',movement_commands=0,physical_approval=False)
    sources=[Path(__file__),Path(__file__).with_name('general_home')/'native_spline.py']
    result['source_sha256']={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    with args.output.open('x') as file:json.dump(result,file,indent=2);file.write('\n')
    print(json.dumps(result))


if __name__=='__main__':
    try:
        main()
    except (ValueError,OSError,ImportError,RuntimeError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        raise SystemExit(2)
