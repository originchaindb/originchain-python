# Releasing this SDK

The Release workflow runs only from main, with an explicit version that must
match the committed package metadata and have no existing tag. It reruns the
compatibility matrix and requires live E2E tests. A missing test credential or a
network failure fails release verification. The negative SQL test only passes
on a real 400/422 server response.

For npm/PyPI, build artifacts are produced once and the same archive is uploaded
by the publish job. Configure either the existing registry token secret or a
registry trusted publisher for this repository's release.yml workflow and
production-npm / production-pypi environment. Existing environment protection
rules are respected. Never put token values in source, logs or release notes.

Dispatch Release with the intended X.Y.Z version after changes are merged.
The workflow creates the public version tag and GitHub Release only after the
checks and package upload pass. Go publication consists of that version tag.
Verify public package metadata and an install/import after the workflow ends.

Registry trusted-publisher configuration is separate from adding this workflow:
https://docs.npmjs.com/trusted-publishers/
https://docs.pypi.org/trusted-publishers/using-a-publisher/
