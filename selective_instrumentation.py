import os
import re
import argparse
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Runs a shell command with error handling"""
    print(f"\n[+] Executing: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd, cwd=cwd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Command failed (exit code {e.returncode})")
    except FileNotFoundError:
        print("[!] Command not found. Ensure gn and ninja are installed and in PATH")
    return False

def check_dependencies():
    """Checks for required system tools"""
    required = ['gn', 'ninja', 'clang++']
    missing = []
    for tool in required:
        if not any(Path(p).joinpath(tool).exists() for p in os.environ['PATH'].split(os.pathsep)):
            missing.append(tool)
    
    if missing:
        print(f"[!] Critical dependencies missing: {', '.join(missing)}")
        return False
    return True

def modify_toolchain(toolchain_path):
    """Adds custom instrumentation rule to toolchain.ninja"""
    try:
        with open(toolchain_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if "rule cxx-instr" not in content:
            new_rule = (
                "\n"
                "rule cxx-instr\n"
                "  command =  ../../third_party/llvm-build/Release+Asserts/bin/clang++ -fsanitize-coverage=trace-pc-guard -MMD -MF ${out}.d ${defines} ${include_dirs} ${cflags} ${cflags_cc} -c ${in} -o ${out}\n"
                "  description = CXX ${out}\n"
                "  depfile = ${out}.d\n"
                "  deps = gcc\n"
            )
            
            new_content = re.sub(
                r'(rule cxx\n.+?)(\n\n|\Z)',
                r'\1' + new_rule + r'\2',
                content,
                flags=re.DOTALL
            )
            
            with open(toolchain_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"[+] Added cxx-instr rule to {toolchain_path}")
        else:
            print(f"[i] cxx-instr rule already exists in {toolchain_path}")
    except Exception as e:
        print(f"[!] Error modifying toolchain: {e}")

def selective_instrumentation(build_dir, target_files):
    """Modifies build files for target sources in obj/v8"""
    modified_count = 0
    v8_obj_dir = Path(build_dir) / 'obj' / 'v8'
    
    if not v8_obj_dir.exists():
        print(f"[!] V8 directory not found: {v8_obj_dir}")
        return
    
    # Normalize target filenames
    target_basenames = [os.path.basename(t) for t in target_files]
    print(f"[i] Searching for: {', '.join(target_basenames)} in {v8_obj_dir}")
    
    for ninja_file in v8_obj_dir.glob('*.ninja'):
        try:
            modified = False
            lines = []
            
            with open(ninja_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Check if it's a cxx build rule for target file
                    if ': cxx ' in line and any(f'/{name}"' in line or f'/{name}' in line for name in target_basenames):
                        new_line = line.replace(': cxx ', ': cxx-instr ')
                        if new_line != line:
                            modified = True
                        lines.append(new_line)
                    else:
                        lines.append(line)
            
            if modified:
                with open(ninja_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                modified_count += 1
                print(f"[+] Modified {ninja_file.name}")
        except Exception as e:
            print(f"[!] Error processing {ninja_file}: {e}")
    
    print(f"\n[i] Result: Modified {modified_count} build files")

parser = argparse.ArgumentParser(description='V8 Selective Instrumentation Tool')
parser.add_argument('build_dir', help='Build directory path (e.g., out/Release)')
parser.add_argument('--targets', nargs='+', required=True, 
                    help='Target source files (e.g., v8/src/compiler/node-properties.cc)')

args = parser.parse_args()

# 1. Dependency check
if not check_dependencies():
    sys.exit(1)

# 2. Generate project with GN
gn_args = [
    'dcheck_always_on=true',
    'is_asan=true',
    'is_debug=false',
    'target_cpu="x64"',
    'use_sanitizer_coverage=false',
    'v8_enable_verify_heap=true',
    'v8_fuzzilli=true',
    'v8_static_library=true'
]

if not run_command([
    'gn', 'gen', args.build_dir,
    '--args=' + ' '.join(gn_args)
]):
    sys.exit(1)

# 3. Modify build system
toolchain_path = Path(args.build_dir) / 'toolchain.ninja'
if not toolchain_path.exists():
    print(f"[!] Error: {toolchain_path} not found!")
    sys.exit(1)

modify_toolchain(toolchain_path)
selective_instrumentation(args.build_dir, args.targets)

# 4. Build d8 with Ninja
if not run_command(['ninja', '-C', args.build_dir, 'd8']):
    print("\n[!] Build failed. Check configuration.")
    sys.exit(1)

print("\n[+] Success! d8 built with selective instrumentation.")