#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtGui import QPixmap, QIcon
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
            key = folder[0].lower()
            if key in used_keys and len(folder) > 1:
                key = folder[1].lower()
            if key in used_keys:
                key = random.choice([c for c in "abcdefghijklmnopqrstuvwxyz" if c not in used_keys])
            used_keys.add(key)
            key_map[key] = folder
        return key_map

    def init_ui(self):
        print("Инициализация интерфейса")
        self.setWindowTitle("Photo Sorter")
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_layout = QHBoxLayout()
        for i in range(3):
            if i < len(self.folders):
                folder = self.folders[i]
                if folder not in self.hidden_folders:
                    frame = self.create_folder_frame(folder)
                    top_layout.addWidget(frame)
            else:
                top_layout.addStretch()
        main_layout.addLayout(top_layout)

        middle_layout = QHBoxLayout()
        left_arrow = QLabel("<")
        left_arrow.setAlignment(Qt.AlignCenter)
        middle_layout.addWidget(left_arrow)

        self.image_label = QLabel()
        self.update_image()
        middle_layout.addWidget(self.image_label)

        right_arrow = QLabel(">")
        right_arrow.setAlignment(Qt.AlignCenter)
        middle_layout.addWidget(right_arrow)
        main_layout.addLayout(middle_layout)

        self.bottom_layout = QHBoxLayout()
        for i in range(3, 6):
            if i < len(self.folders):
                folder = self.folders[i]
                if folder not in self.hidden_folders:
                    frame = self.create_folder_frame(folder)
                    self.bottom_layout.addWidget(frame)
            else:
                self.bottom_layout.addStretch()
        main_layout.addLayout(self.bottom_layout)

    def create_folder_frame(self, folder):
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        frame.setStyleSheet("QFrame { border: 1px solid black; } QFrame:hover { border: 2px solid blue; }")
        layout = QHBoxLayout(frame)

        icon_label = QLabel()
        icon_label.setPixmap(QIcon.fromTheme("folder").pixmap(16, 16))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        name_label = QLabel(folder)
        name_label.setAlignment(Qt.AlignCenter)
        key = [k for k, v in self.key_map.items() if v == folder][0]
        key_label = QLabel(f"({key})")
        key_label.setAlignment(Qt.AlignCenter)
        text_layout.addWidget(name_label)
        text_layout.addWidget(key_label)
        layout.addLayout(text_layout)

        frame.folder_name = folder
        frame.setMouseTracking(True)
        return frame

    def update_image(self):
        print(f"Обновление изображения: {self.current_index}")
        if self.image_list:
            pixmap = QPixmap(self.image_list[self.current_index])
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio)
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("Ошибка: Не удалось загрузить изображение")
        else:
            self.image_label.setText("Нет изображений")

    def update_folder_colors(self):
        for layout in [self.centralWidget().layout().itemAt(0).layout(), self.bottom_layout]:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    frame = item.widget()
                    if hasattr(frame, 'folder_name'):
                        if frame.folder_name == self.active_folder:
                            frame.setStyleSheet("QFrame { border: 2px solid green; } QFrame:hover { border: 2px solid blue; }")
                        else:
                            frame.setStyleSheet("QFrame { border: 1px solid black; } QFrame:hover { border: 2px solid blue; }")

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
        elif key == Qt.Key_Delete:  # Удаление изображения
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
            elif modifiers == Qt.ControlModifier:  # Копирование с Ctrl + клавиша
                if self.image_list:
                    self.active_folder = folder
                    self.update_folder_colors()
                    source = self.image_list[self.current_index]
                    destination = os.path.join(self.parent_dir, folder, os.path.basename(source))
                    shutil.copy2(source, destination)  # Копируем вместо перемещения
                    print(f"Скопировано в {folder}")
                    self.update_image()  # Обновляем, но не удаляем изображение
            else:  # Перемещение без модификаторов
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
