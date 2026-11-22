#!/bin/sh
# Make EPM2Mod-VERSION.dmg from the release zip (epm2mod package), on a Mac: EPM2Mod.app (EPM2Mod.applescript,
# launch.sh and the zip's folder) next to a link to Applications. Run the app from the disk image, or drag it to
# Applications to keep it.
#   make-dmg.sh ZIP [OUT_DIR]
# Environment:
#   EPM2MOD_SIGN_IDENTITY   a "Developer ID Application: ..." certificate in the keychain; default: ad-hoc (local tests)
#   EPM2MOD_NOTARY_PROFILE  a notarytool keychain profile (xcrun notarytool store-credentials): notarize and staple
set -eu
ZIP=$1
OUT=${2:-.}
HERE=$(cd "$(dirname "$0")" && pwd)
IDENTITY=${EPM2MOD_SIGN_IDENTITY:--}
PROFILE=${EPM2MOD_NOTARY_PROFILE:-}
[ -n "$PROFILE" ] && [ "$IDENTITY" = - ] && { echo "notarizing needs EPM2MOD_SIGN_IDENTITY" >&2; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "${WORK:?}"' EXIT
ditto -x -k "$ZIP" "$WORK/zip"
FOLDER=$(ls "$WORK/zip")
VERSION=${FOLDER#EPM2Mod-}
[ "$FOLDER" != "$VERSION" ] || { echo "$ZIP: no EPM2Mod-VERSION folder in it" >&2; exit 1; }

APP="$WORK/dmg/EPM2Mod.app"
mkdir -p "$WORK/dmg"
osacompile -o "$APP" "$HERE/EPM2Mod.applescript"
cp "$HERE/launch.sh" "$APP/Contents/Resources/launch.sh"
chmod +x "$APP/Contents/Resources/launch.sh"
ditto "$WORK/zip/$FOLDER" "$APP/Contents/Resources/EPM2Mod"
PLIST="$APP/Contents/Info.plist"
plutil -replace CFBundleIdentifier -string io.github.cfu288.epm2mod "$PLIST"
plutil -replace CFBundleShortVersionString -string "$VERSION" "$PLIST"
plutil -replace CFBundleVersion -string "${VERSION%%-*}" "$PLIST"
xattr -cr "$APP"

if [ "$IDENTITY" = - ]; then
  codesign --force --sign - "$APP"
else
  codesign --force --options runtime --timestamp --sign "$IDENTITY" "$APP"
fi
codesign --verify --strict --verbose=2 "$APP"

ln -s /Applications "$WORK/dmg/Applications"
mkdir -p "$OUT"
DMG="$OUT/EPM2Mod-$VERSION.dmg"
hdiutil create -quiet -volname "EPM2Mod $VERSION" -srcfolder "$WORK/dmg" -format UDZO -ov "$DMG"
[ "$IDENTITY" = - ] || codesign --force --timestamp --sign "$IDENTITY" "$DMG"

if [ -n "$PROFILE" ]; then
  RESULT=$(xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait --output-format json)
  echo "$RESULT"
  case "$RESULT" in
    *'"status":"Accepted"'*) ;;
    *) echo "notarization failed: xcrun notarytool log ID --keychain-profile $PROFILE gives the reason" >&2; exit 1 ;;
  esac
  xcrun stapler staple "$DMG"
  spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG"
fi
echo "$DMG"
