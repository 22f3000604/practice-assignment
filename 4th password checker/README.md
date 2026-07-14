# Password Strength Checker

## Description
A CLI tool that evaluates password strength and provides specific feedback on weaknesses. Rates passwords as Weak, Fair, Good, or Strong based on length, character variety, and common patterns.

## Installation
```bash
pip install pytest pytest-cov
```

## Usage
```bash
python app.py
```

## Examples
```
Enter the password: hello
Score: 2/8 — Weak
Feedback:
  - Too short (minimum 8 characters)
  - Missing uppercase letters
  - Missing numbers
  - Missing special characters (!@#$%...)
  - This is a commonly used password!
```

```
Enter the password: Akshit@2005#3
Score: 8/8 — Strong
Your password is excellent! No weaknesses found.
```

## Scoring System
| Criteria          | Points |
|-------------------|--------|
| Length >= 8        | +1     |
| Length >= 12       | +2     |
| Has uppercase     | +1     |
| Has lowercase     | +1     |
| Has number        | +1     |
| Has special char  | +1     |
| Not common        | +1     |

## Rating Scale
| Score | Rating |
|-------|--------|
| 0-2   | Weak   |
| 3-4   | Fair   |
| 5-6   | Good   |
| 7-8   | Strong |

## Running Tests
```bash
pytest test_app.py -v
pytest --cov=app test_app.py
```
