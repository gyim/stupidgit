#ifndef GITMODIFIEDFILEMODEL_H
#define GITMODIFIEDFILEMODEL_H

#include <QAbstractItemModel>
#include <QList>
#include <QPair>
#include "gitrepository.h"

class GitModifiedFileModel : public QAbstractItemModel
{
	Q_OBJECT

private:
	GitRepository *repo;
	QList<GitModificationType> folderTypes;
	QList<GitFileInfoList> folders;

public:
	GitModifiedFileModel();

	GitModifiedFileModel(GitRepository *repo, QObject *parent = 0);
	~GitModifiedFileModel();

	// Getting/setting data
	void setRepository(GitRepository *repo);
	GitModificationType getModificationType(QModelIndex &index);
	QString getFileName(QModelIndex &index);

	// QAbstractItemModel implementation
	QVariant data(const QModelIndex &index, int role) const;
	Qt::ItemFlags flags(const QModelIndex &index) const;
	QVariant headerData(int section, Qt::Orientation orientation,
						int role = Qt::DisplayRole) const;
	QModelIndex index(int row, int column,
					  const QModelIndex &parent = QModelIndex()) const;
	QModelIndex parent(const QModelIndex &index) const;
	int rowCount(const QModelIndex &parent = QModelIndex()) const;
	int columnCount(const QModelIndex &parent = QModelIndex()) const;
};

#endif // GITMODIFIEDFILEMODEL_H
