"""Earnings Said vs. Filed: compare what a company said with what it filed.

Layers: fetch -> normalize -> compute -> detect -> write -> validate -> render.
Numbers are produced only by code. Prose uses {placeholders} that the
renderer fills from computed values, so the model never types a number.
"""
__version__ = "0.1.0"
