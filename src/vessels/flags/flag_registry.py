# ============================================================================
# Project X
# Vessel Flag Registry
# ============================================================================

import os
from pathlib import Path
from threading import Lock

from vessels.flags.flag_record import FlagRecord

from app.paths import resource_path

_FLAGS_PACKAGE_DIR = Path(__file__).resolve().parent

FLAGS_DIR = Path(
    os.environ.get(
        "PROJECTX_FLAGS_DIR",
        str(resource_path("flags")),
    )
)

DEFAULT_FLAG_FILE = "default.svg"

ALPHA3_TO_ALPHA2 = {
    "AFG": "AF",
    "ALA": "AX",
    "ALB": "AL",
    "DZA": "DZ",
    "ASM": "AS",
    "AND": "AD",
    "AGO": "AO",
    "AIA": "AI",
    "ATA": "AQ",
    "ATG": "AG",
    "ARG": "AR",
    "ARM": "AM",
    "ABW": "AW",
    "AUS": "AU",
    "AUT": "AT",
    "AZE": "AZ",
    "BHS": "BS",
    "BHR": "BH",
    "BGD": "BD",
    "BRB": "BB",
    "BLR": "BY",
    "BEL": "BE",
    "BLZ": "BZ",
    "BEN": "BJ",
    "BMU": "BM",
    "BTN": "BT",
    "BOL": "BO",
    "BES": "BQ",
    "BIH": "BA",
    "BWA": "BW",
    "BVT": "BV",
    "BRA": "BR",
    "IOT": "IO",
    "BRN": "BN",
    "BGR": "BG",
    "BFA": "BF",
    "BDI": "BI",
    "CPV": "CV",
    "KHM": "KH",
    "CMR": "CM",
    "CAN": "CA",
    "CYM": "KY",
    "CAF": "CF",
    "TCD": "TD",
    "CHL": "CL",
    "CHN": "CN",
    "CXR": "CX",
    "CCK": "CC",
    "COL": "CO",
    "COM": "KM",
    "COG": "CG",
    "COD": "CD",
    "COK": "CK",
    "CRI": "CR",
    "CIV": "CI",
    "HRV": "HR",
    "CUB": "CU",
    "CUW": "CW",
    "CYP": "CY",
    "CZE": "CZ",
    "DNK": "DK",
    "DJI": "DJ",
    "DMA": "DM",
    "DOM": "DO",
    "ECU": "EC",
    "EGY": "EG",
    "SLV": "SV",
    "GNQ": "GQ",
    "ERI": "ER",
    "EST": "EE",
    "SWZ": "SZ",
    "ETH": "ET",
    "FLK": "FK",
    "FRO": "FO",
    "FJI": "FJ",
    "FIN": "FI",
    "FRA": "FR",
    "GUF": "GF",
    "PYF": "PF",
    "ATF": "TF",
    "GAB": "GA",
    "GMB": "GM",
    "GEO": "GE",
    "DEU": "DE",
    "GHA": "GH",
    "GIB": "GI",
    "GRC": "GR",
    "GRL": "GL",
    "GRD": "GD",
    "GLP": "GP",
    "GUM": "GU",
    "GTM": "GT",
    "GGY": "GG",
    "GIN": "GN",
    "GNB": "GW",
    "GUY": "GY",
    "HTI": "HT",
    "HMD": "HM",
    "VAT": "VA",
    "HND": "HN",
    "HKG": "HK",
    "HUN": "HU",
    "ISL": "IS",
    "IND": "IN",
    "IDN": "ID",
    "IRN": "IR",
    "IRQ": "IQ",
    "IRL": "IE",
    "IMN": "IM",
    "ISR": "IL",
    "ITA": "IT",
    "JAM": "JM",
    "JPN": "JP",
    "JEY": "JE",
    "JOR": "JO",
    "KAZ": "KZ",
    "KEN": "KE",
    "KIR": "KI",
    "PRK": "KP",
    "KOR": "KR",
    "KWT": "KW",
    "KGZ": "KG",
    "LAO": "LA",
    "LVA": "LV",
    "LBN": "LB",
    "LSO": "LS",
    "LBR": "LR",
    "LBY": "LY",
    "LIE": "LI",
    "LTU": "LT",
    "LUX": "LU",
    "MAC": "MO",
    "MDG": "MG",
    "MWI": "MW",
    "MYS": "MY",
    "MDV": "MV",
    "MLI": "ML",
    "MLT": "MT",
    "MHL": "MH",
    "MTQ": "MQ",
    "MRT": "MR",
    "MUS": "MU",
    "MYT": "YT",
    "MEX": "MX",
    "FSM": "FM",
    "MDA": "MD",
    "MCO": "MC",
    "MNG": "MN",
    "MNE": "ME",
    "MSR": "MS",
    "MAR": "MA",
    "MOZ": "MZ",
    "MMR": "MM",
    "NAM": "NA",
    "NRU": "NR",
    "NPL": "NP",
    "NLD": "NL",
    "NCL": "NC",
    "NZL": "NZ",
    "NIC": "NI",
    "NER": "NE",
    "NGA": "NG",
    "NIU": "NU",
    "NFK": "NF",
    "MKD": "MK",
    "MNP": "MP",
    "NOR": "NO",
    "OMN": "OM",
    "PAK": "PK",
    "PLW": "PW",
    "PSE": "PS",
    "PAN": "PA",
    "PNG": "PG",
    "PRY": "PY",
    "PER": "PE",
    "PHL": "PH",
    "PCN": "PN",
    "POL": "PL",
    "PRT": "PT",
    "PRI": "PR",
    "QAT": "QA",
    "REU": "RE",
    "ROU": "RO",
    "RUS": "RU",
    "RWA": "RW",
    "BLM": "BL",
    "SHN": "SH",
    "KNA": "KN",
    "LCA": "LC",
    "MAF": "MF",
    "SPM": "PM",
    "VCT": "VC",
    "WSM": "WS",
    "SMR": "SM",
    "STP": "ST",
    "SAU": "SA",
    "SEN": "SN",
    "SRB": "RS",
    "SYC": "SC",
    "SLE": "SL",
    "SGP": "SG",
    "SXM": "SX",
    "SVK": "SK",
    "SVN": "SI",
    "SLB": "SB",
    "SOM": "SO",
    "ZAF": "ZA",
    "SGS": "GS",
    "SSD": "SS",
    "ESP": "ES",
    "LKA": "LK",
    "SDN": "SD",
    "SUR": "SR",
    "SJM": "SJ",
    "SWE": "SE",
    "CHE": "CH",
    "SYR": "SY",
    "TWN": "TW",
    "TJK": "TJ",
    "TZA": "TZ",
    "THA": "TH",
    "TLS": "TL",
    "TGO": "TG",
    "TKL": "TK",
    "TON": "TO",
    "TTO": "TT",
    "TUN": "TN",
    "TUR": "TR",
    "TKM": "TM",
    "TCA": "TC",
    "TUV": "TV",
    "UGA": "UG",
    "UKR": "UA",
    "ARE": "AE",
    "GBR": "GB",
    "USA": "US",
    "UMI": "UM",
    "URY": "UY",
    "UZB": "UZ",
    "VUT": "VU",
    "VEN": "VE",
    "VNM": "VN",
    "VGB": "VG",
    "VIR": "VI",
    "WLF": "WF",
    "ESH": "EH",
    "YEM": "YE",
    "ZMB": "ZM",
    "ZWE": "ZW",
}

COUNTRY_NAMES = {
    "HU": "Hungary",
    "AT": "Austria",
    "DE": "Germany",
    "FR": "France",
    "GB": "United Kingdom",
    "US": "United States",
    "NL": "Netherlands",
    "IT": "Italy",
    "ES": "Spain",
    "PL": "Poland",
    "RO": "Romania",
    "HR": "Croatia",
    "RS": "Serbia",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "CZ": "Czechia",
    "DK": "Denmark",
    "SE": "Sweden",
    "NO": "Norway",
    "FI": "Finland",
    "GR": "Greece",
    "TR": "Turkey",
    "UA": "Ukraine",
    "RU": "Russia",
    "CN": "China",
    "JP": "Japan",
    "BE": "Belgium",
}


def normalize_country_code(value: str | None) -> str | None:

    text = str(value or "").strip()

    if not text:
        return None

    if len(text) == 2:
        return text.upper()

    if len(text) == 3:
        alpha3 = text.upper()
        return ALPHA3_TO_ALPHA2.get(alpha3)

    return None


class FlagRegistry:

    def __init__(self, flags_dir: Path | str | None = None):

        self._flags_dir = Path(flags_dir or FLAGS_DIR)
        self._flags: dict[str, FlagRecord] = {}
        self._default_flag = FlagRecord(
            country_code="",
            name="Unknown",
            svg_file=str(self._flags_dir / DEFAULT_FLAG_FILE),
            source="builtin",
        )
        self._lock = Lock()
        self._load_builtin_flags()

    @property
    def flags_dir(self) -> Path:

        return self._flags_dir

    def get(self, country_code: str) -> FlagRecord | None:

        normalized = normalize_country_code(country_code)

        if normalized is None:
            return None

        with self._lock:
            return self._flags.get(normalized)

    def has(self, country_code: str) -> bool:

        record = self.get(country_code)

        if record is None:
            return False

        return self._svg_exists(record)

    def register(self, record: FlagRecord) -> FlagRecord:

        normalized = normalize_country_code(record.country_code)

        if normalized is None:
            raise ValueError("Flag record requires a valid country code")

        payload = FlagRecord(
            country_code=normalized,
            name=record.safe_text(record.name) or COUNTRY_NAMES.get(normalized, ""),
            svg_file=record.safe_text(record.svg_file),
            source=record.safe_text(record.source) or "registered",
        )

        if not payload.svg_file:
            raise ValueError("Flag record requires an SVG file path")

        with self._lock:
            self._flags[normalized] = payload

        return payload

    def available_codes(self) -> list[str]:

        with self._lock:
            codes = list(self._flags.keys())

        valid_codes = [
            code
            for code in codes
            if self._svg_exists(self._flags[code])
        ]

        return sorted(valid_codes)

    def default_flag(self) -> FlagRecord:

        return self._default_flag

    def resolve_svg_path(self, record: FlagRecord) -> Path | None:

        return self._resolve_svg_path(record.svg_file)

    def _load_builtin_flags(self) -> None:

        self._flags_dir.mkdir(parents=True, exist_ok=True)

        for svg_path in sorted(self._flags_dir.glob("*.svg")):
            if svg_path.name == DEFAULT_FLAG_FILE:
                continue

            code = svg_path.stem.upper()

            if len(code) != 2 or not code.isalpha():
                continue

            self._flags[code] = FlagRecord(
                country_code=code,
                name=COUNTRY_NAMES.get(code, ""),
                svg_file=str(svg_path),
                source="builtin",
            )

    def _resolve_svg_path(self, svg_file: str | None) -> Path | None:

        text = str(svg_file or "").strip()

        if not text:
            return None

        path = Path(text)

        if not path.is_absolute():
            path = self._flags_dir / path

        if path.exists() and path.is_file():
            return path

        return None

    def _svg_exists(self, record: FlagRecord) -> bool:

        return self._resolve_svg_path(record.svg_file) is not None


flag_registry = FlagRegistry()
