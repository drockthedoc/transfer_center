import argparse
import os
import sys

# Ensure the project root is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.rag_components import get_exclusion_criteria_retriever

# Define hospital IDs for easy reference in the test script
# These should match the 'campus_id' values used in your system
# and stored in the vector store metadata.
AVAILABLE_HOSPITAL_IDS = [
    "TCH_MAIN_TMC",
    "TCH_WOODLANDS",
    "TCH_WEST_KATY",
    "TCH_PAVILION_WOMEN",
    "TCH_NORTH_AUSTIN",
    "community_sites_general_info" # If this is a valid filterable ID
]

def test_retrieval(query: str, hospital_id: str = None, top_k: int = 5):
    """
    Tests RAG retrieval with an optional hospital_id filter.
    """
    print(f"\n--- Testing RAG Retrieval ---")
    print(f"Query: '{query}'")
    if hospital_id:
        print(f"Filtering for Hospital ID: {hospital_id}")
    print(f"Retrieving top {top_k} results.")

    retriever_instance = get_exclusion_criteria_retriever()

    if not retriever_instance:
        print("Failed to initialize retriever. Ensure vector store exists.")
        return

    search_kwargs = {}
    if hospital_id:
        # FAISS metadata filtering expects a dictionary for the 'filter' kwarg.
        # This assumes your metadata field is named 'hospital_id'.
        search_kwargs['filter'] = {'hospital_id': hospital_id}
    
    # Update retriever with search_kwargs if hospital_id is specified
    if hospital_id:
        # Re-create the retriever with the filter. 
        # The as_retriever() method can take search_kwargs directly.
        # We need to access the base vector_store from the retriever if it's already created,
        # or ideally, get the vector_store first and then call as_retriever() with kwargs.
        # For simplicity here, we'll assume get_exclusion_criteria_retriever() returns the vector_store
        # and then we call as_retriever on it. 
        # Let's adjust get_exclusion_criteria_retriever or how we use it.
        
        # Modification: Assume get_exclusion_criteria_retriever() returns the vector_store itself
        # or we modify it to do so, or we have a separate function to get the store.
        # For now, let's assume we can pass search_kwargs to the existing retriever setup.
        # The .as_retriever() method can be called with search_kwargs.
        # If get_exclusion_criteria_retriever() returns a configured retriever, we might need to adjust it
        # or create a new retriever instance with the filter.

        # Let's assume get_exclusion_criteria_retriever() returns the vector_store object
        vector_store = get_exclusion_criteria_retriever() # This should be the store, not retriever
        if not vector_store: # Check if vector_store is None
             print("Failed to load vector store from get_exclusion_criteria_retriever. Exiting.")
             return
        
        # Check if it's a retriever already or a vector store
        if hasattr(vector_store, 'as_retriever'): # It's a vector store
            retriever_instance = vector_store.as_retriever(search_kwargs=search_kwargs)
        else: # It's already a retriever, this approach might not work directly for filtering after creation
            print("Warning: Retriever already configured. Filtering might not apply as expected.")
            # Attempt to update search_kwargs if possible (some retriever types allow this)
            if hasattr(retriever_instance, 'search_kwargs'):
                 retriever_instance.search_kwargs = search_kwargs
            else:
                print("Cannot dynamically update search_kwargs on this retriever type after instantiation.")
                print("Consider modifying get_exclusion_criteria_retriever to accept search_kwargs or return the vector_store.")
                # For now, we will proceed without the filter if this path is hit, or you can choose to exit.

    # Set k for the number of results
    if hasattr(retriever_instance, 'k'): # For some retriever types
        retriever_instance.k = top_k
    elif hasattr(retriever_instance, 'search_kwargs') and 'k' not in retriever_instance.search_kwargs:
        retriever_instance.search_kwargs['k'] = top_k
    else: # Default if k cannot be set directly
        print(f"Note: Using default k or pre-set k for retriever. Requested top_k={top_k}")


    try:
        results = retriever_instance.invoke(query)
        
        if results:
            print(f"\nFound {len(results)} documents:")
            for i, doc in enumerate(results):
                print(f"  Result {i+1}: Score: {doc.metadata.get('_score', 'N/A')}") # FAISS might not populate _score this way with invoke
                print(f"    Content: {doc.page_content[:200]}...")
                print(f"    Metadata: {doc.metadata}")
        else:
            print("No documents found for the given query and filter.")
            
    except Exception as e:
        print(f"An error occurred during retrieval: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test RAG retrieval for exclusion criteria.")
    parser.add_argument("query", type=str, help="The query string to search for.")
    parser.add_argument("--hospital_id", type=str, choices=AVAILABLE_HOSPITAL_IDS, 
                        help="Optional hospital ID to filter results.")
    parser.add_argument("--top_k", type=int, default=3, help="Number of top results to retrieve.")

    args = parser.parse_args()

    # Check if get_exclusion_criteria_retriever returns a vector_store or a retriever
    # For the filtering to work best, it should return the vector_store, then we call .as_retriever()
    # The current rag_components.get_exclusion_criteria_retriever() returns retriever_instance = vector_store.as_retriever()
    # This means we cannot easily set search_kwargs for filtering after it's created.
    # For this test script to work with filtering, rag_components.py should be modified
    # to return the vector_store, or accept search_kwargs.
    
    # TEMPORARY WORKAROUND: We will call get_exclusion_criteria_retriever() and if a hospital_id is provided,
    # we will essentially re-create the retriever with the filter. This is not ideal but will work for testing.
    # A better solution is to refactor get_exclusion_criteria_retriever.

    if args.hospital_id:
        print(f"Note: Applying filter for hospital_id: {args.hospital_id}. This test script re-initializes the retriever for filtering.")
        # This part of the code in main will handle the recreation of the retriever with filter
        base_retriever = get_exclusion_criteria_retriever()
        if base_retriever and hasattr(base_retriever, 'vectorstore'):
            filtered_retriever = base_retriever.vectorstore.as_retriever(
                search_kwargs={'filter': {'hospital_id': args.hospital_id}}
            )
            # Update search_kwargs for 'k' as well for the new retriever
            if hasattr(filtered_retriever, 'search_kwargs') and 'k' not in filtered_retriever.search_kwargs:
                 filtered_retriever.search_kwargs['k'] = args.top_k
            elif hasattr(filtered_retriever, 'k'): # for some retriever types
                 filtered_retriever.k = args.top_k
            
            retriever_to_use = filtered_retriever
            print(f"Using filtered retriever for hospital_id: {args.hospital_id}, top_k: {args.top_k}")
        else:
            print("Could not get base vectorstore from retriever to apply filter. Running unfiltered.")
            retriever_to_use = get_exclusion_criteria_retriever()
            if retriever_to_use and hasattr(retriever_to_use, 'search_kwargs') and 'k' not in retriever_to_use.search_kwargs:
                retriever_to_use.search_kwargs['k'] = args.top_k
            elif retriever_to_use and hasattr(retriever_to_use, 'k'): # for some retriever types
                retriever_to_use.k = args.top_k
            print(f"Using unfiltered retriever, top_k: {args.top_k}")

    else:
        retriever_to_use = get_exclusion_criteria_retriever()
        if retriever_to_use and hasattr(retriever_to_use, 'search_kwargs') and 'k' not in retriever_to_use.search_kwargs:
            retriever_to_use.search_kwargs['k'] = args.top_k
        elif retriever_to_use and hasattr(retriever_to_use, 'k'): # for some retriever types
            retriever_to_use.k = args.top_k
        print(f"Using unfiltered retriever, top_k: {args.top_k}")

    if retriever_to_use:
        try:
            results = retriever_to_use.invoke(args.query)
            if results:
                print(f"\nFound {len(results)} documents for query '{args.query}':")
                for i, doc in enumerate(results):
                    # FAISS .invoke() might not directly provide scores in metadata like similarity_search_with_score
                    # We'll print what's available.
                    print(f"  Result {i+1}: Content: {doc.page_content[:200]}...")
                    print(f"    Metadata: {doc.metadata}")
            else:
                print("No documents found for the given query and filter.")
        except Exception as e:
            print(f"An error occurred during retrieval: {e}")
    else:
        print("Failed to initialize retriever for the test.")

    print("\n--- Test Complete ---")
