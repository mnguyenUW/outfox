"""Test provider API endpoints."""
import httpx
import asyncio
from typing import Dict


async def test_provider_endpoints():
    """Test all provider endpoints."""
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Test 1: DRG suggestions with 'sepsis'
        print("\n🧪 Test 1: DRG autocomplete suggestions for 'sepsis'")
        response = await client.get(
            f"{base_url}/providers/drg-suggestions",
            params={"q": "sepsis"}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"   ✅ Found {len(data['suggestions'])} suggestions")
        for sug in data['suggestions'][:3]:
            print(f"      - DRG {sug['drg_cd']}: {sug['drg_desc'][:50]}...")

        # Test 2: Search providers with drg=sepsis, zip=78852, radius_km=500
        print("\n🧪 Test 2: Search providers (drg=sepsis, zip=78852, radius_km=500)")
        response = await client.get(
            f"{base_url}/providers",
            params={"drg": "sepsis", "zip": "78852", "radius_km": 500}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"   ✅ Found {data['total_results']} providers for DRG 'sepsis'")
        if data['providers']:
            cheapest = data['providers'][0]
            print(f"   💰 Cheapest: {cheapest['rndrng_prvdr_org_name']} - ${cheapest['avg_submtd_cvrd_chrg']:,.2f}")

        # Test 3: Search providers with drg=872, zip=78852, radius_km=500
        print("\n🧪 Test 3: Search providers (drg=872, zip=78852, radius_km=500)")
        response = await client.get(
            f"{base_url}/providers",
            params={"drg": "872", "zip": "78852", "radius_km": 500}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"   ✅ Found {data['total_results']} providers for DRG '872'")
        if data['providers']:
            cheapest = data['providers'][0]
            print(f"   💰 Cheapest: {cheapest['rndrng_prvdr_org_name']} - ${cheapest['avg_submtd_cvrd_chrg']:,.2f}")
        
        print("\n✅ All provider API tests passed!")


if __name__ == "__main__":
    asyncio.run(test_provider_endpoints())