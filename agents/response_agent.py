__all__ = ["ResponseAgent"]

from xyz.node.agent import Agent
from xyz.utils.llm.openai_client import OpenAIClient
from xyz.node.basic.llm_agent import LLMAgent
from tools.json_store import local_read
import concurrent
import sys

class ResponseAgent(Agent):

    def __init__(self, llm_client: OpenAIClient):
        super().__init__()

        self.set_information(
            {
                "type": "function",
                "function": {
                    "name": "ResponseAgent",
                    "description": "This function can analyse and produce a concise response to an original query based on sources provided. To be called ONLY ONCE.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The original query input by the user at the beginning."},
                        },
                        "required": ["query"],
                    },
                }
            }
        )
        self.input_type = "str"
        self.output_type = "str"

        self.llm_response = LLMAgent(template=response_prompt, llm_client=llm_client, stream=True)

    def flowing(self, query: str, timeout=10):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.llm_response, query=query, sources=local_read())
            try:
                result = future.result(timeout=timeout)
                return result
            except concurrent.futures.TimeoutError:
                print("The operation timed out. Terminating the program.")
                sys.exit(1)

        

response_prompt = [
    {
        "role": "system",
        "content": """

Note to AI Manager:
    - Execute the Response Agent only after gathering all sources through multiple calls by the Search Agent on each sub-query.
    - Do not call the Response Agent repeatedly. It should run only once.
    - Run the Interaction Agent after the Response Agent completes.

As a response agent, your task is to respond to the original query based on the extracted text content from the refined search results. Follow these steps to ensure a concises and accurate response.

Instructions for Responding to the Original Query:

1. **Understand the Query:**
    - Read the user's original query carefully.
    - Identify the core question and key details.

2. **Review and Extract Key Points from Sources:**
    - Examine provided sources (each with 'link' and 'text' keys).
    - Extract information directly answering the user's query.
    - Ignore extraneous or unrelated content.

3. **Organize Extracted Information:**
    - Group related information.
    - Ensure logical flow and comprehensive coverage of the query.

4. **Compose a Focused Answer:**
    - Write a concise and clear response.
    - Integrate extracted information smoothly.
    - Provide short, accurate points instead of a long report.

5. **Cite Sources Appropriately:**
    - Cite each piece of information in the format (source: <full url>).

6. **Format the Final Answer:**
    - Ensure readability with bullet points or headings if necessary.
    - Keep the response directly related to the query without unnecessary details.

**Emphasis:**
    - Focus on core information needed to answer the query.
    - Avoid irrelevant or redundant information.
    - If an answer cannot be provided, inform the user.

""" },
    {
        "role": "user",
        "content": """
Based on the following sources, respond to the original query comprehensively and cite each source for the information provided.
Remember to use the original query not the sub-queries.
**Original Query:** {query}

**Sources:**
{sources}

The final output should address the query and provide citations for each piece of information strictly in the format (source: <full url>). Please do not include the steps.
Ensure that the link to the source is included in the citation.
"""
    }
]