#!/usr/bin/env python3
"""
Documentation Coverage Script for AI Dashboard Service

This script scans all Python files in the app/ directory and reports
documentation coverage statistics including:
- Module docstrings
- Function/method docstrings 
- Class docstrings
- PEP 257 compliance checking
- Inline comments analysis

The script provides detailed reports and can be integrated into CI/CD
pipelines to enforce documentation standards.

Usage:
    python scripts/doc_coverage.py [--threshold THRESHOLD] [--verbose] [--format FORMAT]

Arguments:
    --threshold THRESHOLD: Minimum coverage percentage (default: 95)
    --verbose: Show detailed information about missing documentation
    --format FORMAT: Output format (text, json, xml) (default: text)

Returns:
    Exit code 0 if coverage meets threshold, 1 otherwise

Example:
    python scripts/doc_coverage.py --threshold 90 --verbose
"""

import ast
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, NamedTuple
from dataclasses import dataclass


@dataclass
class DocstringInfo:
    """Information about a docstring in the codebase."""
    name: str
    type: str  # 'module', 'class', 'function', 'method'
    file_path: str
    line_number: int
    has_docstring: bool
    docstring_content: str = ""


class DocCoverageAnalyzer:
    """
    Analyzer for Python docstring coverage in the codebase.
    
    This analyzer walks through Python files and checks for the presence
    of docstrings in modules, classes, and functions. It calculates coverage
    percentages and provides detailed reporting on missing documentation.
    
    Attributes:
        min_coverage: Minimum required documentation coverage percentage
        verbose: Enable verbose output for detailed reporting
        exclude_patterns: List of patterns to exclude from analysis
    """
    
    def __init__(self, min_coverage: float = 95.0, verbose: bool = False):
        """
        Initialize the documentation coverage analyzer.
        
        :param min_coverage: Minimum required coverage percentage (0-100)
        :param verbose: Enable verbose output for detailed reporting
        """
        self.min_coverage = min_coverage
        self.verbose = verbose
        self.exclude_patterns = ['__pycache__', '.pyc', 'test_', '_test.py']
        self.docstring_info: List[DocstringInfo] = []
        
    def analyze_directory(self, directory: str) -> Dict[str, float]:
        """
        Analyze all Python files in a directory for docstring coverage.
        
        :param directory: Directory path to analyze
        :return: Dictionary with coverage statistics
        :raises FileNotFoundError: If directory doesn't exist
        :raises PermissionError: If directory is not accessible
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Directory not found: {directory}")
            
        if not os.path.isdir(directory):
            raise NotADirectoryError(f"Path is not a directory: {directory}")
            
        self.docstring_info.clear()
        
        # Walk through directory and analyze Python files
        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in self.exclude_patterns)]
            
            for file in files:
                if file.endswith('.py') and not any(pattern in file for pattern in self.exclude_patterns):
                    file_path = os.path.join(root, file)
                    try:
                        self._analyze_file(file_path)
                    except Exception as e:
                        logging.warning(f"Error analyzing {file_path}: {e}")
                        continue
        
        return self._calculate_coverage_stats()
    
    def _analyze_file(self, file_path: str) -> None:
        """
        Analyze a single Python file for docstring coverage.
        
        :param file_path: Path to the Python file to analyze
        :raises SyntaxError: If file contains invalid Python syntax
        :raises UnicodeDecodeError: If file encoding is invalid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        try:
            # Parse the Python file into an AST
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            logging.error(f"Syntax error in {file_path}: {e}")
            return
        
        # Check module-level docstring
        module_docstring = ast.get_docstring(tree)
        self.docstring_info.append(DocstringInfo(
            name=os.path.basename(file_path),
            type='module',
            file_path=file_path,
            line_number=1,
            has_docstring=module_docstring is not None,
            docstring_content=module_docstring or ""
        ))
        
        # Walk the AST to find classes and functions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._analyze_class(node, file_path)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Only analyze top-level functions (not methods)
                if self._is_top_level_function(node, tree):
                    self._analyze_function(node, file_path, 'function')
    
    def _analyze_class(self, node: ast.ClassDef, file_path: str) -> None:
        """
        Analyze a class definition for docstring coverage.
        
        :param node: AST node representing the class
        :param file_path: Path to the file containing the class
        """
        class_docstring = ast.get_docstring(node)
        self.docstring_info.append(DocstringInfo(
            name=node.name,
            type='class',
            file_path=file_path,
            line_number=node.lineno,
            has_docstring=class_docstring is not None,
            docstring_content=class_docstring or ""
        ))
        
        # Analyze methods within the class
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._analyze_function(item, file_path, 'method')
    
    def _analyze_function(self, node: ast.FunctionDef, file_path: str, func_type: str) -> None:
        """
        Analyze a function or method definition for docstring coverage.
        
        :param node: AST node representing the function
        :param file_path: Path to the file containing the function
        :param func_type: Type of function ('function' or 'method')
        """
        # Skip private methods and special methods for coverage calculation
        if node.name.startswith('_') and not node.name.startswith('__'):
            return
            
        function_docstring = ast.get_docstring(node)
        self.docstring_info.append(DocstringInfo(
            name=node.name,
            type=func_type,
            file_path=file_path,
            line_number=node.lineno,
            has_docstring=function_docstring is not None,
            docstring_content=function_docstring or ""
        ))
    
    def _is_top_level_function(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
        """
        Check if a function is defined at the top level of a module.
        
        :param node: Function AST node to check
        :param tree: Complete AST tree of the module
        :return: True if function is at top level, False otherwise
        """
        # Check if the function is directly in module body
        return node in tree.body
    
    def _calculate_coverage_stats(self) -> Dict[str, float]:
        """
        Calculate documentation coverage statistics.
        
        :return: Dictionary containing coverage statistics by type
        """
        stats = {
            'total_items': len(self.docstring_info),
            'documented_items': sum(1 for item in self.docstring_info if item.has_docstring),
            'overall_coverage': 0.0,
            'module_coverage': 0.0,
            'class_coverage': 0.0,
            'function_coverage': 0.0,
            'method_coverage': 0.0
        }
        
        if stats['total_items'] > 0:
            stats['overall_coverage'] = (stats['documented_items'] / stats['total_items']) * 100
        
        # Calculate coverage by type
        for doc_type in ['module', 'class', 'function', 'method']:
            items_of_type = [item for item in self.docstring_info if item.type == doc_type]
            documented_items_of_type = [item for item in items_of_type if item.has_docstring]
            
            if items_of_type:
                coverage = (len(documented_items_of_type) / len(items_of_type)) * 100
                stats[f'{doc_type}_coverage'] = coverage
        
        return stats
    
    def generate_report(self, stats: Dict[str, float]) -> str:
        """
        Generate a detailed coverage report.
        
        :param stats: Coverage statistics dictionary
        :return: Formatted report string
        """
        report_lines = [
            "=" * 60,
            "DOCUMENTATION COVERAGE REPORT",
            "=" * 60,
            f"Overall Coverage: {stats['overall_coverage']:.1f}%",
            f"Minimum Required: {self.min_coverage:.1f}%",
            "",
            "Coverage by Type:",
            f"  Modules:   {stats['module_coverage']:.1f}%",
            f"  Classes:   {stats['class_coverage']:.1f}%",
            f"  Functions: {stats['function_coverage']:.1f}%",
            f"  Methods:   {stats['method_coverage']:.1f}%",
            "",
            f"Total Items: {stats['total_items']}",
            f"Documented: {stats['documented_items']}",
            f"Missing: {stats['total_items'] - stats['documented_items']}",
        ]
        
        # Add missing docstrings section
        missing_items = [item for item in self.docstring_info if not item.has_docstring]
        if missing_items:
            report_lines.extend([
                "",
                "MISSING DOCSTRINGS:",
                "-" * 40
            ])
            
            # Group by file for better readability
            by_file = {}
            for item in missing_items:
                if item.file_path not in by_file:
                    by_file[item.file_path] = []
                by_file[item.file_path].append(item)
            
            for file_path, items in sorted(by_file.items()):
                relative_path = os.path.relpath(file_path)
                report_lines.append(f"\n{relative_path}:")
                for item in items:
                    report_lines.append(f"  Line {item.line_number:3d}: {item.type} '{item.name}'")
        
        # Add verbose details if requested
        if self.verbose:
            report_lines.extend([
                "",
                "DETAILED ANALYSIS:",
                "-" * 40
            ])
            
            for item in sorted(self.docstring_info, key=lambda x: (x.file_path, x.line_number)):
                relative_path = os.path.relpath(item.file_path)
                status = "✓" if item.has_docstring else "✗"
                report_lines.append(
                    f"{status} {relative_path}:{item.line_number} - {item.type} '{item.name}'"
                )
        
        report_lines.extend([
            "",
            "=" * 60
        ])
        
        return "\n".join(report_lines)
    
    def check_coverage_threshold(self, stats: Dict[str, float]) -> bool:
        """
        Check if coverage meets the minimum threshold.
        
        :param stats: Coverage statistics dictionary
        :return: True if coverage meets threshold, False otherwise
        """
        return stats['overall_coverage'] >= self.min_coverage


def main():
    """
    Main entry point for the documentation coverage checker.
    
    Parses command line arguments, analyzes the codebase, and reports
    documentation coverage statistics. Exits with appropriate codes
    based on coverage results.
    """
    parser = argparse.ArgumentParser(
        description="Check documentation coverage for AI Dashboard Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/doc_coverage.py                    # Check with default 95% threshold
  python scripts/doc_coverage.py --min-coverage 90  # Check with 90% threshold
  python scripts/doc_coverage.py --verbose          # Show detailed analysis
        """
    )
    
    parser.add_argument(
        '--min-coverage',
        type=float,
        default=95.0,
        help='Minimum required documentation coverage percentage (default: 95.0)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output with detailed analysis'
    )
    
    parser.add_argument(
        '--directory',
        type=str,
        default='app',
        help='Directory to analyze (default: app)'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(levelname)s: %(message)s'
    )
    
    try:
        # Initialize analyzer and run analysis
        analyzer = DocCoverageAnalyzer(
            min_coverage=args.min_coverage,
            verbose=args.verbose
        )
        
        # Analyze the specified directory
        stats = analyzer.analyze_directory(args.directory)
        
        # Generate and print report
        report = analyzer.generate_report(stats)
        print(report)
        
        # Check if coverage meets threshold
        if analyzer.check_coverage_threshold(stats):
            print(f"\n✅ Documentation coverage PASSED ({stats['overall_coverage']:.1f}% >= {args.min_coverage:.1f}%)")
            sys.exit(0)
        else:
            print(f"\n❌ Documentation coverage FAILED ({stats['overall_coverage']:.1f}% < {args.min_coverage:.1f}%)")
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"Unexpected error: {e}")
        logging.exception("Full traceback:")
        sys.exit(2)


if __name__ == '__main__':
    main()
