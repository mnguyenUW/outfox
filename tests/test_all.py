import asyncio
from tests.test_ask_api import test_ask_endpoint
from tests.test_providers_api import test_provider_endpoints

async def main():
    print("\n=== Running all API integration tests ===\n")
    await test_ask_endpoint()
    await test_provider_endpoints()
    print("\n=== All tests completed ===\n")

if __name__ == "__main__":
    asyncio.run(main())