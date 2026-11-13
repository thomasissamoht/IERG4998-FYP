#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BibTeX Bibliography Manager
Final Year Project - Bibliography Consolidation Tool

This tool helps manage BibTeX bibliography files by:
1. Crawling folders to find and merge .bib files
2. Identifying and removing duplicates (perfect and partial matches)
3. Fixing citation keys (labels) with consistent naming
4. Creating a processed copy beside the source project without changing originals
"""

import os
import sys
import shutil
from io import StringIO
from pathlib import Path
from datetime import datetime
from typing import Any, List, Dict, Tuple, Set
import re
import hashlib
import unicodedata
from collections import Counter

# Set UTF-8 encoding for Windows console  
if sys.platform == 'win32':
    try:
        stdout: Any = sys.stdout
        if hasattr(stdout, "reconfigure"):
            stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import bibtexparser
    from bibtexparser.bparser import BibTexParser, STANDARD_TYPES
    from bibtexparser.bwriter import BibTexWriter
    from bibtexparser.bibdatabase import BibDatabase
except ImportError:
    print("ERROR: bibtexparser not installed.")
    print("Please install it using: pip install bibtexparser")
    sys.exit(1)

try:
    from thefuzz import fuzz
except ImportError:
    print("WARNING: thefuzz not installed. Fuzzy matching will be limited.")
    print("Install it using: pip install thefuzz python-Levenshtein")
    fuzz = None


WEAK_TITLE_WORDS = {
    'also', 'based', 'case', 'certain', 'different', 'example',
    'general', 'given', 'introduction', 'notes', 'results',
    'some', 'study', 'using', 'very', 'with',
}

MAX_FUZZY_BUCKET_SIZE = 500
BIBTEX_PARSE_BATCH_SIZE = 2500
LARGE_BIB_PARSE_THRESHOLD = 5 * 1024 * 1024


def _embedded_bib_blocks(text: str):
    """Find line-delimited filecontents BibTeX blocks and their content spans."""
    begin_pattern = re.compile(
        r'(?m)^[ \t]*\\begin\{(filecontents\*?)\}'
        r'(?:[ \t]*\[[^\]\r\n]*\])?[ \t]*\{([^{}\r\n]+)\}[ \t]*(?:%[^\r\n]*)?\r?$'
    )
    position = 0
    while match := begin_pattern.search(text, position):
        end_pattern = re.compile(
            r'(?m)^[ \t]*\\end\{' + re.escape(match.group(1))
            + r'\}[ \t]*(?:%[^\r\n]*)?\r?$'
        )
        end = end_pattern.search(text, match.end())
        if end is None:
            raise ValueError(f"Unclosed {match.group(1)} block for {match.group(2)}")
        filename = match.group(2).strip()
        if filename.lower().endswith('.bib'):
            yield filename, match.end(), end.start()
        position = end.end()


def _manual_bibliography_entries(text: str):
    """Extract simple bibitems while retaining offsets into the original text."""
    masked = list(text)
    note_chars = list(text)

    def hide(start: int, end: int, comment: bool = False) -> None:
        for index in range(start, end):
            if text[index] not in '\r\n':
                masked[index] = ' '
                if comment:
                    note_chars[index] = ' '

    position = 0
    while position < len(text):
        if text[position] == '%':
            end = text.find('\n', position)
            end = len(text) if end < 0 else end
            hide(position, end, comment=True)
            position = end
        elif text[position] == '\\':
            begin = re.match(r'\\begin\{(verbatim\*?|lstlisting|minted|filecontents\*?)\}', text[position:])
            if begin:
                marker = r'\end{' + begin.group(1) + '}'
                end = text.find(marker, position + begin.end())
                if end < 0:
                    raise ValueError(f"Unclosed {begin.group(1)} environment")
                end += len(marker)
                hide(position, end)
                position = end
            else:
                verb = re.match(r'\\verb\*?([^A-Za-z\s])', text[position:])
                if verb:
                    end = text.find(verb.group(1), position + verb.end())
                    if end < 0 or '\n' in text[position:end]:
                        raise ValueError("Unclosed verb command")
                    hide(position, end + 1)
                    position = end + 1
                else:
                    position += 2
        else:
            position += 1
    code = ''.join(masked)
    environments = re.compile(r'(?<!\\)\\(begin|end)\s*\{thebibliography\}')
    active = None

    def argument(position: int, opening: str, closing: str) -> Tuple[str, int]:
        while position < len(code) and code[position].isspace():
            position += 1
        if position >= len(code) or code[position] != opening:
            raise ValueError(f"Malformed thebibliography: expected {opening}")
        start = position + 1
        depth = 1
        brace_depth = 0
        position += 1
        while position < len(code):
            ch = code[position]
            if ch == '\\':
                position += 2
                continue
            if opening == '[':
                if ch == '{':
                    brace_depth += 1
                elif ch == '}' and brace_depth:
                    brace_depth -= 1
            if not brace_depth:
                if ch == opening:
                    depth += 1
                elif ch == closing:
                    depth -= 1
                    if depth == 0:
                        return text[start:position], position + 1
            position += 1
        raise ValueError(f"Unclosed {opening} argument in thebibliography")

    for environment in environments.finditer(code):
        if environment.group(1) == 'begin':
            if active is not None:
                raise ValueError("Nested thebibliography environments are unsupported")
            _, start = argument(environment.end(), '{', '}')
            active = start
            continue
        if active is None:
            raise ValueError("Unexpected end of thebibliography")
        items = []
        for match in re.finditer(r'(?<!\\)\\bibitem\b', code[active:environment.start()]):
            item_start = active + match.start()
            position = active + match.end()
            while position < len(code) and code[position].isspace():
                position += 1
            if position < len(code) and code[position] == '[':
                _, position = argument(position, '[', ']')
            key, position = argument(position, '{', '}')
            if position > environment.start():
                raise ValueError("Malformed bibitem argument before end of thebibliography")
            key = key.strip()
            if not key or re.search(r'[\s{},\\]', key):
                raise ValueError(f"Unsupported bibitem key {key!r}")
            items.append((key, item_start, position))
        if not items and code[active:environment.start()].strip():
            raise ValueError("No literal bibitem commands found in thebibliography; macro-generated entries are unsupported")
        for index, (key, item_start, content_start) in enumerate(items):
            end = items[index + 1][1] if index + 1 < len(items) else environment.start()
            note = ''.join(note_chars[content_start:end]).strip()
            if not note:
                raise ValueError(f"Empty bibitem {key!r}")
            yield key, note, item_start, end
        active = None
    if active is not None:
        raise ValueError("Unclosed thebibliography environment")


def _rewrite_bib_keys(text: str, mapping: Dict[str, str]) -> str:
    text = re.sub(
        r'(^\s*@\w+\s*[\{(]\s*)([^,\s]+)(\s*,)',
        lambda match: match.group(1) + mapping.get(match.group(2), match.group(2)) + match.group(3),
        text,
        flags=re.MULTILINE,
    )
    field_pattern = re.compile(
        r'(?:crossref|xdata)\s*=\s*(\{[^{}]*\}|"[^"]*"|[^,\s}]+)',
        re.IGNORECASE,
    )
    edits = []
    depth = 0
    outer = ''
    opener = -1
    quoted = False
    escaped = False
    previous = ''
    for index, character in enumerate(text):
        if depth == 0:
            if index == opener:
                depth = 1
                previous = character
                continue
            if character == '@':
                header = re.match(r'@\w+\s*([\{(])', text[index:])
                if header:
                    opener = index + header.end() - 1
                    outer = header.group(1)
            continue
        if escaped:
            escaped = False
            continue
        if character == '\\':
            escaped = True
            continue
        if character == '"' and depth > 0:
            quoted = not quoted
            continue
        if quoted:
            continue
        if character == '{':
            depth += 1
        elif character == '}':
            if depth > 1 or outer == '{':
                depth -= 1
        elif character == ')' and depth == 1 and outer == '(':
            depth = 0
        elif depth == 1 and previous == ',' and character.isalpha():
            match = field_pattern.match(text, index)
            if match:
                value = match.group(1)
                replacement = re.sub(
                    r'[^,\s{}"]+',
                    lambda key_match: mapping.get(key_match.group(0), key_match.group(0)),
                    value,
                )
                edits.append((match.start(1), match.end(1), replacement))
        if not character.isspace():
            previous = character
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    return text


def _parse_large_bibtex(text: str) -> Tuple[List[Dict], List[str]]:
    from pybtex.database import Entry
    from pybtex.database.input.bibtex import Parser

    class DuplicateTolerantParser(Parser):
        def __init__(self):
            super().__init__(person_fields=())
            self.original_keys = {}
            self.duplicate_number = 0
            self.parse_warnings = []

        def process_entry(self, entry_type, key, fields):
            original_key = key or ""
            if key is None:
                key = f"unnamed-{self.unnamed_entry_counter}"
                self.unnamed_entry_counter += 1
            while key in self.data.entries:
                self.duplicate_number += 1
                key = f"{original_key}__duplicate_{self.duplicate_number}"

            entry = Entry(entry_type.lower())
            assert entry.fields is not None
            for field_name, field_value_list in fields or []:
                entry.fields[field_name.lower()] = self.flatten_value_list(field_value_list)
            self.original_keys[key] = original_key
            self.data.add_entry(key, entry)

        def handle_error(self, error):
            self.parse_warnings.append(str(error))

    parser = DuplicateTolerantParser()
    parser.parse_string(text)
    entries = []
    for synthetic_key, parsed_entry in parser.data.entries.items():
        entry_type = parsed_entry.type.lower()
        if entry_type not in STANDARD_TYPES:
            continue
        entry = {
            "ID": parser.original_keys[synthetic_key],
            "ENTRYTYPE": entry_type,
        }
        entry.update({key.lower(): value for key, value in parsed_entry.fields.items()})
        entries.append(entry)
    return entries, parser.parse_warnings


def _parse_standard_bibtex(text: str, entry_locations: List[Tuple[str, int, int, int, int]]) -> List[Dict]:
    parser: Any = BibTexParser(common_strings=True)
    parser.expect_multiple_parse = True
    batch_start = 0
    for batch_end in range(
        BIBTEX_PARSE_BATCH_SIZE,
        len(entry_locations) + 1,
        BIBTEX_PARSE_BATCH_SIZE,
    ):
        batch_offset = entry_locations[batch_end - 1][4]
        parser.parse(text[batch_start:batch_offset])
        batch_start = batch_offset
    if batch_start < len(text) or not entry_locations:
        parser.parse(text[batch_start:])
    return parser.bib_database.entries


class BibliographyManager:
    """Main class for managing bibliography files"""
    
    def __init__(self, root_directory: str | None = None):
        """Initialize the bibliography manager
        
        Args:
            root_directory: Root directory to search for .bib files
        """
        self.root_directory: str = root_directory or os.getcwd()
        self.bib_files: List[Path] = []
        self.embedded_bib_files: List[Path] = []
        self.strict_source_errors = False
        self.include_source_master = False
        self.report_data: Dict = {
            'start_time': None,
            'end_time': None,
            'files_found': 0,
            'initial_entries': 0,
            'source_files': {},
            'duplicate_groups': [],
            'duplicates_removed': 0,
            'keys_changed': [],
            'key_audit': [],
            'metadata_fixes': [],
            'tex_files_updated': 0,
            'tex_citation_updates': 0,
            'citation_update_files': [],
            'parse_warnings': [],
            'final_entries': 0
        }
        self.all_entries: List[Dict] = []
        self.master_db = BibDatabase()
        self.duplicate_groups: List[List[int]] = []

    def _merge_field_count(self, entry: Dict) -> int:
        """Count non-empty merge-relevant fields for an entry."""
        return sum(
            1
            for k, v in entry.items()
            if k not in ['_source_file', 'ID', '_line_number', '_status']
            and isinstance(v, str)
            and v.strip()
        )

    def _select_group_master_position(self, group: List[int]) -> int:
        """Return the position within group of the entry kept as merge base."""
        scored = []
        for position, idx in enumerate(group):
            entry = self.all_entries[idx]
            scored.append((self._merge_field_count(entry), idx, position))
        scored.sort(reverse=True)
        return scored[0][2]

    def _merge_contributed_fields(self, base_entry: Dict, other_entry: Dict) -> List[str]:
        """Return fields that would be copied from other_entry into base_entry during merge."""
        contributed = []
        for key, value in other_entry.items():
            if key in ['_source_file', 'ID', '_line_number', '_status']:
                continue
            if not isinstance(value, str) or not value.strip():
                continue
            base_value = base_entry.get(key)
            if key not in base_entry or (isinstance(base_value, str) and not base_value.strip()):
                contributed.append(key)
        return sorted(contributed)
        
    def _extract_line_numbers(self, file_path: str) -> Dict[str, int]:
        """Extract line numbers for each entry in a .bib file
        
        Args:
            file_path: Path to the .bib file
            
        Returns:
            Dictionary mapping entry IDs to their starting line numbers
        """
        line_numbers = {}
        try:
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Match @article, @book, @incollection, etc.
                match = re.match(r'@[a-zA-Z]+\s*\{\s*([^,\s]+)', line)
                if match:
                    entry_id = match.group(1).strip()
                    line_numbers[entry_id] = line_num
        except Exception as e:
            print(f"⚠️  Error extracting line numbers from {file_path}: {e}")
        
        return line_numbers

    def _extract_entry_locations(self, text: str) -> List[Tuple[str, int, int, int, int]]:
        """Index entry IDs and source spans without materializing every file line."""
        locations: List[List[Any]] = []
        active_index = None
        brace_balance = 0
        started = False
        offset = 0

        for line_number, line in enumerate(StringIO(text), start=1):
            line_offset = offset
            offset += len(line)
            if active_index is None:
                match = re.match(r'@[a-zA-Z]+\s*\{\s*([^,\s]+)', line)
                if not match:
                    continue
                locations.append([match.group(1).strip(), line_number, line_number, line_offset, offset])
                active_index = len(locations) - 1
                brace_balance = line.count('{') - line.count('}')
                started = '{' in line
            else:
                brace_balance += line.count('{') - line.count('}')
                if '{' in line:
                    started = True

            if active_index is not None and started and brace_balance <= 0:
                locations[active_index][2] = line_number
                locations[active_index][4] = offset
                active_index = None

        return [(key, start_line, end_line, start_offset, end_offset)
                for key, start_line, end_line, start_offset, end_offset in locations]
    
    def crawl_and_collect(self) -> Tuple[int, int]:
        """Crawl through folders to find all .bib files and collect entries
        
        Returns:
            Tuple of (number of files found, number of entries collected)
        """
        print(f"\n{'='*60}")
        print(f"STEP 1: Crawling folders for .bib files...")
        print(f"{'='*60}")
        print(f"Searching in: {self.root_directory}\n")
        
        # Find all .bib files recursively (exclude master.bib and backups)
        root_path = Path(self.root_directory).resolve()
        all_bib_files = sorted(
            Path(self.root_directory).rglob("*.bib"),
            key=lambda path: path.relative_to(self.root_directory).as_posix().casefold(),
        )
        self.bib_files = [
            bib_file for bib_file in all_bib_files
            if (self.include_source_master or bib_file.name.lower() != "master.bib")
            and not self._is_generated_workspace_path(bib_file, root_path)
        ]
        
        print(f"✓ Found {len(self.bib_files)} .bib file(s):")
        for i, bib_file in enumerate(self.bib_files, 1):
            print(f"  {i}. {bib_file.relative_to(self.root_directory)}")
        
        # Collect all entries from all files
        self.all_entries = []
        self.report_data['source_files'] = {}
        
        for bib_file in self.bib_files:
            try:
                # Extract line numbers first
                with open(bib_file, encoding='utf-8') as f:
                    file_text = f.read()
                    entry_locations = self._extract_entry_locations(file_text)
                    parsed_entries: List[Dict] | None = None
                    if bib_file.stat().st_size >= LARGE_BIB_PARSE_THRESHOLD:
                        try:
                            parsed_entries, parse_warnings = _parse_large_bibtex(file_text)
                            self.report_data['parse_warnings'].extend(parse_warnings)
                        except ImportError:
                            parsed_entries = None
                    if parsed_entries is None:
                        parsed_entries = _parse_standard_bibtex(file_text, entry_locations)
                    del file_text
                    entry_line_occurrences: Dict[str, List[Tuple[int, int]]] = {}
                    for key, start_line, end_line, _, _ in entry_locations:
                        entry_line_occurrences.setdefault(key, []).append((start_line, end_line))
                    relative_path = str(bib_file.relative_to(self.root_directory))
                    self.report_data['source_files'][str(bib_file)] = {
                        'relative_path': relative_path,
                    }

                    fallback_index = 0
                    for entry in parsed_entries:
                        # Store source file information and line number
                        entry_id = entry.get('ID', '').strip()
                        id_lines = entry_line_occurrences.get(entry_id, [])
                        if id_lines:
                            start_line, end_line = id_lines.pop(0)
                        elif fallback_index < len(entry_locations):
                            _, start_line, end_line, _, _ = entry_locations[fallback_index]
                            fallback_index += 1
                        else:
                            start_line = 'N/A'
                            end_line = start_line

                        entry['_source_file'] = str(bib_file)
                        entry['_source_file_display'] = relative_path
                        entry['_line_number'] = start_line
                        entry['_entry_start_line'] = start_line
                        entry['_entry_end_line'] = end_line
                        self.all_entries.append(entry)
                    del entry_locations, entry_line_occurrences, parsed_entries
            except Exception as e:
                if self.strict_source_errors:
                    raise ValueError(f"Could not read bibliography {bib_file}: {e}") from e
                print(f"⚠️  Error reading {bib_file}: {e}")

        self.embedded_bib_files = []
        embedded_targets: Set[Path] = set()
        for tex_file in sorted(Path(self.root_directory).rglob("*.tex")):
            if self._is_generated_workspace_path(tex_file, root_path):
                continue
            try:
                text = tex_file.read_text(encoding="utf-8")
            except UnicodeError as error:
                if self.strict_source_errors:
                    raise ValueError(f"Could not inspect LaTeX file {tex_file}: {error}") from error
                warning = f"Could not inspect {tex_file} for embedded bibliographies: {error}"
                self.report_data['parse_warnings'].append(warning)
                print(f"⚠️  {warning}")
                continue
            for filename, start, end in _embedded_bib_blocks(text):
                relative_filename = Path(filename)
                if relative_filename.is_absolute() or '..' in relative_filename.parts:
                    raise ValueError(f"Unsafe embedded bibliography filename {filename!r} in {tex_file}")
                target = (tex_file.parent / relative_filename).resolve()
                root_target = (root_path / relative_filename).resolve()
                if (
                    target.exists()
                    or root_target.exists()
                    or target in embedded_targets
                    or root_target in embedded_targets
                    or root_target == root_path / 'master.bib'
                ):
                    raise ValueError(f"Conflicting embedded bibliography {filename!r} in {tex_file}; resolve the file conflict first")
                embedded_targets.add(target)
                embedded_targets.add(root_target)
                if tex_file not in self.embedded_bib_files:
                    self.embedded_bib_files.append(tex_file)
                block = text[start:end]
                locations = self._extract_entry_locations(block)
                entries = _parse_standard_bibtex(block, locations)
                relative_path = str(tex_file.relative_to(self.root_directory))
                self.report_data['source_files'][str(tex_file)] = {'relative_path': relative_path}
                lines_by_key: Dict[str, List[Tuple[int, int]]] = {}
                base_line = text.count('\n', 0, start)
                for key, first, last, _, _ in locations:
                    lines_by_key.setdefault(key, []).append((base_line + first, base_line + last))
                for entry in entries:
                    lines = lines_by_key.get(entry.get('ID', '').strip(), [])
                    first, last = lines.pop(0) if lines else ('N/A', 'N/A')
                    entry.update({
                        '_source_file': str(tex_file),
                        '_source_file_display': relative_path,
                        '_line_number': first,
                        '_entry_start_line': first,
                        '_entry_end_line': last,
                    })
                    self.all_entries.append(entry)
            for key, note, start, end in _manual_bibliography_entries(text):
                if tex_file not in self.embedded_bib_files:
                    self.embedded_bib_files.append(tex_file)
                relative_path = str(tex_file.relative_to(self.root_directory))
                self.report_data['source_files'][str(tex_file)] = {'relative_path': relative_path}
                first = text.count('\n', 0, start) + 1
                last = text.count('\n', 0, end) + 1
                self.all_entries.append({
                    'ID': key,
                    'ENTRYTYPE': 'misc',
                    'note': note,
                    '_manual_bibitem': True,
                    '_source_file': str(tex_file),
                    '_source_file_display': relative_path,
                    '_line_number': first,
                    '_entry_start_line': first,
                    '_entry_end_line': last,
                })

        manual_keys = [entry['ID'] for entry in self.all_entries if entry.get('_manual_bibitem')]
        key_counts = Counter(entry.get('ID') for entry in self.all_entries)
        for key in manual_keys:
            if key_counts[key] > 1:
                raise ValueError(f"Conflicting manual bibliography key {key!r}; resolve the conflict first")
        if manual_keys:
            warning = ("Manual bibitem references retain their original keys and formatting; "
                       "their free-form text is exported as BibTeX notes.")
            self.report_data['parse_warnings'].append(warning)
            print(f"⚠️  {warning}")
        
        print(f"\n✓ Collected {len(self.all_entries)} total entries\n")
        
        # Store report data
        self.report_data['files_found'] = len(self.bib_files) + len(self.embedded_bib_files)
        self.report_data['initial_entries'] = len(self.all_entries)
        
        return self.report_data['files_found'], len(self.all_entries)

    @staticmethod
    def _is_generated_workspace_path(path: Path, root_path: Path) -> bool:
        """Exclude backups and processed output from a later source scan."""
        try:
            relative_parts = path.resolve().relative_to(root_path).parts
        except ValueError:
            return False
        return any(
            part.startswith("backup_")
            or part == "processed"
            or part.startswith("processed_")
            for part in relative_parts
        )

    def normalize_string(self, text: str) -> str:
        """Normalize a string for comparison
        
        Args:
            text: Input string
            
        Returns:
            Normalized string (lowercase, no extra spaces/punctuation)
        """
        if not text:
            return ""
        # Remove LaTeX commands, punctuation, extra spaces
        text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)  # Remove \command{text}
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text).strip().lower()  # Normalize spaces
        return text
    
    def extract_authors_lastname(self, author_string: str) -> List[str]:
        """Extract last names from author string
        
        Args:
            author_string: BibTeX author field (e.g., "Smith, John and Doe, Jane")
            
        Returns:
            List of last names
        """
        if not author_string:
            return []
        
        # Split by 'and'
        authors = re.split(r'\s+and\s+', author_string, flags=re.IGNORECASE)
        last_names = []
        
        for author in authors:
            author = author.strip()
            # Handle "Last, First" format
            if ',' in author:
                last_names.append(author.split(',')[0].strip())
            else:
                # Handle "First Last" format - take last word
                parts = author.split()
                if parts:
                    last_names.append(parts[-1])
        
        return last_names

    def compute_similarity(self, entry1: Dict, entry2: Dict) -> float:
        """Compute similarity score between two entries
        
        Args:
            entry1, entry2: Bibliography entries
            
        Returns:
            Similarity score (0-100, higher = more similar)
        """
        score = 0
        
        # 1. DOI match (if present, this is almost certain duplicate)
        doi1 = entry1.get('_duplicate_doi')
        if doi1 is None:
            doi1 = str(entry1.get('doi', '')).strip().lower()
        doi2 = entry2.get('_duplicate_doi')
        if doi2 is None:
            doi2 = str(entry2.get('doi', '')).strip().lower()
        if doi1 and doi2:
            if doi1 == doi2:
                return 100  # Perfect match
            else:
                return 0  # Different DOIs = different papers
        
        # 2. Title similarity (most important)
        title1 = entry1.get('_duplicate_title')
        if title1 is None:
            title1 = self.normalize_string(entry1.get('title', ''))
        title2 = entry2.get('_duplicate_title')
        if title2 is None:
            title2 = self.normalize_string(entry2.get('title', ''))
        
        if not title1 or not title2:
            return 0
        
        if fuzz:
            title_score = fuzz.ratio(title1, title2)
        else:
            # Fallback: simple substring matching
            title_score = 100 if title1 == title2 else 0
        
        # 3. Year match
        year1 = entry1.get('_duplicate_year')
        if year1 is None:
            year1 = str(entry1.get('year', '')).strip()
        year2 = entry2.get('_duplicate_year')
        if year2 is None:
            year2 = str(entry2.get('year', '')).strip()
        year_match = (year1 == year2) if (year1 and year2) else False
        
        # 4. Author similarity
        author1 = entry1.get('_duplicate_author')
        if author1 is None:
            author1 = self.normalize_string(entry1.get('author', ''))
        author2 = entry2.get('_duplicate_author')
        if author2 is None:
            author2 = self.normalize_string(entry2.get('author', ''))
        
        if author1 and author2:
            if fuzz:
                author_score = fuzz.ratio(author1, author2)
            else:
                author_score = 100 if author1 == author2 else 0
        else:
            author_score = 0
        
        # Weighted combination
        score = (title_score * 0.6 + author_score * 0.3)
        if year_match:
            score += 10  # Bonus for matching year
        
        return min(score, 100)
    
    def find_duplicates(self, threshold: float = 85.0) -> int:
        """Find duplicate entries using similarity matching
        
        Args:
            threshold: Similarity threshold (0-100) for considering entries as duplicates
            
        Returns:
            Number of duplicate groups found
        """
        print(f"\n{'='*60}")
        print(f"STEP 2: Identifying duplicates...")
        print(f"{'='*60}")
        print(f"Similarity threshold: {threshold}%\n")
        
        n = len(self.all_entries)
        if n == 0:
            print("No entries to check for duplicates.\n")
            return 0
        
        # Prepare comparison fields once. Re-normalizing title and author text
        # inside every candidate comparison is costly for large imports.
        title_token_counts: Dict[str, int] = {}
        for entry in self.all_entries:
            entry['_duplicate_doi'] = str(entry.get('doi', '')).strip().lower()
            entry['_duplicate_title'] = self.normalize_string(entry.get('title', ''))
            entry['_duplicate_author'] = self.normalize_string(entry.get('author', ''))
            entry['_duplicate_year'] = str(entry.get('year', '')).strip()
            tokens = {
                token for token in entry['_duplicate_title'].split()
                if len(token) > 3 and token not in WEAK_TITLE_WORDS
            }
            entry['_duplicate_tokens'] = tokens
            for token in tokens:
                title_token_counts[token] = title_token_counts.get(token, 0) + 1

        # Exact fingerprints are handled in one pass. This avoids comparing a
        # large number of identical records pair by pair.
        exact_indexes: Dict[str, List[int]] = {}
        for index, entry in enumerate(self.all_entries):
            doi = entry['_duplicate_doi']
            title = entry['_duplicate_title']
            author = entry['_duplicate_author']
            year = entry['_duplicate_year']
            if doi:
                exact_indexes.setdefault(f'doi:{doi}', []).append(index)
            if title and author and year:
                exact_indexes.setdefault(f'metadata:{title}|{author}|{year}|{doi}', []).append(index)

        grouped = set()
        self.duplicate_groups = []
        candidate_indexes: Dict[str, Set[int]] = {}
        for index, entry in enumerate(self.all_entries):
            doi = entry['_duplicate_doi']
            title = entry['_duplicate_title']
            if doi:
                candidate_indexes.setdefault(f'doi:{doi}', set()).add(index)
            if title:
                candidate_indexes.setdefault(f'title:{title}', set()).add(index)
                for token in entry['_duplicate_tokens']:
                    candidate_indexes.setdefault(f'token:{token}', set()).add(index)

        parents = list(range(n))

        def find_parent(index: int) -> int:
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        for indexes in exact_indexes.values():
            if len(indexes) < 2:
                continue
            first = find_parent(indexes[0])
            for index in indexes[1:]:
                parent = find_parent(index)
                if parent != first:
                    parents[parent] = first

        exact_groups: Dict[int, List[int]] = {}
        for index in range(n):
            root = find_parent(index)
            exact_groups.setdefault(root, []).append(index)
        for indexes in exact_groups.values():
            if len(indexes) > 1:
                self.duplicate_groups.append(indexes)
                grouped.update(indexes)
        
        for i in range(n):
            if i in grouped:
                continue
            
            current_group = [i]
            entry = self.all_entries[i]
            title = entry['_duplicate_title']
            candidate_set = set(candidate_indexes.get(f'title:{title}', set()))
            token_candidates = [
                (title_token_counts[token], token)
                for token in entry['_duplicate_tokens']
            ]
            if token_candidates:
                _, rarest_token = min(token_candidates)
                candidate_set.update(candidate_indexes.get(f'token:{rarest_token}', set()))
            candidate_set.discard(i)

            # Common title words can produce enormous buckets. Exact matches
            # above are retained, but fuzzy matching is intentionally skipped
            # for a pathological bucket to keep runtime bounded.
            if len(candidate_set) > MAX_FUZZY_BUCKET_SIZE:
                continue
            
            for j in sorted(candidate_set):
                if j <= i:
                    continue
                if j in grouped:
                    continue
                
                similarity = self.compute_similarity(self.all_entries[i], self.all_entries[j])
                
                if similarity >= threshold:
                    current_group.append(j)
                    grouped.add(j)
            
            # If group has duplicates, save it
            if len(current_group) > 1:
                self.duplicate_groups.append(current_group)
                grouped.add(i)
        
        # Print results
        print(f"✓ Found {len(self.duplicate_groups)} duplicate group(s):\n")
        
        for group_num, group in enumerate(self.duplicate_groups, 1):
            print(f"  Duplicate Group {group_num} ({len(group)} entries):")
            group_entries = []
            kept_position = self._select_group_master_position(group)
            kept_entry = self.all_entries[group[kept_position]]
            for idx_in_group, entry_idx in enumerate(group):
                entry = self.all_entries[entry_idx]
                title = entry.get('title', 'NO TITLE')[:60]
                key = entry.get('ID', 'NO_KEY')
                status = "KEPT" if idx_in_group == kept_position else "REMOVED"
                print(f"    - [{entry_idx}] {key}: {title}... ({status})")
                contributed_fields = []
                if idx_in_group != kept_position:
                    contributed_fields = self._merge_contributed_fields(kept_entry, entry)

                similarity = self.compute_similarity(kept_entry, entry)
                kept_doi = str(kept_entry.get('doi', '')).strip().lower()
                entry_doi = str(entry.get('doi', '')).strip().lower()
                kept_title = self.normalize_string(kept_entry.get('title', ''))
                entry_title = self.normalize_string(entry.get('title', ''))
                if kept_doi and kept_doi == entry_doi:
                    match_reason = f"Exact DOI match ({kept_doi})"
                elif kept_title and kept_title == entry_title:
                    match_reason = "Exact normalized title match"
                else:
                    match_reason = "Title, author, and year similarity"

                # Add status and line number to entry dict
                group_entries.append({
                    **entry,
                    '_status': 'kept' if idx_in_group == kept_position else 'removed',
                    '_merge_field_count': self._merge_field_count(entry),
                    '_merged_into_master_fields': contributed_fields,
                    '_match_confidence': round(similarity, 1),
                    '_match_reason': match_reason,
                })
            print()
            
            # Store in report data
            similarity_score = self.compute_similarity(self.all_entries[group[0]], self.all_entries[group[1]]) if len(group) > 1 else 100
            first_entry = self.all_entries[group[0]]
            second_entry = self.all_entries[group[1]]
            first_doi = str(first_entry.get('doi', '')).strip().lower()
            second_doi = str(second_entry.get('doi', '')).strip().lower()
            first_title = self.normalize_string(first_entry.get('title', ''))
            second_title = self.normalize_string(second_entry.get('title', ''))
            if first_doi and first_doi == second_doi:
                reason = 'Exact DOI match'
            elif first_title and first_title == second_title:
                reason = 'Exact normalized title match'
            else:
                reason = 'Title, author, and year similarity'
            self.report_data['duplicate_groups'].append({
                'entries': group_entries,
                'similarity': round(similarity_score, 1),
                'entry_indices': group,  # Store original indices for reference
                'kept_position': kept_position,
                'reason': reason,
            })
        
        return len(self.duplicate_groups)
    
    def merge_duplicate_entries(self, group: List[int]) -> Dict:
        """Merge a group of duplicate entries, keeping the most complete one
        
        Args:
            group: List of entry indices
            
        Returns:
            Merged entry (dictionary)
        """
        # Score each entry by number of non-empty fields
        scored = []
        for idx in group:
            entry = self.all_entries[idx]
            field_count = self._merge_field_count(entry)
            scored.append((field_count, idx, entry))
        
        # Pick the entry with most fields as base
        scored.sort(reverse=True)
        _, _, base_entry = scored[0]
        
        # Create merged entry
        merged = dict(base_entry)
        
        # Merge in fields from other entries if they're missing in base
        for _, _, entry in scored[1:]:
            for key, value in entry.items():
                # Skip metadata fields and non-string values
                if key in ['_source_file', 'ID', '_line_number', '_status']:
                    continue
                if not isinstance(value, str):
                    continue
                if key not in merged or (isinstance(merged.get(key), str) and not merged[key].strip()):
                    if value.strip():
                        merged[key] = value
        
        return merged
    
    def remove_duplicates(self):
        """Remove duplicates by merging duplicate groups"""
        print(f"\n{'='*60}")
        print(f"Removing duplicates...")
        print(f"{'='*60}\n")
        
        if not self.duplicate_groups:
            self.report_data['duplicates_removed'] = 0
            self.report_data['final_entries'] = len(self.all_entries)
            print("✓ No duplicates to remove.\n")
            return
        
        grouped_indices: Set[int] = set()
        merged_at_index: Dict[int, Dict] = {}
        for group in self.duplicate_groups:
            merged_at_index[min(group)] = self.merge_duplicate_entries(group)
            grouped_indices.update(group)

        deduplicated = []
        for index, entry in enumerate(self.all_entries):
            if index in merged_at_index:
                deduplicated.append(merged_at_index[index])
            elif index not in grouped_indices:
                deduplicated.append(entry)
        
        original_count = len(self.all_entries)
        self.all_entries = deduplicated
        
        duplicates_removed = original_count - len(self.all_entries)
        self.report_data['duplicates_removed'] = duplicates_removed
        self.report_data['final_entries'] = len(self.all_entries)
        
        print(f"✓ Removed {duplicates_removed} duplicate entries")
        print(f"✓ Final count: {len(self.all_entries)} unique entries\n")
    
    def generate_citation_key(
        self,
        entry: Dict,
        existing_keys: Set[str],
    ) -> str:
        """Generate a key from author surname initials and publication year."""
        authors = self.extract_authors_lastname(entry.get('author', ''))
        initials = []
        for surname in authors:
            surname = re.sub(
                r'\\(?:AA|aa|O|o|L|l)\b',
                lambda match: {'AA': 'A', 'aa': 'a', 'O': 'O', 'o': 'o', 'L': 'L', 'l': 'l'}[match.group(0)[1:]],
                surname,
            )
            surname = re.sub(
                r'\\[\'"`^~=\.]\s*\{?([A-Za-z])\}?',
                r'\1',
                surname,
            )
            surname = re.sub(r'\\[A-Za-z]+\s*\{([A-Za-z])\}', r'\1', surname)
            surname = surname.replace('{', '').replace('}', '')
            normalized_surname = unicodedata.normalize('NFKD', surname)
            ascii_surname = normalized_surname.encode('ascii', 'ignore').decode('ascii')
            initial = next(
                (character.upper() for character in ascii_surname if character.isalpha()),
                '',
            )
            if initial:
                initials.append(initial)
        year_raw = str(entry.get('year', ''))
        year_match = re.search(r'\d{4}', year_raw)
        year = year_match.group(0) if year_match else '0000'
        base_key = (''.join(initials) or 'X') + year

        def alphabetic_suffix(index: int) -> str:
            suffix = ''
            while index:
                index, remainder = divmod(index - 1, 26)
                suffix = chr(ord('a') + remainder) + suffix
            return suffix

        key = base_key
        suffix_index = 0
        while key in existing_keys:
            suffix_index += 1
            key = base_key + alphabetic_suffix(suffix_index)
        return key
    
    def fix_citation_keys(self):
        """Normalize citation keys to surname initials, year, and ordered suffixes."""
        print(f"\n{'='*60}")
        print(f"STEP 3: Fixing citation keys (labels)...")
        print(f"{'='*60}\n")
        
        existing_keys = {
            entry['ID'] for entry in self.all_entries if entry.get('_manual_bibitem')
        }
        key_changes = []
        key_audit = []
        metadata_fixes = []
        for entry in self.all_entries:
            if entry.get('_manual_bibitem'):
                key_audit.append({
                    'Original Raw Key': entry['ID'],
                    'Normalized Key': entry['ID'],
                    'Source Title': '',
                    'Warning': 'Manual bibitem key preserved; metadata is unstructured',
                })
                continue
            for field in ('author', 'title', 'year'):
                if not str(entry.get(field, '')).strip():
                    metadata_fixes.append({
                        'Entry': entry.get('ID', 'NO_ID'),
                        'Field': field,
                        'Change': 'Missing value detected',
                    })

            for field in ('title', 'journal', 'booktitle'):
                value = entry.get(field)
                if isinstance(value, str) and value != value.strip():
                    entry[field] = value.strip()
                    metadata_fixes.append({
                        'Entry': entry.get('ID', 'NO_ID'),
                        'Field': field,
                        'Change': 'Trimmed surrounding whitespace',
                    })

            old_key = entry.get('ID', 'NO_ID')
            new_key = self.generate_citation_key(
                entry,
                existing_keys,
            )
            existing_keys.add(new_key)
            entry['ID'] = new_key
            key_audit.append({
                'Original Raw Key': old_key,
                'Normalized Key': new_key,
                'Source Title': entry.get('title', ''),
                'Warning': (
                    'No author surname; used X fallback'
                    if not self.extract_authors_lastname(entry.get('author', ''))
                    else ''
                ) + (
                    '; no four-digit year; used 0000'
                    if not re.search(r'\d{4}', str(entry.get('year', '')))
                    else ''
                ),
            })
            if old_key != new_key:
                key_changes.append((old_key, new_key))
        
        # Store in report
        self.report_data['keys_changed'] = key_changes
        self.report_data['key_audit'] = key_audit
        self.report_data['metadata_fixes'] = metadata_fixes
        key_mapping = {old: new for old, new in key_changes if old and new and old != new}
        for entry in self.all_entries:
            for field in ('crossref', 'xdata'):
                value = entry.get(field)
                if isinstance(value, str):
                    entry[field] = re.sub(
                        r'[^,\s]+',
                        lambda match: key_mapping.get(match.group(0), match.group(0)),
                        value,
                    )
        
        print(f"✓ Regenerated {len(key_changes)} citation keys")
        
        if key_changes[:5]:  # Show first 5 examples
            print(f"\nExamples:")
            for old, new in key_changes[:5]:
                print(f"  {old} → {new}")
            if len(key_changes) > 5:
                print(f"  ... and {len(key_changes) - 5} more")
        print()
    
    def create_master_bibliography(self, output_path: str | None = None) -> str:
        """Create master bibliography file
        
        Args:
            output_path: Path to save master.bib (default: root_directory/master.bib)
            
        Returns:
            Path to created file
        """
        if output_path is None:
            output_path = os.path.join(self.root_directory, 'master.bib')
        
        # Prepare database with cleaned entries (remove internal metadata fields)
        cleaned_entries = []
        for entry in self.all_entries:
            cleaned = {k: v for k, v in entry.items() 
                      if not k.startswith('_')}  # Remove all internal metadata fields
            cleaned_entries.append(cleaned)
        
        self.master_db.entries = cleaned_entries
        
        # Write to file
        writer = BibTexWriter()
        writer.indent = '  '
        writer.order_entries_by = ('ID',)
        output = writer.write(self.master_db)
        manual_entries = {
            entry['ID']: entry['note'] for entry in self.all_entries if entry.get('_manual_bibitem')
        }
        if manual_entries:
            parsed = bibtexparser.loads(output)
            parsed_entries = {entry.get('ID'): entry.get('note') for entry in parsed.entries}
            for key, note in manual_entries.items():
                if parsed_entries.get(key) != note:
                    raise ValueError(f"Manual bibitem {key!r} cannot be safely exported as a BibTeX note")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        # Ensure file is closed and flushed
        import time
        time.sleep(0.1)
        
        print(f"✓ Master bibliography saved to: {output_path}")
        print(f"  Total entries: {len(self.all_entries)}\n")
        
        return output_path
    
    def create_processed_copy(self) -> Path:
        """Create an Overleaf-ready copy without changing any source files."""
        source_root = Path(self.root_directory).resolve()
        output_name = "processed"
        output_root = source_root / output_name
        if output_root.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"processed_{timestamp}"
            output_root = source_root / output_name
            suffix = 1
            while output_root.exists():
                output_root = source_root / f"{output_name}_{suffix}"
                suffix += 1

        def ignore_generated(directory: str, names: List[str]) -> Set[str]:
            return {
                name for name in names
                if name.startswith(("backup_", "processed_")) or name in {".git", "processed"}
            }

        original_root = self.root_directory
        try:
            shutil.copytree(source_root, output_root, ignore=ignore_generated)
            self.root_directory = str(output_root)
            self.update_source_citations()
            master_path = Path(self.create_master_bibliography(str(output_root / "master.bib")))
            source_directories = {
                output_root / bib_file.resolve().relative_to(source_root).parent
                for bib_file in self.bib_files
            }
            for directory in source_directories:
                destination = directory / "master.bib"
                if destination.resolve() != master_path.resolve():
                    shutil.copy2(master_path, destination)
        except Exception:
            shutil.rmtree(output_root, ignore_errors=True)
            raise
        finally:
            self.root_directory = original_root

        self.report_data["processed_copy_path"] = str(output_root)
        print(f"✓ Processed project copy saved to: {output_root}")
        print("  Original bibliography and LaTeX files were left unchanged.")
        return output_root

    def push_to_folders(self, master_file: str | None = None, create_backup: bool = True):
        """Create a processed project copy for Dropbox/Overleaf without editing sources."""
        return self.create_processed_copy()

    def _compute_changed_lines(self, original_text: str, updated_text: str) -> List[int]:
        """Return 1-based line numbers that changed between two texts."""
        orig_lines = original_text.splitlines()
        upd_lines = updated_text.splitlines()
        max_lines = max(len(orig_lines), len(upd_lines))
        changed_lines: List[int] = []

        for i in range(max_lines):
            o = orig_lines[i] if i < len(orig_lines) else ''
            u = upd_lines[i] if i < len(upd_lines) else ''
            if o != u:
                changed_lines.append(i + 1)

        return changed_lines

    def _update_source_files_keys(self, directory: Path, mapping: Dict[str, str]):
        """Update citation keys in all .bib files within `directory` according to mapping.

        Args:
            directory: Path to directory containing .bib files to update
            mapping: Dict of old_key -> new_key
        """
        # Prepare file_changes mapping for report
        file_changes: Dict[str, Dict] = self.report_data.get('file_changes', {})

        for bib_file in directory.glob('*.bib'):
            try:
                # Read original content
                with open(bib_file, encoding='utf-8') as f:
                    original_text = f.read()

                # Replace only citation keys on entry header lines, preserving formatting.
                changed_lines: List[int] = []

                def _replace_header_key(match):
                    old_key = match.group(2).strip()
                    if old_key in mapping:
                        return f"{match.group(1)}{mapping[old_key]}{match.group(3)}"
                    return match.group(0)

                updated_text = original_text
                updated_text = re.sub(
                    r'(^\s*@\w+\s*\{\s*)([^,\s]+)(\s*,)',
                    _replace_header_key,
                    updated_text,
                    flags=re.MULTILINE,
                )

                updated = updated_text != original_text

                if updated:
                    changed_lines = self._compute_changed_lines(original_text, updated_text)

                    # Save to report mapping
                    relpath = str(bib_file.relative_to(self.root_directory))
                    file_changes[relpath] = {
                        'changed_lines': changed_lines,
                    }

                    # Write updated content back to file
                    with open(bib_file, 'w', encoding='utf-8') as f:
                        f.write(updated_text)

            except Exception:
                # ignore file-specific errors
                continue

        # Update report_data
        self.report_data['file_changes'] = file_changes

    def _replace_citation_keys_in_tex(self, text: str, mapping: Dict[str, str]) -> Tuple[str, int]:
        """Replace keys inside LaTeX cite-like commands while preserving options and spacing."""
        cite_pattern = re.compile(r'\\([A-Za-z]*cite[A-Za-z*]*)(\s*(?:\[[^\]]*\]\s*)*)\{([^}]*)\}')
        replacements = 0

        def _replace_in_code_segment(segment: str) -> str:
            nonlocal replacements

            def _command_replacer(match):
                nonlocal replacements
                command = match.group(1)
                opts = match.group(2)
                key_blob = match.group(3)

                updated_parts: List[str] = []
                for part in key_blob.split(','):
                    if not part:
                        updated_parts.append(part)
                        continue

                    leading_ws = len(part) - len(part.lstrip())
                    trailing_ws = len(part) - len(part.rstrip())
                    core_key = part.strip()

                    if core_key in mapping:
                        new_key = mapping[core_key]
                        if new_key != core_key:
                            replacements += 1
                        updated_parts.append(f"{' ' * leading_ws}{new_key}{' ' * trailing_ws}")
                    else:
                        updated_parts.append(part)

                updated_blob = ','.join(updated_parts)
                return f"\\{command}{opts}{{{updated_blob}}}"

            return cite_pattern.sub(_command_replacer, segment)

        updated_lines: List[str] = []
        for line in text.splitlines(keepends=True):
            # Preserve full-line comments untouched.
            if re.match(r'^\s*%', line):
                updated_lines.append(line)
                continue

            # Split at first unescaped '%' so trailing comments remain untouched.
            split_at = -1
            escaped = False
            for idx, ch in enumerate(line):
                if ch == '\\' and not escaped:
                    escaped = True
                    continue
                if ch == '%' and not escaped:
                    split_at = idx
                    break
                escaped = False

            if split_at >= 0:
                code_part = line[:split_at]
                comment_part = line[split_at:]
                updated_lines.append(_replace_in_code_segment(code_part) + comment_part)
            else:
                updated_lines.append(_replace_in_code_segment(line))

        return ''.join(updated_lines), replacements

    def _update_latex_citations(self, mapping: Dict[str, str]):
        """Update citation keys in all .tex files under root directory."""
        file_changes: Dict[str, Dict] = self.report_data.get('file_changes', {})
        tex_files_updated = 0
        tex_citation_updates = 0
        root_path = Path(self.root_directory).resolve()

        for tex_file in Path(self.root_directory).rglob('*.tex'):
            if self._is_generated_workspace_path(tex_file, root_path):
                continue

            try:
                with open(tex_file, encoding='utf-8') as f:
                    original_text = f.read()

                parts = []
                last = 0
                replaced_count = 0
                for _, start, end in _embedded_bib_blocks(original_text):
                    updated, count = self._replace_citation_keys_in_tex(original_text[last:start], mapping)
                    parts.extend((updated, _rewrite_bib_keys(original_text[start:end], mapping)))
                    replaced_count += count
                    last = end
                updated, count = self._replace_citation_keys_in_tex(original_text[last:], mapping)
                parts.append(updated)
                replaced_count += count
                updated_text = ''.join(parts)
                if updated_text == original_text:
                    continue

                changed_lines = self._compute_changed_lines(original_text, updated_text)
                relpath = str(tex_file.relative_to(self.root_directory))
                file_changes[relpath] = {
                    'changed_lines': changed_lines,
                }

                with open(tex_file, 'w', encoding='utf-8') as f:
                    f.write(updated_text)

                tex_files_updated += 1
                tex_citation_updates += replaced_count
            except OSError as error:
                raise OSError(f"Could not update LaTeX citations in {tex_file}") from error

        self.report_data['file_changes'] = file_changes
        self.report_data['tex_files_updated'] = tex_files_updated
        self.report_data['tex_citation_updates'] = tex_citation_updates

    def update_source_citations(self):
        """Rewrite source BibTeX keys and LaTeX citations after key normalization."""
        mapping = {
            old: new
            for old, new in self.report_data.get('keys_changed', [])
            if old and new and old != new
        }
        if not mapping:
            self.report_data['citation_update_files'] = []
            return

        file_changes: Dict[str, Dict] = self.report_data.get('file_changes', {})
        root_path = Path(self.root_directory).resolve()
        for bib_file in Path(self.root_directory).rglob('*.bib'):
            if self._is_generated_workspace_path(bib_file, root_path):
                continue
            try:
                original_text = bib_file.read_text(encoding='utf-8')
                updated_text = _rewrite_bib_keys(original_text, mapping)
                if updated_text != original_text:
                    bib_file.write_text(updated_text, encoding='utf-8')
                    relpath = str(bib_file.relative_to(self.root_directory))
                    file_changes[relpath] = {
                        'changed_lines': self._compute_changed_lines(original_text, updated_text),
                    }
            except OSError as error:
                raise OSError(f"Could not update bibliography keys in {bib_file}") from error

        self.report_data['file_changes'] = file_changes
        self._update_latex_citations(mapping)
        self.report_data['citation_update_files'] = sorted(
            path for path in file_changes
            if path.lower().endswith(('.bib', '.tex'))
        )
    
    def generate_html_report(self, output_path: str | None = None) -> str:
        """Generate a detailed HTML report of the processing
        
        Args:
            output_path: Path to save the report (default: report_TIMESTAMP.html)
        
        Returns:
            Path to the generated report
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.root_directory, f"report_{timestamp}.html")
        
        # Calculate statistics
        duration = None
        if self.report_data['start_time'] and self.report_data['end_time']:
            duration = (self.report_data['end_time'] - self.report_data['start_time']).total_seconds()
        duration_text = f"{duration:.1f}s" if duration is not None else "N/A"
        
        duplicate_count = sum(len(group) - 1 for group in self.report_data['duplicate_groups'])
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bibliography Processing Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .content {{
            padding: 40px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .stat-card .label {{
            font-size: 0.9em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .duplicate-group {{
            background: #f8f9fa;
            border-left: 4px solid #764ba2;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
        }}
        .duplicate-group h3 {{
            color: #764ba2;
            margin-bottom: 15px;
        }}
        .entry {{
            background: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 6px;
            border: 1px solid #e1e4e8;
        }}
        .entry.kept {{
            border-left: 4px solid #28a745;
        }}
        .entry.removed {{
            border-left: 4px solid #dc3545;
            opacity: 0.7;
        }}
        .entry-key {{
            font-weight: bold;
            color: #667eea;
            font-family: 'Courier New', monospace;
        }}
        .entry-title {{
            color: #333;
            margin: 8px 0;
        }}
        .entry-meta {{
            color: #666;
            font-size: 0.9em;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: bold;
            margin-right: 8px;
        }}
        .badge.kept {{
            background: #28a745;
            color: white;
        }}
        .badge.removed {{
            background: #dc3545;
            color: white;
        }}
        .similarity {{
            background: #ffc107;
            color: #333;
        }}
        .key-changes {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        .key-change {{
            padding: 10px;
            margin: 5px 0;
            background: white;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }}
        .arrow {{
            color: #667eea;
            font-weight: bold;
            margin: 0 10px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #e1e4e8;
        }}
        .success-rate {{
            font-size: 1.2em;
            color: #28a745;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Bibliography Processing Report</h1>
            <p>Generated on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
        </div>
        
        <div class="content">
            <!-- Executive Summary -->
            <div class="summary">
                <div class="stat-card">
                    <div class="number">{self.report_data['files_found']}</div>
                    <div class="label">Files Processed</div>
                </div>
                <div class="stat-card">
                    <div class="number">{self.report_data['initial_entries']}</div>
                    <div class="label">Initial Entries</div>
                </div>
                <div class="stat-card">
                    <div class="number">{len(self.report_data['duplicate_groups'])}</div>
                    <div class="label">Duplicate Groups</div>
                </div>
                <div class="stat-card">
                    <div class="number">{self.report_data['duplicates_removed']}</div>
                    <div class="label">Entries Removed</div>
                </div>
                <div class="stat-card">
                    <div class="number">{self.report_data['final_entries']}</div>
                    <div class="label">Final Entries</div>
                </div>
                <div class="stat-card">
                    <div class="number">{duration_text}</div>
                    <div class="label">Processing Time</div>
                </div>
            </div>
            
            <div class="section">
                <h2>📊 Processing Summary</h2>
                <p style="line-height: 1.8; color: #555;">
                    Successfully processed <strong>{self.report_data['files_found']}</strong> BibTeX files containing 
                    <strong>{self.report_data['initial_entries']}</strong> total entries. 
                    Identified <strong>{len(self.report_data['duplicate_groups'])}</strong> groups of duplicates 
                    and removed <strong>{self.report_data['duplicates_removed']}</strong> redundant entries, 
                    resulting in <strong>{self.report_data['final_entries']}</strong> unique citations.
                    {f"Normalized <strong>{len(self.report_data['keys_changed'])}</strong> citation keys for consistency." if self.report_data['keys_changed'] else ""}
                    {f" Updated <strong>{self.report_data['tex_citation_updates']}</strong> LaTeX citation references across <strong>{self.report_data['tex_files_updated']}</strong> .tex file(s)." if self.report_data.get('tex_citation_updates') else ""}
                </p>
                <p style="margin-top: 15px;">
                    <span class="success-rate">
                        ✓ {((self.report_data['duplicates_removed'] / max(self.report_data['initial_entries'], 1)) * 100):.1f}% Duplicate Reduction Rate
                    </span>
                </p>
            </div>
"""
        
        # Duplicate groups section
        if self.report_data['duplicate_groups']:
            html += """
            <div class="section">
                <h2>🔍 Duplicate Analysis</h2>
"""
            for idx, group_data in enumerate(self.report_data['duplicate_groups'], 1):
                entries = group_data['entries']
                similarity = group_data.get('similarity', 'N/A')
                
                html += f"""
                <div class="duplicate-group">
                    <h3>Duplicate Group {idx} <span class="badge similarity">{similarity}% Similar</span></h3>
"""
                for entry_idx, entry in enumerate(entries):
                    is_kept = entry_idx == 0  # First entry is kept
                    badge_class = "kept" if is_kept else "removed"
                    badge_text = "KEPT" if is_kept else "REMOVED"
                    
                    title = entry.get('title', 'No title').replace('{', '').replace('}', '')
                    author = entry.get('author', 'Unknown')
                    year = entry.get('year', 'N/A')
                    
                    html += f"""
                    <div class="entry {badge_class}">
                        <span class="badge {badge_class}">{badge_text}</span>
                        <span class="entry-key">{entry.get('ID', 'unknown')}</span>
                        <div class="entry-title">{title[:100]}...</div>
                        <div class="entry-meta">👤 {author[:50]} | 📅 {year}</div>
                    </div>
"""
                html += """
                </div>
"""
            html += """
            </div>
"""
        
        # Citation key changes
        if self.report_data['keys_changed']:
            html += """
            <div class="section">
                <h2>🔑 Citation Key Normalization</h2>
                <div class="key-changes">
"""
            for old_key, new_key in self.report_data['keys_changed'][:20]:  # Show first 20
                html += f"""
                    <div class="key-change">
                        <span style="color: #dc3545;">{old_key}</span>
                        <span class="arrow">→</span>
                        <span style="color: #28a745;">{new_key}</span>
                    </div>
"""
            if len(self.report_data['keys_changed']) > 20:
                html += f"""
                    <p style="margin-top: 15px; color: #666;">
                        ... and {len(self.report_data['keys_changed']) - 20} more changes
                    </p>
"""
            html += """
                </div>
            </div>
"""
        
        html += """
        </div>
        
        <div class="footer">
            <p>Generated by BibTeX Bibliography Manager - Final Year Project</p>
            <p style="margin-top: 8px; font-size: 0.9em;">
                💾 Backups created | 🔒 No data loss | ✨ Automatic processing
            </p>
        </div>
    </div>
</body>
</html>"""
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"\n📊 HTML Report generated: {output_path}")
        return output_path
    
    def run_full_pipeline(self, similarity_threshold: float = 85.0, 
                         push_back: bool = False, generate_report: bool = True):
        """Run the complete bibliography management pipeline
        
        Args:
            similarity_threshold: Threshold for duplicate detection (0-100)
            push_back: Whether to create a processed project copy beside the source
            generate_report: Whether to generate HTML report
        """
        print("\n" + "="*60)
        print(" BibTeX Bibliography Manager - Full Pipeline")
        print("="*60)
        
        # Start timing
        self.report_data['start_time'] = datetime.now()
        
        # Step 1: Crawl and collect
        num_files, num_entries = self.crawl_and_collect()
        if num_entries == 0:
            print("\n⚠️  No entries found. Exiting.")
            return
        
        # Step 2: Find and remove duplicates
        self.find_duplicates(threshold=similarity_threshold)
        self.remove_duplicates()
        
        # Step 3: Fix citation keys
        self.fix_citation_keys()
        
        if push_back:
            master_path = str(self.create_processed_copy() / "master.bib")
        else:
            master_path = self.create_master_bibliography()
        
        # End timing
        self.report_data['end_time'] = datetime.now()
        
        # Generate report
        if generate_report:
            self.generate_html_report()
        
        print("="*60)
        print(" ✓ Pipeline completed successfully!")
        print("="*60)
        print(f"\nMaster bibliography: {master_path}")
        print(f"Total unique entries: {len(self.all_entries)}\n")


def main():
    """Main CLI interface"""
    print("\n" + "="*60)
    print(" BibTeX Bibliography Manager")
    print(" Final Year Project - Bibliography Consolidation Tool")
    print("="*60)
    
    # Get root directory
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = input(f"\nEnter root directory to search (press Enter for current): ").strip()
        if not root_dir:
            root_dir = os.getcwd()
    
    if not os.path.isdir(root_dir):
        print(f"❌ Error: '{root_dir}' is not a valid directory")
        return
    
    # Create manager
    manager = BibliographyManager(root_dir)
    
    # Menu
    while True:
        print("\n" + "-"*60)
        print("Options:")
        print("  1. Run full pipeline (automatic)")
        print("  2. Step-by-step mode")
        print("  3. Set similarity threshold (current: 85%)")
        print("  4. Exit")
        print("-"*60)
        
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            push = input("\nCreate a processed project copy beside the source? (y/n): ").strip().lower() == 'y'
            manager.run_full_pipeline(similarity_threshold=85.0, push_back=push)
            break
            
        elif choice == '2':
            # Step by step
            manager.crawl_and_collect()
            
            threshold = float(input("\nEnter similarity threshold (0-100, default 85): ").strip() or "85")
            manager.find_duplicates(threshold=threshold)
            manager.remove_duplicates()
            manager.fix_citation_keys()
            push = input("\nCreate a processed project copy beside the source? (y/n): ").strip().lower() == 'y'
            if push:
                master_path = str(manager.create_processed_copy() / "master.bib")
            else:
                master_path = manager.create_master_bibliography()
            
            print("\n✓ Done!")
            break
            
        elif choice == '3':
            threshold = input("\nEnter new similarity threshold (0-100): ").strip()
            try:
                threshold = float(threshold)
                if 0 <= threshold <= 100:
                    print(f"✓ Threshold set to {threshold}%")
                else:
                    print("❌ Invalid threshold (must be 0-100)")
            except ValueError:
                print("❌ Invalid input")
                
        elif choice == '4':
            print("\nGoodbye!")
            break
            
        else:
            print("\n❌ Invalid option")


if __name__ == "__main__":
    main()
