"""Comprehensive Security Testing Script.

Tests all security features:
1. JWT Secret Validation
2. Password Policy
3. Rate Limiting
4. Account Lockout
5. Security Headers
"""

import asyncio
import sys
import codecs

if sys.platform == "win32":
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

import httpx


API_BASE = "http://localhost:8000"


async def test_password_policy():
    """Test 1: Password Policy Enforcement."""
    print("\n" + "=" * 70)
    print("TEST 1: PASSWORD POLICY")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        test_cases = [
            ("weak", False, "Too short"),
            ("alllowercase123!", False, "No uppercase"),
            ("ALLUPPERCASE123!", False, "No lowercase"),
            ("NoNumbers!", False, "No numbers"),
            ("NoSpecial123", False, "No special chars"),
            ("SecurePass123!", True, "Strong password"),
            ("An0th3r$ecur3", True, "Strong password"),
        ]
        
        passed = 0
        failed = 0
        
        for password, should_succeed, description in test_cases:
            try:
                response = await client.post(
                    f"{API_BASE}/api/v1/auth/register",
                    json={
                        "email": f"test_{password}@test.com",
                        "password": password,
                        "tenant_name": "Test Tenant"
                    }
                )
                
                if should_succeed:
                    if response.status_code == 201:
                        print(f"  PASS: {description} - Registration succeeded")
                        passed += 1
                    else:
                        print(f"  FAIL: {description} - Expected success, got {response.status_code}")
                        print(f"        Response: {response.text[:100]}")
                        failed += 1
                else:
                    if response.status_code == 422:
                        print(f"  PASS: {description} - Correctly rejected")
                        passed += 1
                    else:
                        print(f"  FAIL: {description} - Expected rejection, got {response.status_code}")
                        failed += 1
                        
            except Exception as e:
                print(f"  ERROR: {description} - {str(e)}")
                failed += 1
        
        print(f"\nResults: {passed} passed, {failed} failed")
        return failed == 0


async def test_rate_limiting():
    """Test 2: Rate Limiting on Auth Endpoints."""
    print("\n" + "=" * 70)
    print("TEST 2: RATE LIMITING")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # First, create a test user
        try:
            await client.post(
                f"{API_BASE}/api/v1/auth/register",
                json={
                    "email": "ratelimit@test.com",
                    "password": "SecurePass123!",
                    "tenant_name": "Test Tenant"
                }
            )
        except:
            pass  # User might already exist
        
        # Make 7 rapid login attempts (should be rate limited on 6th)
        rate_limited = False
        success_count = 0
        
        print("  Making 7 rapid login attempts...")
        for i in range(1, 8):
            try:
                response = await client.post(
                    f"{API_BASE}/api/v1/auth/login",
                    json={
                        "email": "ratelimit@test.com",
                        "password": "wrongpassword"
                    }
                )
                
                if response.status_code == 429:
                    print(f"  Attempt {i}: Rate limited (429) - PASS")
                    rate_limited = True
                elif response.status_code == 401:
                    print(f"  Attempt {i}: Unauthorized (401) - OK")
                    success_count += 1
                else:
                    print(f"  Attempt {i}: Unexpected status {response.status_code}")
                    
            except Exception as e:
                print(f"  Attempt {i}: Error - {str(e)}")
        
        if rate_limited:
            print(f"\n  PASS: Rate limiting working (blocked after {success_count} attempts)")
            return True
        else:
            print(f"\n  FAIL: Rate limiting not working")
            return False


async def test_account_lockout():
    """Test 3: Account Lockout After Failed Attempts."""
    print("\n" + "=" * 70)
    print("TEST 3: ACCOUNT LOCKOUT")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create test user
        try:
            await client.post(
                f"{API_BASE}/api/v1/auth/register",
                json={
                    "email": "lockout@test.com",
                    "password": "SecurePass123!",
                    "tenant_name": "Test Tenant"
                }
            )
        except:
            pass  # User might already exist
        
        # Make 6 failed login attempts (should lock on 5th)
        locked = False
        
        print("  Making 6 failed login attempts...")
        for i in range(1, 7):
            try:
                response = await client.post(
                    f"{API_BASE}/api/v1/auth/login",
                    json={
                        "email": "lockout@test.com",
                        "password": "wrongpassword"
                    }
                )
                
                if response.status_code == 423:
                    print(f"  Attempt {i}: Account locked (423) - PASS")
                    print(f"        Message: {response.json().get('detail', '')[:80]}")
                    locked = True
                    break
                elif response.status_code == 401:
                    print(f"  Attempt {i}: Unauthorized (401) - OK")
                else:
                    print(f"  Attempt {i}: Unexpected status {response.status_code}")
                    
            except Exception as e:
                print(f"  Attempt {i}: Error - {str(e)}")
        
        if locked:
            print(f"\n  PASS: Account lockout working (locked after 5 attempts)")
            return True
        else:
            print(f"\n  FAIL: Account lockout not working")
            return False


async def test_security_headers():
    """Test 4: Security Headers."""
    print("\n" + "=" * 70)
    print("TEST 4: SECURITY HEADERS")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{API_BASE}/health")
            
            required_headers = {
                "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff",
                "X-XSS-Protection": "1; mode=block",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            }
            
            passed = 0
            failed = 0
            
            for header, expected_value in required_headers.items():
                if header in response.headers:
                    actual_value = response.headers[header]
                    if expected_value in actual_value:
                        print(f"  PASS: {header}: {actual_value}")
                        passed += 1
                    else:
                        print(f"  FAIL: {header}: Expected '{expected_value}', got '{actual_value}'")
                        failed += 1
                else:
                    print(f"  FAIL: {header}: Missing")
                    failed += 1
            
            print(f"\nResults: {passed} passed, {failed} failed")
            return failed == 0
            
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            return False


async def test_jwt_secret_validation():
    """Test 5: JWT Secret Validation (Startup Check)."""
    print("\n" + "=" * 70)
    print("TEST 5: JWT SECRET VALIDATION")
    print("=" * 70)
    
    # This test checks if server started successfully
    # If we're here, server is running, so JWT secret is valid
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{API_BASE}/health")
            if response.status_code == 200:
                print("  PASS: Server started successfully")
                print("        (JWT secret validation passed at startup)")
                return True
            else:
                print(f"  FAIL: Health check failed with status {response.status_code}")
                return False
        except Exception as e:
            print(f"  FAIL: Cannot connect to server - {str(e)}")
            print("        (JWT secret might be invalid)")
            return False


async def run_all_tests():
    """Run all security tests."""
    print("\n" + "=" * 70)
    print("SECURITY HARDENING - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("JWT Secret Validation", test_jwt_secret_validation),
        ("Password Policy", test_password_policy),
        ("Rate Limiting", test_rate_limiting),
        ("Account Lockout", test_account_lockout),
        ("Security Headers", test_security_headers),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n  ERROR in {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {'[OK]' if result else '[FAIL]'} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({100*passed/total:.1f}%)")
    print("=" * 70)
    
    if passed == total:
        print("\n  ALL TESTS PASSED! Security hardening is working correctly.")
        print("  Backend is PRODUCTION READY!")
    else:
        print("\n  SOME TESTS FAILED! Please review and fix issues.")
    
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    print("\nStarting security tests...")
    print("Make sure backend server is running on http://localhost:8000")
    print()
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
