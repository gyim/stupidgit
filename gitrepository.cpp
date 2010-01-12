#include <QFileInfo>
#include <QProcess>
#include <QDebug>
#include "gitrepository.h"

#define _gitBinary "/opt/local/bin/git"

GitRepository::GitRepository(QObject *parent) :
    QObject(parent)
{
    refreshProcess = 0;
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
    process->start(_gitBinary, arguments);
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
    refreshProcess->start(_gitBinary, QStringList() << "diff" << "--name-status");
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
            QChar status = line[0];
            QString filename = line.right(line.length()-2);
            unstagedChanges[filename] = fileStatusByCode(status);
        }
    }

    delete refreshProcess;
    refreshProcess = 0;

    // Fetch staged changes
    refreshProcess = createProcess();
    connect(refreshProcess, SIGNAL(finished(int,QProcess::ExitStatus)),
            this, SLOT(stagedStatusRefreshed(int,QProcess::ExitStatus)));
    refreshProcess->start(_gitBinary, QStringList() << "diff" << "--cached" << "--name-status");
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
            QChar status = line[0];
            QString filename = line.right(line.length()-2);
            if (!(status.toLatin1() == 'U' && unstagedChanges.contains(filename))) {
                stagedChanges[filename] = fileStatusByCode(status);
            }
        }
    }

    delete refreshProcess;
    refreshProcess = 0;

    // Fetch untracked changes
    refreshProcess = createProcess();
    connect(refreshProcess, SIGNAL(finished(int,QProcess::ExitStatus)),
            this, SLOT(untrackedStatusRefreshed(int,QProcess::ExitStatus)));
    refreshProcess->start(_gitBinary, QStringList() << "ls-files" << "--others" << "--exclude-standard");
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
        unstagedChanges[line] = GitFileUntracked;
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
