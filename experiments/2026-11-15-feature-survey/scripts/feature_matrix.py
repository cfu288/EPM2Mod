"""For a list of features: which bodies have UI text for it, which have code-side name strings.

    python3 feature_matrix.py ENU_DIR STR_DIR > feature-matrix.md

ENU_DIR: <code>_<ver>.json from lang_enu.py. STR_DIR: <code>_<ver>.txt = `strings -n 5 | sort -u`
of the (expanded) main block. A cell shows the number of distinct matching strings; '.' = none.
Lines with "dummy" are not counted on the code side (api_*_dummy_* are name-only stubs).
The regular expressions are the evidence: read a hit list with --show FEATURE CODE.
"""
import json, re, sys
from pathlib import Path

ORDER = ["097", "100", "101", "112", "108", "111", "109", "113", "115", "118", "120", "122", "126",
         "125", "130", "133", "139", "140", "142", "143", "144", "147"]
HEAD = ["M5", "PL5", "PM2", "PL6", "P5", "ST1", "M1", "M10", "PL7", "M5ii", "M10ii", "PenF", "PL8",
        "M1ii", "M10iii", "PL9", "M1iii", "M10iv", "P7", "OM1", "OM5", "OM3"]
# name: (UI regex on icon-stripped text, code regex on main-block strings)
F = {
 "HDR in-camera merge (HDR1/HDR2)": (r"^HDR ?[12]$|HDR Shooting|^HDR$", r"hdr_?comb|Rec_HDR|Record_Media_HDR|HDR_Work|RecView_HDR|hdr_shoot|HDR_MODE"),
 "Focus peaking": (r"Peaking", r"peaking"),
 "Peaking colour / intensity / brightness adj.": (r"Peaking Color|Highlight Intensity|Image Brightness Adj", r"peaking_?(color|level|intens)|PEAKING_(RED|YELLOW|COLOR)"),
 "Color Creator": (r"Color Creator", r"color_?creat"),
 "Photo Story": (r"Fun Frames|Photo Story|^Layout$|Works in progress", r"photo_?story|photostory|PhotoSession"),
 "Live Composite": (r"Live Composite|Composite Settings|composite shooting", r"live_?comp|comp_?shoot|TakeComposite|LvComp|lv_?composite|COMPOSITE_(SHOOT|MODE|START)"),
 "Keystone Compensation": (r"Keystone", r"keystone|trapezoid|digital_?shift"),
 "Focus Bracketing": (r"Focus BKT|Focus Bracketing", r"focus_?bkt|focus_?bracket"),
 "Focus Stacking": (r"Focus Stacking|Images are then stacked", r"focus_?stack|stacking"),
 "Silent (electronic) shutter": (r"Silent", r"silent"),
 "Anti-shock 0 s (electronic first curtain)": (r"Anti-Shock@|first shutter curtain", r"anti_?shock.*(0|zero|elec)|efcs|EFS_|elec.*(front|first)|sakimaku|front_?curtain|ANTISHOCK_(0|ZERO|E)"),
 "Zebra": (r"Zebra", r"zebra"),
 "Live ND": (r"Live ND|ND Number", r"live_?nd|digital_?nd"),
 "Live GND": (r"Live GND", r"live_?gnd|gnd_"),
 "High Res Shot": (r"High Res", r"high_?res|hires"),
 "Pro Capture": (r"Pro Capture|Pre-shutter", r"pro_?cap(?!acity)|pre_?capture"),
 "Starry Sky AF": (r"Starry Sky", r"starry"),
 "Subject / eye detection (new style)": (r"Subject Detection|Face & Eye|Eye Detection", r"subject_?det|subj_?detect|eye_?detect"),
 "Face priority with eye priority (old style)": (r"Face Priority", r"face_?prior|pupil|eye_?prior"),
 "Small AF target": (r"@mall@|Small Target|AF Target (Mode|Settings)", r"target_?size|small_?target|af_?area_?size|AF_TARGET_(SMALL|SPOT|SIZE)|super_?spot"),
 "AF Limiter": (r"AF Limiter", r"af_?limit"),
 "Preset MF": (r"Preset MF", r"preset_?mf"),
 "MF Clutch / focus ring lock": (r"MF Clutch|Focus Ring Lock", r"clutch"),
 "C-AF Lock / C-AF Sensitivity": (r"C-AF Lock|C-AF Sensitivity", r"caf_?(lock|sens)|c_af_lock|AF_LOCK_ON_SENS"),
 "AF Area Pointer on/off": (r"AF Area Pointer", r"area_?pointer"),
 "AF Focus Adjust (phase detect)": (r"AF Focus Adj", r"AfFinetune|af_?fine"),
 "ISO LOW / L64 / L100": (r"ISO LOW|ISO L\d+|^LOW$", r"iso_?low|low_?iso|ISO_EXT_L"),
 "Lowest shutter speed for ISO-Auto": (r"Lowest S/S", r"lowest_?ss|low_?limit_?ss|ss_?limit"),
 "Release Lag-Time (short)": (r"Lag-Time", r"lag_?time|rls_?lag|release_?lag|short_?lag|timelag"),
 "EVF auto switch for the external VF-4": (r"Enable the eye sensor", r"External_?Eye|EXTERNAL_EYE"),
 "Level gauge": (r"Level Gauge|Level Disp|Half Way Level", r"Slope_Roll_Pitch|levelCtrl"),
 "Interval shooting / time lapse movie": (r"Time Lapse|Interval Sh|Intrvl", r"interval_?shoot|timelapse|time_?lapse"),
 "Custom self-timer": (r"Custom Self-timer", r"custom_?self"),
 "Movie time code": (r"Time Code", r"time_?code"),
 "Movie frame rate choice (24p/25p/50p/60p)": (r"^2[45]p$|^[56]0p$|Video Frame Rate|Frame Rate Priority", r"24p|25p|FRAME_RATE_(24|25|50|60)"),
 "Movie bit rate choice / ALL-Intra": (r"ALL-Intra|Bit Rate|Super Fine", r"all_?intra|bit_?rate_?(mode|sel)|superfine|super_fine"),
 "High-speed / slow-fast movie": (r"HighSpeed|HS 120|Slow or Fast|Slow/Fast", r"slow_?fast|quick_?motion|slow_?motion|hs_?movie|highspeed_?mov"),
 "4K movie": (r"3840|4K", r"3840|2160"),
 "Movie picture modes Flat / OM-Log / HLG": (r"@? ?Flat$|OM-Log|HLG", r"om_?log|PICTURE_MODE_FLAT|PIC_MODE_FLAT|hlg"),
 "Clips / My Clips": (r"My Clips|^Clips$", r"my_?clip"),
 "Movie effects (echo, art fade, movie tele)": (r"Movie Effect|Art Fade|Multi Echo|One.?Shot Echo", r"multi_?echo|oneshot|art_?fade|movie_?effect"),
 "Movie+Photo mode": (r"Movie\+Photo", r"movie_?photo|mov_?plus"),
 "Audio: level meter / limiter / headphone / PCM link": (r"Volume Limiter|Headphone|PCM Recorder|Rec\. Level|Recording Level", r"vol_?limit|headphone|pcm_?rec|slate"),
 "Wi-Fi (built in)": (r"Wi-Fi", r"WIFI_MNGR|HTTPD|In_Wlan|wifi_remocon"),
 "Bluetooth LE / GPS log from phone": (r"Bluetooth", r"\bBLE_|ble_"),
 "USB tethering (remote capture)": (r"@PC RAW|Olympus Capture|^0?@?Control$|Webcam|@ Control", r"InitiateCapture|remote_?cap|tether|PC_START_PC|RawEdit.*Usb|usb_?raw"),
 "USB power / USB PD / webcam": (r"USB PD|Power Supply from USB|Webcam", r"usb_?pd|uvc|webcam"),
 "Custom modes on the dial / C1-C4": (r"Custom Mode|Mode Dial Function", r"custom_?mode"),
 "My Menu": (r"My Menu", r"my_?menu"),
 "Menu Recall / menu cursor position": (r"Menu Recall|Menu Cursor|Menu Start Position", r"menu_?recall|menu_?cursor"),
 "Multi Function button": (r"Multi Function", r"multi_?func"),
 "Lens Info Settings (adapted lens data)": (r"Lens Info|Lens Data|Lens Name|Create Lens", r"lens_?info_?(set|reg|edit|name)|lensdata_?set|manual_?lens|LENS_INFO_SETTING|UserLens|user_?lens"),
 "Fisheye Compensation": (r"Fisheye Comp", r"fisheye"),
 "Flicker Scan / anti-flicker shooting": (r"Flicker Scan|Anti-Flicker", r"flicker_?scan|anti_?flicker|flk_?scan"),
 "Flicker reduction (live view)": (r"Flicker reduction|Flicker Reduction", r"flicker"),
 "LV Boost 2 / Night Vision / per-mode boost": (r"Live View Boost On2|^On2$|Night Vision|Bulb/Time Live View Boost|Other Live View Boost", r"lv_?boost_?2|night_?vision|NIGHT_LV|lvboost2"),
 "LV dynamic range expansion (S-OVF)": (r"D-Range|Dyn\. Range|S-OVF", r"lv_?drange|d_?range_?exp|sovf|s_ovf"),
 "BULB/TIME monitor brightness": (r"BULB/TIME Monitor|Bulb/Time Monitor", r"bulb_?monitor|bulb.*bright"),
 "Art: Vintage": (r"Vintage", r"vintage"),
 "Art: Partial Color": (r"Partial Color", r"partial_?col|one_?point|PARTCOLOR|part_?color"),
 "Art: Bleach Bypass": (r"Bleach Bypass", r"bleach"),
 "Art: Instant Film": (r"Instant Film", r"instant_?film|instantfilm"),
 "Art effects: Blur / Shade top-bottom, left-right": (r"Blur Effect|Shade Effect", r"art_effect_(blur|shade)|tilt_?blur|effect_?shade"),
 "Art BKT RAW edit in playback": (r"ART BKT", r"ArtBktRaw|artbkt_raw"),
 "Color / Monochrome Profile Control": (r"Color Profile|Monochrome Profile|Mono Profile", r"color_?prof|mono_?prof"),
 "Monochrome colour filter / film grain / shading": (r"Color Filter|Film Grain Effect|^Shading( Effect)?$", r"film_?grain|grain_?effect|color_?filter|shading_?effect"),
 "Highlight&Shadow with Midtone": (r"Midtone", r"midtone|mid_?tone"),
 "e-Portrait as a picture mode": (r"^@e-Portrait$", r"PICTURE_MODE_E_?PORTRAIT|pic_?mode.*eportrait"),
 "Underwater picture mode": (r"^@Underwater$", r"PICTURE_MODE_UNDERWATER|uw_?pict"),
 "SCN: Hand-Held Starlight": (r"Hand-?[Hh]eld Starlight", r"starlight|hand_?held_?night|tebure_?yakei|HHS_"),
 "SCN: Panning": (r"^Panning$", r"panning"),
 "SCN/AP: Multi Focus Shot, Light Trails, Backlight HDR": (r"Multi Focus Shot|Light Trails|Backlight HDR", r"multi_?focus|light_?trail|backlight_?hdr"),
 "Sweep / in-camera panorama": (r"Panorama", r"sweep_?pano|pano_?stitch|PanoramaShoot|swing_?pano"),
 "Electronic zoom speed / zoom by arrow keys": (r"Zoom Speed|E\.Zoom|Electronic Zoom|Zoom In/Out", r"Ez_Zoom|EZoom|powerzoom|ZOOM_UP_LOW_SPEED"),
 "Preview lock (hold depth of field preview)": (r"depth of field preview is maintained", r"preview_?lock"),
 "Spot metering linked to the AF target": (r"^@?Spot Metering$", r"spot_?af_?link|spot_?link|SPOT_METERING_AF"),
 "Quick Sleep Mode": (r"Quick Sleep", r"quick_?sleep"),
 "Frame count limiter (sequential)": (r"Frame Count Limiter", r"frame_?count_?limit|max_?frame_?num"),
 "Low ISO Processing (detail / drive priority)": (r"Low ISO Processing", r"low_?iso_?proc|detail_?prior"),
 "Grid colour / grid settings": (r"Grid Settings|Display Color", r"grid_?color"),
 "Magnify settings (LV Close Up Settings)": (r"LV Close Up Settings|Magnify Frame", r"closeup_?set|magnify_?frame"),
 "Selfie Assist (flip screen)": (r"Selfie", r"selfie|Swivel"),
 "Movie trimming / in-movie image capture": (r"Movie Trimming|In-Movie Image Capture|Movie Edit", r"movie_?trim|trimming_?mov|mov_?edit|MovieEdit"),
 "World time / time zone": (r"World Time|Time Zone", r"world_?time|time_?zone|timezone"),
 "Exposure smoothing (interval)": (r"Exposure Smoothing", r"exp_?smooth|deflicker"),
 "Dual card slots": (r"Card Slot|Dual Independent", r"slot_?2|card_?slot"),
 "Field sensors (GPS, compass, barometer)": (r"Field Sensor|Elevation", r"barometer|field_?sensor|manometer"),
}


def main() -> None:
    enu, strs = Path(sys.argv[1]), Path(sys.argv[2])
    ui, code = {}, {}
    for p in enu.glob("*.json"):
        ui[p.name[:3]] = sorted({re.sub(r"\s+", " ", re.sub(r"@A[0-9A-F]{3}@", "@", s)).strip() for s in json.load(open(p)) if s})
    for p in strs.glob("*.txt"):
        code[p.name[:3]] = [l for l in p.read_text(errors="replace").split("\n") if "dummy" not in l]
    if "--show" in sys.argv:
        name, c = sys.argv[sys.argv.index("--show") + 1:][:2]
        u, k = F[name]
        print("UI:", [s for s in ui[c] if re.search(u, s)][:60])
        print("CODE:", [s for s in code[c] if re.search(k, s, re.I)][:80])
        return
    print("| Feature | side | " + " | ".join(HEAD) + " |")
    print("|---|---|" + "---|" * len(HEAD))
    for name, (u, k) in F.items():
        ru, rk = re.compile(u), re.compile(k, re.I)
        row_u = [sum(1 for s in ui[c] if ru.search(s)) for c in ORDER]
        row_k = [sum(1 for s in code[c] if rk.search(s)) for c in ORDER]
        f = lambda r: " | ".join(str(min(x, 99)) if x else "." for x in r)
        print(f"| {name} | text | {f(row_u)} |")
        print(f"| | code | {f(row_k)} |")


main()
