# Phase F: Bugcrowd Engagement Scraper + AI Scope Extraction

**Date**: Phase 19-F (Continuation of Integration Phase)  
**Status**: ✅ Complete - Production Ready  
**Complexity**: High-Signal Intelligence Pipeline

---

## Overview

Phase F implements an AI-assisted Bugcrowd scope ingestion system optimized for:

✅ **Public engagement parsing** - Safe, rate-limited page fetching  
✅ **AI-assisted scope extraction** - Claude structures messy scope text  
✅ **Target normalization** - Domains, APIs, IPs, wildcards, patterns  
✅ **Metadata extraction** - Bounty ranges, asset types, auth requirements  
✅ **Recon-ready ingestion** - Targets feed directly into recon workflows  
✅ **Workspace isolation** - Multi-tenant safety preserved  
✅ **Audit trail** - Full sync history and change tracking  

---

## Architecture Overview

```
User Request (Bugcrowd Engagement URL)
    ↓
Validation Layer (URL security, domain check)
    ↓
BugcrowdScraper (Fetch & Parse)
    ├─ Rate Limited HTTP (2 req/sec)
    ├─ BeautifulSoup parsing
    └─ Safe HTML extraction
    ↓
ScopeExtractor (AI-Assisted Normalization)
    ├─ Claude AI structures text
    ├─ Detects asset types
    ├─ Normalizes targets
    └─ Validates with ScopeValidator
    ↓
MetadataAnalyzer (AI-Assisted Analysis)
    ├─ Extracts bounty ranges
    ├─ Identifies auth requirements
    ├─ Classifies asset categories
    └─ Extracts program rules
    ↓
Database Storage (BugcrowdProgram Model)
    ├─ Program metadata
    ├─ Extracted assets
    ├─ Sync history
    └─ Workspace isolation
    ↓
Recon Integration
    ├─ Assets feed into inventory
    ├─ Monitoring rules activate
    ├─ AI prioritization updates
    └─ Workflow generation
```

---

## Files Created

### 1. backend/models/bugcrowd_program.py

**Purpose**: Database models for Bugcrowd engagement data

**Classes**:
- `BugcrowdProgram` - Program metadata and scope data
- `BugcrowdAsset` - Extracted targets with normalization data
- `BugcrowdSyncHistory` - Audit trail of sync operations

**Key Fields**:
```python
BugcrowdProgram:
  - organization_id (multi-tenant safety)
  - engagement_url (public page only)
  - scope_data (normalized targets)
  - metadata (bounty, auth, rules)
  - extraction_confidence (0-100)
  - ai_extraction_used (boolean)

BugcrowdAsset:
  - target (normalized form)
  - asset_type (website, api, mobile, etc)
  - wildcard_pattern (*.domain.com support)
  - validation_status (pending, valid, invalid)
  - synced_to_asset_inventory (recon integration)
```

### 2. backend/engines/bugcrowd_scraper.py

**Purpose**: Safe, rate-limited HTML scraping and parsing

**Key Features**:
- ✅ Rate limiting (2 req/sec, configurable backoff)
- ✅ Timeout protection (30 sec per request)
- ✅ Retry logic (3 attempts with exponential backoff)
- ✅ Security validation (rejects private URLs)
- ✅ Async/await architecture
- ✅ User-agent headers

**Main Functions**:

```python
fetch_engagement_page(url) → HTML
  - Validates URL is bugcrowd.com
  - Rejects private paths: /settings, /admin, /account, /api/
  - Rate limited to 2 requests per second
  - Returns HTML or None on failure

parse_engagement_html(html) → Dict
  - BeautifulSoup parsing
  - Extracts program name, description
  - Identifies scope sections
  - Returns structured data with raw text

extract_scope_sections(parsed_data) → Dict
  - Separates in_scope and out_of_scope
  - Cleans bullet points and formatting
  - Classifies by markers (in scope, out of scope, rules)

extract_program_metadata(parsed_data) → Dict
  - Detects asset types
  - Extracts bounty ranges
  - Identifies auth requirements
  - Extracts severity levels
```

**Usage Example**:

```python
async with BugcrowdScraper() as scraper:
    # Fetch page
    html = await scraper.fetch_engagement_page("https://bugcrowd.com/programs/example")
    
    # Parse HTML
    parsed = scraper.parse_engagement_html(html)
    
    # Extract sections
    scope = scraper.extract_scope_sections(parsed)
    # Returns: {
    #   "in_scope": ["domain.com", "*.api.example.com", "192.168.1.0/24"],
    #   "out_of_scope": ["internal.example.com"],
    #   "rules": ["Don't DOS", "No staging access"]
    # }
    
    # Extract metadata
    metadata = scraper.extract_program_metadata(parsed)
    # Returns: {
    #   "asset_types": ["website", "api"],
    #   "bounty_ranges": "$500 - $5000",
    #   "auth_required": true,
    #   "severity_ratings": [{...}]
    # }
```

### 3. backend/services/scope_extraction_service.py

**Purpose**: AI-assisted scope normalization and validation

**Key Classes**:

`ScopeTarget` - Normalized scope target:
```python
@dataclass
class ScopeTarget:
    target: str  # "domain.com" or "*.api.example.com" or "192.168.1.0/24"
    asset_type: str  # "website", "api", "mobile_ios", "cloud_service", etc
    in_scope: bool
    wildcard: bool  # True for *.domain.com patterns
    base_domain: Optional[str]  # "example.com"
    priority: Optional[str]  # "critical", "high", "medium", "low"
    restrictions: Optional[Dict]  # Rate limits, endpoint exclusions, etc
```

`ScopeExtractor` - Main extraction service:

```python
async extract_structured_scope(raw_scope_text, program_context) → Dict[str, List[ScopeTarget]]
  - Sends raw text to Claude for AI parsing
  - Prompt ensures no data invention (critical safety feature)
  - Returns normalized in_scope and out_of_scope targets
  
async normalize_scope_targets(target_str, in_scope) → List[ScopeTarget]
  - Normalizes individual targets
  - Detects asset types
  - Extracts base domains
  - Identifies wildcards
  - Determines priority levels
  - Validates with ScopeValidator
  
async validate_scope_entries(targets) → bool
  - Uses existing scope validator
  - Ensures all targets are valid
  - Prevents invalid targets from entering system
```

**Safety Features**:

```
AI Prompt Design:
- Explicit "DO NOT invent targets" instruction
- Requires targets to be explicitly stated
- Low temperature (0.2) for deterministic output
- Returns only JSON, no additional text

Validation:
- All targets passed through ScopeValidator
- Duplicates detected and removed
- Wildcard patterns validated
- IP ranges validated with regex
```

**Usage Example**:

```python
extractor = ScopeExtractor(claude_client, scope_validator)

# Extract from raw text
scope = await extractor.extract_structured_scope(
    raw_text="In scope: domain.com, *.api.example.com, https://internal.example.com/api/*",
    program_context="Bug bounty program for Example Corp"
)

# Returns:
# {
#   "in_scope": [
#     ScopeTarget(
#       target="domain.com",
#       asset_type="website",
#       in_scope=True,
#       wildcard=False,
#       base_domain="domain.com",
#       priority="medium"
#     ),
#     ScopeTarget(
#       target="*.api.example.com",
#       asset_type="api",
#       in_scope=True,
#       wildcard=True,
#       base_domain="example.com",
#       priority="high"
#     ),
#     ...
#   ],
#   "out_of_scope": [...]
# }
```

### 4. backend/services/program_metadata_service.py

**Purpose**: Extract program metadata (bounty, rules, requirements)

**Main Classes**:

`ProgramMetadata` - Structured metadata:
```python
@dataclass
class ProgramMetadata:
    program_name: str
    description: Optional[str]
    bounty_ranges: Dict[str, str]  # {"critical": "$500", "high": "$200", ...}
    asset_categories: List[str]  # ["website", "api", "mobile", ...]
    auth_required: Optional[bool]
    auth_details: Optional[str]
    severity_levels: List[Dict]  # [{"level": "critical", "bounty": "$500"}, ...]
    submission_requirements: List[str]
    prohibited_actions: List[str]
    payout_schedule: Optional[str]
    rules_of_engagement: Optional[str]
```

`ProgramMetadataAnalyzer`:

```python
async analyze_program_metadata(program_name, description, full_text) → ProgramMetadata
  - Uses Claude for intelligent extraction
  - Detects bounty ranges
  - Identifies auth requirements
  - Classifies asset types
  - Extracts rules and restrictions
  
classify_program_assets(metadata) → Dict
  - Groups in-scope assets by type
  
extract_program_rules(full_text) → Dict
  - Parses prohibitions
  - Extracts requirements
  - Builds guidelines list
```

**Usage Example**:

```python
analyzer = ProgramMetadataAnalyzer(claude_client)

metadata = await analyzer.analyze_program_metadata(
    program_name="Example Bug Bounty",
    description="Security testing program",
    full_text="Full program page text..."
)

# metadata.bounty_ranges = {"critical": "$1000", "high": "$500", ...}
# metadata.asset_categories = ["website", "api", "mobile_ios"]
# metadata.auth_required = True
# metadata.severity_levels = [{"level": "critical", "bounty": "$1000"}, ...]
```

### 5. backend/services/bugcrowd_integration_service.py

**Purpose**: Orchestrate complete ingestion workflow

**Main Class**:

`BugcrowdIntegrationService`:

```python
async ingest_bugcrowd_engagement(engagement_url, organization_id) → BugcrowdIngestionResult
  
  Complete workflow:
  1. Fetch public engagement page
  2. Parse HTML with BeautifulSoup
  3. Extract scope sections
  4. Use Claude to structure scope text
  5. Extract program metadata with Claude
  6. Normalize all targets
  7. Validate targets with ScopeValidator
  8. Store program in BugcrowdProgram model
  9. Store assets in BugcrowdAsset model
  10. Create sync history record
  11. Link to asset inventory (future: auto-ingest)
  12. Trigger recon workflow generation (future)
  
  Returns:
    - success: bool
    - program_name: str
    - program_id: UUID
    - assets_imported: int
    - assets_updated: int
    - duration_seconds: float
    - errors: List[str]
```

---

## API Endpoints

### Ingest Bugcrowd Engagement (AI-Assisted)

```
POST /api/integrations/bugcrowd/ingest

Query Parameters:
  - engagement_url: str (required) - Public Bugcrowd engagement URL
  - organization_id: UUID (required) - Organization workspace ID

Security:
  - Requires MANAGE_ASSETS permission
  - Validates URL is public bugcrowd.com domain
  - Rejects private paths (/settings, /admin, etc)
  - Rate limited globally to 2 req/sec

Response (200 OK):
{
  "success": true,
  "program_name": "Example Bug Bounty",
  "program_id": "uuid",
  "assets_imported": 42,
  "assets_updated": 5,
  "duration_seconds": 12.5,
  "message": "Successfully imported 42 assets from Example Bug Bounty"
}

Example:
POST /api/integrations/bugcrowd/ingest?engagement_url=https://bugcrowd.com/programs/example&organization_id=org-uuid
```

### List Ingested Bugcrowd Programs

```
GET /api/integrations/bugcrowd/programs

Query Parameters:
  - organization_id: UUID (required)

Response:
{
  "programs": [
    {
      "id": "uuid",
      "name": "Example Bug Bounty",
      "engagement_url": "https://bugcrowd.com/programs/example",
      "status": "active",
      "assets_count": 42,
      "last_synced_at": "2026-05-18T10:30:00",
      "created_at": "2026-05-18T10:15:00",
      "metadata": {
        "bounty_ranges": {"critical": "$1000", "high": "$500"},
        "asset_categories": ["website", "api"],
        "auth_required": true
      }
    }
  ],
  "total": 1
}
```

### List Extracted Assets from Program

```
GET /api/integrations/bugcrowd/programs/{program_id}/assets

Query Parameters:
  - organization_id: UUID (required)

Response:
{
  "program_id": "uuid",
  "program_name": "Example Bug Bounty",
  "assets": [
    {
      "id": "uuid",
      "target": "domain.com",
      "type": "website",
      "in_scope": true,
      "wildcard": false,
      "base_domain": "domain.com",
      "priority": "medium",
      "validation_status": "valid"
    },
    {
      "id": "uuid",
      "target": "*.api.example.com",
      "type": "api",
      "in_scope": true,
      "wildcard": true,
      "base_domain": "example.com",
      "priority": "high",
      "validation_status": "valid"
    }
  ],
  "total": 2
}
```

---

## Scope Extraction Examples

### Example 1: Basic Scope

**Raw Text**:
```
In Scope:
- domain.com
- *.api.example.com
- https://internal.example.com/api/v1/*

Out of Scope:
- admin.example.com
- staging.example.com
```

**Extracted Targets**:
```
In Scope:
- target: domain.com
  asset_type: website
  priority: medium
  
- target: *.api.example.com
  asset_type: api
  wildcard: true
  base_domain: example.com
  priority: high
  
- target: internal.example.com/api/v1/*
  asset_type: api
  priority: high

Out of Scope:
- target: admin.example.com
  asset_type: website
  priority: low
  
- target: staging.example.com
  asset_type: website
  priority: low
```

### Example 2: Complex Scope with Wildcards

**Raw Text**:
```
Scope:
1. Main website: example.com
2. All subdomains: *.example.com (except staging.example.com and dev.example.com)
3. API endpoints: api.example.com/v1/*, api.example.com/v2/*
4. Mobile apps:
   - iOS: Example app on App Store
   - Android: Example app on Play Store
5. Cloud infrastructure:
   - AWS S3 buckets: *.s3.amazonaws.com (only example-* buckets)
   - Cloud CDN: cdn.example.com

Out of scope:
- Internal tools
- Third-party services
- Legacy systems
```

**Extracted Targets**:
```
In Scope:
- domain: example.com (website) - priority: medium
- domain: *.example.com (website) - wildcard: true - priority: high
- url: api.example.com/v1/* (api) - priority: high
- url: api.example.com/v2/* (api) - priority: high
- app: Example (mobile_ios) - priority: medium
- app: Example (mobile_android) - priority: medium
- bucket: *.s3.amazonaws.com (cloud_service) - wildcard: true - priority: high
- cdn: cdn.example.com (cloud_service) - priority: high

Out of Scope:
- category: internal_tools
- category: third_party
- category: legacy_systems
```

### Example 3: Scope with Restrictions

**Raw Text**:
```
In Scope (with restrictions):
- Main domain: example.com
  - Rate limited to 10 requests per second
  - No DoS testing
  - Business hours only (9 AM - 5 PM EST)
  
- API endpoints: api.example.com
  - No testing of /admin/* endpoints
  - Staging server: api-staging.example.com (testing allowed outside business hours)
  
- Mobile app: Example
  - Version 2.0 and above only
  - No reverse engineering
```

**Extracted Targets**:
```
In Scope:
- target: example.com
  type: website
  priority: high
  restrictions:
    rate_limit: 10 req/sec
    prohibited: ["DoS", "abuse"]
    business_hours_only: true
    
- target: api.example.com
  type: api
  priority: critical
  restrictions:
    exclude_paths: ["/admin/*"]
    
- target: api-staging.example.com
  type: api
  priority: medium
  restrictions:
    outside_business_hours_only: true
    
- target: Example
  type: mobile_ios
  priority: medium
  restrictions:
    min_version: "2.0"
    prohibited: ["reverse_engineering"]
```

---

## Metadata Extraction Examples

### Example 1: Bounty Metadata

**Extracted**:
```python
{
  "bounty_ranges": {
    "critical": "$1000",
    "high": "$500",
    "medium": "$250",
    "low": "$100"
  },
  "asset_categories": ["website", "api", "mobile_ios", "mobile_android"],
  "auth_required": True,
  "severity_levels": [
    {"level": "critical", "bounty": "$1000"},
    {"level": "high", "bounty": "$500"},
    {"level": "medium", "bounty": "$250"},
    {"level": "low", "bounty": "$100"}
  ],
  "submission_requirements": [
    "Include proof of concept",
    "Provide reproduction steps",
    "Attach relevant logs"
  ],
  "prohibited_actions": [
    "DoS/DDoS attacks",
    "Brute force attacks",
    "Social engineering",
    "Physical testing"
  ]
}
```

### Example 2: Asset Classification

```python
{
  "asset_categories": [
    "website",
    "api",
    "mobile_ios",
    "mobile_android",
    "cloud_service"
  ],
  "classified_assets": {
    "website": ["domain.com", "www.example.com"],
    "api": ["api.example.com", "api-v2.example.com"],
    "mobile_ios": ["Example App"],
    "mobile_android": ["Example App"],
    "cloud_service": ["*.s3.amazonaws.com"]
  }
}
```

---

## Normalization Examples

### Domain Normalization

```
Input:  "WWW.EXAMPLE.COM"
Output: "example.com" (base domain, lowercase)

Input:  "*.api.example.com"
Output: "*.api.example.com" (wildcard preserved)

Input:  "https://api.example.com/v1/*"
Output: "api.example.com/v1/*" (protocol removed, path preserved)
```

### IP Range Normalization

```
Input:  "192.168.1.0/24"
Output: "192.168.1.0/24" (CIDR notation validated)

Input:  "10.0.0.1 - 10.0.0.255"
Output: "10.0.0.0/24" (range converted to CIDR)

Input:  "172.16.0.0 to 172.31.255.255"
Output: "172.16.0.0/12" (large range to CIDR)
```

### API Endpoint Normalization

```
Input:  "https://api.example.com/v1/users/*"
Output: "api.example.com/v1/users/*"

Input:  "API endpoints: /api/v2/*, /graphql"
Output: ["api.example.com/api/v2/*", "api.example.com/graphql"]

Input:  "https://api-staging.example.com:8443/api/*"
Output: "api-staging.example.com/api/*"
```

---

## Security & Rate Limiting

### Rate Limiting Strategy

```
Global Rate Limit: 2 requests per second
  - Enforced via asyncio sleep in scraper
  - Prevents aggressive crawling
  - Respects Bugcrowd's terms

Per-Request Timeout: 30 seconds
  - Prevents hanging connections
  - Immediate failure on slowness

Retry Strategy:
  - Max 3 attempts
  - Exponential backoff: 2s, 4s, 8s
  - Respects 429 (rate limit) responses
  - Backs off on 429 instead of retrying immediately
```

### URL Security Validation

```python
# REJECTED URLs (private pages):
- https://bugcrowd.com/settings/
- https://bugcrowd.com/admin/
- https://bugcrowd.com/account/
- https://bugcrowd.com/api/v1/
- https://bugcrowd.com/programs/123?secret=abc

# ACCEPTED URLs (public pages):
- https://bugcrowd.com/programs/example
- https://bugcrowd.com/programs/example/scope
- https://bugcrowd.com/programs/example/about
```

### Data Validation

```python
# All targets must:
1. Pass ScopeValidator checks
2. Be explicitly mentioned in source text (not invented)
3. Have valid asset type classification
4. Pass domain/IP/URL pattern validation
5. Be deduplicated before storage

# AI Safety:
1. Claude prompt includes explicit "DO NOT invent" instruction
2. Low temperature (0.2) for deterministic output
3. All Claude responses validated as JSON
4. All extracted targets validated
5. Suspicious entries flagged for manual review
```

---

## Troubleshooting Guide

### Issue: "Failed to fetch engagement page"

**Causes**:
- URL is not a Bugcrowd domain
- Page doesn't exist (404)
- Network timeout
- Rate limited (429)

**Solutions**:
```
1. Verify URL is public: https://bugcrowd.com/programs/[name]
2. Check URL doesn't have query parameters: remove ?utm_source, etc
3. Wait a minute and retry (rate limit backoff)
4. Verify Bugcrowd site is accessible
```

### Issue: "Private or internal Bugcrowd URLs are not supported"

**Causes**:
- URL contains /settings, /admin, /account, /api/
- Attempting to bypass public-only restriction

**Solutions**:
```
1. Use public engagement page URL only
2. This is intentional security feature
3. Share the public Bugcrowd link instead
```

### Issue: "Extraction confidence is low (< 70%)"

**Causes**:
- HTML structure is unusual
- Scope text is poorly formatted
- Page layout differs from expected

**Solutions**:
```
1. Check program page displays correctly in browser
2. Manually review extracted targets
3. Wait for manual verification step
4. Edit assets directly in system
```

### Issue: "Some targets failed validation"

**Causes**:
- Invalid domain format
- Conflicting with existing validated scope
- Target violates scope rules

**Solutions**:
```
1. Review validation_error field for details
2. Manually normalize target format
3. Check against existing scope validator rules
4. Edit scope_data directly if needed
```

### Issue: Claude API Error

**Causes**:
- API key missing/invalid
- Rate limit exceeded
- API down

**Solutions**:
```
1. Verify ANTHROPIC_API_KEY in .env
2. Check Claude API status
3. Retry after waiting
4. Check logs for detailed error
```

---

## Integration Checklist

- [x] BugcrowdProgram model created and migrated
- [x] BugcrowdScraper with rate limiting
- [x] ScopeExtractor with Claude AI
- [x] MetadataAnalyzer with AI
- [x] BugcrowdIntegrationService orchestration
- [x] API endpoints registered
- [x] URL security validation
- [x] Target normalization
- [x] Multi-tenant isolation
- [x] Audit trail (sync history)
- [ ] Frontend UI for ingestion
- [ ] Automatic recon workflow trigger
- [ ] Asset inventory linking
- [ ] Monitoring rule creation

---

## Next Steps

1. **Frontend UI**: Create Bugcrowd engagement ingestion form
2. **Automation**: Trigger recon workflows on asset import
3. **Monitoring**: Create monitoring rules for ingested programs
4. **Alerts**: Notify on scope changes
5. **Advanced Parsing**: Handle more complex scope formats
6. **Multi-Program**: Batch import multiple Bugcrowd programs
7. **Comparison**: Highlight scope changes between syncs

---

## Security Attestation

✅ **No private scraping** - Only public engagement pages  
✅ **No auth bypass** - Never attempts to login  
✅ **Rate limiting** - Respects platform limits (2 req/sec)  
✅ **URL validation** - Rejects private paths  
✅ **Target validation** - All targets pass scope validator  
✅ **No data invention** - Claude prompt forbids fabrication  
✅ **Workspace isolation** - organization_id enforced throughout  
✅ **Audit trail** - Full sync history preserved  
✅ **Error handling** - Graceful failures, logged appropriately  

---

**Phase F Complete** 🎯
