Custom Unix Shell (mysh)
Overview

mysh is a custom Unix-like shell implemented in Python. It supports command parsing, built-in commands, environment variable expansion, pipelines and execution of external programs using low-level operating system primitives.

The project demonstrates how a shell translates user input into executable processes while managing inter-process communication and terminal control.

Features
Built-in commands: cd, pwd, exit, which, var, chmod, help
Execution of external programs via fork and exec
Pipeline support using |
Environment variable expansion using ${VAR}
Escaped variable handling (e.g. \${VAR})
Shell configuration via .myshrc
Input validation for syntax errors (pipes, quotes)
Customisable shell prompt

File Structure
mysh.py      → main shell execution engine
parsing.py   → command parsing (pipe-aware splitting)
tests/       → input/output-based test cases

Execution Flow
The shell follows a structured pipeline from user input to execution:

User Input
→ Syntax Validation
→ Pipe Splitting
→ Variable Expansion
→ Tokenisation (shlex)
→ Command Dispatch
→ Execution (built-in or external)
→ Output

Core Components
Entry Point
The program starts in mysh.py:

if __name__ == "__main__":
    main()

main() initialises the shell environment and starts the interactive loop.

Shell Loop (run_shell)
run_shell() is the core of the program. It:

Reads user input
Validates syntax
Splits commands by pipes
Expands variables
Dispatches commands

Command Dispatch
Commands are classified into:

Built-in Commands

Handled directly inside the shell:

cd → change directory
pwd → print working directory
exit → terminate shell
which → locate command
var → manage environment variables
chmod → modify file permissions
help → display available commands

These do not create new processes.

External Commands

All non built-in commands are executed using:

os.fork() → create child process
os.execvp() → replace process with program
os.waitpid() → parent waits for completion

Pipelines
Pipelines are handled using:

os.pipe() → create communication channels
os.dup2() → redirect stdin/stdout
os.fork() → create processes for each command

This allows chaining commands such as:

ls | grep file | wc -l
Environment Variables

The shell supports variable expansion:

echo ${HOME}
Variables are stored in os.environ
Expansion is handled manually by parsing logic
Escaped variables (e.g. \${VAR}) are treated as literals
Configuration (.myshrc)

The shell loads environment variables from a .myshrc file at startup:

JSON-based configuration
Validates variable names and values
Supports variable expansion within config

State Management
The shell maintains its state using:

current_working_directory → tracks logical directory
os.environ → stores environment variables
prompt → controls shell prompt display
process groups → manage terminal control for child processes

Testing Strategy
Testing is performed using input/output file comparison:

.in files simulate user input
.out files define expected output
Covers:
built-in commands
pipelines (including multiple pipes)
path resolution
variable handling
error cases

Concepts Demonstrated
This project demonstrates key systems and programming concepts:

Operating Systems
Process creation (fork)
Program execution (exec)
Inter-process communication (pipes)
File descriptor manipulation (dup2)
Process groups and terminal control
Signal handling
Programming
Command parsing and tokenisation
String processing
Error handling and validation
Modular design
Environment variable management
Example Usage
>> pwd
/home/user

>> var NAME Winston
>> echo ${NAME}
Winston

>> ls | grep mysh
mysh.py

>> which python
/usr/bin/python
Summary

mysh is a simplified but functional Unix shell that demonstrates how high-level user commands are translated into low-level system operations. It has provided me with hands-on exposure to process management, command parsing, and inter-process communication.