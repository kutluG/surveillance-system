#!/usr/bin/env python3
"""
Documentation Coverage Script for Edge Service

This script analyzes the edge_service codebase to identify missing docstrings
and generate a comprehensive documentation coverage report. It follows PEP 257
standards and provides actionable feedback for improving code documentation.

Features:
    - Scans all Python files in the edge_service directory
    - Identifies public functions and classes without docstrings
    - Calculates coverage percentages for different code elements
    - Generates detailed reports with missing docstring locations
    - Supports CI/CD integration with configurable coverage thresholds
    - Provides recommendations for improving documentation quality

Usage:
    python scripts/doc_coverage_edge.py [--threshold 95] [--verbose] [--output report.json]

Exit Codes:
    0: Coverage meets or exceeds threshold
    1: Coverage below threshold or errors encountered
    2: Invalid arguments or configuration

Author: Edge AI Service Team
Version: 1.0.0
"""

import ast
import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class DocstringIssue:
    """Represents a missing or problematic docstring."""
    file_path: str
    line_number: int
    element_type: str  # 'function', 'class', 'method'
    element_name: str
    is_public: bool
    parent_class: Optional[str] = None


@dataclass
class CoverageStats:
    """Documentation coverage statistics."""
    total_elements: int
    documented_elements: int
    missing_docstrings: int
    coverage_percentage: float
    by_type: Dict[str, Dict[str, int]]


class DocstringAnalyzer(ast.NodeVisitor):
    """
    AST visitor to analyze docstring coverage in Python files.
    
    This class walks through the Abstract Syntax Tree (AST) of Python files
    to identify functions, classes, and methods, then checks for the presence
    of docstrings according to PEP 257 standards.
    """
    
    def __init__(self, file_path: str):
        """
        Initialize the analyzer for a specific file.
        
        :param file_path: Path to the Python file to analyze
        """
        self.file_path = file_path
        self.issues: List[DocstringIssue] = []
        self.stats = defaultdict(lambda: defaultdict(int))
        self.current_class = None
    
    def is_public(self, name: str) -> bool:
        """
        Determine if a function or class name is public.
        
        According to PEP 8, names starting with underscore are private.
        Special methods (dunder methods) are considered public.
        
        :param name: Function or class name to check
        :return: True if the name represents a public API element
        """
        # Special methods like __init__, __str__ are public
        if name.startswith('__') and name.endswith('__'):
            return True
        # Names starting with underscore are private
        if name.startswith('_'):
            return False
        return True
    
    def has_docstring(self, node: ast.AST) -> bool:
        """
        Check if an AST node has a docstring.
        
        A docstring is the first statement in a function, class, or module
        that is a string literal (ast.Expr containing ast.Str or ast.Constant).
        
        :param node: AST node to check (FunctionDef, ClassDef, or Module)
        :return: True if the node has a docstring
        """
        if not node.body:
            return False
        
        first_stmt = node.body[0]
        
        # Check for different AST node types representing strings
        if isinstance(first_stmt, ast.Expr):
            # Python 3.8+: ast.Constant for string literals
            if isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
                return True
            # Python 3.7 and earlier: ast.Str for string literals
            if isinstance(first_stmt.value, ast.Str):
                return True
        
        return False
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """
        Visit class definition nodes.
        
        :param node: ClassDef AST node
        """
        is_public = self.is_public(node.name)
        has_docstring = self.has_docstring(node)
        
        # Update statistics
        self.stats['class']['total'] += 1
        if is_public:
            self.stats['class']['public'] += 1
            if has_docstring:
                self.stats['class']['documented'] += 1
            else:
                # Record missing docstring
                self.issues.append(DocstringIssue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    element_type='class',
                    element_name=node.name,
                    is_public=True
                ))
        
        # Visit class methods with current class context
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        Visit function definition nodes.
        
        :param node: FunctionDef AST node
        """
        is_public = self.is_public(node.name)
        has_docstring = self.has_docstring(node)
        
        # Determine if this is a method or standalone function
        element_type = 'method' if self.current_class else 'function'
        
        # Update statistics
        self.stats[element_type]['total'] += 1
        if is_public:
            self.stats[element_type]['public'] += 1
            if has_docstring:
                self.stats[element_type]['documented'] += 1
            else:
                # Record missing docstring
                self.issues.append(DocstringIssue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    element_type=element_type,
                    element_name=node.name,
                    is_public=True,
                    parent_class=self.current_class
                ))
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """
        Visit async function definition nodes.
        
        :param node: AsyncFunctionDef AST node
        """
        # Treat async functions the same as regular functions
        self.visit_FunctionDef(node)


class DocumentationCoverageAnalyzer:
    """
    Main analyzer class for documentation coverage reporting.
    
    This class orchestrates the analysis of multiple Python files,
    aggregates results, and generates comprehensive coverage reports.
    """
    
    def __init__(self, edge_service_path: str, verbose: bool = False):
        """
        Initialize the coverage analyzer.
        
        :param edge_service_path: Path to the edge_service directory
        :param verbose: Enable verbose output for debugging
        """
        self.edge_service_path = Path(edge_service_path)
        self.verbose = verbose
        self.all_issues: List[DocstringIssue] = []
        self.file_stats: Dict[str, Dict] = {}
    
    def find_python_files(self) -> List[Path]:
        """
        Find all Python files in the edge_service directory.
        
        :return: List of Python file paths
        """
        python_files = []
        
        # Skip certain directories and files
        skip_dirs = {'__pycache__', '.git', '.pytest_cache', 'tests'}
        skip_files = {'__init__.py'}  # Often legitimately empty
        
        for file_path in self.edge_service_path.rglob('*.py'):
            # Skip files in excluded directories
            if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                continue
            
            # Skip excluded files
            if file_path.name in skip_files:
                continue
            
            python_files.append(file_path)
        
        return sorted(python_files)
    
    def analyze_file(self, file_path: Path) -> Tuple[List[DocstringIssue], Dict]:
        """
        Analyze a single Python file for docstring coverage.
        
        :param file_path: Path to the Python file
        :return: Tuple of (issues, statistics)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the file into an AST
            tree = ast.parse(content, filename=str(file_path))
            
            # Analyze the AST
            analyzer = DocstringAnalyzer(str(file_path))
            analyzer.visit(tree)
            
            return analyzer.issues, dict(analyzer.stats)
            
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return [], {}
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return [], {}
    
    def analyze_all_files(self) -> CoverageStats:
        """
        Analyze all Python files in the edge_service directory.
        
        :return: Aggregated coverage statistics
        """
        python_files = self.find_python_files()
        
        if not python_files:
            print("No Python files found in edge_service directory")
            return CoverageStats(0, 0, 0, 0.0, {})
        
        print(f"Analyzing {len(python_files)} Python files...")
        
        # Aggregate statistics
        total_stats = defaultdict(lambda: defaultdict(int))
        
        for file_path in python_files:
            if self.verbose:
                print(f"Analyzing: {file_path}")
            
            issues, file_stats = self.analyze_file(file_path)
            
            # Store per-file statistics
            self.file_stats[str(file_path)] = file_stats
            self.all_issues.extend(issues)
            
            # Aggregate statistics
            for element_type, stats in file_stats.items():
                for stat_name, count in stats.items():
                    total_stats[element_type][stat_name] += count
        
        # Calculate overall coverage
        total_public = sum(stats.get('public', 0) for stats in total_stats.values())
        total_documented = sum(stats.get('documented', 0) for stats in total_stats.values())
        
        coverage_percentage = (total_documented / total_public * 100) if total_public > 0 else 100.0
        
        return CoverageStats(
            total_elements=total_public,
            documented_elements=total_documented,
            missing_docstrings=len(self.all_issues),
            coverage_percentage=coverage_percentage,
            by_type=dict(total_stats)
        )
    
    def generate_report(self, stats: CoverageStats, output_format: str = 'text') -> str:
        """
        Generate a formatted coverage report.
        
        :param stats: Coverage statistics
        :param output_format: Output format ('text' or 'json')
        :return: Formatted report as string
        """
        if output_format == 'json':
            return self._generate_json_report(stats)
        else:
            return self._generate_text_report(stats)
    
    def _generate_text_report(self, stats: CoverageStats) -> str:
        """
        Generate a human-readable text report.
        
        :param stats: Coverage statistics
        :return: Formatted text report
        """
        report = []
        report.append("=" * 80)
        report.append("EDGE SERVICE DOCUMENTATION COVERAGE REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Overall statistics
        report.append("OVERALL STATISTICS:")
        report.append(f"  Total public elements: {stats.total_elements}")
        report.append(f"  Documented elements: {stats.documented_elements}")
        report.append(f"  Missing docstrings: {stats.missing_docstrings}")
        report.append(f"  Coverage: {stats.coverage_percentage:.1f}%")
        report.append("")
        
        # Coverage by type
        report.append("COVERAGE BY TYPE:")
        for element_type, type_stats in stats.by_type.items():
            public_count = type_stats.get('public', 0)
            documented_count = type_stats.get('documented', 0)
            if public_count > 0:
                type_coverage = (documented_count / public_count) * 100
                report.append(f"  {element_type.title()}s: {documented_count}/{public_count} ({type_coverage:.1f}%)")
        report.append("")
        
        # Missing docstrings
        if self.all_issues:
            report.append("MISSING DOCSTRINGS:")
            
            # Group by file
            issues_by_file = defaultdict(list)
            for issue in self.all_issues:
                issues_by_file[issue.file_path].append(issue)
            
            for file_path, file_issues in sorted(issues_by_file.items()):
                report.append(f"  {file_path}:")
                for issue in sorted(file_issues, key=lambda x: x.line_number):
                    location = f"line {issue.line_number}"
                    if issue.parent_class:
                        name = f"{issue.parent_class}.{issue.element_name}"
                    else:
                        name = issue.element_name
                    report.append(f"    - {issue.element_type} '{name}' ({location})")
                report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        if stats.coverage_percentage < 95:
            report.append("  - Add docstrings to all public functions and classes")
            report.append("  - Follow PEP 257 docstring conventions")
            report.append("  - Include parameter descriptions, return values, and exceptions")
        else:
            report.append("  - Excellent documentation coverage!")
            report.append("  - Consider adding more detailed examples in docstrings")
        
        return "\n".join(report)
    
    def _generate_json_report(self, stats: CoverageStats) -> str:
        """
        Generate a JSON report for CI/CD integration.
        
        :param stats: Coverage statistics
        :return: JSON-formatted report
        """
        report_data = {
            'summary': asdict(stats),
            'issues': [asdict(issue) for issue in self.all_issues],
            'file_stats': self.file_stats
        }
        
        return json.dumps(report_data, indent=2, sort_keys=True)


def main():
    """
    Main entry point for the documentation coverage script.
    """
    parser = argparse.ArgumentParser(
        description='Analyze documentation coverage for edge_service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/doc_coverage_edge.py
  python scripts/doc_coverage_edge.py --threshold 90 --verbose
  python scripts/doc_coverage_edge.py --output report.json --format json
        """
    )
    
    parser.add_argument(
        '--threshold', 
        type=float, 
        default=95.0,
        help='Coverage threshold percentage (default: 95.0)'
    )
    
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--output', 
        type=str,
        help='Output file path (default: print to stdout)'
    )
    
    parser.add_argument(
        '--format', 
        choices=['text', 'json'],
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--edge-service-path',
        type=str,
        default='edge_service',
        help='Path to edge_service directory (default: edge_service)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not os.path.exists(args.edge_service_path):
        print(f"Error: edge_service directory not found: {args.edge_service_path}")
        sys.exit(2)
    
    if not (0 <= args.threshold <= 100):
        print("Error: threshold must be between 0 and 100")
        sys.exit(2)
    
    try:
        # Analyze documentation coverage
        analyzer = DocumentationCoverageAnalyzer(args.edge_service_path, args.verbose)
        stats = analyzer.analyze_all_files()
        
        # Generate report
        report = analyzer.generate_report(stats, args.format)
        
        # Output report
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Report written to: {args.output}")
        else:
            print(report)
        
        # Check threshold and exit with appropriate code
        if stats.coverage_percentage < args.threshold:
            print(f"\nERROR: Documentation coverage ({stats.coverage_percentage:.1f}%) "
                  f"is below threshold ({args.threshold}%)")
            sys.exit(1)
        else:
            print(f"\nSUCCESS: Documentation coverage ({stats.coverage_percentage:.1f}%) "
                  f"meets threshold ({args.threshold}%)")
            sys.exit(0)
    
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
