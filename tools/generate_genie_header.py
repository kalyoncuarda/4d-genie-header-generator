#!/usr/bin/env python3
"""
4D Systems Genie C Header Generator
Parses .4DGenie / .4DWork project files and generates deterministic C/C++ headers.
"""

import sys
import os
import re
import json
import argparse
from typing import List, Dict, Tuple, Optional


class GenieObject:
    """Represents an extracted Genie object from .4DGenie file."""
    def __init__(self, obj_type: str, name: str, alias: str, index: int, line_num: int):
        self.obj_type = obj_type
        self.name = name
        self.alias = alias
        self.index = index
        self.line_num = line_num

    def __repr__(self):
        return f"GenieObject({self.obj_type}, index={self.index}, alias='{self.alias}')"


def normalize_to_macro_name(alias: str) -> str:
    if not alias:
        return ""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', alias)
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
    s3 = re.sub(r'[^a-zA-Z0-9_]', '_', s2)
    s4 = re.sub(r'_+', '_', s3)
    result = s4.strip('_').upper()
    if result and result[0].isdigit():
        result = '_' + result
    return result


# ---------------------------------------------------------------------------
# Desteklenen Genie obje tipleri artik kaynak koda gomulu (hardcoded) degil,
# script ile ayni klasordeki 'genie_types.json' dosyasindan okunuyor. Bu
# sayede yeni bir tip eklemek icin .py dosyasini elle degistirmeye gerek
# kalmiyor - CLI'dan '--add-type' ile eklenebiliyor.
#
# JSON formati: {"TipAdi": "Header'da gorunecek baslik", ...}
# Sozlukteki SIRA, header'daki bolum sirasini da belirler (Python 3.7+
# itibariyla dict sirasi korunur, JSON da bu sirayla yazilip okunur).
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TYPES_CONFIG_PATH = os.path.join(SCRIPT_DIR, "genie_types.json")

DEFAULT_TYPES: Dict[str, str] = {
    'Form': 'Forms / Menus',
    'UserButton': 'User Buttons',
    'WinButton': 'WinButtons',
    'Strings': 'Strings',
    'UserImages': 'User Images',
    'Keyboard': 'Keyboards',
    'Video': 'Videos',
    'Image': 'Static Images',
    'Sounds': 'Sounds',
    'StaticText': 'Static Texts',
    'Panel': 'Panels',
    'Border': 'Borders',
}

# Bunlar obje degil, proje meta/ayar bilgisi tasiyan bloklar (Options,
# Depends, Platform, PlatRes, Version). Name/Alias alanlari olmadigi icin
# obje listesine hic girmezler, bilerek atlanirlar. Bunlar 'add-type' ile
# eklenebilecek turden degil, formatin sabit bir parcasi oldugu icin
# kaynak kodda sabit tutuluyor.
KNOWN_NON_OBJECT_BLOCKS = {'Options', 'Depends', 'Platform', 'PlatRes', 'Version'}


def load_type_config(config_path: Optional[str] = None) -> Dict[str, str]:
    """
    genie_types.json dosyasini okur. Dosya yoksa, varsayilan tiplerle
    otomatik olarak olusturur (ilk calistirmada).
    """
    path = config_path or DEFAULT_TYPES_CONFIG_PATH
    if not os.path.exists(path):
        save_type_config(DEFAULT_TYPES, path)
        return dict(DEFAULT_TYPES)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict) or not data:
        raise ValueError(f"Invalid or empty type config file: {path}")
    return data


def save_type_config(config: Dict[str, str], config_path: Optional[str] = None) -> None:
    path = config_path or DEFAULT_TYPES_CONFIG_PATH
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write('\n')


def add_type(
    name: str,
    config_path: Optional[str] = None,
) -> bool:
    """
    Yeni bir Genie obje tipini genie_types.json'a ekler (listenin sonuna,
    baslik olarak tipin kendi adini kullanarak). Basariyla eklendiyse
    True, tip zaten varsa False doner.
    """
    config = load_type_config(config_path)
    if name in config:
        return False

    config[name] = name
    save_type_config(config, config_path)
    return True


def remove_type(
    name: str,
    config_path: Optional[str] = None,
) -> bool:
    """
    Bir Genie obje tipini genie_types.json'dan siler. Basariyla
    silindiyse True, tip zaten yoksa False doner.
    """
    config = load_type_config(config_path)
    if name not in config:
        return False

    del config[name]
    save_type_config(config, config_path)
    return True


def parse_4dgenie(file_path: str, type_config: Optional[Dict[str, str]] = None) -> List[GenieObject]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Project file not found: {file_path}")

    if type_config is None:
        type_config = load_type_config()

    GENIE_TYPES = set(type_config.keys())
    # Buyuk/kucuk harf duyarsiz karsilastirma icin: "userbutton" -> "UserButton"
    GENIE_TYPES_LOWER = {t.lower(): t for t in GENIE_TYPES}

    objects: List[GenieObject] = []

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    current_type: Optional[str] = None
    current_name: Optional[str] = None
    current_alias: Optional[str] = None
    block_start_line = 0
    # Bilinen bir meta blogun (Options, Depends, vb.) icindeyken TRUE olur;
    # bu blogun ic satirlarini (orn. Options icindeki tek kelimelik "Genie"
    # satiri) yanlislikla yeni bir blok basligi sanmamak icin, 'end'
    # gorene kadar HER SEYI atlariz.
    skipping_meta_block = False

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith(';'):
            continue

        if skipping_meta_block:
            if stripped == 'end':
                skipping_meta_block = False
            continue

        if stripped == 'end':
            if current_type and current_type in GENIE_TYPES:
                index_match = re.search(r'\d+$', current_name or '')
                if index_match:
                    index = int(index_match.group())
                    alias = current_alias if current_alias else (current_name or '')

                    objects.append(GenieObject(
                        obj_type=current_type,
                        name=current_name or '',
                        alias=alias,
                        index=index,
                        line_num=block_start_line
                    ))
                else:
                    # Name alaninin sonunda rakam yok, index guvenilir
                    # sekilde cikarilamiyor. Yanlis/hayalet bir "index 0"
                    # uretip header'i kirletmek yerine, bu objeyi tamamen
                    # atlayip net bir uyari basiyoruz.
                    print(
                        f"WARNING: Could not extract index from Name '{current_name}' "
                        f"({current_type}) at line {block_start_line} - reason: "
                        f"'Name' does not end with a number (expected format like "
                        f"'{current_type}5', got '{current_name}'). Object skipped.",
                        file=sys.stderr
                    )
            current_type = None
            current_name = None
            current_alias = None
            continue

        parts = stripped.split()
        if len(parts) == 1:
            candidate = parts[0]
            # Once tam (case-sensitive) eslesmeye bak, sonra buyuk/kucuk harf
            # duyarsiz eslesmeyi dene (orn. 'USERBUTTON' -> 'UserButton').
            matched_type = candidate if candidate in GENIE_TYPES else GENIE_TYPES_LOWER.get(candidate.lower())
            if matched_type:
                current_type = matched_type
                current_name = None
                current_alias = None
                block_start_line = idx
                continue
            elif candidate in KNOWN_NON_OBJECT_BLOCKS or candidate.lower() in {'options', 'depends', 'platform', 'platres', 'version'}:
                # Bilinen meta blok (proje ayarlari), obje degil - sessizce
                # atla. Ic satirlarini da atlamak icin skip moduna gec.
                skipping_meta_block = True
                continue
            elif current_type is None:
                # GENIE_TYPES'ta da bilinen meta bloklarda da olmayan,
                # daha once hic gorulmemis bir blok basligi. Sessizce
                # atlamak yerine uyariyoruz - boylece gelecekte formatta
                # kucuk bir fark olursa fark edilmeden veri kaybi yasanmaz.
                # NOT: eger bu gercekten yeni bir Genie obje tipiyse,
                # '--add-type' komutuyla eklenebilir.
                print(
                    f"WARNING: Unrecognized block type '{candidate}' at line {idx}. "
                    f"If this is a new Genie object type, register it with: "
                    f"--add-type {candidate}. Skipped.",
                    file=sys.stderr
                )
                skipping_meta_block = True
                continue

        if current_type:
            kv_match = re.match(r'^([A-Za-z0-9_.]+)\s+(.+)$', stripped)
            if kv_match:
                key, val = kv_match.group(1).strip(), kv_match.group(2).strip()
                if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                    val = val[1:-1]

                if key == 'Name':
                    current_name = val
                elif key == 'Alias':
                    current_alias = val

    return objects


def generate_header_content(
    objects: List[GenieObject],
    strict: bool = False,
    type_config: Optional[Dict[str, str]] = None,
) -> str:
    if type_config is None:
        type_config = load_type_config()

    # Sozlugun ANAHTAR SIRASI, header'daki bolum sirasini belirliyor.
    TYPE_ORDER = list(type_config.keys())
    type_display = type_config

    warnings = []
    errors = []
    missing_alias_objects = []  # strict modda tek ozet hata icin biriktirilir

    seen_macros: Dict[str, GenieObject] = {}
    seen_type_indices: Dict[Tuple[str, int], GenieObject] = {}

    lines = [
        "#ifndef GENIE_OBJECTS_H",
        "#define GENIE_OBJECTS_H",
        "",
        "/*",
        " * AUTO-GENERATED FILE.",
        " *",
        " * Generated from 4D Systems Genie project.",
        " * Do not edit manually.",
        " */",
        ""
    ]

    for obj_type in TYPE_ORDER:
        type_objs = [o for o in objects if o.obj_type == obj_type]
        if not type_objs:
            continue

        type_objs.sort(key=lambda x: x.index)

        lines.append(f"/* {type_display.get(obj_type, obj_type)} */")

        for obj in type_objs:
            idx_key = (obj.obj_type, obj.index)
            if idx_key in seen_type_indices:
                errors.append(f"Duplicate index found: {obj.obj_type} index {obj.index} at line {obj.line_num}")
            else:
                seen_type_indices[idx_key] = obj

            default_name_pattern = re.match(r'^[A-Za-z]+(\d+)$', obj.alias)
            has_no_alias = not obj.alias or (default_name_pattern and obj.alias.lower() == obj.name.lower())

            if has_no_alias:
                msg = f"WARNING: {obj.obj_type} index {obj.index} does not have an alias."
                warnings.append(msg)
                if strict:
                    # Strict modda anlik WARNING basmiyoruz; hepsini
                    # biriktirip dongu bitince TEK bir ozet hata olarak
                    # raporluyoruz (ayni bilgiyi iki kere yazdirmamak icin).
                    missing_alias_objects.append((obj.obj_type, obj.index))
                else:
                    print(msg, file=sys.stderr)

            norm_name = normalize_to_macro_name(obj.alias)
            macro_name = f"{obj.obj_type.upper()}_{norm_name}"

            if macro_name in seen_macros:
                errors.append(f"Duplicate macro name generated: {macro_name} ({obj} vs {seen_macros[macro_name]})")
            else:
                seen_macros[macro_name] = obj

            lines.append(f"#define {macro_name} {obj.index}")

        lines.append("")

    lines.append("#endif /* GENIE_OBJECTS_H */\n")

    if missing_alias_objects:
        summary_lines = [f"Strict mode error: {len(missing_alias_objects)} object(s) missing alias:"]
        for obj_type, index in missing_alias_objects:
            summary_lines.append(f"  - {obj_type} index {index}")
        errors.append("\n".join(summary_lines))

    if errors:
        raise ValueError("\n".join(errors))

    return "\n".join(lines)


class _WideHelpFormatter(argparse.HelpFormatter):
    """--project/--output gibi uzun secenek isimlerinin aciklamayla ayni
    satirda kalmasi icin varsayilandan biraz daha genis bir yardim
    formati (help text hizasi kaymasin diye)."""
    def __init__(self, prog):
        super().__init__(prog, max_help_position=35, width=100)


def main():
    parser = argparse.ArgumentParser(
        description="Generate C header from 4D Systems Genie project.",
        formatter_class=_WideHelpFormatter,
    )
    parser.add_argument("--project", "-p", required=False, default=None,
                         help="Path to .4DGenie or .4DWork file/folder")
    parser.add_argument("--output", "-o", required=False, default=None,
                         help="Path to output header file (.h)")
    parser.add_argument("--strict", action="store_true",
                         help="Fail if any object lacks an alias")
    parser.add_argument("--check", action="store_true",
                         help="Check mode: Verify header is up to date without modifying")
    parser.add_argument("--dry-run", action="store_true",
                         help="Simulate the run: print the header that WOULD be generated "
                              "to stdout, without writing or modifying any file on disk.")
    parser.add_argument("--add-type", metavar="TYPE_NAME", default=None,
                         help="Register a new Genie object type (e.g. Gauge) in "
                              "genie_types.json and exit. No --project/--output "
                              "needed. Added to the end of the type list.")
    parser.add_argument("--list-types", action="store_true",
                         help="List all currently registered Genie object types "
                              "(from genie_types.json) and exit. If genie_types.json "
                              "does not exist yet, it is created with the default "
                              "type list first, then shown.")

    args = parser.parse_args()

    if args.check and args.dry_run:
        parser.error("--check and --dry-run cannot be used together.")

    # --- add-type modu: proje/output gerektirmez, tip kaydedip cikar ---
    if args.add_type:
        try:
            added = add_type(args.add_type)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if added:
            print(f"Added new Genie object type: '{args.add_type}'.")
            print("It will now be recognized automatically when parsing .4DGenie files.")
            sys.exit(0)
        else:
            print(f"Error: type '{args.add_type}' already exists in genie_types.json.", file=sys.stderr)
            sys.exit(1)

    # --- list-types modu: proje/output gerektirmez, mevcut tipleri gosterip cikar ---
    if args.list_types:
        existed_before = os.path.exists(DEFAULT_TYPES_CONFIG_PATH)
        type_config = load_type_config()

        if not existed_before:
            print(
                f"No genie_types.json found yet - created one with the default "
                f"type list at: {DEFAULT_TYPES_CONFIG_PATH}",
                file=sys.stderr
            )
            print("", file=sys.stderr)

        print(f"Registered Genie object types ({len(type_config)}):")
        for i, (type_name, display) in enumerate(type_config.items(), start=1):
            if type_name == display:
                print(f"  {i}. {type_name}")
            else:
                print(f"  {i}. {type_name}  (section title: '{display}')")
        sys.exit(0)

    # --- normal calisma modu: proje/output zorunlu ---
    if not args.project or not args.output:
        parser.error("--project and --output are required (unless using --add-type).")

    project_file = args.project
    if os.path.isdir(project_file):
        for root, _, files in os.walk(project_file):
            for file in files:
                if file.endswith('.4DGenie'):
                    project_file = os.path.join(root, file)
                    break

    try:
        type_config = load_type_config()
        objects = parse_4dgenie(project_file, type_config=type_config)
        new_header = generate_header_content(objects, strict=args.strict, type_config=type_config)

        if args.dry_run:
            print(new_header)
            line_count = len(new_header.splitlines())
            print(
                f"\n[DRY RUN] No file was written. {line_count} lines would be written to: {args.output}",
                file=sys.stderr
            )
            sys.exit(0)

        if args.check:
            if not os.path.exists(args.output):
                print(f"Error: Output file {args.output} does not exist for check mode.", file=sys.stderr)
                sys.exit(1)
            with open(args.output, 'r', encoding='utf-8') as f:
                current_header = f.read()

            if current_header != new_header:
                print("Error: Generated header does not match existing header. Run generator to update.", file=sys.stderr)
                sys.exit(1)
            else:
                print("Check passed: Header is up to date.")
                sys.exit(0)

        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(new_header)

        print(f"Successfully generated header: {args.output}")
        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
