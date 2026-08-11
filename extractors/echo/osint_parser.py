#!/usr/bin/env python3
"""
OSINT Parser v4 - Advanced version for the multi-agent OSINT stack

Includes:
- BeautifulSoup + PDF/OCR support
- Advanced entity extraction (spaCy preferred, regex fallback)
- Link classification
- Standardized ECHO helper
"""

from bs4 import BeautifulSoup
import requests
from typing import Optional, Dict, Any, List
import re
from urllib.parse import urljoin, urlparse
from collections import defaultdict

# Optional advanced libraries
try:
    import spacy
    _SPACY_NLP = None
    HAS_SPACY = True
except ImportError:
    HAS_SPACY = False
    _SPACY_NLP = None

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


class OSINTParser:
    def __init__(self, user_agent: str = "ELITE-OSINT-SWARM/3.0 (Echo-Parser)"):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self._spacy_nlp = None

    # ==================== spaCy Loader (lazy) ====================

    def _get_spacy_nlp(self):
        """Lazily load spaCy model for better entity extraction."""
        global _SPACY_NLP
        if _SPACY_NLP is not None:
            return _SPACY_NLP
        if HAS_SPACY:
            try:
                _SPACY_NLP = spacy.load("en_core_web_sm", disable=["parser", "tagger"])
                return _SPACY_NLP
            except Exception:
                return None
        return None

    # ==================== MAIN ENTRY POINT ====================

    def parse(self, url: str, **kwargs) -> Dict[str, Any]:
        if url.lower().endswith(".pdf") or "pdf" in url.lower():
            return self.parse_pdf(url, **kwargs)
        return self.fetch_and_parse(url, **kwargs)

    # ==================== HTML PARSING ====================

    def fetch_and_parse(
        self,
        url: str,
        selector: Optional[str] = None,
        remove_selectors: Optional[List[str]] = None,
        extract_tables: bool = False,
        extract_entities: bool = True,
        classify_links: bool = True
    ) -> Dict[str, Any]:
        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "header", "aside"]):
                tag.decompose()
            if remove_selectors:
                for sel in remove_selectors:
                    for t in soup.select(sel):
                        t.decompose()

            title = soup.title.string.strip() if soup.title else (soup.find("h1").get_text(strip=True) if soup.find("h1") else None)

            if selector:
                target = soup.select_one(selector)
                main_text = self._clean_text(target) if target else self._clean_text(soup)
            else:
                main_text = self._clean_text(soup)

            result = {
                "url": url,
                "status": "success",
                "content_type": "html",
                "title": title,
                "main_text": main_text[:30000],
                "word_count": len(main_text.split()),
                "source_domain": urlparse(url).netloc,
            }

            if extract_entities:
                result["entities"] = self.extract_entities(main_text)

            if classify_links:
                result["classified_links"] = self.classify_links(soup, url)

            if extract_tables:
                result["tables"] = self._extract_html_tables(soup)

            return result

        except Exception as e:
            return {"url": url, "status": "error", "error": str(e)}

    # ==================== PDF + OCR ====================

    def parse_pdf(self, url: str, extract_tables: bool = True, ocr_fallback: bool = True) -> Dict[str, Any]:
        try:
            resp = self.session.get(url, timeout=40)
            content = resp.content
            text_parts = []
            tables = []
            ocr_used = False

            if HAS_PDFPLUMBER:
                import io
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        page_text = page.extract_text()
                        if page_text and len(page_text.strip()) > 30:
                            text_parts.append(f"[Page {page_num}]\n{page_text}")
                        elif ocr_fallback and HAS_OCR and HAS_PYMUPDF:
                            ocr_text = self._ocr_page_with_pymupdf(content, page_num)
                            if ocr_text:
                                text_parts.append(f"[Page {page_num} - OCR]\n{ocr_text}")
                                ocr_used = True
                        if extract_tables:
                            for t in page.extract_tables() or []:
                                tables.append({"page": page_num, "data": t})
            elif HAS_PYMUPDF:
                doc = fitz.open(stream=content, filetype="pdf")
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    if text and len(text.strip()) > 30:
                        text_parts.append(f"[Page {page_num+1}]\n{text}")
                    elif ocr_fallback and HAS_OCR:
                        pix = page.get_pixmap(dpi=200)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        ocr_text = pytesseract.image_to_string(img)
                        text_parts.append(f"[Page {page_num+1} - OCR]\n{ocr_text}")
                        ocr_used = True

            full_text = "\n\n".join(text_parts)
            return {
                "url": url,
                "status": "success",
                "content_type": "pdf",
                "main_text": full_text[:35000],
                "word_count": len(full_text.split()),
                "tables": tables,
                "page_count": len(text_parts),
                "ocr_used": ocr_used,
                "entities": self.extract_entities(full_text) if full_text else {},
            }
        except Exception as e:
            return {"url": url, "status": "error", "error": str(e)}

    def _ocr_page_with_pymupdf(self, pdf_bytes: bytes, page_num: int) -> str:
        if not (HAS_PYMUPDF and HAS_OCR):
            return ""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page = doc[page_num - 1]
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return pytesseract.image_to_string(img)
        except Exception:
            return ""

    # ==================== ADVANCED ENTITY EXTRACTION ====================

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Advanced entity extraction.
        Tries spaCy first (much better quality). Falls back to regex if spaCy is unavailable.
        """
        nlp = self._get_spacy_nlp()
        if nlp:
            return self._extract_entities_spacy(text, nlp)
        else:
            return self._extract_entities_regex(text)

    def _extract_entities_spacy(self, text: str, nlp) -> Dict[str, List[str]]:
        """High-quality extraction using spaCy."""
        doc = nlp(text[:500000])  # safety limit
        entities = defaultdict(set)

        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "LOC", "DATE", "EMAIL"):
                entities[ent.label_.lower()].add(ent.text.strip())

        # Also catch emails with regex (spaCy is weak on emails)
        entities["email"].update(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))

        # Normalize keys
        normalized = {}
        for k, v in entities.items():
            key = {
                "person": "people",
                "org": "organizations",
                "gpe": "locations",
                "loc": "locations",
                "date": "dates",
                "email": "emails"
            }.get(k, k)
            normalized[key] = sorted(list(v))[:40]

        return normalized

    def _extract_entities_regex(self, text: str) -> Dict[str, List[str]]:
        """Fallback regex-based extraction (previous version improved)."""
        entities = defaultdict(set)
        entities["emails"].update(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text))
        entities["dates"].update(re.findall(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4})\b', text))
        entities["urls"].update(re.findall(r'https?://[^\s<>"\']+', text))
        org_pattern = r'\b([A-Z][a-zA-Z&]+(?:\s+[A-Z][a-zA-Z&]+){0,3})\s+(?:Inc|Corp|LLC|Ltd|Agency|Department|Ministry|Office|Committee|Force|Administration)\b'
        entities["organizations"].update(re.findall(org_pattern, text))
        return {k: sorted(list(v))[:30] for k, v in entities.items() if v}

    # ==================== LINK CLASSIFICATION ====================

    def classify_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, List[Dict]]:
        categories = defaultdict(list)
        for a in soup.find_all("a", href=True):
            href = urljoin(base_url, a["href"])
            text = a.get_text(strip=True)[:120]
            if not href or href.startswith(("#", "javascript:", "mailto:")):
                continue
            domain = urlparse(href).netloc.lower()
            entry = {"text": text, "url": href}
            if any(d in domain for d in [".gov", ".mil", "house.gov", "senate.gov", "whitehouse.gov"]):
                categories["primary_government"].append(entry)
            elif any(d in domain for d in ["rt.com", "tass.com", "globaltimes.cn", "presstv.ir", "cgtn.com"]):
                categories["adversarial_state_media"].append(entry)
            elif any(d in domain for d in ["twitter.com", "x.com", "facebook.com", "tiktok.com"]):
                categories["social_media"].append(entry)
            elif any(x in domain for x in ["reuters.com", "apnews.com", "bbc.com", "nytimes.com"]):
                categories["mainstream_media"].append(entry)
            else:
                categories["other"].append(entry)
        return dict(categories)

    def _clean_text(self, element) -> str:
        if element is None:
            return ""
        text = element.get_text(separator="\n", strip=True)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _extract_html_tables(self, soup: BeautifulSoup) -> List[Dict]:
        tables = []
        for table in soup.find_all("table"):
            rows = [[cell.get_text(strip=True) for cell in row.find_all(["th", "td"])] for row in table.find_all("tr")]
            if rows:
                tables.append({"headers": rows[0] if rows else [], "rows": rows[1:], "row_count": len(rows)})
        return tables


# ==================== STANDARDIZED CALLABLE HELPER ====================

def call_echo(url: str, **kwargs) -> Dict[str, Any]:
    """The standard helper function agents use to invoke ECHO."""
    parser = OSINTParser()
    return parser.parse(url, **kwargs)


if __name__ == "__main__":
    print("OSINT Parser v4 ready (with spaCy entity extraction when available).")