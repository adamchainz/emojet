use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};
use std::collections::HashSet;
use unicode_normalization::UnicodeNormalization;

#[rustfmt::skip]
mod data;
use data::{
    ALIAS_RANGES, ALIAS_SPANS, ASCII_STARTS, EMOJI_SPANS, EN_SPANS, LANG_CODES, LANG_SORTED,
    LANG_SORTED_STARTS, LANG_SPANS, NAME_MAP, POOL, STATUSES, TRIE_EDGES, TRIE_NODES,
    UNICODE_VERSION, VARIANTS, VERSIONS,
};

const ZWJ: char = '\u{200d}';
const VS15: char = '\u{fe0e}';
const VS16: char = '\u{fe0f}';

#[inline]
fn span_str(span: (u32, u32)) -> &'static str {
    &POOL[span.0 as usize..span.1 as usize]
}

#[inline]
fn emoji_str(idx: usize) -> &'static str {
    span_str(EMOJI_SPANS[idx])
}

#[inline]
fn en_name(idx: usize) -> &'static str {
    span_str(EN_SPANS[idx])
}

fn aliases(idx: usize) -> impl Iterator<Item = &'static str> {
    let (start, end) = ALIAS_RANGES[idx];
    ALIAS_SPANS[start as usize..end as usize]
        .iter()
        .map(|&span| span_str(span))
}

/// The name of the emoji in the given language id, or None if untranslated.
#[inline]
fn lang_name(lang: usize, idx: usize) -> Option<&'static str> {
    let span = LANG_SPANS[lang][idx];
    if span == (0, 0) {
        None
    } else {
        Some(span_str(span))
    }
}

/// A language argument: English, English aliases, or another language's id.
#[derive(Clone, Copy, PartialEq)]
enum Language {
    En,
    Alias,
    Other(usize),
}

fn parse_language(language: &str) -> PyResult<Language> {
    match language {
        "en" => Ok(Language::En),
        "alias" => Ok(Language::Alias),
        _ => match LANG_CODES.iter().position(|&code| code == language) {
            Some(lang) => Ok(Language::Other(lang)),
            None => Err(PyValueError::new_err(format!(
                "Unsupported language: {language:?}"
            ))),
        },
    }
}

/// The trie child of a node for a code point, or -1.
#[inline]
fn trie_child(node: u32, ch: char) -> i32 {
    let n = &TRIE_NODES[node as usize];
    let start = n.edges_start as usize;
    let edges = &TRIE_EDGES[start..start + n.n_edges as usize];
    match edges.binary_search_by_key(&(ch as u32), |edge| edge.0) {
        Ok(pos) => edges[pos].1 as i32,
        Err(_) => -1,
    }
}

/// The emoji data index for an exact emoji string, or None.
fn lookup_emoji(s: &str) -> Option<usize> {
    let mut node: u32 = 0;
    let mut any = false;
    for ch in s.chars() {
        let child = trie_child(node, ch);
        if child < 0 {
            return None;
        }
        node = child as u32;
        any = true;
    }
    let idx = TRIE_NODES[node as usize].emoji_idx;
    (any && idx >= 0).then_some(idx as usize)
}

/// The longest emoji match starting exactly at `byte_i`, as
/// (byte length, char length, emoji index).
#[inline]
fn match_at(s: &str, byte_i: usize) -> Option<(usize, usize, usize)> {
    let mut node: u32 = 0;
    let mut best = None;
    let mut chars = 0;
    for (offset, ch) in s[byte_i..].char_indices() {
        let child = trie_child(node, ch);
        if child < 0 {
            break;
        }
        node = child as u32;
        chars += 1;
        if TRIE_NODES[node as usize].emoji_idx >= 0 {
            best = Some((
                offset + ch.len_utf8(),
                chars,
                TRIE_NODES[node as usize].emoji_idx as usize,
            ));
        }
    }
    best
}

/// The byte length of the UTF-8 character starting with `byte`.
#[inline]
fn utf8_len(byte: u8) -> usize {
    match byte {
        0x00..=0x7F => 1,
        0x80..=0xDF => 2,
        0xE0..=0xEF => 3,
        _ => 4,
    }
}

/// Scan a string for emoji, longest match first, calling `on_emoji` with
/// (emoji index, byte range, char range) for each. Returning false stops
/// the scan. ASCII characters other than the keycap bases are skipped
/// without a trie lookup.
#[inline]
fn scan(s: &str, mut on_emoji: impl FnMut(usize, usize, usize, usize, usize) -> bool) {
    let bytes = s.as_bytes();
    let mut byte_i = 0;
    let mut char_i = 0;
    while byte_i < bytes.len() {
        let byte = bytes[byte_i];
        if byte < 128 && !ASCII_STARTS[byte as usize] {
            byte_i += 1;
            char_i += 1;
            continue;
        }
        if let Some((byte_len, char_len, idx)) = match_at(s, byte_i) {
            if !on_emoji(idx, byte_i, byte_i + byte_len, char_i, char_i + char_len) {
                return;
            }
            byte_i += byte_len;
            char_i += char_len;
        } else {
            byte_i += utf8_len(byte);
            char_i += 1;
        }
    }
}

/// Append a text segment between emoji matches, dropping stray variation
/// selectors like the emoji package does.
fn push_text(out: &mut String, segment: &str) {
    if segment.contains(VS15) || segment.contains(VS16) {
        out.extend(segment.chars().filter(|&ch| ch != VS15 && ch != VS16));
    } else {
        out.push_str(segment);
    }
}

/// Append an emoji name wrapped in the given delimiters. Names are stored
/// with colons, so the default colon delimiters need no rebuilding.
fn push_name(out: &mut String, name: &str, delimiters: (&str, &str)) {
    if delimiters == (":", ":") {
        out.push_str(name);
    } else {
        out.push_str(delimiters.0);
        out.push_str(&name[1..name.len() - 1]);
        out.push_str(delimiters.1);
    }
}

#[pyfunction]
#[pyo3(signature = (string, *, language="en", delimiters=(":", ":")))]
fn demojize(string: &str, language: &str, delimiters: (&str, &str)) -> PyResult<String> {
    let language = parse_language(language)?;
    let mut out = String::with_capacity(string.len());
    let mut last = 0;
    scan(string, |idx, byte_start, byte_end, _, _| {
        push_text(&mut out, &string[last..byte_start]);
        match language {
            Language::En => push_name(&mut out, en_name(idx), delimiters),
            Language::Alias => {
                let name = aliases(idx).next().unwrap_or_else(|| en_name(idx));
                push_name(&mut out, name, delimiters);
            }
            Language::Other(lang) => match lang_name(lang, idx) {
                Some(name) => push_name(&mut out, name, delimiters),
                // Untranslated: keep the emoji
                None => out.push_str(&string[byte_start..byte_end]),
            },
        }
        last = byte_end;
        true
    });
    push_text(&mut out, &string[last..]);
    Ok(out)
}

/// Characters allowed in emoji names between the delimiters: alphanumerics
/// and underscore, plus specific punctuation and combining characters, like
/// the emoji package's name pattern.
#[inline]
fn is_name_char(ch: char) -> bool {
    if ch.is_ascii() {
        return ch.is_ascii_alphanumeric()
            || matches!(
                ch,
                '_' | '-' | '&' | '.' | '(' | ')' | '!' | '#' | '*' | '+' | ',' | '/'
            );
    }
    ch.is_alphanumeric()
        || matches!(
            ch,
            '\u{ab}' | '\u{bb}' | '\u{2019}' | '\u{201c}' | '\u{201d}'
        )
        || matches!(
            ch,
            '\u{300}'
                | '\u{301}'
                | '\u{302}'
                | '\u{303}'
                | '\u{306}'
                | '\u{308}'
                | '\u{30a}'
                | '\u{327}'
                | '\u{64b}'
                | '\u{64e}'
                | '\u{64f}'
                | '\u{650}'
                | '\u{653}'
                | '\u{654}'
                | '\u{655}'
                | '\u{3099}'
                | '\u{309a}'
                | '\u{30fb}'
        )
}

/// The emoji data index for a delimited name (stored form ":name:"), NFKC
/// normalizing non-ASCII names. `key_buf` is reused across candidates.
fn name_to_idx(name: &str, language: Language, key_buf: &mut String) -> Option<usize> {
    key_buf.clear();
    key_buf.push(':');
    if name.is_ascii() {
        key_buf.push_str(name);
    } else {
        key_buf.extend(name.nfkc());
    }
    key_buf.push(':');

    match language {
        Language::En | Language::Alias => {
            let &(en_idx, alias_idx) = NAME_MAP.get(key_buf.as_str())?;
            let idx = if language == Language::Alias && alias_idx != u16::MAX {
                alias_idx
            } else {
                en_idx
            };
            (idx != u16::MAX).then_some(idx as usize)
        }
        Language::Other(lang) => {
            let start = LANG_SORTED_STARTS[lang] as usize;
            let end = LANG_SORTED_STARTS[lang + 1] as usize;
            let entries = &LANG_SORTED[start..end];
            entries
                .binary_search_by_key(&key_buf.as_str(), |&(a, b, _)| span_str((a, b)))
                .ok()
                .map(|pos| entries[pos].2 as usize)
        }
    }
}

#[derive(Clone, Copy)]
enum Variant {
    Unset,
    Text,
    Emoji,
}

#[pyfunction]
#[pyo3(signature = (string, *, language="en", delimiters=(":", ":"), variant=None))]
fn emojize(
    string: &str,
    language: &str,
    delimiters: (&str, &str),
    variant: Option<&str>,
) -> PyResult<String> {
    let language = parse_language(language)?;
    let variant = match variant {
        None => Variant::Unset,
        Some("text_type") => Variant::Text,
        Some("emoji_type") => Variant::Emoji,
        Some(other) => {
            return Err(PyValueError::new_err(format!(
                "variant must be None, 'text_type' or 'emoji_type', not {other:?}"
            )));
        }
    };
    let (d0, d1) = delimiters;
    if d0.is_empty() || d1.is_empty() {
        return Err(PyValueError::new_err("delimiters must not be empty"));
    }

    let mut out = String::with_capacity(string.len());
    let mut key_buf = String::new();
    let mut last = 0;
    let mut i = 0;
    while let Some(rel) = string[i..].find(d0) {
        let start = i + rel;
        let inner_start = start + d0.len();
        // Take name characters until the closing delimiter
        let mut j = inner_start;
        let mut end = None;
        while j < string.len() {
            if j > inner_start && string[j..].starts_with(d1) {
                end = Some(j);
                break;
            }
            match string[j..].chars().next() {
                Some(ch) if is_name_char(ch) => j += ch.len_utf8(),
                _ => break,
            }
        }
        let after_first = start + utf8_len(string.as_bytes()[start]);
        let Some(end) = end else {
            i = after_first;
            continue;
        };
        let Some(idx) = name_to_idx(&string[inner_start..end], language, &mut key_buf) else {
            i = after_first;
            continue;
        };

        out.push_str(&string[last..start]);
        let emoji = emoji_str(idx);
        match variant {
            Variant::Unset => out.push_str(emoji),
            _ if !VARIANTS[idx] => out.push_str(emoji),
            _ => {
                let emoji = emoji
                    .strip_suffix(VS15)
                    .or_else(|| emoji.strip_suffix(VS16))
                    .unwrap_or(emoji);
                out.push_str(emoji);
                out.push(match variant {
                    Variant::Text => VS15,
                    _ => VS16,
                });
            }
        }
        last = end + d1.len();
        i = last;
    }
    out.push_str(&string[last..]);
    Ok(out)
}

#[pyfunction]
#[pyo3(signature = (string, replace=None))]
fn replace_emoji(string: &str, replace: Option<&Bound<'_, PyAny>>) -> PyResult<String> {
    enum Replacer<'a, 'py> {
        Str(&'a str),
        Callable(&'a Bound<'py, PyAny>),
    }
    let replacer = match replace {
        None => Replacer::Str(""),
        Some(obj) if obj.is_callable() => Replacer::Callable(obj),
        Some(obj) => Replacer::Str(obj.extract()?),
    };
    let mut out = String::with_capacity(string.len());
    let mut error = None;
    let mut last = 0;
    scan(string, |_, byte_start, byte_end, _, _| {
        push_text(&mut out, &string[last..byte_start]);
        last = byte_end;
        match &replacer {
            Replacer::Str(replacement) => {
                out.push_str(replacement);
                true
            }
            Replacer::Callable(callable) => {
                match callable
                    .call1((&string[byte_start..byte_end],))
                    .and_then(|result| result.extract::<String>())
                {
                    Ok(replacement) => {
                        out.push_str(&replacement);
                        true
                    }
                    Err(exc) => {
                        error = Some(exc);
                        false
                    }
                }
            }
        }
    });
    if let Some(exc) = error {
        return Err(exc);
    }
    push_text(&mut out, &string[last..]);
    Ok(out)
}

#[pyfunction]
fn emoji_list<'py>(py: Python<'py>, string: &str) -> PyResult<Bound<'py, PyList>> {
    let list = PyList::empty(py);
    let mut error = None;
    scan(string, |_, byte_start, byte_end, char_start, char_end| {
        let result = (|| {
            let entry = PyDict::new(py);
            entry.set_item("emoji", &string[byte_start..byte_end])?;
            entry.set_item("match_start", char_start)?;
            entry.set_item("match_end", char_end)?;
            list.append(entry)
        })();
        match result {
            Ok(()) => true,
            Err(exc) => {
                error = Some(exc);
                false
            }
        }
    });
    match error {
        Some(exc) => Err(exc),
        None => Ok(list),
    }
}

#[pyfunction]
fn distinct_emoji_list(string: &str) -> Vec<&'static str> {
    let mut seen = HashSet::new();
    let mut result = Vec::new();
    scan(string, |idx, _, _, _, _| {
        if seen.insert(idx) {
            result.push(emoji_str(idx));
        }
        true
    });
    result
}

#[pyfunction]
#[pyo3(signature = (string, *, unique=false))]
fn emoji_count(string: &str, unique: bool) -> usize {
    if unique {
        let mut seen = HashSet::new();
        scan(string, |idx, _, _, _, _| {
            seen.insert(idx);
            true
        });
        seen.len()
    } else {
        let mut count = 0;
        scan(string, |_, _, _, _, _| {
            count += 1;
            true
        });
        count
    }
}

#[pyfunction]
fn is_emoji(string: &str) -> bool {
    lookup_emoji(string).is_some()
}

#[pyfunction]
fn purely_emoji(string: &str) -> bool {
    let mut byte_i = 0;
    let mut prev_was_emoji = false;
    while byte_i < string.len() {
        if let Some((byte_len, _, _)) = match_at(string, byte_i) {
            byte_i += byte_len;
            prev_was_emoji = true;
            continue;
        }
        let ch = string[byte_i..].chars().next().unwrap();
        match ch {
            VS15 | VS16 => {}
            ZWJ if prev_was_emoji => {}
            _ => return false,
        }
        byte_i += ch.len_utf8();
    }
    true
}

#[pyfunction]
fn version(string: &str) -> PyResult<f64> {
    if let Some(idx) = lookup_emoji(string) {
        return Ok(VERSIONS[idx]);
    }
    if string.starts_with(':') && string.ends_with(':') && string.len() > 2 {
        let mut key_buf = String::new();
        if let Some(idx) = name_to_idx(&string[1..string.len() - 1], Language::Alias, &mut key_buf)
        {
            return Ok(VERSIONS[idx]);
        }
    }
    let mut found = None;
    scan(string, |idx, _, _, _, _| {
        found = Some(idx);
        false
    });
    match found {
        Some(idx) => Ok(VERSIONS[idx]),
        None => Err(PyValueError::new_err("No emoji found in string")),
    }
}

#[pyfunction]
#[pyo3(signature = (name, *, language="en"))]
fn get_emoji_by_name(name: &str, language: &str) -> PyResult<Option<&'static str>> {
    let language = parse_language(language)?;
    if !(name.starts_with(':') && name.ends_with(':') && name.len() > 2) {
        return Ok(None);
    }
    let mut key_buf = String::new();
    Ok(name_to_idx(&name[1..name.len() - 1], language, &mut key_buf).map(emoji_str))
}

/// The status of an emoji: "component", "fully_qualified",
/// "minimally_qualified", or "unqualified".
#[pyfunction]
fn emoji_status(string: &str) -> PyResult<&'static str> {
    match lookup_emoji(string) {
        Some(idx) => Ok(match STATUSES[idx] {
            1 => "component",
            2 => "fully_qualified",
            3 => "minimally_qualified",
            _ => "unqualified",
        }),
        None => Err(PyValueError::new_err("Not an emoji")),
    }
}

#[pymodule(gil_used = false)]
fn _scan(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(demojize, m)?)?;
    m.add_function(wrap_pyfunction!(emojize, m)?)?;
    m.add_function(wrap_pyfunction!(replace_emoji, m)?)?;
    m.add_function(wrap_pyfunction!(emoji_list, m)?)?;
    m.add_function(wrap_pyfunction!(distinct_emoji_list, m)?)?;
    m.add_function(wrap_pyfunction!(emoji_count, m)?)?;
    m.add_function(wrap_pyfunction!(is_emoji, m)?)?;
    m.add_function(wrap_pyfunction!(purely_emoji, m)?)?;
    m.add_function(wrap_pyfunction!(version, m)?)?;
    m.add_function(wrap_pyfunction!(get_emoji_by_name, m)?)?;
    m.add_function(wrap_pyfunction!(emoji_status, m)?)?;
    let mut languages = vec!["en"];
    languages.extend(LANG_CODES);
    m.add("LANGUAGES", PyList::new(py, &languages)?)?;
    m.add("UNICODE_VERSION", PyString::new(py, UNICODE_VERSION))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lookup_emoji() {
        assert!(lookup_emoji("👍").is_some());
        assert!(lookup_emoji("👍👍").is_none());
        assert!(lookup_emoji("x").is_none());
        assert!(lookup_emoji("").is_none());
    }

    #[test]
    fn test_match_at_longest() {
        // Family ZWJ sequence matches as one emoji
        let s = "👨\u{200d}👩\u{200d}👧\u{200d}👦";
        let (byte_len, char_len, _) = match_at(s, 0).unwrap();
        assert_eq!(byte_len, s.len());
        assert_eq!(char_len, 7);
        // Dead-end ZWJ walk backtracks to the last match
        let s = "👨\u{200d}👩";
        let (byte_len, char_len, idx) = match_at(s, 0).unwrap();
        assert_eq!((byte_len, char_len), (4, 1));
        assert_eq!(emoji_str(idx), "👨");
    }

    #[test]
    fn test_scan_ascii_fast_path() {
        let mut count = 0;
        scan(
            "plain text without emoji, keycap starts: # * 5",
            |_, _, _, _, _| {
                count += 1;
                true
            },
        );
        assert_eq!(count, 0);
    }
}
