"""
Call logs data processing script.

Loads user and call log data from CSV files, validates/cleans the data,
and generates analytics and ordered call reports.
"""
import csv
import os
import sqlite3

# Resolve the resources folder relative to this file
RESOURCES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'resources'
)

# Database connection and cursor (global for use across functions)
conn = sqlite3.connect(':memory:')
cursor = conn.cursor()


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


# This function will load the users.csv file into the users table, discarding any records with incomplete data
def load_and_clean_users(file_path):

    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader, None)  # skip header row
        rows_to_insert = []

        for row in reader:
            if len(row) != 3:
                continue
            if any(field.strip() == '' for field in row):
                continue
            if not row[0].strip().isdigit():
                continue

            userId, firstName, lastName = row
            rows_to_insert.append((int(userId), firstName, lastName))

        cursor.executemany('''INSERT INTO users (userId, firstName, lastName)
                               VALUES (?, ?, ?)''', rows_to_insert)
        conn.commit()


# This function will load the callLogs.csv file into the callLogs table, discarding any records with incomplete data
def load_and_clean_call_logs(file_path):

    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader, None)  # skip header row

        rows_to_insert = []

        for row in reader:
            if len(row) != 5:
                continue
            if any(field.strip() == '' for field in row):
                continue
            if not row[1].strip().lstrip('-').isdigit() or not row[2].strip().lstrip('-').isdigit() or not row[4].strip().isdigit():
                continue

            phoneNumber, startTime, endTime, direction, userId = row
            rows_to_insert.append((phoneNumber, int(startTime), int(endTime), direction, int(userId)))

        cursor.executemany('''INSERT INTO callLogs (phoneNumber, startTime, endTime, direction, userId)
                               VALUES (?, ?, ?, ?, ?)''', rows_to_insert)
        conn.commit()


# This function will write analytics data to testUserAnalytics.csv - average call time, and number of calls per user.
def write_user_analytics(csv_file_path):

    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.writer(file)

        cursor.execute('''SELECT userId, endTime - startTime FROM callLogs''')

        durations = {}
        counts = {}

        for userId, duration in cursor:
            durations.setdefault(userId, []).append(duration)
            counts[userId] = counts.get(userId, 0) + 1

        # Sort by userId to ensure consistent ordering
        for userId in sorted(durations.keys()):
            avgDuration = sum(durations[userId]) / len(durations[userId])
            numCalls = counts[userId]
            writer.writerow([userId, avgDuration, numCalls])


# This function will write the callLogs ordered by userId, then start time.
def write_ordered_calls(csv_file_path):

    with open(csv_file_path, 'w', newline='') as file:
        writer = csv.writer(file)

        cursor.execute('''SELECT * FROM callLogs ORDER BY userId, startTime''')

        for row in cursor:
            writer.writerow(row)


# No need to touch the functions below!------------------------------------------

def select_from_users_and_call_logs():

    print()
    print("PRINTING DATA FROM USERS")
    print("-------------------------")

    cursor.execute('''SELECT * FROM users''')
    for row in cursor:
        print(row)

    print()
    print("PRINTING DATA FROM CALLLOGS")
    print("-------------------------")

    cursor.execute('''SELECT * FROM callLogs''')
    for row in cursor:
        print(row)


def return_cursor():
    return cursor


if __name__ == '__main__':
    main()
