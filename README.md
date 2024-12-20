## Тестовое задание для Chat2Desk

1) Клонируйте git репозиторий на ваш компьютер
```commandline
git clone <адрес репозитория>
```
2) Активируйте виртуальное окружение в корне проекта:
```commandline
pip install virtualenv
python -m virtualenv venv 
.\venv\Scripts\activate 
```
3) Установите `poetry` в вашем виртуальном окружении
```commandline
python -m pip install poetry
```
4) Установите зависимости
```commandline
python -m poetry install
```

## Структура

* `main.py` - Файл с кодом класса Handler.
    Содержит методы-обработчики триггеров, методы для запроса к API
    и методы, реализующие необходимый функционал.
* `test.py` - Файл с unit-тестами. Проверяют следующие тест-кейсы.
  *     Запрос из внешней системы. Пользователь с именем существует.
  *     Запрос из внешней системы. Пользователь с именем не существует.
  *     Новое обращение. У пользователя тег VIP, есть свободный оператор.
  *     Новое обращение. У пользователя тег VIP, нет свободного оператора.
  *     Новое обращение. У пользователя нет тега VIP.
  Можно запустить командой `python.exe -m unittest test.py`

## Схемы работы алгоритмов 

### Задача 1

![Задача 1](/task1.jpg)

### Задача 2

![Задача 2](/task2.jpg)
