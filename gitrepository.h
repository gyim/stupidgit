#ifndef GITREPOSITORY_H
#define GITREPOSITORY_H

#include <QObject>
#include <QDir>
#include <QMap>
#include <QProcess>

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

class GitRepository : public QObject
{
Q_OBJECT
private:
    // Repository parameters
    QDir dir;

    // Status information
    QMap<QString, GitFileStatus> unstagedChanges;
    QMap<QString, GitFileStatus> stagedChanges;

    // Processes
    QProcess *refreshProcess;
    QProcess *createProcess();

    // Utility functions
    GitFileStatus fileStatusByCode(QChar statusCode);

public:
    explicit GitRepository(QObject *parent = 0);

    // Directory
    bool setDirectory(QString& directory);
    QDir& getDirectory();

    // Running process
    const QString commandOutput(QStringList& arguments);

    // Repository information
    QMap<QString,GitFileStatus>& getUnstagedChanges() { return unstagedChanges; }
    QMap<QString,GitFileStatus>& getStagedChanges() { return stagedChanges; }

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
