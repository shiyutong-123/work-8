from __future__ import annotations

from typing import Any

from lxml import etree


def _force_fix(
    root: Any,
    namespaces: dict[str, str] | None = None,
) -> tuple[Any, dict[str, str] | None]:
    if not isinstance(root, etree._Element):
        return root, namespaces

    fixed_namespaces = dict(namespaces or {})
    alias_index = 1

    for element in root.iter():
        for prefix, uri in (element.nsmap or {}).items():
            if not uri:
                continue

            alias = prefix or "xmlns"
            if alias not in fixed_namespaces:
                fixed_namespaces[alias] = uri
                continue

            if fixed_namespaces[alias] == uri:
                continue

            while True:
                candidate = f"{alias}{alias_index}"
                alias_index += 1
                if candidate not in fixed_namespaces:
                    fixed_namespaces[candidate] = uri
                    break

    return root, fixed_namespaces
