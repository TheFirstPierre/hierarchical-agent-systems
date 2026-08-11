#!/usr/bin/env python3
"""
Demo script for the ECHO parser integration.

This shows how the ECHO agent would use BeautifulSoup in practice.
Run this to test the parser on real OSINT targets.
"""

from osint_parser import OSINTParser

def main():
    parser = OSINTParser()

    # Example 1: Primary government source (Burlison letter)
    print("=" * 60)
    print("EXAMPLE 1: Primary .gov source")
    print("=" * 60)
    url1 = "https://burlison.house.gov/media/press-releases/burlison-presses-mitre-answers-uap-records-ffrdc-accountability-and-compliance"
    result1 = parser.fetch_and_parse(url1)
    print(f"Title: {result1.get('title')}")
    print(f"Word count: {result1.get('word_count')}")
    print(f"Status: {result1.get('status')}")
    print("\nFirst 800 characters of clean text:\n")
    print(result1.get('main_text', '')[:800])
    print("\n")

    # Example 2: Adversarial state media (example RT article structure)
    print("=" * 60)
    print("EXAMPLE 2: How ECHO would handle adversarial media")
    print("=" * 60)
    print("In a real swarm run, BRAVO would send a URL like:")
    print("https://www.rt.com/news/640673-iran-targeted-us-base/")
    print("\nECHO would return clean article body with navigation/footers removed.\n")

    # Example 3: Table extraction (useful for reports)
    print("=" * 60)
    print("EXAMPLE 3: Table extraction capability")
    print("=" * 60)
    print("Parser can extract tables from government reports when needed.\n")

    print("Integration complete. ECHO is ready to be spawned as a subagent.")


if __name__ == "__main__":
    main()