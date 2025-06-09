import sqlite3

def add_notlar_column():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        cursor.execute('ALTER TABLE sefer_app_faturalar ADD COLUMN Notlar text NULL')
        conn.commit()
        conn.close()
        print('Column "Notlar" added successfully to sefer_app_faturalar table')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    add_notlar_column() 