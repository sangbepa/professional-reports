"""Bounded scalar price inversion; no valuation assumptions or market data."""
import math

def solve(price, target, low, high, *, samples=81, price_tolerance=1e-6, iterations=100):
    if not all(math.isfinite(x) for x in (target,low,high)) or target<=0 or low>=high:
        raise ValueError('Finite positive target and ordered bounds required')
    if samples<3 or price_tolerance<=0 or iterations<1:
        raise ValueError('Invalid numerical controls')
    points=[]
    for i in range(samples):
        x=low+(high-low)*i/(samples-1);y=float(price(x))
        if not math.isfinite(y):raise ValueError('Nonfinite forward price')
        points.append((x,y-target))
    brackets=[];roots=[]
    for x,y in points:
        if abs(y)<=price_tolerance:roots.append(x)
    for (a,fa),(b,fb) in zip(points,points[1:]):
        if fa*fb<0:brackets.append((a,b,fa,fb))
    for a,b,fa,fb in brackets:
        for _ in range(iterations):
            x=(a+b)/2;fx=float(price(x))-target
            if not math.isfinite(fx):raise ValueError('Nonfinite forward price')
            if abs(fx)<=price_tolerance:break
            if fa*fx<0:b,fb=x,fx
            else:a,fa=x,fx
        else:return dict(status='not_converged',roots=roots,bounds=[low,high])
        roots.append(x)
    roots=sorted(roots)
    unique=[]
    for x in roots:
        if not unique or abs(x-unique[-1])>1e-9:unique.append(x)
    return dict(status='no_bracket' if not unique else 'multiple_roots' if len(unique)>1 else 'solved',
                roots=unique,bounds=[low,high],samples=samples,
                observed_grid_monotonic=all(b[1]>a[1] for a,b in zip(points,points[1:])),
                root_completeness='Sign-changing roots on sampled intervals only; tangencies may be missed',
                price_tolerance=price_tolerance)
