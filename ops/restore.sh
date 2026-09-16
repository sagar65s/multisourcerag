#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

[[ "${CONFIRM_RESTORE:-}" == "RESTORE_PRIVATE_DATA" ]] || { echo "Set CONFIRM_RESTORE=RESTORE_PRIVATE_DATA after entering a maintenance window" >&2; exit 1; }
: "${BACKUP_SOURCE:?Set BACKUP_SOURCE to one completed backup directory}"
: "${AGE_IDENTITY_FILE:?Set AGE_IDENTITY_FILE to the protected age private identity file}"
: "${MONGODB_URI:?Set MONGODB_URI}"
: "${QDRANT_URL:?Set QDRANT_URL}"
: "${QDRANT_COLLECTION:?Set QDRANT_COLLECTION}"
: "${PRIVATE_STORAGE_ROOT:?Set PRIVATE_STORAGE_ROOT}"

for command_name in age curl mongorestore sha256sum tar; do
  command -v "$command_name" >/dev/null || { echo "Missing required command: $command_name" >&2; exit 1; }
done
test -f "$AGE_IDENTITY_FILE" || { echo "Age identity file does not exist" >&2; exit 1; }
test -f "$BACKUP_SOURCE/SHA256SUMS" || { echo "Backup checksum manifest is missing" >&2; exit 1; }
(cd "$BACKUP_SOURCE" && sha256sum --check SHA256SUMS)
mkdir -p "$PRIVATE_STORAGE_ROOT"
if find "$PRIVATE_STORAGE_ROOT" -mindepth 1 -print -quit | grep -q .; then
  echo "PRIVATE_STORAGE_ROOT must be empty before restore" >&2
  exit 1
fi

age --decrypt --identity "$AGE_IDENTITY_FILE" "$BACKUP_SOURCE/mongodb.archive.gz.age" \
  | mongorestore --quiet --uri="$MONGODB_URI" --archive --gzip --drop

temporary_directory="$(mktemp -d)"
snapshot_file="$temporary_directory/qdrant.snapshot"
cleanup() { find "$temporary_directory" -type f -delete; rmdir "$temporary_directory" 2>/dev/null || true; }
trap cleanup EXIT
age --decrypt --identity "$AGE_IDENTITY_FILE" --output "$snapshot_file" "$BACKUP_SOURCE/qdrant.snapshot.age"
qdrant_headers=()
if [[ -n "${QDRANT_API_KEY:-}" ]]; then qdrant_headers=(-H "api-key: $QDRANT_API_KEY"); fi
curl --fail --silent --show-error --request POST "${qdrant_headers[@]}" \
  --form "snapshot=@$snapshot_file" "$QDRANT_URL/collections/$QDRANT_COLLECTION/snapshots/upload?priority=snapshot" >/dev/null

age --decrypt --identity "$AGE_IDENTITY_FILE" "$BACKUP_SOURCE/private-storage.tar.age" \
  | tar --extract --file=- --directory="$PRIVATE_STORAGE_ROOT" --no-same-owner --no-same-permissions
cleanup
trap - EXIT
echo "Restore completed. Start the application and verify readiness before reopening traffic."
