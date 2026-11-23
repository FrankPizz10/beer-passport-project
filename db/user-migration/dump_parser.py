"""Parse mysqldump INSERT statements into row dicts.

Stdlib only. Handles the mysqldump output format produced by the EFS
recovery guide (Phase H): backtick-quoted identifiers, an explicit column
list per INSERT, and value tuples containing NULL, numbers, hex literals
(0x...), and single-quoted strings with MySQL backslash escapes or doubled
single quotes. Character-set introducers (_utf8, _binary, ...) are accepted
and stripped; the underlying bytes are decoded as UTF-8 with replacement
so mojibake in the source survives to the transform stage, where it is
detected and repaired deliberately rather than silently.
"""

import re

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")
_INTRODUCER_RE = re.compile(r"^_(utf8mb4|utf8|binary|latin1)\s*", re.IGNORECASE)
_INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+`(?P<table>[^`]+)`\s*\((?P<cols>[^)]*)\)\s*VALUES\s*",
    re.IGNORECASE,
)

_ESCAPES = {
    "0": "\0",
    "'": "'",
    '"': '"',
    "b": "\b",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "Z": "\x1a",
    "\\": "\\",
}


def _parse_string(text, i):
    """Parse a single-quoted string starting at text[i] == "'".

    Returns (value, next_index). MySQL escapes: backslash sequences and
    doubled single quotes.
    """
    assert text[i] == "'"
    i += 1
    out = []
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n:
            nxt = text[i + 1]
            out.append(_ESCAPES.get(nxt, nxt))
            i += 2
        elif c == "'":
            if i + 1 < n and text[i + 1] == "'":
                out.append("'")
                i += 2
            else:
                return "".join(out), i + 1
        else:
            out.append(c)
            i += 1
    raise ValueError("unterminated string literal in dump")


def _parse_value(text, i):
    """Parse one scalar value starting at or after index i.

    Returns (value, next_index) where value is None, int, float, or str.
    """
    n = len(text)
    while i < n and text[i] in " \t\r\n":
        i += 1
    if text.startswith("NULL", i) and (i + 4 >= n or not (text[i + 4].isalnum() or text[i + 4] == "_")):
        return None, i + 4
    m = _INTRODUCER_RE.match(text, i)
    if m:
        i = m.end()
    if i < n and text[i] == "'":
        return _parse_string(text, i)
    if text.startswith("0x", i) or text.startswith("0X", i):
        j = i + 2
        while j < n and text[j] in "0123456789abcdefABCDEF":
            j += 1
        raw = bytes.fromhex(text[i + 2 : j])
        return raw.decode("utf-8", errors="replace"), j
    j = i
    while j < n and text[j] not in ",)":
        j += 1
    token = text[i:j].strip()
    if _INT_RE.match(token):
        return int(token), j
    if _FLOAT_RE.match(token):
        return float(token), j
    raise ValueError(f"unrecognized value token at offset {i}: {token!r}")


def _parse_tuple(text, i):
    """Parse one parenthesized value tuple starting at text[i] == '('."""
    assert text[i] == "("
    i += 1
    values = []
    n = len(text)
    while True:
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i < n and text[i] == ")":
            return values, i + 1
        value, i = _parse_value(text, i)
        values.append(value)
        while i < n and text[i] in " \t\r\n":
            i += 1
        if i < n and text[i] == ",":
            i += 1
            continue
        if i < n and text[i] == ")":
            return values, i + 1
        raise ValueError(f"unexpected character in tuple at offset {i}: {text[i:i+20]!r}")


def parse_dump(sql_text):
    """Parse all INSERT statements in a mysqldump file.

    Returns {table_name: [row_dict, ...]} preserving file order. Raises
    ValueError on malformed input or a column/value count mismatch, so a
    truncated or corrupt dump fails loudly instead of loading partially.
    """
    tables = {}
    pos = 0
    while True:
        m = _INSERT_RE.search(sql_text, pos)
        if not m:
            break
        table = m.group("table")
        cols = [c.strip().strip("`") for c in m.group("cols").split(",")]
        i = m.end()
        n = len(sql_text)
        rows = tables.setdefault(table, [])
        while True:
            while i < n and sql_text[i] in " \t\r\n":
                i += 1
            if i < n and sql_text[i] == "(":
                values, i = _parse_tuple(sql_text, i)
                if len(values) != len(cols):
                    raise ValueError(
                        f"{table}: row has {len(values)} values for {len(cols)} columns"
                    )
                rows.append(dict(zip(cols, values)))
                while i < n and sql_text[i] in " \t\r\n":
                    i += 1
                if i < n and sql_text[i] == ",":
                    i += 1
                    continue
                if i < n and sql_text[i] == ";":
                    i += 1
                    break
                raise ValueError(f"{table}: unexpected character after tuple at offset {i}")
            elif i < n and sql_text[i] == ";":
                i += 1
                break
            else:
                raise ValueError(f"{table}: expected value tuple at offset {i}")
        pos = i
    return tables
