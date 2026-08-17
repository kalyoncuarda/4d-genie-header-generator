"""
generate_genie_header.py icin otomatik testler.

Kapsanan senaryolar (dokuman'daki 'Testler' bolumunden):
  - Alias dogru okunuyor
  - Form alias'i dogru macro'ya donusuyor
  - UserButton alias'i dogru macro'ya donusuyor
  - camelCase alias dogru normalize ediliyor
  - boslukli alias dogru normalize ediliyor
  - duplicate alias tespit ediliyor
  - duplicate index tespit ediliyor
  - alias olmayan obje tespit ediliyor
  - ayni proje iki kez calistirilinca ayni header olusuyor (determinizm)
  - uretilen header C compiler tarafindan kabul ediliyor
  - uretilen header C++ compiler tarafindan kabul ediliyor
"""

import os
import subprocess
import sys
import shutil

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from generate_genie_header import (
    parse_4dgenie,
    generate_header_content,
    normalize_to_macro_name,
)


# ---------------------------------------------------------------------------
# Yardimci: gecici bir .4DGenie dosyasi olusturmak icin kucuk bir sablon
# ---------------------------------------------------------------------------
def make_genie_file(tmp_path, blocks):
    """
    blocks: [("UserButton", {"Name": "Userbutton4", "Alias": "ConnectButton"}), ...]
    """
    lines = []
    for obj_type, fields in blocks:
        lines.append(obj_type)
        for k, v in fields.items():
            lines.append(f"    {k}    {v}")
        lines.append("end")
    content = "\n".join(lines) + "\n"
    path = tmp_path / "test_project.4DGenie"
    path.write_text(content, encoding="utf-8")
    return str(path)


# ---------------------------------------------------------------------------
# 1) Alias dogru okunuyor
# ---------------------------------------------------------------------------
def test_alias_dogru_okunuyor(tmp_path):
    path = make_genie_file(tmp_path, [
        ("UserButton", {"Name": "Userbutton4", "Alias": "ConnectButton"}),
    ])
    objs = parse_4dgenie(path)
    assert len(objs) == 1
    assert objs[0].alias == "ConnectButton"
    assert objs[0].index == 4
    assert objs[0].obj_type == "UserButton"


# ---------------------------------------------------------------------------
# 2) Form alias'i dogru macro'ya donusuyor
# ---------------------------------------------------------------------------
def test_form_alias_dogru_macroya_donusuyor(tmp_path):
    path = make_genie_file(tmp_path, [
        ("Form", {"Name": "Form1", "Alias": "SettingsMenu"}),
    ])
    objs = parse_4dgenie(path)
    header = generate_header_content(objs)
    assert "#define FORM_SETTINGS_MENU 1" in header


# ---------------------------------------------------------------------------
# 3) UserButton alias'i dogru macro'ya donusuyor
# ---------------------------------------------------------------------------
def test_userbutton_alias_dogru_macroya_donusuyor(tmp_path):
    path = make_genie_file(tmp_path, [
        ("UserButton", {"Name": "Userbutton4", "Alias": "ConnectButton"}),
    ])
    objs = parse_4dgenie(path)
    header = generate_header_content(objs)
    assert "#define USERBUTTON_CONNECT_BUTTON 4" in header


# ---------------------------------------------------------------------------
# 4) camelCase alias dogru normalize ediliyor
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("MainMenu", "MAIN_MENU"),
    ("mainMenu", "MAIN_MENU"),
    ("connectButton", "CONNECT_BUTTON"),
])
def test_camelcase_normalize(raw, expected):
    assert normalize_to_macro_name(raw) == expected


# ---------------------------------------------------------------------------
# 5) Boslukli / tireli alias dogru normalize ediliyor
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("Main Menu", "MAIN_MENU"),
    ("Connect-Button", "CONNECT_BUTTON"),
    ("connect_button", "CONNECT_BUTTON"),
])
def test_boslukli_tireli_normalize(raw, expected):
    assert normalize_to_macro_name(raw) == expected


# ---------------------------------------------------------------------------
# 6) Duplicate alias tespit ediliyor (ayni tipte iki obje ayni alias'i
#    kullanirsa, ayni macro adi uretilir ve generate_header_content hata
#    firlatmalidir)
# ---------------------------------------------------------------------------
def test_duplicate_alias_tespit_ediliyor(tmp_path):
    path = make_genie_file(tmp_path, [
        ("UserButton", {"Name": "Userbutton1", "Alias": "Connect"}),
        ("UserButton", {"Name": "Userbutton2", "Alias": "Connect"}),
    ])
    objs = parse_4dgenie(path)
    with pytest.raises(ValueError, match="Duplicate macro"):
        generate_header_content(objs)


# ---------------------------------------------------------------------------
# 7) Duplicate index tespit ediliyor
# ---------------------------------------------------------------------------
def test_duplicate_index_tespit_ediliyor(tmp_path):
    # Ayni tipte, farkli Name/Alias ama ayni index'e sahip iki obje
    # (normalde .4DGenie'de olmaz, ama parser/generator'in kendini
    # savunmasini test ediyoruz)
    path = make_genie_file(tmp_path, [
        ("UserButton", {"Name": "Userbutton4", "Alias": "Connect"}),
        ("UserButton", {"Name": "Userbutton04", "Alias": "OtherName"}),
    ])
    objs = parse_4dgenie(path)
    with pytest.raises(ValueError, match="Duplicate index"):
        generate_header_content(objs)


# ---------------------------------------------------------------------------
# 8) Alias olmayan obje tespit ediliyor (strict modda hataya donusuyor)
# ---------------------------------------------------------------------------
def test_alias_olmayan_obje_strict_modda_hata_veriyor(tmp_path):
    path = make_genie_file(tmp_path, [
        ("UserButton", {"Name": "Userbutton7", "Alias": "Userbutton7"}),  # alias yok (Name ile ayni)
    ])
    objs = parse_4dgenie(path)
    with pytest.raises(ValueError, match="Strict mode error"):
        generate_header_content(objs, strict=True)


def test_alias_olmayan_obje_normal_modda_uyari_ile_gecer(tmp_path, capsys):
    path = make_genie_file(tmp_path, [
        ("UserButton", {"Name": "Userbutton7", "Alias": "Userbutton7"}),
    ])
    objs = parse_4dgenie(path)
    header = generate_header_content(objs, strict=False)
    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "does not have an alias" in captured.err
    # yine de bir macro uretilmis olmali (fallback isimle)
    assert "#define USERBUTTON_USERBUTTON7 7" in header


# ---------------------------------------------------------------------------
# 9) Ayni proje iki kez calistirilinca ayni header olusuyor (determinizm)
# ---------------------------------------------------------------------------
def test_determinizm(tmp_path):
    path = make_genie_file(tmp_path, [
        ("UserButton", {"Name": "Userbutton9", "Alias": "Save"}),
        ("Form", {"Name": "Form2", "Alias": "MainMenu"}),
        ("Strings", {"Name": "Strings5", "Alias": "StatusText"}),
    ])
    objs1 = parse_4dgenie(path)
    header1 = generate_header_content(objs1)
    objs2 = parse_4dgenie(path)
    header2 = generate_header_content(objs2)
    assert header1 == header2


def test_determinizm_gercek_projede(tmp_path):
    """Gercek MainScreen.4DGenie ile de determinizm saglanmali."""
    real_project = os.path.join(os.path.dirname(__file__), "..", "MainScreen.4DGenie")
    if not os.path.exists(real_project):
        pytest.skip("MainScreen.4DGenie bulunamadi, bu test atlandi.")
    objs1 = parse_4dgenie(real_project)
    header1 = generate_header_content(objs1)
    objs2 = parse_4dgenie(real_project)
    header2 = generate_header_content(objs2)
    assert header1 == header2


# ---------------------------------------------------------------------------
# 10) Uretilen header C compiler tarafindan kabul ediliyor
# ---------------------------------------------------------------------------
@pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc bulunamadi")
def test_header_c_ile_derleniyor(tmp_path):
    path = make_genie_file(tmp_path, [
        ("Form", {"Name": "Form0", "Alias": "SplashForm"}),
        ("UserButton", {"Name": "Userbutton1", "Alias": "Connect"}),
    ])
    objs = parse_4dgenie(path)
    header = generate_header_content(objs)

    header_path = tmp_path / "genie_objects.h"
    header_path.write_text(header, encoding="utf-8")

    c_file = tmp_path / "test.c"
    c_file.write_text(
        f'#include "{header_path.name}"\n'
        f"int main(void) {{ return FORM_SPLASH_FORM + USERBUTTON_CONNECT; }}\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["gcc", "-Wall", "-Wextra", "-Werror", "-c", str(c_file), "-o", str(tmp_path / "test_c.o")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"gcc hata verdi:\n{result.stderr}"


# ---------------------------------------------------------------------------
# 11) Uretilen header C++ compiler tarafindan kabul ediliyor
# ---------------------------------------------------------------------------
@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ bulunamadi")
def test_header_cpp_ile_derleniyor(tmp_path):
    path = make_genie_file(tmp_path, [
        ("Form", {"Name": "Form0", "Alias": "SplashForm"}),
        ("UserButton", {"Name": "Userbutton1", "Alias": "Connect"}),
    ])
    objs = parse_4dgenie(path)
    header = generate_header_content(objs)

    header_path = tmp_path / "genie_objects.h"
    header_path.write_text(header, encoding="utf-8")

    cpp_file = tmp_path / "test.cpp"
    cpp_file.write_text(
        f'#include "{header_path.name}"\n'
        f"int main() {{ return FORM_SPLASH_FORM + USERBUTTON_CONNECT; }}\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["g++", "-Wall", "-Wextra", "-Werror", "-c", str(cpp_file), "-o", str(tmp_path / "test_cpp.o")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"g++ hata verdi:\n{result.stderr}"


# ---------------------------------------------------------------------------
# Ekstra: gercek proje uzerinde uctan uca (end-to-end) dogrulama
# ---------------------------------------------------------------------------
def test_gercek_proje_uctan_uca(tmp_path):
    """MainScreen.4DGenie ile gercekten header uretilebiliyor mu ve
    beklenen bazi tanimlar dogru mu, uctan uca kontrol eder."""
    real_project = os.path.join(os.path.dirname(__file__), "..", "MainScreen.4DGenie")
    if not os.path.exists(real_project):
        pytest.skip("MainScreen.4DGenie bulunamadi, bu test atlandi.")

    objs = parse_4dgenie(real_project)
    assert len(objs) > 0
    header = generate_header_content(objs)

    assert "#ifndef GENIE_OBJECTS_H" in header
    assert "#endif" in header
    # Bilinen birkac gercek tanimin varligini dogrula
    assert "#define FORM_SPLASH_FORM 0" in header
