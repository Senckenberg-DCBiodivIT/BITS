# TIB API Comparison: Current Search vs V2 Entities

## Overview

This document compares the current search API (`/api/search?`) with the v2 entities API (`/api/v2/entities?search=`) and explains what would happen if you switch between them.

## Current API (`/api/search?`)

### URL Structure
```
https://api.terminology.tib.eu/api/search?q={search_term}&ontology={ontology_name}
```

### Response Structure
```json
{
  "response": {
    "docs": [
      {
        "iri": "http://www.eionet.europa.eu/gemet/concept/8405",
        "ontology_name": "gemet",
        "ontology_prefix": "GEMET",
        "short_form": "GEMET_8405",
        "description": ["To carry out an examination..."],
        "label": "test",
        "obo_id": "GEMET:8405",
        "type": "class"
      }
    ],
    "numFound": 6624,
    "start": 0
  },
  "responseHeader": {
    "QTime": 18,
    "status": 0
  },
  "facet_counts": { ... }
}
```

### Key Fields Used by BITS
- `docs` - Array of search results
- `ontology_name` - Name of the ontology
- `short_form` - Short identifier
- `label` - String label
- `iri` - Internationalized Resource Identifier
- `type` - String type

## V2 API (`/api/v2/entities?search=`)

### URL Structure
```
https://api.terminology.tib.eu/api/v2/entities?search={search_term}&ontologyId={ontology_id}
```

### Response Structure
```json
{
  "page": 0,
  "numElements": 3,
  "totalPages": 3526,
  "totalElements": 10578,
  "elements": [
    {
      "appearsIn": ["fibo"],
      "curie": "TestamentaryTrust",
      "definition": ["trust established in accordance with..."],
      "iri": "https://spec.edmcouncil.org/fibo/ontology/BE/Trusts/Trusts/TestamentaryTrust",
      "isDefiningOntology": false,
      "isObsolete": false,
      "label": ["testamentary trust"],
      "linkedEntities": { ... },
      "numDescendants": 0.0,
      "ontologyId": "fibo",
      "ontologyIri": "https://spec.edmcouncil.org/fibo/ontology/AboutFIBOProd/",
      "ontologyPreferredPrefix": "fibo-prod",
      "shortForm": "TestamentaryTrust",
      "type": ["class", "entity"]
    }
  ],
  "facetFieldsToCounts": {}
}
```

### Key Fields Used by BITS
- `elements` - Array of search results (different from `docs`)
- `ontologyId` - Name of the ontology (different from `ontology_name`)
- `shortForm` - Short identifier (different from `short_form`)
- `label` - Array of strings (different from single string)
- `iri` - Internationalized Resource Identifier
- `type` - Array of strings (different from single string)

## Key Differences

| Aspect | Current API | V2 API | Impact |
|--------|-------------|--------|---------|
| **Results Array** | `response.docs` | `elements` | ❌ Breaking change |
| **Ontology Field** | `ontology_name` | `ontologyId` | ❌ Breaking change |
| **Short Form Field** | `short_form` | `shortForm` | ❌ Breaking change |
| **Label Format** | String | Array of strings | ❌ Breaking change |
| **Type Format** | String | Array of strings | ❌ Breaking change |
| **Response Structure** | Nested under `response` | Direct at root | ❌ Breaking change |
| **Pagination** | `numFound`, `start` | `numElements`, `page` | ❌ Breaking change |

## What Would Happen If You Switch

### ❌ **Immediate Issues:**

1. **Code would break** because the response structure is completely different
2. **Field mapping errors** - code expects `ontology_name` but gets `ontologyId`
3. **Array vs String errors** - code expects string `label` but gets array
4. **Missing fields** - code looks for `docs` but finds `elements`

### ✅ **Benefits of V2 API:**

1. **More comprehensive data** - includes definitions, linked entities, hierarchy info
2. **Better pagination** - more detailed pagination controls
3. **Richer metadata** - includes ontology IRIs, preferred prefixes
4. **Future-proof** - likely the newer, maintained endpoint

### 🔧 **Required Changes:**

To switch to V2 API, you would need to:

1. **Update response processing** in `__perform_query_search()`
2. **Transform field names** (`ontologyId` → `ontology_name`)
3. **Handle array fields** (take first element from `label` array)
4. **Update URL construction** (different parameter names)

## Implementation Strategy

### Option 1: Gradual Migration
- Keep current API as default
- Add V2 API as experimental feature
- Test with transformation layer

### Option 2: Direct Switch
- Update all code to handle V2 response format
- Modify field mappings throughout the codebase
- Update URL construction logic

### Option 3: Hybrid Approach
- Create adapter pattern to support both APIs
- Allow configuration to choose which API to use
- Maintain backward compatibility

## Recommendation

The V2 API appears to be more feature-rich and future-proof, but switching requires significant code changes. Consider implementing a transformation layer (as shown in the `__perform_query_search_v2` method) to handle the response format differences while maintaining the existing code structure.