import re
from typing import Union, Any
from bisect import insort_left
try:
    from spacy.tokens.doc import Doc
except ImportError:
    Doc = Any
    


def get_split_offsets(text: str, delimiters: list):
    start_char = 0
    start_chars = []
    split_pattern = "|".join([re.escape(d) for d in delimiters])
    delimiter_len = len(delimiters[0])
    assert all(len(d) == delimiter_len for d in delimiters[1:])
    for p in re.split(split_pattern, text):
        start_chars.append(start_char)
        start_char += len(p) + delimiter_len

    return start_chars


def get_semantic_bounderies(
        doc: Union[Doc, str], 
        ordered_semantic_chunk_types=["paragraphs", "sentences", "subparts", "tokens"], 
        sentence_boundary_chars=['. ', '? ', '! '],
        token_boundary_chars = [' '],
    ):
    """
    Returns the character offsets of the semantic boundaries of the given Doc or str.
    
    The boundary types must be ordered from larger semantic chunks (such as paragraphs) 
    to smaller ones (such as sentences). The returned boundaries of more abstract chunks 
    are subsets of the boundaries of more concrete chunks.

    Args:
        doc (Doc): spaCy Doc object (that includes sentence boundary information).
        ordered_semantic_chunk_types (list[str], optional): The ordered list of semantic chunk types. Defaults to ["paragraphs", "sentences", "subparts", "tokens"].
        sentence_boundary_chars (list[str], optional): The characters to use as sentence boundaries if spaCy is not available. Defaults to ['. ', '? ', '! '].
        token_boundary_chars (list[str], optional): The characters to use as token boundaries if spaCy is not available. Defaults to [' '].

    Returns:
        tuple[tuple[int]]: The character offsets of the semantic boundaries.
    """

    if type(doc) == str:
        # spaCy annotations not available. 
        # Use simple fallback pattern to get sentence and token boundaries.
        text = doc
        sentence_start_chars = get_split_offsets(text, sentence_boundary_chars)
        token_start_chars = get_split_offsets(text, token_boundary_chars)
    else:
        # Use spaCy annotations for sentence and token boundaries.
        text = doc.text
        sentence_start_chars = [sent.start_char for sent in doc.sents]
        token_start_chars = [token.idx for token in doc]

    boundaries = []
    for chunk_type in ordered_semantic_chunk_types:
        if chunk_type == "paragraphs":
            # Paragraph boundaries.
            paragraph_start_chars = get_split_offsets(text, ['\n\n'])
            boundaries.append(paragraph_start_chars)
        elif chunk_type == "sentences":
            # Sentence boundaries.            
            boundaries.append(sentence_start_chars)
        elif chunk_type == "subparts":
            # Subpart boundaries.
            subpart_start_chars = get_split_offsets(text, [': ', '; ', ', '])
            boundaries.append(subpart_start_chars)
        elif chunk_type == "tokens":
            # Token boundaries.            
            boundaries.append(token_start_chars)
        else:
            raise ValueError(f"Unknown chunk type: {chunk_type}")
        
    # Make sure that the boundaries of more abstract chunks 
    # are subsets of the boundaries of more concrete chunks.
    for i in range(0, len(boundaries)-1):
        for j in range(i+1, len(boundaries)):
            for b in boundaries[i]:
                if b not in boundaries[j]:
                    insort_left(boundaries[j], b)

    # We return tuples as they are hashable which is required for caching.
    return tuple(tuple(b) for b in boundaries)


def adapt_semantic_boundaries(boundaries, chunk_char_offset: int, chunk_len: int, added_chars_len: int=0, added_chars_end_pos: int=0):
    """
    Adapt semantic boundaries to chunk of original text and or added characters.
    
    Semantic boundaries outside of the chunk are removed.
    The characters are assumed to be all added at the same position and end on added_chars_end_pos.
    
    Args:
        boundaries (tuple[tuple[int]]): The character offsets of the semantic boundaries.
        chunk_char_offset (int): The character offset of the chunk with respect to the original text.
        chunk_len (int): The length of the chunk.
        added_chars_len (int, optional): The number of added characters. Defaults to 0.
        added_chars_end_pos (int, optional): The end position of the added characters. Defaults to 0.                
    """
    boundaries_ = []
    for i in range(0, len(boundaries)):
        boundaries_.append([])
        for b in boundaries[i]:
            new_b = b - chunk_char_offset
            if new_b >= added_chars_end_pos:
                # Adapt offset to added symbols.
                new_b += added_chars_len                                        
            if new_b >= 0 and new_b <= chunk_len:
                # Inside chunk. Add.
                boundaries_[i].append(new_b)
            elif new_b > chunk_len:
                # Outside of chunk.
                break
                    
    # Add start boundary if not present.
    for b in boundaries_:
        if len(b) == 0 or b[0] != 0:
            b.insert(0, 0)                    

    return tuple(tuple(b) for b in boundaries_)