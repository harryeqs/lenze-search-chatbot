__all__ = ["SearchAgent"]

from xyz.node.agent import Agent
from xyz.utils.llm.openai_client import OpenAIClient
from xyz.node.basic.llm_agent import LLMAgent
from tools.google_search import google_search
from tools.web_scraper import scrape_urls
from tools.source_store import local_store
import json
import time

class SearchAgent(Agent):

    def __init__(self, llm_client: OpenAIClient):
        super().__init__()

        self.set_information(
            {
                "type": "function",
                "function": {
                    "name": "SearchAgent",
                    "description": "This agent can search across the internet on a sub-query provided by the user by following the searching process and return a list of raw source data. To be called only once.",

                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sub_queries": {"type": "array", 
                                            "items": {"type": "string"}, 
                                            "description": "The sub-queries here which need help. It should passed to the next agent it its original form. To be called ONLY ONCE."},
                        },
                        "required": ["sub_queries"],
                    },
                }
            }
        )
        self.input_type = "str"
        self.output_type = "list"

        self.opt_agent = LLMAgent(template=opt_prompt, llm_client=llm_client, stream=False)

    def flowing(self, sub_queries: list):
        
        # Initialise
        all_results = []
        sources = []
        
        for sub_query in sub_queries:
            # Generate optimised query
            opt_query = self.opt_agent(sub_query=sub_query)
            yield (f'\n**Optimized query:** \n {opt_query}' +
                f'\n --------------------')
        
            # Search using optimised query
            results = json.loads(google_search(opt_query))
            yield (f'\n**Search results:** \n {results}' +
                f'\n --------------------')
            all_results += results

            # scrape URLs contained in search results and returned compiled sources

        yield ('\n**Scraping texts from results.**\n')
        start_time = time.time()
        urls = [result['link'] for result in all_results]
        scraped_texts = scrape_urls(urls)
        end_time = time.time()
        time_taken = f"Scraping took {end_time - start_time:.4f} seconds\n"
        yield(time_taken)

        for result, text in zip(all_results, scraped_texts):
            result['text'] = text
            sources.append(result)
        
        local_store(sources)
        yield ('SearchAgent completes job.')
    


opt_prompt = [
    {
        "role": "system",
        "content": """
As an intelligent search optimization agent, your task is to refine and optimize a given query to achieve the most accurate and relevant results on Google. Follow these steps to enhance the query and ensure precision:

**Note to AI Manager:**
    - Remember to mark the SearchAgent's work as completed.
    - After the SearchAgent completes, run the ResponseAgent only once.

Steps to Optimize the Query:

1. **Understand the Query:**
   - Analyze the initial query to grasp the key concepts and the user’s intent.
   - Identify the main topic, specific details, and any implicit or explicit requirements.

2. **Refine Keywords:**
   - Break down the query into essential keywords.
   - Remove command words like 'compare', 'list'.
   - Add or modify keywords to include synonyms, related terms, and variations that capture the full scope of the user’s intent.

3. **Use Operators:**
   - Utilize Google search operators to narrow down the results only when necessary:
     - Use the minus sign (-) to exclude unwanted terms.
     - Use the filetype: operator to find specific types of files (e.g., PDFs, DOCs).
     - Use the intitle (only when necessary): operator to ensure the main keyword appears in the title of the results.
   - *Important*: DO NOT use quotation marks or sites.

4. **Incorporate Filters:**
   - Add filters like location, date range, or language to make the search results more relevant.
   - For example, add “2024” to find the most recent information or specify “site:.edu” or "site:.ac.*" for educational resources.

5. **Formulate the Optimized Query:**
   - Combine the refined keywords, operators, and filters into a coherent and effective search query.
   - Ensure the query is directly aligned with the user’s intent and avoids generating random or irrelevant results.

Goal:
Create a search query that maximizes accuracy and relevance, aligning with the user’s intent and providing the best possible results.
""" },
    {
        "role": "user",
        "content": """
Now, apply these steps to optimize the following query:

**Sub-query:** {sub_query}

Do not inclue the steps in the final output. The final output should be a single string of optimised query.
"""
    }
]