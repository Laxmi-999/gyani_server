from pydantic import BaseModel, ConfigDict
from typing import Optional,List,Dict,Any
from enum import Enum



class SearchType(str, Enum):
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class NoteSearchResult(BaseModel):
    id:int
    title:Optional[str] = None
    content: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    auto_tags: Optional[List[str]] = None
    similarity_score:float

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    query: str
    search_type:SearchType
    total: int
    results: List[NoteSearchResult]