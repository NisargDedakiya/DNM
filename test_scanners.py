"""
Standalone scanner test script - tests scanner logic without database.
Tests subdomain discovery and HTTP probing on example.com
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.scanners.scanner_manager import ScannerManager


async def main():
    """Test scanner pipeline on example.com"""
    print("=" * 70)
    print("NisargHunter AI - Recon Engine Scanner Test")
    print("=" * 70)
    print()

    manager = ScannerManager()

    # Test target
    target = "example.com"
    
    print(f"🎯 Target: {target}")
    print(f"📅 Date: 2026-05-15")
    print()

    # Test 1: Subfinder validation
    print("[1/4] Testing Subfinder Target Validation...")
    is_valid = manager.subfinder.validate_target(target)
    print(f"     Result: {'✅ VALID' if is_valid else '❌ INVALID'}")
    print()

    # Test 2: Run Subfinder scan
    print("[2/4] Executing Subfinder Subdomain Discovery...")
    print("     Command: subfinder -d example.com -silent")
    print()
    
    try:
        subfinder_result = await manager.run_subfinder_scan(target)
        
        print(f"     Status: {subfinder_result['status']}")
        print(f"     Subdomains Found: {subfinder_result.get('count', 0)}")
        
        if subfinder_result['status'] == 'success':
            subdomains = subfinder_result.get('results', [])
            if subdomains:
                print(f"     First 5 Results:")
                for subdomain in subdomains[:5]:
                    print(f"       ├─ {subdomain}")
                if len(subdomains) > 5:
                    print(f"       └─ ... and {len(subdomains) - 5} more")
            else:
                print("     ⚠️  No subdomains discovered")
        else:
            error = subfinder_result.get('error', 'Unknown error')
            print(f"     Error: {error}")
        
        print()

        # Test 3: Run HTTPx scan on discovered subdomains
        if subfinder_result['status'] == 'success':
            subdomains = subfinder_result.get('results', [])
            
            if subdomains:
                print("[3/4] Executing HTTPx Live Host Detection...")
                print(f"     Probing {len(subdomains)} discovered subdomains")
                print()
                
                httpx_result = await manager.run_httpx_scan(subdomains)
                
                print(f"     Status: {httpx_result['status']}")
                print(f"     Live Hosts Found: {httpx_result.get('count', 0)}")
                
                if httpx_result['status'] == 'success':
                    hosts = httpx_result.get('results', [])
                    if hosts:
                        print(f"     First 3 Live Hosts:")
                        for host in hosts[:3]:
                            url = host.get('url', 'N/A')
                            status = host.get('status_code', 'N/A')
                            title = host.get('title', 'No title')
                            print(f"       ├─ {url} [{status}]")
                            if title:
                                print(f"       │  Title: {title}")
                        if len(hosts) > 3:
                            print(f"       └─ ... and {len(hosts) - 3} more live hosts")
                    else:
                        print("     ⚠️  No live hosts detected")
                else:
                    error = httpx_result.get('error', 'Unknown error')
                    print(f"     Error: {error}")
                
                print()

                # Test 4: Full pipeline summary
                print("[4/4] Recon Pipeline Summary")
                print(f"     Total Subdomains: {len(subdomains)}")
                print(f"     Live Hosts: {httpx_result.get('count', 0)}")
                print(f"     Success Rate: {(httpx_result.get('count', 0) / len(subdomains) * 100):.1f}%")
            else:
                print("[3/4] Skipping HTTPx - No subdomains discovered")
                print("[4/4] Recon Pipeline Summary")
                print("     Status: INCOMPLETE - No discovery targets")
        else:
            print("[3/4] Skipping HTTPx - Subfinder failed")
            print("[4/4] Recon Pipeline Summary")
            print("     Status: FAILED - Subfinder error")

    except Exception as exc:
        print(f"     ❌ Error: {exc}")
        print()
        print("[3/4] Skipping HTTPx - Subfinder error")
        print("[4/4] Recon Pipeline Summary")
        print(f"     Status: FAILED - {exc}")

    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)
    print()
    print("📊 Available Scanners:")
    for scanner in manager.list_scanners():
        print(f"   • {scanner}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
