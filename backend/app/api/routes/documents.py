from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Depends, Query, status
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentMetadata,
    DocumentDeleteResponse
)
from app.schemas.processing import (
    DocumentProcessingResponse,
    DocumentProcessingStatusResponse,
    DocumentChunk
)
from app.schemas.universal_pdf import ProcessedPage
from app.schemas.search import IndexDocumentResponse, IndexStatusResponse
from app.services.document_service import document_service
from app.services.processing_service import processing_service
from app.services.vector.indexing_service import indexing_service
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    """
    Validates, uploads, and stores a PDF document file with user ownership.
    Enforces PDF MIME type, magic bytes verification, and maximum upload size limit.
    """
    return await document_service.save_uploaded_file(file, user_id=user_id)

@router.get("", response_model=List[DocumentMetadata], status_code=status.HTTP_200_OK)
async def list_documents(
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves metadata for all uploaded documents accessible to the user.
    """
    return document_service.list_documents(user_id=user_id)

@router.get("/{document_id}", response_model=DocumentMetadata, status_code=status.HTTP_200_OK)
async def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves metadata for a specific uploaded document by ID.
    """
    return document_service.get_document(document_id)

@router.delete("/{document_id}", response_model=DocumentDeleteResponse, status_code=status.HTTP_200_OK)
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Safely deletes a document file, its metadata, processed chunk artifacts, and vector index.
    """
    return document_service.delete_document(document_id, user_id=user_id)

@router.post("/{document_id}/process", response_model=DocumentProcessingResponse, status_code=status.HTTP_200_OK)
async def process_document(document_id: str):
    """
    Executes Phase 3 PDF processing pipeline:
    1. Extracts text page-by-page preserving 1-based page numbers.
    2. Cleans text preserving CLI commands, error codes, and technical metrics.
    3. Splits text using LangChain RecursiveCharacterTextSplitter.
    4. Persists chunks to backend/data/processed/{document_id}.json.
    """
    return await processing_service.process_document(document_id)

@router.get("/{document_id}/processing-status", response_model=DocumentProcessingStatusResponse, status_code=status.HTTP_200_OK)
async def get_processing_status(document_id: str):
    """
    Retrieves the current processing state ('uploaded', 'processing', 'processed', 'failed')
    and extraction metrics for a document.
    """
    return processing_service.get_processing_status(document_id)

@router.get("/{document_id}/chunks", response_model=List[DocumentChunk], status_code=status.HTTP_200_OK)
async def get_document_chunks(document_id: str):
    """
    Retrieves all generated chunks for a processed document.
    """
    return processing_service.get_processed_chunks(document_id)

@router.get("/{document_id}/pages", response_model=List[ProcessedPage], status_code=status.HTTP_200_OK)
async def get_document_pages(document_id: str):
    """
    Retrieves all processed pages, headings, tables, and extraction metadata for a processed document.
    """
    return processing_service.get_processed_pages(document_id)

@router.post("/{document_id}/index", response_model=IndexDocumentResponse, status_code=status.HTTP_200_OK)
async def index_document(
    document_id: str,
    reindex: bool = Query(False, description="Force reindexing if already indexed"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Indexes document into ChromaDB (vector embeddings) and BM25 (keyword index).
    Enforces user isolation and prevents unauthorized document indexing.
    """
    return await indexing_service.index_document(document_id=document_id, user_id=user_id, reindex=reindex)

@router.get("/{document_id}/index-status", response_model=IndexStatusResponse, status_code=status.HTTP_200_OK)
async def get_index_status(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves the indexing status and indexed chunk count for a document in ChromaDB.
    """
    return indexing_service.get_index_status(document_id=document_id, user_id=user_id)

@router.delete("/{document_id}/index", status_code=status.HTTP_200_OK)
async def delete_document_index(
    document_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Deletes the document's vector embeddings from ChromaDB and purges its BM25 index.
    """
    return indexing_service.delete_index(document_id=document_id, user_id=user_id)
