#!/usr/bin/env python3
import csv
import collections
from datetime import datetime
import os

CSV_PATH = '/Volumes/ANTIGRAVITY_MEMORY_01/APEX_CASE_OFFLOAD/EXTRACTED_MESSAGES/extracted_messages.csv'
LEDGER_PATH = '/Users/macarena1/dev/projects/apex-fs-commander/legal_documents/intel/COMMUNICATIONS_LEDGER.md'

# Identity Map
IDENTITY_MAP = {
    "+17203087615": "UNKNOWN_VECTOR_ALPHA",
    "+18086738156": "UNKNOWN_VECTOR_BETA",
    "+14233553533": "UNKNOWN_VECTOR_GAMMA",
}

def main():
    if not os.path.exists(CSV_PATH):
        print(f"Error: Could not find extracted messages at {CSV_PATH}")
        return

    messages = []
    sender_counts = collections.Counter()

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            messages.append(row)
            sender_counts[row['sender_id']] += 1

    # Sort messages chronologically
    messages.sort(key=lambda x: x['date'])

    # Build Ledger
    lines = [
        "# 📡 COMMUNICATIONS INTELLIGENCE LEDGER",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "**Source:** Local iMessage Database Extraction",
        f"**Total Records:** {len(messages)}",
        "",
        "## 📊 TOP COMMUNICATORS",
        "| Identity | Sender ID | Message Count |",
        "| :--- | :--- | :---: |"
    ]

    for sender, count in sender_counts.most_common(15):
        identity = IDENTITY_MAP.get(sender, "Unattributed")
        if sender == "Me":
            identity = "Target (Self)"
        lines.append(f"| `{identity}` | `{sender}` | **{count}** |")

    lines.extend([
        "",
        "---",
        "## 📅 CHRONOLOGICAL HIGHLIGHT REEL",
        "*(Displaying earliest and latest critical communications)*",
        ""
    ])

    # Show first 10 and last 10
    if len(messages) > 20:
        display_messages = messages[:10] + [{"msg_id": "...", "date": "...", "sender_id": "...", "is_from_me": "...", "text": "...", "attachment": ""}] + messages[-10:]
    else:
        display_messages = messages

    for msg in display_messages:
        if msg["msg_id"] == "...":
            lines.append("\n...\n*(Hundreds of communications omitted for brevity)*\n...\n")
            continue
        
        direction = "➡️ OUT" if msg['is_from_me'] == "Yes" else "⬅️ IN"
        sender = IDENTITY_MAP.get(msg['sender_id'], msg['sender_id'])
        if msg['sender_id'] == "Me": sender = "Self"

        lines.append(f"### [{msg['date']}] {direction} ({sender})")
        lines.append(f"> {msg['text']}")
        if msg['attachment']:
            lines.append(f"📎 **Attachment:** `{msg['attachment']}`")
        lines.append("")

    # Write to file
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

    print(f"Ledger generated successfully at {LEDGER_PATH}")

if __name__ == "__main__":
    main()
