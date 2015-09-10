## Система нагрузочного тестирования телекоммуникационных систем на основе имитационной модели

Простая однопоточная программная реализация комплекса систем оператора мобильной связи (на примере МТС). Используется для решения следующей задачи тестирования: как подать уменьшенную нагрузку на тестовую систему, обладающую в разы меньшими вычислительными мощностями и объёмом памяти, но сохранить основные сценарии использования в тех же пропорциях?

Используется кластерный анализ активности абонентов, которые объединяются в группы, и в дальнейшем активность части абонентов из каждой группы воспроизводится на тестовой системе (в рамках ВКР просто копируются записи из БД).

Реализовано на языке Python 3 с применением библиотек NumPy, SQLAlchemy, scikit-learn.

## Установка

- Установите интерпретатор Python 3 с официального сайта.

- Установите необходимые библиотеки
  - MacOS X и Linux:
  
  ```bash
  git clone https://github.com/SukharevAndrey/Diploma
  cd Diploma
  pip3 install -r requirements.txt
  ```
  - Windows:
  
  Установите пакеты, указанные в requirements.txt, с сайта http://www.lfd.uci.edu/~gohlke/pythonlibs/

## Запуск

Перейдите в папку с проектом и выполните:
```bash
python3 main.py
```
