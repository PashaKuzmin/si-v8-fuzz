# V8 Fuzzing Selective Instrumentation

A tool for enabling selective instrumentation in the V8 JavaScript engine to support fuzz testing. This helps focus fuzzing on specific source files.

---

## Requirements
- depot_tools installed
- A local clone of the Chromium source code

---

## Usage

```bash
python3 selective_instrumentation.py <build_dir> --targets <v8/src/file1.cc> <v8/src/file2.cc> ...