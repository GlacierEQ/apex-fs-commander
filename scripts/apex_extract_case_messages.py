#!/usr/bin/env python3
import sqlite3
import os
import shutil
import csv
from datetime import datetime

DB_PATH = os.path.expanduser("~/Library/Messages/chat.db")
DEST_DIR = "/Volumes/ANTIGRAVITY_MEMORY_01/APEX_CASE_OFFLOAD/EXTRACTED_MESSAGES"
DEST_ATTACHMENTS = os.path.join(DEST_DIR, "attachments")
CSV_PATH = os.path.join(DEST_DIR, "extracted_messages.csv")

KEYWORDS = [
    'visitation', 'court', 'custody', 'judge', 'order', 'evidence', 
    'timeline', 'case', 'signal', 'lawyer', 'attorney', 'hearing', 
    'trial', 'ruling', 'decree', 'apex', 'mastermind'
]

def main():
    print(f"Starting extraction to {DEST_DIR}...")
    if not os.path.exists(DEST_ATTACHMENTS):
        os.makedirs(DEST_ATTACHMENTS, exist_ok=True)

    # Mac epoch starts at 2001-01-01
    MAC_EPOCH = 978307200

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    # Build the WHERE clause for keywords
    like_clauses = " OR ".join([f"m.text LIKE '%{k}%'" for k in KEYWORDS])

    query = f"""
    SELECT 
        m.rowid,
        datetime(m.date/1000000000 + {MAC_EPOCH}, 'unixepoch', 'localtime') as date,
        m.text,
        m.is_from_me,
        h.id as sender_id,
        a.filename
    FROM message m
    LEFT JOIN handle h ON m.handle_id = h.rowid
    LEFT JOIN message_attachment_join maj ON m.rowid = maj.message_id
    LEFT JOIN attachment a ON maj.attachment_id = a.rowid
    WHERE m.text IS NOT NULL AND ({like_clauses})
    ORDER BY m.date ASC
    """

    print("Executing query...")
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Failed to execute query: {e}")
        return

    print(f"Found {len(rows)} matching messages/attachments. Processing...")

    extracted = []
    attachment_count = 0

    for row in rows:
        msg_id, msg_date, text, is_from_me, sender_id, attachment_filename = row
        
        copied_attachment_path = ""
        if attachment_filename:
            # The filename in chat.db usually looks like '~/Library/Messages/Attachments/xx/yy/zz/file.jpg'
            # We need to resolve it relative to the home directory
            
            if attachment_filename.startswith('~/'):
                src_path = os.path.expanduser(attachment_filename)
            else:
                src_path = attachment_filename

            if os.path.exists(src_path):
                # Copy the file to the thumbdrive
                base_name = os.path.basename(src_path)
                dest_path = os.path.join(DEST_ATTACHMENTS, f"{msg_id}_{base_name}")
                try:
                    shutil.copy2(src_path, dest_path)
                    copied_attachment_path = f"attachments/{msg_id}_{base_name}"
                    attachment_count += 1
                except Exception as e:
                    copied_attachment_path = f"ERROR COPYING: {e}"
            else:
                copied_attachment_path = "FILE NOT FOUND"

        extracted.append({
            'msg_id': msg_id,
            'date': msg_date,
            'sender_id': sender_id or ('Me' if is_from_me else 'Unknown'),
            'is_from_me': "Yes" if is_from_me else "No",
            'text': text.replace('\n', ' ') if text else "",
            'attachment': copied_attachment_path
        })

    # Write CSV
    print("Writing CSV report...")
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['msg_id', 'date', 'sender_id', 'is_from_me', 'text', 'attachment'])
        writer.writeheader()
        writer.writerows(extracted)

    print("=======================================")
    print(f"Extraction complete.")
    print(f"Total Messages Processed: {len(extracted)}")
    print(f"Total Attachments Copied: {attachment_count}")
    print(f"Results saved to: {DEST_DIR}")
    print("=======================================")

if __name__ == "__main__":
    main()
