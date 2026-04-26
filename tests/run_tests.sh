#!/bin/bash

shell_script="../mysh.py"
test_dir="./io_files"

for input_file in "$test_dir"/*.in; do
    test_name=$(basename "$input_file" .in)

    expected_output_file="$test_dir/$test_name.out"
    actual_output_file="$test_dir/$test_name.actual"

    python3 "$shell_script" < "$input_file" > "$actual_output_file"

    if diff "$actual_output_file" "$expected_output_file" > /dev/null; then
        echo "$test_name: PASSED"
    else
        echo "$test_name: FAILED"
        diff "$actual_output_file" "$expected_output_file"
    fi
done

