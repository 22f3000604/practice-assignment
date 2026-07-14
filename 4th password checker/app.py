# ---- Common Passwords List ----

common_passwords = [
    "password", "12345678", "qwerty", "admin123", "hello world",
    "letmein", "welcome", "monkey", "dragon", "master",
    "login", "abc123", "111111", "password1", "iloveyou",
    "123456", "password123", "admin", "root", "guest"
]


# ---- Password Strength Checker ----

def check_password(passwo):
    points = 0
    feedback = []

    # Check length >= 8
    if len(passwo) >= 8:
        points += 1
    else:
        feedback.append("Too short (minimum 8 characters)")

    # Check length >= 12
    if len(passwo) >= 12:
        points += 2
    
    # Check uppercase
    if any(char.isupper() for char in passwo):
        points += 1
    else:
        feedback.append("Missing uppercase letters")

    # Check lowercase
    if any(char.islower() for char in passwo):
        points += 1
    else:
        feedback.append("Missing lowercase letters")

    # Check digits
    if any(char.isdigit() for char in passwo):
        points += 1
    else:
        feedback.append("Missing numbers")

    # Check special characters
    special_chars = "!@#$%^&*()_+-=[]{}|;:',.<>?/"
    if any(char in special_chars for char in passwo):
        points += 1
    else:
        feedback.append("Missing special characters (!@#$%...)")

    # Check not common
    if passwo.lower() not in common_passwords:
        points += 1
    else:
        feedback.append("This is a commonly used password!")

    return points, feedback


# ---- Score to Rating ----

def score_checker(points, feedback):
    if points <= 2:
        rating = "Weak"
    elif points <= 4:
        rating = "Fair"
    elif points <= 6:
        rating = "Good"
    else:
        rating = "Strong"

    print(f"\nScore: {points}/8 — {rating}")

    if feedback:
        print("\nFeedback:")
        for msg in feedback:
            print(f"  - {msg}")
    else:
        print("\nYour password is excellent! No weaknesses found.")


# ---- Main ----

if __name__ == "__main__":
    password = input("Enter the password: ")
    points, feedback = check_password(password)
    score_checker(points, feedback)