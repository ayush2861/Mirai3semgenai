import os
import shutil
import sys
import json
import argparse

# Directory containing user data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "backend", "data")

def get_user_id_map():
    """Maps usernames and emails to user IDs."""
    users_file = os.path.join(DATA_DIR, "users", "users.json")
    mapping = {}
    if os.path.exists(users_file):
        try:
            with open(users_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for uid, uinfo in data.items():
                    mapping[uid] = uid
                    if "username" in uinfo:
                        mapping[uinfo["username"].lower()] = uid
                    if "email" in uinfo:
                        mapping[uinfo["email"].lower()] = uid
        except Exception:
            pass
    return mapping

def clear_chat_history(target_user: str = None):
    """
    Clears chat conversations while preserving documents and embeddings.
    If target_user is provided, only that user's conversations are removed.
    Otherwise, clears conversations for all users.
    """
    conv_file = os.path.join(DATA_DIR, "conversations_index.json")
    state_file = os.path.join(DATA_DIR, "state.json")

    user_map = get_user_id_map()
    resolved_uid = user_map.get(target_user.lower()) if target_user else None
    if target_user and not resolved_uid:
        resolved_uid = target_user  # fallback to raw string

    if resolved_uid:
        # Filter out only target user's conversations
        if os.path.exists(conv_file):
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    convs = json.load(f)
                remaining = {cid: c for cid, c in convs.items() if c.get("user_id") != resolved_uid}
                with open(conv_file, "w", encoding="utf-8") as f:
                    json.dump(remaining, f, indent=2, ensure_ascii=False)
                removed_count = len(convs) - len(remaining)
                print(f"✓ Removed {removed_count} conversation(s) for user '{target_user}'.")
            except Exception as e:
                print(f"Error processing {conv_file}: {e}")
        print(f"Chat history for user '{target_user}' cleared successfully.")
    else:
        # Clear all conversations for all users
        for file_path in [conv_file, state_file]:
            if os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("{}\n")
                print(f"✓ Cleared: {os.path.relpath(file_path, BASE_DIR)}")
        print("Chat history cleared for ALL users.")

def clear_all_data():
    """Safely clears chat history, uploaded PDFs, and vector index (ChromaDB) for all users."""
    clear_chat_history()
    
    # Reset documents index
    doc_index = os.path.join(DATA_DIR, "documents_index.json")
    if os.path.exists(doc_index):
        with open(doc_index, "w", encoding="utf-8") as f:
            f.write("{}\n")
        print(f"✓ Reset: {os.path.relpath(doc_index, BASE_DIR)}")
    
    # Folders to clean
    dirs_to_clean = ["documents", "uploads", "processed", "chroma"]
    for dir_name in dirs_to_clean:
        dir_path = os.path.join(DATA_DIR, dir_name)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)
            print(f"✓ Emptied folder: {os.path.relpath(dir_path, BASE_DIR)}")

    print("All chats, uploaded documents, and vector indexes have been safely reset for all users.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InfraMind Storage Cleaner")
    parser.add_argument("mode", nargs="?", default="chats", choices=["chats", "all"], help="Scope of cleanup: 'chats' (default) or 'all'")
    parser.add_argument("--user", type=str, default=None, help="Specific username, email, or user_id to clear chat history for")
    
    args = parser.parse_args()

    if args.mode == "all":
        clear_all_data()
    else:
        clear_chat_history(target_user=args.user)
