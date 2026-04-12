SEVERITY_ICON = {
    "high":   "🔴",
    "medium": "🟡",
    "low":    "🔵",
}

TYPE_LABEL = {
    "bug":          "Bug",
    "architecture": "Architecture",
    "style":        "Style",
}


def to_github_comment(review: dict, repo: str, pr_number: int) -> str:
    lines = [
        f"## 🤖 ReviewAgent — `{repo}` PR #{pr_number}",
        "",
        "### Summary",
        review.get("summary", "No summary provided."),
        "",
    ]

    issues = review.get("issues", [])

    if not issues:
        lines += ["### Issues", "_No issues found._", ""]
    else:
        high   = [i for i in issues if i.get("severity") == "high"]
        medium = [i for i in issues if i.get("severity") == "medium"]
        low    = [i for i in issues if i.get("severity") == "low"]

        lines += ["### Issues", ""]

        for group, label in ((high, "High"), (medium, "Medium"), (low, "Low")):
            if not group:
                continue
            icon = SEVERITY_ICON[label.lower()]
            lines.append(f"#### {icon} {label} Severity")
            for issue in group:
                type_label = TYPE_LABEL.get(issue.get("type", "style"), "Style")
                confidence = issue.get("confidence")
                conf_str = f" _(confidence: {confidence}%)_" if confidence is not None else ""
                lines.append(f"- **[{type_label}]** {issue.get('message', '')}{conf_str}")
                if issue.get("suggestion"):
                    lines.append(f"  - 💡 {issue['suggestion']}")
                if issue.get("reference"):
                    lines.append(f"  - 📌 _{issue['reference']}_")
            lines.append("")

    total = len(issues)
    high_count = sum(1 for i in issues if i.get("severity") == "high")
    lines += [
        "---",
        f"_ReviewAgent found **{total}** issue(s) — **{high_count}** high severity. "
        "Powered by persistent belief system._",
    ]

    return "\n".join(lines)
