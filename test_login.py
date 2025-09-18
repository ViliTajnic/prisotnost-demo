#!/usr/bin/env python3

from werkzeug.security import generate_password_hash, check_password_hash
import sys

# Test password hashing
password = "admin123"
print(f"Testing password: {password}")

# Generate a new hash
new_hash = generate_password_hash(password)
print(f"Generated hash: {new_hash}")

# Test with the current hash from database
db_hash = "scrypt:32768:8:1$XYZ123$hash_here"
print(f"Database hash: {db_hash}")

# Check if password matches
result = check_password_hash(db_hash, password)
print(f"Password check result: {result}")

# Also test different common passwords
test_passwords = ["admin", "admin123", "password", "123456"]
for test_pass in test_passwords:
    result = check_password_hash(db_hash, test_pass)
    print(f"Password '{test_pass}' matches: {result}")