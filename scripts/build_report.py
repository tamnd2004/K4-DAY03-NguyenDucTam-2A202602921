"""Fill the original Day 03 report format from recorded live evidence."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_published():
    """Check the last locally recorded upstream commit; do not contact the network."""
    command = ["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse"]
    try:
        head = subprocess.check_output(command + ["HEAD"], cwd=ROOT, stderr=subprocess.DEVNULL)
        upstream = subprocess.check_output(command + ["@{upstream}"], cwd=ROOT, stderr=subprocess.DEVNULL)
        return head.strip() == upstream.strip()
    except subprocess.CalledProcessError:
        return False


def main():
    live = json.loads((ROOT / "docs/trace_waterfall.json").read_text(encoding="utf-8"))
    evaluations = {item["id"]: item for item in live["evaluations"]}
    runs = live["runs"]
    valid = [run for run in runs if run.get("live") and run["status"] == "completed"
             and evaluations.get(run["test_case"], {}).get("passed")]
    example = next((run for run in valid if run["test_case"] == "TC04"), next(iter(valid), None))
    if example is None:
        raise SystemExit("No successful live run available; existing report left unchanged.")

    # A short, real Thought -> Action -> Observation -> Final Answer excerpt.
    action = next((event for event in example["trace"]
                   if event["action_type"] == "ACTION" and event.get("tool_name") == "create_leave_request"), None)
    if action:
        thought = next(event for event in example["trace"]
                       if event["action_type"] == "THOUGHT" and event["step"] == action["step"])
        observation = next(event for event in example["trace"]
                           if event["action_type"] == "OBSERVATION" and event["call_id"] == action["call_id"])
        final = next(event for event in reversed(example["trace"]) if event["action_type"] == "FINAL_ANSWER")
        selected = [thought, action, observation, final]
    else:
        selected = [event for event in example["trace"]
                    if event["action_type"] in {"THOUGHT", "ACTION", "OBSERVATION", "FINAL_ANSWER"}]
    fields = {"step", "action_type", "summary", "tool_name", "arguments", "observation", "output", "latency_ms"}
    excerpt = [{key: value for key, value in event.items() if key in fields} for event in selected]
    core_ids = {f"TC{index:02d}" for index in range(1, 6)}
    core = [item for item in evaluations.values() if item["id"] in core_ids]
    extra = [item for item in evaluations.values() if item["id"] not in core_ids]
    values = {
        "CASE_ID": example["test_case"],
        "MODEL": example["model"],
        "RUN_ID": example["run_id"],
        "TRACE_EXCERPT": json.dumps(excerpt, ensure_ascii=False, indent=2),
        "LIVE_CHECK": "x" if len(valid) == len(runs) == len(evaluations) and runs else " ",
        "CORE_PASSED": sum(item["passed"] for item in core),
        "EXTRA_PASSED": sum(item["passed"] for item in extra),
        "EXTRA_TOTAL": len(extra),
        "TOTAL_PASSED": sum(item["passed"] for item in evaluations.values()),
        "TOTAL": len(evaluations),
        "CORE_TOOLS": sum(run["tool_calls"] for run in runs if run["test_case"] in core_ids),
        "TOTAL_TOOLS": sum(run["tool_calls"] for run in runs),
        "GIT_CHECK": "x" if git_published() else " ",
    }
    template = (ROOT / "docs/templates/trace_eval.template.md").read_text(encoding="utf-8")
    report = re.sub(r"\{\{([A-Z_]+)\}\}", lambda match: str(values[match.group(1)]), template)
    (ROOT / "docs/trace_eval.md").write_text(report, encoding="utf-8")
    print(f"Report generated in original format: {values['CORE_PASSED']}/5 core, "
          f"{values['EXTRA_PASSED']}/{values['EXTRA_TOTAL']} extra, {values['TOTAL_TOOLS']} tool calls.")


if __name__ == "__main__":
    main()
