# Local notes project

## Requirements
- Define a versioned JSON note format containing an ID, title, and body.
- Save a note as UTF-8 JSON in a user-selected local directory.
- Reopen a saved note with its ID, title, and body unchanged.
- Reject unsupported format versions with a clear error.

## Validation
- Use a temporary directory to exercise a save-and-reopen round trip.
- Verify that an unsupported version is rejected.

## Decisions
- User-interface design is outside this plan; provide a Python library first.
