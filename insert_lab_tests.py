import csv
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "rapidlabs.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

with open("tests.csv", newline='', encoding="latin-1") as file:
    reader = csv.DictReader(file)

    for row in reader:
        # 🔥 CLEAN HEADERS (VERY IMPORTANT)
        row = {k.strip().upper(): v for k, v in row.items()}

        service_code = row.get("SERVICE CODE")
        test_name = row.get("TEST NAME")
        mrp = row.get("MRP")
        b2b = row.get("B2B")

        # skip invalid rows
        if not service_code or not test_name:
            continue

        service_code = service_code.strip()
        test_name = test_name.strip()

        # check duplicate
        cursor.execute(
            "SELECT id FROM lab_tests WHERE service_code=?",
            (service_code,)
        )
        if cursor.fetchone():
            print(f"Skipping: {service_code}")
            continue

        try:
            mrp_val = float(mrp) if mrp and mrp.strip() else 0
        except:
            mrp_val = 0

        try:
            b2b_val = float(b2b) if b2b and b2b.strip() else 0
        except:
            b2b_val = 0

        cursor.execute("""
            INSERT INTO lab_tests (test_name, service_code, mrp, price)
            VALUES (?, ?, ?, ?)
        """, (
            test_name,
            service_code,
            mrp_val,
            b2b_val
        ))

conn.commit()
conn.close()

print("✅ Data inserted successfully!")