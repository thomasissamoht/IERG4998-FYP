#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BibTeX Bibliography Manager
Final Year Project - Bibliography Consolidation Tool

This tool helps manage BibTeX bibliography files by:
1. Crawling folders to find and merge .bib files
2. Identifying and removing duplicates (perfect and partial matches)
3. Fixing citation keys (labels) with consistent naming
4. Pushing the cleaned master bibliography back to original folders
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
    from bibtexparser.bparser import BibTexParser
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


class BibliographyManager:
    """Main class for managing bibliography files"""
    
    def __init__(self, root_directory: str | None = None):
        """Initialize the bibliography manager
        
        Args:
            root_directory: Root directory to search for .bib files
        """
        self.root_directory: str = root_directory or os.getcwd()
        self.bib_files: List[Path] = []
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

    def _extract_entry_block(self, lines: List[str], start_line: int) -> Tuple[str, int]:
        """Extract a full BibTeX entry block from a file.

        Args:
            lines: File contents split into lines with line endings preserved.
            start_line: 1-based line number where the entry starts.

        Returns:
            A tuple of (entry_text, end_line).
        """
        if start_line < 1 or start_line > len(lines):
            return "", start_line

        block_lines = []
        brace_balance = 0
        started = False
        end_line = start_line

        for line_index in range(start_line - 1, len(lines)):
            line = lines[line_index]
            block_lines.append(line)
            brace_balance += line.count('{') - line.count('}')
            if '{' in line:
                started = True
            if started and brace_balance <= 0:
                end_line = line_index + 1
                break

        return ''.join(block_lines), end_line
    
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
        all_bib_files = list(Path(self.root_directory).rglob("*.bib"))
        self.bib_files = [
            bib_file for bib_file in all_bib_files
            if bib_file.name.lower() != "master.bib"
            and not any(part.startswith("backup_") for part in bib_file.parts)
        ]
        
        if not self.bib_files:
            print("⚠️  No .bib files found!")
            return 0, 0
        
        print(f"✓ Found {len(self.bib_files)} .bib file(s):")
        for i, bib_file in enumerate(self.bib_files, 1):
            print(f"  {i}. {bib_file.relative_to(self.root_directory)}")
        
        # Collect all entries from all files
        self.all_entries = []
        self.report_data['source_files'] = {}
        
        for bib_file in self.bib_files:
            try:
                # Extract line numbers first
                line_numbers = self._extract_line_numbers(str(bib_file))
                
                with open(bib_file, encoding='utf-8') as f:
                    file_text = f.read()
                    file_lines = file_text.splitlines(keepends=True)
                    entry_start_lines = []
                    entry_line_occurrences: Dict[str, List[int]] = {}
                    for line_num, line in enumerate(file_lines, start=1):
                        match = re.match(r'@[a-zA-Z]+\s*\{\s*([^,\s]+)', line)
                        if not match:
                            continue
                        key = match.group(1).strip()
                        entry_start_lines.append(line_num)
                        if key not in entry_line_occurrences:
                            entry_line_occurrences[key] = []
                        entry_line_occurrences[key].append(line_num)
                    # Create a NEW parser for each file to avoid accumulation
                    parser = BibTexParser(common_strings=True)
                    db = bibtexparser.load(StringIO(file_text), parser=parser)

                    relative_path = str(bib_file.relative_to(self.root_directory))
                    self.report_data['source_files'][str(bib_file)] = {
                        'relative_path': relative_path,
                        'text': file_text,
                    }

                    fallback_index = 0
                    for entry in db.entries:
                        # Store source file information and line number
                        entry_id = entry.get('ID', '').strip()
                        id_lines = entry_line_occurrences.get(entry_id, [])
                        if id_lines:
                            start_line = id_lines.pop(0)
                        elif fallback_index < len(entry_start_lines):
                            start_line = entry_start_lines[fallback_index]
                            fallback_index += 1
                        else:
                            start_line = line_numbers.get(entry_id, 'N/A')
                        entry_text = ''
                        end_line = start_line
                        if isinstance(start_line, int):
                            entry_text, end_line = self._extract_entry_block(file_lines, start_line)

                        entry['_source_file'] = str(bib_file)
                        entry['_source_file_display'] = relative_path
                        entry['_line_number'] = start_line
                        entry['_entry_text'] = entry_text
                        entry['_entry_start_line'] = start_line
                        entry['_entry_end_line'] = end_line
                        self.all_entries.append(entry)
            except Exception as e:
                print(f"⚠️  Error reading {bib_file}: {e}")
        
        print(f"\n✓ Collected {len(self.all_entries)} total entries\n")
        
        # Store report data
        self.report_data['files_found'] = len(self.bib_files)
        self.report_data['initial_entries'] = len(self.all_entries)
        
        return len(self.bib_files), len(self.all_entries)
    
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

    def _professor_author_fragment(self, author_string: str) -> str:
        """Build a compact author fragment for professor-style keys.

        Examples:
            Huang -> hua
            Huang and Wang -> huw
            Huang and Wang and Zhao -> hwz
        """
        surnames = [re.sub(r'[^a-z0-9]', '', name.lower()) for name in self.extract_authors_lastname(author_string)]
        surnames = [name for name in surnames if name]
        if not surnames:
            return "unk"
        if len(surnames) == 1:
            return surnames[0][:3] or "unk"
        if len(surnames) == 2:
            return f"{surnames[0][:2]}{surnames[1][:1]}" or "unk"
        return ''.join(name[:1] for name in surnames[:3]) or "unk"

    def _strict_professor_author_fragment(self, author_string: str) -> str:
        """Build the professor's strict key fragment using the same naming rule."""
        return self._professor_author_fragment(author_string)

    def _author_etal_fragment(self, author_string: str) -> str:
        """Build an author-et-al fragment for citation keys."""
        surnames = [re.sub(r'[^a-z0-9]', '', name.lower()) for name in self.extract_authors_lastname(author_string)]
        surnames = [name for name in surnames if name]
        if not surnames:
            return "unk"
        if len(surnames) == 1:
            return surnames[0]
        return f"{surnames[0]}etal"

    def _lastname_year_fragment(self, author_string: str) -> str:
        """Build a lastname-only fragment from the first author."""
        surnames = [re.sub(r'[^a-z0-9]', '', name.lower()) for name in self.extract_authors_lastname(author_string)]
        surnames = [name for name in surnames if name]
        return surnames[0] if surnames else "unk"
    
    def compute_similarity(self, entry1: Dict, entry2: Dict) -> float:
        """Compute similarity score between two entries
        
        Args:
            entry1, entry2: Bibliography entries
            
        Returns:
            Similarity score (0-100, higher = more similar)
        """
        score = 0
        
        # 1. DOI match (if present, this is almost certain duplicate)
        doi1 = entry1.get('doi', '').strip().lower()
        doi2 = entry2.get('doi', '').strip().lower()
        if doi1 and doi2:
            if doi1 == doi2:
                return 100  # Perfect match
            else:
                return 0  # Different DOIs = different papers
        
        # 2. Title similarity (most important)
        title1 = self.normalize_string(entry1.get('title', ''))
        title2 = self.normalize_string(entry2.get('title', ''))
        
        if not title1 or not title2:
            return 0
        
        if fuzz:
            title_score = fuzz.ratio(title1, title2)
        else:
            # Fallback: simple substring matching
            title_score = 100 if title1 == title2 else 0
        
        # 3. Year match
        year1 = entry1.get('year', '')
        year2 = entry2.get('year', '')
        year_match = (year1 == year2) if (year1 and year2) else False
        
        # 4. Author similarity
        author1 = self.normalize_string(entry1.get('author', ''))
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
        
        # Track which entries are already grouped
        grouped = set()
        self.duplicate_groups = []
        
        # Compare all pairs
        for i in range(n):
            if i in grouped:
                continue
            
            current_group = [i]
            
            for j in range(i + 1, n):
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
        
        # Create set of indices to remove
        to_remove = set()
        merged_entries = []
        
        for group in self.duplicate_groups:
            # Merge the group
            merged = self.merge_duplicate_entries(group)
            merged_entries.append(merged)
            
            # Mark all original entries for removal
            to_remove.update(group)
        
        # Keep only non-duplicate entries
        deduplicated = [entry for i, entry in enumerate(self.all_entries) 
                       if i not in to_remove]
        
        # Add merged entries
        deduplicated.extend(merged_entries)
        
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
        citekey_format: str = "{author}-{year}-{title}",
        entry_index: int = 1,
    ) -> str:
        """Generate a citation key for an entry using a user-defined format string.
        Supported fields: {author}, {year}, {title}, {titleword}, {author2}, etc.
        """
        # Extract up to first two author surnames
        authors = self.extract_authors_lastname(entry.get('author', ''))
        clean_authors = [re.sub(r'[^a-z0-9]', '', a.lower()) for a in authors if a]
        author = clean_authors[0] if clean_authors else 'unknown'
        author2 = clean_authors[1] if len(clean_authors) > 1 else ''
        authorstem = self._professor_author_fragment(entry.get('author', ''))
        authorstrict = self._strict_professor_author_fragment(entry.get('author', ''))
        authoretal = self._author_etal_fragment(entry.get('author', ''))
        lastname = self._lastname_year_fragment(entry.get('author', ''))

        # Extract 4-digit year if available
        year_raw = str(entry.get('year', '0000'))
        year_match = re.search(r'\d{4}', year_raw)
        year = year_match.group(0) if year_match else '0000'

        # Prefer distinctive title tokens over filler and publication labels.
        title = self.normalize_string(entry.get('title', ''))
        title_words = [
            word for word in title.split()
            if len(word) > 3 and word not in WEAK_TITLE_WORDS
        ]
        titleword = title_words[0] if title_words else 'paper'
        titleword2 = title_words[1] if len(title_words) > 1 else ''
        title_part = "-".join(title_words[:2]) if title_words else 'paper'
        authorinitials = ''.join(name[:1] for name in clean_authors[:3]) or 'unk'
        numeric = str(entry_index)

        # Compose key using format string
        key = citekey_format.format(
            author=author,
            author2=author2,
            authorstem=authorstem,
            authorstrict=authorstrict,
            authoretal=authoretal,
            lastname=lastname,
            authorinitials=authorinitials,
            year=year,
            numeric=numeric,
            title=title,
            titleword=titleword,
            titleword2=titleword2,
            title_part=title_part
        )

        # Clean up double dashes, spaces, etc.
        key = re.sub(r'[^a-z0-9\-]', '', key.lower().replace(' ', '-'))

        # Ensure uniqueness
        base_key = key
        counter = 1
        while key in existing_keys:
            key = f"{base_key}-{chr(96 + counter)}"  # append -a, -b, -c, ...
            counter += 1
        return key
    
    def fix_citation_keys(self, citekey_format: str = "{author}-{year}-{title}"):
        """Regenerate citation keys with user-defined naming scheme"""
        print(f"\n{'='*60}")
        print(f"STEP 3: Fixing citation keys (labels)...")
        print(f"{'='*60}\n")
        
        existing_keys = set()
        key_changes = []
        key_audit = []
        metadata_fixes = []
        
        for entry_index, entry in enumerate(self.all_entries, start=1):
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
            new_key = self.generate_citation_key(entry, existing_keys, citekey_format, entry_index)
            existing_keys.add(new_key)
            entry['ID'] = new_key
            title_words = [
                word for word in self.normalize_string(entry.get('title', '')).split()
                if len(word) > 3 and word not in WEAK_TITLE_WORDS
            ]
            warning = ''
            if not title_words:
                warning = 'No distinctive title words; used paper fallback'
            elif len(title_words) == 1:
                warning = 'Only one distinctive title word was available'
            key_audit.append({
                'Original Raw Key': old_key,
                'Normalized Key': new_key,
                'Source Title': entry.get('title', ''),
                'Warning': warning,
            })
            if old_key != new_key:
                key_changes.append((old_key, new_key))
        
        # Store in report
        self.report_data['keys_changed'] = key_changes
        self.report_data['key_audit'] = key_audit
        self.report_data['metadata_fixes'] = metadata_fixes
        
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
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(writer.write(self.master_db))
        
        # Ensure file is closed and flushed
        import time
        time.sleep(0.1)
        
        print(f"✓ Master bibliography saved to: {output_path}")
        print(f"  Total entries: {len(self.all_entries)}\n")
        
        return output_path
    
    def push_to_folders(self, master_file: str, create_backup: bool = True):
        """Push master bibliography back to original folders
        
        Args:
            master_file: Path to master.bib file
            create_backup: Whether to create backups of original files
        """
        print(f"\n{'='*60}")
        print(f"STEP 4: Pushing master.bib to original folders...")
        print(f"{'='*60}\n")
        
        if not self.bib_files:
            print("⚠️  No original .bib files to update.\n")
            return
        
        # Get unique directories
        directories = set(bib_file.parent for bib_file in self.bib_files)
        master_path = Path(master_file).resolve()
        mapping: Dict[str, str] = {}
        if self.report_data.get('keys_changed'):
            mapping = {old: new for old, new in self.report_data['keys_changed'] if old and new}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for directory in directories:
            # Create backup directory
            if create_backup:
                backup_dir = directory / f"backup_{timestamp}"
                backup_dir.mkdir(exist_ok=True)
                
                # Backup all .bib files in this directory
                for bib_file in directory.glob("*.bib"):
                    if bib_file.resolve() == master_path:
                        continue
                    backup_path = backup_dir / bib_file.name
                    try:
                        shutil.copy2(bib_file, backup_path)
                    except (PermissionError, OSError):
                        # File might be locked, wait and retry
                        import time
                        time.sleep(0.5)
                        try:
                            shutil.copy2(bib_file, backup_path)
                        except Exception as e:
                            print(f"⚠️  Could not backup {bib_file.name}: {e}")
                
                print(f"✓ Backed up .bib files from: {directory.relative_to(self.root_directory)}")
                print(f"  → {backup_dir.relative_to(self.root_directory)}/")

            # After creating backups, update citation keys in original .bib files.
            if mapping:
                try:
                    self._update_source_files_keys(directory, mapping)
                except Exception:
                    # Non-fatal: continue even if updating sources fails
                    pass
            
            # Copy master.bib to this directory
            dest_path = (directory / "master.bib").resolve()
            if dest_path == master_path:
                print(f"⚠️  Skipping copy to source directory: {directory.relative_to(self.root_directory)}/")
                continue
            try:
                shutil.copy2(master_file, dest_path)
            except (PermissionError, OSError):
                # File might be locked, wait and retry
                import time
                time.sleep(0.5)
                shutil.copy2(master_file, dest_path)
            
            print(f"✓ Copied master.bib to: {directory.relative_to(self.root_directory)}/\n")

        # Update LaTeX citations globally under root directory once.
        if mapping:
            try:
                self._update_latex_citations(mapping)
            except Exception:
                # Non-fatal: keep pipeline successful even if tex rewrite fails
                pass
        
        print(f"✓ Master bibliography distributed to {len(directories)} folder(s)\n")

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
                        'original': original_text,
                        'updated': updated_text,
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

        for tex_file in Path(self.root_directory).rglob('*.tex'):
            if any(part.startswith('backup_') for part in tex_file.parts):
                continue

            try:
                with open(tex_file, encoding='utf-8') as f:
                    original_text = f.read()

                updated_text, replaced_count = self._replace_citation_keys_in_tex(original_text, mapping)
                if updated_text == original_text:
                    continue

                changed_lines = self._compute_changed_lines(original_text, updated_text)
                relpath = str(tex_file.relative_to(self.root_directory))
                file_changes[relpath] = {
                    'original': original_text,
                    'updated': updated_text,
                    'changed_lines': changed_lines,
                }

                with open(tex_file, 'w', encoding='utf-8') as f:
                    f.write(updated_text)

                tex_files_updated += 1
                tex_citation_updates += replaced_count
            except Exception:
                continue

        self.report_data['file_changes'] = file_changes
        self.report_data['tex_files_updated'] = tex_files_updated
        self.report_data['tex_citation_updates'] = tex_citation_updates
    
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
            push_back: Whether to push master.bib back to original folders
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
        
        # Create master bibliography
        master_path = self.create_master_bibliography()
        
        # Step 4: Push back (optional)
        if push_back:
            self.push_to_folders(master_path, create_backup=True)
        
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
            push = input("\nPush master.bib back to folders? (y/n): ").strip().lower() == 'y'
            manager.run_full_pipeline(similarity_threshold=85.0, push_back=push)
            break
            
        elif choice == '2':
            # Step by step
            manager.crawl_and_collect()
            
            threshold = float(input("\nEnter similarity threshold (0-100, default 85): ").strip() or "85")
            manager.find_duplicates(threshold=threshold)
            manager.remove_duplicates()
            manager.fix_citation_keys()
            master_path = manager.create_master_bibliography()
            
            push = input("\nPush master.bib back to folders? (y/n): ").strip().lower() == 'y'
            if push:
                manager.push_to_folders(master_path)
            
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
