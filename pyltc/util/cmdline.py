"""
Command line execution utility module.

"""
import time
import subprocess


def popen_factory():
    """Returns subprocess.Popen on Linux, otherwise returns MockPopen
       class assuming this is a test run."""
    import platform
    if platform.system() == 'Linux':
        return subprocess.Popen

    class MockPopen(object):
        """Mocks command execution to allow testing on non-Linux OS."""
        def __init__(self, command_list, *args, **kw):
            self._cmd_list = command_list
            self._args = args
            self._kw = kw
            self.returncode = 0

        def communicate(self, timeout=None):
            if self._cmd_list[0].endswith('echo'):
                return bytes(" ".join(self._cmd_list[1:]), encoding='utf-8'), None
            if self._cmd_list[0].endswith('/bin/true'):
                return None, None
            if self._cmd_list[0].endswith('/bin/false'):
                self.returncode = 1
                return None, None
            if self._cmd_list[0].endswith('sleep'):
                pause = float(self._cmd_list[1])
                if timeout and timeout < pause:
                        time.sleep(timeout)
                        cmd = " ".join(self._cmd_list)
                        raise subprocess.TimeoutExpired(cmd, timeout)
                time.sleep(pause)
                return None, None
            raise RuntimeError("UNREACHABLE")
    return MockPopen


class CommandFailed(Exception):
    """Rased when a command line execution yielded a non-zero return code."""

    def __init__(self, command):
        assert isinstance(command, CommandLine) and command.returncode, \
                 "expecting failed command, got {!r}".format(command)
        output = command.stderr
        if command.stdout:
            output = "out:{}\nerr: {}".format(command.stdout, output)
        msg = "Command failed (rc={}, {!r})".format(command.returncode, command.cmdline)
        if output:
            msg += ": " + output
        super(CommandFailed, self).__init__(msg)
        self._command = command

    @property
    def returncode(self):
        return self._command.returncode


class CommandLine(object):
    """Command line execution class."""

    def __init__(self, cmdline, ignore_errors=False, verbose=False, sudo=False):
        self._cmdline = cmdline
        self._ignore_errors = ignore_errors
        self._verbose = verbose
        self._sudo = sudo
        self._returncode = None
        self._stdout = None
        self._stderr = None
        self._proc = None

    @property
    def cmdline(self):
        return self._cmdline

    def _construct_cmd_list(self, command):
        """Recursively process the command string to exctract any quoted segments
           as a single command element.
           """
        QUOTE = '"'

        def validate(command):
            quote_count = command.count(QUOTE)
            if quote_count % 2 != 0:
                raise RuntimeError('Unbalanced quotes in command: {!r}'.format(command))

        def construct_the_list(command):
            if QUOTE not in command:
                return command.split()
            left, mid, right = command.split(QUOTE, 2)
            return left.split() + [mid] + construct_the_list(right)  # recursively process the right part

        validate(command)
        result = ['sudo'] if self._sudo else []
        result += construct_the_list(command)
        return result

    def terminate(self):
        # TODO: refactor
        if not self._proc:
            return None
        self._proc.terminate()
        rc = self._proc.poll()
        c = 0
        while rc == None:
            time.sleep(0.1)
            if c > 19:
                self._proc.kill()
                break
            c += 1
            rc = self._proc.poll()
        time.sleep(0.1)
        return self._proc.poll()

    def execute_daemon(self):
        command_list = self._construct_cmd_list(self._cmdline)
        PopenClass = popen_factory()
        proc = PopenClass(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._proc = proc
        return self  # allows for one-line creation + execution with assignment

    def execute(self, timeout=10):
        """Prepares and executes the command."""
        command_list = self._construct_cmd_list(self._cmdline)
        PopenClass = popen_factory()
        proc = PopenClass(command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._proc = proc
        stdout, stderr = proc.communicate(timeout=timeout)
        self._stdout = stdout.decode('unicode_escape') if stdout else ""
        self._stderr = stderr.decode('unicode_escape') if stderr else ""
        rc = proc.returncode
        self._returncode = rc
        if self._verbose:
            print(">", " ".join(command_list))
        if rc and not self._ignore_errors:
            raise CommandFailed(self)
        return self  # allows for one-line creation + execution with assignment

    @property
    def returncode(self):
        return self._returncode

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr
