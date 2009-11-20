import os
import os.path
import sys
import subprocess
import re
import tempfile
from util import *

FILE_ADDED       = 'A'
FILE_MODIFIED    = 'M'
FILE_DELETED     = 'D'
FILE_COPIED      = 'C'
FILE_RENAMED     = 'R'
FILE_UNMERGED    = 'U'
FILE_TYPECHANGED = 'T'
FILE_UNTRACKED   = 'N'
FILE_BROKEN      = 'B'
FILE_UNKNOWN     = 'X'

MERGE_TOOLS = {
    'diffmerge.app': (
        ['/Applications/DiffMerge.app/Contents/MacOS/DiffMerge'],
        ['--nosplash', '-t1={FILENAME}.LOCAL', '-t2={FILENAME}.MERGED', '-t3={FILENAME}.REMOTE', '{LOCAL}', '{MERGED}', '{REMOTE}']
    ),
    'diffmerge.cmdline': (
        ['{PATH}/diffmerge', '{PATH}/diffmerge.sh'],
        ['--nosplash', '-t1=LOCAL', '-t2=MERGED', '-t3=REMOTE', '{LOCAL}', '{MERGED}', '{REMOTE}']
    ),
    'meld': (
        ['{PATH}/meld'],
        ['{LOCAL}', '{MERGED}', '{REMOTE}']
    ),
    'winmerge.win32': (
        [r'C:\Program Files\WinMerge\WinMergeU.exe'],
        ['{MERGED}'] # It does not support 3-way merge yet...
    ),
    'winmerge.cygwin': (
        ['/c/Program Files/WinMerge/WinMergeU.exe'],
        ['{MERGED}'] # It does not support 3-way merge yet...
    )
}

_git = None
commit_pool = {}

class GitError(RuntimeError): pass

def git_binary():
    global _git

    if _git:
        return _git

    # Search for git binary
    if os.name == 'posix':
        locations = ['{PATH}/git', '/opt/local/bin/git', '/usr/local/git/bin']
    elif sys.platform == 'win32':
        locations = (r'{PATH}\git.exe', r'C:\Program Files\Git\bin\git.exe')
    elif sys.platform == 'cygwin':
        locations = (r'{PATH}/git.exe', r'/c/Program Files/Git/bin/git.exe')
    else:
        locations = []

    for _git in find_binary(locations):
        return _git

    _git = None
    raise GitError, "git executable not found"

_mergetool = None
def detect_mergetool():
    global _mergetool

    if _mergetool:
        return _mergetool

    # Select tools
    if sys.platform == 'darwin':
        # Mac OS X
        tools = ['diffmerge.app', 'diffmerge.cmdline', 'meld']
    elif os.name == 'posix':
        # Other Unix
        tools = ['diffmerge.cmdline', 'meld']
    elif sys.platform == 'win32':
        # Windows
        tools = ['winmerge.win32']
    elif sys.platform == 'cygwin':
        # Cygwin
        tools = ['winmerge.cygwin']
    else:
        raise GitError, "Cannot detect any merge tool"

    # Detect binaries
    for tool in tools:
        locations, args = MERGE_TOOLS[tool]
        for location in find_binary(locations):
            _mergetool = (location, args)
            return _mergetool

    # Return error if no tool was found
    raise GitError, "Cannot detect any merge tool"

def run_cmd(dir, args, with_retcode=False, with_stderr=False, raise_error=False, input=None, env={}):
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

    git_env = dict(os.environ)
    git_env.update(env)

    p = Popen([git_binary()] + args, stdout=subprocess.PIPE,
              stderr=subprocess.PIPE, stdin=subprocess.PIPE,
              env=git_env, shell=False)

    if input == None:
        stdout,stderr = p.communicate('')
    else:
        stdout,stderr = p.communicate(utf8_str(input))
    
    # Return command output in a form given by arguments
    ret = []

    if p.returncode != 0 and raise_error:
        raise GitError, 'git returned with the following error:\n%s' % stderr

    if with_retcode:
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
                if new_repodir == repodir:
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

        # Load refs
        self.load_refs()

        # Get submodule info
        self.submodules = self.get_submodules()
        self.all_modules = [self] + self.submodules

    def load_refs(self):
        self.refs = {}
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

        # Main module references
        if self.parent:
            self.main_ref = self.parent.get_submodule_version(self.name, 'HEAD')
            if os.path.exists(os.path.join(self.parent.dir, '.git', 'MERGE_HEAD')):
                self.main_merge_ref = self.parent.get_submodule_version(self.name, 'MERGE_HEAD')
            else:
                self.main_merge_ref = None
        else:
            self.main_ref = None
            self.main_merge_ref = None

        # References
        for line in self.run_cmd(['show-ref']).split('\n'):
            commit_id, _, refname = line.partition(' ')
            self.refs[refname] = commit_id

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

        # Inverse reference hashes
        self.refs_by_sha1 = invert_hash(self.refs)
        self.branches_by_sha1 = invert_hash(self.branches)
        self.remote_branches_by_sha1 = invert_hash(self.remote_branches)
        self.tags_by_sha1 = invert_hash(self.tags)

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

    def get_submodule_version(self, submodule_name, main_version):
        dir = os.path.dirname(submodule_name)
        name = os.path.basename(submodule_name)
        output = self.run_cmd(['ls-tree', '-z', '%s:%s' % (main_version, dir)])
        for line in output.split('\x00'):
            if not line.strip(): continue

            meta, filename = line.split('\t')
            if filename == name:
                mode, filetype, sha1 = meta.split(' ')
                if filetype == 'commit':
                    return sha1

        return None

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

    def commit(self, author_name, author_email, msg, amend=False):
        if amend:
            # Get details of current HEAD
            is_merge_resolve = False

            output = self.run_cmd(['log', '-1', '--pretty=format:%P%n%an%n%ae%n%aD'])
            if not output.strip():
                raise GitError, "Cannot amend in an empty repository!"

            parents, author_name, author_email, author_date = output.split('\n')
            parents = parents.split(' ')
        else:
            author_date = None # Use current date

            # Get HEAD sha1 id
            head = self.run_cmd(['rev-parse', 'HEAD']).strip()
            parents = [head]

            # Get merge head if exists
            is_merge_resolve = False
            try:
                merge_head_filename = os.path.join(self.dir, '.git', 'MERGE_HEAD')
                if os.path.isfile(merge_head_filename):
                    f = open(merge_head_filename)
                    p = f.read().strip()
                    f.close()
                    parents.append(p)
                    is_merge_resolve = True
            except OSError:
                raise GitError, "Cannot open MERGE_HEAD file"

        # Write tree
        tree = self.run_cmd(['write-tree'], raise_error=True).strip()

        # Write commit
        parent_args = []
        for parent in parents:
            parent_args += ['-p', parent]

        env = {}
        if author_name: env['GIT_AUTHOR_NAME'] = author_name
        if author_email: env['GIT_AUTHOR_EMAIL'] = author_email
        if author_date: env['GIT_AUTHOR_DATE'] = author_date

        commit = self.run_cmd(
            ['commit-tree', tree] + parent_args,
            raise_error=True,
            input=msg,
            env=env
        ).strip()

        # Update reference
        self.run_cmd(['update-ref', 'HEAD', commit], raise_error=True)

        # Remove MERGE_HEAD
        if is_merge_resolve:
            try:
                os.unlink(os.path.join(self.dir, '.git', 'MERGE_HEAD'))
                os.unlink(os.path.join(self.dir, '.git', 'MERGE_MODE'))
                os.unlink(os.path.join(self.dir, '.git', 'MERGE_MSG'))
                os.unlink(os.path.join(self.dir, '.git', 'ORIG_HEAD'))
            except OSError:
                pass

    def get_status(self):
        unstaged_changes = {}
        staged_changes = {}

        # Unstaged changes
        changes = self.run_cmd(['diff', '--name-status', '-z']).split('\x00')
        for i in xrange(len(changes)/2):
            status, filename = changes[2*i], changes[2*i+1]
            if filename not in unstaged_changes or status == FILE_UNMERGED:
                unstaged_changes[filename] = status

        # Untracked files
        for filename in self.run_cmd(['ls-files', '--others', '--exclude-standard', '-z']).split('\x00'):
            if filename and filename not in unstaged_changes:
                unstaged_changes[filename] = FILE_UNTRACKED

        # Staged changes
        changes = self.run_cmd(['diff', '--cached', '--name-status', '-z']).split('\x00')
        for i in xrange(len(changes)/2):
            status, filename = changes[2*i], changes[2*i+1]
            if status != FILE_UNMERGED or filename not in unstaged_changes:
                staged_changes[filename] = status

        return unstaged_changes, staged_changes

    def get_unified_status(self):
        unified_changes = {}

        # Staged & unstaged changes
        changes = self.run_cmd(['diff', 'HEAD', '--name-status', '-z']).split('\x00')
        for i in xrange(len(changes)/2):
            status, filename = changes[2*i], changes[2*i+1]
            if filename not in unified_changes or status == FILE_UNMERGED:
                unified_changes[filename] = status

        # Untracked files
        for filename in self.run_cmd(['ls-files', '--others', '--exclude-standard', '-z']).split('\x00'):
            if filename and filename not in unified_changes:
                unified_changes[filename] = FILE_UNTRACKED

        return unified_changes

    def merge_file(self, filename):
        # Store file versions in temporary files
        _, local_file = tempfile.mkstemp(os.path.basename(filename) + '.LOCAL')
        f = open(local_file, 'w')
        f.write(self.run_cmd(['show', ':2:%s' % filename], raise_error=True))
        f.close()

        _, remote_file = tempfile.mkstemp(os.path.basename(filename) + '.REMOTE')
        f = open(remote_file, 'w')
        f.write(self.run_cmd(['show', ':3:%s' % filename], raise_error=True))
        f.close()

        # Run mergetool
        mergetool, args = detect_mergetool()
        args = list(args)

        for i in xrange(len(args)):
            args[i] = args[i].replace('{FILENAME}', os.path.basename(filename))
            args[i] = args[i].replace('{LOCAL}', local_file)
            args[i] = args[i].replace('{REMOTE}', remote_file)
            args[i] = args[i].replace('{MERGED}', os.path.join(self.dir, filename))

        s = Popen([mergetool] + args, shell=False)

    def get_lost_commits(self, refname, moving_to=None):
        # Note: refname must be a full reference name (e.g. refs/heads/master)
        # or HEAD (if head is detached).
        # moving_to must be a SHA1 commit identifier
        if refname == 'HEAD':
            commit_id = self.head
        else:
            commit_id = self.refs[refname]
        commit = commit_pool[commit_id]

        # If commit is not moving, it won't be lost :)
        if commit_id == moving_to:
            return []

        # If a commit has another reference, it won't be lost :)
        head_refnum = len(self.refs_by_sha1.get(commit_id, []))
        if (refname == 'HEAD' and head_refnum > 0) or head_refnum > 1:
            return []

        # If commit has descendants, it won't be lost: at least one of its
        # descendants has another reference
        if commit.children:
            return []

        # If commit has parents, traverse the commit graph into this direction.
        # Mark every commit as lost commit until:
        #   (1) the end of the graph is found
        #   (2) a reference is found
        #   (3) the moving_to destination is found
        #   (4) a commit is found that has more than one children.
        #       (it must have a descendant that has a reference)
        lost_commits = []
        search_pos = [commit]

        while search_pos:
            next_search_pos = []

            for c in search_pos:
                for p in c.parents:
                    if p.sha1 not in self.refs_by_sha1 and p.sha1 != moving_to \
                        and len(p.children) == 1:
                        next_search_pos.append(p)

            lost_commits += search_pos
            search_pos = next_search_pos

        return lost_commits

    def update_head(self, content):
        try:
            f = open(os.path.join(self.dir, '.git', 'HEAD'), 'w')
            f.write(content)
            f.close()
        except OSError:
            raise GitError, "Write error:\nCannot write into .git/HEAD"

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

# Utility functions
def diff_for_untracked_file(filename):
    # Start "diff" text
    diff_text = 'New file: %s\n' % filename

    # Detect whether file is binary
    if is_binary_file(filename):
        diff_text += "@@ File is binary.\n\n"
    else:
        # Text file => show lines
        newfile_text = ''
        try:
            f = open(filename, 'r')
            lines = f.readlines()
            f.close()

            newfile_text += '@@ -1,0 +1,%d @@\n' % len(lines)

            for line in lines:
                newfile_text += '+ ' + line

            diff_text += newfile_text
        except OSError:
            diff_text += '@@ Error: Cannot open file\n\n'

    return diff_text

