"""Visible method regression cases; no protected evaluation data or release claims."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

COMPONENT = Path(__file__).resolve().parents[1]
HELPER = COMPONENT / 'scripts/calculate.py'
spec = importlib.util.spec_from_file_location('wacc', HELPER)
wacc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wacc)


def sample():
    return dict(currency='TEST', monetary_unit='units', risk_free=.03, erp=.05,
                beta=1.2, pre_tax_debt_cost=.04, tax_shield_rate=.25,
                equity_market_value=80, debt_market_value=20)


class WaccChecks(unittest.TestCase):
    def test_weighted_capital_cost(self):
        r = wacc.calculate(sample())
        self.assertAlmostEqual(r['cost_of_equity'], .09)
        self.assertAlmostEqual(r['after_tax_debt_cost'], .03)
        self.assertAlmostEqual(r['wacc'], .078)
        self.assertEqual(r['economic_review'], 'pending')

    def test_unlevered_equity_cost(self):
        r = wacc.calculate(dict(sample(), debt_market_value=0))
        self.assertEqual(r['debt_weight'], 0)
        self.assertAlmostEqual(r['wacc'], .09)

    def test_net_cash_is_not_negative_financing_debt(self):
        with self.assertRaises(ValueError):
            wacc.calculate(dict(sample(), debt_market_value=-20))

    def test_nonfinite_and_boolean_inputs(self):
        for value in (True, math.nan, math.inf, -math.inf, '0.05'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                wacc.calculate(dict(sample(), erp=value))

    def test_market_capital_overflow(self):
        with self.assertRaises(ValueError):
            wacc.calculate(dict(sample(), equity_market_value=1e308, debt_market_value=1e308))

    def test_tax_boundaries(self):
        for tax in (-.01, 1, 1.5):
            with self.subTest(tax=tax), self.assertRaises(ValueError):
                wacc.calculate(dict(sample(), tax_shield_rate=tax))

    def test_invalid_equity_and_nonpositive_wacc(self):
        for overrides in ({'equity_market_value': 0}, {'risk_free': -.2}, {'pre_tax_debt_cost': -.1}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                wacc.calculate(dict(sample(), **overrides))

    def test_cli_bindings_and_immutable_output(self):
        with tempfile.TemporaryDirectory(dir=COMPONENT) as temp:
            root = Path(temp)
            evidence = root / 'selected-policy.txt'
            evidence.write_text('Synthetic selected-input evidence for a method regression test.\n')
            data = sample()
            data['input_bindings'] = [{'path': evidence.name, 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}]
            inp, out = root / 'input.json', root / 'result.json'
            inp.write_text(json.dumps(data))
            def run():
                return subprocess.run([sys.executable, '-B', str(HELPER), '--input', str(inp), '--out', str(out)], capture_output=True, text=True)
            self.assertEqual(run().returncode, 0)
            r = json.loads(out.read_text())
            self.assertAlmostEqual(r['wacc'], .078)
            self.assertEqual(r['helper_sha256'], hashlib.sha256(HELPER.read_bytes()).hexdigest())
            self.assertEqual(r['input_sha256'], hashlib.sha256(inp.read_bytes()).hexdigest())
            self.assertNotIn(str(root), out.read_text())
            original = out.read_bytes()
            self.assertNotEqual(run().returncode, 0)
            self.assertEqual(out.read_bytes(), original)
            out.unlink()
            evidence.write_text('Changed evidence')
            self.assertNotEqual(run().returncode, 0)
            self.assertFalse(out.exists())

    def test_cli_rejects_nonportable_or_missing_bindings(self):
        with tempfile.TemporaryDirectory(dir=COMPONENT) as temp:
            root = Path(temp)
            for bindings in ([], [{'path': '/not/portable', 'sha256': '0'*64}],
                             [{'path': '../outside', 'sha256': '0'*64}],
                             [{'sha256': '0'*64}], [{'path': 'absent', 'sha256': '0'*64}]):
                with self.subTest(bindings=bindings):
                    inp, out = root/'input.json', root/'result.json'
                    inp.write_text(json.dumps(dict(sample(), input_bindings=bindings)))
                    p = subprocess.run([sys.executable, '-B', str(HELPER), '--input', str(inp), '--out', str(out)], capture_output=True)
                    self.assertNotEqual(p.returncode, 0)
                    self.assertFalse(out.exists())

    def test_cli_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory(dir=COMPONENT) as temp:
            root = Path(temp)
            (root/'external-link').symlink_to(HELPER)
            inp, out = root/'input.json', root/'result.json'
            inp.write_text(json.dumps(dict(sample(), input_bindings=[{'path':'external-link','sha256':hashlib.sha256(HELPER.read_bytes()).hexdigest()}])))
            p = subprocess.run([sys.executable, '-B', str(HELPER), '--input', str(inp), '--out', str(out)], capture_output=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
