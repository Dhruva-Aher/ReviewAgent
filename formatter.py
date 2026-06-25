SEVERITY_ICON = {
    "high":   "🔴",
    "medium": "🟡",
    "low":    "🔵",
}

TYPE_LABEL = {
    "bug":          "Bug",
    "security":     "Security",
    "performance":  "Performance",
    "architecture": "Architecture",
    "style":        "Style",
}


def to_github_comment(review: dict, repo: str, pr_number: int) -> str:
    issues = review.get("issues", [])
    summary = review.get("summary", "No summary provided.")

    lines = [
        f"## 🧠 PRBeliefs — `{repo}` PR #{pr_number}",
        "",
    ]

    if not issues:
        lines += [
            "### ✅ Approved",
            "",
            summary,
        ]
    else:
        lines += [
            "### Summary",
            summary,
            "",
            "### Issues",
            "",
        ]

        high   = [i for i in issues if i.get("severity") == "high"]
        medium = [i for i in issues if i.get("severity") == "medium"]
        low    = [i for i in issues if i.get("severity") == "low"]

        for group, label in ((high, "High"), (medium, "Medium"), (low, "Low")):
            if not group:
                continue
            icon = SEVERITY_ICON[label.lower()]
            lines.append(f"#### {icon} {label} Severity")
            for issue in group:
                type_label = TYPE_LABEL.get(issue.get("type", "bug"), "Bug")
                confidence = issue.get("confidence")
                loc = ""
                if issue.get("file"):
                    loc = f" in `{issue['file']}`"
                    if issue.get("line"):
                        loc += f" (line {issue['line']})"
                conf_str = f" — _{confidence}% confidence_" if confidence is not None else ""
                lines.append(f"- **[{type_label}]** {issue.get('message', '')}{loc}{conf_str}")
                if issue.get("suggestion"):
                    lines.append(f"  - 💡 **Fix:** {issue['suggestion']}")
                if issue.get("reference"):
                    lines.append(f"  - 📌 _Violates team rule: {issue['reference']}_")
            lines.append("")

        high_count = len(high)
        lines += [
            "---",
            f"_Found **{len(issues)}** issue(s) — **{high_count}** high severity._",
        ]

    return "\n".join(lines)
