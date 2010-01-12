#ifndef GITREPOSITORY_H
#define GITREPOSITORY_H

#include <QObject>
#include <QDir>

class GitRepository : public QObject
{
Q_OBJECT
private:
    QDir dir;

public:
    explicit GitRepository(QObject *parent = 0);

    // Directory
    bool setDirectory(QString& directory);
    QDir& getDirectory();

    // Running process
    const QString commandOutput(QStringList& arguments);

signals:

public slots:

};

#endif // GITREPOSITORY_H
