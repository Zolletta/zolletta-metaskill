"""Grice maxims — deterministic documentation scoring.

The scanners here score project documentation against Grice's Quantity,
Quality, Relation and Manner maxims, normalized against the corpus itself. They
read the same corpus as the documentor tools and print a report; nothing is
rewritten and nothing fails a build.
"""
