import os
import re
from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import Document, BaseNode, TextNode
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.utils import get_tokenizer
from typing import List
from pathlib import Path # Added for __main__ example

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
    Loads all PDF documents from a specified folder.
    """
    reader = SimpleDirectoryReader(
        input_dir=folder_path,
        required_exts=[".pdf"]
    )
    documents = reader.load_data()
    return documents

def chunk_documents(
    documents: list[Document],
    default_chunk_size: int = 1024,
    default_chunk_overlap: int = 200,
    max_chars_per_section_chunk: int = 4000,
    min_section_content_length: int = 100
) -> list[BaseNode]:
    all_nodes: list[BaseNode] = []
    tokenizer = get_tokenizer()

    for doc_idx, doc in enumerate(documents):
        doc_text = doc.text
        # Ensure doc.metadata is not None. SimpleDirectoryReader usually initializes it.
        original_doc_metadata = doc.metadata if doc.metadata is not None else {}
        
        # Create a base metadata dictionary for all nodes from this document
        base_node_metadata = {**original_doc_metadata}
        base_node_metadata["original_doc_id"] = doc.doc_id # Preserve original document id
        if 'file_name' not in base_node_metadata and 'file_path' in base_node_metadata:
            base_node_metadata['file_name'] = os.path.basename(base_node_metadata['file_path'])

        nodes_from_doc: list[BaseNode] = []
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
        
        # Assign unique IDs to nodes
        for i, node in enumerate(nodes_from_doc):
            node.id_ = f"{doc.doc_id}_node_{i}" # Ensure unique node IDs
            node.metadata["full_doc_id"] = doc.doc_id # Keep original doc id if needed later
        all_nodes.extend(nodes_from_doc)
            
    return all_nodes

if __name__ == '__main__':
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
    
    current_script_path = Path(os.path.abspath(__file__))
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
