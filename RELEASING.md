# Releasing ns8-borgbackupserver

Maintainer notes for versioning, publishing module images, and cleaning up the registry.

## Releases and testing cleanup

Follow the [NethServer versioning rules](https://handbook.nethserver.org/version_numbering/):
use immutable tags such as `0.2.2-testing.1`, `0.2.2-testing.2`, then `0.2.2` for stable.
Publish testing releases as GitHub **pre-releases**, so the NS8 workflows classify them correctly.
Use the official release tool with our repository explicitly selected:

```bash
gh extension install NethServer/gh-ns8
gh ns8 module-release create --repo francio87/ns8-borgbackupserver --testing 0.2.2-testing.1
gh ns8 module-release create --repo francio87/ns8-borgbackupserver 0.2.2
```

Without `--release-refs`, GitHub uses the repository's default branch (`main`).
To publish a testing release from another branch without merging it, switch to that
branch, commit the changes, and push them before creating the release:

```bash
git switch my-testing-branch
git push origin my-testing-branch
gh ns8 module-release create \
  --repo francio87/ns8-borgbackupserver \
  --testing \
  --release-refs "$(git rev-parse HEAD)" \
  0.2.2-testing.1
```

Replace the branch and version with your own. `--release-refs` selects the committed
source for the tag and pre-release; uncommitted changes are not included. Publication
builds that tagged commit. Testing numbers are shared across all branches: use the
next unused number (for example, `0.2.2-testing.2`) and never reuse an existing tag.
The catalog advertises the highest testing SemVer newer than stable, regardless of
its source branch. Publish the release workflow changes on `main` before using this
procedure.

Development images are published on branch pushes; versioned images are published
when a GitHub release is published. Pushing a Git tag alone does not publish a release
image. This avoids rebuilding the same version on both tag push and release publication.
Do not rerun publication for an existing version; create a new version instead.
Do not create releases from
Actions with the default `GITHUB_TOKEN` and expect another workflow to publish the
image: those events do not trigger downstream workflows. Verify image publication
and application tests before announcing a release. `latest` follows `main`, not stable.

The catalog at `https://francio87.github.io/ns8-repomd/` refreshes every six hours.
It advertises the latest stable and, when newer, the latest testing. On NS8 Core 3.0+
reload repositories, then use **Software Center → Installed → Instances → ⋮ → Update to testing version**.
Instances installed from development tags such as `main` require a manual update.

After successful publication, on a published release, and daily, **Clean up registry**
checks that the newest stable GHCR image has a published stable GitHub release and
is present in the public catalog. It deletes GHCR versions containing only
`X.Y.Z-testing.N` tags whose base version is at most that stable version. Digests
sharing a stable or any other tag are preserved. The official
`gh ns8 module-release clean` command removes GitHub pre-releases created between
the previous and selected stable release. **Git tags and stable images are retained.**
Cleanup stops if that date window contains a newer or unrecognized pre-release.
Testing images newer than stable are retained; only the latest is advertised.
Deleting obsolete testing images prevents reinstalling or restoring those versions.

Deleting a branch also cleans its single-tag GHCR image. Stable tags, `main`, `master`
and `latest` are protected. Daily and empty-ref manual cleanup also removes untagged
versions last updated more than seven days ago, after inspecting every image manifest.
Publication and cleanup share a concurrency group so they do not modify the registry
at the same time. Digests referenced by other manifests (including multiarch images and artifact subjects)
are retained. Cleanup is deferred while publication is running, queued, or waiting,
and each candidate is checked again for tags and metadata changes before deletion.
The workflow needs package admin access for its `GITHUB_TOKEN`.
Use **Run workflow** with the default **dry_run** enabled to preview cleanup; leave
**ref** empty for release cleanup, or provide a removed branch name for branch cleanup.
For an immediate manual cleanup of already reviewed untagged versions, set
**untagged_keep_days** to `0`; otherwise leave its default of `7`. The dry run applies
to both testing and untagged cleanup. Optionally set **untagged_version_ids** to a
comma-separated list of reviewed GHCR version IDs to limit manual untagged cleanup.
Retired digests are no longer available for
direct downloads or restoring an old development build by digest.
Publication and cleanup are restricted to `francio87/ns8-borgbackupserver` and
`ghcr.io/francio87/borgbackupserver`; official NethServer repositories are dependencies only.

Branch images and versioned testing releases have separate lifecycles:

| Event | Development image | Versioned testing image, Git tag and GitHub pre-release |
| --- | --- | --- |
| Merge into `main`, keeping the branch | `main` and `latest` are rebuilt; the branch image remains | Unchanged; merging does not publish a stable release |
| Delete the branch, merged or abandoned | Cleanup deletes its single-tag GHCR version | Unchanged; the release tag still identifies the tested commit |
| Publish the corresponding stable | Branch images are not affected | Obsolete testing images and pre-releases are cleaned after the catalog is ready; Git tags remain |

Enable automatic head-branch deletion for merged pull requests if their development
images should be cleaned automatically. Cleanup checks branch existence again when
a branch build completes, removing an image published after the branch was deleted.
Shared digests are retained; obsolete untagged versions are handled by daily cleanup,
so deleting a branch does not immediately reclaim all storage from its previous builds.
Abandoning a branch does not withdraw its testing release: it can still be advertised
until a newer version supersedes it. Withdraw such a release separately if necessary.

