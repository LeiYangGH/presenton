# Upstream Changes Summary (Feb 2026 - Apr 2026)

This document summarizes the major updates in the `main` branch of Presenton since late February 2026 and their potential impact on the `lite` branch.

## 1. Electron Desktop Support
The most significant architectural change is the introduction of a native desktop application powered by Electron.
- **Integrated Dependencies:** The desktop app now includes built-in installers for critical dependencies like **LibreOffice** (for PPTX/PDF conversion) and **Chromium** (via Puppeteer). This removes the previous requirement for users to manually install these on their host system.
- **Local-First Architecture:** While the Docker version remains supported, the Electron version optimizes for local execution with SQLite and local file management.
- **Monitoring & Telemetry:** Integration of **Sentry** for error tracking and **Mixpanel** for advanced usage analytics.
- **Unified Build Process:** New build scripts (`build:all`) automate the packaging of FastAPI (via PyInstaller) and Next.js into a single executable.

## 2. PPTX Generation & Quality Improvements
Significant effort has been put into improving the reliability and quality of generated presentations.
- **Overflow Mitigation (Schema Validation Loop):** A new recursive loop in `LLMClient.generate_structured` validates LLM output against the JSON schema. If character limits are exceeded or the structure is invalid, the error is fed back to the LLM for automatic correction (up to 5 retries).
- **Strict Prompt Engineering:** System prompts have been revamped to enforce strict character limits for every field, preventing text clipping in UI and exported files.
- **Font Resolution:** Added support for resolving and embedding specific fonts in presentations, ensuring the exported PPTX matches the web preview.
- **Document Decomposition:** Integration of **LiteParse** and **Docling** services for more accurate processing of uploaded documents (PDFs, Word, etc.) into presentation outlines.

## 3. Templates and Themes
- **New Core Templates:** Four professional templates were added: **Code**, **Education**, **Product Overview**, and **Report**.
- **Custom Template UI:** A completely revamped interface for creating and managing custom templates, allowing developers/users to build their own designs using HTML/Tailwind.
- **Theme Management:** Improved color palette generation and theme application across all slide layouts.
- **Code Highlighting:** Enhanced support for code blocks within templates, including syntax highlighting.

## 4. Stability & Infrastructure
- **Database Migrations:** Transitioned to a more robust migration system that automatically syncs the database schema on startup, supporting legacy database migrations.
- **Provider Enhancements:** Better support for **Anthropic (Claude)**, **Google (Gemini)**, and **Codex**, including improved streaming logic and retry mechanisms.
- **Ollama Integration:** Improved handling of local Ollama models, including model metadata fetching and status reporting.

## 5. Impact on Lite Branch
Since the `lite` branch is likely focused on a lightweight, Docker-based or API-only deployment:
- **Feature Parity:** The `lite` branch benefits from the improved prompts and the **Schema Validation Loop**, which significantly reduces "broken" generation results.
- **Dependency Management:** The new `Dockerfile.lite` and related changes in `main` might conflict if they assume the presence of Electron-specific binaries.
- **Export Logic:** Changes to `export_utils` and the use of specialized conversion binaries (managed by `sync_export_runtime.js`) may require the `lite` branch to ensure it has the correct version of the conversion tool compatible with its environment.
- **Schema Changes:** Recent database schema updates (themes, fonts) will require a migration if existing data is being preserved.
