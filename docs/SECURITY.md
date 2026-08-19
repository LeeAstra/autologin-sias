# Security and privacy checklist

- Confirm `.env` is ignored and not tracked.
- Search for phone numbers, passwords, MAC addresses, cookies, tokens, and HAR files.
- Do not commit `build/`, `dist/`, `release_*`, virtual environments, or runtime logs.
- Remove real credentials from historical examples and screenshots.
- Treat the portal's HTTP + RC4 protocol as a compatibility requirement, not as strong cryptography.
- If credentials were exposed, rotate them before publishing.
