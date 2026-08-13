# /// script
# requires-python = ">=3.12"
# ///
"""
Generate the static Rust data table (src/data.rs) for pslr, by
downloading the Public Suffix List direct from its source at
publicsuffix.org and compiling it into a trie over domain labels.
Also vendors the list's own test data (tests/data/test_psl.txt), direct
from its source repository.

Rules are parsed like the publicsuffixlist package
(https://github.com/ko-zu/psl): lowercased, taking the first
space-separated token of each line, with a punycoded variant of every
internationalized rule generated with Python's "idna" codec, so that
Unicode and punycode domains both match. Rules in the list's ICANN
section also set a second group of trie flags, for icann_only lookups.

Run with:

    uv run scripts/generate_data.py
"""

from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path
from typing import Any

PSL_URL = "https://publicsuffix.org/list/public_suffix_list.dat"
TEST_PSL_URL = (
    "https://raw.githubusercontent.com/publicsuffix/list/main/tests/test_psl.txt"
)

# Node flags, mirrored in src/lib.rs. The low bits cover all rules;
# the same flags shifted left cover only ICANN-section rules.
EXACT = 1
WILDCARD = 2
EXCEPTION = 4
ICANN_SHIFT = 3

SCRIPTS_DIR = Path(__file__).parent
RUST_SRC = SCRIPTS_DIR.parent / "src"
TEST_DATA = SCRIPTS_DIR.parent / "tests" / "data" / "test_psl.txt"


def main() -> None:
    print("Downloading and compiling the Public Suffix List...")
    text = download(PSL_URL)
    rules = parse_rules(text)
    checksum = hashlib.sha256(text.encode()).hexdigest()
    write_data_rs(rules, checksum)

    test_data = download(TEST_PSL_URL)
    TEST_DATA.write_text(test_data, encoding="utf-8")
    print(f"Vendored test data: {len(test_data.encode()):,} bytes.")


def download(url: str) -> str:
    print(f"  Downloading {url}")
    with urllib.request.urlopen(url) as response:
        content: str = response.read().decode("utf-8")
    return content


def parse_rules(text: str) -> dict[str, bool]:
    """Parse list rules, adding punycoded variants of internationalized
    rules, like the publicsuffixlist package's parser.

    Returns a dict of rule to whether it is in the ICANN section.
    """
    rules: dict[str, bool] = {}
    in_icann = False
    for line in text.splitlines():
        if line.rstrip() == "// ===BEGIN ICANN DOMAINS===":
            in_icann = True
            continue
        if line.rstrip() == "// ===END ICANN DOMAINS===":
            in_icann = False
            continue
        rule = line.lower().split(" ")[0].rstrip()
        if rule == "" or rule.startswith("//"):
            continue

        bare = rule.lstrip("!")
        encoded = bare.encode("idna").decode("ascii")
        encoded_rule = "!" + encoded if rule.startswith("!") else encoded
        for variant in (rule, encoded_rule):
            rules[variant] = rules.get(variant, False) or in_icann
    return rules


def build_trie(rules: dict[str, bool]) -> tuple[list[list[int]], list[tuple[str, int]]]:
    """Build a trie over rule labels, matched right to left from the TLD,
    flattened breadth-first so that the root is node 0.

    Returns (nodes, edges): nodes as [edges_start, n_edges, flags] and
    edges as (label, child node), sorted by label bytes per node.
    """
    root: dict[str, Any] = {"flags": 0, "children": {}}
    for rule, is_icann in sorted(rules.items()):
        if rule.startswith("!"):
            flag = EXCEPTION
            stripped = rule[1:]
        elif rule.startswith("*."):
            flag = WILDCARD
            stripped = rule[2:]
        else:
            flag = EXACT
            stripped = rule
        labels = stripped.split(".")
        # The list format only allows a single, leading wildcard label
        assert all("*" not in label and "!" not in label for label in labels), rule
        assert all(labels), rule

        node = root
        for label in reversed(labels):
            node = node["children"].setdefault(label, {"flags": 0, "children": {}})
        node["flags"] |= flag
        if is_icann:
            node["flags"] |= flag << ICANN_SHIFT

    nodes: list[list[int]] = []
    edges: list[tuple[str, int]] = []
    queue = [root]
    nodes.append([0, 0, root["flags"]])
    numbered = {id(root): 0}
    while queue:
        node = queue.pop(0)
        node_idx = numbered[id(node)]
        # Sorted by UTF-8 bytes, matching Rust &str ordering
        children = sorted(node["children"].items(), key=lambda kv: kv[0].encode())
        nodes[node_idx][0] = len(edges)
        nodes[node_idx][1] = len(children)
        for label, child in children:
            child_idx = len(nodes)
            numbered[id(child)] = child_idx
            nodes.append([0, 0, child["flags"]])
            edges.append((label, child_idx))
            queue.append(child)
    return nodes, edges


class Pool:
    """A pool of strings concatenated for Rust span slicing, deduplicated."""

    __slots__ = ("data", "spans")

    def __init__(self) -> None:
        self.data = ""
        self.spans: dict[str, tuple[int, int]] = {}

    def add(self, string: str) -> tuple[int, int]:
        try:
            return self.spans[string]
        except KeyError:
            start = len(self.data.encode())
            span = (start, start + len(string.encode()))
            self.data += string
            self.spans[string] = span
            return span


def rust_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_data_rs(rules: dict[str, bool], checksum: str) -> None:
    nodes, edges = build_trie(rules)

    pool = Pool()
    edge_spans = [(*pool.add(label), child) for label, child in edges]

    out = [
        "// Generated by scripts/generate_data.py - do not edit by hand.",
        "",
        f'pub static LIST_CHECKSUM: &str = "{checksum}";',
        "",
        "// Node flags, mirrored in scripts/generate_data.py. The low bits",
        "// cover all rules; the same flags shifted left by ICANN_SHIFT",
        "// cover only ICANN-section rules.",
        "pub const EXACT: u8 = 1;",
        "pub const WILDCARD: u8 = 2;",
        "pub const EXCEPTION: u8 = 4;",
        "pub const ICANN_SHIFT: u8 = 3;",
        "",
        "pub static POOL: &str = " + rust_str(pool.data) + ";",
        "",
        "// Trie over rule labels, matched right to left from the TLD",
        "pub struct TrieNode { pub edges_start: u32, pub n_edges: u16, pub flags: u8 }",
        "pub static TRIE_NODES: [TrieNode; {}] = [{}];".format(
            len(nodes),
            ",".join(
                f"TrieNode{{edges_start:{s},n_edges:{c},flags:{f}}}"
                for s, c, f in nodes
            ),
        ),
        "// (label span start, label span end, child node), sorted by label",
        "pub static TRIE_EDGES: [(u32, u32, u32); {}] = [{}];".format(
            len(edge_spans), ",".join(f"({a},{b},{c})" for a, b, c in edge_spans)
        ),
        "",
    ]
    (RUST_SRC / "data.rs").write_text("\n".join(out), encoding="utf-8")
    n_icann = sum(rules.values())
    print(
        f"Generated data.rs for {len(rules)} rules ({n_icann} ICANN): "
        f"pool {len(pool.data.encode())} bytes, "
        f"{len(nodes)} trie nodes, {len(edges)} edges."
    )


if __name__ == "__main__":
    main()
