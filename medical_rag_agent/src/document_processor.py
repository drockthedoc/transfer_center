"""
Document processor for medical RAG system.

This module handles loading PDF documents and chunking them into nodes
with section-aware splitting for better context preservation.
"""
import logging
import re
from pathlib import Path
from typing import List, Optional

from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document, BaseNode, TextNode
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.utils import get_tokenizer

logger = logging.getLogger(__name__)

COMMON_SECTION_HEADERS = [
    "Abstract", "Introduction", "Background", "Methods", "Methodology", "Materials and Methods",
    "Results", "Findings", "Discussion", "Conclusion", "Summary", "Recommendations",
    "Patient History", "Clinical Presentation", "Symptoms", "Diagnosis", "Differential Diagnosis",
    "Treatment", "Treatment Plan", "Management", "Medication", "Dosage", "Administration",
    "Allergies", "Adverse Effects", "Contraindications",
    "Guidelines", "Clinical Guidelines", "Protocols", "Procedure",
    "Inclusion Criteria", "Exclusion Criteria",
    "Acknowledgements", "References", "Appendix"
]
HEADER_REGEX = re.compile(
    r"^(?:\d+\.\s*|\d+\.\d+\.\s*|[A-Za-z]\.\s*)?(" + "|".join(re.escape(header) for header in COMMON_SECTION_HEADERS) + r")\s*$",
    re.IGNORECASE | re.MULTILINE
)

def load_pdfs_from_folder(folder_path: str) -> List[Document]:
    """
    Load all PDF documents from a specified folder.
    
    Args:
        folder_path: Path to the folder containing PDF files.
        
    Returns:
        List of loaded Document objects.
        
    Raises:
        FileNotFoundError: If the folder does not exist.
        ValueError: If no PDF files are found in the folder.
    """
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"PDF folder not found: {folder_path}")
    
    reader = SimpleDirectoryReader(
        input_dir=str(folder),
        required_exts=[".pdf"]
    )
    
    documents = reader.load_data()
    if not documents:
        raise ValueError(f"No PDF documents found in {folder_path}")
    
    logger.info(f"Loaded {len(documents)} PDF documents from {folder_path}")
    return documents

def chunk_documents(
    documents: List[Document],
    default_chunk_size: int = 1024,
    default_chunk_overlap: int = 200,
    max_chars_per_section_chunk: int = 4000,
    min_section_content_length: int = 100
) -> List[BaseNode]:
    """
    Chunk documents into nodes with section-aware splitting.
    
    Attempts to split by section headers first, then falls back to sentence splitting
    if sections are too large or no headers are found.
    
    Args:
        documents: List of Document objects to chunk.
        default_chunk_size: Default chunk size for sentence splitting.
        default_chunk_overlap: Overlap for sentence splitting.
        max_chars_per_section_chunk: Max chars per section before splitting.
        min_section_content_length: Minimum content length for a chunk.
        
    Returns:
        List of chunked nodes with metadata.
        
    Raises:
        ValueError: If no valid nodes can be created from documents.
    """
    if not documents:
        raise ValueError("No documents provided for chunking")
    
    all_nodes: List[BaseNode] = []
    tokenizer = get_tokenizer()

    for doc_idx, doc in enumerate(documents):
        try:
            nodes_from_doc = _process_single_document(
                doc, tokenizer, default_chunk_size, default_chunk_overlap,
                max_chars_per_section_chunk, min_section_content_length
            )
            all_nodes.extend(nodes_from_doc)
        except Exception as e:
            logger.warning(f"Failed to process document {doc_idx}: {e}")
            continue
    
    if not all_nodes:
        raise ValueError("No valid nodes could be created from the provided documents")
    
    logger.info(f"Created {len(all_nodes)} nodes from {len(documents)} documents")
    return all_nodes


def _process_single_document(
    doc: Document,
    tokenizer,
    default_chunk_size: int,
    default_chunk_overlap: int,
    max_chars_per_section_chunk: int,
    min_section_content_length: int
) -> List[BaseNode]:
    """Process a single document into nodes."""
    doc_text = doc.text
    # Ensure doc.metadata is not None. SimpleDirectoryReader usually initializes it.
    original_doc_metadata = doc.metadata if doc.metadata is not None else {}
    
    # Create a base metadata dictionary for all nodes from this document
    base_node_metadata = {**original_doc_metadata}
    base_node_metadata["original_doc_id"] = doc.doc_id # Preserve original document id
    if 'file_name' not in base_node_metadata and 'file_path' in base_node_metadata:
        file_path = Path(base_node_metadata['file_path'])
        base_node_metadata['file_name'] = file_path.name

    nodes_from_doc: List[BaseNode] = []
    last_split_end = 0
    current_section_header = "Default" # For content before any recognized header

    matches = list(HEADER_REGEX.finditer(doc_text))

    if not matches: # No headers found
        if len(doc_text) > max_chars_per_section_chunk:
            splitter = SentenceSplitter(chunk_size=default_chunk_size, chunk_overlap=default_chunk_overlap, tokenizer=tokenizer)
            text_splits = splitter.split_text(doc_text)
            for i, split_text in enumerate(text_splits):
                node = TextNode(
                    text=split_text,
                    metadata={**base_node_metadata, "section": current_section_header, "chunk_in_section": i + 1}
                )
                nodes_from_doc.append(node)
        elif len(doc_text) >= min_section_content_length:
            node = TextNode(
                text=doc_text,
                metadata={**base_node_metadata, "section": current_section_header}
            )
            nodes_from_doc.append(node)
    else: # Headers found
        # Process content using the header-based logic from the prompt
        for i, match in enumerate(matches):
            section_start = match.start()
            header_name = match.group(1).strip()

            # Content before this header (belongs to previous section or is initial content)
            content_before_header = doc_text[last_split_end:section_start].strip()
            if len(content_before_header) >= min_section_content_length:
                if len(content_before_header) > max_chars_per_section_chunk:
                    splitter = SentenceSplitter(chunk_size=default_chunk_size, chunk_overlap=default_chunk_overlap, tokenizer=tokenizer)
                    text_splits = splitter.split_text(content_before_header)
                    for j, split_text in enumerate(text_splits):
                        node = TextNode(
                            text=split_text,
                            metadata={**base_node_metadata, "section": current_section_header, "chunk_in_section": j + 1}
                        )
                        nodes_from_doc.append(node)
                else:
                    node = TextNode(
                        text=content_before_header,
                        metadata={**base_node_metadata, "section": current_section_header}
                    )
                    nodes_from_doc.append(node)
            
            current_section_header = header_name # Update current section name for the next block of text
            last_split_end = match.end()

        # Content of the last section (after the last recognized header)
        last_section_content = doc_text[last_split_end:].strip()
        if len(last_section_content) >= min_section_content_length:
            if len(last_section_content) > max_chars_per_section_chunk:
                splitter = SentenceSplitter(chunk_size=default_chunk_size, chunk_overlap=default_chunk_overlap, tokenizer=tokenizer)
                text_splits = splitter.split_text(last_section_content)
                for k, split_text in enumerate(text_splits):
                    node = TextNode(
                        text=split_text,
                        metadata={**base_node_metadata, "section": current_section_header, "chunk_in_section": k + 1}
                    )
                    nodes_from_doc.append(node)
            else:
                node = TextNode(
                    text=last_section_content,
                    metadata={**base_node_metadata, "section": current_section_header}
                )
                nodes_from_doc.append(node)
    
    # Ensure all required metadata fields are set
    for i, node in enumerate(nodes_from_doc):
        node.id_ = f"{doc.doc_id}_node_{i}"
        node.metadata["full_doc_id"] = doc.doc_id
        node.metadata.setdefault("file_name", base_node_metadata.get("file_name", "unknown"))
        node.metadata.setdefault("section", current_section_header)
        
    return nodes_from_doc

if __name__ == '__main__':
    # Only for demonstration/testing, not for production use
    print("Document Processor Advanced Chunking Example")

    sample_text = """
    This is some introductory content before any formal section. It might be a preamble or abstract summary.
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

    1. Introduction
    This section introduces the main topic of the document. RAG systems are becoming increasingly important.
    The introduction might be long enough to be split by the sentence splitter if it exceeds max_chars_per_section_chunk.
    Let's add more text to ensure it potentially gets split. Introduction continued. Introduction again.

    Methods
    The methodology used in this study is described here. We used several techniques.
    First technique. Second technique. This section is shorter.

    Results
    The findings are presented in this part. We found that X leads to Y.
    This is a very important result and has many implications.

    A. Discussion
    We discuss the implications of our findings. This is a very long discussion section that will definitely exceed the max_chars_per_section_chunk.
    It needs to be split into multiple smaller chunks using the sentence splitter. We will elaborate on many points.
    Point one. Point two. Point three, which itself is a rather long sentence that could be split if the chunk size is small enough but here we care about section splitting first.
    Another sentence to make it longer. And another. This should be enough to trigger sentence splitting for this specific Discussion section.

    Conclusion
    This is the final conclusion.
    """
    
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent

    dummy_doc = Document(
        text=sample_text,
        metadata={
            "file_name": "dummy_test_document.txt", # Example metadata
            "file_path": str(project_root / "data" / "dummy_test_document.txt") # Example metadata
        }
    )
    dummy_doc.doc_id = "test_doc_001_simple_id" # Simulate a simple doc_id

    print(f"\nOriginal Document (ID: {dummy_doc.doc_id}, File: {dummy_doc.metadata.get('file_name')})")
    print("--------------------------------------------------")
    print(dummy_doc.text[:300] + "...") # Print an excerpt
    print("--------------------------------------------------")

    print("\nChunking document with new logic...")
    chunked_nodes = chunk_documents([dummy_doc], 
                                    default_chunk_size=200, 
                                    default_chunk_overlap=50,
                                    max_chars_per_section_chunk=300, # Reduced to ensure splitting for test
                                    min_section_content_length=30) # Reduced for test
    
    print(f"\nCreated {len(chunked_nodes)} nodes (chunks).")
    if chunked_nodes:
        for i, node in enumerate(chunked_nodes):
            print(f"\n  Node {i+1}: ID='{node.id_}'") # Quotes for clarity
            print(f"  Node Metadata: {node.metadata}") # Should include section, original_doc_id, full_doc_id
            print(f"  Node Text Excerpt: '{node.get_content()[:150].strip()}...'")
    else:
        print("No nodes created. Check chunking parameters and input text.")

    print("\nDocument Processor Advanced Chunking Example Finished.")
