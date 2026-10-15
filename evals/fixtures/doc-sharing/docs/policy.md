# Sharing policy

This is the promise to customers. The code must match it.

A document has one owner (the account that created it). Any other account gets a role on the
document from a share. A share may carry an `until` date.

| role      | read | comment | edit | share | delete |
|-----------|------|---------|------|-------|--------|
| viewer    | yes  | no      | no   | no    | no     |
| commenter | yes  | yes     | no   | no    | no     |
| editor    | yes  | yes     | yes  | no    | no     |
| owner     | yes  | yes     | yes  | yes   | yes    |

Rules that override the table:

1. A suspended account can do nothing, including on documents it owns.
2. A support account (`support = True`) can read any document and can never comment on, edit,
   share, or delete any document.
3. A share expires at the start of its `until` day: a share with `until = 2026-10-15` grants
   nothing on 2026-10-15 or any later day.
4. A denied action raises `Forbidden`, is recorded in the audit log, and has no other effect.
