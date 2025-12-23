import os
import re
import shutil
from datetime import datetime
import win32security
import win32con
import logging

FISCAL_SERVER = r"\\yekzepmsifc01\c$\Fiscal"
DESTINATION_FOLDER = r"\\yekzeoa01\groups$\Accounting\Fiscal logs"

def impersonate(domain, username, password):
    """Имперсонация указанного пользователя"""
    try:
        h_token = win32security.LogonUser(
            username,
            domain,
            password,
            win32con.LOGON32_LOGON_INTERACTIVE,
            win32con.LOGON32_PROVIDER_DEFAULT
        )
        win32security.ImpersonateLoggedOnUser(h_token)
        return True
    except Exception as e:
        print(f"Ошибка аутентификации: {e}")
        return False


def revert_impersonation():
    """Возврат к оригинальным правам"""
    win32security.RevertToSelf()


def read_file_simple(file_path):
    """Простое чтение файла - игнорируем ошибки кодировки"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()

        # Пробуем разные кодировки
        encodings = ['windows-1251', 'cp1251', 'utf-8', 'latin-1', 'cp866']

        for encoding in encodings:
            try:
                return content.decode(encoding, errors='ignore')
            except:
                continue

        # Если ничего не сработало, возвращаем как есть с заменой ошибок
        return content.decode('utf-8', errors='ignore')
    except Exception as e:
        logging.error(f"Ошибка чтения файла {file_path}: {e}")
        return ""


# === Учетные данные ===
DOMAIN = "DOMAIN"
USERNAME = "USERNAME"
PASSWORD = "PASSWORD"

if not impersonate(DOMAIN, USERNAME, PASSWORD):
    exit("Не удалось аутентифицироваться")

try:
    # Настройка логирования ПОСЛЕ имперсонации
    log_dir = DESTINATION_FOLDER
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        filename=os.path.join(log_dir, 'fiscal_script.log'),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8'
    )

    # Добавляем вывод в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

    logging.info("=" * 60)
    logging.info("Скрипт запущен")

    current_year = datetime.now().year
    current_month = datetime.now().month
    month_dict = [f'Январь {current_year}', f'Февраль {current_year}',
                  f'Март {current_year}', f'Апрель {current_year}', f'Май {current_year}',
                  f'Июнь {current_year}', f'Июль {current_year}', f'Август {current_year}',
                  f'Сентябрь {current_year}', f'Октябрь {current_year}', f'Ноябрь {current_year}',
                  f'Декабрь {current_year}']

    if current_month < 10:
        current_month_str = '0' + str(current_month) + ' ' + month_dict[current_month - 1]
    else:
        current_month_str = str(current_month) + ' ' + month_dict[current_month - 1]

    logging.info(f"Текущий год: {current_year}, месяц: {current_month_str}")

    # Получаем текущую дату
    current_date = datetime.now().strftime("%d.%m")
    logging.info(f"Текущая дата: {current_date}")

    # Проверяем, нужно ли создавать архивную папку
    date_check = current_date.split('.')[0]
    if date_check in ['01', '1', '15']:
        current_date += ' archive'
        logging.info(f"Создание архивной папки для даты: {date_check}")

    # Указываем пути
    source_dir = FISCAL_SERVER
    destination_dir = os.path.join(fr"{DESTINATION_FOLDER}\{current_year}\{current_month_str}",
                                   current_date)

    logging.info(f"Источник: {source_dir}")
    logging.info(f"Назначение: {destination_dir}")

    os.makedirs(destination_dir, exist_ok=True)
    logging.info(f"Создана директория: {destination_dir}")

    date_pattern = re.compile(r'^\d{2}\.\d{2}\.\d{4}')
    file_info = []

    # Обрабатываем файлы hrsfiscal.lo0 - hrsfiscal.lo9
    logging.info("Начинаем обработку файлов hrsfiscal.lo0 - hrsfiscal.lo9")

    for i in range(10):
        file_name = f'hrsfiscal.lo{i}'
        file_path = os.path.join(source_dir, file_name)

        if os.path.exists(file_path):
            logging.info(f"Файл найден: {file_name}")

            # Получаем дату модификации файла
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            mod_date = mod_time.strftime("%d.%m")
            logging.debug(f"Дата модификации: {mod_date}")

            file_date = None

            # Читаем файл
            content = read_file_simple(file_path)

            if content:
                # Ищем дату в содержимом файла (первые 10 строк)
                lines = content.split('\n')
                for line in lines[:10]:
                    line = line.strip()
                    if line:
                        parts = line.split()
                        if parts and date_pattern.match(parts[0]):
                            full_date = parts[0]  # Пример: "09.12.2025"
                            date_parts = full_date.split('.')
                            if len(date_parts) >= 2:
                                file_date = date_parts[0] + '.' + date_parts[1]  # "09.12"
                                logging.debug(f"Найдена дата в файле: {full_date} -> {file_date}")
                                break

            if not file_date:
                # Если дату не нашли в содержимом, используем дату модификации
                file_date = mod_date
                logging.info(f"Файл {file_name}: дата не найдена в содержимом, используем модификацию: {mod_date}")
            else:
                logging.info(f"Файл {file_name}: дата из файла={file_date}, модификация={mod_date}")

            file_info.append({
                'original_name': file_name,
                'file_date': file_date,
                'mod_date': mod_date,
                'source_path': file_path
            })
        else:
            logging.warning(f"Файл не найден: {file_name}")

    logging.info(f"Обработано файлов: {len(file_info)}")

    # Удаляем старые папки
    parent_dir = fr"{DESTINATION_FOLDER}\{current_year}\{current_month_str}"

    if os.path.exists(parent_dir):
        logging.info(f"Очистка старых папок в: {parent_dir}")

        for item in os.listdir(parent_dir):
            item_path = os.path.join(parent_dir, item)

            # Проверяем, является ли это архивной папкой
            try:
                arh_check = item.split(' ')[1] if len(item.split(' ')) > 1 else ''
            except:
                arh_check = ''

            if (os.path.isdir(item_path) and
                    item != current_date and
                    arh_check == '' and
                    re.match(r'^\d{2}\.\d{2}', item)):

                try:
                    shutil.rmtree(item_path)
                    logging.info(f"Удалена папка: {item}")
                except Exception as e:
                    logging.error(f"Ошибка при удалении папки {item}: {e}")
    else:
        logging.warning(f"Родительская директория не существует: {parent_dir}")

    # Копируем файлы
    logging.info(f"Начинаем копирование {len(file_info)} файлов")

    i = 11
    copied_count = 0

    for info in file_info:
        i -= 1
        file_date = info['file_date']
        mod_date = info['mod_date']

        # Формируем имя файла
        if file_date == mod_date:
            new_name = f"{i}. {file_date}.log"
        else:
            new_name = f"{i}. {file_date} - {mod_date}.log"

        dest_path = os.path.join(destination_dir, new_name)

        logging.info(f"Копирование: {info['original_name']} -> {new_name}")

        try:
            shutil.copy2(info['source_path'], dest_path)
            copied_count += 1
            logging.info(f"Успешно скопирован: {info['original_name']}")
        except Exception as e:
            logging.error(f"Ошибка при копировании файла {info['original_name']}: {e}")

    logging.info(f"Скопировано файлов: {copied_count} из {len(file_info)}")

    # Обработка hrsfiscal.log
    log_file = os.path.join(source_dir, 'hrsfiscal.log')
    logging.info(f"Проверка основного файла: {log_file}")

    if os.path.exists(log_file):
        dest_path = os.path.join(destination_dir, "hrsfiscal.log")
        try:
            shutil.copy2(log_file, dest_path)
            logging.info("Успешно скопирован файл hrsfiscal.log")
        except Exception as e:
            logging.error(f"Ошибка при копировании файла hrsfiscal.log: {e}")
    else:
        logging.warning(f"Файл hrsfiscal.log не найден")

    logging.info("Все операции завершены успешно")

except Exception as e:
    logging.error(f"Критическая ошибка в скрипте: {e}", exc_info=True)

finally:
    # Всегда возвращаем оригинальные права
    revert_impersonation()
    logging.info("=" * 60)
    logging.info("Скрипт завершил работу")
    logging.info("\n")