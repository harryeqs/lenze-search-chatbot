from tools.google_search import google_scrape_search, get_urls
from tools.source_store import local_store, local_read, generate_embedding, find_most_relevant_sources
from tools.text_extraction import process_urls_async
from datetime import date
from .base.web_search_prompts import complete_template, ANALYZE_PROMPT, ANSWER_PROMPT, INTERACTION_PROPMT
from .base.base_agent import BaseAgent
from typing import AsyncGenerator
import numpy as np
import time
import json
import ast

__all__ = ["WebSearchAgent"]

class WebSearchAgent(BaseAgent):     

    def analyze(self):
        current_date = date.today()
        values = {'query': self.query, 'current_date': current_date, 'search_history': self.search_history}
        message = complete_template(ANALYZE_PROMPT, values)
        analysis = self._get_response(message)
        analysis = json.loads(analysis)
        need_search, refined_query = analysis["need_search"], analysis["refined_query"]
        return need_search, refined_query
  
    async def search(self, refiend_query: str):

        sources = []
        urls = get_urls(google_scrape_search(refiend_query))
        urls = list(set(urls))

        scraped_texts = await process_urls_async(urls)
        sources = [{'link': url, 'text': text} for url, text in zip(urls, scraped_texts)]
        
        local_store(sources)

    def find_sources(self):
        query_embedding = generate_embedding(self.query)
        sources = local_read()
        most_relevant_sources = find_most_relevant_sources(np.frombuffer(query_embedding, dtype=np.float32), sources)
        return most_relevant_sources
    
    def answer(self, most_relevant_sources):
        values = {'sources': most_relevant_sources, 'query': self.query}
        message = complete_template(ANSWER_PROMPT, values)
    
        print('\n=====Answer=====\n')
        response = self._get_response(message)
        self.response = response

        self.search_history.append({'query:': self.query, 'response': self.response})
        print(response)
        return self.response
    
    async def answer_stream(self, most_relevant_sources) -> AsyncGenerator[str, None]:
        values = {'sources': most_relevant_sources, 'query': self.query}
        message = complete_template(ANSWER_PROMPT, values)

        full_response = ""

        print('\n=====Answer=====\n')
        async for content in self._async_generator_wrapper(self._get_response_stream(message)):
            full_response += content
            print(content, end='', flush=True)
            formatted_content = content.replace('\n', '\ndata: ')
            yield f"data: {formatted_content}\n\n"

        self.search_history.append({'query:': self.query, 'response': full_response})

    def interact(self):

        values = {'query': self.query, 'response': self.response}
        message = complete_template(INTERACTION_PROPMT, values)

        print('\n\n=====Related=====\n')
        related_queries = self._get_response(message)
        related = ast.literal_eval(related_queries)
        print(related)
        return related

    async def run(self, query): # for testing

            self.query = query
            start_time = time.time()
                
            need_search, refined_query = self.analyze()
                
            if need_search:
                await self.search(refined_query)
            
            most_relevant_sources = self.find_sources()
            answer, related = self.answer(most_relevant_sources), self.interact()

            end_time = time.time()
            time_taken = f'**Response generated in {end_time-start_time:.4f} seconds**'
            print(f'\n{time_taken}\n')

            return answer, related
        