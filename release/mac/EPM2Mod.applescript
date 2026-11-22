-- EPM2Mod.app (make-dmg.sh compiles it): start launch.sh from the app's Resources in the background, then quit.
-- The installer page opens in the browser; the server stops when the page is closed.
on run
	set launcher to POSIX path of (path to me) & "Contents/Resources/launch.sh"
	do shell script quoted form of launcher & " >/dev/null 2>&1 &"
end run
