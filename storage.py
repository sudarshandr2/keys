import json
import os
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash

class Storage:
    def __init__(self):
        self.users_file = 'data/users.json'
        self.keys_file = 'data/keys.json'
        self.transactions_file = 'data/transactions.json'
        self._ensure_data_files()
        self._ensure_admin_user()

    def _ensure_data_files(self):
        os.makedirs('data', exist_ok=True)
        for file_path in [self.users_file, self.keys_file, self.transactions_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)

    def _ensure_admin_user(self):
        users = self._read_json(self.users_file)
        admin_exists = any(user['role'] == 'admin' for user in users)

        if not admin_exists:
            # Create default admin user
            admin_user = {
                'id': str(uuid.uuid4()),
                'username': 'admin',
                'password_hash': generate_password_hash('admin123'),
                'role': 'admin',
                'balance': 0,
                'created_at': datetime.utcnow().isoformat()
            }
            users.append(admin_user)
            self._write_json(self.users_file, users)
            print("Default admin user created! Username: admin, Password: admin123")

    def _read_json(self, file_path):
        with open(file_path, 'r') as f:
            return json.load(f)

    def _write_json(self, file_path, data):
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_user(self, username):
        users = self._read_json(self.users_file)
        return next((user for user in users if user['username'] == username), None)

    def get_user_by_id(self, user_id):
        users = self._read_json(self.users_file)
        return next((user for user in users if user['id'] == user_id), None)

    def add_user(self, username, password_hash, role='reseller'):
        users = self._read_json(self.users_file)
        new_user = {
            'id': str(uuid.uuid4()),
            'username': username,
            'password_hash': password_hash,
            'role': role,
            'balance': 0,
            'created_at': datetime.utcnow().isoformat()
        }
        users.append(new_user)
        self._write_json(self.users_file, users)
        return new_user

    def get_keys(self, status=None):
        keys = self._read_json(self.keys_file)
        if status:
            return [key for key in keys if key['status'] == status]
        return keys

    def add_key(self, key_value, duration):
        keys = self._read_json(self.keys_file)
        new_key = {
            'id': str(uuid.uuid4()),
            'key': key_value,
            'duration': duration,
            'status': 'available',
            'created_at': datetime.utcnow().isoformat()
        }
        keys.append(new_key)
        self._write_json(self.keys_file, keys)
        return new_key

    def update_key_status(self, key_id, status, reseller_id=None):
        keys = self._read_json(self.keys_file)
        for key in keys:
            if key['id'] == key_id:
                key['status'] = status
                if reseller_id:
                    key['reseller_id'] = reseller_id
                key['updated_at'] = datetime.utcnow().isoformat()
                break
        self._write_json(self.keys_file, keys)