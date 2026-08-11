use pyo3::basic::CompareOp;
use pyo3::create_exception;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyString, PyType};
use pyo3::IntoPyObjectExt;

#[rustfmt::skip]
mod data;
use data::{IbanSpec, IBAN_SPECS, ISO3166_COUNTRIES};

create_exception!(
    swifter,
    SwifterError,
    PyValueError,
    "Base exception for all swifter errors."
);
create_exception!(
    swifter,
    InvalidLength,
    SwifterError,
    "The length of the value does not match the specification."
);
create_exception!(
    swifter,
    InvalidStructure,
    SwifterError,
    "The value contains unexpected characters."
);
create_exception!(
    swifter,
    InvalidCountryCode,
    SwifterError,
    "The country code of the value is unknown."
);
create_exception!(
    swifter,
    InvalidChecksumDigits,
    SwifterError,
    "The IBAN's checksum digits are incorrect."
);
create_exception!(
    swifter,
    InvalidBankCode,
    SwifterError,
    "The bank code does not fit the country's IBAN structure."
);
create_exception!(
    swifter,
    InvalidBranchCode,
    SwifterError,
    "The branch code does not fit the country's IBAN structure."
);
create_exception!(
    swifter,
    InvalidAccountCode,
    SwifterError,
    "The account code does not fit the country's IBAN structure."
);

/// Remove all whitespace and uppercase, the normalization applied to all
/// input values.
fn clean(value: &str) -> String {
    value
        .chars()
        .filter(|ch| !ch.is_whitespace())
        .flat_map(char::to_uppercase)
        .collect()
}

/// The IBAN specification for a country code, if registered.
fn find_spec(country_code: &str) -> Option<&'static IbanSpec> {
    IBAN_SPECS
        .binary_search_by_key(&country_code, |spec| spec.country)
        .ok()
        .map(|pos| &IBAN_SPECS[pos])
}

/// Whether a byte matches a BBAN character class: 0 = digits,
/// 1 = uppercase letters, 2 = uppercase letters and digits.
#[inline]
fn class_matches(class: u8, byte: u8) -> bool {
    match class {
        0 => byte.is_ascii_digit(),
        1 => byte.is_ascii_uppercase(),
        _ => byte.is_ascii_digit() || byte.is_ascii_uppercase(),
    }
}

/// The ISO 7064 mod-97-10 remainder of a string, where digits keep their
/// value and uppercase letters map to 10-35. None for other characters.
fn mod97(s: &str) -> Option<u32> {
    let mut remainder: u32 = 0;
    for byte in s.bytes() {
        let value = match byte {
            b'0'..=b'9' => u32::from(byte - b'0'),
            b'A'..=b'Z' => u32::from(byte - b'A') + 10,
            _ => return None,
        };
        remainder = if value < 10 {
            (remainder * 10 + value) % 97
        } else {
            (remainder * 100 + value) % 97
        };
    }
    Some(remainder)
}

/// The checksum digits that make `<country_code><digits><bban>` pass the
/// mod-97-10 check.
fn compute_checksum_digits(country_code: &str, bban: &str) -> PyResult<String> {
    let remainder = mod97(&format!("{bban}{country_code}00"))
        .ok_or_else(|| InvalidStructure::new_err("Invalid characters in IBAN"))?;
    Ok(format!("{:02}", 98 - remainder))
}

/// Validate a compact IBAN and return its country's specification.
fn validate_iban(compact: &str) -> PyResult<&'static IbanSpec> {
    if !compact.bytes().all(|byte| byte.is_ascii_alphanumeric()) {
        return Err(InvalidStructure::new_err("Invalid characters in IBAN"));
    }
    let country_code = compact.get(0..2).unwrap_or("");
    if !country_code.bytes().all(|byte| byte.is_ascii_uppercase()) {
        return Err(InvalidStructure::new_err(format!(
            "Invalid country code {country_code:?}"
        )));
    }
    let Some(spec) = find_spec(country_code) else {
        return Err(InvalidCountryCode::new_err(format!(
            "Unknown country code {country_code:?}"
        )));
    };
    if compact.len() != spec.iban_length as usize {
        return Err(InvalidLength::new_err(format!(
            "Invalid IBAN length: expected {} characters for {country_code}, got {}",
            spec.iban_length,
            compact.len(),
        )));
    }
    let checksum_digits = &compact[2..4];
    if !checksum_digits.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(InvalidStructure::new_err(
            "Invalid characters in IBAN checksum digits",
        ));
    }
    let bban = &compact[4..];
    let mut bytes = bban.bytes();
    for &(length, class) in spec.groups {
        for _ in 0..length {
            // Lengths sum to the BBAN length, checked above.
            let byte = bytes.next().unwrap();
            if !class_matches(class, byte) {
                return Err(InvalidStructure::new_err(format!(
                    "Invalid BBAN structure: {bban:?} does not match {country_code}"
                )));
            }
        }
    }
    if mod97(&format!("{}{}", bban, &compact[..4])) != Some(1) {
        return Err(InvalidChecksumDigits::new_err(format!(
            "Invalid checksum digits in IBAN {compact:?}"
        )));
    }
    Ok(spec)
}

/// The value spaced into groups of four characters.
fn format_in_fours(compact: &str) -> String {
    let chars: Vec<char> = compact.chars().collect();
    chars
        .chunks(4)
        .map(|chunk| chunk.iter().collect::<String>())
        .collect::<Vec<String>>()
        .join(" ")
}

/// Compare against another instance of the same class or a string, for
/// __richcmp__ implementations.
fn compare_str(
    compact: &str,
    other_compact: Option<String>,
    op: CompareOp,
    py: Python<'_>,
) -> PyResult<Py<PyAny>> {
    match other_compact {
        Some(other) => op.matches(compact.cmp(&other)).into_py_any(py),
        None => Ok(py.NotImplemented()),
    }
}

/// Right-align a component within a zero-filled BBAN field.
fn place_component(
    bban: &mut [u8],
    range: (u8, u8),
    component: &str,
    make_error: fn(String) -> PyErr,
    label: &str,
) -> PyResult<()> {
    let (start, end) = (range.0 as usize, range.1 as usize);
    let width = end - start;
    if component.len() > width {
        return Err(make_error(format!(
            "{label} exceeds its {width} character field"
        )));
    }
    bban[end - component.len()..end].copy_from_slice(component.as_bytes());
    Ok(())
}

/// An International Bank Account Number.
///
/// Instantiating validates the IBAN and raises a `SwifterError` subclass
/// for invalid values, unless `allow_invalid` is true.
#[allow(clippy::upper_case_acronyms)]
#[pyclass(frozen, module = "swifter")]
struct IBAN {
    compact: String,
    spec: Option<&'static IbanSpec>,
}

impl IBAN {
    fn from_compact(compact: String, allow_invalid: bool) -> PyResult<Self> {
        if !allow_invalid {
            validate_iban(&compact)?;
        }
        let spec = compact.get(0..2).and_then(find_spec);
        Ok(IBAN { compact, spec })
    }

    fn spec(&self) -> PyResult<&'static IbanSpec> {
        self.spec.ok_or_else(|| {
            InvalidCountryCode::new_err(format!(
                "Unknown country code {:?}",
                self.compact.get(0..2).unwrap_or("")
            ))
        })
    }

    fn bban_slice(&self, range: (u8, u8)) -> &str {
        self.compact
            .get(4 + range.0 as usize..4 + range.1 as usize)
            .unwrap_or("")
    }
}

#[pymethods]
impl IBAN {
    #[new]
    #[pyo3(signature = (iban, *, allow_invalid = false))]
    fn new(iban: &str, allow_invalid: bool) -> PyResult<Self> {
        Self::from_compact(clean(iban), allow_invalid)
    }

    /// Create an IBAN from a country code and BBAN, computing the checksum
    /// digits.
    #[classmethod]
    #[pyo3(signature = (country_code, bban, *, allow_invalid = false))]
    fn from_bban(
        _cls: &Bound<'_, PyType>,
        country_code: &str,
        bban: &str,
        allow_invalid: bool,
    ) -> PyResult<Self> {
        let country_code = clean(country_code);
        let bban = clean(bban);
        let checksum_digits = compute_checksum_digits(&country_code, &bban)?;
        Self::from_compact(
            format!("{country_code}{checksum_digits}{bban}"),
            allow_invalid,
        )
    }

    /// Generate an IBAN from its components, right-aligning each within its
    /// field with zeroes, and computing the checksum digits.
    #[classmethod]
    #[pyo3(signature = (country_code, *, bank_code, account_code, branch_code = ""))]
    fn generate(
        cls: &Bound<'_, PyType>,
        country_code: &str,
        bank_code: &str,
        account_code: &str,
        branch_code: &str,
    ) -> PyResult<Self> {
        let country_code = clean(country_code);
        let spec = find_spec(&country_code).ok_or_else(|| {
            InvalidCountryCode::new_err(format!("Unknown country code {country_code:?}"))
        })?;
        let mut bban = vec![b'0'; spec.iban_length as usize - 4];
        place_component(
            &mut bban,
            spec.bank_code,
            &clean(bank_code),
            InvalidBankCode::new_err,
            "Bank code",
        )?;
        place_component(
            &mut bban,
            spec.branch_code,
            &clean(branch_code),
            InvalidBranchCode::new_err,
            "Branch code",
        )?;
        place_component(
            &mut bban,
            spec.account_code,
            &clean(account_code),
            InvalidAccountCode::new_err,
            "Account code",
        )?;
        // The components are ASCII, checked in place_component.
        let bban = String::from_utf8(bban).unwrap();
        Self::from_bban(cls, &country_code, &bban, false)
    }

    /// Validate the IBAN, returning True or raising a `SwifterError`
    /// subclass.
    fn validate(&self) -> PyResult<bool> {
        validate_iban(&self.compact)?;
        Ok(true)
    }

    /// Whether the IBAN is valid.
    #[getter]
    fn is_valid(&self) -> bool {
        validate_iban(&self.compact).is_ok()
    }

    /// The IBAN without any spaces.
    #[getter]
    fn compact(&self) -> &str {
        &self.compact
    }

    /// The IBAN spaced into groups of four characters.
    #[getter]
    fn formatted(&self) -> String {
        format_in_fours(&self.compact)
    }

    /// The ISO 3166 alpha-2 country code.
    #[getter]
    fn country_code(&self) -> &str {
        self.compact.get(0..2).unwrap_or("")
    }

    /// The two checksum digits after the country code.
    #[getter]
    fn checksum_digits(&self) -> &str {
        self.compact.get(2..4).unwrap_or("")
    }

    /// The country-specific Basic Bank Account Number: everything after the
    /// country code and checksum digits.
    #[getter]
    fn bban(&self) -> &str {
        self.compact.get(4..).unwrap_or("")
    }

    /// The country-specific bank code, or an empty string if the country
    /// does not define its position.
    #[getter]
    fn bank_code(&self) -> PyResult<&str> {
        Ok(self.bban_slice(self.spec()?.bank_code))
    }

    /// The country-specific branch code, or an empty string if the country
    /// does not define one.
    #[getter]
    fn branch_code(&self) -> PyResult<&str> {
        Ok(self.bban_slice(self.spec()?.branch_code))
    }

    /// The country-specific account code, or an empty string if the country
    /// does not define its position.
    #[getter]
    fn account_code(&self) -> PyResult<&str> {
        Ok(self.bban_slice(self.spec()?.account_code))
    }

    /// The country-specific checksum digits within the BBAN, or an empty
    /// string if the country does not have any.
    #[getter]
    fn national_checksum_digits(&self) -> PyResult<&str> {
        Ok(self.bban_slice(self.spec()?.national_checksum_digits))
    }

    /// Whether the country is in the Single Euro Payments Area.
    #[getter]
    fn in_sepa_zone(&self) -> PyResult<bool> {
        Ok(self.spec()?.in_sepa_zone)
    }

    fn __str__(&self) -> &str {
        &self.compact
    }

    fn __repr__(&self) -> String {
        format!("<IBAN={}>", self.compact)
    }

    fn __len__(&self) -> usize {
        self.compact.chars().count()
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        PyString::new(py, &self.compact).hash()
    }

    fn __richcmp__(
        &self,
        other: &Bound<'_, PyAny>,
        op: CompareOp,
        py: Python<'_>,
    ) -> PyResult<Py<PyAny>> {
        let other_compact = if let Ok(iban) = other.cast::<IBAN>() {
            Some(iban.get().compact.clone())
        } else {
            other.extract::<String>().ok()
        };
        compare_str(&self.compact, other_compact, op, py)
    }
}

/// A Business Identifier Code, as defined in ISO 9362:2022.
///
/// Instantiating validates the BIC and raises a `SwifterError` subclass
/// for invalid values, unless `allow_invalid` is true.
#[allow(clippy::upper_case_acronyms)]
#[pyclass(frozen, module = "swifter")]
struct BIC {
    compact: String,
}

/// Validate a compact BIC.
fn validate_bic(compact: &str) -> PyResult<()> {
    let char_count = compact.chars().count();
    if char_count != 8 && char_count != 11 {
        return Err(InvalidLength::new_err(format!(
            "Invalid BIC length: expected 8 or 11 characters, got {char_count}"
        )));
    }
    let bytes = compact.as_bytes();
    let structure_ok = bytes[0..4].iter().all(u8::is_ascii_alphanumeric)
        && bytes[4..6].iter().all(u8::is_ascii_uppercase)
        && bytes[6..].iter().all(u8::is_ascii_alphanumeric);
    if !structure_ok {
        return Err(InvalidStructure::new_err(format!(
            "Invalid BIC structure {compact:?}"
        )));
    }
    let country_code = &compact[4..6];
    if ISO3166_COUNTRIES.binary_search(&country_code).is_err() {
        return Err(InvalidCountryCode::new_err(format!(
            "Unknown country code {country_code:?}"
        )));
    }
    Ok(())
}

#[pymethods]
impl BIC {
    #[new]
    #[pyo3(signature = (bic, *, allow_invalid = false))]
    fn new(bic: &str, allow_invalid: bool) -> PyResult<Self> {
        let compact = clean(bic);
        if !allow_invalid {
            validate_bic(&compact)?;
        }
        Ok(BIC { compact })
    }

    /// Validate the BIC, returning True or raising a `SwifterError`
    /// subclass.
    fn validate(&self) -> PyResult<bool> {
        validate_bic(&self.compact)?;
        Ok(true)
    }

    /// Whether the BIC is valid.
    #[getter]
    fn is_valid(&self) -> bool {
        validate_bic(&self.compact).is_ok()
    }

    /// The BIC without any spaces.
    #[getter]
    fn compact(&self) -> &str {
        &self.compact
    }

    /// The BIC spaced into its components.
    #[getter]
    fn formatted(&self) -> String {
        let mut parts = Vec::with_capacity(4);
        for range in [0..4, 4..6, 6..8, 8..11] {
            if let Some(part) = self.compact.get(range) {
                if !part.is_empty() {
                    parts.push(part);
                }
            }
        }
        parts.join(" ")
    }

    /// The bank code: the first four characters.
    #[getter]
    fn bank_code(&self) -> &str {
        self.compact.get(0..4).unwrap_or("")
    }

    /// The ISO 3166 alpha-2 country code.
    #[getter]
    fn country_code(&self) -> &str {
        self.compact.get(4..6).unwrap_or("")
    }

    /// The two-character location code.
    #[getter]
    fn location_code(&self) -> &str {
        self.compact.get(6..8).unwrap_or("")
    }

    /// The three-character branch code, or an empty string for eight
    /// character BICs.
    #[getter]
    fn branch_code(&self) -> &str {
        self.compact.get(8..11).unwrap_or("")
    }

    /// The connection type indicated by the location code: "testing",
    /// "passive", "reverse billing", or "default".
    #[getter(r#type)]
    fn type_(&self) -> &'static str {
        match self.compact.as_bytes().get(7) {
            Some(b'0') => "testing",
            Some(b'1') => "passive",
            Some(b'2') => "reverse billing",
            _ => "default",
        }
    }

    fn __str__(&self) -> &str {
        &self.compact
    }

    fn __repr__(&self) -> String {
        format!("<BIC={}>", self.compact)
    }

    fn __len__(&self) -> usize {
        self.compact.chars().count()
    }

    fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
        PyString::new(py, &self.compact).hash()
    }

    fn __richcmp__(
        &self,
        other: &Bound<'_, PyAny>,
        op: CompareOp,
        py: Python<'_>,
    ) -> PyResult<Py<PyAny>> {
        let other_compact = if let Ok(bic) = other.cast::<BIC>() {
            Some(bic.get().compact.clone())
        } else {
            other.extract::<String>().ok()
        };
        compare_str(&self.compact, other_compact, op, py)
    }
}

#[pymodule(gil_used = false)]
fn _core(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<IBAN>()?;
    m.add_class::<BIC>()?;
    m.add("SwifterError", py.get_type::<SwifterError>())?;
    m.add("InvalidLength", py.get_type::<InvalidLength>())?;
    m.add("InvalidStructure", py.get_type::<InvalidStructure>())?;
    m.add("InvalidCountryCode", py.get_type::<InvalidCountryCode>())?;
    m.add(
        "InvalidChecksumDigits",
        py.get_type::<InvalidChecksumDigits>(),
    )?;
    m.add("InvalidBankCode", py.get_type::<InvalidBankCode>())?;
    m.add("InvalidBranchCode", py.get_type::<InvalidBranchCode>())?;
    m.add("InvalidAccountCode", py.get_type::<InvalidAccountCode>())?;
    let country_codes: Vec<&str> = IBAN_SPECS.iter().map(|spec| spec.country).collect();
    m.add("COUNTRY_CODES", PyList::new(py, &country_codes)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clean() {
        assert_eq!(clean(" de89 3704\t0044 "), "DE8937040044");
        assert_eq!(clean("gb82west"), "GB82WEST");
    }

    #[test]
    fn test_mod97() {
        // From the ISO 13616 example IBAN
        assert_eq!(mod97("WEST12345698765432GB82"), Some(1));
        assert_eq!(mod97("_"), None);
    }

    #[test]
    fn test_find_spec() {
        assert_eq!(find_spec("DE").unwrap().iban_length, 22);
        assert!(find_spec("XX").is_none());
        assert!(find_spec("").is_none());
    }

    #[test]
    fn test_validate_iban() {
        assert!(validate_iban("GB82WEST12345698765432").is_ok());
        assert!(validate_iban("GB82WEST1234569876543").is_err());
        assert!(validate_iban("GB83WEST12345698765432").is_err());
        assert!(validate_iban("GB82TEST1234569876543E").is_err());
    }

    #[test]
    fn test_compute_checksum_digits() {
        assert_eq!(
            compute_checksum_digits("GB", "WEST12345698765432").unwrap(),
            "82"
        );
    }
}
