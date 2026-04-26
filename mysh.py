"""
mysh.py - A customised shell implementation for handling and parsing various commands.
"""

import shlex
import json
import signal
import sys
import os
from parsing import split_by_pipe_op


def setup_signals() -> None:
    """
    Setup signals required by this program.
    """
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)


def myshrc():
    """
    Load and parses the .myshrc configuration file.
    """
    myshrc_path = os.path.expanduser("~/.myshrc")
    myshdotdir = os.environ.get("MYSHDOTDIR")

    if myshdotdir:
        myshrc_path = os.path.join(myshdotdir, ".myshrc")

    if os.path.exists(myshrc_path):
        with open(myshrc_path, 'r', encoding='utf-8') as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError:
                print("mysh: invalid JSON format for .myshrc", file=sys.stderr)
                return

        for var, value in settings.items():
            if not isinstance(value, str):
                print(f"mysh: .myshrc: {var}: not a string", file=sys.stderr)
                continue

            if not all(c.isalnum() or c == '_' for c in var):
                print(f"mysh: .myshrc: {var}: invalid characters for variable name", file=sys.stderr)
                continue

            value = os.path.expandvars(value)
            os.environ[var] = value


def main() -> None:
    """
    Main function that initialises the shell.
    """
    setup_signals()
    myshrc()
    default_variables()
    run_shell()


def handle_exit(command_exit):
    """
    Handles the exit command and exits the shell as per task outline.
    """
    if len(command_exit) > 2:
        print("exit: too many arguments", file=sys.stderr)
        return False

    if len(command_exit) == 2:
        try:
            exit_code = int(command_exit[1])
        except ValueError:
            print(f"exit: non-integer exit code provided: {command_exit[1]}", file=sys.stderr)
            return False
        sys.exit(exit_code)

    sys.exit(0)


current_working_directory = os.getcwd()


def handle_pwd(command_parts, return_output=False):
    """
    Prints or returns the current working directory.
    If the -P flag is provided, this method resolves any sym links and prints the 'real path.'
    """
    if len(command_parts) > 1:
        for part in command_parts[1:]:
            if not part.startswith("-"):
                print("pwd: not expecting any arguments", file=sys.stderr)
                return ""
            for char in part[1:]:
                if char != "P":
                    print(f"pwd: invalid option: -{char}", file=sys.stderr)
                    return ""

    current_dir = os.path.realpath(current_working_directory) if "-P" in command_parts else current_working_directory

    if return_output:
        return current_dir
    print(current_dir)


def handle_cd(command_parts):
    """
    Handles the cd command. Changes the current working directory and updates
    the global current_working_directory variable accordingly.
    """
    global current_working_directory

    if len(command_parts) > 2:
        print(f"cd: too many arguments", file=sys.stderr)
        return

    if len(command_parts) == 1 or command_parts[1] == '~':
        new_directory = os.path.expanduser('~')
    else:
        new_directory = command_parts[1]

    try:
        os.chdir(new_directory)
        current_working_directory = os.path.normpath(os.path.join(current_working_directory, new_directory))
        os.environ['PWD'] = current_working_directory
    except FileNotFoundError:
        print(f"cd: no such file or directory: {new_directory}", file=sys.stderr)
    except NotADirectoryError:
        print(f"cd: not a directory: {new_directory}", file=sys.stderr)
    except PermissionError:
        print(f"cd: permission denied: {new_directory}", file=sys.stderr)


built_in_commands = ['exit', 'pwd', 'cd', 'which', 'var', 'help']


def handle_which(command_parts, return_output=False):
    """
    Handles the which command. Checks if the given commands are shell built-in commands which were programmed.
    """
    output = []
    if len(command_parts) == 1:
        print("usage: which command ...", file=sys.stderr)
        return ""

    for cmd in command_parts[1:]:
        if cmd in built_in_commands:
            output.append(f"{cmd}: shell built-in command")
        else:
            search_path = os.environ.get("PATH", os.defpath)
            found = False
            for path_dir in search_path.split(os.pathsep):
                executable_path = os.path.join(path_dir, cmd)
                if os.path.isfile(executable_path) and os.access(executable_path, os.X_OK):
                    output.append(executable_path)
                    found = True
                    break
            if not found:
                output.append(f"{cmd} not found")

    result = "\n".join(output)
    if return_output:
        return result
    print(result)


def handle_var(command_parts):
    """
    Initialises and sets environmental variables.
    """
    if len(command_parts) < 3:
        print(f"var: expected 2 arguments, got {len(command_parts) - 1}", file=sys.stderr)
        return

    if command_parts[1] == '-s':
        if len(command_parts) != 4:
            print(f"var: expected 2 arguments, got {len(command_parts) - 2}", file=sys.stderr)
            return
        variable_name = command_parts[2]
        command_argument = command_parts[3]

        r, w = os.pipe()
        pid = os.fork()
        if pid == 0:  
            os.close(r)  
            os.dup2(w, sys.stdout.fileno())
            os.close(w)

            try:
                command_list = shlex.split(command_argument)
                os.execvp(command_list[0], command_list)
            except FileNotFoundError:
                print(f"mysh: command not found: {command_list[0]}", file=sys.stderr)
            except PermissionError:
                print(f"mysh: permission denied: {command_list[0]}", file=sys.stderr)
            sys.exit(1)
        else:  
            os.close(w)
            with os.fdopen(r) as pipe_read:
                output = pipe_read.read().strip()
                if output:
                    os.environ[variable_name] = output
            os.waitpid(pid, 0)
    else:
        if command_parts[1].startswith('-'):
            for char in command_parts[1][1:]:
                if char != 's':
                    print(f"var: invalid option: -{char}", file=sys.stderr)
                    return

        if len(command_parts) != 3:
            print(f"var: expected 2 arguments, got {len(command_parts) - 1}", file=sys.stderr)
            return

        variable_name = command_parts[1]
        variable_value = os.path.expanduser(command_parts[2])

        if not all(c.isalnum() or c == '_' for c in variable_name):
            print(f"var: invalid characters for variable {variable_name}", file=sys.stderr)
            return

        os.environ[variable_name] = variable_value.strip('"').strip("'")

        if variable_name == "PROMPT":
            update_prompt()
        return

    if not all(c.isalnum() or c == '_' for c in variable_name):
        print(f"var: invalid characters for variable {variable_name}", file=sys.stderr)
        return



def update_prompt():
    """
    Updates the shell with the current PROMPT env variable.
    """
    global prompt
    prompt = os.path.expandvars(os.environ.get("PROMPT", ">> "))


def execute_command(command):
    """
    Execute a simple command like echo, like helper function.
    """
    if command.startswith('"') and command.endswith('"'):
        command = command[1:-1]
    if command.startswith("'") and command.endswith("'"):
        command = command[1:-1]

    expanded_command = ""
    i = 0
    while i < len(command):
        if command[i] == '\\' and i + 1 < len(command):
            expanded_command += command[i] + command[i + 1]
            i += 2
        else:
            expanded_command += command[i]
            i += 1

    expanded_command = expand_vars(expanded_command)

    if expanded_command.startswith("echo "):
        return expanded_command[5:].strip()

    return expanded_command


def expand_vars(command):
    """
    Expands environment variables in the command.
    """
    expanded_command = ""
    i = 0
    while i < len(command):
        if command[i:i+2] == '\\${':
            expanded_command += '${'
            i += 3
        elif command[i:i+2] == '${' and (i == 0 or command[i-1] != '\\'):
            j = i + 2
            while j < len(command) and command[j] != '}':
                j += 1
            if j < len(command):
                var_name = command[i + 2:j]
                if not all(c.isalnum() or c == '_' for c in var_name):
                    print(f"mysh: syntax error: invalid characters for variable {var_name}", file=sys.stderr)
                    return ""
                expanded_command += os.getenv(var_name, "")
                i = j + 1
                continue
        else:
            expanded_command += command[i]
            i += 1

    return expanded_command



def var_additionals(command):
    """
    Handles additional variable-related syntax/parsing.
    """
    i = 0
    expanded_command = ""
    inside_double_quotes = False

    while i < len(command):
        if command[i] == '"':
            inside_double_quotes = not inside_double_quotes
            expanded_command += command[i]
            i += 1
            continue

        if command[i:i + 2] == r'\${':
            expanded_command += r'\${'
            i += 3
            continue

        if command[i:i + 2] == '${' and (i == 0 or command[i - 1] != '\\'):
            j = i + 2
            while j < len(command) and command[j] != '}':
                j += 1
            var_name = command[i + 2:j]
            if not all(c.isalnum() or c == '_' for c in var_name):
                print(f"mysh: syntax error: invalid characters for variable {var_name}", file=sys.stderr)
                return ""

            expanded_value = os.getenv(var_name, "")
            expanded_command += expanded_value
            i = j + 1
            continue

        expanded_command += command[i]
        i += 1

    return expanded_command


def check_unterminated_quotes(command):
    """
    Ensures there are no unterminated quotes in the command,
    handling escaped quotes.
    """
    inside_single_quote = False
    inside_double_quote = False
    escaped = False

    i = 0
    while i < len(command):
        if command[i] == '\\' and not escaped:
            escaped = True
            i += 1
            continue

        if command[i] == '"' and not inside_single_quote and not escaped:
            inside_double_quote = not inside_double_quote
        elif command[i] == "'" and not inside_double_quote and not escaped:
            inside_single_quote = not inside_single_quote

        escaped = False 

        i += 1

    if inside_single_quote or inside_double_quote:
        print("mysh: syntax error: unterminated quote", file=sys.stderr)
        return False

    return True


def check_pipe_syntax(command):
    """
    Checks for proper pipe syntax in the command.
    """
    if '|' in command:
        parts = command.split('|')
        for part in parts:
            if not part.strip():
                print("mysh: syntax error: expected command after pipe", file=sys.stderr)
                return False
    return True


def handle_pipes(command_parts):
    """
    Handles piping, given there are multiple commands.
    """
    num_commands = len(command_parts)
    pipes = []

    for i in range(num_commands - 1):
        r, w = os.pipe()
        pipes.append((r, w))

    pgid = 0 

    for i in range(num_commands):
        command = command_parts[i].strip()
        command_given = shlex.split(command)

        if not command_given:
            print("mysh: syntax error: expected command after pipe", file=sys.stderr)
            return

        pid = os.fork()
        if pid == 0:  
            if i == 0:  
                os.setpgid(0, 0)
            else:  
                os.setpgid(0, pgid)

            if i > 0:  
                os.dup2(pipes[i - 1][0], 0)
            if i < num_commands - 1: 
                os.dup2(pipes[i][1], 1)

            for r, w in pipes:
                os.close(r)
                os.close(w)

            try:
                os.execvp(command_given[0], command_given)
            except FileNotFoundError:
                print(f"mysh: command not found: {command_given[0]}", file=sys.stderr)
            except PermissionError:
                print(f"mysh: permission denied: {command_given[0]}", file=sys.stderr)
            sys.exit(1)
        else:  
            if i == 0:
                pgid = pid
                os.setpgid(pid, pgid) 
            else:
                try:
                    os.setpgid(pid, pgid)  
                except PermissionError:
                    pass

    for r, w in pipes:
        os.close(r)
        os.close(w)

    with open("/dev/tty") as tty_fd:
        os.tcsetpgrp(tty_fd.fileno(), pgid)

    for _ in range(num_commands):
        os.wait()

    with open("/dev/tty") as tty_fd:
        os.tcsetpgrp(tty_fd.fileno(), os.getpgrp())


def default_variables():
    """
    Initialises the default environment variables.
    """
    if 'PROMPT' not in os.environ:
        os.environ['PROMPT'] = '>> '
    if 'MYSH_VERSION' not in os.environ:
        os.environ['MYSH_VERSION'] = '1.0'


def handle_chmod(command_parts):
    """
    Handle the chmod which uses os.stat to configure the method.
    """
    if len(command_parts) != 3:
        print(f"chmod: expected 2 arguments, got {len(command_parts) - 1}", file=sys.stderr)
        return

    mode = command_parts[1]
    path = os.path.expanduser(command_parts[2])

    try:
        current_mode = os.stat(path).st_mode
        if mode == '+x':
            new_mode = current_mode | 0o111
        elif mode == '-x':
            new_mode = current_mode & ~0o111
        else:
            print(f"chmod: invalid mode: {mode}", file=sys.stderr)
            return

        os.chmod(path, new_mode)
    except FileNotFoundError:
        print(f"chmod: cannot access '{path}': No such file or directory", file=sys.stderr)
    except PermissionError:
        print(f"mysh: permission denied: {path}", file=sys.stderr)

def handle_help(command_parts):
    """
    Handles the help function, by displaying the possible command options.
    """
    print("Built-in commands:")
    print("  exit [code]        - Exit the shell")
    print("  pwd [-P]           - Print current directory")
    print("  cd [dir]           - Change directory")
    print("  which command      - Locate a command")
    print("  var name value     - Set environment variable")
    print("  help               - Show this help message")

def run_shell():
    """
    Main loop that runs the shell.
    """
    update_prompt()

    while True:
        try:
            command = input(prompt).strip()

            if not check_unterminated_quotes(command):
                continue

            if not check_pipe_syntax(command):
                continue

            command_parts = split_by_pipe_op(command)

            if len(command_parts) > 1:
                handle_pipes(command_parts)
                continue

            command = var_additionals(command)

            try:
                command_given = shlex.split(command)
            except ValueError as e:
                if "No closing quotation" in str(e):
                    print("mysh: syntax error: unterminated quote", file=sys.stderr)
                    continue
                else:
                    raise

            if not command_given:
                continue

            if command_given[0] == "exit":
                if handle_exit(command_given):
                    break

            elif command_given[0] == "pwd":
                handle_pwd(command_given)

            elif command_given[0] == "cd":
                handle_cd(command_given)

            elif command_given[0] == "which":
                handle_which(command_given)

            elif command_given[0] == "var":
                handle_var(command_given)
                update_prompt()

            elif command_given[0] == "chmod":
                handle_chmod(command_given)

            elif command_given[0] == "help":
                handle_help(command_given)

            else:
                command_given = [os.path.expanduser(arg) if arg.startswith('~') else arg for arg in command_given]
                pid = os.fork()
                if pid == 0:
                    try:
                        os.setpgid(0, 0)
                        signal.signal(signal.SIGINT, signal.SIG_DFL) 
                        os.execvp(command_given[0], command_given)
                    except FileNotFoundError:
                        print(f"mysh: command not found: {command_given[0]}", file=sys.stderr)
                        os._exit(1)
                    except PermissionError:
                        print(f"mysh: permission denied: {command_given[0]}", file=sys.stderr)
                        os._exit(1)
                    except Exception as e:
                        print(f"Error: {str(e)}", file=sys.stderr)
                        os._exit(1)
                else:
                    try:
                        os.setpgid(pid, pid)
                    except PermissionError:
                        pass

                    child_pgid = os.getpgid(pid)
                    with open("/dev/tty") as tty_fd:
                        os.tcsetpgrp(tty_fd.fileno(), child_pgid)

                    try:
                        os.waitpid(pid, 0)
                    except KeyboardInterrupt:
                        os.killpg(child_pgid, signal.SIGINT)

                    with open("/dev/tty") as tty_fd:
                        os.tcsetpgrp(tty_fd.fileno(), os.getpgrp())

        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue


if __name__ == "__main__":
    main()

