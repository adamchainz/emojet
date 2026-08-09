# /// script
# requires-python = ">=3.12"
# ///
"""
Generate the static Rust data tables (src/data.rs) for emojet, by
downloading and combining the emoji data from its original sources,
following the emoji package's data pipeline
(https://github.com/carpedm20/emoji/tree/master/utils):

* Emoji, their English names, statuses, and versions, from Unicode's
  emoji-test.txt.
* Variation selector support from Unicode's emoji-variation-sequences.txt.
* Translated names from Unicode CLDR annotations.
* Aliases from GitHub's gemoji database.

Alias names from older sources and their ordering, plus translations for
emoji that CLDR does not cover, accumulated over the years by the emoji
package, come from the checked-in seed files in scripts/seeds/, derived
from emoji 2.15.0 (BSD licensed - see LICENSE-EMOJI). This mirrors the
emoji package's own scripts, which combine the downloads with the data of
the previous release.

Run with:

    uv run scripts/generate_data.py

Downloads are cached in build/downloads/.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Update these to pull in new data. Find the latest versions at:
# https://www.unicode.org/reports/tr51/#emoji_data
# https://github.com/unicode-org/cldr/releases
# https://github.com/github/gemoji/releases
UNICODE_VERSION = "17.0.0"
CLDR_TAG = "release-48-alpha3"
GEMOJI_TAG = "v4.1.0"
# The emoji package release that the generated data matches.
EMOJI_PACKAGE_VERSION = "2.15.0"

# Languages other than English, in the order of the emoji package's
# LANGUAGES list. CLDR uses the same language codes.
LANGUAGES = [
    "es",
    "ja",
    "ko",
    "pt",
    "it",
    "fr",
    "de",
    "fa",
    "id",
    "zh",
    "ru",
    "tr",
    "ar",
]

STATUS = {
    "component": 1,
    "fully_qualified": 2,
    "minimally_qualified": 3,
    "unqualified": 4,
}
FULLY_QUALIFIED = STATUS["fully_qualified"]

SCRIPTS_DIR = Path(__file__).parent
RUST_SRC = SCRIPTS_DIR.parent / "src"
CACHE_DIR = SCRIPTS_DIR.parent / "build" / "downloads"


def main() -> None:
    print("Downloading and combining emoji data...")
    emojis = extract_emojis()
    aliases = combine_aliases(emojis)
    translations = build_translations(emojis)

    entries = []
    for emj, v in sorted(emojis.items(), key=lambda item: item[1]["en"]):
        version = v["version"]
        data = {
            "en": f":{v['en']}:",
            "status": STATUS[v["status"]],
            "E": int(version) if version.is_integer() else version,
        }
        if aliases[emj]:
            data["alias"] = [f":{a}:" for a in aliases[emj]]
        if "variant" in v:
            data["variant"] = True
        for lang in LANGUAGES:
            if emj in translations[lang]:
                data[lang] = translations[lang][emj]
        entries.append((emj, data))

    write_data_rs(entries, LANGUAGES)
    print(
        f"Generated data for {len(entries)} emoji from Unicode {UNICODE_VERSION},"
        f" CLDR {CLDR_TAG}, and gemoji {GEMOJI_TAG}."
    )


def download(filename: str, url: str) -> str:
    """Download a file, or reuse a previous download from the cache."""
    cache_path = CACHE_DIR / filename
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    print(f"  Downloading {url}")
    try:
        with urllib.request.urlopen(url) as response:
            content: str = response.read().decode("utf-8")
    except OSError as exc:
        raise SystemExit(f"Could not download {filename}: {exc}")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(content, encoding="utf-8")
    return content


def extract_emojis() -> dict[str, dict[str, Any]]:
    """Parse Unicode's emoji-test.txt and emoji-variation-sequences.txt into
    a dict of emoji, in file order, like the emoji package's
    generate_emoji.py."""

    test_lines = download(
        f"emoji-test-{UNICODE_VERSION}.txt",
        f"https://unicode.org/Public/{UNICODE_VERSION}/emoji/emoji-test.txt",
    ).splitlines()
    sequences_lines = download(
        f"emoji-variation-sequences-{UNICODE_VERSION}.txt",
        f"https://www.unicode.org/Public/{UNICODE_VERSION}/ucd/emoji/emoji-variation-sequences.txt",
    ).splitlines()

    output: dict[str, dict[str, Any]] = {}
    for line in test_lines:
        if line == "" or line.startswith("#"):
            continue
        status = line.split(";")[1].strip().split(" ")[0].replace("-", "_")
        codes = line.split(";")[0].strip().split(" ")
        emj = "".join(chr(int(code, 16)) for code in codes)

        separated_line = line.split(" # ")[-1].strip().split(" ")
        name = (
            "_".join(separated_line[2:])
            .removeprefix("flag:_")
            .replace(":", "")
            .replace(",", "")
            .replace("“", "")
            .replace("”", "")
            .replace("⊛", "")
            .strip()
            .replace(" ", "_")
            .replace("_-_", "-")
        )
        version = float(separated_line[1].removeprefix("E").strip())

        if emj in output:
            raise ValueError(f"Duplicate emoji: {name} {emj!r}")
        output[emj] = {"en": name, "status": status, "version": version}

    for line in sequences_lines:
        if line == "" or line.startswith("#"):
            continue
        sequence = "".join(
            chr(int(code, 16)) for code in line.split(";")[0].strip().split(" ")
        )
        # Mark the sequence itself and it without a trailing variation
        # selector (U+FE0E text / U+FE0F emoji).
        for candidate in {sequence, sequence.rstrip("\ufe0e\ufe0f")}:
            if candidate in output:
                output[candidate]["variant"] = True

    return output


GITHUB_REMOVED_CHARS = re.compile("\u200d|\ufe0f|\ufe0e", re.IGNORECASE)


def load_gemoji_aliases() -> dict[str, str]:
    """Load a dict of alias name to emoji from GitHub's gemoji database, the
    source behind the GitHub API's emoji list."""
    data = json.loads(
        download(
            f"gemoji-{GEMOJI_TAG}.json",
            f"https://raw.githubusercontent.com/github/gemoji/{GEMOJI_TAG}/db/emoji.json",
        )
    )
    output: dict[str, str] = {}
    for entry in data:
        emj = entry.get("emoji")
        if not emj:
            continue  # Custom GitHub emoji that are not part of Unicode
        # Strip ZWJ and variation selectors, like the GitHub API does
        emj = GITHUB_REMOVED_CHARS.sub("", emj)
        for alias in entry["aliases"]:
            output[alias] = emj
    assert len(output) > 100
    return output


def combine_aliases(emojis: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Build the alias list for each emoji: the names from the seed file, in
    order, plus any new names from gemoji, like the emoji package's
    generate_emoji.py combines its previous release's aliases with new ones.

    Names are handled without their colons here.
    """
    with open(SCRIPTS_DIR / "seeds" / "aliases.json", encoding="utf-8") as f:
        seed: dict[str, list[str]] = {
            emj: [a[1:-1] for a in alias_list]
            for emj, alias_list in json.load(f).items()
        }

    gemoji = load_gemoji_aliases()

    # Names already in use, which new aliases may not shadow
    existing_names = {a for alias_list in seed.values() for a in alias_list}
    existing_names.update(v["en"] for v in emojis.values())

    output: dict[str, list[str]] = {}
    for emj, v in emojis.items():
        emj_no_variant = re.sub("[\ufe0e\ufe0f]$", "", emj)

        aliases = set(seed.get(emj, []))
        aliases.update(seed.get(emj_no_variant, []))

        # Strip ZWJ and variation selectors, because the GitHub data has
        # them stripped too
        emj_clean = GITHUB_REMOVED_CHARS.sub("", emj)
        github_aliases = {
            alias
            for alias, gh_emj in gemoji.items()
            if gh_emj in (emj, emj_clean)
            or ("variant" in v and gh_emj == emj_no_variant)
        }
        aliases.update(
            alias
            for alias in github_aliases
            if alias in seed.get(emj, []) or alias not in existing_names
        )

        aliases.discard(v["en"])

        # Keep the order of seeded aliases intact, and sort new ones
        seeded = [a for a in seed.get(emj, []) if a in aliases]
        alias_list = seeded + sorted(aliases.difference(seeded))

        # Put :flag_for_COUNTRY: aliases first so that demojize() picks them,
        # for compatibility with old emoji package versions
        if any("flag_for_" in a for a in alias_list):
            alias_list = [a for a in alias_list if "flag_for_" in a] + [
                a for a in alias_list if "flag_for_" not in a
            ]

        output[emj] = alias_list

    return output


def build_translations(emojis: dict[str, dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Build emoji name translations for each language: the names from the
    seed file, updated from the Unicode CLDR annotations, like the emoji
    package's generate_emoji_translations.py."""
    with open(SCRIPTS_DIR / "seeds" / "translations.json", encoding="utf-8") as f:
        seed: dict[str, dict[str, str]] = json.load(f)

    output: dict[str, dict[str, str]] = {}
    for lang in LANGUAGES:
        data = dict(seed[lang])
        for directory in ("annotations", "annotationsDerived"):
            xml = download(
                f"cldr-{CLDR_TAG}-{directory}-{lang}.xml",
                f"https://raw.githubusercontent.com/unicode-org/cldr/{CLDR_TAG}/common/{directory}/{lang}.xml",
            )
            annotations = ET.fromstring(xml).find("annotations")
            assert annotations is not None
            for annotation in annotations:
                if annotation.get("type") == "tts":
                    emj = annotation.get("cp")
                    assert emj is not None
                    assert annotation.text is not None
                    data[emj] = adapt_emoji_name(annotation.text.strip(), lang, emj)

        # Some emoji have two code sequences, one that ends with ️ and
        # one that does not. If the translation data only has one of the two,
        # use the translation for both, like upstream.
        missing: dict[str, str] = {}
        for emj in data:
            if emj.endswith("\ufe0f") and emj[:-1] not in data and emj[:-1] in emojis:
                missing[emj[:-1]] = data[emj]
            with_emoji_type = f"{emj}\ufe0f"
            if (
                not emj.endswith("\ufe0f")
                and with_emoji_type not in data
                and with_emoji_type in emojis
            ):
                missing[with_emoji_type] = data[emj]
        data.update(missing)

        # Emoji containing ️ inside the sequence, e.g. eye in speech
        # bubble: use the translation of the sequence without any ️
        for emj in emojis:
            if emj in data:
                continue
            emj_no_variant = emj.replace("\ufe0f", "")
            if emj_no_variant != emj and emj_no_variant in data:
                data[emj] = data[emj_no_variant]

        # Resolve variants to the base emoji's translation, like upstream
        # does when writing the emoji_{lang}.json files
        resolved: dict[str, str] = {}
        for emj, v in emojis.items():
            if emj in data:
                resolved[emj] = data[emj]
            elif "variant" in v:
                emj_no_variant = emj.rstrip("\ufe0e\ufe0f")
                if emj_no_variant in data:
                    resolved[emj] = data[emj_no_variant]
        output[lang] = resolved

    return output


def adapt_emoji_name(text: str, lang: str, emj: str) -> str:
    """Normalize a CLDR annotation into an emoji name, ported from the emoji
    package's generateutils.adapt_emoji_name()."""
    # Use NFKC-form (single character instead of character + diacritic)
    text = unicodedata.normalize("NFKC", text)

    # Fix German clock times "12:30 Uhr" -> "12.30 Uhr"
    text = re.sub(r"(\d+):(\d+)", r"\1.\2", text)
    text = text.replace("Ziffernblatt ", "")

    text = "_".join(text.split(" "))

    emoji_name = (
        ":"
        + (
            text.lower()
            .removeprefix("flag:_")
            .replace(":", "")
            .replace(",", "")
            .replace('"', "")
            .replace("„", "")
            .replace("‟", "")
            .replace(" ", "")
            .replace("⊛", "")
            .replace("–", "-")
            .replace(",_", ",")
            .strip()
            .replace(" ", "_")
            .replace("_-_", "-")
        )
        + ":"
    )

    if lang == "de":
        emoji_name = emoji_name.replace("“", "").replace("”", "")
        emoji_name = re.sub(r"(hautfarbe)_und_([a-z]+_hautfarbe)", r"\1,\2", emoji_name)

    if lang == "fa":
        emoji_name = emoji_name.replace("‌", "_")
        emoji_name = emoji_name.replace("‏", "_")
        emoji_name = emoji_name.replace("،", "_")
        emoji_name = re.sub("_+", "_", emoji_name)

    if lang == "tr":
        emoji_name = emoji_name.replace("̇", "")

    if lang == "ar":
        # Removal of Arabic comma
        emoji_name = emoji_name.replace("،", "")
        # Removal of supplementary Arabic diacritics "tashkīl"
        emoji_name = re.sub("[ًٌٍّْـﱢ]", "", emoji_name)
        # Renaming duplicates
        duplicates = {
            "\U0001f9db\U0001f3ff": ":مصاص_دماء_رجل_بشرة_بلون_غامق:",
            "\U0001f9db\U0001f3fb": ":مصاص_دماء_رجل_بشرة_بلون_فاتح:",
            "\U0001f9db\U0001f3fe": ":مصاص_دماء_رجل_بشرة_بلون_معتدل_مائل_للغامق:",
            "\U0001f9db\U0001f3fc": ":مصاص_دماء_رجل_بشرة_بلون_فاتح_ومعتدل:",
            "\U0001f9db\U0001f3fd": ":مصاص_دماء_رجل_بشرة_بلون_معتدل:",
            "\U0001f9db‍♂️": ":مصاص_دماء_رجل:",
            "\U0001f9a2": ":إوَزة:",
        }
        if emj in duplicates:
            emoji_name = duplicates[emj]

    if lang == "zh":
        emoji_name = (
            ":"
            + (
                text.replace(":", "")
                .replace(",", "")
                .replace("-", "")
                .replace("„", "")
                .replace("‟", "")
                .replace(" ", "")
                .replace("⊛", "")
                .replace(",_", ",")
                .strip()
                .replace(" ", "_")
            )
            + ":"
        )

        if "日文" in emoji_name:
            # Japanese buttons
            emoji_name = (
                emoji_name.replace("日文的", "")
                .replace("按钮", "")
                .replace("“", "")
                .replace("”", "")
            )
        if "箭头" in emoji_name:
            # Arrows
            emoji_name = emoji_name.replace("_", "").replace("!", "")
        if "按钮" in emoji_name:
            # English buttons
            emoji_name = emoji_name.replace("_", "")
        if "型血" in emoji_name:
            emoji_name = emoji_name.replace("_", "")
        if "中等-" in emoji_name:
            emoji_name = emoji_name.replace("中等-", "中等")
        if emoji_name.startswith(":旗_"):
            # Countries
            emoji_name = emoji_name.replace(":旗_", ":")

        hardcoded = {
            "\U0001f1ed\U0001f1f0": ":香港:",
            "\U0001f1ee\U0001f1e9": ":印度尼西亞:",
            "\U0001f1f0\U0001f1ff": ":哈薩克:",
            "\U0001f1f2\U0001f1f4": ":澳門:",
            "\U0001f1e8\U0001f1ec": ":刚果_布:",
            "\U0001f1e8\U0001f1e9": ":刚果_金:",
            "\U0001f193": ":FREE按钮:",
            "\U0001f238": ":申:",
            "\U0001f250": ":得:",
            "\U0001f22f": ":指:",
            "\U0001f232": ":禁:",
            "㊗️": ":祝:",
            "㊗": ":祝:",
            "\U0001f239": ":割:",
            "\U0001f21a": ":无:",
            "\U0001f237️": ":月:",
            "\U0001f237": ":月:",
            "\U0001f235": ":满:",
            "\U0001f236": ":有:",
            "\U0001f234": ":合:",
            "㊙️": ":秘:",
            "㊙": ":秘:",
            "\U0001f233": ":空:",
            "\U0001f251": ":可:",
            "\U0001f23a": ":营:",
            "\U0001f202️": ":服务:",
            "\U0001f202": ":服务:",
        }
        if emj in hardcoded:
            emoji_name = hardcoded[emj]

    if lang == "ru":
        emoji_name = (
            ":"
            + (
                text.replace(":", "")
                .replace(",", "")
                .replace("-", " ")
                .replace("—", "")
                .replace(",_", ",")
                .strip()
                .replace(" ", "_")
            )
            + ":"
        )

    emoji_name = (
        emoji_name.replace("____", "_")
        .replace("___", "_")
        .replace("__", "_")
        .replace("--", "-")
    )

    return emoji_name


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


def build_trie(
    entries: list[tuple[str, dict[str, Any]]],
) -> tuple[list[list[int]], list[tuple[int, int]]]:
    """Build a static trie over the code points of all emoji.

    Returns (nodes, edges) where each node is [edges_start, n_edges, emoji_idx]
    and each edge is (code_point, child_node_index).
    """
    root: dict[str, Any] = {"idx": -1, "children": {}}
    for i, (emj, _) in enumerate(entries):
        node = root
        for char in emj:
            node = node["children"].setdefault(char, {"idx": -1, "children": {}})
        node["idx"] = i

    nodes: list[list[int]] = []
    edges: list[tuple[int, int]] = []
    # Breadth-first so that the root is node 0.
    queue = [root]
    numbered = {id(root): 0}
    nodes.append([0, 0, root["idx"]])
    while queue:
        node = queue.pop(0)
        node_idx = numbered[id(node)]
        children = sorted(node["children"].items(), key=lambda kv: ord(kv[0]))
        nodes[node_idx][0] = len(edges)
        nodes[node_idx][1] = len(children)
        for char, child in children:
            child_idx = len(nodes)
            numbered[id(child)] = child_idx
            nodes.append([0, 0, child["idx"]])
            edges.append((ord(char), child_idx))
            queue.append(child)
    return nodes, edges


def rust_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def spans_array(name: str, spans: list[tuple[int, int]]) -> str:
    body = ",".join(f"({a},{b})" for a, b in spans)
    return f"pub static {name}: [(u32, u32); {len(spans)}] = [{body}];"


def write_data_rs(
    entries: list[tuple[str, dict[str, Any]]], languages: list[str]
) -> None:
    n = len(entries)
    pool = Pool()

    emoji_spans = [pool.add(emj) for emj, _ in entries]
    en_spans = [pool.add(data["en"]) for _, data in entries]
    statuses = [data["status"] for _, data in entries]
    versions = [float(data["E"]) for _, data in entries]
    variants = [int(bool(data.get("variant", False))) for _, data in entries]

    alias_spans: list[tuple[int, int]] = []
    alias_ranges: list[tuple[int, int]] = []
    for _, data in entries:
        aliases = data.get("alias", [])
        alias_ranges.append((len(alias_spans), len(alias_spans) + len(aliases)))
        alias_spans += [pool.add(alias) for alias in aliases]

    # Per-language name spans by index, (0, 0) where untranslated
    lang_spans: list[list[tuple[int, int]]] = []
    for lang in languages:
        lang_spans.append(
            [pool.add(data[lang]) if lang in data else (0, 0) for _, data in entries]
        )

    # Sorted (name span, index) arrays per language, for name lookups. The
    # first emoji in order whose name matches wins, among emoji with status
    # <= fully_qualified, like the emoji package's get_emoji_by_name().
    lang_sorted: list[tuple[int, int, int]] = []
    lang_sorted_starts = [0]
    for lang in languages:
        first_idx: dict[str, int] = {}
        for i, (_, data) in enumerate(entries):
            name = data.get(lang)
            if name is not None and data["status"] <= FULLY_QUALIFIED:
                first_idx.setdefault(name, i)
        # Sorted by UTF-8 bytes, matching Rust &str ordering
        lang_sorted += (
            (*pool.add(name), idx)
            for name, idx in sorted(first_idx.items(), key=lambda kv: kv[0].encode())
        )
        lang_sorted_starts.append(len(lang_sorted))

    nodes, edges = build_trie(entries)

    # English name or alias -> (en index, alias index), u16::MAX = none.
    # Mirrors get_emoji_by_name(): first emoji in order whose name matches,
    # among emoji with status <= fully_qualified.
    en_first: dict[str, int] = {}
    alias_first: dict[str, int] = {}
    for i, (_, data) in enumerate(entries):
        if data["status"] <= FULLY_QUALIFIED:
            en_first.setdefault(data["en"], i)
            for alias in data.get("alias", []):
                alias_first.setdefault(alias, i)
    name_map_entries = []
    for name in sorted(en_first.keys() | alias_first.keys()):
        en_idx = en_first.get(name, 0xFFFF)
        alias_idx = alias_first.get(name, 0xFFFF)
        name_map_entries.append(f"    {rust_str(name)} => ({en_idx}, {alias_idx}),")

    # ASCII characters that can start an emoji (keycap bases)
    ascii_starts = [0] * 128
    for emj, _ in entries:
        if ord(emj[0]) < 128:
            ascii_starts[ord(emj[0])] = 1

    out = [
        "// Generated by scripts/generate_data.py - do not edit by hand.",
        "",
        f"pub const N: usize = {n};",
        f'pub static UNICODE_VERSION: &str = "{UNICODE_VERSION}";',
        "",
        "pub static LANG_CODES: [&str; {}] = [{}];".format(
            len(languages), ", ".join(f'"{lang}"' for lang in languages)
        ),
        "",
        "pub static POOL: &str = " + rust_str(pool.data) + ";",
        "",
        spans_array("EMOJI_SPANS", emoji_spans),
        spans_array("EN_SPANS", en_spans),
        f"pub static STATUSES: [u8; N] = [{','.join(str(s) for s in statuses)}];",
        f"pub static VERSIONS: [f64; N] = [{','.join(repr(v) for v in versions)}];",
        f"pub static VARIANTS: [bool; N] = [{','.join('true' if v else 'false' for v in variants)}];",
        spans_array("ALIAS_SPANS", alias_spans),
        f"pub static ALIAS_RANGES: [(u32, u32); N] = [{','.join(f'({a},{b})' for a, b in alias_ranges)}];",
        "",
        f"pub static LANG_SPANS: [[(u32, u32); N]; {len(languages)}] = [",
    ]
    for spans in lang_spans:
        out.append("    [" + ",".join(f"({a},{b})" for a, b in spans) + "],")
    out += [
        "];",
        "",
        "// (name span start, name span end, emoji index), sorted by name, per language",
        "pub static LANG_SORTED: [(u32, u32, u16); {}] = [{}];".format(
            len(lang_sorted), ",".join(f"({a},{b},{i})" for a, b, i in lang_sorted)
        ),
        "pub static LANG_SORTED_STARTS: [u32; {}] = [{}];".format(
            len(lang_sorted_starts), ",".join(str(v) for v in lang_sorted_starts)
        ),
        "",
        "pub struct TrieNode { pub edges_start: u32, pub n_edges: u16, pub emoji_idx: i32 }",
        "pub static TRIE_NODES: [TrieNode; {}] = [{}];".format(
            len(nodes),
            ",".join(
                f"TrieNode{{edges_start:{s},n_edges:{c},emoji_idx:{i}}}"
                for s, c, i in nodes
            ),
        ),
        "pub static TRIE_EDGES: [(u32, u32); {}] = [{}];".format(
            len(edges), ",".join(f"({cp},{ch})" for cp, ch in edges)
        ),
        "",
        f"pub static ASCII_STARTS: [bool; 128] = [{','.join('true' if v else 'false' for v in ascii_starts)}];",
        "",
        "// English name or alias -> (en index, alias index), u16::MAX = none",
        "pub static NAME_MAP: phf::Map<&'static str, (u16, u16)> = phf::phf_map! {",
        *name_map_entries,
        "};",
        "",
    ]
    (RUST_SRC / "data.rs").write_text("\n".join(out))
    print(
        f"data.rs: pool {len(pool.data.encode())} bytes, "
        f"{len(nodes)} trie nodes, {len(name_map_entries)} name keys"
    )


if __name__ == "__main__":
    main()
