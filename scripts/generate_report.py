#!/usr/bin/env python3
"""Generate test reports from JUnit XML and coverage files."""

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import glob


def parse_junit_xml(file_path: Path) -> Dict[str, Any]:
    """Parse a JUnit XML file and extract test results."""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    results = {
        "file": str(file_path),
        "testsuite": root.attrib.get("name", "unknown"),
        "tests": int(root.attrib.get("tests", 0)),
        "failures": int(root.attrib.get("failures", 0)),
        "errors": int(root.attrib.get("errors", 0)),
        "skipped": int(root.attrib.get("skipped", 0)),
        "time": float(root.attrib.get("time", 0)),
        "testcases": []
    }
    
    for testcase in root.findall(".//testcase"):
        tc = {
            "name": testcase.attrib.get("name", ""),
            "classname": testcase.attrib.get("classname", ""),
            "time": float(testcase.attrib.get("time", 0)),
            "status": "passed"
        }
        
        if testcase.find("failure") is not None:
            tc["status"] = "failed"
            tc["failure"] = testcase.find("failure").attrib.get("message", "")
        elif testcase.find("error") is not None:
            tc["status"] = "error"
            tc["error"] = testcase.find("error").attrib.get("message", "")
        elif testcase.find("skipped") is not None:
            tc["status"] = "skipped"
        
        results["testcases"].append(tc)
    
    return results


def parse_coverage_json(file_path: Path) -> Dict[str, Any]:
    """Parse coverage JSON file."""
    with open(file_path) as f:
        return json.load(f)


def find_files(input_dir: Path, patterns: List[str]) -> List[Path]:
    """Find files matching patterns."""
    files = []
    for pattern in patterns:
        files.extend(input_dir.rglob(pattern))
    return files


def generate_html_report(data: Dict[str, Any], output_path: Path):
    """Generate HTML test report."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .skipped {{ color: orange; }}
        .error {{ color: purple; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .suite {{ margin-bottom: 30px; }}
    </style>
</head>
<body>
    <h1>Test Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: {data['summary']['total_tests']}</p>
        <p class="passed">Passed: {data['summary']['passed']}</p>
        <p class="failed">Failed: {data['summary']['failed']}</p>
        <p class="skipped">Skipped: {data['summary']['skipped']}</p>
        <p class="error">Errors: {data['summary']['errors']}</p>
        <p>Total Time: {data['summary']['total_time']:.2f}s</p>
    </div>
    
    <h2>Coverage</h2>
    <p>Line Coverage: {data['coverage'].get('line_coverage', 'N/A')}%</p>
    <p>Branch Coverage: {data['coverage'].get('branch_coverage', 'N/A')}%</p>
    
    <h2>Test Suites</h2>
"""
    
    for suite in data['suites']:
        html += f"""
    <div class="suite">
        <h3>{suite['testsuite']} ({suite['file']})</h3>
        <p>Tests: {suite['tests']}, Failures: {suite['failures']}, Errors: {suite['errors']}, Skipped: {suite['skipped']}, Time: {suite['time']:.2f}s</p>
        <table>
            <tr>
                <th>Test</th>
                <th>Class</th>
                <th>Status</th>
                <th>Time (s)</th>
            </tr>
"""
        for tc in suite['testcases']:
            status_class = tc['status']
            html += f"""
            <tr>
                <td>{tc['name']}</td>
                <td>{tc['classname']}</td>
                <td class="{status_class}">{tc['status'].upper()}</td>
                <td>{tc['time']:.3f}</td>
            </tr>
"""
        html += """
        </table>
    </div>
"""
    
    html += """
</body>
</html>
"""
    
    with open(output_path, 'w') as f:
        f.write(html)


def generate_markdown_report(data: Dict[str, Any], output_path: Path):
    """Generate Markdown test report."""
    md = f"""# Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {data['summary']['total_tests']} |
| Passed | {data['summary']['passed']} |
| Failed | {data['summary']['failed']} |
| Skipped | {data['summary']['skipped']} |
| Errors | {data['summary']['errors']} |
| Total Time | {data['summary']['total_time']:.2f}s |

## Coverage

| Metric | Value |
|--------|-------|
| Line Coverage | {data['coverage'].get('line_coverage', 'N/A')}% |
| Branch Coverage | {data['coverage'].get('branch_coverage', 'N/A')}% |

## Test Suites

"""
    
    for suite in data['suites']:
        md += f"### {suite['testsuite']}\n\n"
        md += f"**File:** {suite['file']}  \n"
        md += f"**Tests:** {suite['tests']} | **Failures:** {suite['failures']} | **Errors:** {suite['errors']} | **Skipped:** {suite['skipped']} | **Time:** {suite['time']:.2f}s\n\n"
        
        md += "| Test | Class | Status | Time (s) |\n"
        md += "|------|-------|--------|----------|\n"
        
        for tc in suite['testcases']:
            status = tc['status'].upper()
            md += f"| {tc['name']} | {tc['classname']} | {status} | {tc['time']:.3f} |\n"
        
        md += "\n"
    
    with open(output_path, 'w') as f:
        f.write(md)


def generate_json_report(data: Dict[str, Any], output_path: Path):
    """Generate JSON test report."""
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Generate test reports")
    parser.add_argument("--input-dir", required=True, help="Input directory with test results")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--format", choices=["html", "markdown", "json"], required=True, help="Output format")
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    
    # Find JUnit XML files
    junit_files = find_files(input_dir, ["*.xml"])
    
    # Find coverage files
    coverage_files = find_files(input_dir, ["coverage.json", "coverage/*.json"])
    
    all_results = []
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_errors = 0
    total_time = 0.0
    
    for junit_file in junit_files:
        try:
            result = parse_junit_xml(junit_file)
            all_results.append(result)
            
            total_tests += result['tests']
            total_failed += result['failures']
            total_errors += result['errors']
            total_skipped += result['skipped']
            total_time += result['time']
            
            for tc in result['testcases']:
                if tc['status'] == 'passed':
                    total_passed += 1
        except Exception as e:
            print(f"Error parsing {junit_file}: {e}")
    
    # Parse coverage
    coverage_data = {}
    for cov_file in coverage_files:
        try:
            cov = parse_coverage_json(cov_file)
            if 'totals' in cov:
                coverage_data['line_coverage'] = cov['totals'].get('percent_covered', 0)
                coverage_data['branch_coverage'] = cov['totals'].get('branch_coverage', 0)
            break
        except Exception as e:
            print(f"Error parsing coverage {cov_file}: {e}")
    
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "errors": total_errors,
            "total_time": total_time
        },
        "coverage": coverage_data,
        "suites": all_results
    }
    
    if args.format == "html":
        generate_html_report(report_data, output_path)
    elif args.format == "markdown":
        generate_markdown_report(report_data, output_path)
    elif args.format == "json":
        generate_json_report(report_data, output_path)
    
    print(f"Report generated: {output_path}")


if __name__ == "__main__":
    main()