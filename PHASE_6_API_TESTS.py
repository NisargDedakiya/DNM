"""
Phase 6 Findings Engine - Comprehensive API Testing Guide
Complete workflow for testing all finding endpoints with real data.
"""

import asyncio
import json
from uuid import uuid4

# Test data structure
test_scenarios = {
    "1_create_finding": {
        "endpoint": "POST /findings",
        "description": "Create a new security finding",
        "request": {
            "title": "SQL Injection in Login Form",
            "severity": "critical",
            "description": "Discovered SQL injection vulnerability in the login endpoint. Input validation is insufficient.",
            "endpoint": "/api/v1/auth/login",
            "evidence": "Payload: admin' OR '1'='1\nResponse: Username field accepted raw SQL syntax",
            "scan_id": "550e8400-e29b-41d4-a716-446655440005",
            "program_id": "550e8400-e29b-41d4-a716-446655440000"
        },
        "expected_response": {
            "status": 201,
            "body": {
                "id": "UUID",
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "scan_id": "550e8400-e29b-41d4-a716-446655440005",
                "created_by_id": "UUID",
                "title": "SQL Injection in Login Form",
                "severity": "critical",
                "description": "Discovered SQL injection vulnerability...",
                "endpoint": "/api/v1/auth/login",
                "evidence": "Payload: admin' OR '1'='1\n...",
                "status": "open",
                "created_at": "2026-05-15T10:30:00.000000",
                "updated_at": "2026-05-15T10:30:00.000000"
            }
        },
        "headers": {
            "Authorization": "Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
    },
    
    "2_list_findings": {
        "endpoint": "GET /findings",
        "description": "List findings with optional filters",
        "query_params": {
            "program_id": "550e8400-e29b-41d4-a716-446655440000",
            "severity": "critical",
            "status": "open",
            "limit": 10,
            "offset": 0
        },
        "expected_response": {
            "status": 200,
            "body": {
                "total": 3,
                "findings": [
                    {
                        "id": "UUID",
                        "program_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "SQL Injection in Login Form",
                        "severity": "critical",
                        "status": "open",
                        "endpoint": "/api/v1/auth/login",
                        "created_at": "2026-05-15T10:30:00.000000"
                    },
                    {
                        "id": "UUID",
                        "program_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "CORS Misconfiguration",
                        "severity": "high",
                        "status": "open",
                        "endpoint": "*",
                        "created_at": "2026-05-15T09:15:00.000000"
                    }
                ]
            }
        },
        "headers": {
            "Authorization": "Bearer {jwt_token}"
        }
    },
    
    "3_get_finding_details": {
        "endpoint": "GET /findings/{finding_id}",
        "description": "Retrieve specific finding with full details",
        "path_params": {
            "finding_id": "UUID_OF_FINDING"
        },
        "expected_response": {
            "status": 200,
            "body": {
                "id": "UUID",
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "scan_id": "550e8400-e29b-41d4-a716-446655440005",
                "created_by_id": "USER_UUID",
                "title": "SQL Injection in Login Form",
                "severity": "critical",
                "description": "Discovered SQL injection vulnerability in the login endpoint...",
                "endpoint": "/api/v1/auth/login",
                "evidence": "Payload: admin' OR '1'='1\nResponse: Username field accepted raw SQL syntax",
                "status": "open",
                "created_at": "2026-05-15T10:30:00.000000",
                "updated_at": "2026-05-15T10:30:00.000000"
            }
        },
        "headers": {
            "Authorization": "Bearer {jwt_token}"
        }
    },
    
    "4_update_finding": {
        "endpoint": "PUT /findings/{finding_id}",
        "description": "Update finding status or details",
        "request": {
            "status": "triaged",
            "severity": "high",
            "evidence": "Payload: admin' OR '1'='1\nResponse: Username field accepted raw SQL syntax\nPatch released: v2.3.1"
        },
        "expected_response": {
            "status": 200,
            "body": {
                "id": "UUID",
                "status": "triaged",
                "severity": "high",
                "evidence": "Payload: admin' OR '1'='1\n...\nPatch released: v2.3.1",
                "updated_at": "2026-05-15T11:45:00.000000"
            }
        },
        "headers": {
            "Authorization": "Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
    },
    
    "5_check_duplicates": {
        "endpoint": "POST /findings/check-duplicates",
        "description": "Check for existing findings with same title/severity/endpoint",
        "request": {
            "title": "SQL Injection in Login Form",
            "severity": "critical",
            "endpoint": "/api/v1/auth/login",
            "program_id": "550e8400-e29b-41d4-a716-446655440000"
        },
        "expected_response": {
            "status": 200,
            "body": {
                "count": 2,
                "has_duplicates": True,
                "duplicates": [
                    {
                        "id": "UUID",
                        "title": "SQL Injection in Login Form",
                        "severity": "critical",
                        "status": "open",
                        "created_at": "2026-05-15T10:30:00.000000"
                    },
                    {
                        "id": "UUID",
                        "title": "SQL Injection in Login Form",
                        "severity": "critical",
                        "status": "duplicate",
                        "created_at": "2026-05-15T08:20:00.000000"
                    }
                ]
            }
        },
        "headers": {
            "Authorization": "Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
    },
    
    "6_findings_summary": {
        "endpoint": "GET /findings/{program_id}/summary",
        "description": "Get summary statistics for all findings in program",
        "expected_response": {
            "status": 200,
            "body": {
                "program_id": "550e8400-e29b-41d4-a716-446655440000",
                "severity_summary": {
                    "critical": 2,
                    "high": 3,
                    "medium": 5,
                    "low": 8,
                    "info": 12
                },
                "status_summary": {
                    "open": 15,
                    "triaged": 8,
                    "confirmed": 5,
                    "fixed": 2,
                    "accepted": 0,
                    "duplicate": 0
                },
                "critical_findings": 2,
                "total_findings": 30
            }
        },
        "headers": {
            "Authorization": "Bearer {jwt_token}"
        }
    },
    
    "7_delete_finding": {
        "endpoint": "DELETE /findings/{finding_id}",
        "description": "Delete finding from program",
        "expected_response": {
            "status": 204,
            "body": None
        },
        "headers": {
            "Authorization": "Bearer {jwt_token}"
        }
    }
}


# Error scenarios
error_scenarios = {
    "unauthorized": {
        "endpoint": "GET /findings",
        "description": "Request without JWT token",
        "headers": {},
        "expected_status": 401,
        "expected_detail": "Not authenticated"
    },
    
    "invalid_token": {
        "endpoint": "GET /findings",
        "description": "Request with invalid JWT token",
        "headers": {
            "Authorization": "Bearer invalid_token_xyz"
        },
        "expected_status": 401,
        "expected_detail": "Invalid authentication credentials"
    },
    
    "program_not_found": {
        "endpoint": "GET /findings",
        "query": {
            "program_id": "00000000-0000-0000-0000-000000000000"
        },
        "description": "Request for findings in non-existent program",
        "expected_status": 404,
        "expected_detail": "Program not found"
    },
    
    "cross_user_access": {
        "endpoint": "GET /findings/{finding_id}",
        "description": "Try to access another user's finding",
        "user_context": "user_b",
        "finding_owner": "user_a",
        "expected_status": 404,
        "expected_detail": "Finding not found"
    },
    
    "validation_error": {
        "endpoint": "POST /findings",
        "description": "Create finding with invalid data",
        "request": {
            "title": "X",  # Too short (min 3)
            "severity": "invalid_severity",  # Invalid enum
            "description": "Short",  # Too short (min 10)
            "program_id": "not_a_uuid"
        },
        "expected_status": 422,
        "expected_detail": "Validation error"
    }
}


# Complete workflow test
complete_workflow = """
==================================================
PHASE 6 FINDINGS ENGINE - COMPLETE WORKFLOW TEST
==================================================

1. User Registration
   POST /auth/register
   └─ Returns: JWT token

2. Program Creation
   POST /programs
   └─ Returns: program_id

3. Create First Finding
   POST /findings
   ├─ Title: SQL Injection in Login
   ├─ Severity: critical
   ├─ Status: open (default)
   └─ Returns: finding_id

4. Create Potential Duplicate Finding
   POST /findings
   ├─ Title: SQL Injection in Login (same)
   ├─ Severity: critical (same)
   ├─ Endpoint: /api/v1/auth/login (same)
   └─ Returns: finding_id_2

5. Check for Duplicates
   POST /findings/check-duplicates
   ├─ Title: SQL Injection in Login
   ├─ Severity: critical
   ├─ Endpoint: /api/v1/auth/login
   └─ Returns: count=2, has_duplicates=true

6. List All Findings (Unfiltered)
   GET /findings?program_id={id}&limit=100
   └─ Returns: total=2, findings=[...]

7. List Critical Findings
   GET /findings?program_id={id}&severity=critical
   └─ Returns: total=2 (only critical)

8. Update Finding Status
   PUT /findings/{finding_id}
   ├─ status: triaged
   └─ Returns: updated finding

9. Get Findings Summary
   GET /findings/{program_id}/summary
   └─ Returns: critical=2, high=0, ..., total=2

10. Delete Duplicate Finding
    DELETE /findings/{finding_id_2}
    └─ Returns: 204 No Content

11. Verify Deletion
    GET /findings?program_id={id}
    └─ Returns: total=1 (only first finding remains)

12. Create Critical Finding
    POST /findings
    ├─ Severity: critical
    └─ Returns: finding_id_3

13. Update to Resolved
    PUT /findings/{finding_id_3}
    ├─ status: fixed
    └─ Returns: updated finding

14. Final Summary
    GET /findings/{program_id}/summary
    └─ Returns: critical=2, status_summary={open:1, fixed:1}

==================================================
EXPECTED OUTCOMES
==================================================

✅ No cross-user access violations
✅ Duplicate detection works
✅ Status transitions work
✅ Ownership validation enforced
✅ All filters work correctly
✅ Summary statistics accurate
✅ Pagination works
✅ Severity levels respected
"""


# Test request examples for curl/Postman
curl_examples = """
==================================================
CURL TEST EXAMPLES
==================================================

1. CREATE FINDING (Critical Severity)
curl -X POST http://localhost:8000/findings \\
  -H "Authorization: Bearer {jwt_token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "SQL Injection in Login Form",
    "severity": "critical",
    "description": "SQL injection vulnerability discovered in login endpoint. Input validation insufficient.",
    "endpoint": "/api/v1/auth/login",
    "evidence": "Payload: admin'"'"' OR '"'"'1'"'"'='"'"'1",
    "program_id": "550e8400-e29b-41d4-a716-446655440000"
  }'

2. LIST ALL FINDINGS
curl -X GET "http://localhost:8000/findings?program_id=550e8400-e29b-41d4-a716-446655440000&limit=10" \\
  -H "Authorization: Bearer {jwt_token}"

3. LIST CRITICAL FINDINGS
curl -X GET "http://localhost:8000/findings?program_id=550e8400-e29b-41d4-a716-446655440000&severity=critical" \\
  -H "Authorization: Bearer {jwt_token}"

4. GET FINDING DETAILS
curl -X GET http://localhost:8000/findings/{finding_id} \\
  -H "Authorization: Bearer {jwt_token}"

5. UPDATE FINDING STATUS
curl -X PUT http://localhost:8000/findings/{finding_id} \\
  -H "Authorization: Bearer {jwt_token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "status": "triaged",
    "severity": "high"
  }'

6. CHECK FOR DUPLICATES
curl -X POST http://localhost:8000/findings/check-duplicates \\
  -H "Authorization: Bearer {jwt_token}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "title": "SQL Injection in Login Form",
    "severity": "critical",
    "endpoint": "/api/v1/auth/login",
    "program_id": "550e8400-e29b-41d4-a716-446655440000"
  }'

7. GET FINDINGS SUMMARY
curl -X GET http://localhost:8000/findings/550e8400-e29b-41d4-a716-446655440000/summary \\
  -H "Authorization: Bearer {jwt_token}"

8. DELETE FINDING
curl -X DELETE http://localhost:8000/findings/{finding_id} \\
  -H "Authorization: Bearer {jwt_token}"

==================================================
POSTMAN ENVIRONMENT VARIABLES
==================================================

{{base_url}} = http://localhost:8000
{{jwt_token}} = <your_jwt_token_here>
{{program_id}} = 550e8400-e29b-41d4-a716-446655440000
{{finding_id}} = <created_finding_id>

==================================================
"""


if __name__ == "__main__":
    print(complete_workflow)
    print("\n")
    print(curl_examples)
    print("\n")
    print("Test scenarios documented in test_scenarios dict")
    print("Error scenarios documented in error_scenarios dict")
