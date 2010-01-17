#include <QFileInfo>
#include <QProcess>
#include <QDir>
#include <QFileInfo>
#include <QDebug>
#include <stdlib.h>
#include "gitrepository.h"

static QString *_gitBinary = 0;

GitRepository::GitRepository(QObject *parent) :
	QObject(parent)
{
	refreshProcess = 0;
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

const QString GitRepository::commandOutput(QStringList& arguments)
{
	QProcess *process = createProcess();
	process->start(gitBinary(), arguments);
	process->closeWriteChannel();

	if (!process->waitForFinished()) {
		delete process;
		return "";
	}

	QString result = process->readAllStandardOutput();
	delete process;
	return result;
}

void GitRepository::refresh()
{
	if (refreshProcess)
		return;

	refreshProcess = createProcess();
	connect(refreshProcess, SIGNAL(finished(int,QProcess::ExitStatus)),
			this, SLOT(unstagedStatusRefreshed(int,QProcess::ExitStatus)));
	refreshProcess->start(gitBinary(), QStringList() << "diff" << "--name-status");
}

void GitRepository::unstagedStatusRefreshed(int exitCode, QProcess::ExitStatus /*exitStatus*/)
{
	// Check error
	if (exitCode != 0) {
		emit gitError(exitCode, refreshProcess->readAllStandardError());
		delete refreshProcess;
		refreshProcess = 0;
		return;
	}

	// Parse output
	QString output = refreshProcess->readAllStandardOutput();
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

	delete refreshProcess;
	refreshProcess = 0;

	// Fetch staged changes
	refreshProcess = createProcess();
	connect(refreshProcess, SIGNAL(finished(int,QProcess::ExitStatus)),
			this, SLOT(stagedStatusRefreshed(int,QProcess::ExitStatus)));
	refreshProcess->start(gitBinary(), QStringList() << "diff" << "--cached" << "--name-status");
}

void GitRepository::stagedStatusRefreshed(int exitCode, QProcess::ExitStatus /*exitStatus*/)
{
	// Check error
	if (exitCode != 0) {
		emit gitError(exitCode, refreshProcess->readAllStandardError());
		delete refreshProcess;
		refreshProcess = 0;
		return;
	}

	// Parse output
	QString output = refreshProcess->readAllStandardOutput();
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

	delete refreshProcess;
	refreshProcess = 0;

	// Fetch untracked changes
	refreshProcess = createProcess();
	connect(refreshProcess, SIGNAL(finished(int,QProcess::ExitStatus)),
			this, SLOT(untrackedStatusRefreshed(int,QProcess::ExitStatus)));
	refreshProcess->start(gitBinary(), QStringList() << "ls-files" << "--others" << "--exclude-standard");
}

void GitRepository::untrackedStatusRefreshed(int exitCode, QProcess::ExitStatus /*exitStatus*/)
{
	// Check error
	if (exitCode != 0) {
		emit gitError(exitCode, refreshProcess->readAllStandardError());
		delete refreshProcess;
		refreshProcess = 0;
		return;
	}

	// Parse output
	QString output = refreshProcess->readAllStandardOutput();
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
