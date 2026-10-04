"""Independent, bounded replay of current selected originals; never financial approval.

No producer parser, extraction code or valuation model is used. Passing means
byte/coordinate/arithmetic agreement only, not semantic source acceptance.
"""
import argparse
import hashlib
import io
import json
import re
import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_ITEMS = 10000
MAX_MISMATCHES = 100
SOURCE_UNITS = {'KRW': '1', 'KRW_thousand': '1000', 'KRW_million': '1000000',
                'shares': '1', 'fraction': '1', 'percent': '.01', 'text': '1'}
TARGET_UNITS = {'KRW': '1', 'KRW per share': '1', 'KRW thousand': '1000',
                'KRW million': '1000000', 'KRW billion': '1000000000',
                'KRW trillion': '1000000000000', 'KRW_trillion': '1000000000000',
                'shares': '1', 'fraction': '1', 'ratio': '1', 'text': '1'}
LABELS = {'KRW': '원', 'KRW_thousand': '천원', 'KRW_million': '백만원',
          'shares': '주', 'percent': '%', 'fraction': '비율'}


class _OriginalTables(HTMLParser):
    """Tokenize DART mixed XML/HTML directly into table and text fragments."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = {}
        self.frames = []
        self.active = []
        self.outside = []
        self.serial = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.serial += 1
            if self.serial > MAX_ITEMS:
                raise ValueError('table limit exceeded')
            self.frames.append({'id': self.serial, 'rows': [],
                                'context': ' '.join(self.outside[-16:])[-1200:]})
        elif tag == 'tr' and self.frames:
            self.frames[-1]['rows'].append([])
        elif tag in ('td', 'th', 'te', 'tu') and self.frames:
            rows = self.frames[-1]['rows']
            if not rows:
                rows.append([])
            cell = []
            rows[-1].append(cell)
            self.active.append((tag, cell))

    def handle_endtag(self, tag):
        if tag in ('td', 'th', 'te', 'tu'):
            for n in range(len(self.active) - 1, -1, -1):
                if self.active[n][0] == tag:
                    self.active.pop(n)
                    break
        elif tag == 'table' and self.frames:
            frame = self.frames.pop()
            frame['rows'] = [[' '.join(' '.join(c).split()) for c in row]
                             for row in frame['rows']]
            self.tables[frame['id']] = frame

    def handle_data(self, text):
        if self.active:
            for _, cell in self.active:
                cell.append(text)
        elif not self.frames and text.strip():
            self.outside.append(' '.join(text.split()))
            self.outside = self.outside[-16:]


def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError('unsafe numeric type')
    n = Decimal(str(value))
    if not n.is_finite():
        raise ValueError('nonfinite number')
    return n


def _number(raw):
    if raw is None:
        return None
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float, Decimal)):
        raise ValueError('original must be scalar')
    text = str(raw).strip().replace(',', '').replace('−', '-')
    if text in ('', '-', '—'):
        return None
    if text.startswith('(') and text.endswith(')'):
        text = '-' + text[1:-1]
    if text.endswith('%'):
        text = text[:-1]
    if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?', text):
        raise ValueError('ambiguous numeric original')
    return _decimal(text)


def _coordinate(v, positive=False):
    if type(v) is not int or v < (1 if positive else 0):
        raise ValueError('unsafe coordinate type or negative index')
    return v


def _locate(data, kind, loc):
    if not isinstance(loc, dict):
        raise ValueError('unsafe locator type')
    if kind == 'table':
        if set(loc) != {'table', 'row', 'col'}:
            raise ValueError('unknown table locator')
        t = data[_coordinate(loc['table'], True)]
        return t['rows'][_coordinate(loc['row'])][_coordinate(loc['col'])], None
    if kind != 'json' or set(loc) != {'path'} or not isinstance(loc['path'], list) or not loc['path']:
        raise ValueError('unknown source kind or unsafe JSON locator')
    parent = None
    receipt = None
    for key in loc['path']:
        parent = data
        if isinstance(parent, dict):
            if type(key) is not str:
                raise ValueError('JSON object key must be string')
            receipt = parent.get('rcept_no', receipt)
        elif isinstance(parent, list):
            _coordinate(key)
        else:
            raise ValueError('JSON locator crosses scalar')
        data = parent[key]
    if isinstance(data, (dict, list, bool)):
        raise ValueError('selected JSON original must be scalar')
    return data, (parent, receipt)


class _Audit:
    def __init__(self, out):
        self.root = Path(out).resolve()
        self.cache = {}
        self.total = 0
        self.checks = []
        self.limitations = [
            'No period/perimeter semantic approval, source suitability approval, or report qualification.',
            'Only current selected scalar cells and supplied hash bindings are replayed.',
            'Recorded floating values are checked against the producer-compatible float representation; amount_exact uses exact Decimal.',
        ]

    def check(self, code, status, **detail):
        self.checks.append(dict(code=code, status=status, **detail))

    def equal(self, code, actual, expected, **detail):
        self.check(code, 'passed' if actual == expected else 'failed',
                   actual=actual, expected=expected, **detail)

    def path(self, name, source=False):
        if not isinstance(name, str) or not name or '\\' in name:
            raise ValueError('unsafe path type')
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('path escape')
        p = self.root.joinpath(*relative.parts).resolve()
        boundary = self.root / 'sources' if source else self.root
        if not p.is_relative_to(boundary):
            raise ValueError('symlink/path escape')
        return p

    def read(self, name, source=False):
        p = self.path(name, source)
        key = p.relative_to(self.root).as_posix()
        if key not in self.cache:
            if p.stat().st_size > MAX_FILE:
                raise ValueError('file size limit exceeded')
            with p.open('rb') as f:
                raw = f.read(MAX_FILE + 1)
            self.total += len(raw)
            if len(raw) > MAX_FILE or self.total > MAX_TOTAL:
                raise ValueError('input byte limit exceeded')
            self.cache[key] = (raw, hashlib.sha256(raw).hexdigest())
        return self.cache[key][0]

    def data(self, name, source=False):
        return json.loads(self.read(name, source), parse_float=Decimal)

    def digest(self, name, source=False):
        return hashlib.sha256(self.read(name, source)).hexdigest()

    def bind(self, name, expected, code, **detail):
        if not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected):
            self.check(code, 'insufficient', file=name, reason='missing valid SHA-256 binding', **detail)
        else:
            self.equal(code, self.digest(name, name.startswith('sources/')), expected, file=name, **detail)

    def source(self, sid, src, kind, cutoff):
        if not isinstance(src, dict):
            raise ValueError('unsafe source record')
        name = src['file']
        self.bind(name, src.get('sha256'), 'source_hash', source_id=sid)
        data = self.data(name, True)
        pub = date.fromisoformat(src['publication_date'])
        self.check('publication_cutoff', 'passed' if pub <= cutoff else 'failed', source_id=sid,
                   publication_date=pub.isoformat(), cutoff=cutoff.isoformat())
        receipt = src.get('receipt')
        if not isinstance(receipt, str) or not re.fullmatch(r'\d{14}', receipt):
            self.check('publication_original', 'insufficient', source_id=sid, reason='missing receipt')
        else:
            self.equal('publication_receipt', receipt[:8], pub.strftime('%Y%m%d'), source_id=sid)
        if kind == 'json':
            return data, None
        if kind != 'table':
            raise ValueError('unsupported source kind')
        if not src.get('original_file'):
            raise FileNotFoundError('preserved original archive binding missing')
        archive = src['original_file']
        self.bind(archive, src.get('original_archive_sha256'), 'ledger_archive_hash', source_id=sid)
        self.bind(archive, data.get('original_archive_sha256'), 'index_archive_hash', source_id=sid)
        member = data['member']
        if not isinstance(member, str) or '\\' in member or PurePosixPath(member).is_absolute() or '..' in PurePosixPath(member).parts:
            raise ValueError('unsafe archive member')
        self.equal('member_binding', member, src.get('member'), source_id=sid)
        with zipfile.ZipFile(io.BytesIO(self.read(archive, True))) as z:
            if len(z.infolist()) > MAX_ITEMS:
                raise ValueError('archive member limit')
            matches = [i for i in z.infolist() if i.filename == member]
            if len(matches) != 1 or not member.lower().endswith('.xml'):
                raise ValueError('unique XML member required')
            info = matches[0]
            if info.file_size > MAX_FILE or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('unsafe XML member size/type')
            with z.open(info) as f:
                raw = f.read(MAX_FILE + 1)
            self.total += len(raw)
            if len(raw) > MAX_FILE or self.total > MAX_TOTAL:
                raise ValueError('XML byte limit exceeded')
        digest = hashlib.sha256(raw).hexdigest()
        for label, expected in [('index_xml_hash', data.get('xml_sha256')), ('ledger_xml_hash', src.get('xml_sha256'))]:
            self.equal(label, digest, expected, source_id=sid)
        match = re.search(r'filing-(\d{14})', PurePosixPath(archive).name)
        if match:
            self.equal('archive_receipt', match[1], receipt, source_id=sid)
        else:
            self.check('archive_receipt', 'insufficient', source_id=sid, reason='original publication receipt unavailable')
        encoding = data.get('encoding')
        if encoding not in ('utf-8', 'euc-kr'):
            raise ValueError('unsupported original encoding')
        parser = _OriginalTables()
        parser.feed(raw.decode(encoding))
        parser.close()
        return parser.tables, data

    def proof(self, item, raw, tables, index, parent):
        unit = item['source_unit']
        evidence = item.get('unit_evidence')
        if unit == 'text':
            return
        if parent is not None:
            obj, _ = parent
            if unit == 'KRW' and isinstance(obj, dict):
                self.equal('unit_proof', obj.get('currency'), 'KRW', id=item['id'])
                return
            if unit == 'shares' and item['locator']['path'][-1] in ('istc_totqy', 'tsstk_co', 'distb_stock_co', 'istc_totqy_totqy', 'istc_totqy_cotc'):
                self.check('unit_proof', 'passed', id=item['id'], field=item['locator']['path'][-1])
                return
            self.check('unit_proof', 'insufficient', id=item['id'], reason='no supported original JSON unit proof')
            return
        if unit == 'percent' and str(raw).strip().endswith('%'):
            self.check('unit_proof', 'passed', id=item['id'], actual=raw)
            return
        if not evidence:
            self.check('unit_proof', 'insufficient', id=item['id'], reason='missing original unit proof')
            return
        if not isinstance(evidence, dict) or not isinstance(evidence.get('quote'), str) or not evidence['quote']:
            raise ValueError('unsafe unit evidence')
        t = tables[item['locator']['table']]
        proof = t['context']
        if 'cell' in evidence:
            cell = evidence['cell']
            if not isinstance(cell, dict) or set(cell) != {'row', 'col'}:
                raise ValueError('unsafe unit locator')
            table_id = evidence.get('table', item['locator']['table'])
            _coordinate(table_id, True)
            proof = tables[table_id]['rows'][_coordinate(cell['row'])][_coordinate(cell['col'])]
            indexed = [v for v in index['tables'] if v['table_index'] == table_id]
            if len(indexed) != 1:
                raise ValueError('ambiguous unit table index')
            self.equal('unit_index_cell', proof, indexed[0]['rows'][cell['row']][cell['col']]['text'], id=item['id'])
        quote = evidence['quote']
        label = LABELS[unit]
        pattern = re.escape(label) if label == '%' else r'(?<![가-힣])' + re.escape(label) + r'(?![가-힣])'
        self.check('unit_proof', 'passed' if quote in proof and re.search(pattern, quote) else 'failed',
                   id=item['id'], actual=proof, expected=quote, source_unit=unit)


def audit_sources(out):
    """Read current mandate/selectors/ledgers and return a JSON-safe audit receipt."""
    a = _Audit(out)
    observations = 0
    selected = {}
    ledgers = {}
    cutoff = None
    target = {}
    errors = (OSError, ValueError, KeyError, IndexError, TypeError, InvalidOperation,
              zipfile.BadZipFile, UnicodeError, RecursionError, AttributeError)
    for name in ('mandate.json', 'selectors.json', 'accounting-evidence.json', 'capital-evidence.json'):
        try:
            data = a.data(name)
            if name == 'mandate.json':
                cutoff = date.fromisoformat(data['cutoff'])
                a.check('mandate_cutoff', 'passed', cutoff=cutoff.isoformat())
            elif name == 'selectors.json':
                items = data['selectors']
                if not isinstance(items, list) or len(items) > MAX_ITEMS:
                    raise ValueError('selector list limit/type')
                for item in items:
                    identity = item['id']
                    if not isinstance(identity, str) or not identity or identity in selected:
                        raise ValueError('duplicate/unsafe selector ID')
                    if item['output'] not in ('accounting', 'capital'):
                        raise ValueError('unknown selector output')
                    selected[identity] = item
            else:
                if not isinstance(data.get('observations'), list) or not isinstance(data.get('sources'), dict) or len(data['observations']) > MAX_ITEMS or len(data['sources']) > MAX_ITEMS:
                    raise ValueError('ledger shape/limit')
                ledgers[name.split('-')[0]] = data
        except errors as exc:
            a.check('input', 'insufficient' if isinstance(exc, FileNotFoundError) else 'failed', file=name, reason=str(exc)[:300])
    try:
        target = a.data('analysis-review-target.json')['artifacts']
        if not isinstance(target, dict):
            raise ValueError('unsafe artifact hash map')
        for name in ('mandate.json', 'selectors.json', 'accounting-evidence.json', 'capital-evidence.json'):
            if name in target or name.endswith('-evidence.json'):
                a.bind(name, target.get(name), 'current_artifact_hash')
    except errors as exc:
        a.check('current_artifact_hash', 'insufficient' if isinstance(exc, FileNotFoundError) else 'failed', reason=str(exc)[:300])
    seen = set()
    sources = {}
    for group, ledger in ledgers.items():
        for gap in ledger.get('gaps', []):
            a.check('recorded_gap', 'insufficient', group=group, gap=gap)
        for obs in ledger['observations']:
            observations += 1
            identity = obs.get('id') if isinstance(obs, dict) else None
            try:
                if not isinstance(obs, dict):
                    raise ValueError('unsafe observation record')
                if not isinstance(identity, str) or identity in seen:
                    raise ValueError('duplicate/unsafe observation ID')
                seen.add(identity)
                item = selected.get(identity)
                if item is None or item['output'] != group:
                    raise ValueError('unknown observation selector')
                sid = obs['source_id']
                if not isinstance(sid, str) or sid not in ledger['sources']:
                    raise ValueError('unknown source')
                if not isinstance(item['source_file'], str) or PurePosixPath(item['source_file']).name != item['source_file']:
                    raise ValueError('unsafe selector source path')
                a.equal('selector_source', sid, item['source_file'], id=identity)
                src = ledger['sources'][sid]
                a.equal('source_file_binding', src['file'], 'sources/' + item['source_file'], id=identity)
                for field in ('locator', 'source_unit', 'target_scale', 'unit', 'period_end', 'perimeter', 'rationale'):
                    if field == 'target_scale':
                        a.equal('selector_' + field, _decimal(obs[field]), _decimal(item[field]), id=identity)
                    else:
                        a.equal('selector_' + field, obs.get(field), item.get(field), id=identity)
                if cutoff is None:
                    a.check('replay', 'insufficient', id=identity, reason='current cutoff unavailable')
                    continue
                end = date.fromisoformat(obs['period_end'])
                a.check('period_cutoff', 'passed' if end <= cutoff else 'failed', id=identity, period_end=end.isoformat(), cutoff=cutoff.isoformat())
                cache_key = (sid, json.dumps(src, sort_keys=True, default=str), item['kind'])
                if cache_key not in sources:
                    sources[cache_key] = a.source(sid, src, item['kind'], cutoff)
                    if src['file'] in target:
                        a.bind(src['file'], target[src['file']], 'target_source_hash')
                original, index = sources[cache_key]
                raw, parent = _locate(original, item['kind'], obs['locator'])
                if index is not None:
                    tables = [t for t in index['tables'] if t['table_index'] == obs['locator']['table']]
                    if len(tables) != 1:
                        raise ValueError('ambiguous selected index table')
                    indexed = tables[0]['rows'][obs['locator']['row']][obs['locator']['col']]['text']
                    a.equal('index_raw', raw, indexed, id=identity)
                else:
                    receipt = parent[1]
                    a.equal('original_receipt', receipt, src.get('receipt'), id=identity)
                    if not isinstance(receipt, str) or not re.fullmatch(r'\d{14}', receipt):
                        a.check('original_publication_cutoff', 'insufficient', id=identity, reason='original receipt unavailable')
                    else:
                        published = date.fromisoformat(receipt[:4] + '-' + receipt[4:6] + '-' + receipt[6:8])
                        a.check('original_publication_cutoff', 'passed' if published <= cutoff else 'failed', id=identity)
                a.equal('recorded_raw', raw, obs.get('raw'), id=identity)
                a.equal('selector_raw', raw, item.get('expected_raw'), id=identity)
                unit = obs['source_unit']
                if unit not in SOURCE_UNITS or obs['unit'] not in TARGET_UNITS:
                    raise ValueError('unsupported unit')
                scale = _decimal(obs['target_scale'])
                if scale <= 0:
                    raise ValueError('target scale must be positive')
                a.equal('target_scale', scale, Decimal(TARGET_UNITS[obs['unit']]), id=identity)
                money = unit.startswith('KRW')
                if money != obs['unit'].startswith('KRW') or (unit == 'shares' and obs['unit'] != 'shares') or (unit == 'text' and obs['unit'] != 'text') or (unit in ('percent', 'fraction') and obs['unit'] not in ('fraction', 'ratio')):
                    raise ValueError('incompatible source/output units')
                a.proof(item, raw, original, index, parent)
                n = None if unit == 'text' else _number(raw)
                if unit == 'text':
                    a.equal('normalized_exact', str(raw), obs.get('amount_exact'), id=identity)
                    a.equal('normalized_value', str(raw), obs.get('value'), id=identity)
                elif n is None:
                    a.check('missing_scalar', 'insufficient', id=identity, actual=None)
                    a.equal('missing_amount', obs.get('amount_exact'), None, id=identity)
                    a.equal('missing_value', obs.get('value'), None, id=identity)
                else:
                    with localcontext() as ctx:
                        ctx.prec = max(100, len(n.as_tuple().digits) + 40)
                        exact = n * Decimal(SOURCE_UNITS[unit]) / scale
                    a.equal('normalized_exact', exact, _decimal(obs['amount_exact']), id=identity)
                    expected_value = Decimal(str(float(exact))) if isinstance(obs.get('value'), (float, Decimal)) else exact
                    a.equal('normalized_value', expected_value, _decimal(obs['value']), id=identity)
            except errors as exc:
                a.check('observation', 'insufficient' if isinstance(exc, FileNotFoundError) else 'failed', id=identity, reason=str(exc)[:300])
    for identity in selected.keys() - seen:
        a.check('missing_observation', 'insufficient', id=identity)
    if not observations:
        a.check('coverage', 'insufficient', reason='no observations replayed')
    # Detect mutation after initial read; never rewrite inputs or an earlier receipt.
    for name, (_, digest) in list(a.cache.items()):
        try:
            p = a.path(name, name.startswith('sources/'))
            with p.open('rb') as f:
                current = f.read(MAX_FILE + 1)
            a.equal('input_stability', hashlib.sha256(current).hexdigest(), digest, file=name)
        except errors as exc:
            a.check('input_stability', 'failed', file=name, reason=str(exc)[:300])
    counts = {status: sum(c['status'] == status for c in a.checks) for status in ('passed', 'failed', 'insufficient')}
    counts.update(observations=observations, selectors=len(selected), sources=len(sources), checks=len(a.checks))
    mismatches = [c for c in a.checks if c['status'] == 'failed']
    result = {'status': 'failed' if counts['failed'] else 'insufficient' if counts['insufficient'] else 'passed',
              'counts': counts, 'input_file_hashes': {k: v[1] for k, v in sorted(a.cache.items())},
              'checks': a.checks, 'mismatches': mismatches[:MAX_MISMATCHES],
              'mismatches_truncated': len(mismatches) > MAX_MISMATCHES,
              'limitations': a.limitations, 'financial_approval': False}
    # Convert Decimal from raw JSON without losing numeric precision.
    return json.loads(json.dumps(result, ensure_ascii=False, default=str))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--output', type=Path, help='Explicit new append-only receipt path; existing files are refused')
    args = parser.parse_args()
    result = audit_sources(args.out)
    if args.output:
        with args.output.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({'status': result['status'], 'counts': result['counts'], 'financial_approval': False}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
