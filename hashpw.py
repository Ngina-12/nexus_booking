from werkzeug.security import generate_password_hash
pw = input("Enter password: ")
print("Hash:", generate_password_hash(pw))