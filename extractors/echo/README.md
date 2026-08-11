# ECHO — Extraction Helpers

High-fidelity document and page extraction utilities for multi-agent collectors:

- HTML extraction (BeautifulSoup)
- PDF / OCR fallback path
- Shared protocol for inter-agent extraction requests

## Usage

```python
from extractors.echo.osint_parser import call_echo  # adjust import path as installed
```

See `echo_protocol.md` for the handoff format used by specialized agents.
