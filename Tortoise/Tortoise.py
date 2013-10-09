import sublime
import sublime_plugin
import os.path
import subprocess
import re
import time


class RepositoryNotFoundError(Exception):
    pass


class NotFoundError(Exception):
    pass


file_status_cache = {}


class TortoiseCommand():
    def get_path(self, paths):
        if paths == True:
            return self.window.active_view().file_name()
        return paths[0] if paths else self.window.active_view().file_name()

    def get_vcs(self, path):
        settings = sublime.load_settings('Tortoise.sublime-settings')

        if path == None:
            raise NotFoundError('Unable to run commands on an unsaved file')
        vcs = None

        try:
            vcs = TortoiseSVN(settings.get('svn_tortoiseproc_path'), path)
        except (RepositoryNotFoundError):
            pass

        try:
            vcs = TortoiseGit(settings.get('git_tortoiseproc_path'), path)
        except (RepositoryNotFoundError):
            pass

        try:
            vcs = TortoiseHg(settings.get('hg_hgtk_path'), path)
        except (RepositoryNotFoundError):
            pass

        if vcs == None:
            raise NotFoundError('The current file does not appear to be in an ' +
                'SVN, Git or Mercurial working copy')

        return vcs

    def menus_enabled(self):
        settings = sublime.load_settings('Tortoise.sublime-settings')
        return settings.get('enable_menus', True)


def handles_not_found(fn):
    def handler(self, *args, **kwargs):
        try:
            fn(self, *args, **kwargs)
        except (NotFoundError) as (exception):
            sublime.error_message('Tortoise: ' + str(exception))
    return handler


def invisible_when_not_found(fn):
    def handler(self, *args, **kwargs):
        try:
            res = fn(self, *args, **kwargs)
            if res != None:
                return res
            return True
        except (NotFoundError):
            return False
    return handler


class TortoiseExploreCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).explore(path if paths else None)


class TortoiseCommitCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).commit(path if os.path.isdir(path) else None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        if not path:
            return False
        self.get_vcs(path)
        return os.path.isdir(path)


class TortoiseStatusCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).status(path if os.path.isdir(path) else None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        if not path:
            return False
        self.get_vcs(path)
        return os.path.isdir(path)


class TortoiseSyncCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).sync(path if os.path.isdir(path) else None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        if not path:
            return False
        self.get_vcs(path)
        return os.path.isdir(path)


class TortoiseLogCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).log(path if paths else None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        vcs = self.get_vcs(path)
        if os.path.isdir(path):
            return True
        return path and vcs.get_status(path) in \
            ['A', '', 'M', 'R', 'C', 'U']

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return path and self.get_vcs(path).get_status(path) in \
            ['', 'M', 'R', 'C', 'U']

class TortoiseBlameCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).blame(path if paths else None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        if os.path.isdir(path):
            return False
        vcs = self.get_vcs(path)
        return path and vcs.get_status(path) in \
            ['A', '', 'M', 'R', 'C', 'U']

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return False
        return path and self.get_vcs(path).get_status(path) in \
            ['A', '', 'M', 'R', 'C', 'U']

class TortoiseDiffCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).diff(path if paths else None)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        vcs = self.get_vcs(path)
        if os.path.isdir(path):
            return True
        return vcs.get_status(path) in \
            ['A', '', 'M', 'R', 'C', 'U']

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        vcs = self.get_vcs(path)
        if isinstance(vcs, TortoiseHg):
            return vcs.get_status(path) in ['M']
        else:
            return vcs.get_status(path) in ['A', 'M', 'R', 'C', 'U']


class TortoiseAddCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).add(path)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        return self.get_vcs(path).get_status(path) in ['D', '?']


class TortoiseRemoveCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).remove(path)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        return self.get_vcs(path).get_status(path) in \
            ['A', '', 'M', 'R', 'C', 'U']

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return self.get_vcs(path).get_status(path) in ['']


class TortoiseRevertCommand(sublime_plugin.WindowCommand, TortoiseCommand):
    @handles_not_found
    def run(self, paths=None):
        path = self.get_path(paths)
        self.get_vcs(path).revert(path)

    @invisible_when_not_found
    def is_visible(self, paths=None):
        if not self.menus_enabled():
            return False
        path = self.get_path(paths)
        return self.get_vcs(path).get_status(path) in \
            ['A', '', 'M', 'R', 'C', 'U']

    @invisible_when_not_found
    def is_enabled(self, paths=None):
        path = self.get_path(paths)
        if os.path.isdir(path):
            return True
        return self.get_vcs(path).get_status(path) in \
            ['A', 'M', 'R', 'C', 'U']


class ForkGui():
    def __init__(self, cmd, cwd):
        subprocess.Popen(cmd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=cwd)


class Tortoise():
    def find_root(self, name, path, find_first=True):
        root_dir = None
        last_dir = None
        cur_dir  = path if os.path.isdir(path) else os.path.dirname(path)
        while cur_dir != last_dir:
            if root_dir != None and not os.path.exists(os.path.join(cur_dir,
                    name)):
                break
            if os.path.exists(os.path.join(cur_dir, name)):
                root_dir = cur_dir
                if find_first:
                    break
            last_dir = cur_dir
            cur_dir  = os.path.dirname(cur_dir)

        if root_dir == None:
            raise RepositoryNotFoundError('Unable to find ' + name +
                ' directory')
        self.root_dir = root_dir

    def set_binary_path(self, path_suffix, binary_name, setting_name):
        root_drive = os.path.expandvars('%HOMEDRIVE%\\')

        possible_dirs = [
            'Program Files\\',
            'Program Files (x86)\\'
        ]

        for dir in possible_dirs:
            path = root_drive + dir + path_suffix
            if os.path.exists(path):
                self.path = path
                return

        self.path = None
        normal_path = root_drive + possible_dirs[0] + path_suffix
        raise NotFoundError('Unable to find ' + self.__class__.__name__ +
                            '.\n\nPlease add the path to ' + binary_name +
                            ' to the setting "' + setting_name + '" in "' +
                            sublime.packages_path() +
                            '\\Tortoise\\Tortoise.sublime-settings".\n\n' +
                            'Example:\n\n' + '{"' + setting_name + '": r"' +
                            normal_path + '"}')

    def explore(self, path=None):
        if path == None:
            ForkGui('explorer.exe "' + self.root_dir + '"', None)
        else:
            ForkGui('explorer.exe "' + os.path.dirname(path) + '"', None)

    def process_status(self, vcs, path):
        global file_status_cache
        settings = sublime.load_settings('Tortoise.sublime-settings')
        if path in file_status_cache and file_status_cache[path]['time'] > \
                time.time() - settings.get('cache_length'):
            if settings.get('debug'):
                print 'Fetching cached status for %s' % path
            return file_status_cache[path]['status']

        if settings.get('debug'):
            start_time = time.time()

        try:
            status = vcs.check_status(path)
        except (Exception) as (exception):
            sublime.error_message(str(exception))

        file_status_cache[path] = {
            'time': time.time() + settings.get('cache_length'),
            'status': status
        }

        if settings.get('debug'):
            print 'Fetching status for %s in %s seconds' % (path,
                str(time.time() - start_time))

        return status


class TortoiseProc(Tortoise):
    def status(self, path=None):
        path = self.root_dir if path == None else path
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:repostatus /path:"%s"' % path,
            self.root_dir)

    def commit(self, path=None):
        path = self.root_dir if path == None else path
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:commit /path:"%s"' % path,
            self.root_dir)

    def log(self, path=None):
        path = self.root_dir if path == None else path
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:log /path:"%s"' % path,
            self.root_dir)

    def blame(self, path=None):
        path = self.root_dir if path == None else path
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:blame /path:"%s"' % path,
            self.root_dir)

    def diff(self, path):
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:diff /path:"%s"' % path,
            self.root_dir)

    def add(self, path):
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:add /path:"%s"' % path,
            self.root_dir)

    def remove(self, path):
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:remove /path:"%s"' % path,
            self.root_dir)

    def revert(self, path):
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:revert /path:"%s"' % path,
            self.root_dir)


class TortoiseSVN(TortoiseProc):
    def __init__(self, binary_path, file):
        self.find_root('.svn', file, False)
        if binary_path != None:
            self.path = binary_path
        else:
            self.set_binary_path('TortoiseSVN\\bin\\TortoiseProc.exe',
                'TortoiseProc.exe', 'svn_tortoiseproc_path')

    def sync(self, path=None):
        path = self.root_dir if path == None else path
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:update /path:"%s"' % path,
            self.root_dir)

    def get_status(self, path):
        svn = SVN(self.root_dir)
        return self.process_status(svn, path)


class TortoiseGit(TortoiseProc):
    def __init__(self, binary_path, file):
        self.find_root('.git', file)
        if binary_path != None:
            self.path = binary_path
        else:
            self.set_binary_path('TortoiseGit\\bin\\TortoiseProc.exe',
                'TortoiseProc.exe', 'git_tortoiseproc_path')

    def sync(self, path=None):
        path = self.root_dir if path == None else path
        path = os.path.relpath(path, self.root_dir)
        ForkGui('"' + self.path + '" /command:sync /path:"%s"' % path,
            self.root_dir)

    def get_status(self, path):
        git = Git(self.path, self.root_dir)
        return self.process_status(git, path)


class TortoiseHg(Tortoise):
    def __init__(self, binary_path, file):
        self.find_root('.hg', file)
        if binary_path != None:
            self.path = binary_path
        else:
            try:
                self.set_binary_path('TortoiseHg\\thgw.exe',
                    'thgw.exe', 'hg_hgtk_path')
            except (NotFoundError):
                self.set_binary_path('TortoiseHg\\hgtk.exe',
                    'thgw.exe (for TortoiseHg v2.x) or hgtk.exe (for ' +
                    'TortoiseHg v1.x)', 'hg_hgtk_path')

    def status(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'status', '--nofork', path]
        ForkGui(args, self.root_dir)

    def commit(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'commit', '--nofork', path]
        ForkGui(args, self.root_dir)

    def sync(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'synch', '--nofork', path]
        ForkGui(args, self.root_dir)

    def log(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'log', '--nofork', path]
        ForkGui(args, self.root_dir)

    def blame(self, path=None):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'blame', '--nofork', path]
        ForkGui(args, self.root_dir)

    def diff(self, path):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'vdiff', '--nofork', path]
        ForkGui(args, self.root_dir)

    def add(self, path):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'add', '--nofork', path]
        ForkGui(args, self.root_dir)

    def remove(self, path):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'remove', '--nofork', path]
        ForkGui(args, self.root_dir)

    def revert(self, path):
        path = os.path.relpath(path, self.root_dir)
        args = [self.path, 'revert', '--nofork', path]
        ForkGui(args, self.root_dir)

    def get_status(self, path):
        hg = Hg(self.path, self.root_dir)
        return self.process_status(hg, path)


class NonInteractiveProcess():
    def __init__(self, args, cwd=None):
        self.args = args
        self.cwd  = cwd

    def run(self):
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        proc = subprocess.Popen(self.args, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            startupinfo=startupinfo, cwd=self.cwd)

        return proc.stdout.read().replace('\r\n', '\n').rstrip(' \n\r')


class SVN():
    def __init__(self, root_dir):
        self.root_dir = root_dir

    def check_status(self, path):
        svn_path = os.path.join(sublime.packages_path(), __name__, 'svn',
            'svn.exe')
        proc = NonInteractiveProcess([svn_path, 'status', path],
            cwd=self.root_dir)
        result = proc.run().split('\n')
        for line in result:
            if len(line) < 1:
                continue

            path_without_root = path.replace(self.root_dir + '\\', '', 1)
            path_regex = re.escape(path_without_root) + '$'
            if self.root_dir != path and re.search(path_regex, line) == None:
                continue

            return line[0]
        return ''


class Git():
    def __init__(self, tortoise_proc_path, root_dir):
        self.git_path = os.path.dirname(tortoise_proc_path) + '\\tgit.exe'
        self.root_dir = root_dir

    def check_status(self, path):
        if os.path.isdir(path):
            proc = NonInteractiveProcess([self.git_path, 'log', '-1', path],
                cwd=self.root_dir)
            result = proc.run().strip().split('\n')
            if result == ['']:
                return '?'
            return ''

        proc = NonInteractiveProcess([self.git_path, 'status', '--short'],
            cwd=self.root_dir)
        result = proc.run().strip().split('\n')
        for line in result:
            if len(line) < 2:
                continue
            path_without_root = path.replace(self.root_dir + '\\', '', 1)
            path_regex = re.escape(path_without_root) + '$'
            if self.root_dir != path and re.search(path_regex, line) == None:
                continue

            if line[0] != ' ':
                res = line[0]
            else:
                res = line[1]
            return res.upper()
        return ''


class Hg():
    def __init__(self, tortoise_proc_path, root_dir):
        self.hg_path = os.path.dirname(tortoise_proc_path) + '\\hg.exe'
        self.root_dir = root_dir

    def check_status(self, path):
        if os.path.isdir(path):
            proc = NonInteractiveProcess([self.hg_path, 'log', '-l', '1',
                '"' + path + '"'], cwd=self.root_dir)
            result = proc.run().strip().split('\n')
            if result == ['']:
                return '?'
            return ''

        proc = NonInteractiveProcess([self.hg_path, 'status', path],
            cwd=self.root_dir)
        result = proc.run().split('\n')
        for line in result:
            if len(line) < 1:
                continue
            return line[0].upper()
        return ''