#!/usr/bin/env python3
"""Generate HTML report for skill description optimization."""

import argparse
import html
import json
from pathlib import Path


TITLE_PREFIX = "Skill Description Optimization - "


def generate_report(data: dict, output_path: Path) -> None:
    """Generate an HTML report from optimization data."""
    history = data.get("history", [])
    train_queries = data.get("train_queries", [])
    test_queries = data.get("test_queries", [])

    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "    <meta charset='UTF-8'>",
        "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"    <title>{TITLE_PREFIX}{data.get('skill_name', 'Skill')}</title>",
        "    <style>",
        "        body { font-family: system-ui, -apple-system, sans-serif; margin: 20px; background: #f5f5f5; }",
        "        .container { max-width: 1400px; margin: 0 auto; }",
        "        h1 { color: #333; }",
        "        .summary { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        "        table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
        "        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }",
        "        th { background: #f8f9fa; font-weight: 600; }",
        "        .pass { color: #28a745; }",
        "        .fail { color: #dc3545; }",
        "        .score-good { background: #d4edda; }",
        "        .score-ok { background: #fff3cd; }",
        "        .score-bad { background: #f8d7da; }",
        "        .best-row { background: #d4edda; }",
        "        .positive-col { border-left: 3px solid #28a745; }",
        "        .negative-col { border-left: 3px solid #dc3545; }",
        "        .description-cell { max-width: 400px; word-wrap: break-word; }",
        "    </style>",
        "</head>",
        "<body>",
        "    <div class='container'>",
        f"        <h1>{TITLE_PREFIX}{data.get('skill_name', 'Skill')}</h1>",
    ]

    # Summary section
    best_test_score = data.get("best_test_score")
    best_train_score = data.get("best_train_score")
    html_parts.extend([
        "        <div class='summary'>",
        f"            <p><strong>Original:</strong> {html.escape(data.get('original_description', 'N/A'))}</p>",
        f"            <p><strong>Best:</strong> {html.escape(data.get('best_description', 'N/A'))}</p>",
        f"            <p><strong>Best Score:</strong> {data.get('best_score', 'N/A')} {'(test)' if best_test_score else '(train)'}</p>",
        f"            <p><strong>Iterations:</strong> {data.get('iterations_run', 0)} | Train: {data.get('train_size', '?')} | Test: {data.get('test_size', '?')}</p>",
        "        </div>",
    ])

    # Legend
    html_parts.extend([
        "        <p>",
        "            <strong>Query columns:</strong> ",
        "            <span style='color: #28a745;'>✓ Should trigger</span> | ",
        "            <span style='color: #dc3545;'>✗ Should NOT trigger</span> | ",
        "            <strong>Train</strong> | <strong>Test</strong>",
        "        </p>",
    ])

    # Table header
    html_parts.extend([
        "        <table>",
        "            <thead>",
        "                <tr>",
        "                    <th>Iter</th>",
        "                    <th>Train</th>",
        "                    <th>Test</th>",
        "                    <th>Description</th>",
    ])

    # Add column headers for train queries
    for qinfo in train_queries:
        polarity = "positive-col" if qinfo["should_trigger"] else "negative-col"
        html_parts.append(f"                    <th class='{polarity}'>{html.escape(qinfo['query'][:50])}...</th>")

    # Add column headers for test queries (different color)
    for qinfo in test_queries:
        polarity = "positive-col" if qinfo["should_trigger"] else "negative-col"
        html_parts.append(f"                    <th class='{polarity}'>{html.escape(qinfo['query'][:50])}...</th>")

    html_parts.extend([
        "                </tr>",
        "            </thead>",
        "            <tbody>",
    ])

    # Find best iteration for highlighting
    if test_queries:
        best_iter = max(history, key=lambda h: h.get("test_passed") or 0).get("iteration")
    else:
        best_iter = max(history, key=lambda h: h.get("train_passed", h.get("passed", 0))).get("iteration")

    # Create rows for each iteration
    for h in history:
        iteration = h.get("iteration", "?")
        train_passed = h.get("train_passed", h.get("passed", 0))
        train_total = h.get("train_total", h.get("total", 0))
        test_passed = h.get("test_passed")
        test_total = h.get("test_total")
        description = h.get("description", "")

        train_results = h.get("train_results", h.get("results", []))
        test_results = h.get("test_results", [])

        # Compute aggregate correct/total runs across all retries
        def aggregate_runs(results: list[dict]) -> tuple[int, int]:
            correct = 0
            total = 0
            for r in results:
                runs = r.get("runs", 0)
                triggers = r.get("triggers", 0)
                total += runs
                if r.get("should_trigger", True):
                    correct += triggers
                else:
                    correct += runs - triggers
            return correct, total

        train_correct, train_runs = aggregate_runs(train_results)
        test_correct, test_runs = aggregate_runs(test_results)

        # Determine score classes
        def score_class(correct: int, total: int) -> str:
            if total > 0:
                ratio = correct / total
                if ratio >= 0.8:
                    return "score-good"
                elif ratio >= 0.5:
                    return "score-ok"
            return "score-bad"

        train_class = score_class(train_correct, train_runs)
        test_class = score_class(test_correct, test_runs)
        row_class = "best-row" if iteration == best_iter else ""

        html_parts.extend([
            f"                <tr class='{row_class}'>",
            f"                    <td>{iteration}</td>",
            f"                    <td class='{train_class}'>{train_correct}/{train_runs}</td>",
            f"                    <td class='{test_class}'>{test_correct}/{test_runs}</td>",
            f"                    <td class='description-cell'>{html.escape(description)}</td>",
        ])

        # Add result for each train query
        train_by_query = {r["query"]: r for r in train_results}
        for qinfo in train_queries:
            r = train_by_query.get(qinfo["query"], {})
            did_pass = r.get("pass", False)
            triggers = r.get("triggers", 0)
            runs = r.get("runs", 0)
            icon = "✓" if did_pass else "✗"
            css_class = "pass" if did_pass else "fail"
            html_parts.append(f"                    <td class='{css_class}'>{icon}{triggers}/{runs}</td>")

        # Add result for each test query (with different background)
        test_by_query = {r["query"]: r for r in test_results}
        for qinfo in test_queries:
            r = test_by_query.get(qinfo["query"], {})
            did_pass = r.get("pass", False)
            triggers = r.get("triggers", 0)
            runs = r.get("runs", 0)
            icon = "✓" if did_pass else "✗"
            css_class = "pass" if did_pass else "fail"
            html_parts.append(f"                    <td class='{css_class}'>{icon}{triggers}/{runs}</td>")

        html_parts.append("                </tr>")

    html_parts.extend([
        "            </tbody>",
        "        </table>",
        "    </div>",
        "</body>",
        "</html>",
    ])

    output_path.write_text("\n".join(html_parts))


def main():
    parser = argparse.ArgumentParser(description="Generate HTML report for description optimization")
    parser.add_argument("--input", required=True, type=Path, help="Path to optimization results JSON")
    parser.add_argument("--output", required=True, type=Path, help="Path to output HTML file")
    args = parser.parse_args()

    data = json.loads(args.input.read_text())
    generate_report(data, args.output)
    print(f"Report generated: {args.output}")


if __name__ == "__main__":
    main()
