"""Simple Security Test - No Emoji."""

import httpx
import sys

API_BASE = "http://localhost:8000"

def test_password_policy():
    print("\n=== TEST 1: PASSWORD POLICY ===")
    
    client = httpx.Client(timeout=30.0)
    
    # Test weak password
    r = client.post(
        f"{API_BASE}/api/v1/auth/register",
        json={"email": "weak@test.com", "password": "weak", "tenant_name": "Test"}
    )
    print(f"Weak password (weak): {r.status_code} - Expected 422")
    if r.status_code == 422:
        print("  PASS: Correctly rejected")
    else:
        print(f"  FAIL: Should be rejected")
        return False
    
    # Test strong password
    r = client.post(
        f"{API_BASE}/api/v1/auth/register",
        json={"email": "strong@test.com", "password": "SecurePass123!", "tenant_name": "Test"}
    )
    print(f"Strong password (SecurePass123!): {r.status_code} - Expected 201")
    if r.status_code == 201:
        print("  PASS: Correctly accepted")
        return True
    else:
        print(f"  FAIL: Should be accepted - {r.text[:100]}")
        return False


def test_security_headers():
    print("\n=== TEST 2: SECURITY HEADERS ===")
    
    client = httpx.Client(timeout=30.0)
    r = client.get(f"{API_BASE}/health")
    
    headers_to_check = [
        "X-Frame-Options",
        "X-Content-Type-Options",
        "X-XSS-Protection",
        "Referrer-Policy",
    ]
    
    passed = 0
    for header in headers_to_check:
        if header in r.headers:
            print(f"  {header}: {r.headers[header]} - PASS")
            passed += 1
        else:
            print(f"  {header}: MISSING - FAIL")
    
    print(f"\nResult: {passed}/{len(headers_to_check)} headers present")
    return passed == len(headers_to_check)


def test_rate_limiting():
    print("\n=== TEST 3: RATE LIMITING ===")
    
    client = httpx.Client(timeout=30.0)
    
    # Make 7 rapid requests
    rate_limited = False
    for i in range(1, 8):
        r = client.post(
            f"{API_BASE}/api/v1/auth/login",
            json={"email": "test@test.com", "password": "wrong"}
        )
        print(f"  Attempt {i}: {r.status_code}")
        if r.status_code == 429:
            print(f"  PASS: Rate limited at attempt {i}")
            rate_limited = True
            break
    
    if not rate_limited:
        print("  FAIL: Rate limiting not triggered")
        return False
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SECURITY TESTING - SIMPLE MODE")
    print("=" * 70)
    
    results = []
    
    try:
        results.append(("Password Policy", test_password_policy()))
    except Exception as e:
        print(f"ERROR: {e}")
        results.append(("Password Policy", False))
    
    try:
        results.append(("Security Headers", test_security_headers()))
    except Exception as e:
        print(f"ERROR: {e}")
        results.append(("Security Headers", False))
    
    try:
        results.append(("Rate Limiting", test_rate_limiting()))
    except Exception as e:
        print(f"ERROR: {e}")
        results.append(("Rate Limiting", False))
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, r in results if r)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    
    print(f"\nTotal: {passed}/{len(results)} passed")
    print("=" * 70)
    
    if passed == len(results):
        print("\nALL TESTS PASSED!")
    else:
        print("\nSOME TESTS FAILED!")
    
    sys.exit(0 if passed == len(results) else 1)
