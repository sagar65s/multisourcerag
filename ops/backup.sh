#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

: "${BACKUP_DIRECTORY:?Set BACKUP_DIRECTORY to an encrypted-backup staging directory}"
: "${BACKUP_AGE_RECIPIENT:?Set BACKUP_AGE_RECIPIENT to the offline age public recipient}"
: "${MONGODB_URI:?Set MONGODB_URI}"
: "${QDRANT_URL:?Set QDRANT_URL}"
: "${QDRANT_COLLECTION:?Set QDRANT_COLLECTION}"
: "${PRIVATE_STORAGE_ROOT:?Set PRIVATE_STORAGE_ROOT}"

for command_name in age curl jq mongodump sha256sum tar; do
  command -v "$command_name" >/dev/null || { echo "Missing required command: $command_name" >&2; exit 1; }
done
test -d "$PRIVATE_STORAGE_ROOT" || { echo "Private storage directory does not exist" >&2; exit 1; }

backup_id="$(date -u +%Y%m%dT%H%M%SZ)"
destination="$BACKUP_DIRECTORY/$backup_id"
mkdir -p "$destination"

mongodump --quiet --uri="$MONGODB_URI" --archive --gzip \
  | age --encrypt --recipient "$BACKUP_AGE_RECIPIENT" --output "$destination/mongodb.archive.gz.age"

qdrant_headers=()
if [[ -n "${QDRANT_API_KEY:-}" ]]; then qdrant_headers=(-H "api-key: $QDRANT_API_KEY"); fi
snapshot_response="$(curl --fail --silent --show-error --request POST "${qdrant_headers[@]}" "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots")"
snapshot_name="$(jq -er '.result.name' <<<"$snapshot_response")"
cleanup_snapshot() {
  curl --fail --silent --show-error --request DELETE "${qdrant_headers[@]}" "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots/$snapshot_name" >/dev/null || true
}
trap cleanup_snapshot EXIT
curl --fail --silent --show-error "${qdrant_headers[@]}" "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots/$snapshot_name" \
  | age --encrypt --recipient "$BACKUP_AGE_RECIPIENT" --output "$destination/qdrant.snapshot.age"

tar --create --file=- --directory="$PRIVATE_STORAGE_ROOT" . \
  | age --encrypt --recipient "$BACKUP_AGE_RECIPIENT" --output "$destination/private-storage.tar.age"

(
  cd "$destination"
  sha256sum mongodb.archive.gz.age qdrant.snapshot.age private-storage.tar.age > SHA256SUMS
)
cleanup_snapshot
trap - EXIT
printf 'Encrypted backup completed: %s\n' "$destination"
