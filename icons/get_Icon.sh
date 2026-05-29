#!/bin/bash

while true; do
    # Запрашиваем у пользователя путь к иконке
    read -p "Введите путь к иконке (или 'exit' для выхода): " icon_path

    # Проверяем, хочет ли пользователь выйти
    if [[ "$icon_path" == "exit" ]]; then
        echo "Выход из программы."
        break
    fi

    # Проверяем, существует ли файл
    if [[ -f "$icon_path" ]]; then
        # Получаем имя файла
        filename=$(basename "$icon_path")
        # Копируем файл в текущую директорию
        cp "$icon_path" ./"$filename"
        echo "Иконка '$filename' скопирована в текущую папку."
    else
        echo "Ошибка: Файл не найден. Попробуйте снова."
    fi
done
