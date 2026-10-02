from pydantic import BaseModel
import re

class ValidationResult(BaseModel):
    valid_citations: list[int]
    invalid_citations: list[int]
    is_valid: bool

def validate_citations(response_text: str, retrieved_chunk_ids: list[str]) -> ValidationResult:
    citations = [int(m) for m in re.findall(r'\[(\d+)\]', response_text)]
    valid = []
    invalid = []
    for c in citations:
        if 1 <= c <= len(retrieved_chunk_ids):
            valid.append(c)
        else:
            invalid.append(c)
    return ValidationResult(valid_citations=valid, invalid_citations=invalid, is_valid=len(invalid)==0)
