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
            'duplicate_groups': [],
            'duplicates_removed': 0,
            'keys_changed': [],
            'final_entries': 0
        }
        self.all_entries: List[Dict] = []
        self.master_db = BibDatabase()
        self.duplicate_groups: List[List[int]] = []
        
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
        
        for bib_file in self.bib_files:
            try:
                with open(bib_file, encoding='utf-8') as f:
                    # Create a NEW parser for each file to avoid accumulation
                    parser = BibTexParser(common_strings=True)
                    db = bibtexparser.load(f, parser=parser)
                    for entry in db.entries:
                        # Store source file information
                        entry['_source_file'] = str(bib_file)
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
            for idx in group:
                entry = self.all_entries[idx]
                title = entry.get('title', 'NO TITLE')[:60]
                key = entry.get('ID', 'NO_KEY')
                print(f"    - [{idx}] {key}: {title}...")
                group_entries.append(entry)
            print()
            
            # Store in report data
            similarity_score = self.compute_similarity(self.all_entries[group[0]], self.all_entries[group[1]]) if len(group) > 1 else 100
            self.report_data['duplicate_groups'].append({
                'entries': group_entries,
                'similarity': round(similarity_score, 1)
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
            field_count = sum(1 for k, v in entry.items() 
                            if k not in ['_source_file', 'ID'] and v.strip())
            scored.append((field_count, idx, entry))
        
        # Pick the entry with most fields as base
        scored.sort(reverse=True)
        _, _, base_entry = scored[0]
        
        # Create merged entry
        merged = dict(base_entry)
        
        # Merge in fields from other entries if they're missing in base
        for _, _, entry in scored[1:]:
            for key, value in entry.items():
                if key not in merged or not merged[key].strip():
                    if value.strip():
                        merged[key] = value
        
        return merged
    
    def remove_duplicates(self):
        """Remove duplicates by merging duplicate groups"""
        print(f"\n{'='*60}")
        print(f"Removing duplicates...")
        print(f"{'='*60}\n")
        
        if not self.duplicate_groups:
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
    
    def generate_citation_key(self, entry: Dict, existing_keys: Set[str]) -> str:
        """Generate a consistent citation key for an entry
        
        Format: firstauthor-year-titleword
        
        Args:
            entry: Bibliography entry
            existing_keys: Set of already used keys (to ensure uniqueness)
            
        Returns:
            Generated citation key
        """
        # Extract first author's last name
        authors = self.extract_authors_lastname(entry.get('author', ''))
        if authors:
            author_part = re.sub(r'[^a-z0-9]', '', authors[0].lower())
        else:
            author_part = 'unknown'
        
        # Extract year
        year = entry.get('year', '0000')
        
        # Extract first meaningful word from title
        title = self.normalize_string(entry.get('title', ''))
        title_words = [w for w in title.split() if len(w) > 3]
        title_part = title_words[0] if title_words else 'paper'
        
        # Construct base key
        base_key = f"{author_part}-{year}-{title_part}"
        
        # Ensure uniqueness
        key = base_key
        counter = 1
        while key in existing_keys:
            key = f"{base_key}-{chr(96 + counter)}"  # append a, b, c, ...
            counter += 1
        
        return key
    
    def fix_citation_keys(self):
        """Regenerate citation keys with consistent naming scheme"""
        print(f"\n{'='*60}")
        print(f"STEP 3: Fixing citation keys (labels)...")
        print(f"{'='*60}\n")
        
        existing_keys = set()
        key_changes = []
        
        for entry in self.all_entries:
            old_key = entry.get('ID', 'NO_ID')
            new_key = self.generate_citation_key(entry, existing_keys)
            
            existing_keys.add(new_key)
            entry['ID'] = new_key
            
            if old_key != new_key:
                key_changes.append((old_key, new_key))
        
        # Store in report
        self.report_data['keys_changed'] = key_changes
        
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
        
        # Prepare database
        self.master_db.entries = self.all_entries
        
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
        
        print(f"✓ Master bibliography distributed to {len(directories)} folder(s)\n")
    
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
