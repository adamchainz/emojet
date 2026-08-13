use pyo3::prelude::*;
use pyo3::types::PyTuple;

#[rustfmt::skip]
mod data;
use data::{EXACT, EXCEPTION, ICANN_SHIFT, LIST_CHECKSUM, POOL, TRIE_EDGES, TRIE_NODES, WILDCARD};

/// A domain prepared for lookup: the input with one trailing dot removed,
/// its lowercased form, and the label count the two forms share.
struct Prepared<'a> {
    orig: &'a str,
    lower: String,
    nlabels: usize,
}

/// Prepare a domain like the publicsuffixlist package: drop one trailing
/// dot, lowercase, and reject empty labels. Lowercasing never adds or
/// removes dots, so both forms split into the same labels.
fn prepare(domain: &str) -> Option<Prepared<'_>> {
    let orig = domain.strip_suffix('.').unwrap_or(domain);
    let lower = orig.to_lowercase();
    if lower.is_empty() || lower.split('.').any(str::is_empty) {
        return None;
    }
    Some(Prepared {
        orig,
        nlabels: lower.split('.').count(),
        lower,
    })
}

/// A pooled label as a string slice.
#[inline]
fn span_str(start: u32, end: u32) -> &'static str {
    &POOL[start as usize..end as usize]
}

/// The trie child of a node for a label, or -1.
#[inline]
fn trie_child(node: u32, label: &str) -> i32 {
    let n = &TRIE_NODES[node as usize];
    let start = n.edges_start as usize;
    let edges = &TRIE_EDGES[start..start + n.n_edges as usize];
    match edges.binary_search_by(|&(a, b, _)| span_str(a, b).cmp(label)) {
        Ok(pos) => edges[pos].2 as i32,
        Err(_) => -1,
    }
}

/// The number of public labels at the end of the domain, or 0 if none:
/// the publicsuffixlist package's rule evaluation, walking the trie from
/// the rightmost label with the deepest matching rule winning. A wildcard
/// rule makes its parent domain itself a public suffix, the
/// interpretation required by the list's linter, and unknown TLDs count
/// as one public label unless `accept_unknown` is false. With
/// `icann_only`, only rules from the list's ICANN section match.
fn count_public(prepared: &Prepared, accept_unknown: bool, icann_only: bool) -> usize {
    let mut node: u32 = 0;
    let mut publen = 0;
    let mut found = false;
    for (i, label) in prepared.lower.rsplit('.').enumerate() {
        let child = trie_child(node, label);
        if child < 0 {
            break;
        }
        node = child as u32;
        let depth = i + 1;
        let mut flags = TRIE_NODES[node as usize].flags;
        if icann_only {
            flags >>= ICANN_SHIFT;
        }
        // The check order must be exception > wildcard > exact
        if flags & EXCEPTION != 0 {
            publen = depth - 1;
            found = true;
        } else if flags & WILDCARD != 0 {
            // An entire match is the implicit root of the wildcard
            publen = if depth < prepared.nlabels {
                depth + 1
            } else {
                depth
            };
            found = true;
        } else if flags & EXACT != 0 {
            publen = depth;
            found = true;
        }
    }
    if !found {
        return if accept_unknown { 1 } else { 0 };
    }
    publen
}

/// The tail of a domain starting at the given label index, which must be
/// less than the domain's label count.
fn tail_from(s: &str, start_label: usize) -> &str {
    let mut rest = s;
    for _ in 0..start_label {
        rest = &rest[rest.find('.').unwrap() + 1..];
    }
    rest
}

impl Prepared<'_> {
    fn cased(&self, keep_case: bool) -> &str {
        if keep_case {
            self.orig
        } else {
            &self.lower
        }
    }
}

#[pyfunction]
#[pyo3(signature = (domain, *, accept_unknown=true, icann_only=false, keep_case=false))]
fn publicsuffix(
    domain: &str,
    accept_unknown: bool,
    icann_only: bool,
    keep_case: bool,
) -> Option<String> {
    let prepared = prepare(domain)?;
    let publen = count_public(&prepared, accept_unknown, icann_only);
    if publen == 0 {
        return None;
    }
    let s = prepared.cased(keep_case);
    Some(tail_from(s, prepared.nlabels - publen).to_string())
}

#[pyfunction]
#[pyo3(signature = (domain, *, accept_unknown=true, icann_only=false, keep_case=false))]
fn privatesuffix(
    domain: &str,
    accept_unknown: bool,
    icann_only: bool,
    keep_case: bool,
) -> Option<String> {
    let prepared = prepare(domain)?;
    let publen = count_public(&prepared, accept_unknown, icann_only);
    if publen == 0 || prepared.nlabels < publen + 1 {
        return None;
    }
    let s = prepared.cased(keep_case);
    Some(tail_from(s, prepared.nlabels - (publen + 1)).to_string())
}

#[pyfunction]
#[pyo3(signature = (domain, *, accept_unknown=true, icann_only=false))]
fn is_public(domain: &str, accept_unknown: bool, icann_only: bool) -> bool {
    match prepare(domain) {
        Some(prepared) => count_public(&prepared, accept_unknown, icann_only) == prepared.nlabels,
        None => false,
    }
}

#[pyfunction]
#[pyo3(signature = (domain, *, accept_unknown=true, icann_only=false))]
fn is_private(domain: &str, accept_unknown: bool, icann_only: bool) -> bool {
    match prepare(domain) {
        Some(prepared) => {
            let publen = count_public(&prepared, accept_unknown, icann_only);
            publen > 0 && publen < prepared.nlabels
        }
        None => false,
    }
}

#[pyfunction]
#[pyo3(signature = (domain, *, accept_unknown=true, icann_only=false, keep_case=false))]
fn privateparts<'py>(
    py: Python<'py>,
    domain: &str,
    accept_unknown: bool,
    icann_only: bool,
    keep_case: bool,
) -> PyResult<Option<Bound<'py, PyTuple>>> {
    let Some(prepared) = prepare(domain) else {
        return Ok(None);
    };
    let publen = count_public(&prepared, accept_unknown, icann_only);
    if publen == 0 || prepared.nlabels < publen + 1 {
        return Ok(None);
    }
    let s = prepared.cased(keep_case);
    let start = prepared.nlabels - (publen + 1);
    let mut parts: Vec<&str> = s.split('.').take(start).collect();
    parts.push(tail_from(s, start));
    Ok(Some(PyTuple::new(py, parts)?))
}

#[pyfunction]
#[pyo3(signature = (domain, depth, *, accept_unknown=true, icann_only=false, keep_case=false))]
fn subdomain(
    domain: &str,
    depth: usize,
    accept_unknown: bool,
    icann_only: bool,
    keep_case: bool,
) -> Option<String> {
    let prepared = prepare(domain)?;
    let publen = count_public(&prepared, accept_unknown, icann_only);
    // Compare without adding to depth, which could overflow
    if publen == 0 || prepared.nlabels < publen + 1 || prepared.nlabels - publen - 1 < depth {
        return None;
    }
    let s = prepared.cased(keep_case);
    Some(tail_from(s, prepared.nlabels - publen - 1 - depth).to_string())
}

#[pymodule(gil_used = false)]
fn _lookup(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(publicsuffix, m)?)?;
    m.add_function(wrap_pyfunction!(privatesuffix, m)?)?;
    m.add_function(wrap_pyfunction!(is_public, m)?)?;
    m.add_function(wrap_pyfunction!(is_private, m)?)?;
    m.add_function(wrap_pyfunction!(privateparts, m)?)?;
    m.add_function(wrap_pyfunction!(subdomain, m)?)?;
    m.add("LIST_CHECKSUM", LIST_CHECKSUM)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn publen(domain: &str, accept_unknown: bool) -> usize {
        match prepare(domain) {
            Some(prepared) => count_public(&prepared, accept_unknown, false),
            None => 0,
        }
    }

    fn publen_icann(domain: &str) -> usize {
        let prepared = prepare(domain).unwrap();
        count_public(&prepared, true, true)
    }

    #[test]
    fn test_prepare() {
        assert!(prepare("").is_none());
        assert!(prepare(".").is_none());
        assert!(prepare("..").is_none());
        assert!(prepare(".com").is_none());
        assert!(prepare("example..com").is_none());
        let prepared = prepare("WwW.Example.COM.").unwrap();
        assert_eq!(prepared.orig, "WwW.Example.COM");
        assert_eq!(prepared.lower, "www.example.com");
        assert_eq!(prepared.nlabels, 3);
    }

    #[test]
    fn test_trie_child() {
        let com = trie_child(0, "com");
        assert!(com >= 0);
        // com is an exact rule in the ICANN section
        let flags = TRIE_NODES[com as usize].flags;
        assert_eq!(flags, EXACT | (EXACT << ICANN_SHIFT));
        assert_eq!(trie_child(0, "not-a-real-tld"), -1);
        assert_eq!(trie_child(0, ""), -1);
    }

    #[test]
    fn test_count_public_exact() {
        assert_eq!(publen("com", true), 1);
        assert_eq!(publen("example.com", true), 1);
        assert_eq!(publen("www.example.co.uk", true), 2);
        assert_eq!(publen("example.com", false), 1);
    }

    #[test]
    fn test_count_public_unknown() {
        assert_eq!(publen("unknowntld", true), 1);
        assert_eq!(publen("unknowntld", false), 0);
        assert_eq!(publen("example.unknowntld", true), 1);
        assert_eq!(publen("example.unknowntld", false), 0);
    }

    #[test]
    fn test_count_public_wildcard() {
        // *.ck, with the exception rule !www.ck
        assert_eq!(publen("test.ck", true), 2);
        assert_eq!(publen("a.b.test.ck", true), 2);
        assert_eq!(publen("www.ck", true), 1);
        // The wildcard makes ck itself public, even without accept_unknown
        assert_eq!(publen("ck", false), 1);
    }

    #[test]
    fn test_count_public_wildcard_root() {
        // kobe.jp is not listed itself, but *.kobe.jp makes it public
        assert_eq!(publen("kobe.jp", true), 2);
        assert_eq!(publen("c.kobe.jp", true), 3);
        assert_eq!(publen("b.c.kobe.jp", true), 3);
        // ...except for the exception rule !city.kobe.jp
        assert_eq!(publen("city.kobe.jp", true), 2);
    }

    #[test]
    fn test_count_public_icann_only() {
        // github.io is in the list's private section
        assert_eq!(publen("adamchainz.github.io", true), 2);
        assert_eq!(publen_icann("adamchainz.github.io"), 1);
        assert_eq!(publen_icann("www.example.co.uk"), 2);
        assert_eq!(publen_icann("kobe.jp"), 2);
    }

    #[test]
    fn test_list_checksum() {
        assert_eq!(LIST_CHECKSUM.len(), 64);
        assert!(LIST_CHECKSUM.bytes().all(|b| b.is_ascii_hexdigit()));
    }

    #[test]
    fn test_subdomain_huge_depth() {
        // Must not overflow the depth comparison
        let result = subdomain("www.example.com", usize::MAX, true, false, false);
        assert_eq!(result, None);
        let result = subdomain("www.example.com", usize::MAX - 1, true, false, false);
        assert_eq!(result, None);
    }

    #[test]
    fn test_tail_from() {
        assert_eq!(tail_from("a.b.c", 0), "a.b.c");
        assert_eq!(tail_from("a.b.c", 1), "b.c");
        assert_eq!(tail_from("a.b.c", 2), "c");
    }
}
