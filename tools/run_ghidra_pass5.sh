#!/usr/bin/env bash
# Run Ghidra pass 5 (intro decode) headless against the exe.
#
# Usage: tools/run_ghidra_pass5.sh [output path]
#   default output: docs/ghidra-output/pass5_intro.txt
# Env overrides: GHIDRA_HOME, JAVA_HOME, GHIDRA_PROJECT_DIR.
# The Ghidra project is throwaway: imported fresh and deleted after the run.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
ghidra_home="${GHIDRA_HOME:-$HOME/ghidra/ghidra_12.1.2_PUBLIC}"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@21}"
output_path="${1:-$repo_root/docs/ghidra-output/pass5_intro.txt}"
project_dir="${GHIDRA_PROJECT_DIR:-$(mktemp -d)}"
mkdir -p "$project_dir"

[[ -x "$ghidra_home/support/analyzeHeadless" ]] || { echo "analyzeHeadless not found under $ghidra_home" >&2; exit 1; }
[[ -x "$JAVA_HOME/bin/java" ]] || { echo "java not found under $JAVA_HOME" >&2; exit 1; }

"$ghidra_home/support/analyzeHeadless" "$project_dir" pass5 \
    -import "$repo_root/FixitFelixJr.exe" \
    -overwrite \
    -scriptPath "$repo_root/tools" \
    -postScript GhidraPass5Intro.java "$output_path" \
    -deleteProject

[[ -s "$output_path" ]] || { echo "pass 5 produced no output at $output_path" >&2; exit 1; }
echo "pass 5 output: $output_path ($(wc -l < "$output_path") lines)"
