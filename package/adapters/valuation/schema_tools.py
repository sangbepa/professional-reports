"""Small strict validator for the checked-in JSON Schema (no runtime dependency)."""
import datetime
import json
import math
import re
from pathlib import Path


def validate_schema(data):
    root = json.loads(Path(__file__).with_name('input.schema.json').read_text())

    def walk(value, schema, path):
        if '$ref' in schema:
            schema = root['$defs'][schema['$ref'].split('/')[-1]]
        typ = schema.get('type')
        types = {'object': dict, 'array': list, 'string': str, 'number': (int, float),
                 'integer': int, 'boolean': bool, 'null': type(None)}
        if typ and (not isinstance(value, types[typ]) or
                    (typ in ('number', 'integer') and isinstance(value, bool))):
            raise ValueError(f'{path}: expected {typ}')
        if 'enum' in schema and value not in schema['enum']:
            raise ValueError(f'{path}: must be one of {schema["enum"]}')
        if isinstance(value, (float, int)) and not isinstance(value, bool):
            if not math.isfinite(value):
                raise ValueError(f'{path}: non-finite number')
            for key, invalid in [('minimum', lambda n: value < n), ('maximum', lambda n: value > n),
                                 ('exclusiveMinimum', lambda n: value <= n)]:
                if key in schema and invalid(schema[key]):
                    raise ValueError(f'{path}: violates {key} {schema[key]}')
        if isinstance(value, str):
            if len(value.strip()) < schema.get('minLength', 0):
                raise ValueError(f'{path}: empty text')
            if 'pattern' in schema and not re.fullmatch(schema['pattern'], value):
                raise ValueError(f'{path}: invalid format')
            if schema.get('format') == 'date':
                try:
                    datetime.date.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError(f'{path}: invalid date') from exc
        if isinstance(value, dict):
            missing = set(schema.get('required', [])) - value.keys()
            props = schema.get('properties', {})
            extra = value.keys() - props.keys()
            if missing or (extra and schema.get('additionalProperties') is False):
                raise ValueError(f'{path}: missing {sorted(missing)}, unexpected {sorted(extra)}')
            for key, item in value.items():
                if key in props:
                    walk(item, props[key], f'{path}.{key}')
        if isinstance(value, list):
            if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', 100000):
                raise ValueError(f'{path}: invalid length')
            for index, item in enumerate(value):
                walk(item, schema['items'], f'{path}.{index}')
    walk(data, root, '$')


def leaves(data, path=''):
    if isinstance(data, dict) and 'value' in data:
        yield path, data
    elif isinstance(data, dict):
        for key, value in data.items():
            yield from leaves(value, f'{path}.{key}'.strip('.'))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from leaves(value, f'{path}.{index}')
