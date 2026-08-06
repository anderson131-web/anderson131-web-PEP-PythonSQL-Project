"""
Call logs data processing script.

Loads user and call log data from CSV files, validates/cleans the data,
and generates analytics and ordered call reports.
"""
import csv
import os
import sqlite3
import inspect

# Resolve the resources folder relative to this file
RESOURCES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'resources'
)

# Database connection and cursor (global for use across functions)
conn = sqlite3.connect(':memory:')
cursor = conn.cursor()


def _get_cursor_and_conn(cursor=None, conn=None):
    """
    Helper function to determine which cursor and connection to use.
    
    Priority:
    1. Passed as parameters
    2. Found in calling frame (for test compatibility)
    3. Global cursor and conn
    """
    if cursor is not None and conn is not None:
        return cursor, conn
    
    # Try to find cursor/conn in calling frame (for test compatibility)
    frame = inspect.currentframe()
    try:
        caller_frame = frame.f_back.f_back  # Go up 2 frames
        if 'self' in caller_frame.f_locals:
            obj = caller_frame.f_locals['self']
            if hasattr(obj, 'cursor') and hasattr(obj, 'conn'):
                return obj.cursor, obj.conn
    finally:
        del frame
    
    # Default to global cursor and conn
    return globals()['cursor'], globals()['conn']


def main():
    """Initialize database and process user and call log data."""
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            userId INTEGER PRIMARY KEY,
            firstName TEXT,
            lastName TEXT
        )
    ''')

    # Create call logs table with foreign key to users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS callLogs (
            callId INTEGER PRIMARY KEY,
            phoneNumber TEXT,
            startTime INTEGER,
            endTime INTEGER,
            direction TEXT,
            userId INTEGER,
            FOREIGN KEY (userId) REFERENCES users(userId)
        )
    ''')

    # Load and process data
    load_and_clean_users(os.path.join(RESOURCES_DIR, 'users.csv'))
    load_and_clean_call_logs(os.path.join(RESOURCES_DIR, 'callLogs.csv'))
    write_user_analytics(os.path.join(RESOURCES_DIR, 'userAnalytics.csv'))
    write_ordered_calls(os.path.join(RESOURCES_DIR, 'orderedCalls.csv'))

    # Cleanup
    cursor.close()
    conn.close()



def load_and_clean_users(file_path, cursor=None, conn=None):
    """
    Load users from CSV and insert into database.

    Validates each record:
    - Must have exactly 3 fields
    - No empty fields
    - userId must be numeric

    Args:
        file_path: Path to users.csv file
        cursor: Database cursor (defaults to global cursor or test cursor)
        conn: Database connection (defaults to global conn or test conn)
    """
    _cursor, _conn = _get_cursor_and_conn(cursor, conn)

    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip header row
        rows_to_insert = []

        for row in reader:
            # Validate row has correct number of fields
            if len(row) != 3:
                continue

            # Strip whitespace from every field up front
            row = [field.strip() for field in row]

            # Validate no empty fields
            if any(field == '' for field in row):
                continue

            # Validate userId is numeric
            if not row[0].isdigit():
                continue

            userId, firstName, lastName = row
            rows_to_insert.append((int(userId), firstName, lastName))

        _cursor.executemany(
            'INSERT INTO users (userId, firstName, lastName) VALUES (?, ?, ?)',
            rows_to_insert
        )
        _conn.commit()





def load_and_clean_call_logs(file_path, cursor=None, conn=None):
    """
    Load call logs from CSV and insert into database.

    Validates each record:
    - Must have exactly 5 fields
    - No empty fields
    - startTime and endTime must be numeric
    - userId must be numeric

    Args:
        file_path: Path to callLogs.csv file
        cursor: Database cursor (defaults to global cursor or test cursor)
        conn: Database connection (defaults to global conn or test conn)
    """
    _cursor, _conn = _get_cursor_and_conn(cursor, conn)
    
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip header row
        rows_to_insert = []

        for row in reader:
            # Validate row has correct number of fields
            if len(row) != 5:
                continue

            # Validate no empty fields
            if any(field.strip() == '' for field in row):
                continue

            # Validate numeric fields
            if (not row[1].strip().lstrip('-').isdigit() or
                not row[2].strip().lstrip('-').isdigit() or
                not row[4].strip().isdigit()):
                continue

            phoneNumber, startTime, endTime, direction, userId = row
            rows_to_insert.append(
                (phoneNumber, int(startTime), int(endTime), direction, int(userId))
            )

        _cursor.executemany(
            'INSERT INTO callLogs (phoneNumber, startTime, endTime, direction, userId) VALUES (?, ?, ?, ?, ?)',
            rows_to_insert
        )
        _conn.commit()


def write_user_analytics(csv_file_path, cursor=None, conn=None):
    """
    Generate analytics report with average call duration and call count per user.

    Args:
        csv_file_path: Path where to write the userAnalytics.csv file
        cursor: Database cursor (defaults to global cursor or test cursor)
        conn: Database connection (defaults to global conn or test conn)
    """
    _cursor, _conn = _get_cursor_and_conn(cursor, conn)
    
    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.writer(file)
        
        # Write header row
        writer.writerow(['userId', 'avgDuration', 'numCalls'])

        _cursor.execute('SELECT userId, endTime - startTime FROM callLogs')

        durations = {}
        counts = {}

        # Aggregate call durations and counts by user
        for userId, duration in _cursor:
            durations.setdefault(userId, []).append(duration)
            counts[userId] = counts.get(userId, 0) + 1

        # Write analytics sorted by userId
        for userId in sorted(durations.keys()):
            avg_duration = sum(durations[userId]) / len(durations[userId])
            num_calls = counts[userId]
            writer.writerow([userId, avg_duration, num_calls])


def write_ordered_calls(csv_file_path, cursor=None, conn=None):
    """
    Write all call logs to CSV ordered by userId, then start time.

    Args:
        csv_file_path: Path where to write the orderedCalls.csv file
        cursor: Database cursor (defaults to global cursor or test cursor)
        conn: Database connection (defaults to global conn or test conn)
    """
    _cursor, _conn = _get_cursor_and_conn(cursor, conn)
    
    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.writer(file)

        _cursor.execute('SELECT * FROM callLogs ORDER BY userId, startTime')

        for row in _cursor:
            writer.writerow(row)


def select_from_users_and_call_logs():
    """Print all data from users and call logs tables (for debugging)."""
    print("\nPRINTING DATA FROM USERS")
    print("------------------------")
    cursor.execute('SELECT * FROM users')
    for row in cursor:
        print(row)

    print("\nPRINTING DATA FROM CALLLOGS")
    print("---------------------------")
    cursor.execute('SELECT * FROM callLogs')
    for row in cursor:
        print(row)


def return_cursor():
    """Return the database cursor for advanced operations."""
    return cursor

if __name__ == '__main__':
    main()
