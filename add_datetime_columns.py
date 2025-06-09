import sqlite3
import datetime

def add_datetime_columns():
    try:
        # Get current timestamp as string
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # Add OlusturmaTarihi column with default value
        cursor.execute(f"ALTER TABLE sefer_app_faturalar ADD COLUMN OlusturmaTarihi timestamp DEFAULT '{now}'")
        
        # Add GuncellenmeTarihi column with default value
        cursor.execute(f"ALTER TABLE sefer_app_faturalar ADD COLUMN GuncellenmeTarihi timestamp DEFAULT '{now}'")
        
        conn.commit()
        conn.close()
        print('Columns "OlusturmaTarihi" and "GuncellenmeTarihi" added successfully to sefer_app_faturalar table')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    add_datetime_columns() 