#!/usr/bin/env python3
# PhotoSorter: программа для сортировки изображений в папки с возможностью перетаскивания.

import sys
import os
import platform
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QWidget,
                             QPushButton, QFileDialog, QMenuBar, QMessageBox, QAction, QSizePolicy)
from PyQt5.QtGui import (QPixmap, QIcon, QDrag, QImage, QTransform)
from PyQt5.QtCore import Qt, QMimeData, QSize, QTimer, QRect
import shutil
import send2trash
from PIL import Image, ExifTags
import time

class DraggableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(1, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap() and self.image_path:
            # Копируем путь к изображению в буфер обмена
            clipboard = QApplication.clipboard()
            clipboard.setText(self.image_path)
            
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
            event.acceptProposedAction()

    def dropEvent(self, event):
        source_path = event.mimeData().text()
        destination_path = os.path.join(self.window().parent_dir, self.folder_name, os.path.basename(source_path))
        try:
            shutil.move(source_path, destination_path)
            window = self.window()
            window.image_list.remove(source_path)
            window.action_stack.append(('move', source_path, destination_path))
            if window.current_index >= len(window.image_list):
                window.current_index = len(window.image_list) - 1
            if window.image_list:
                window.highlight_folder(self.folder_name)
                window.update_image()
            else:
                # Когда осталась последняя фотка, спрашиваем о сохранении списка папок
                window.ask_save_folders_before_close()
        except Exception as e:
            print(f"Ошибка при перемещении: {e}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            folder_path = os.path.normpath(os.path.join(self.window().parent_dir, self.folder_name))
            try:
                if platform.system() == "Windows":
                    os.startfile(folder_path)
                else:
                    subprocess.run(['xdg-open', folder_path], capture_output=True, text=True)
            except Exception as e:
                print(f"Не удалось открыть папку {folder_path}: {e}")

class PhotoSorter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.icon_directory = os.path.join(os.path.dirname(__file__), 'icons')
        
        # Если папка не указана в аргументах, открываем пустое окно
        if len(sys.argv) > 1:
            self.current_dir = sys.argv[1]
        else:
            self.current_dir = os.getcwd()
            
        self.parent_dir = os.path.dirname(self.current_dir)
        self.image_list = self.get_images()
        self.current_index = 0
        self.folders = []
        self.key_map = self.assign_keys()
        self.hidden_folders = set()
        self.active_folder = None
        self.action_stack = []
        self.current_rotation = 0
        self.folders_saved = True  # Флаг, указывающий сохранен ли текущий список папок
        self.original_folders = []  # Сохраняем оригинальный список папок для сравнения

        self.setWindowTitle(f"Photo Sorter - {self.current_dir}")
        self.setGeometry(100, 100, 1000, 800)
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QLabel { font-size: 14px; color: #333333; }
        """)

        self.setup_menu()
        self.init_ui()

    def ask_save_folders_before_close(self):
        """Спрашивает пользователя, хочет ли он сохранить список папок перед закрытием"""
        if not self.folders:
            return True  # Нет папок для сохранения
            
        if self.folders_saved and self.folders == self.original_folders:
            return True  # Список уже сохранен и не изменялся
            
        reply = QMessageBox.question(self, "Сохранение списка папок",
                                    "Хотите сохранить список папок перед закрытием?",
                                    QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Yes:
            self.save_folders_to_file()
            self.folders_saved = True
            self.original_folders = self.folders.copy()
            return True
        elif reply == QMessageBox.No:
            return True
        else:  # Cancel
            return False

    def closeEvent(self, event):
        """Обработчик события закрытия окна"""
        if not self.ask_save_folders_before_close():
            event.ignore()  # Отменяем закрытие, если пользователь выбрал Cancel
        else:
            event.accept()  # Закрываем окно

    def setup_menu(self):
        file_menu = self.menuBar().addMenu("Файл")
        open_action = QAction(QIcon(os.path.join(self.icon_directory, "folder.png")), "Открыть папку", self)
        open_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_action)

        load_file_action = QAction(QIcon(os.path.join(self.icon_directory, "menu-editor.png")), "Открыть список папок из файла", self)
        load_file_action.triggered.connect(self.load_folders_from_file)
        file_menu.addAction(load_file_action)

        load_dir_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-templates.png")), "Открыть список папок из директории", self)
        load_dir_action.triggered.connect(self.load_folders_from_directory)
        file_menu.addAction(load_dir_action)

        save_action = QAction(QIcon(os.path.join(self.icon_directory, "user-bookmarks.png")), "Сохранить список папок", self)
        save_action.triggered.connect(self.save_folders_to_file)
        file_menu.addAction(save_action)

        save_images_action = QAction(QIcon(os.path.join(self.icon_directory, "folder-download.png")), "Сохранить список файлов как", self)
        save_images_action.triggered.connect(self.save_images_to_file)
        file_menu.addAction(save_images_action)

        clear_action = QAction(QIcon(os.path.join(self.icon_directory, "user-trash.png")), "Очистить список папок", self)
        clear_action.triggered.connect(self.clear_folders)
        file_menu.addAction(clear_action)

        exit_action = QAction(QIcon(os.path.join(self.icon_directory, "process-stop.png")), "Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = self.menuBar().addMenu("Правка")
        rotate_left_action = QAction(QIcon(os.path.join(self.icon_directory, "object-rotate-left.png")), "Повернуть влево", self)
        rotate_left_action.setShortcut("Ctrl+L")
        rotate_left_action.triggered.connect(self.rotate_left)
        edit_menu.addAction(rotate_left_action)

        rotate_right_action = QAction(QIcon(os.path.join(self.icon_directory, "object-rotate-right.png")), "Повернуть вправо", self)
        rotate_right_action.setShortcut("Ctrl+R")
        rotate_right_action.triggered.connect(self.rotate_right)
        edit_menu.addAction(rotate_right_action)

        help_menu = self.menuBar().addMenu("Справка")
        about_action = QAction(QIcon.fromTheme("help-about"), "О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def get_images(self):
        supported_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
        try:
            images = [f for f in os.listdir(self.current_dir) if f.lower().endswith(supported_extensions)]
            return sorted([os.path.join(self.current_dir, f) for f in images])
        except (FileNotFoundError, PermissionError):
            # Если папка недоступна или не существует, возвращаем пустой список
            return []

    def get_exif_rotation(self, image_path):
        try:
            with Image.open(image_path) as img:
                if hasattr(img, '_getexif'):
                    exif = img._getexif()
                    if exif:
                        for tag, value in exif.items():
                            if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                                return value
        except Exception as e:
            print(f"Ошибка при чтении EXIF данных: {e}")
        return 1

    def apply_rotation(self, pixmap, exif_orientation):
        transform = QTransform()

        if exif_orientation == 3:
            transform.rotate(180)
        elif exif_orientation == 6:
            transform.rotate(90)
        elif exif_orientation == 8:
            transform.rotate(270)

        if self.current_rotation != 0:
            transform.rotate(self.current_rotation)

        return pixmap.transformed(transform)

    def rotate_left(self):
        if self.image_list:
            self.current_rotation = (self.current_rotation - 90) % 360
            self.update_image()

    def rotate_right(self):
        if self.image_list:
            self.current_rotation = (self.current_rotation + 90) % 360
            self.update_image()

    def save_rotated_image(self):
        if not self.image_list:
            return

        image_path = self.image_list[self.current_index]
        try:
            # Сохраняем оригинальные временные метки файла
            original_stat = os.stat(image_path)
            original_ctime = original_stat.st_ctime
            original_mtime = original_stat.st_mtime
            
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                exif_orientation = self.get_exif_rotation(image_path)
                rotated_pixmap = self.apply_rotation(pixmap, exif_orientation)

                # Сохраняем в тот же файл, перезаписывая оригинал
                rotated_pixmap.save(image_path)
                
                # Восстанавливаем оригинальные временные метки
                os.utime(image_path, (original_ctime, original_mtime))
                
        except Exception as e:
            print(f"Ошибка при сохранении изображения: {e}")

    def apply_rotation(self, pixmap, exif_orientation):
        transform = QTransform()

        if exif_orientation == 3:
            transform.rotate(180)
        elif exif_orientation == 6:
            transform.rotate(90)
        elif exif_orientation == 8:
            transform.rotate(270)

        if self.current_rotation != 0:
            transform.rotate(self.current_rotation)

        return pixmap.transformed(transform, Qt.SmoothTransformation)

    def assign_keys(self):
        key_map = {}
        used_keys = set()
        kirillica_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
            'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k',
            'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
            'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c',
            'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
            'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        allowed_keys = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for folder in self.folders:
            first_letter = folder[0].lower()
            if 'а' <= first_letter <= 'я':
                latin_letter = kirillica_to_latin.get(first_letter, None)
                if latin_letter and latin_letter in allowed_keys.lower():
                    first_letter = latin_letter
                else:
                    first_letter = None
            if first_letter and first_letter in allowed_keys.lower() and first_letter not in used_keys:
                key_map[first_letter] = folder
                used_keys.add(first_letter)
            else:
                for letter in allowed_keys.lower():
                    if letter not in used_keys:
                        key_map[letter] = folder
                        used_keys.add(letter)
                        break
        return key_map

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        max_top = 6
        max_bottom = 6
        max_side = 4

        for i, folder in enumerate(self.folders):
            if folder in self.hidden_folders:
                continue

            frame = self.create_folder_frame(folder)

            if i < max_top:
                top_layout.addWidget(frame)
            elif i < max_top + max_bottom:
                bottom_layout.addWidget(frame)
            elif i < max_top + max_bottom + max_side:
                left_layout.addWidget(frame)
            elif i < max_top + max_bottom + max_side * 2:
                right_layout.addWidget(frame)

        if top_layout.count() > 0:
            main_layout.addLayout(top_layout)
        if bottom_layout.count() > 0:
            main_layout.addLayout(bottom_layout)

        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(10)

        if left_layout.count() > 0:
            middle_layout.addLayout(left_layout)

        image_layout = QVBoxLayout()
        self.image_label = DraggableLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFocusPolicy(Qt.NoFocus)
        self.update_image()
        image_layout.addWidget(self.image_label, 1)
        middle_layout.addLayout(image_layout, 1)

        if right_layout.count() > 0:
            middle_layout.addLayout(right_layout)

        main_layout.addLayout(middle_layout, 1)

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 20)
        nav_layout.addStretch()

        add_button = QPushButton()
        add_button.setIcon(QIcon(os.path.join(self.icon_directory, "list-add.png")))
        add_button.setFixedSize(40, 40)
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #005bb5;
            }
        """)
        add_button.clicked.connect(self.add_folder)
        nav_layout.addWidget(add_button)

        buttons = [
            ("go-next-rtl.png", self.left_arrow_clicked, "#0078d7", "#005bb5"),
            ("go-next.png", self.right_arrow_clicked, "#0078d7", "#005bb5"),
            ("user-trash.png", self.delete_image, "#ff4444", "#cc0000"),
            ("edit-redo-rtl.png", self.undo_last_action, "#00cc66", "#00994c"),
            ("object-rotate-left.png", self.rotate_left, "#ffaa00", "#cc8800"),
            ("object-rotate-right.png", self.rotate_right, "#ffaa00", "#cc8800"),
            ("document-save.png", self.save_rotated_image, "#00aa00", "#008800"),
        ]

        for icon, callback, normal_color, hover_color in buttons:
            button = QPushButton()
            button.setIcon(QIcon(os.path.join(self.icon_directory, icon)))
            button.setFixedSize(40, 40)
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {normal_color};
                    border-radius: 20px;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                }}
            """)
            button.clicked.connect(callback)
            nav_layout.addWidget(button)

        nav_layout.addStretch()
        main_layout.addLayout(nav_layout)

    def create_folder_frame(self, folder):
        frame = FolderFrame(folder)
        frame.setFixedSize(150, 120)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        pixmap = QIcon(os.path.join(self.icon_directory, "folder.png")).pixmap(64, 64)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)

        folder_label = QLabel(os.path.basename(folder))
        folder_label.setAlignment(Qt.AlignCenter)
        folder_label.setWordWrap(True)
        folder_label.setMaximumWidth(140)

        key_list = [k for k, v in self.key_map.items() if v == folder]
        if key_list:
            folder_label.setText(f"{os.path.basename(folder)}\n({key_list[0].upper()})")

        layout.addWidget(folder_label)

        remove_button = QPushButton()
        remove_button.setIcon(QIcon(os.path.join(self.icon_directory, "list-remove.png")))
        remove_button.setFixedSize(24, 24)
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
        """)
        remove_button.clicked.connect(lambda: self.remove_folder(folder))

        remove_button.move(frame.width() - 30, 5)
        remove_button.setParent(frame)
        remove_button.raise_()

        return frame

    def highlight_folder(self, folder_name):
        for frame in self.findChildren(FolderFrame):
            if frame.folder_name == folder_name:
                original_style = frame.styleSheet()
                frame.setStyleSheet("QFrame { border: 3px solid #0078d7; border-radius: 10px; }")
                QTimer.singleShot(500, lambda: frame.setStyleSheet(original_style))
                break

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сортировки", self.parent_dir, QFileDialog.ShowDirsOnly)
        if folder:
            folder_name = os.path.relpath(folder, self.parent_dir)
            if folder_name and folder_name not in self.folders:
                self.folders.append(folder_name)
                self.folders_saved = False  # Список изменен, требуется сохранение
                self.key_map = self.assign_keys()
                self.init_ui()

    def save_folders_to_file(self):
        sort_dir_list_path = os.path.join(self.current_dir, "SortDirList.txt")
        with open(sort_dir_list_path, 'w') as file:
            for folder in self.folders:
                file.write(f"{folder}\n")
        self.folders_saved = True
        self.original_folders = self.folders.copy()

    def save_images_to_file(self):
        if not self.image_list:
            QMessageBox.information(self, "Информация", "Нет изображений для сохранения.")
            return
            
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить список файлов как", self.current_dir, "Text Files (*.txt)")
        if file_name:
            with open(file_name, 'w') as file:
                for image in self.image_list:
                    file.write(f"{image}\n")

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
            self.current_rotation = 0
            self.folders_saved = True
            self.original_folders = self.folders.copy()
            self.setWindowTitle(f"Photo Sorter - {self.current_dir}")
            self.init_ui()

    def get_folders(self):
        return self.folders

    def clear_folders(self):
        self.folders.clear()
        self.folders_saved = False  # Список изменен, требуется сохранение
        self.key_map = self.assign_keys()
        self.init_ui()

    def remove_folder(self, folder):
        if folder in self.folders:
            self.folders.remove(folder)
            self.folders_saved = False  # Список изменен, требуется сохранение
            self.key_map = self.assign_keys()
            self.init_ui()

    def load_folders_from_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Выберите файл со спиком папок", self.current_dir, "Text Files (*.txt)")
        if file_name:
            with open(file_name, 'r') as file:
                self.folders = [line.strip() for line in file.readlines() if line.strip()]
            self.folders_saved = True
            self.original_folders = self.folders.copy()
            self.key_map = self.assign_keys()
            self.init_ui()

    def load_folders_from_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите директорию с папками", self.parent_dir)
        if dir_path:
            self.folders = [os.path.relpath(os.path.join(dir_path, f), self.parent_dir)
                           for f in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, f))]
            self.folders_saved = False  # Список изменен, требуется сохранение
            self.key_map = self.assign_keys()
            self.init_ui()

    def show_about(self):
        about_text = (
            "PhotoSorter\n"
            "Версия: 0.24\n"
            "Описание: Удобное приложение для сортировки изображений по папкам.\n"
            "Автор: [crazysova]\n"
            "Лицензия: GPLv3\n\n"
            "Поддержите автора через Dogecoin:\n"
            "Dogi кошелёк: D123456789ABCDEFGHJKLMNPQRSTUVWXYZ\n\n"
            "Функции:\n"
            "- Просмотр и сортировка изображений\n"
            "- Управление списком папок\n"
            "- Поддержка горячих клавиш и drag-and-drop\n"
            "- Автоповорот изображений по EXIF-данным\n"
            "- Ручной поворот без изменения файлов"
        )
        QMessageBox.about(self, "О программе", about_text)

    def update_image(self):
        if not self.image_list:
            self.image_label.setText("Нет изображений\nПеретащите папку с фото или откройте через меню Файл")
            self.image_label.image_path = None
            # Показываем диалог сохранения только если фото закончились
            if hasattr(self, '_had_images') and self._had_images:
                self.ask_save_folders_after_sorting()
            return
        else:
            self._had_images = True

        # При первом обновлении изображения вызываем resizeEvent
        if not hasattr(self, '_first_image_shown'):
            self._first_image_shown = True
            QTimer.singleShot(100, lambda: self.resizeEvent(None))

        image_path = self.image_list[self.current_index]
        self.image_label.image_path = image_path

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.image_label.setText("Ошибка: Не удалось загрузить изображение")
            return

        exif_orientation = self.get_exif_rotation(image_path)

        rotated_pixmap = self.apply_rotation(pixmap, exif_orientation)

        label_size = self.image_label.size()
        available_width = label_size.width()
        available_height = label_size.height()

        scaled_pixmap = rotated_pixmap.scaled(
            available_width, available_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.image_label.setPixmap(scaled_pixmap)
        self.setFocus()

    def ask_save_folders_after_sorting(self):
        """Спрашивает о сохранении списка папок после завершения сортировки"""
        if not self.folders:
            return
            
        if self.folders_saved and self.folders == self.original_folders:
            return  # Список уже сохранен и не изменялся
            
        reply = QMessageBox.question(self, "Сохранение списка папок",
                                    "Все изображения отсортированы.\nХотите сохранить список папок?",
                                    QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.save_folders_to_file()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_image()

    def left_arrow_clicked(self):
        if self.image_list:
            self.current_index = (self.current_index - 1) % len(self.image_list)
            self.current_rotation = 0
            self.update_image()

    def right_arrow_clicked(self):
        if self.image_list:
            self.current_index = (self.current_index + 1) % len(self.image_list)
            self.current_rotation = 0
            self.update_image()

    def delete_image(self):
        if self.image_list:
            image_path = self.image_list[self.current_index]
            send2trash.send2trash(image_path)
            self.action_stack.append(('delete', image_path, self.current_index))
            del self.image_list[self.current_index]
            if self.current_index >= len(self.image_list):
                self.current_index = len(self.image_list) - 1
            if self.image_list:
                self.update_image()
            else:
                # Когда удалили последнее изображение, спрашиваем о сохранении списка папок
                self.ask_save_folders_after_sorting()

    def undo_last_action(self):
        if self.action_stack:
            last_action = self.action_stack.pop()
            if last_action[0] == 'move':
                _, source, destination = last_action
                shutil.move(destination, source)
                self.image_list.insert(self.current_index, source)
            elif last_action[0] == 'delete':
                _, image_path, original_index = last_action
                trash_dir = send2trash.get_trash_dir()
                potential_path = os.path.join(trash_dir, os.path.basename(image_path))
                if os.path.exists(potential_path):
                    shutil.move(potential_path, image_path)
                elif os.path.exists(image_path):
                    shutil.move(image_path, self.current_dir)
                self.image_list.insert(original_index, image_path)
                self.current_index = original_index
            self.update_image()

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key_Left:
            if self.image_list:
                self.current_index = (self.current_index - 1) % len(self.image_list)
                self.current_rotation = 0
                self.update_image()
        elif key == Qt.Key_Right:
            if self.image_list:
                self.current_index = (self.current_index + 1) % len(self.image_list)
                self.current_rotation = 0
                self.update_image()
        elif key == Qt.Key_Delete:
            self.delete_image()
        elif key == Qt.Key_L and modifiers == Qt.ControlModifier:
            self.rotate_left()
        elif key == Qt.Key_R and modifiers == Qt.ControlModifier:
            self.rotate_right()
        elif event.text().lower() in self.key_map:
            folder = self.key_map[event.text().lower()]
            if modifiers == Qt.ShiftModifier:
                self.hidden_folders.add(folder)
                self.init_ui()
            elif modifiers == Qt.ControlModifier:
                if self.image_list:
                    self.active_folder = folder
                    source = self.image_list[self.current_index]
                    destination = os.path.join(self.parent_dir, folder, os.path.basename(source))
                    shutil.copy2(source, destination)
                    self.update_image()
            else:
                if self.image_list:
                    self.active_folder = folder
                    source = self.image_list[self.current_index]
                    destination = os.path.join(self.parent_dir, folder, os.path.basename(source))
                    try:
                        shutil.move(source, destination)
                        self.action_stack.append(('move', source, destination))
                        del self.image_list[self.current_index]
                        if self.current_index >= len(self.image_list):
                            self.current_index = len(self.image_list) - 1
                        self.highlight_folder(folder)
                        if self.image_list:
                            self.update_image()
                        else:
                            # Когда переместили последнее изображение, спрашиваем о сохранении списка папок
                            self.ask_save_folders_after_sorting()
                    except Exception as e:
                        QMessageBox.warning(self, "Ошибка", f"Не удалось переместить файл: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhotoSorter()
    window.show()
    sys.exit(app.exec_())