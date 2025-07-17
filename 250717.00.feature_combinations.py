# -*- coding: utf-8 -*-
# https://chatgpt.com/share/6878a80c-0d74-8001-a560-ee21169bde1c
from itertools import product, combinations
from typing import Any, Dict, List
from pprint import pprint


# ------------------------------------------------------------------
# 1) spec -> examples map
# ------------------------------------------------------------------
def make_examples(spec: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Generate example sentences for all feature combinations.

    Parameters
    ----------
    spec : {
        "features": {
            "voice": ["active", "passive"],
            "progressive": [0, 1],
            "perfect": [0, 1]
        }
    }

    Returns
    -------
    {"examples": {combo_id: sentence, ...}}

    combo_id format preserves the feature order in spec["features"]:
        voice=<v>|progressive=<p>|perfect=<pf>
    """
    feats = spec["features"]
    order = list(feats.keys())  # preserve insertion order

    # Canonical example sentences (상어=행위자, 니모=대상)
    CANON = {
        ("active", 0, 0): ("Sharks eat clownfish.", "★★★★★"),
        ("passive", 0, 0): ("Clownfish are eaten by sharks.", "★★★★★"),

        ("active", 1, 0): ("The shark is eating Nemo!", "★★★★★"),
        ("passive", 1, 0): ("Nemo is being eaten by the shark!", "★★★★☆"),

        ("active", 0, 1): ("The shark has eaten Nemo.", "★★★★☆"),
        ("passive", 0, 1): ("Nemo has been eaten by the shark.", "★★★☆☆"),

        ("active", 1, 1): ("The shark has been eating Nemo.", "★★★☆☆"),
        ("passive", 1, 1): ("Nemo has been being eaten by the shark.", "★☆☆☆☆"),
    }

    # convenience: pull lists
    voice_vals = feats.get("voice", [])
    prog_vals = feats.get("progressive", [])
    perf_vals = feats.get("perfect", [])

    def _cid(vals: Dict[str, Any]) -> str:
        return "|".join(f"{k}={vals[k]}" for k in order)

    out = {}
    for combo in product(*(feats[k] for k in order)):
        vals = dict(zip(order, combo))
        key = _cid(vals)

        # Attempt canonical lookup only if the 3 known features exist.
        sent = None
        if set(order) == {"voice", "progressive", "perfect"} and len(order) == 3:
            sent = CANON.get((vals["voice"], vals["progressive"], vals["perfect"]))

        # Fallback: quick descriptive placeholder
        if sent is None:
            desc_parts = []
            for k in order:
                desc_parts.append(f"{k}={vals[k]}")
            if vals.get("voice") == "active":
                sent = f"The shark ({', '.join(desc_parts)}) something Nemo-ish."
            elif vals.get("voice") == "passive":
                sent = f"Nemo ({', '.join(desc_parts)}) by a shark."
            else:
                sent = "Example: " + ", ".join(desc_parts)

        out[key] = sent

    return {"examples": out}


# ------------------------------------------------------------------
# 2) examples map -> pairwise diff list (dedup i<j)
# ------------------------------------------------------------------
def examples_to_pairs(ex_json: Dict[str, Dict[str, str]],
                      include_examples: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build unordered pairwise comparisons (중복 제거) from an examples map.

    Parameters
    ----------
    ex_json : {"examples": {case_id: sentence}}
    include_examples : attach sentences to each pair item if True.

    Returns
    -------
    {
      "pairs": [
         {"a": case_id_A,
          "b": case_id_B,
          "diff": [feature_names_that_differ, ...],
          "a_ex": "...",   # if include_examples
          "b_ex": "..."    # if include_examples
         },
         ...
      ]
    }
    """
    ex_map = ex_json["examples"]
    ids = list(ex_map.keys())

    # parse an id like voice=active|progressive=0|perfect=1
    def parse_id(cid: str) -> Dict[str, Any]:
        d = {}
        for part in cid.split("|"):
            k, v = part.split("=", 1)
            # try int conversion for numeric-like strings
            try:
                d[k] = int(v)
            except ValueError:
                d[k] = v
        return d

    parsed = {cid: parse_id(cid) for cid in ids}

    pairs: List[Dict[str, Any]] = []
    for a, b in combinations(ids, 2):  # i<j automatically
        da = parsed[a]
        db = parsed[b]
        diff = [k for k in da if da[k] != db[k]]
        item = {"a": a, "b": b, "diff": diff}
        if include_examples:
            item["a_ex"] = ex_map[a]
            item["b_ex"] = ex_map[b]
        pairs.append(item)

    return {"pairs": pairs}


# ------------------------------------------------------------------
# Demo
# ------------------------------------------------------------------
if __name__ == "__main__":
    spec = {
        "features": {
            "voice": ["active", "passive"],
            "progressive": [0, 1],
            "perfect": [0, 1],
        }
    }

    examples = make_examples(spec)
    pairs = examples_to_pairs(examples)

    print(f"cases: {len(examples['examples'])}")  # 8
    print(f"pairs: {len(pairs['pairs'])}")        # 28
    # print first few
    i = 0
    for p in pairs["pairs"]:
        print(f"[{i+1}]")
        pprint(p)
        i += 1
