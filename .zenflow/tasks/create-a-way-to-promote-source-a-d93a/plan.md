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

### [ ] Step: Implement Core Helper Functions (db.py)

Add helper functions to `db.py` for nested field access and transformation tracking:

1. **`get_nested_field(obj, path)`**: Safely access nested dictionary fields using dot notation (e.g., `"sources.kaggle.orbital_band"`)
2. **`set_nested_field(obj, path, value)`**: Safely set nested dictionary fields using dot notation
3. **`record_transformation(doc, source_field, target_field, value)`**: Add transformation record to `metadata.transformations` array

**Verification**:
- Test with sample document structures
- Verify edge cases: missing intermediate keys, null values, deeply nested paths

---

### [ ] Step: Implement CLI Script Skeleton (promote_attributes.py)

Create `promote_attributes.py` with:

1. Argument parsing using `argparse`:
   - Positional: source_field, target_field
   - Optional: --dry-run, --all, --filter, --yes, --reason, --verbose
2. MongoDB connection setup
3. Basic validation (required arguments provided)
4. Help text and usage examples

**Verification**:
- Run with `--help` flag
- Test argument parsing with various input combinations

---

### [ ] Step: Implement Document Query and Filtering

Add functionality to query and filter documents:

1. Parse filter expressions (e.g., `"identifier=NORAD-12345"`, `"canonical.country_of_origin=USA"`)
2. Build MongoDB query from filter
3. Query documents that have the source field
4. Handle cases where source field doesn't exist

**Verification**:
- Test various filter patterns
- Verify correct document selection

---

### [ ] Step: Implement Field Promotion Logic

Implement core promotion functionality:

1. Extract value from source field using `get_nested_field()`
2. Set value to target field using `set_nested_field()`
3. Record transformation using `record_transformation()`
4. Update document in MongoDB
5. Handle errors gracefully (skip document, log error)

**Verification**:
- Test with single document
- Verify canonical field updated
- Verify transformation history recorded

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
