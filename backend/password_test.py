from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

password = "mypassword123"

hashed_password = password_hash.hash(password)

print("Original password:")
print(password)

print("\nHashed password:")
print(hashed_password)

print("\nChecking password:")

if password_hash.verify(password, hashed_password):
    print("Password is correct ✅")
else:
    print("Password is incorrect ❌")