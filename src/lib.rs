use pyo3::exceptions::{PyAttributeError, PyKeyError, PyLookupError, PyTypeError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyIterator, PyList, PyString};
use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use unicode_normalization::char::is_combining_mark;
use unicode_normalization::UnicodeNormalization;

#[rustfmt::skip]
mod data;
use data::*;

const KIND_COUNTRY: usize = 0;
const KIND_HISTORIC: usize = 1;
const KIND_SUBDIVISION: usize = 2;
const KIND_CURRENCY: usize = 3;
const KIND_LANGUAGE: usize = 4;
const KIND_LANGUAGE_FAMILY: usize = 5;
const KIND_SCRIPT: usize = 6;

/// One ISO dataset: its records as per-field string spans into POOL, plus
/// sorted lowercased indexes for the fields that get() accepts, in
/// lookup()'s search order, and the non-indexed fields that only lookup()
/// scans.
struct Dataset {
    class_name: &'static str,
    fields: &'static [&'static str],
    data: &'static [(u32, u32)],
    indexed: &'static [usize],
    index: &'static [(u32, u32, u32)],
    index_starts: &'static [u32],
    non_indexed: &'static [usize],
}

static DATASETS: [Dataset; 7] = [
    Dataset {
        class_name: "Country",
        fields: &COUNTRY_FIELDS,
        data: &COUNTRY_DATA,
        indexed: &COUNTRY_INDEXED,
        index: &COUNTRY_INDEX,
        index_starts: &COUNTRY_INDEX_STARTS,
        non_indexed: &COUNTRY_NON_INDEXED,
    },
    Dataset {
        class_name: "Country",
        fields: &HISTORIC_FIELDS,
        data: &HISTORIC_DATA,
        indexed: &HISTORIC_INDEXED,
        index: &HISTORIC_INDEX,
        index_starts: &HISTORIC_INDEX_STARTS,
        non_indexed: &HISTORIC_NON_INDEXED,
    },
    Dataset {
        class_name: "Subdivision",
        fields: &SUBDIVISION_FIELDS,
        data: &SUBDIVISION_DATA,
        indexed: &SUBDIVISION_INDEXED,
        index: &SUBDIVISION_INDEX,
        index_starts: &SUBDIVISION_INDEX_STARTS,
        non_indexed: &SUBDIVISION_NON_INDEXED,
    },
    Dataset {
        class_name: "Currency",
        fields: &CURRENCY_FIELDS,
        data: &CURRENCY_DATA,
        indexed: &CURRENCY_INDEXED,
        index: &CURRENCY_INDEX,
        index_starts: &CURRENCY_INDEX_STARTS,
        non_indexed: &CURRENCY_NON_INDEXED,
    },
    Dataset {
        class_name: "Language",
        fields: &LANGUAGE_FIELDS,
        data: &LANGUAGE_DATA,
        indexed: &LANGUAGE_INDEXED,
        index: &LANGUAGE_INDEX,
        index_starts: &LANGUAGE_INDEX_STARTS,
        non_indexed: &LANGUAGE_NON_INDEXED,
    },
    Dataset {
        class_name: "LanguageFamily",
        fields: &LANGUAGE_FAMILY_FIELDS,
        data: &LANGUAGE_FAMILY_DATA,
        indexed: &LANGUAGE_FAMILY_INDEXED,
        index: &LANGUAGE_FAMILY_INDEX,
        index_starts: &LANGUAGE_FAMILY_INDEX_STARTS,
        non_indexed: &LANGUAGE_FAMILY_NON_INDEXED,
    },
    Dataset {
        class_name: "Script",
        fields: &SCRIPT_FIELDS,
        data: &SCRIPT_DATA,
        indexed: &SCRIPT_INDEXED,
        index: &SCRIPT_INDEX,
        index_starts: &SCRIPT_INDEX_STARTS,
        non_indexed: &SCRIPT_NON_INDEXED,
    },
];

#[inline]
fn span_str(span: (u32, u32)) -> Option<&'static str> {
    if span == A {
        None
    } else {
        Some(&POOL[span.0 as usize..span.1 as usize])
    }
}

impl Dataset {
    fn n(&self) -> usize {
        self.data.len() / self.fields.len()
    }

    /// The value of a record's field, or None where the source data has no
    /// value.
    fn value(&self, idx: usize, field: usize) -> Option<&'static str> {
        span_str(self.data[idx * self.fields.len() + field])
    }

    fn field_pos(&self, name: &str) -> Option<usize> {
        self.fields.iter().position(|&field| field == name)
    }

    fn indexed_pos(&self, field_pos: usize) -> Option<usize> {
        self.indexed.iter().position(|&field| field == field_pos)
    }

    /// The record with the given lowercased value in an indexed field, or
    /// None. Where several records share a value, the last wins, like
    /// pycountry's overwriting index writes.
    fn get_indexed(&self, indexed_pos: usize, value_lower: &str) -> Option<usize> {
        let start = self.index_starts[indexed_pos] as usize;
        let end = self.index_starts[indexed_pos + 1] as usize;
        let entries = &self.index[start..end];
        entries
            .binary_search_by_key(&value_lower, |&(a, b, _)| &POOL[a as usize..b as usize])
            .ok()
            .map(|pos| entries[pos].2 as usize)
    }
}

/// The record with the given lowercased value in the named indexed field.
fn get_field(kind: usize, field: &str, value_lower: &str) -> Option<usize> {
    let ds = &DATASETS[kind];
    let indexed_pos = ds.indexed_pos(ds.field_pos(field)?)?;
    ds.get_indexed(indexed_pos, value_lower)
}

/// The contiguous range of subdivision records for a lowercased country
/// code, or None for unknown codes and countries without subdivisions.
fn country_range(value_lower: &str) -> Option<(usize, usize)> {
    SUBDIVISION_COUNTRY_RANGES
        .binary_search_by_key(&value_lower, |&(a, b, _, _)| &POOL[a as usize..b as usize])
        .ok()
        .map(|pos| {
            let (_, _, start, end) = SUBDIVISION_COUNTRY_RANGES[pos];
            (start as usize, end as usize)
        })
}

/// The country record for a subdivision, via its country code.
fn subdivision_country(idx: usize) -> Option<usize> {
    let ds = &DATASETS[KIND_SUBDIVISION];
    let country_code = ds.value(idx, ds.field_pos("country_code")?)?;
    get_field(KIND_COUNTRY, "alpha_2", &country_code.to_lowercase())
}

fn make_record(py: Python<'_>, kind: usize, idx: usize) -> PyResult<Py<PyAny>> {
    Ok(match kind {
        KIND_COUNTRY | KIND_HISTORIC => Py::new(py, Country { kind, idx })?.into_any(),
        KIND_SUBDIVISION => Py::new(py, Subdivision { idx })?.into_any(),
        KIND_CURRENCY => Py::new(py, Currency { idx })?.into_any(),
        KIND_LANGUAGE => Py::new(py, Language { idx })?.into_any(),
        KIND_LANGUAGE_FAMILY => Py::new(py, LanguageFamily { idx })?.into_any(),
        _ => Py::new(py, Script { idx })?.into_any(),
    })
}

fn subdivision_list(py: Python<'_>, start: usize, end: usize) -> PyResult<Py<PyList>> {
    let list = PyList::empty(py);
    for idx in start..end {
        list.append(Py::new(py, Subdivision { idx })?)?;
    }
    Ok(list.unbind())
}

/// A record attribute: the field's value, or AttributeError.
fn record_getattr(py: Python<'_>, kind: usize, idx: usize, name: &str) -> PyResult<Py<PyAny>> {
    let ds = &DATASETS[kind];
    if let Some(pos) = ds.field_pos(name) {
        if let Some(value) = ds.value(idx, pos) {
            return Ok(PyString::new(py, value).unbind().into_any());
        }
    }
    Err(PyAttributeError::new_err(name.to_owned()))
}

/// A pycountry-style repr with the fields in sorted order, like
/// Country(alpha_2='DE', ...). Subdivisions without a parent show
/// parent_code=None, matching their None attribute.
fn record_repr(py: Python<'_>, kind: usize, idx: usize) -> PyResult<String> {
    let ds = &DATASETS[kind];
    let mut items: Vec<(&str, String)> = Vec::with_capacity(ds.fields.len());
    for (pos, &field) in ds.fields.iter().enumerate() {
        match ds.value(idx, pos) {
            Some(value) => {
                items.push((field, PyString::new(py, value).repr()?.to_str()?.to_owned()));
            }
            None if kind == KIND_SUBDIVISION && field == "parent_code" => {
                items.push((field, "None".to_owned()));
            }
            None => {}
        }
    }
    items.sort_by_key(|&(field, _)| field);
    let fields: Vec<String> = items
        .into_iter()
        .map(|(field, value)| format!("{field}={value}"))
        .collect();
    Ok(format!("{}({})", ds.class_name, fields.join(", ")))
}

/// Iterating a record yields (field, value) pairs, so that dict() casts it,
/// like pycountry. A subdivision's parent field yields the parent record.
fn record_iter(py: Python<'_>, kind: usize, idx: usize) -> PyResult<Py<PyIterator>> {
    let ds = &DATASETS[kind];
    let list = PyList::empty(py);
    for (pos, &field) in ds.fields.iter().enumerate() {
        let value = ds.value(idx, pos);
        if kind == KIND_SUBDIVISION && field == "parent" {
            if value.is_some() {
                list.append((field, Subdivision { idx }.parent(py)?))?;
            }
            continue;
        }
        match value {
            Some(value) => list.append((field, value))?,
            None if kind == KIND_SUBDIVISION && field == "parent_code" => {
                list.append((field, py.None()))?;
            }
            None => {}
        }
    }
    Ok(list.try_iter()?.unbind())
}

#[pyclass(frozen, eq, hash)]
#[derive(PartialEq, Eq, Hash)]
struct Country {
    kind: usize,
    idx: usize,
}

#[pymethods]
impl Country {
    fn __getattr__(&self, py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
        record_getattr(py, self.kind, self.idx, name)
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        record_repr(py, self.kind, self.idx)
    }

    fn __iter__(&self, py: Python<'_>) -> PyResult<Py<PyIterator>> {
        record_iter(py, self.kind, self.idx)
    }
}

macro_rules! simple_record {
    ($cls:ident, $kind:expr) => {
        #[pyclass(frozen, eq, hash)]
        #[derive(PartialEq, Eq, Hash)]
        struct $cls {
            idx: usize,
        }

        #[pymethods]
        impl $cls {
            fn __getattr__(&self, py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
                record_getattr(py, $kind, self.idx, name)
            }

            fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
                record_repr(py, $kind, self.idx)
            }

            fn __iter__(&self, py: Python<'_>) -> PyResult<Py<PyIterator>> {
                record_iter(py, $kind, self.idx)
            }
        }
    };
}

simple_record!(Currency, KIND_CURRENCY);
simple_record!(Language, KIND_LANGUAGE);
simple_record!(LanguageFamily, KIND_LANGUAGE_FAMILY);
simple_record!(Script, KIND_SCRIPT);

#[pyclass(frozen, eq, hash)]
#[derive(PartialEq, Eq, Hash)]
struct Subdivision {
    idx: usize,
}

#[pymethods]
impl Subdivision {
    /// The subdivision's country.
    #[getter]
    fn country(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match subdivision_country(self.idx) {
            Some(idx) => make_record(py, KIND_COUNTRY, idx),
            None => Ok(py.None()),
        }
    }

    /// The parent subdivision, or None for top-level subdivisions.
    #[getter]
    fn parent(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let ds = &DATASETS[KIND_SUBDIVISION];
        let pos = ds.field_pos("parent_code").unwrap();
        match ds.value(self.idx, pos) {
            Some(code) => match get_field(KIND_SUBDIVISION, "code", &code.to_lowercase()) {
                Some(idx) => make_record(py, KIND_SUBDIVISION, idx),
                None => Ok(py.None()),
            },
            None => Ok(py.None()),
        }
    }

    fn __getattr__(&self, py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
        if name == "parent_code" {
            let ds = &DATASETS[KIND_SUBDIVISION];
            if ds
                .value(self.idx, ds.field_pos("parent_code").unwrap())
                .is_none()
            {
                return Ok(py.None());
            }
        }
        record_getattr(py, KIND_SUBDIVISION, self.idx, name)
    }

    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        record_repr(py, KIND_SUBDIVISION, self.idx)
    }

    fn __iter__(&self, py: Python<'_>) -> PyResult<Py<PyIterator>> {
        record_iter(py, KIND_SUBDIVISION, self.idx)
    }
}

#[pyclass(frozen)]
struct RecordIter {
    kind: usize,
    next: AtomicUsize,
}

#[pymethods]
impl RecordIter {
    fn __iter__(slf: PyRef<'_, Self>) -> PyRef<'_, Self> {
        slf
    }

    fn __next__(&self, py: Python<'_>) -> PyResult<Option<Py<PyAny>>> {
        let idx = self.next.fetch_add(1, Ordering::Relaxed);
        if idx < DATASETS[self.kind].n() {
            Ok(Some(make_record(py, self.kind, idx)?))
        } else {
            Ok(None)
        }
    }
}

/// The single field=value criterion from get()'s keyword arguments.
fn single_criterion<'py>(
    kwargs: Option<&Bound<'py, PyDict>>,
) -> PyResult<(String, Bound<'py, PyAny>)> {
    if let Some(kwargs) = kwargs {
        if kwargs.len() == 1 {
            let (field, value) = kwargs.iter().next().unwrap();
            return Ok((field.extract()?, value));
        }
    }
    Err(PyTypeError::new_err("Only one criteria may be given"))
}

fn get_impl(
    py: Python<'_>,
    kind: usize,
    default: Option<Bound<'_, PyAny>>,
    kwargs: Option<&Bound<'_, PyDict>>,
) -> PyResult<Py<PyAny>> {
    let (field, value) = single_criterion(kwargs)?;
    let Ok(value) = value.cast::<PyString>() else {
        return Err(PyLookupError::new_err(()));
    };
    let value_lower = value.to_str()?.to_lowercase();
    let default = || default.map_or_else(|| py.None(), Bound::unbind);

    if kind == KIND_SUBDIVISION && field == "country_code" {
        if let Some((start, end)) = country_range(&value_lower) {
            return Ok(subdivision_list(py, start, end)?.into_any());
        }
        // A known country with no subdivisions gives an empty list
        if get_field(KIND_COUNTRY, "alpha_2", &value_lower).is_some() {
            return Ok(PyList::empty(py).unbind().into_any());
        }
        return Ok(default());
    }

    let ds = &DATASETS[kind];
    let Some(indexed_pos) = ds.field_pos(&field).and_then(|pos| ds.indexed_pos(pos)) else {
        return Err(PyKeyError::new_err(field));
    };
    match ds.get_indexed(indexed_pos, &value_lower) {
        Some(idx) => make_record(py, kind, idx),
        None => Ok(default()),
    }
}

fn lookup_impl(py: Python<'_>, kind: usize, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    let Ok(value_str) = value.cast::<PyString>() else {
        return Err(PyLookupError::new_err(()));
    };
    let value_lower = value_str.to_str()?.to_lowercase();
    let ds = &DATASETS[kind];

    // Indexed fields first
    for indexed_pos in 0..ds.indexed.len() {
        if let Some(idx) = ds.get_indexed(indexed_pos, &value_lower) {
            return make_record(py, kind, idx);
        }
    }

    // A country code looks up the country's subdivisions
    if kind == KIND_SUBDIVISION {
        if let Some((start, end)) = country_range(&value_lower) {
            return Ok(subdivision_list(py, start, end)?.into_any());
        }
    }

    // Non-indexed values now
    for idx in 0..ds.n() {
        for &field in ds.non_indexed {
            if let Some(v) = ds.value(idx, field) {
                if v.to_lowercase() == value_lower {
                    return make_record(py, kind, idx);
                }
            }
        }
    }

    Err(PyLookupError::new_err(format!(
        "Could not find a record for {}",
        value.repr()?
    )))
}

/// lookup() reduced to the matched record index, for search_fuzzy().
fn lookup_idx(kind: usize, value_lower: &str) -> Option<usize> {
    let ds = &DATASETS[kind];
    for indexed_pos in 0..ds.indexed.len() {
        if let Some(idx) = ds.get_indexed(indexed_pos, value_lower) {
            return Some(idx);
        }
    }
    for idx in 0..ds.n() {
        for &field in ds.non_indexed {
            if let Some(v) = ds.value(idx, field) {
                if v.to_lowercase() == value_lower {
                    return Some(idx);
                }
            }
        }
    }
    None
}

/// Strip accents from a string, NFKD-normalizing and dropping combining
/// marks, like pycountry's remove_accents().
fn remove_accents(input: &str) -> String {
    if input.is_ascii() {
        input.to_owned()
    } else {
        input.nfkd().filter(|&c| !is_combining_mark(c)).collect()
    }
}

/// A candidate value normalized for fuzzy matching: lowercased and
/// accent-stripped.
fn fuzzy_key(value: &str) -> String {
    remove_accents(&value.to_lowercase())
}

/// The character (not byte) index of needle in haystack, like Python's
/// str.find(), or None.
fn char_find(haystack: &str, needle: &str) -> Option<i64> {
    haystack
        .find(needle)
        .map(|pos| haystack[..pos].chars().count() as i64)
}

/// Fuzzy-search countries, porting pycountry's scoring: exact lookups, then
/// exact subdivision matches, then partial name and initials matches, then
/// partial subdivision name matches.
fn search_fuzzy_countries(py: Python<'_>, query: &str) -> PyResult<Py<PyList>> {
    let q = fuzzy_key(query.trim());
    let mut points: HashMap<usize, i64> = HashMap::new();

    // Prio 1: exact matches on country names
    if let Some(idx) = lookup_idx(KIND_COUNTRY, &q) {
        *points.entry(idx).or_default() += 50;
    }

    // Prio 2: exact matches on subdivision values, including
    // semicolon-separated alternative names
    let subs = &DATASETS[KIND_SUBDIVISION];
    for sub_idx in 0..subs.n() {
        for pos in 0..subs.fields.len() {
            if let Some(v) = subs.value(sub_idx, pos) {
                if fuzzy_key(v).split(';').any(|w| w == q) {
                    if let Some(idx) = subdivision_country(sub_idx) {
                        *points.entry(idx).or_default() += 49;
                    }
                }
            }
        }
    }

    // Prio 3: initials and partial matches on country names
    let ds = &DATASETS[KIND_COUNTRY];
    for idx in 0..ds.n() {
        for field in ["name", "official_name", "comment"] {
            let Some(pos) = ds.field_pos(field) else {
                continue;
            };
            let Some(v) = ds.value(idx, pos) else {
                continue;
            };
            let initials: String = v.chars().filter(|c| c.is_uppercase()).collect();
            if q == fuzzy_key(&initials) {
                *points.entry(idx).or_default() += 40;
                break;
            }
            if let Some(found) = char_find(&fuzzy_key(v), &q) {
                // Prefer matches early in the name
                *points.entry(idx).or_default() += (30 - 2 * found).max(5);
                break;
            }
        }
    }

    // Prio 4: partial matches on subdivision names
    let name_pos = subs.field_pos("name").unwrap();
    for sub_idx in 0..subs.n() {
        if let Some(v) = subs.value(sub_idx, name_pos) {
            if let Some(found) = char_find(&fuzzy_key(v), &q) {
                if let Some(idx) = subdivision_country(sub_idx) {
                    *points.entry(idx).or_default() += (5 - found).max(1);
                }
            }
        }
    }

    if points.is_empty() {
        return Err(PyLookupError::new_err(q));
    }

    // Sort by points, then country code for stable results
    let alpha_2_pos = ds.field_pos("alpha_2").unwrap();
    let mut ranked: Vec<(i64, &str, usize)> = points
        .into_iter()
        .map(|(idx, pts)| (-pts, ds.value(idx, alpha_2_pos).unwrap(), idx))
        .collect();
    ranked.sort();
    let list = PyList::empty(py);
    for &(_, _, idx) in &ranked {
        list.append(Py::new(
            py,
            Country {
                kind: KIND_COUNTRY,
                idx,
            },
        )?)?;
    }
    Ok(list.unbind())
}

/// Fuzzy-search subdivisions, porting pycountry's scoring: exact matches on
/// subdivision values, then partial matches on subdivision names.
fn search_fuzzy_subdivisions(py: Python<'_>, query: &str) -> PyResult<Py<PyList>> {
    let q = fuzzy_key(query.trim());
    let mut points: HashMap<usize, i64> = HashMap::new();

    let ds = &DATASETS[KIND_SUBDIVISION];
    for idx in 0..ds.n() {
        for pos in 0..ds.fields.len() {
            if let Some(v) = ds.value(idx, pos) {
                if fuzzy_key(v).split(';').any(|w| w == q) {
                    *points.entry(idx).or_default() += 50;
                }
            }
        }
    }

    let name_pos = ds.field_pos("name").unwrap();
    for idx in 0..ds.n() {
        if let Some(v) = ds.value(idx, name_pos) {
            if let Some(found) = char_find(&fuzzy_key(v), &q) {
                *points.entry(idx).or_default() += (5 - found).max(1);
            }
        }
    }

    if points.is_empty() {
        return Err(PyLookupError::new_err(q));
    }

    let code_pos = ds.field_pos("code").unwrap();
    let mut ranked: Vec<(i64, &str, usize)> = points
        .into_iter()
        .map(|(idx, pts)| (-pts, ds.value(idx, code_pos).unwrap(), idx))
        .collect();
    ranked.sort();
    let list = PyList::empty(py);
    for &(_, _, idx) in &ranked {
        list.append(Py::new(py, Subdivision { idx })?)?;
    }
    Ok(list.unbind())
}

#[pyclass(frozen)]
struct Countries;

#[pymethods]
impl Countries {
    fn __len__(&self) -> usize {
        DATASETS[KIND_COUNTRY].n()
    }

    fn __iter__(&self) -> RecordIter {
        RecordIter {
            kind: KIND_COUNTRY,
            next: AtomicUsize::new(0),
        }
    }

    #[pyo3(signature = (*, default=None, **kwargs))]
    fn get(
        &self,
        py: Python<'_>,
        default: Option<Bound<'_, PyAny>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Py<PyAny>> {
        get_impl(py, KIND_COUNTRY, default, kwargs)
    }

    fn lookup(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        lookup_impl(py, KIND_COUNTRY, value)
    }

    fn search_fuzzy(&self, py: Python<'_>, query: &str) -> PyResult<Py<PyList>> {
        search_fuzzy_countries(py, query)
    }
}

#[pyclass(frozen)]
struct HistoricCountries;

#[pymethods]
impl HistoricCountries {
    fn __len__(&self) -> usize {
        DATASETS[KIND_HISTORIC].n()
    }

    fn __iter__(&self) -> RecordIter {
        RecordIter {
            kind: KIND_HISTORIC,
            next: AtomicUsize::new(0),
        }
    }

    #[pyo3(signature = (*, default=None, **kwargs))]
    fn get(
        &self,
        py: Python<'_>,
        default: Option<Bound<'_, PyAny>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Py<PyAny>> {
        get_impl(py, KIND_HISTORIC, default, kwargs)
    }

    fn lookup(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        lookup_impl(py, KIND_HISTORIC, value)
    }
}

#[pyclass(frozen)]
struct Subdivisions;

#[pymethods]
impl Subdivisions {
    fn __len__(&self) -> usize {
        DATASETS[KIND_SUBDIVISION].n()
    }

    fn __iter__(&self) -> RecordIter {
        RecordIter {
            kind: KIND_SUBDIVISION,
            next: AtomicUsize::new(0),
        }
    }

    #[pyo3(signature = (*, default=None, **kwargs))]
    fn get(
        &self,
        py: Python<'_>,
        default: Option<Bound<'_, PyAny>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Py<PyAny>> {
        get_impl(py, KIND_SUBDIVISION, default, kwargs)
    }

    fn lookup(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        lookup_impl(py, KIND_SUBDIVISION, value)
    }

    fn search_fuzzy(&self, py: Python<'_>, query: &str) -> PyResult<Py<PyList>> {
        search_fuzzy_subdivisions(py, query)
    }
}

#[pyclass(frozen)]
struct Currencies;

#[pymethods]
impl Currencies {
    fn __len__(&self) -> usize {
        DATASETS[KIND_CURRENCY].n()
    }

    fn __iter__(&self) -> RecordIter {
        RecordIter {
            kind: KIND_CURRENCY,
            next: AtomicUsize::new(0),
        }
    }

    #[pyo3(signature = (*, default=None, **kwargs))]
    fn get(
        &self,
        py: Python<'_>,
        default: Option<Bound<'_, PyAny>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Py<PyAny>> {
        get_impl(py, KIND_CURRENCY, default, kwargs)
    }

    fn lookup(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        lookup_impl(py, KIND_CURRENCY, value)
    }
}

#[pyclass(frozen)]
struct Languages;

#[pymethods]
impl Languages {
    fn __len__(&self) -> usize {
        DATASETS[KIND_LANGUAGE].n()
    }

    fn __iter__(&self) -> RecordIter {
        RecordIter {
            kind: KIND_LANGUAGE,
            next: AtomicUsize::new(0),
        }
    }

    #[pyo3(signature = (*, default=None, **kwargs))]
    fn get(
        &self,
        py: Python<'_>,
        default: Option<Bound<'_, PyAny>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Py<PyAny>> {
        get_impl(py, KIND_LANGUAGE, default, kwargs)
    }

    fn lookup(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        lookup_impl(py, KIND_LANGUAGE, value)
    }
}

#[pyclass(frozen)]
struct LanguageFamilies;

#[pymethods]
impl LanguageFamilies {
    fn __len__(&self) -> usize {
        DATASETS[KIND_LANGUAGE_FAMILY].n()
    }

    fn __iter__(&self) -> RecordIter {
        RecordIter {
            kind: KIND_LANGUAGE_FAMILY,
            next: AtomicUsize::new(0),
        }
    }

    #[pyo3(signature = (*, default=None, **kwargs))]
    fn get(
        &self,
        py: Python<'_>,
        default: Option<Bound<'_, PyAny>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Py<PyAny>> {
        get_impl(py, KIND_LANGUAGE_FAMILY, default, kwargs)
    }

    fn lookup(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        lookup_impl(py, KIND_LANGUAGE_FAMILY, value)
    }
}

#[pyclass(frozen)]
struct Scripts;

#[pymethods]
impl Scripts {
    fn __len__(&self) -> usize {
        DATASETS[KIND_SCRIPT].n()
    }

    fn __iter__(&self) -> RecordIter {
        RecordIter {
            kind: KIND_SCRIPT,
            next: AtomicUsize::new(0),
        }
    }

    #[pyo3(signature = (*, default=None, **kwargs))]
    fn get(
        &self,
        py: Python<'_>,
        default: Option<Bound<'_, PyAny>>,
        kwargs: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Py<PyAny>> {
        get_impl(py, KIND_SCRIPT, default, kwargs)
    }

    fn lookup(&self, py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
        lookup_impl(py, KIND_SCRIPT, value)
    }
}

#[pymodule(gil_used = false)]
fn _db(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Country>()?;
    m.add_class::<Subdivision>()?;
    m.add_class::<Currency>()?;
    m.add_class::<Language>()?;
    m.add_class::<LanguageFamily>()?;
    m.add_class::<Script>()?;
    m.add_class::<Countries>()?;
    m.add_class::<HistoricCountries>()?;
    m.add_class::<Subdivisions>()?;
    m.add_class::<Currencies>()?;
    m.add_class::<Languages>()?;
    m.add_class::<LanguageFamilies>()?;
    m.add_class::<Scripts>()?;
    m.add("countries", Py::new(py, Countries)?)?;
    m.add("historic_countries", Py::new(py, HistoricCountries)?)?;
    m.add("subdivisions", Py::new(py, Subdivisions)?)?;
    m.add("currencies", Py::new(py, Currencies)?)?;
    m.add("languages", Py::new(py, Languages)?)?;
    m.add("language_families", Py::new(py, LanguageFamilies)?)?;
    m.add("scripts", Py::new(py, Scripts)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_field() {
        let idx = get_field(KIND_COUNTRY, "alpha_2", "de").unwrap();
        let ds = &DATASETS[KIND_COUNTRY];
        assert_eq!(
            ds.value(idx, ds.field_pos("name").unwrap()),
            Some("Germany")
        );
        assert_eq!(get_field(KIND_COUNTRY, "alpha_2", "xx"), None);
        assert_eq!(get_field(KIND_COUNTRY, "nope", "de"), None);
    }

    #[test]
    fn test_country_range() {
        let (start, end) = country_range("us").unwrap();
        assert!(end - start > 50);
        let ds = &DATASETS[KIND_SUBDIVISION];
        let code_pos = ds.field_pos("code").unwrap();
        for idx in start..end {
            assert!(ds.value(idx, code_pos).unwrap().starts_with("US-"));
        }
        assert_eq!(country_range("xx"), None);
    }

    #[test]
    fn test_remove_accents() {
        assert_eq!(remove_accents("plain"), "plain");
        assert_eq!(remove_accents("åland"), "aland");
        assert_eq!(remove_accents("côte d'ivoire"), "cote d'ivoire");
    }

    #[test]
    fn test_char_find() {
        assert_eq!(char_find("türkiye", "kiye"), Some(3));
        assert_eq!(char_find("türkiye", "nope"), None);
        assert_eq!(char_find("türkiye", ""), Some(0));
    }
}
