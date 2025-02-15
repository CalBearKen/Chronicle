from typing import List, Dict
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os
from dotenv import load_dotenv
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

class NewsBot:
    def __init__(self):
        self.qdrant = QdrantClient("qdrant", port=6333)
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.openai = OpenAI(
            base_url="http://llm:8000/v1",  # Point to local LLM
            api_key="not-needed",  # Dummy key
            http_client=httpx.Client(
                timeout=120.0,  # Increased timeout
                transport=httpx.HTTPTransport(retries=3)
            )
        )
        
    def search_articles(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for relevant articles"""
        # Generate embedding for query
        query_vector = self.encoder.encode(query).tolist()
        
        # Search Qdrant
        results = self.qdrant.search(
            collection_name="news_articles",
            query_vector=query_vector,
            limit=limit
        )
        
        return [hit.payload for hit in results]
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_response(self, query: str, context_articles: List[Dict]) -> str:
        """Generate response using context"""
        try:
            # Format context
            context = "\n\n".join([
                f"Title: {article['title']}\n"
                f"Publication: {article['publication']}\n"
                f"Date: {article['published']}\n"
                f"Summary: {article['summary']}\n"
                f"Link: {article['link']}"
                for article in context_articles
            ])
            
            # Create prompt
            prompt = f"""Based on the following news articles, please answer the user's question.
            Include relevant quotes and citations when appropriate.

            Articles:
            {context}

            Question: {query}

            Answer:"""
            
            # Generate response
            response = self.openai.chat.completions.create(
                model="gpt-4",  # Model name doesn't matter for Yi
                messages=[
                    {"role": "system", "content": "You are a helpful news assistant. Answer questions based on the provided articles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "I'm sorry, I encountered an error while trying to answer your question. Please try again."
    
    def chat(self, query: str) -> str:
        """Main chat function"""
        # Search for relevant articles
        articles = self.search_articles(query)
        
        if not articles:
            return "I'm sorry, I couldn't find any relevant articles to answer your question."
        
        # Generate response using context
        return self.generate_response(query, articles) 