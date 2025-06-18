# V8 Fuzzing Selective Instrumentation

This tool lets you enable selective instrumentation in the V8 JavaScript engine to focus fuzz testing on specific files.

---

## Requirements
- Installed depot_tools
- Local Chromium source code clone

---

## Usage

```bash
python3 selective_instrumentation.py <build_dir> --targets <v8/src/file1.cc> <v8/src/file2.cc> ...
