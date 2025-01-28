
import pytest
import os
import hashlib
from core_functions import generate_hashsum, compare_checksums, initialize_mapping_db
import sqlite3
import tempfile

def test_generate_hashsum_file():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"test content")
        file_path = tf.name
    
    expected_hash = hashlib.sha256(b"test content").hexdigest()
    result = generate_hashsum(file_path)
    
    os.unlink(file_path)
    assert result == expected_hash

def test_compare_checksums():
    checksum1 = "abc123"
    checksum2 = "abc123"
    assert compare_checksums(checksum1, checksum2) == True
    
    checksum2 = "def456"
    assert compare_checksums(checksum1, checksum2) == False

def test_initialize_mapping_db():
    test_db_path = '.storage/test_chat_mappings.db'
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        
    # Temporarily override the db path
    import core_functions
    original_path = core_functions.mappings_db_path
    core_functions.mappings_db_path = test_db_path
    
    initialize_mapping_db()
    
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_mappings'")
    assert cursor.fetchone() is not None
    
    # Check table structure
    cursor.execute("PRAGMA table_info(chat_mappings)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    expected_columns = ['integration', 'assistant_id', 'chat_id', 'thread_id', 'date_of_creation']
    assert all(col in column_names for col in expected_columns)
    
    conn.close()
    core_functions.mappings_db_path = original_path
    os.remove(test_db_path)
