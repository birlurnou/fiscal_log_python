import os
import re
import shutil
from datetime import datetime
import win32security
import win32con
import win32api
import win32profile

def impersonate(domain, username, password):
    try:
        # Log in using the specified credentials
        h_token = win32security.LogonUser(
            username,
            domain,
            password,
            win32con.LOGON32_LOGON_INTERACTIVE,
            win32con.LOGON32_PROVIDER_DEFAULT
        )

        # We impersonate the user
        win32security.ImpersonateLoggedOnUser(h_token)
        return True
    except Exception as e:
        print(f"Authentication Error: {e}")
        return False

def revert_impersonation():
    win32security.RevertToSelf()

current_year = datetime.now().year
current_month = datetime.now().month
month_dict = [f'January {current_year}', f'February {current_year}',
              f'March {current_year}', f'April {current_year}', f'May {current_year}',
              f'June {current_year}', f'Jule {current_year}', f'August {current_year}',
              f'September {current_year}', f'October {current_year}', f'November {current_year}', f'December {current_year}']
if int(current_month) < 10:
    current_month = '0' + str(current_month) + ' ' + month_dict[current_month-1]

# ========================================
DOMAIN = "domain.local"
USERNAME = "user"
PASSWORD = "pass"
# ========================================

if not impersonate(DOMAIN, USERNAME, PASSWORD):
    exit("Failed to authenticate")

try:
    # We get the current date in the format dd.MM.yyyy
    current_date = datetime.now().strftime("%d.%m")

    try:
        date_check = current_date.split('.')[0]
        if date_check == '01' or date_check == '1' or date_check == '15':
            current_date += ' archive'
    except:
        ...

    # We indicate the paths
    source_dir = r"\\server\c$\Fiscal"
    destination_dir = os.path.join(fr"\\server\path\Fiscal logs\{current_year}\{current_month}", current_date)

    # Create a folder with the current date
    os.makedirs(destination_dir, exist_ok=True)

    # Regular expression to find date in dd.mm.yyyy format
    date_pattern = re.compile(r'^\d{2}\.\d{2}\.\d{4}')

    # List for storing information about files
    file_info = []

    # Processing files fiscal.lo0 - fiscal.lo9
    for i in range(10):
        file_name = f'fiscal.lo{i}'
        file_path = os.path.join(source_dir, file_name)

        if os.path.exists(file_path):
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            mod_date = mod_time.strftime("%d.%m")

            file_date = None
            try:
                with open(file_path, 'r', encoding='windows-1251') as f:
                    for line in f:
                        stripped_line = line.strip()
                        if stripped_line and date_pattern.match(stripped_line.split()[0]):
                            file_date = stripped_line.split()[0]
                            file_date = file_date.split('.')[0] + '.' + file_date.split('.')[1]
                            break
            except Exception as e:
                print(f"Error reading file {file_name}: {e}")
                continue

            if file_date:
                file_info.append({
                    'original_name': file_name,
                    'file_date': file_date,
                    'mod_date': mod_date,
                    'source_path': file_path
                })

    # Delete folders with dates different from the current one
    parent_dir = fr"\\server\path\Fiscal logs\{current_year}\{current_month}"
    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        try:
            arh_check = item.split(' ')[1]
        except:
            arh_check = ''

        if os.path.isdir(item_path) and item != current_date and arh_check == '' and re.match(r'^\d{2}\.\d{2}', item):
            try:
                shutil.rmtree(item_path)
                print(f"Folder deleted: {item}")
            except Exception as e:
                print(f"Error deleting folder {item}: {e}")

    # Copy files to the destination folder with a new name
    i = 11
    for info in file_info:
        i -= 1
        file_date = info['file_date']
        mod_date = info['mod_date']

        new_name = f"{i}. {file_date}.log" if file_date == mod_date else f"{i}. {file_date} - {mod_date}.log"
        print(new_name)

        dest_path = os.path.join(destination_dir, new_name)
        try:
            shutil.copy2(info['source_path'], dest_path)
        except Exception as e:
            print(f"Error copying file {info['original_name']}: {e}")

    # Processing fiscal.log
    log_file = os.path.join(source_dir, 'fiscal.log')
    if os.path.exists(log_file):
        dest_path = os.path.join(destination_dir, "fiscal.log")
        try:
            shutil.copy2(log_file, dest_path)
        except Exception as e:
            print(f"Error copying file fiscal.log: {e}")


finally:
    # We always return the original rights
    revert_impersonation()