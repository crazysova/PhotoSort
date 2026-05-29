#!/usr/bin/env python3
# Изменения:
# 1. Убрана панель инструментов (QToolBar).
# 2. Добавлены иконки к пунктам меню "Файл" и "Справка".

import sys
import os
import platform
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QFileDialog, QMenuBar, QMessageBox, QAction)
from PyQt5.QtGui import (QPixmap, QIcon)
from PyQt5.QtCore import Qt, QMimeData
import shutil
import random
import send2trash

class DraggableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap():
            print(f"Начало перетаскивания: {self.image_path}")
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.image_path)
            drag.setMimeData(mime_data)
            thumbnail = self.pixmap().scaled(100, 100, Qt.KeepAspectRatio)
            drag.setPixmap(thumbnail)
            drag.setHotSpot(thumbnail.rect().center())
            drag.exec_(Qt.MoveAction)

class FolderFrame(QFrame):
    def __init__(self, folder_name, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            print(f"Drag enter: {self.folder_name}")
            event.acceptProposedAction()

    def dropEvent(self, event):
        source_path = event.mimeData().text()
        print(f"Drop event: {source_path} -> {self.folder_name}")
        destination_path = os.path.join(self.parent().parent_dir, self.folder_name, os.path.basename(source_path))
        try:
            shutil.move(source_path, destination_path)
            print(f"Фото перемещено в {self.folder_name}")
            window = self.window()
            window.image_list.remove(source_path)
            if window.current_index >= len(window.image_list):
                window.current_index = len(window.image_list) - 1
            if window.image_list:
                window.update_image()
            else:
                window.close()
        except Exception as e:
            print(f"Ошибка при перемещении: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            folder_path = os.path.normpath(os.path.join(self.window().parent_dir, self.folder_name))
            print(f"Попытка открыть папку: {folder_path}")
            try:
                if platform.system() == "Windows":
                    os.startfile(folder_path)
                    print(f"Папка {folder_path} успешно открыта через os.startfile")
                else:
                    result = subprocess.run(['xdg-open', folder_path], capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"Папка {folder_path} успешно открыта через xdg-open")
                    else:
                        print(f"Ошибка запуска xdg-open: {result.stderr}")
            except Exception as e:
                print(f"Не удалось открыть папку {folder_path}: {e}")

class PhotoSorter(QMainWindow):
    def __init__(self):
        super().__init__()
        # Получаем путь к папке иконок
        self.icon_directory = os.path.join(os.path.dirname(__file__), 'icons')
        print("Инициализация PhotoSorter")
        self.current_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
        self.parent_dir = os.path.dirname(self.current_dir)
        print(f"Текущая папка: {self.current_dir}")
        print(f"Родительская папка: {self.parent_dir}")

        self.image_list = self.get_images()
        if not self.image_list:
            print("Нет изображений в текущей папке. Завершение работы.")
            sys.exit(1)
        print(f"Найденные изображения: {self.image_list}")
        self.current_index = 0

        self.folders = []
        print(f"Найденные папки: {self.folders}")
        self.key_map = self.assign_keys()
        print(f"Привязка клавиш: {self.key_map}")
        self.hidden_folders = set()
        self.active_folder = None

        self.init_ui()

    def get_images(self):
        supported_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
        images = [f for f in os.listdir(self.current_dir) if f.lower().endswith(supported_extensions)]
        return sorted([os.path.join(self.current_dir, f) for f in images])

    def get_folders(self):
        return self.folders

    def assign_keys(self):
        key_map = {}
        used_keys = set()
        for folder in self.folders:
            available_keys = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in used_keys]
            if available_keys:
                key = random.choice(available_keys)
                used_keys.add(key)
                key_map[key] = folder
            else:
                key_map[""] = folder
        return key_map

    def init_ui(self):
        print("Инициализация интерфейса")
        self.setWindowTitle("Photo Sorter")
        self.setGeometry(100, 100, 1000, 800)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QFrame {
                background-color: white;
                border-radius: 10px;
            }
            QFrame:hover {
                border: 2px solid #0078d7;
            }
            QLabel {
                font-size: 14px;
                color: #333333;
            }
        """)

        # Меню "Файл"
        file_menu = self.menuBar().addMenu("Файл")
        open_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-templates.png")), "Открыть папку", self)
        open_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_action)

        load_file_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-templates.png")), "Открыть список папок из файла", self)
        load_file_action.triggered.connect(self.load_folders_from_file)
        file_menu.addAction(load_file_action)

        load_dir_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-templates.png")), "Открыть список папок из директории", self)
        load_dir_action.triggered.connect(self.load_folders_from_directory)
        file_menu.addAction(load_dir_action)

        save_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-templates.png")), "Сохранить список папок", self)
        save_action.triggered.connect(self.save_folders_to_file)
        file_menu.addAction(save_action)

        save_images_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-templates.png")), "Сохранить список файлов как", self)
        save_images_action.triggered.connect(self.save_images_to_file)
        file_menu.addAction(save_images_action)

        clear_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-templates.png")), "Очистить список папок", self)
        clear_action.triggered.connect(self.clear_folders)
        file_menu.addAction(clear_action)

        exit_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-templates.png")), "Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню "Справка"
        help_menu = self.menuBar().addMenu("Справка")
        about_action = QAction(QIcon.fromTheme("help-about"), "О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        for i, folder in enumerate(self.folders):
            if i % 4 == 0 and folder not in self.hidden_folders:
                frame = self.create_folder_frame(folder)
                top_layout.addWidget(frame)
        main_layout.addLayout(top_layout)

        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(20)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        for i, folder in enumerate(self.folders):
            if i % 4 == 1 and folder not in self.hidden_folders:
                frame = self.create_folder_frame(folder)
                left_layout.addWidget(frame)
        middle_layout.addLayout(left_layout)

        image_layout = QVBoxLayout()
        self.left_arrow = QLabel("◄")
        self.left_arrow.setAlignment(Qt.AlignCenter)
        self.left_arrow.setStyleSheet("font-size: 24px; color: #0078d7;")
        self.left_arrow.setFocusPolicy(Qt.NoFocus)
        self.left_arrow.mousePressEvent = self.left_arrow_clicked
        image_layout.addWidget(self.left_arrow)

        self.image_label = DraggableLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFocusPolicy(Qt.NoFocus)
        self.update_image()
        image_layout.addWidget(self.image_label)

        self.right_arrow = QLabel("►")
        self.right_arrow.setAlignment(Qt.AlignCenter)
        self.right_arrow.setStyleSheet("font-size: 24px; color: #0078d7;")
        self.right_arrow.setFocusPolicy(Qt.NoFocus)
        self.right_arrow.mousePressEvent = self.right_arrow_clicked
        image_layout.addWidget(self.right_arrow)
        middle_layout.addLayout(image_layout)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)
        for i, folder in enumerate(self.folders):
            if i % 4 == 2 and folder not in self.hidden_folders:
                frame = self.create_folder_frame(folder)
                right_layout.addWidget(frame)
        middle_layout.addLayout(right_layout)

        main_layout.addLayout(middle_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        for i, folder in enumerate(self.folders):
            if i % 4 == 3 and folder not in self.hidden_folders:
                frame = self.create_folder_frame(folder)
                bottom_layout.addWidget(frame)
        add_button = QPushButton()
        add_button.setIcon(QIcon.fromTheme("list-add"))
        add_button.setFixedSize(50, 50)
        add_button.setStyleSheet("QPushButton { background-color: #0078d7; border-radius: 25px; } QPushButton:hover { background-color: #005bb5; }")
        add_button.clicked.connect(self.add_folder)
        bottom_layout.addWidget(add_button)
        bottom_layout.addStretch()
        main_layout.addLayout(bottom_layout)

    def create_folder_frame(self, folder):
        frame = FolderFrame(folder)
        frame.setFixedSize(200, 150)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(frame)
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QIcon.fromTheme("folder").pixmap(200, 150)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        remove_button = QPushButton(frame)
        remove_button.setIcon(QIcon.fromTheme("edit-delete"))
        remove_button.setFixedSize(20, 20)
        remove_button.setStyleSheet("QPushButton { background-color: #0078d7; border-radius: 10px; } QPushButton:hover { background-color: #005bb5; }")
        remove_button.move(175, 5)
        remove_button.clicked.connect(lambda: self.remove_folder(folder))

        key_list = [k for k, v in self.key_map.items() if v == folder]
        key = key_list[0] if key_list else ""
        folder_label_text = f"{os.path.basename(folder)} ({key})" if key else os.path.basename(folder)
        folder_label = QLabel(folder_label_text)
        folder_label.setAlignment(Qt.AlignCenter)
        folder_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: white;
                background-color: rgba(0, 0, 0, 100);
                padding: 5px;
                border-radius: 5px;
            }
        """)
        layout.addWidget(folder_label)

        frame.folder_name = folder
        return frame

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сортировки", self.parent_dir, QFileDialog.ShowDirsOnly)
        if folder:
            folder_name = os.path.relpath(folder, self.parent_dir)
            if folder_name and folder_name not in self.folders:
                self.folders.append(folder_name)
                self.key_map = self.assign_keys()
                self.init_ui()
                print(f"Добавлена новая папка: {folder_name}, обновленные ключи: {self.key_map}")
                self.save_folders_to_file()

    def save_folders_to_file(self):
        sort_dir_list_path = os.path.join(self.current_dir, "SortDirList.txt")
        with open(sort_dir_list_path, 'w') as file:
            for folder in self.folders:
                file.write(f"{folder}\n")
        print(f"Список папок сохранен в {sort_dir_list_path}")

    def save_images_to_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить список файлов как", self.current_dir, "Text Files (*.txt)")
        if file_name:
            with open(file_name, 'w') as file:
                for image in self.image_list:
                    file.write(f"{image}\n")
            print(f"Список файлов сохранен в {file_name}")

    def open_folder(self):
        new_dir = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями", self.parent_dir)
        if new_dir:
            self.current_dir = new_dir
            self.parent_dir = os.path.dirname(self.current_dir)
            self.image_list = self.get_images()
            self.current_index = 0
            self.folders = self.get_folders()
            self.key_map = self.assign_keys()
            self.hidden_folders.clear()
            self.active_folder = None
            self.init_ui()
            print(f"Открыта новая папка: {self.current_dir}")

    def clear_folders(self):
        self.folders.clear()
        self.key_map = self.assign_keys()
        self.init_ui()
        print("Список папок очищен")

    def remove_folder(self, folder):
        if folder in self.folders:
            self.folders.remove(folder)
            self.key_map = self.assign_keys()
            self.init_ui()
            print(f"Папка {folder} удалена из списка")

    def load_folders_from_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Выберите файл со списком папок", self.current_dir, "Text Files (*.txt)")
        if file_name:
            with open(file_name, 'r') as file:
                self.folders = [line.strip() for line in file.readlines() if line.strip()]
            self.key_map = self.assign_keys()
            self.init_ui()
            print(f"Список папок загружен из файла: {file_name}")

    def load_folders_from_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите директорию с папками", self.parent_dir)
        if dir_path:
            self.folders = [os.path.relpath(os.path.join(dir_path, f), self.parent_dir)
                           for f in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, f))]
            self.key_map = self.assign_keys()
            self.init_ui()
            print(f"Список папок загружен из директории: {dir_path}")

    def show_about(self):
        about_text = (
            "SwipeSorter\n"
            "Версия: 0.15\n"
            "Описание: Удобное приложение для сортировки изображений по папкам.\n"
            "SwipeSorter — это простой, но мощный инструмент для тех, кто хочет быстро и удобно организовать свои изображения. Он идеально подходит для фотографов, любителей порядка и всех, кто сталкивается с необходимостью сортировки больших коллекций файлов.\n"
            "Автор: [crazysova]\n"
            "Лицензия: GPLv3\n\n"
            "Поддержите автора через Dogecoin:\n"
            "Dogi кошелёк: D123456789ABCDEFGHJKLMNPQRSTUVWXYZ\n\n"
            "Функции:\n"
            "- Просмотр и сортировка изображений\n"
            "- Управление списком папок\n"
            "- Поддержка горячих клавиш и drag-and-drop"
        )
        QMessageBox.about(self, "О программе", about_text)

    def update_image(self):
        print(f"Обновление изображения: {self.current_index}")
        if self.image_list:
            pixmap = QPixmap(self.image_list[self.current_index])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(600, 600, Qt.KeepAspectRatio)
                self.image_label.setPixmap(scaled_pixmap)
                self.image_label.image_path = self.image_list[self.current_index]
            else:
                self.image_label.setText("Ошибка: Не удалось загрузить изображение")
                self.image_label.image_path = None
        else:
            self.image_label.setText("Нет изображений")
            self.image_label.image_path = None
        self.setFocus()

    def left_arrow_clicked(self, event):
        if event.button() == Qt.LeftButton and self.image_list:
            self.current_index = (self.current_index - 1) % len(self.image_list)
            self.update_image()

    def right_arrow_clicked(self, event):
        if event.button() == Qt.LeftButton and self.image_list:
            self.current_index = (self.current_index + 1) % len(self.image_list)
            self.update_image()

    def update_folder_colors(self):
        for layout in [self.centralWidget().layout().itemAt(0).layout(),
                       self.centralWidget().layout().itemAt(1).layout().itemAt(0).layout(),
                       self.centralWidget().layout().itemAt(1).layout().itemAt(2).layout(),
                       self.centralWidget().layout().itemAt(2).layout()]:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget() and hasattr(item.widget(), 'folder_name'):
                    frame = item.widget()
                    if frame.folder_name == self.active_folder:
                        frame.setStyleSheet("QFrame { border: 2px solid green; }")
                    else:
                        frame.setStyleSheet("QFrame { border: 2px solid #cccccc; } QFrame:hover { border: 2px solid #0078d7; }")

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key_Left:
            if self.image_list:
                self.current_index = (self.current_index - 1) % len(self.image_list)
                self.update_image()
        elif key == Qt.Key_Right:
            if self.image_list:
                self.current_index = (self.current_index + 1) % len(self.image_list)
                self.update_image()
        elif key == Qt.Key_Delete:
            if self.image_list:
                send2trash.send2trash(self.image_list[self.current_index])
                print(f"Удалено в корзину: {self.image_list[self.current_index]}")
                del self.image_list[self.current_index]
                if self.current_index >= len(self.image_list):
                    self.current_index = len(self.image_list) - 1
                if self.image_list:
                    self.update_image()
                else:
                    self.close()
        elif event.text().lower() in self.key_map and self.key_map[event.text().lower()]:
            folder = self.key_map[event.text().lower()]
            if modifiers == Qt.ShiftModifier:
                self.hidden_folders.add(folder)
                self.init_ui()
            elif modifiers == Qt.ControlModifier:
                if self.image_list:
                    self.active_folder = folder
                    self.update_folder_colors()
                    source = self.image_list[self.current_index]
                    destination = os.path.join(self.parent_dir, folder, os.path.basename(source))
                    shutil.copy2(source, destination)
                    print(f"Скопировано в {folder}")
                    self.update_image()
            else:
                if self.image_list:
                    self.active_folder = folder
                    self.update_folder_colors()
                    source = self.image_list[self.current_index]
                    destination = os.path.join(self.parent_dir, folder, os.path.basename(source))
                    shutil.move(source, destination)
                    print(f"Фото перемещено в {folder}")
                    del self.image_list[self.current_index]
                    if self.current_index >= len(self.image_list):
                        self.current_index = len(self.image_list) - 1
                    if self.image_list:
                        self.update_image()
                    else:
                        self.close()

if __name__ == "__main__":
    print("Запуск приложения")
    app = QApplication(sys.argv)
    window = PhotoSorter()
    window.show()
    sys.exit(app.exec_())
