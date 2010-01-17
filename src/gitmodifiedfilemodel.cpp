#include <QDebug>
#include <QIcon>
#include "gitmodifiedfilemodel.h"

GitModifiedFileModel::GitModifiedFileModel(GitRepository *repo, QObject *parent)
	: QAbstractItemModel(parent)
{
	setRepository(repo);
}

GitModifiedFileModel::~GitModifiedFileModel()
{
}

void GitModifiedFileModel::setRepository(GitRepository *_repo)
{
	repo = _repo;

	folderTypes.clear();
	folders.clear();

	// Staged changes
	if (repo->getStagedChanges().count()) {
		folderTypes.append(GitModificationStaged);
		folders.append(repo->getStagedChanges());
	}

	// Unstaged changes
	if (repo->getUnstagedChanges().count()) {
		folderTypes.append(GitModificationUnstaged);
		folders.append(repo->getUnstagedChanges());
	}

	// Unmerged files
	if (repo->getUnmergedFiles().count()) {
		folderTypes.append(GitModificationUnmerged);
		folders.append(repo->getUnmergedFiles());
	}

	// Untracked files
	if (repo->getUntrackedFiles().count()) {
		folderTypes.append(GitModificationUntracked);
		folders.append(repo->getUntrackedFiles());
	}
}

GitModificationType GitModifiedFileModel::getModificationType(QModelIndex &index)
{
	if (index.isValid() && index.parent().isValid()) {
		return folderTypes[index.internalId()];
	}
	else {
		return GitModificationNone;
	}
}

QString GitModifiedFileModel::getFileName(QModelIndex &index)
{
	if (index.isValid() && index.parent().isValid()) {
		return folders[index.internalId()].at(index.row()).first;
	}
	else
		return "";
}

QVariant GitModifiedFileModel::data(const QModelIndex &index, int role) const
{
	if (!index.isValid())
		return QVariant();

	if (role == Qt::DisplayRole) {
		if (!index.parent().isValid()) {
			switch (folderTypes.at(index.row())) {
			case GitModificationStaged:
				return "Selected to commit";
			case GitModificationUnstaged:
				return "Not to commit";
			case GitModificationUnmerged:
				return "Unmerged files";
			case GitModificationUntracked:
				return "Untracked files";
			default:
				return "Unknown";
			}
		}
		else {
			return QVariant(folders.at(index.internalId()).at(index.row()).first);
		}
	}
	else if (role == Qt::DecorationRole) {
		if (!index.parent().isValid()) {
			return QIcon::QIcon(":/icons/folder.png");
		}
		return QIcon(":/icons/text-plain.png");
	}
	return QVariant();
}

Qt::ItemFlags GitModifiedFileModel::flags(const QModelIndex &index) const
{
	if (!index.isValid())
		return 0;

	return Qt::ItemIsSelectable | Qt::ItemIsEnabled;
}

QVariant GitModifiedFileModel::headerData(int section, Qt::Orientation orientation, int role) const
{
	Q_UNUSED(section);
	Q_UNUSED(orientation);
	Q_UNUSED(role);

	return QVariant();
}

QModelIndex GitModifiedFileModel::index(int row, int column, const QModelIndex &parent) const
{
	if (!parent.isValid()) {
		return createIndex(row, column, -1);
	}
	else {
		return createIndex(row, column, parent.row());
	}
}

QModelIndex GitModifiedFileModel::parent(const QModelIndex &index) const
{
	int parentRow = index.internalId();
	if (parentRow < 0) {
		// Root item
		return QModelIndex();
	}
	else {
		return createIndex(parentRow, 0, -1);
	}
}

int GitModifiedFileModel::rowCount(const QModelIndex &parent) const
{
	if (!parent.isValid()) {
		// Root
		return folders.count();
	}
	else if (parent.internalId() == -1) {
		// Folders
		return folders.at(parent.row()).count();
	}
	else {
		// Files
		return 0;
	}
}

int GitModifiedFileModel::columnCount(const QModelIndex &parent) const
{
	Q_UNUSED(parent);
	return 1;
}
