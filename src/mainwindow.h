#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include "gitrepository.h"
#include "gitmodifiedfilemodel.h"

namespace Ui {
	class MainWindow;
}

class MainWindow : public QMainWindow {
	Q_OBJECT
public:
	MainWindow(QWidget *parent = 0);
	~MainWindow();

protected:
	void changeEvent(QEvent *e);

private:
	Ui::MainWindow *ui;
	GitRepository *repo;
	GitModifiedFileModel *modifiedFileModel;

private slots:
	void onRepoRefreshed();
	void onGitError(int returnCode, QString errorMsg);

	void on_actionOpen_Repository_triggered();
	void on_actionQuit_triggered();
};

#endif // MAINWINDOW_H
