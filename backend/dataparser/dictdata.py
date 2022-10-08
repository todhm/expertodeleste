from typing import Union, Dict, List, Generator

import demjson


def find_keys_from_dict(node: Union[Dict, List], kv: str) -> Generator:
    if isinstance(node, list):
        for i in node:
            for x in find_keys_from_dict(i, kv):
                yield x
    elif isinstance(node, dict):
        if kv in node:
            yield node[kv]
        for j in node.values():
            for x in find_keys_from_dict(j, kv):
                yield x


def undefined_to_none(dj):
    if isinstance(dj, dict):
        return {k: undefined_to_none(v) for k, v in dj.items()}
    if isinstance(dj, list):
        return [undefined_to_none(k) for k in dj]
    elif dj == demjson.undefined:
        return None
    else:
        return dj
