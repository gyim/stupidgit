#ifndef GITREPOSITORY_H
#define GITREPOSITORY_H

#include <QObject>
#include <QDir>
#include <QMap>
#include <QProcess>
#include <QList>
#include <QPair>
#include <QVariant>
#include <QMutex>

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

typedef enum {
	GitModificationNone,
	GitModificationStaged,
	GitModificationUnstaged,
	GitModificationUnmerged,
	GitModificationUntracked
} GitModificationType;

typedef QPair<QString,GitFileStatus> GitFileInfo;
typedef QList<GitFileInfo> GitFileInfoList;
typedef QPair<QProcess *, QStringList *> GitProcess;

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
	QList<GitProcess *>processQueue;
	QMutex processQueueMutex;
	QProcess *currentProcess;

	QProcess *createProcess();
	void queueProcess(QProcess *process, QStringList &args);

	bool refreshing;

	// Utility functions
	GitFileStatus fileStatusByCode(QChar statusCode);

public:
	explicit GitRepository(QObject *parent = 0);
	QString gitBinary();

	// Directory
	bool setDirectory(QString& directory);
	QDir& getDirectory();

	// Repository information
	GitFileInfoList& getUnstagedChanges() { return unstagedChanges; }
	GitFileInfoList& getStagedChanges() { return stagedChanges; }
	GitFileInfoList& getUntrackedFiles() { return untrackedFiles; }
	GitFileInfoList& getUnmergedFiles() { return unmergedFiles; }

signals:
	void refreshed(void);
	void gitError(int exitCode, QString errorMessage);
	void gotFileDiff(QString diff);

public slots:
	void refresh(void);
	void getFileDiff(GitModificationType modificationType, QString& filename);

private slots:
	void processFinished(int exitCode, QProcess::ExitStatus exitStatus);
	void unstagedStatusRefreshed(int exitCode, QProcess::ExitStatus exitStatus);
	void stagedStatusRefreshed(int exitCode, QProcess::ExitStatus exitStatus);
	void untrackedStatusRefreshed(int exitCode, QProcess::ExitStatus exitStatus);
	void gotFileDiff(int exitCode, QProcess::ExitStatus exitStatus);
};

#endif // GITREPOSITORY_H
