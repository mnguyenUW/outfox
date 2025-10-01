"""AI service for natural language query processing."""
import json
import re
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings

settings = get_settings()


class AIService:
    """Service for AI-powered natural language processing."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    async def process_question(self, question: str) -> Dict[str, Any]:
        """
        Process a natural language question about healthcare costs and quality.
        """
        # First, determine if the question is in scope
        if not await self._is_healthcare_question(question):
            return {
                "answer": "I can only help with hospital pricing and quality information. Please ask about medical procedures, costs, or hospital ratings.",
                "sql_query": None,
                "confidence": 0.0
            }
        
        # Generate SQL from the natural language query
        sql_query = await self._generate_sql(question)
        
        if not sql_query:
            return {
                "answer": "I couldn't understand your question. Please try rephrasing it. For example: 'What's the cheapest hospital for knee replacement near 10001?'",
                "sql_query": None,
                "confidence": 0.0
            }
        
        # Execute the SQL query
        results = await self._execute_safe_sql(sql_query)
        
        if results is None:
            return {
                "answer": "I encountered an error processing your query. Please try rephrasing your question.",
                "sql_query": sql_query,
                "confidence": 0.3
            }
        
        # Generate a natural language response based on results
        answer = await self._generate_answer(question, results)
        
        return {
            "answer": answer,
            "sql_query": sql_query,
            "confidence": 0.85 if results else 0.6,
            "results_count": len(results) if isinstance(results, list) else 0
        }
    
    async def _is_healthcare_question(self, question: str) -> bool:
        """Check if the question is about healthcare costs or quality."""
        healthcare_keywords = [
            'hospital', 'medical', 'procedure', 'surgery', 'drg', 'cost', 'price',
            'cheapest', 'expensive', 'rating', 'quality', 'medicare', 'treatment',
            'diagnosis', 'heart', 'knee', 'hip', 'replacement', 'care', 'health'
        ]
        
        question_lower = question.lower()
        
        # Quick keyword check first
        if any(keyword in question_lower for keyword in healthcare_keywords):
            return True
        
        # Use AI for ambiguous cases
        prompt = f"""
        Is this question about healthcare costs, hospital quality, or medical procedures?
        Question: "{question}"
        
        Answer only 'yes' or 'no'.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a healthcare query classifier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            answer = response.choices[0].message.content.strip().lower()
            return answer == 'yes'
        except:
            # If AI fails, be permissive
            return True
    
    async def _generate_sql(self, question: str) -> Optional[str]:
        """Generate SQL query from natural language question."""
        
        # Get sample data for context
        sample_data = await self._get_sample_data()
        
        prompt = f"""
        Convert this natural language question to a PostgreSQL query for our healthcare database.
        
        Question: "{question}"
        
        Database Schema:
        - providers table:
          - rndrng_prvdr_ccn (string): Provider ID
          - rndrng_prvdr_org_name (string): Hospital name
          - rndrng_prvdr_city (string): City
          - rndrng_prvdr_state_abrvtn (string): State code (e.g., 'NY')
          - rndrng_prvdr_zip5 (string): ZIP code
          - drg_cd (integer): DRG code
          - drg_desc (string): DRG description
          - avg_submtd_cvrd_chrg (decimal): Average billed charges
          - avg_tot_pymt_amt (decimal): Average total payment
          - avg_mdcr_pymt_amt (decimal): Average Medicare payment
          - latitude, longitude (decimal): Coordinates
          - location (geography): PostGIS point
        
        - provider_ratings table:
          - provider_ccn (string): Links to rndrng_prvdr_ccn
          - rating (decimal): 1.0 to 10.0
          - rating_category (string): 'overall', 'cleanliness', etc.
          - review_count (integer): Number of reviews
        
        - zip_codes table:
          - zip_code (string): 5-digit ZIP
          - latitude, longitude (decimal): Coordinates
          - city, state_code (string): Location info
        
        Sample DRG codes and descriptions:
        {sample_data['drg_samples']}
        
        Sample ZIP codes:
        {sample_data['zip_samples']}
        
        Guidelines:
        1. For geographic searches, use ST_DWithin with geography type for accurate distance
        2. Convert miles to meters (1 mile = 1609.34 meters)
        3. For cost queries, use avg_submtd_cvrd_chrg (what hospitals charge)
        4. For quality/rating queries, join with provider_ratings where rating_category = 'overall'
        5. Always limit results to prevent huge result sets (max 20)
        6. For text matching on DRG descriptions, use ILIKE with % wildcards
        7. Order by cost (ascending) for "cheapest" queries
        8. Order by rating (descending) for "best" queries
        
        Examples:
        - "cheapest knee replacement near 10001" → Search for DRG with 'knee' in description near ZIP 10001
        - "best rated heart surgery in NY" → High-rated cardiac DRGs in NY state
        - "DRG 470 within 25 miles of 90210" → Specific DRG within radius
        
        Return ONLY the SQL query, no explanations. Make sure it's valid PostgreSQL with PostGIS.
        """
        
        try:
            print("\n[DEBUG] OpenAI SQL generation prompt:\n", prompt)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a SQL expert for healthcare data. Return only valid PostgreSQL queries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            print("[DEBUG] OpenAI SQL generation raw response:", response)
            sql = response.choices[0].message.content.strip()
            
            # Clean up the SQL
            sql = sql.replace('```sql', '').replace('```', '').strip()
            
            # Basic SQL injection prevention
            if not self._is_safe_sql(sql):
                print("[DEBUG] Generated SQL failed safety check:", sql)
                return None
            
            return sql
            
        except Exception as e:
            print(f"Error generating SQL: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _get_sample_data(self) -> Dict:
        """Get sample data for context."""
        # Get sample DRGs
        drg_result = await self.db.execute(text("""
            SELECT DISTINCT drg_cd, LEFT(drg_desc, 50) as drg_desc
            FROM providers
            ORDER BY drg_cd
            LIMIT 10
        """))
        drg_samples = [f"- DRG {row[0]}: {row[1]}..." for row in drg_result]
        
        # Get sample ZIPs
        zip_result = await self.db.execute(text("""
            SELECT DISTINCT zip_code, city, state_code
            FROM zip_codes
            LIMIT 10
        """))
        zip_samples = [f"- {row[0]}: {row[1]}, {row[2]}" for row in zip_result]
        
        return {
            'drg_samples': '\n'.join(drg_samples),
            'zip_samples': '\n'.join(zip_samples)
        }
    
    def _is_safe_sql(self, sql: str) -> bool:
        """Basic SQL injection prevention."""
        dangerous_patterns = [
            r';\s*DROP', r';\s*DELETE', r';\s*UPDATE', r';\s*INSERT',
            r';\s*ALTER', r';\s*CREATE', r';\s*TRUNCATE', r'--',
            r';\s*EXEC', r';\s*EXECUTE', r'xp_', r'sp_'
        ]
        
        sql_upper = sql.upper()
        
        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if re.search(pattern, sql_upper):
                return False
        
        # Only allow SELECT statements
        if not sql_upper.strip().startswith('SELECT'):
            return False
        
        # Limit to one statement
        if ';' in sql.rstrip(';'):
            return False
        
        return True
    
    async def _execute_safe_sql(self, sql: str) -> Optional[List[Dict]]:
        """Execute SQL query safely and return results."""
        try:
            # Add a timeout and row limit if not present
            if 'LIMIT' not in sql.upper():
                sql += ' LIMIT 20'
            
            result = await self.db.execute(text(sql))
            
            # Convert to list of dicts
            rows = result.fetchall()
            if not rows:
                return []
            
            # Get column names
            columns = result.keys()
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))
            
            return results
            
        except Exception as e:
            print(f"SQL execution error: {e}")
            print(f"SQL query: {sql}")
            return None
    
    async def _generate_answer(self, question: str, results: List[Dict]) -> str:
        """Generate a natural language answer from query results."""
        
        if not results:
            return "I couldn't find any results matching your query. Try adjusting your search criteria, such as increasing the search radius or using different keywords."
        
        # Format results for the AI
        formatted_results = self._format_results_for_ai(results)
        
        prompt = f"""
        Generate a helpful, conversational answer to this healthcare question based on the database results.
        
        Original Question: "{question}"
        
        Query Results:
        {formatted_results}
        
        Guidelines:
        1. Be conversational and helpful
        2. Mention specific hospital names and locations
        3. Include costs in dollars with proper formatting (e.g., $45,000)
        4. Mention ratings if available (e.g., "rated 8.5/10")
        5. If multiple results, highlight the top 2-3 options
        6. For cost queries, emphasize the cheapest options
        7. For quality queries, emphasize the highest-rated options
        8. Include relevant details like city/state and distance if available
        9. Keep the response concise but informative
        
        Generate a natural, helpful response:
        """
        
        try:
            print("\n[DEBUG] OpenAI answer generation prompt:\n", prompt)
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful healthcare cost advisor. Provide clear, accurate information based on the data."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            print("[DEBUG] OpenAI answer generation raw response:", response)
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating answer: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to simple formatting
            return self._format_simple_answer(results)
    
    def _format_results_for_ai(self, results: List[Dict]) -> str:
        """Format query results for AI consumption."""
        if not results:
            return "No results found"
        
        formatted = []
        for i, row in enumerate(results[:5], 1):  # Limit to top 5
            formatted_row = f"{i}. "
            
            # Add hospital name if present
            if 'rndrng_prvdr_org_name' in row:
                formatted_row += f"Hospital: {row['rndrng_prvdr_org_name']}"
            
            # Add location
            if 'rndrng_prvdr_city' in row and 'rndrng_prvdr_state_abrvtn' in row:
                formatted_row += f" ({row['rndrng_prvdr_city']}, {row['rndrng_prvdr_state_abrvtn']})"
            
            # Add cost
            if 'avg_submtd_cvrd_chrg' in row and row['avg_submtd_cvrd_chrg']:
                formatted_row += f", Cost: ${row['avg_submtd_cvrd_chrg']:,.2f}"
            
            # Add rating
            if 'rating' in row and row['rating']:
                formatted_row += f", Rating: {row['rating']}/10"
            elif 'overall_rating' in row and row['overall_rating']:
                formatted_row += f", Rating: {row['overall_rating']}/10"
            
            # Add DRG info
            if 'drg_cd' in row:
                formatted_row += f", DRG: {row['drg_cd']}"
            
            # Add distance
            if 'distance_km' in row and row['distance_km']:
                miles = row['distance_km'] * 0.621371
                formatted_row += f", Distance: {miles:.1f} miles"
            
            formatted.append(formatted_row)
        
        return "\n".join(formatted)
    
    def _format_simple_answer(self, results: List[Dict]) -> str:
        """Simple fallback answer formatting."""
        if not results:
            return "No results found for your query."
        
        answer = f"I found {len(results)} result(s) for your query:\n\n"
        
        for i, row in enumerate(results[:3], 1):
            if 'rndrng_prvdr_org_name' in row:
                answer += f"{i}. {row['rndrng_prvdr_org_name']}"
                
                if 'rndrng_prvdr_city' in row:
                    answer += f" in {row['rndrng_prvdr_city']}, {row.get('rndrng_prvdr_state_abrvtn', '')}"
                
                if 'avg_submtd_cvrd_chrg' in row and row['avg_submtd_cvrd_chrg']:
                    answer += f" - Average cost: ${row['avg_submtd_cvrd_chrg']:,.2f}"
                
                if 'rating' in row and row['rating']:
                    answer += f" (Rating: {row['rating']}/10)"
                
                answer += "\n"
        
        return answer.strip()