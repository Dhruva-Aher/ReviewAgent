# Privacy Policy

**Effective Date:** June 25, 2026

PRBeliefs (also known as ReviewAgent) is a GitHub App designed to provide automated, context-aware code reviews. We are committed to protecting your privacy and ensuring transparency regarding how your data is handled.

## 1. GitHub Permissions Used

PRBeliefs requests the following permissions upon installation:
* **Pull Requests (Read & Write):** To read diffs and post review comments.
* **Repository Contents (Read-only):** To analyze the files changed in a pull request and read repository configuration (e.g., `requirements.txt`).
* **Issues (Read & Write):** To read and respond to issue comments and slash commands.
* **Metadata (Read-only):** To access basic repository information.

## 2. Data Collected

When PRBeliefs processes a pull request, we temporarily collect and process:
* Pull request metadata (title, description, author, PR number).
* Code diffs and relevant file contents.
* Review comments made by users (to extract past decisions and beliefs).

## 3. Data Stored

* **Team Rules & Past Decisions:** We extract rules, conventions, and past decisions ("beliefs") from pull request discussions and store them in a local SQLite database on the server where the app is hosted.
* **Telemetry & Metrics:** We log agent run durations, confidence scores, and queue lengths for performance monitoring.
* **No Personal Data:** We do not collect or store personal identifiable information (PII) beyond GitHub usernames associated with PRs (strictly for contextual logging and filtering bot comments).
* **Code is not stored:** We do not persistently store your source code or PR diffs. They are only held in memory during the review process.

## 4. Data Retention

* **Beliefs & Rules:** Kept indefinitely or until manually deleted via slash commands. Historical decisions older than 180 days are automatically filtered out from active prompts.
* **Logs & Metrics:** System logs are rotated and typically retained for no longer than 30 days.

## 5. Third-Party Services

* **Groq / LLM Providers:** PRBeliefs sends code diffs and extracted beliefs to third-party Large Language Model providers (such as Groq) to generate the review feedback. These providers act as sub-processors. By using PRBeliefs, you acknowledge that your code snippets will be securely transmitted to these APIs for processing.
* **Redis:** Used locally for job queue management.

## 6. Security Practices

* Data in transit is encrypted using TLS.
* Access to the host environment and databases is strictly limited to authorized maintainers.
* API keys (e.g., Groq, GitHub) are stored securely using environment variables.

## 7. Deletion Requests

If you uninstall the GitHub App, we will cease all data processing for your repositories. To request the deletion of all stored rules, decisions, and telemetry associated with your repository, please contact us at the email below.

## 8. Contact Information

For any privacy-related questions, data deletion requests, or concerns, please contact:
**Email:** daher@asu.edu
