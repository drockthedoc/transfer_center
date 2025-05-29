# Medical RAG Agent: Example Queries & Usage

This document provides example queries to demonstrate the capabilities of the Medical RAG Agent and what kind of responses or agent behavior to expect. These examples assume the agent is running via `scripts/run_agent_cli.py`, the RAG index has been built, and a local LLM server is operational.

## Example Queries

1.  **Basic Medical Information Retrieval (RAG Tool)**
    *   **Query:** `"What are the standard treatment protocols for community-acquired pneumonia in adults?"`
    *   **Expected Agent Behavior:**
        *   The agent should identify that this query requires factual medical information.
        *   It should select the `MedicalInformationRetriever` tool.
        *   The tool will query the vector index of medical documents.
        *   The agent should synthesize the retrieved information from the documents (e.g., excerpts from guidelines or textbooks) into a concise answer.
        *   The response should ideally cite the source documents or sections if that information is available in the retrieved nodes' metadata (e.g., "According to 'guideline_abc.pdf', section 'Treatment'...").

2.  **Medical Information Retrieval with Section Filter (RAG Tool)**
    *   **Query:** `"Find information on the side effects of Metformin, specifically in the 'Adverse Effects' or 'Side Effects' section of the documents."`
    *   **Expected Agent Behavior:**
        *   The agent should recognize the need for specific information and the hint to filter by section.
        *   It should use the `MedicalInformationRetriever` tool, passing both the query about Metformin's side effects and `section_filter="Adverse Effects"` (or a similar relevant section name if "Side Effects" is more common in the indexed data).
        *   The RAG tool will then attempt to retrieve chunks of text primarily from sections matching the filter.
        *   The agent's response will be based on the filtered retrieved context, focusing on side effects as found in those specific sections.

3.  **Complex Scenario Involving Multiple Tools (Patient Transfer Decision Support)**
    *   **Query:** `"I have a 55-year-old patient, John Doe, currently at 'Community Clinic' (address: 123 Main St, Anytown) who is presenting with symptoms of an acute ischemic stroke, onset approximately 1.5 hours ago. He needs urgent evaluation for thrombectomy. Can you help determine the best receiving facility? Consider University Hospital and City General Hospital."`
    *   **Expected Agent Behavior:**
        *   The agent should understand this is a complex patient transfer scenario.
        *   **Step 1 (Assess Need & Facility Capabilities):** It might first use the `FacilityCapabilitiesTool` to check if "University Hospital" and "City General Hospital" are comprehensive stroke centers and are currently accepting stroke patients.
            *   Example internal tool call: `FacilityCapabilitiesTool(facility_query="University Hospital capabilities for acute ischemic stroke")` and `FacilityCapabilitiesTool(facility_query="City General Hospital capabilities for acute ischemic stroke and current stroke diversion status")`.
        *   **Step 2 (Geographic Context):** For facilities identified as appropriate, it should use the `GeographicContextTool` to check travel times from "Community Clinic" (or "123 Main St, Anytown").
            *   Example internal tool call: `GeographicContextTool(location_query="travel time from 123 Main St, Anytown to University Hospital")` and `GeographicContextTool(location_query="travel time from 123 Main St, Anytown to City General Hospital")`.
        *   **Step 3 (Optional - RAG for Guidelines):** If needed, it might consult the `MedicalInformationRetriever` for stroke transfer guidelines, though the primary decision here relies on facility capability and time.
            *   Example internal tool call: `MedicalInformationRetriever(query="guidelines for inter-facility transfer of acute stroke patients")`
        *   **Step 4 (Synthesize & Recommend):** The agent should synthesize the information (e.g., "University Hospital is a comprehensive stroke center, 20 minutes away. City General is also a stroke center but is on diversion / 45 minutes away.").
        *   The final response to the user should be a recommendation with justification, e.g., "Based on current capabilities and estimated travel time, University Hospital is the recommended receiving facility for John Doe. It is a comprehensive stroke center, approximately 20 minutes away, and is currently accepting stroke patients. City General Hospital is further/on diversion."

4.  **Query Requiring Only Facility Information (FacilityCapabilitiesTool)**
    *   **Query:** `"What are the pediatric ICU capabilities at University Hospital?"`
    *   **Expected Agent Behavior:**
        *   The agent should identify this as a query about specific facility capabilities.
        *   It should use the `FacilityCapabilitiesTool`.
        *   Example internal tool call: `FacilityCapabilitiesTool(facility_query="University Hospital pediatric ICU capabilities")`.
        *   The agent should provide the (mocked) information about the PICU at University Hospital.

5.  **Query Requiring Only Geographic Information (GeographicContextTool)**
    *   **Query:** `"What's the weather like at City General Hospital right now?"`
    *   **Expected Agent Behavior:**
        *   The agent should recognize this as a query for geographic/environmental context.
        *   It should use the `GeographicContextTool`.
        *   Example internal tool call: `GeographicContextTool(location_query="weather at City General Hospital")`.
        *   The agent should provide the (mocked) weather information.

## Notes on Mock Tools

*   The `GeographicContextTool` and `FacilityCapabilitiesTool` in the current implementation provide **mock/simulated** responses. In a real-world deployment, these would need to be connected to live APIs or real-time data sources.
*   The agent's ability to perfectly parse complex queries into multiple tool calls and synthesize them depends heavily on the underlying LLM's capabilities and the clarity of the prompts and tool descriptions. The examples above illustrate the *intended* behavior.

These examples should help in understanding how to interact with the agent and the types of tasks it's designed to assist with.
