#ifndef GITREPOSITORY_H
#define GITREPOSITORY_H

#include <QObject>
#include <QDir>
#include <QMap>
#include <QProcess>
#include <QList>
#include <QPair>

typedef enum {
    GitFileAdded,
    GitFileModified,
    GitFileDeleted,
    GitFileCopied,
    GitFileRenamed,
    GitFileUnmerged,
    GitFileTypeChanged,
    GitFileUntracked,
    GitFileBroken,
    GitFileUnknown
} GitFileStatus;

typedef QPair<QString,GitFileStatus> GitFileInfo;
typedef QList<GitFileInfo> GitFileInfoList;

class GitRepository : public QObject
{
Q_OBJECT
private:
    // Repository parameters
    QDir dir;

    // Status information
    GitFileInfoList unstagedChanges;
    GitFileInfoList stagedChanges;
    GitFileInfoList untrackedFiles;
    GitFileInfoList unmergedFiles;

    // Processes
    QProcess *refreshProcess;
    QProcess *createProcess();

    // Utility functions
    GitFileStatus fileStatusByCode(QChar statusCode);

public:
    explicit GitRepository(QObject *parent = 0);
    QString gitBinary();

    // Directory
    bool setDirectory(QString& directory);
    QDir& getDirectory();

    // Running process
    const QString commandOutput(QStringList& arguments);

    // Repository information
    GitFileInfoList& getUnstagedChanges() { return unstagedChanges; }
    GitFileInfoList& getStagedChanges() { return stagedChanges; }
    GitFileInfoList& getUntrackedFiles() { return untrackedFiles; }
    GitFileInfoList& getUnmergedFiles() { return unmergedFiles; }

signals:
    void refreshed(void);
    void gitError(int exitCode, QString errorMessage);

public slots:
    void refresh(void);

private slots:
    void unstagedStatusRefreshed(int exitCode, QProcess::ExitStatus exitStatus);
    void stagedStatusRefreshed(int exitCode, QProcess::ExitStatus exitStatus);
    void untrackedStatusRefreshed(int exitCode, QProcess::ExitStatus exitStatus);
};

#endif // GITREPOSITORY_H
