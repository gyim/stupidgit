#include <QFileInfo>
#include <QProcess>
#include <QDir>
#include <QFileInfo>
#include <QDebug>
#include <stdlib.h>
#include "gitrepository.h"

static QString *_gitBinary = 0;

#define startProcess(args,eventHandler) \
{ \
	QProcess *_p = createProcess(); \
	connect(_p, SIGNAL(finished(int,QProcess::ExitStatus)), this, SLOT(eventHandler(int,QProcess::ExitStatus))); \
	queueProcess(_p, (args)); \
}

#define returnIfProcessFailed(exitCode) \
{ \
	if (exitCode != 0) { \
		emit gitError(exitCode, currentProcess->readAllStandardError()); \
		return; \
	} \
}

GitRepository::GitRepository(QObject *parent) :
	QObject(parent)
{
	currentProcess = 0;
}

QString GitRepository::gitBinary()
{
	if (!_gitBinary) {
		// Search git in PATH
		QString path = getenv("PATH");
#ifdef Q_WS_WIN
		QStringList pathParts = path.split(";");
		pathParts << "C:\\Program Files\\Git\\bin";
		const char *binaryName = "git.exe";
#else
		const char *binaryName = "git";

		QStringList pathParts = path.split(":");
		if (!pathParts.contains("/opt/local/bin"))
			pathParts.append("/opt/local/bin");
		if (!pathParts.contains("/usr/local/git/bin"))
			pathParts.append("/usr/local/git/bin");
#endif

		QChar sep = QDir::separator();
		foreach (QString dir, pathParts) {
			QFileInfo info(dir + sep + binaryName);
			if (info.isFile() && info.isExecutable()) {
				_gitBinary = new QString(info.absoluteFilePath());
			}
		}

		if (!_gitBinary) {
			emit gitError(0,"Cannot find git executable");
		}
	}

	if (_gitBinary)
		return *_gitBinary;
	else
		return "";
}

bool GitRepository::setDirectory(QString& directory)
{
	dir = directory;
	if (!dir.exists())
		return false;

	QDir prevDir = directory;

	// Find the first ancestor that has a .git directory
	do {
		QFileInfo info(dir, ".git");
		if (info.isDir())
			return true;

		prevDir = dir;
		dir = info.dir().path();
	} while (dir != prevDir);

	return false;
}

QDir& GitRepository::getDirectory()
{
	return dir;
}

QProcess *GitRepository::createProcess()
{
	QProcess *process = new QProcess(this);
	process->setWorkingDirectory(dir.path());
	return process;
}

void GitRepository::queueProcess(QProcess *process, QStringList &args)
{
	// It is assumed that this slot is the last which is connected with the finished signal:
	// it will free the process object and start the next process in the queue (if any)
	connect(process, SIGNAL(finished(int,QProcess::ExitStatus)), this, SLOT(processFinished(int,QProcess::ExitStatus)));

	processQueueMutex.lock();

	// Queue new process
	QStringList *argsCopy = new QStringList(args);
	processQueue.append(new GitProcess(process, argsCopy));

	// Start process if currently not running
	if (!currentProcess) {
		currentProcess = process;
		currentProcess->start(gitBinary(), args);
	}
	processQueueMutex.unlock();
}

void GitRepository::processFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
	Q_UNUSED(exitCode);
	Q_UNUSED(exitStatus);

	processQueueMutex.lock();

	// Delete old process
	GitProcess *proc = processQueue.front();
	processQueue.pop_front();
	delete proc->first;
	delete proc->second;
	delete proc;
	currentProcess = 0;

	// Start new process if necessary
	if (processQueue.length()) {
		GitProcess *newProc = processQueue.front();
		currentProcess = newProc->first;
		currentProcess->start(gitBinary(), *(newProc->second));
	}

	processQueueMutex.unlock();
}

void GitRepository::refresh()
{
	startProcess(QStringList() << "diff" << "--name-status", unstagedStatusRefreshed);
}

void GitRepository::unstagedStatusRefreshed(int exitCode, QProcess::ExitStatus /*exitStatus*/)
{
	returnIfProcessFailed(exitCode);

	// Parse output
	QString output = currentProcess->readAllStandardOutput();
	QStringList lines = output.split('\n', QString::SkipEmptyParts);
	foreach (QString line, lines) {
		if (line.length() > 2 && line[1] == '\t') {
			GitFileStatus status = fileStatusByCode(line[0]);
			QString filename = line.right(line.length()-2);
			if (status == GitFileUnmerged) {
				unmergedFiles.append(GitFileInfo(filename, GitFileUnmerged));
			}
			else {
				unstagedChanges.append(GitFileInfo(filename, status));
			}
		}
	}

	// Fetch staged changes
	startProcess(QStringList() << "diff" << "--cached" << "--name-status", stagedStatusRefreshed);
}

void GitRepository::stagedStatusRefreshed(int exitCode, QProcess::ExitStatus /*exitStatus*/)
{
	returnIfProcessFailed(exitCode);

	// Parse output
	QString output = currentProcess->readAllStandardOutput();
	QStringList lines = output.split('\n', QString::SkipEmptyParts);
	foreach (QString line, lines) {
		if (line.length() > 2 && line[1] == '\t') {
			GitFileStatus status = fileStatusByCode(line[0]);
			QString filename = line.right(line.length()-2);
			if (status != GitFileUnmerged) {
				stagedChanges.append(GitFileInfo(filename, status));
			}
		}
	}

	// Fetch untracked changes
	startProcess(QStringList() << "ls-files" << "--others" << "--exclude-standard", untrackedStatusRefreshed);
}

void GitRepository::untrackedStatusRefreshed(int exitCode, QProcess::ExitStatus /*exitStatus*/)
{
	returnIfProcessFailed(exitCode);

	// Parse output
	QString output = currentProcess->readAllStandardOutput();
	QStringList lines = output.split('\n', QString::SkipEmptyParts);
	foreach (QString line, lines) {
		untrackedFiles.append(GitFileInfo(line, GitFileUntracked));
	}

	// Emit "refreshed" signal
	emit refreshed();
}

GitFileStatus GitRepository::fileStatusByCode(QChar statusCode)
{
	switch (statusCode.toLatin1())
	{
	case 'A':
		return GitFileAdded;
	case 'M':
		return GitFileModified;
	case 'D':
		return GitFileDeleted;
	case 'C':
		return GitFileCopied;
	case 'R':
		return GitFileRenamed;
	case 'U':
		return GitFileUnmerged;
	case 'T':
		return GitFileTypeChanged;
	case 'N':
		return GitFileUntracked;
	case 'B':
		return GitFileBroken;
	default:
		return GitFileUnknown;
	}
}
