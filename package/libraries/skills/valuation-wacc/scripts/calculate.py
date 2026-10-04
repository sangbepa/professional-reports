"""Adapted portable CAPM/WACC helper; see provenance.json for original hash and changes."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def calculate(data):
    for key in ("currency", "monetary_unit"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key} is required")
    keys = ("risk_free", "erp", "beta", "pre_tax_debt_cost", "tax_shield_rate", "equity_market_value", "debt_market_value")
    for key in keys:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
    if not 0 <= data["tax_shield_rate"] < 1:
        raise ValueError("tax_shield_rate must be a decimal in [0,1)")
    if data["erp"] < 0 or data["pre_tax_debt_cost"] < 0:
        raise ValueError("ERP and debt cost must be nonnegative decimal rates")
    if data["equity_market_value"] <= 0 or data["debt_market_value"] < 0:
        raise ValueError("Positive market equity and nonnegative gross financing debt required")
    total = data["equity_market_value"] + data["debt_market_value"]
    if not math.isfinite(total):
        raise ValueError("Total market capital must be finite")
    ew = data["equity_market_value"] / total
    dw = data["debt_market_value"] / total
    ke = data["risk_free"] + data["beta"] * data["erp"]
    kd = data["pre_tax_debt_cost"] * (1 - data["tax_shield_rate"])
    wacc = ke * ew + kd * dw
    if not all(math.isfinite(v) for v in (ew, dw, ke, kd, wacc)) or wacc <= 0:
        raise ValueError("Selected inputs must produce a finite positive WACC")
    return dict(currency=data["currency"], monetary_unit=data["monetary_unit"], equity_weight=ew,
                debt_weight=dw, cost_of_equity=ke, after_tax_debt_cost=kd, wacc=wacc,
                checks=[dict(id="market-weight-tie", passed=math.isclose(ew+dw, 1, abs_tol=1e-12)),
                        dict(id="capm-rebuild", passed=math.isclose(ke, data["risk_free"]+data["beta"]*data["erp"], abs_tol=1e-12))],
                economic_review="pending", beta_policy="supplied selected beta; no automatic adjustment")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if args.out.exists():
        p.error("Use a fresh output path; prior versions are immutable")
    try:
        data = json.loads(args.input.read_text())
        bindings = data.get("input_bindings")
        if not isinstance(bindings, list) or not bindings:
            raise ValueError("Nonempty input_bindings required")
        base = args.input.resolve().parent
        for ref in bindings:
            if not isinstance(ref, dict) or not isinstance(ref.get("path"), str) or not isinstance(ref.get("sha256"), str):
                raise ValueError("Each input binding needs a relative path and sha256")
            path = Path(ref["path"])
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Input binding paths must stay relative to input directory")
            bound = (base / path).resolve()
            if not bound.is_relative_to(base):
                raise ValueError("Input binding escapes input directory")
            if digest(bound) != ref["sha256"]:
                raise ValueError("Input binding hash changed")
        result = calculate(data)
        result.update(input_sha256=digest(args.input), helper_sha256=digest(__file__), input_bindings=bindings)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as output:
            output.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    except (ValueError, KeyError, OSError) as exc:
        p.error(str(exc))


if __name__ == "__main__":
    main()
