import os
import os.path
import sys
import subprocess
import re

_git = None
commit_pool = {}

class GitError(RuntimeError): pass

def git_binary():
    global _git

    if _git:
        return _git

    # Search for git binary
    binary_name = 'git.exe' if sys.platform in ['win32','cygwin'] else 'git'
    searchpath_sep = ';' if sys.platform == 'win32' else ':'
    searchpaths = os.environ['PATH'].split(searchpath_sep)

    if os.name == 'posix':
        searchpaths.append('/opt/local/bin') # MacPorts
    elif sys.platform == 'win32':
        searchpaths.append(r'C:\Program Files\Git\bin')
    elif sys.platform == 'cygwin':
        searchpaths.append('/c/Program Files/Git/bin')

    for dir in searchpaths:
        _git = os.path.join(dir, binary_name)
        if os.path.isfile(_git) and os.access(_git, os.X_OK):
            return _git

    _git = None
    raise GitError, "git executable not found"

def run_cmd(dir, args, with_retcode=False, with_stderr=False, raise_error=False):
    # Check args
    if type(args) in [str, unicode]:
        args = [args]

    # Check directory
    if not os.path.isdir(dir):
        raise GitError, 'Directory not exists: ' + dir

    try:
        os.chdir(dir)
    except OSError, msg:
        raise GitError, msg

    # Run command
    if type(args) != list:
        args = [args]

    p = subprocess.Popen([git_binary()] + args, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout,stderr = p.communicate()
    
    # Return command output in a form given by arguments
    ret = []

    if with_retcode:
        if p.returncode != 0 and raise_error:
            raise GitError, 'git returned with the following error:\n%s' % stderr

        ret.append(p.returncode)

    ret.append(stdout)

    if with_stderr:
        ret.append(stderr)

    if len(ret) == 1:
        return ret[0]
    else:
        return tuple(ret)

class Repository(object):
    def __init__(self, repodir, name='Main module', parent=None):
        self.name = name
        self.parent = parent

        # Search for .git directory in repodir ancestors
        repodir = os.path.abspath(repodir)
        try:
            while not os.path.isdir(os.path.join(repodir, '.git')):
                new_repodir = os.path.abspath(os.path.join(repodir, '..'))
                if os.path.samefile(new_repodir, repodir):
                    raise GitError, "Directory is not a git repository"
                else:
                    repodir = new_repodir
        except OSError:
            raise GitError, "Directory is not a git repository or it is not readable"
            
        self.dir = repodir

        # Origin URL
        self.config = ConfigFile(os.path.join(self.dir, '.git', 'config'))
        self.url = None
        self.url = self.config.get_option('remote', 'origin', 'url')

        # Run a git status to see whether this is really a git repository
        retcode,output = self.run_cmd(['status'], with_retcode=True)
        if retcode not in [0,1]:
            raise GitError, "Directory is not a git repository"

        # Get submodule info
        self.submodules = self.get_submodules()
        self.all_modules = [self] + self.submodules

        self.load_refs()

    def load_refs(self):
        self.branches = {}
        self.remote_branches = {}
        self.tags = {}

        # HEAD, current branch
        self.head = self.run_cmd(['rev-parse', 'HEAD']).strip()
        self.current_branch = None
        try:
            f = open(os.path.join(self.dir, '.git', 'HEAD'))
            head = f.read().strip()
            f.close()

            if head.startswith('ref: refs/heads/'):
                self.current_branch = head[16:]
        except OSError:
            pass

        # References
        for line in self.run_cmd(['show-ref']).split('\n'):
            commit_id, _, refname = line.partition(' ')
            if refname.startswith('refs/heads/'):
                branchname = refname[11:]
                self.branches[branchname] = commit_id
            elif refname.startswith('refs/remotes/'):
                branchname = refname[13:]
                self.remote_branches[branchname] = commit_id
            elif refname.startswith('refs/tags/'):
                # Load the referenced commit for tags
                tagname = refname[10:]
                try:
                    self.tags[tagname] = self.run_cmd(['rev-parse', '%s^{commit}' % refname], raise_error=True).strip()
                except GitError:
                    pass

    def run_cmd(self, args, **opts):
        return run_cmd(self.dir, args, **opts)

    def get_submodules(self):
        # Check existence of .gitmodules
        gitmodules_path = os.path.join(self.dir, '.gitmodules')
        if not os.path.isfile(gitmodules_path):
            return []

        # Parse .gitmodules file
        repos = []
        submodule_config = ConfigFile(gitmodules_path)
        for name,opts in submodule_config.sections_for_type('submodule'):
            if 'path' in opts:
                repo_path = os.path.join(self.dir, opts['path'])
                repos.append(Repository(repo_path, name=opts['path'], parent=self))

        return repos

    def get_log(self, args=[]):
        log = self.run_cmd(['log', '-z', '--pretty=format:%H%n%h%n%P%n%T%n%an%n%ae%n%aD%n%s%n%b']+args)

        commit_texts = log.split('\x00')
        commit_texts.reverse()

        commits = []
        for text in commit_texts:
            c = Commit(self)
            c.parse_gitlog_output(text)
            commit_pool[c.sha1] = c
            commits.append(c)

        commits.reverse()
        return commits

class Commit(object):
    def __init__(self, repo):
        self.repo = repo

        self.sha1 = None
        self.abbrev = None

        self.parents = None
        self.children = None
        self.tree = None

        self.author_name = None
        self.author_email = None
        self.author_date = None

        self.short_msg = None
        self.full_msg = None

        self.remote_branches = None
        self.branches = None
        self.tags = None

    def parse_gitlog_output(self, text):
        lines = text.split('\n')

        (self.sha1, self.abbrev, parents, self.tree,
         self.author_name, self.author_email, self.author_date,
         self.short_msg) = lines[0:8]

        if parents:
            parent_ids = parents.split(' ')
            self.parents = [commit_pool[p] for p in parent_ids]
            for parent in self.parents:
                parent.children.append(self)
        else:
            self.parents = []

        self.children = []

        self.full_msg = '\n'.join(lines[8:])


class ConfigFile(object):
    def __init__(self, filename):
        self.sections = []

        # Patterns
        p_rootsect = re.compile(r'\[([^\]\s]+)\]')
        p_sect     = re.compile(r'\[([^\]"\s]+)\s+"([^"]+)"\]')
        p_option   = re.compile(r'(\w+)\s*=\s*(.*)')

        # Parse file
        section = None
        section_type = None
        options = {}

        f = open(filename)
        for line in f:
            line = line.strip()

            if len(line) == 0 or line.startswith('#'):
                continue

            # Parse sections
            m_rootsect = p_rootsect.match(line)
            m_sect     = p_sect.match(line)

            if (m_rootsect or m_sect) and section:
                self.sections.append( (section_type, section, options) )
            if m_rootsect:
                section_type = None
                section = m_rootsect.group(1)
                options = {}
            elif m_sect:
                section_type = m_sect.group(1)
                section = m_sect.group(2)
                options = {}
                
            # Parse options
            m_option = p_option.match(line)
            if section and m_option:
                options[m_option.group(1)] = m_option.group(2)

        if section:
            self.sections.append( (section_type, section, options) )
        f.close()

    def has_section(self, sect_type, sect_name):
        m = [ s for s in self.sections if s[0]==sect_type and s[1] == sect_name ]
        return len(m) > 0

    def sections_for_type(self, sect_type):
        return [ (s[1],s[2]) for s in self.sections if s[0]==sect_type ]

    def options_for_section(self, sect_type, sect_name):
        m = [ s[2] for s in self.sections if s[0]==sect_type and s[1] == sect_name ]
        if m:
            return m[0]
        else:
            return None

    def get_option(self, sect_type, sect_name, option):
        opts = self.options_for_section(sect_type, sect_name)
        if opts:
            return opts.get(option)
        else:
            return None


