#!/bin/sh
# Make or delete the keychain that signs and notarizes the disk image in CI (package.yml, job dmg).
#   keychain.sh create KEYCHAIN
#   keychain.sh delete KEYCHAIN
# create makes KEYCHAIN the default keychain, so that codesign and notarytool find the certificate. It also stores
# the notarization login as the profile epm2mod. It reads MAC_CERT_P12 (a base64 .p12), MAC_CERT_PASSWORD, APPLE_ID,
# APPLE_TEAM_ID and APPLE_APP_PASSWORD from the environment.
set -eu
ACTION=$1
KC=$2
# Apple's Developer ID G2 intermediate certificate (https://www.apple.com/certificateauthority/).
CA_URL=https://www.apple.com/certificateauthority/DeveloperIDG2CA.cer
CA_SHA256=f16cd3c54c7f83cea4bf1a3e6a0819c8aaa8e4a1528fd144715f350643d2df3a

case $ACTION in
  create)
    WORK=$(mktemp -d)
    trap 'rm -rf "${WORK:?}"' EXIT
    PASS=$(openssl rand -hex 16)
    [ -z "${GITHUB_ACTIONS:-}" ] || echo "::add-mask::$PASS"
    security create-keychain -p "$PASS" "$KC"
    security set-keychain-settings -lut 21600 "$KC"
    security unlock-keychain -p "$PASS" "$KC"
    security default-keychain -s "$KC"
    security list-keychains -d user -s "$KC"
    curl -fsSL -o "$WORK/ca.cer" "$CA_URL"
    echo "$CA_SHA256  $WORK/ca.cer" | shasum -a 256 -c -
    security import "$WORK/ca.cer" -k "$KC"
    printf %s "$MAC_CERT_P12" | base64 --decode > "$WORK/cert.p12"
    security import "$WORK/cert.p12" -k "$KC" -P "$MAC_CERT_PASSWORD" -T /usr/bin/codesign
    security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k "$PASS" "$KC" > /dev/null
    xcrun notarytool store-credentials epm2mod --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" \
      --password "$APPLE_APP_PASSWORD"
    ;;
  delete)
    # The create step may have failed before it made the keychain.
    [ ! -e "$KC" ] || security delete-keychain "$KC"
    ;;
  *)
    echo "usage: keychain.sh create|delete KEYCHAIN" >&2
    exit 2
    ;;
esac
