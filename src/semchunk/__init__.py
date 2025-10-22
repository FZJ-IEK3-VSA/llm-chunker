"""A fast, lightweight and easy-to-use Python library for splitting text into semantically meaningful chunks."""

from .semchunk import chunk, Chunker, chunkerify, get_single_centered_chunk
from .boundaries import get_semantic_bounderies, adapt_semantic_boundaries