#include <QFileInfo>
#include <QProcess>
#include "gitrepository.h"

#define _gitBinary "/opt/local/bin/git"

GitRepository::GitRepository(QObject *parent) :
    QObject(parent)
{
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

const QString GitRepository::commandOutput(QStringList& arguments)
{
    QProcess process;
    process.setWorkingDirectory(dir.path());
    process.start(_gitBinary, arguments);
    process.closeWriteChannel();

    if (!process.waitForFinished()) {
        return "";
    }
    return process.readAll();
}
