from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from unittest.mock import patch


sys.dont_write_bytecode = True
spec = spec_from_file_location("cleanup", Path(__file__).parents[1] / ".github/scripts/clean-registry.py")
cleanup = module_from_spec(spec)
spec.loader.exec_module(cleanup)


def image(version_id, *tags):
    return {"id": version_id, "metadata": {"container": {"tags": list(tags)}}}


assert cleanup.stable_version("0.2.2") == (0, 2, 2)
assert cleanup.stable_version("0.2.2-testing.1") is None
assert cleanup.stable_version("v0.2.2") is None
assert cleanup.stable_version("0.02.2") is None
assert cleanup.obsolete_testing("0.2.2-testing.10", (0, 2, 2))
assert cleanup.obsolete_testing("0.2.1-testing.1", (0, 2, 2))
assert not cleanup.obsolete_testing("0.2.3-testing.1", (0, 2, 2))
assert not cleanup.obsolete_testing("0.10.0-testing.1", (0, 2, 2))
assert not cleanup.obsolete_testing("0.2.2-rc.1", (0, 2, 2))
assert cleanup.candidates([
    image(1, "0.2.2-testing.1"),
    image(2, "0.2.1-testing.1", "0.2.2-testing.2"),
    image(3, "0.2.2-testing.3", "0.2.2"),
    image(4, "0.2.1"),
    image(5, "0.2.3-testing.1"),
    image(6),
    image(7, "0.2.2-testing.4", "main", "latest"),
    image(8, "0.2.2-testing.5", "feature-branch"),
], (0, 2, 2)) == [image(1, "0.2.2-testing.1"), image(2, "0.2.1-testing.1", "0.2.2-testing.2")]

catalog = [{"source": "ghcr.io/francio87/borgbackupserver", "versions": [
    {"tag": "0.2.2", "testing": False},
    {"tag": "0.2.3-testing.1", "testing": True},
]}]
assert cleanup.catalog_ready(catalog, "0.2.2", {"0.2.2-testing.1"})
assert not cleanup.catalog_ready(catalog, "0.2.3", set())
assert not cleanup.catalog_ready(catalog, "0.2.2", {"0.2.3-testing.1"})
assert not cleanup.catalog_ready([], "0.2.2", set())

scope = {"REPOSITORY": "francio87/ns8-borgbackupserver", "PACKAGE_OWNER": "francio87", "PACKAGE_OWNER_TYPE": "User"}
with patch.dict(cleanup.os.environ, scope, clear=True):
    cleanup.check_scope()
for other in [{"PACKAGE_OWNER": "NethServer"}, {"REPOSITORY": "NethServer/ns8-borgbackupserver"},
              {"PACKAGE_OWNER_TYPE": "Organization"}]:
    with patch.dict(cleanup.os.environ, {**scope, **other}, clear=True):
        try:
            cleanup.check_scope()
        except SystemExit:
            pass
        else:
            raise AssertionError("Cleanup accepted a repository outside francio87")

print("Release cleanup policy checks passed")


def release(tag, date, testing=False):
    return {"tagName": tag, "createdAt": date, "isPrerelease": testing}


releases = [release("0.2.1", "2026-10-01"),
            release("0.2.2-testing.1", "2026-10-02", True),
            release("0.2.2", "2026-10-03"),
            release("0.2.3-testing.1", "2026-10-04", True)]
assert cleanup.prereleases_between(releases, "0.2.2") == ["0.2.2-testing.1"]
assert cleanup.prereleases_between(releases, "0.2.1") == []
try:
    cleanup.prereleases_between([*releases, release("0.3.0-testing.1", "2026-10-02", True)], "0.2.2")
except SystemExit:
    pass
else:
    raise AssertionError("Official cleanup accepted a future testing release")

versions = [image(1, "0.2.2-testing.1"), image(2, "0.2.2"), image(3, "0.2.3-testing.1")]
from io import BytesIO

for dry_run in ["true", "false"]:
    with patch.dict(cleanup.os.environ, {**scope, "DRY_RUN": dry_run}, clear=True), \
            patch.object(cleanup, "api", side_effect=[versions, {"draft": False, "prerelease": False}]), \
            patch.object(cleanup.urllib.request, "urlopen", return_value=BytesIO(cleanup.json.dumps(catalog).encode())), \
            patch.object(cleanup.subprocess, "check_output", return_value=cleanup.json.dumps(releases)), \
            patch.object(cleanup.subprocess, "run") as mutations:
        cleanup.main()
        if dry_run == "true":
            mutations.assert_not_called()
        else:
            assert mutations.call_args_list == [
                ((["gh", "api", "--method", "DELETE", cleanup.VERSIONS_PATH + "/1"],), {"check": True}),
                ((["gh", "ns8-release-module", "clean", "--repo", cleanup.REPOSITORY,
                   "--release-name", "0.2.2"],), {"check": True}),
            ]

with patch.dict(cleanup.os.environ, {**scope, "DRY_RUN": "false"}, clear=True), \
        patch.object(cleanup, "api", side_effect=[versions, {"draft": False, "prerelease": False}]), \
        patch.object(cleanup.urllib.request, "urlopen", return_value=BytesIO(b'[]')), \
        patch.object(cleanup.subprocess, "run") as mutations:
    cleanup.main()
    mutations.assert_not_called()

with patch.dict(cleanup.os.environ, {**scope, "PACKAGE_REF": "codex/old-branch", "DRY_RUN": "false"}, clear=True), \
        patch.object(cleanup, "api", return_value=[image(1, "codex-old-branch"), image(2, "codex-old-branch", "0.2.2")]), \
        patch.object(cleanup.subprocess, "run") as mutations:
    cleanup.main()
    mutations.assert_called_once_with(["gh", "api", "--method", "DELETE", cleanup.VERSIONS_PATH + "/1"], check=True)

for protected in ["0.2.2", "main", "latest", "master"]:
    with patch.dict(cleanup.os.environ, {**scope, "PACKAGE_REF": protected}, clear=True), \
            patch.object(cleanup, "api") as reads:
        try:
            cleanup.main()
        except SystemExit:
            pass
        else:
            raise AssertionError("Protected tag was accepted")
        reads.assert_not_called()

print("Release cleanup execution checks passed")

from types import SimpleNamespace

for status in [0, 2, 128]:
    with patch.dict(cleanup.os.environ, {**scope, "CHECK_BRANCH": "true", "PACKAGE_REF": "codex/old-branch", "DRY_RUN": "false"}, clear=True), \
            patch.object(cleanup, "api", return_value=[image(1, "codex-old-branch")]) as reads, \
            patch.object(cleanup.subprocess, "run", side_effect=[SimpleNamespace(returncode=status, stderr="network error"), None]) as commands:
        if status == 128:
            try:
                cleanup.main()
            except SystemExit:
                pass
            else:
                raise AssertionError("Network failure was treated as branch deletion")
        else:
            cleanup.main()
        commands.assert_any_call(["git", "ls-remote", "--exit-code", "--heads",
                                  "https://github.com/francio87/ns8-borgbackupserver.git",
                                  "refs/heads/codex/old-branch"], capture_output=True, text=True)
        if status == 2:
            assert commands.call_count == 2
            reads.assert_called_once()
        else:
            assert commands.call_count == 1
            reads.assert_not_called()

print("Deleted-branch publication checks passed")

from datetime import datetime, timezone

now = datetime(2026, 10, 10, tzinfo=timezone.utc)
old = '2026-10-01T00:00:00Z'
recent = '2026-10-09T00:00:00Z'

def untagged_image(version_id, updated=old, *tags):
    return {**image(version_id, *tags), 'name': f'sha256:{version_id}', 'updated_at': updated}

untagged_versions = [untagged_image(1), untagged_image(2, recent),
                     untagged_image(3, old, '0.2.1'), untagged_image(4),
                     untagged_image(5, old, 'main'), untagged_image(6), untagged_image(7)]
manifest_data = {'sha256:5': {'manifests': [{'digest': 'sha256:4'}]},
                 'sha256:7': {'subject': {'digest': 'sha256:6'}}}
inspect_manifest = lambda digest: manifest_data.get(digest, {})
assert cleanup.untagged_candidates(untagged_versions, now, inspect_manifest) == [untagged_versions[0], untagged_versions[6]]
assert cleanup.untagged_candidates(untagged_versions, now, inspect_manifest, 0) == [untagged_versions[0], untagged_versions[1], untagged_versions[6]]

with patch.object(cleanup, 'api', return_value={'total_count': 1}), \
        patch.object(cleanup.urllib.request, 'urlopen') as registry:
    cleanup.prune_untagged(False, 0)
    registry.assert_not_called()

for dry_run, changed in [(True, False), (False, False), (False, True)]:
    candidate = untagged_image(1)
    current = untagged_image(1, old, '0.2.1') if changed else candidate
    responses = [BytesIO(b'{"token":"test-registry-token"}'), BytesIO(b'{"schemaVersion":2}')]
    with patch.object(cleanup, 'api', side_effect=[{'total_count': 0}] * 3 + [[candidate], current]), \
            patch.object(cleanup.urllib.request, 'urlopen', side_effect=responses), \
            patch.object(cleanup.subprocess, 'run') as mutations:
        cleanup.prune_untagged(dry_run, 7)
        if dry_run or changed:
            mutations.assert_not_called()
        else:
            mutations.assert_called_once_with(['gh', 'api', '--method', 'DELETE', cleanup.VERSIONS_PATH + '/1'], check=True)

with patch.object(cleanup, 'api', side_effect=[{'total_count': 0}] * 3 + [[untagged_image(1)]]), \
        patch.object(cleanup.urllib.request, 'urlopen', side_effect=[BytesIO(b'{"token":"test-token"}'), OSError('Registry unavailable')]), \
        patch.object(cleanup.subprocess, 'run') as mutations:
    try:
        cleanup.prune_untagged(False, 7)
    except OSError:
        pass
    else:
        raise AssertionError('Unreadable manifests must prevent deletion')
    mutations.assert_not_called()

print('Untagged cleanup safety checks passed')
