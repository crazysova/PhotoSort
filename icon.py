import sys
import os
from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QHBoxLayout
)
from PyQt5.QtGui import QIcon, QClipboard
from PIL import Image  # Убедитесь, что библиотека PIL установлена

class IconTableViewer(QWidget):
    def __init__(self, theme_path):
        super().__init__()
        self.setWindowTitle("Icon Table Viewer")
        self.resize(1200, 800)

        self.layout = QVBoxLayout()

        # Создаем горизонтальный layout для кнопок
        self.button_layout = QHBoxLayout()

        self.table = QTableWidget()
        self.theme_path = theme_path
        self.icon_sizes = self.get_icon_sizes(theme_path)  # Получаем доступные размеры иконок
        self.size = self.icon_sizes[0] if self.icon_sizes else 64  # Значение по умолчанию

        # Создаем кнопки для каждого размера
        self.create_size_buttons()

        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.table)

        self.setLayout(self.layout)

        # Устанавливаем сигнал для клика ячейки
        self.table.cellClicked.connect(self.copy_icon_to_clipboard)

        self.populate_icons(self.size)

    def create_size_buttons(self):
        # Добавляем кнопки для изменения размера иконок
        for size in self.icon_sizes:
            button = QPushButton(str(size))
            button.setFixedSize(100, 40)  # Устанавливаем фиксированный размер кнопки
            button.clicked.connect(lambda checked, s=size: self.set_icon_size(s))
            self.button_layout.addWidget(button)  # Добавляем кнопку в горизонтальный layout

    def set_icon_size(self, size):
        self.size = size
        self.populate_icons(size)

    def populate_icons(self, size):
        icon_files = self.find_icons(self.theme_path)

        # Фильтруем иконки по размеру
        filtered_icon_files = [icon_path for icon_path in icon_files if self.is_icon_size_correct(icon_path, size)]

        # Устанавливаем количество строк и колонок
        self.table.setRowCount(len(filtered_icon_files) // 5 + 1)  # 5 иконок в строке
        self.table.setColumnCount(5)

        for index, icon_path in enumerate(filtered_icon_files):
            icon = QIcon(icon_path)  # Загружаем иконку

            # Создаем ячейку для иконки
            item = QTableWidgetItem()
            item.setIcon(icon)
            item.setFlags(QtCore.Qt.ItemIsEnabled)  # Устанавливаем, что ячейка только для чтения

            row = index // 5
            col = index % 5
            self.table.setItem(row, col, item)

            # Устанавливаем размер значков в ячейках
            self.table.setRowHeight(row, size)
            self.table.setColumnWidth(col, size)

            # Сохраняем путь к иконке в данных ячейки
            item.setData(QtCore.Qt.UserRole, os.path.basename(icon_path))

        # Установка размера значков
        self.table.setIconSize(QtCore.QSize(size, size))

        # Настраиваем растяжение ячеек
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)

    def is_icon_size_correct(self, icon_path, size):
        try:
            # Используем Pillow для получения размера изображения
            with Image.open(icon_path) as img:
                width, height = img.size
                return width == size and height == size  # Проверяем, соответствует ли ширина и высота
        except Exception as e:
            print(f"Error opening image {icon_path}: {e}")
            return False  # Если возникла ошибка, не показываем иконку

    def copy_icon_to_clipboard(self, row, column):
        item = self.table.item(row, column)
        if item:
            icon_name = item.data(QtCore.Qt.UserRole)  # Получаем название иконки из данных
            clipboard = QApplication.clipboard()
            clipboard.setText(icon_name)  # Копируем название в буфер обмена

    def find_icons(self, theme_path):
        theme_file = os.path.join(theme_path, 'index.theme')
        icon_files = []

        if os.path.exists(theme_file):
            with open(theme_file, 'r', encoding='utf-8') as f:
                directories = []
                for line in f:
                    line = line.strip()
                    if line.startswith('Directories='):
                        directories = line.split('=')[1].split(',')
                        break

            for directory in directories:
                directory_path = os.path.join(theme_path, directory.strip())
                if os.path.exists(directory_path):
                    icon_files.extend(self.get_icons_from_directory(directory_path))

        return icon_files

    def get_icons_from_directory(self, directory):
        supported_formats = ['.png', '.svg', '.xpm', '.ico']
        icons = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in supported_formats):
                    icons.append(os.path.join(root, file))

        return icons

    def get_icon_sizes(self, theme_path):
        sizes = set()  # Используем set для уникальных размеров
        theme_file = os.path.join(theme_path, 'index.theme')

        if os.path.exists(theme_file):
            with open(theme_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Size='):
                        sizes.update(map(int, line.split('=')[1].split(',')))

        return sorted(sizes) if sizes else [16, 32, 48, 64, 128, 256]  # По умолчанию если размеры не указаны

if __name__ == "__main__":
    app = QApplication(sys.argv)

    theme_path = "/usr/share/icons/Mint-L"  # Путь к вашим иконкам

    icon_table_viewer = IconTableViewer(theme_path)
    icon_table_viewer.show()

    sys.exit(app.exec_())
