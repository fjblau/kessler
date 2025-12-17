# Spec and build

## Configuration
- **Artifacts Path**: {@artifacts_path} → `.zenflow/tasks/{task_id}`

---

## Agent Instructions

Ask the user questions when anything is unclear or needs their input. This includes:
- Ambiguous or incomplete requirements
- Technical decisions that affect architecture or user experience
- Trade-offs that require business context

Do not make assumptions on important decisions — get clarification first.

---

## Workflow Steps

### [x] Step: Technical Specification
<!-- chat-id: d2e6265b-2897-4be2-b165-830318651fab -->

**Completed**: Created comprehensive technical specification in `spec.md`
- **Complexity**: Medium
- **Files to create**: `promote_attributes.py`
- **Files to modify**: `db.py`
- **Key features**: Field promotion, transformation history, dry-run mode, filtering

---

### [x] Step: Implement Core Helper Functions (db.py)
<!-- chat-id: 99be571b-b64b-4f0c-92fc-647b67ac6f32 -->

**Completed**: Added three helper functions to `db.py`:
1. **`get_nested_field(obj, path)`**: Safely access nested dictionary fields using dot notation
2. **`set_nested_field(obj, path, value)`**: Safely set nested dictionary fields using dot notation  
3. **`record_transformation(doc, source_field, target_field, value, reason)`**: Add transformation record to `metadata.transformations` array

**Verification**:
- ✓ All tests passed (test_helpers_standalone.py)
- ✓ Verified edge cases: missing intermediate keys, null values, deeply nested paths, non-dict values

---

### [x] Step: Implement CLI Script Skeleton (promote_attributes.py)
<!-- chat-id: ac24db9d-ffd0-4f75-a5c0-564adca6e190 -->

**Completed**: Created `promote_attributes.py` with full CLI skeleton:
1. **Argument parsing** using `argparse`:
   - Positional: source_field, target_field
   - Optional: --dry-run, --all, --filter, --yes, --reason, --verbose
2. **MongoDB connection setup** using db.py functions
3. **Basic validation** for required arguments and filter format
4. **Help text and usage examples** in docstring and epilog

**Verification**:
- ✓ --help flag displays proper usage information
- ✓ Required arguments validated
- ✓ Optional flags work correctly (--dry-run, --verbose, --all, --yes, --reason, --filter)
- ✓ Filter parsing validates format (field=value)
- ✓ Field path normalization (auto-adds "sources." prefix)
- ✓ MongoDB connection and document counting works
- ✓ Successfully tested with actual MongoDB instance (found 14,890 documents)

---

### [x] Step: Implement Document Query and Filtering
<!-- chat-id: c7db1c7f-a580-4e3a-8759-e7cbb0101083 -->

**Completed**: Implemented comprehensive document query and filtering functionality:
1. **Enhanced `parse_filter()`**: Parse filter expressions with support for:
   - Simple equality: `"identifier=NORAD-12345"`
   - Multiple filters: `"field1=value1,field2=value2"`
   - Numeric values (auto-conversion): `"count=123"`, `"altitude=350.5"`
   - Nested fields: `"canonical.country_of_origin=USA"`
2. **Added `build_query()`**: Build MongoDB query from source field and optional filters
3. **Added `query_documents()`**: Query and retrieve matching documents with optional limit
4. **Handle missing source field**: Returns 0 documents when source field doesn't exist

**Verification**:
- ✓ All unit tests passed (test_query_filtering.py)
- ✓ Tested with actual MongoDB instance:
  - No filter: Found 14,890 documents
  - Single filter: `identifier=2025-206B` → 1 document
  - Nested filter: `canonical.country_of_origin=Russian Federation` → 214 documents
  - Multiple filters: Both combined → 1 document
  - --all flag: Retrieved all 214 documents (vs. default 5)
- ✓ Edge cases: empty filter, invalid format (raises ValueError), missing source field

---

### [x] Step: Implement Field Promotion Logic
<!-- chat-id: 37b32bd8-7a77-4cd5-9ea3-25e84b2feadb -->

**Completed**: Implemented core field promotion functionality with three new functions:
1. **`promote_document()`**: Core promotion logic that:
   - Extracts value from source field using `get_nested_field()`
   - Sets value to target field using `set_nested_field()`
   - Records transformation using `record_transformation()`
   - Handles errors gracefully (returns status dict with success/error)
2. **`update_document_in_db()`**: Updates document in MongoDB using `replace_one()`
3. **`process_documents()`**: Batch processor that:
   - Iterates through documents
   - Calls `promote_document()` for each
   - Updates database (unless dry-run mode)
   - Collects statistics (updated, skipped, errors)
   - Provides progress output

**Verification**:
- ✓ Test with single document (test_promotion.py passed)
- ✓ Verified canonical field updated correctly
- ✓ Verified transformation history recorded with all metadata (timestamp, source, target, value, reason)
- ✓ Tested dry-run mode (no database changes made)
- ✓ Tested actual promotion (document updated successfully in MongoDB)
- ✓ Tested batch processing (5 documents processed successfully)
- ✓ Tested error handling (missing source field returns 0 documents)
- ✓ Verified custom reason appears in transformation history

---

### [ ] Step: Implement Batch Processing and Progress Reporting

Add batch processing capabilities:

1. Process multiple documents efficiently
2. Show progress bar or counter for large batches
3. Collect statistics (updated, skipped, errors)
4. Implement confirmation prompts for large operations (>10 documents)

**Verification**:
- Test with small batch (< 10 documents)
- Test with large batch (> 100 documents)
- Verify statistics reporting

---

### [ ] Step: Implement Dry-Run Mode and Safety Features

Add safety features:

1. Implement `--dry-run` flag to preview without applying
2. Show sample of changes (first 5-10 documents)
3. Add confirmation prompts unless `--yes` flag provided
4. Validate source and target field paths before processing

**Verification**:
- Run with `--dry-run` flag
- Verify no database changes made
- Test confirmation prompts

---

### [ ] Step: Testing and Documentation

Final testing and documentation:

1. Test all CLI options and combinations
2. Test edge cases:
   - Source field doesn't exist
   - Source field is null/empty
   - Target field already exists
   - Nested fields
   - Large batches
3. Add usage examples to script docstring
4. Test with actual MongoDB instance

**Verification**:
- Run through all test scenarios
- Verify transformation history is correct
- Confirm no data corruption

---

### [ ] Step: Write Implementation Report

After completing all implementation steps, write a report to `{@artifacts_path}/report.md` describing:
- What was implemented
- How the solution was tested
- Example usage commands
- The biggest issues or challenges encountered
