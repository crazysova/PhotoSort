#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QFileDialog
from PyQt5.QtGui import QPixmap, QIcon, QFont, QColor, QPainter
from PyQt5.QtCore import Qt
import shutil
import random

class PhotoSorter(QMainWindow):
    def __init__(self):
        super().__init__()
        print("Инициализация PhotoSorter")
        self.current_dir = os.getcwd()
        self.parent_dir = os.path.dirname(self.current_dir)
        print(f"Текущая папка: {self.current_dir}")
        print(f"Родительская папка: {self.parent_dir}")

        self.image_list = self.get_images()
        if not self.image_list:
            print("Нет изображений в текущей папке. Завершение работы.")
            sys.exit(1)
        print(f"Найденные изображения: {self.image_list}")
        self.current_index = 0

        self.folders = self.get_folders()
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
        sort_dir_list_path = os.path.join(self.current_dir, "SortDirList.txt")
        if os.path.exists(sort_dir_list_path):
            print("Файл SortDirList.txt найден, читаем директории из него.")
            with open(sort_dir_list_path, 'r') as file:
                folders = [line.strip() for line in file.readlines() if line.strip()]
        else:
            print("Файл SortDirList.txt не найден, используем директории из родительской папки.")
            folders = [f for f in os.listdir(self.parent_dir) if os.path.isdir(os.path.join(self.parent_dir, f))]
            current_folder_name = os.path.basename(self.current_dir)
            folders = sorted([f for f in folders if f != current_folder_name])
        return folders

    def assign_keys(self):
        key_map = {}
        used_keys = set()
        for folder in self.folders:
            available_keys = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in used_keys]
            if not available_keys:
                break
            key = random.choice(available_keys)
            used_keys.add(key)
            key_map[key] = folder
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
        left_arrow = QLabel("◄")
        left_arrow.setAlignment(Qt.AlignCenter)
        left_arrow.setStyleSheet("font-size: 24px; color: #0078d7;")
        left_arrow.setFocusPolicy(Qt.NoFocus)
        image_layout.addWidget(left_arrow)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFocusPolicy(Qt.NoFocus)
        self.update_image()
        image_layout.addWidget(self.image_label)

        right_arrow = QLabel("►")
        right_arrow.setAlignment(Qt.AlignCenter)
        right_arrow.setStyleSheet("font-size: 24px; color: #0078d7;")
        right_arrow.setFocusPolicy(Qt.NoFocus)
        image_layout.addWidget(right_arrow)
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
        frame = QFrame()
        frame.setFixedSize(200, 150)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(frame)
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QIcon.fromTheme("folder").pixmap(200, 150)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        key = [k for k, v in self.key_map.items() if v == folder][0]
        folder_label = QLabel(f"{folder} ({key})", frame)
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
        folder_label.setGeometry(10, 110, 180, 30)
        layout.addWidget(folder_label)

        frame.folder_name = folder
        return frame

    def add_folder(self):
        new_folders = []
        while True:
            folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сортировки", self.parent_dir, QFileDialog.ShowDirsOnly)
            if not folder:  # Пользователь нажал "Отмена"
                break
            folder_name = os.path.basename(folder)
            if folder_name and folder_name not in self.folders:
                new_folders.append(folder_name)
        if new_folders:
            self.folders.extend(new_folders)
            self.key_map = self.assign_keys()
            self.init_ui()
            print(f"Добавлены новые папки: {new_folders}, обновленные ключи: {self.key_map}")
            self.save_folders_to_file()

    def save_folders_to_file(self):
        sort_dir_list_path = os.path.join(self.current_dir, "SortDirList.txt")
        with open(sort_dir_list_path, 'w') as file:
            for folder in self.folders:
                file.write(f"{folder}\n")
        print(f"Список папок сохранен в {sort_dir_list_path}")

    def update_image(self):
        print(f"Обновление изображения: {self.current_index}")
        if self.image_list:
            pixmap = QPixmap(self.image_list[self.current_index])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(600, 600, Qt.KeepAspectRatio)
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("Ошибка: Не удалось загрузить изображение")
        else:
            self.image_label.setText("Нет изображений")
        self.setFocus()

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
                os.remove(self.image_list[self.current_index])
                print(f"Удалено: {self.image_list[self.current_index]}")
                del self.image_list[self.current_index]
                if self.current_index >= len(self.image_list):
                    self.current_index = len(self.image_list) - 1
                if self.image_list:
                    self.update_image()
                else:
                    self.close()
        elif event.text().lower() in self.key_map:
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
