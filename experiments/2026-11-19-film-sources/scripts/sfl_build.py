"""sfl_build.py OUTDIR NEG|PRINT ...: export spectral_film_lut LUTs with the app's own defaults, V-Gamut/V-Log in, sRGB out,
33 points: the format of our film targets (spektrafilm-lut --input vlog --output srgb --resolution 33).
Each argument is NEGATIVE|PRINT (PRINT may be empty for none). With no arguments: list the stocks."""
import os, sys, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication
from spectral_film_lut.film_loader import load_filmstocks
from spectral_film_lut.gui import MainWindow

app = QApplication(sys.argv[:1])
stocks = load_filmstocks(lambda *a: None)
if len(sys.argv) < 3:
    for name, s in stocks.items():
        print(f"{s.stage}\t{s.film_type}\t{name}")
    sys.exit(0)
w = MainWindow(stocks)
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for job in sys.argv[2:]:
    neg, _, prt = job.partition("|")
    w.negative_selector.setCurrentText(neg)
    assert w.negative_selector.currentText() == neg, ("no negative", neg)
    if prt:
        w.print_selector.setCurrentText(prt)
        assert w.print_selector.currentText() == prt, ("no print", prt)
    w.input_colorspace_selector.setCurrentText("V-Gamut")
    assert w.input_colorspace_selector.currentText() == "V-Gamut"
    w.output_gamut.setCurrentText("Rec. 709")
    w.output_gamma.setCurrentText("sRGB")
    w.lut_size.setValue(33)
    name = os.path.join(out, (neg + "__" + (prt or "none")).replace(" ", "-").replace("/", "-"))
    t = time.time()
    w.generate_lut(name)
    print(job, "->", name, f"{time.time() - t:.0f}s", "gamut", w.output_gamut.currentText(), "settings: mode", w.mode.currentText())
