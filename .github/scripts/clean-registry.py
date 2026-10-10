#!/usr/bin/env python3
"""Preserve stable images and Git tags; prune testing superseded by a stable."""

import json
import os
import re
import subprocess
import urllib.request
import argparse
from datetime import datetime, timedelta, timezone


NUMBER = r"(0|[1-9][0-9]*)"
STABLE = re.compile(rf"{NUMBER}\.{NUMBER}\.{NUMBER}")
TESTING = re.compile(rf"{NUMBER}\.{NUMBER}\.{NUMBER}-testing\.{NUMBER}")
CATALOG = "https://francio87.github.io/ns8-repomd/repodata.json"
REPOSITORY = "francio87/ns8-borgbackupserver"
VERSIONS_PATH = "users/francio87/packages/container/borgbackupserver/versions"


def check_scope():
    if (os.environ.get("REPOSITORY") != REPOSITORY
            or os.environ.get("PACKAGE_OWNER") != "francio87"
            or os.environ.get("PACKAGE_OWNER_TYPE") != "User"):
        raise SystemExit("Cleanup is restricted to francio87/ns8-borgbackupserver")


def stable_version(tag):
    match = STABLE.fullmatch(tag)
    return tuple(map(int, match.groups())) if match else None


def obsolete_testing(tag, stable):
    match = TESTING.fullmatch(tag)
    return bool(match and tuple(map(int, match.groups()[:3])) <= stable)


def candidates(versions, stable):
    # A GHCR version is a digest: deleting it also deletes every attached tag.
    return [version for version in versions
            if version["metadata"]["container"]["tags"]
            and all(obsolete_testing(tag, stable)
                    for tag in version["metadata"]["container"]["tags"])]


def catalog_ready(catalog, stable_tag, deleted_tags):
    for app in catalog:
        if app.get("source") == "ghcr.io/francio87/borgbackupserver":
            versions = app["versions"]
            return (any(v["tag"] == stable_tag and not v["testing"] for v in versions)
                    and not any(v["tag"] in deleted_tags for v in versions))
    return False


def api(path, paginate=False):
    args = ["gh", "api", path]
    if paginate:
        args += ["--paginate", "--slurp"]
    result = json.loads(subprocess.check_output(args, text=True))
    return [item for page in result for item in page] if paginate else result


def prereleases_between(releases, stable_tag):
    # Match the official tool's date window, but reject newer or unknown versions.
    stable_releases = [r for r in releases if not r["isPrerelease"]]
    position = next(i for i, r in enumerate(stable_releases) if r["tagName"] == stable_tag)
    if position == 0:
        return []
    start = stable_releases[position - 1]["createdAt"]
    end = stable_releases[position]["createdAt"]
    tags = [r["tagName"] for r in releases
            if r["isPrerelease"] and start < r["createdAt"] <= end]
    if any(not obsolete_testing(tag, stable_version(stable_tag)) for tag in tags):
        raise SystemExit("Official cleanup would remove newer or unrecognized pre-releases; manual review required")
    return tags


def untagged_candidates(versions, now, inspect_manifest, keep_days=7):
    referenced = set()
    for version in versions:
        manifest = inspect_manifest(version["name"])
        referenced.update(item["digest"] for item in manifest.get("manifests", []))
        if manifest.get("subject"):
            referenced.add(manifest["subject"]["digest"])
    cutoff = now - timedelta(days=keep_days)
    return [v for v in versions
            if not v["metadata"]["container"]["tags"] and v["name"] not in referenced
            and datetime.fromisoformat(v["updated_at"].replace("Z", "+00:00")) < cutoff]


def prune_untagged(dry_run, keep_days):
    if keep_days < 0:
        raise SystemExit("Untagged retention must not be negative")
    for status in ["in_progress", "queued", "waiting"]:
        runs = api(f"repos/{REPOSITORY}/actions/workflows/publish-images.yml/runs?status={status}&per_page=1")
        if runs["total_count"]:
            print("Publication is active; untagged cleanup deferred")
            return
    versions = api(VERSIONS_PATH + "?per_page=100", paginate=True)
    registry = "https://ghcr.io"
    with urllib.request.urlopen(registry + "/token?service=ghcr.io&scope=repository:francio87/borgbackupserver:pull", timeout=30) as response:
        token = json.load(response)["token"]

    def inspect_manifest(digest):
        request = urllib.request.Request(
            registry + "/v2/francio87/borgbackupserver/manifests/" + digest,
            headers={"Authorization": "Bearer " + token, "Accept": ", ".join([
                "application/vnd.oci.image.index.v1+json",
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.docker.distribution.manifest.list.v2+json",
                "application/vnd.docker.distribution.manifest.v2+json",
            ])},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    selected = untagged_candidates(versions, datetime.now(timezone.utc), inspect_manifest, keep_days)
    print(f"Untagged cleanup selected {len(selected)} versions (retention: {keep_days} days)", flush=True)
    for version in selected:
        current = api(f'{VERSIONS_PATH}/{version["id"]}')
        # Recheck immediately before deletion: a tag may have moved since inventory.
        if (current["metadata"]["container"]["tags"]
                or current["updated_at"] != version["updated_at"]):
            print(f'Skipping changed version {version["id"]}', flush=True)
            continue
        print(f'{"Would delete" if dry_run else "Deleting"} untagged GHCR version {version["id"]}: {version["name"]}', flush=True)
        if not dry_run:
            subprocess.run(["gh", "api", "--method", "DELETE", f'{VERSIONS_PATH}/{version["id"]}'], check=True)


def main():
    check_scope()
    if os.environ.get("CHECK_BRANCH") == "true":
        branch = os.environ["PACKAGE_REF"]
        result = subprocess.run(["git", "ls-remote", "--exit-code", "--heads",
                                 f"https://github.com/{REPOSITORY}.git", f"refs/heads/{branch}"],
                                capture_output=True, text=True)
        if result.returncode == 0:
            print("Published branch still exists; its image is retained")
            return
        if result.returncode != 2:
            raise SystemExit(f"Cannot check branch existence: {result.stderr}")
    ref = os.environ.get("PACKAGE_REF", "").replace("/", "-")
    dry_run = os.environ.get("DRY_RUN", "true") == "true"
    if ref and (stable_version(ref) is not None or ref in {"main", "master", "latest"}):
        raise SystemExit(f"Protected image tag: {ref}")

    versions = api(VERSIONS_PATH + "?per_page=100", paginate=True)
    stable_tag = None
    prerelease_tags = []
    if ref:
        selected = [v for v in versions if v["metadata"]["container"]["tags"] == [ref]]
    else:
        stable_tags = [tag for v in versions for tag in v["metadata"]["container"]["tags"]
                       if stable_version(tag) is not None]
        if not stable_tags:
            raise SystemExit("No stable image: nothing to clean")
        stable_tag = max(stable_tags, key=stable_version)
        release = api(f"repos/{REPOSITORY}/releases/tags/{stable_tag}")
        if release["draft"] or release["prerelease"]:
            raise SystemExit("Stable image does not have a published stable GitHub release")
        selected = candidates(versions, stable_version(stable_tag))
        deleted_tags = {tag for v in selected for tag in v["metadata"]["container"]["tags"]}
        with urllib.request.urlopen(CATALOG, timeout=30) as response:
            catalog = json.load(response)
        if not catalog_ready(catalog, stable_tag, deleted_tags):
            print("Catalog is not ready; cleanup deferred until the next run")
            return
        releases = json.loads(subprocess.check_output([
            "gh", "release", "list", "--repo", REPOSITORY, "--limit", "1000",
            "--order", "asc", "--json", "tagName,isPrerelease,createdAt",
        ], text=True))
        prerelease_tags = prereleases_between(releases, stable_tag)

    for version in selected:
        print(f'{"Would delete" if dry_run else "Deleting"} GHCR version {version["id"]}: '
              f'{version["metadata"]["container"]["tags"]}', flush=True)
        if not dry_run:
            subprocess.run(["gh", "api", "--method", "DELETE", f'{VERSIONS_PATH}/{version["id"]}'], check=True)
    if prerelease_tags:
        print(f'{"Would clean" if dry_run else "Cleaning"} GitHub pre-releases: {prerelease_tags}', flush=True)
        if not dry_run:
            subprocess.run(["gh", "ns8-release-module", "clean", "--repo", REPOSITORY,
                            "--release-name", stable_tag], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--untagged", action="store_true")
    parser.add_argument("--keep-days", type=int, default=7)
    args = parser.parse_args()
    if args.untagged:
        check_scope()
        prune_untagged(os.environ.get("DRY_RUN", "true") == "true", args.keep_days)
    else:
        main()
