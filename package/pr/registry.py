from pathlib import Path
from .util import ContractError, hash_data, members, read_json, within
from .schema import validate


class Registry:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.entries = {}
        for path in sorted((self.root / "libraries").glob("**/component.json")):
            data = read_json(path)
            validate(self.root, 'component', data)
            for key in ("id", "version", "kind", "status", "entrypoint", "capabilities", "requires"):
                if key not in data:
                    raise ContractError(f"{path}: missing {key}")
            if data["id"] in self.entries:
                raise ContractError("Duplicate component identity")
            if data["kind"] not in {"orchestration", "persona", "skill", "runtime"}:
                raise ContractError("Unknown component kind")
            if not within(path.parent, data["entrypoint"]).is_file():
                raise ContractError(f"Missing entrypoint: {data['id']}")
            self.entries[data["id"]] = (data, path.parent)
        visited=set();active=set()
        def dependency_check(identity):
            if identity in active:raise ContractError('Cyclic component dependency: '+identity)
            if identity in visited:return
            if identity not in self.entries:raise ContractError('Missing required component: '+identity)
            active.add(identity)
            for dependency in self.entries[identity][0]['requires']:dependency_check(dependency)
            active.remove(identity);visited.add(identity)
        for identity in self.entries:dependency_check(identity)

    def reference(self, identity):
        if identity not in self.entries:
            raise ContractError(f"Unknown component: {identity}")
        data, path = self.entries[identity]
        return {"id": identity, "version": data["version"], "sha256": hash_data(members(path))}

    def resolve(self, ref, kind=None):
        if self.reference(ref["id"]) != ref:
            raise ContractError(f"Component version or hash changed: {ref['id']}")
        data, path = self.entries[ref["id"]]
        if kind and data["kind"] != kind:
            raise ContractError(f"Expected {kind}: {ref['id']}")
        return data, path

    def catalog(self):
        return [dict(self.reference(k), kind=v[0]["kind"], status=v[0]["status"],
                     capabilities=v[0]["capabilities"], description=v[0].get("description", ""))
                for k, v in self.entries.items()]

    def evaluation(self, ref):
        p = within(self.root / "protected/evaluations", ref["id"] + ".json")
        data = read_json(p)
        if data["version"] != ref["version"] or hash_data(data) != ref["sha256"]:
            raise ContractError("Evaluation profile version/hash mismatch")
        return data

    def evaluation_ref(self, identity):
        d = read_json(within(self.root / "protected/evaluations", identity + ".json"))
        return {"id": identity, "version": d["version"], "sha256": hash_data(d)}
