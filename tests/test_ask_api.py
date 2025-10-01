"""Test AI assistant endpoint."""
import httpx
import asyncio
from typing import Dict


async def test_ask_endpoint():
    """Test the /ask endpoint with various questions."""
    base_url = "http://localhost:8000"
    
    # Test questions
    test_questions = [
        "What's the cheapest hospital for knee replacement within 500 kilometers of 78852?",
        "Which hospitals have the best ratings for heart surgery near NYC?",
        "Find DRG 872 providers near ZIP 78852 sorted by cost",
        "Show me the most affordable cardiac procedures in Texas",
        "What are the highest rated hospitals for hip replacement?",
        "Compare costs for back surgery near Boston",
        "List hospitals with excellent ratings near Chicago",
        "What's the weather today?",  # Out of scope question
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🤖 Testing AI Assistant Endpoint\n")
        print("=" * 60)
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n📝 Test {i}: {question}")
            print("-" * 40)
            
            try:
                response = await client.post(
                    f"{base_url}/ask",
                    json={"question": question}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Status: Success")
                    print(f"📊 Confidence: {data['confidence']:.0%}")
                    print(f"💬 Answer: {data['answer'][:200]}...")
                    if data.get('results_count'):
                        print(f"🔍 Results found: {data['results_count']}")
                    if data.get('sql_query'):
                        print(f"🔧 SQL Generated: Yes")
                elif response.status_code == 503:
                    print(f"⚠️  AI service not configured (missing API key)")
                else:
                    print(f"❌ Error: {response.status_code}")
                    print(f"   {response.json().get('detail', 'Unknown error')}")
                    
            except Exception as e:
                print(f"❌ Request failed: {e}")
        
        print("\n" + "=" * 60)
        print("✅ AI Assistant testing complete!")


if __name__ == "__main__":
    asyncio.run(test_ask_endpoint())