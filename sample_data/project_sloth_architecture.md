# SlothMate AI Architecture Overview
**Author:** Lead Architect
**Status:** Approved

## System Philosophy
SlothMate AI is built around the "Slow and Steady" design ethos. All document processing must happen 100% on-device using open-weight models via local Ollama.

## Required Tasks:
- Implement bounded JSON repair in local_model.py to handle unescaped characters (Priority: High, Deadline: 2026-10-28).
- Refactor PDF extraction to use PyMuPDF for robust handling of encrypted documents (Priority: Medium, Deadline: 2026-10-30).
- Add automated pytest unit test suite covering task deduplication (Priority: High, Deadline: 2026-10-27).
- Update the README documentation with offline-first guidelines.
