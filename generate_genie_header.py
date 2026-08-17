#!/usr/bin/env python3
"""
4D Systems Genie C Header Generator
Parses .4DGenie / .4DWork project files and generates deterministic C/C++ headers.
"""

import sys
import os
import re
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
    """
    Normalizes alias strings to valid C macro identifiers:
    - MainMenu / mainMenu -> MAIN_MENU
    - Main Menu / Connect-Button -> MAIN_MENU / CONNECT_BUTTON
    - Removes invalid characters, collapses multiple underscores, prevents starting with digit.
    """
    if not alias:
        return ""

    # PascalCase/camelCase to snake_case (örn: SettingsMenu -> Settings_Menu, IPv4 -> I_Pv4 etc.)
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', alias)
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)

    # Convert non-alphanumeric characters (spaces, dashes, dots, etc.) to underscore
    s3 = re.sub(r'[^a-zA-Z0-9_]', '_', s2)

    # Collapse multiple underscores into one
    s4 = re.sub(r'_+', '_', s3)

    # Strip leading/trailing underscores and convert to uppercase
    result = s4.strip('_').upper()

    # C identifiers cannot start with a digit
    if result and result[0].isdigit():
        result = '_' + result

    return result


def parse_4dgenie(file_path: str) -> List[GenieObject]:
    """
    Parses a .4DGenie text file and extracts objects with their types, index, name, and alias.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Project file not found: {file_path}")

    # All known Genie Object Types (12 Proje Tipi)
    GENIE_TYPES = {
        'Form', 'UserButton', 'WinButton', 'Strings', 'Image',
        'UserImages', 'Keyboard', 'Panel', 'Border', 'Video', 'Sounds',
        'StaticText'
    }

    objects: List[GenieObject] = []

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    current_type: Optional[str] = None
    current_name: Optional[str] = None
    current_alias: Optional[str] = None
    block_start_line = 0

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith(';'):
            continue

        if stripped == 'end':
            if current_type and current_type in GENIE_TYPES:
                # Extract index from name (e.g. Form0 -> 0, Userbutton56 -> 56)
                index_match = re.search(r'\d+$', current_name or '')
                index = int(index_match.group()) if index_match else 0
                alias = current_alias if current_alias else (current_name or '')

                objects.append(GenieObject(
                    obj_type=current_type,
                    name=current_name or '',
                    alias=alias,
                    index=index,
                    line_num=block_start_line
                ))
            current_type = None
            current_name = None
            current_alias = None
            continue

        # Check if line is starting a new object block
        parts = stripped.split()
        if len(parts) == 1 and parts[0] in GENIE_TYPES:
            current_type = parts[0]
            current_name = None
            current_alias = None
            block_start_line = idx
            continue

        # Parse key-value properties
        if current_type:
            kv_match = re.match(r'^([A-Za-z0-9_.]+)\s+(.+)$', stripped)
            if kv_match:
                key, val = kv_match.group(1).strip(), kv_match.group(2).strip()
                # Remove quotes if present
                if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                    val = val[1:-1]

                if key == 'Name':
                    current_name = val
                elif key == 'Alias':
                    current_alias = val

    return objects


def generate_header_content(objects: List[GenieObject], strict: bool = False) -> str:
    """
    Generates deterministic C header file content from parsed objects.
    """
    # Deterministic export order across the 12 project types
    TYPE_ORDER = [
        'Form', 'UserButton', 'WinButton', 'Strings',
        'UserImages', 'Keyboard', 'Video', 'Image',
        'Sounds', 'StaticText', 'Panel', 'Border'
    ]

    type_display = {
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
        'Border': 'Borders'
    }

    warnings = []
    errors = []

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

        # Sort deterministically by index
        type_objs.sort(key=lambda x: x.index)

        lines.append(f"/* {type_display.get(obj_type, obj_type)} */")

        for obj in type_objs:
            # Check duplicate index in the same type
            idx_key = (obj.obj_type, obj.index)
            if idx_key in seen_type_indices:
                errors.append(f"Duplicate index found: {obj.obj_type} index {obj.index} at line {obj.line_num}")
            else:
                seen_type_indices[idx_key] = obj

            # Check missing alias
            default_name_pattern = re.match(r'^[A-Za-z]+(\d+)$', obj.alias)
            has_no_alias = not obj.alias or (default_name_pattern and obj.alias.lower() == obj.name.lower())

            if has_no_alias:
                msg = f"WARNING: {obj.obj_type} index {obj.index} does not have an alias."
                warnings.append(msg)
                print(msg, file=sys.stderr)
                if strict:
                    errors.append(f"Strict mode error: {obj.obj_type} index {obj.index} has no alias.")

            norm_name = normalize_to_macro_name(obj.alias)
            macro_name = f"{obj.obj_type.upper()}_{norm_name}"

            # Check duplicate macro
            if macro_name in seen_macros:
                errors.append(f"Duplicate macro name generated: {macro_name} ({obj} vs {seen_macros[macro_name]})")
            else:
                seen_macros[macro_name] = obj

            lines.append(f"#define {macro_name} {obj.index}")

        lines.append("")

    lines.append("#endif /* GENIE_OBJECTS_H */\n")

    if errors:
        raise ValueError("\n".join(errors))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate C header from 4D Systems Genie project.")
    parser.add_argument("--project", "-p", required=True, help="Path to .4DGenie or .4DWork file/folder")
    parser.add_argument("--output", "-o", required=True, help="Path to output header file (.h)")
    parser.add_argument("--strict", action="store_true", help="Fail if any object lacks an alias")
    parser.add_argument("--check", action="store_true", help="Check mode: Verify header is up to date without modifying")

    args = parser.parse_args()

    project_file = args.project
    if os.path.isdir(project_file):
        for root, _, files in os.walk(project_file):
            for file in files:
                if file.endswith('.4DGenie'):
                    project_file = os.path.join(root, file)
                    break

    try:
        objects = parse_4dgenie(project_file)
        new_header = generate_header_content(objects, strict=args.strict)

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

        # Write output file
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