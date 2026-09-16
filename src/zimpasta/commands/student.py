"""Collect information for a new student."""


def add_student():
    name = input("What is the student's name? ").strip() or "n/a"
    class_standing = input(
        "What is the student's class standing (freshman, sophomore, junior, or senior)? "
    ).strip() or "n/a"
    enrolled_class = input("What class is the student enrolled in? ").strip() or "n/a"
    major = input("What is the student's major? ").strip() or "n/a"

    has_minor = input("Does the student have a minor? (y/n): ").strip().lower()
    if has_minor == "y":
        minor = input("What is the student's minor? ").strip() or "n/a"
    else:
        minor = "n/a"

    return {
        "name": name,
        "class_standing": class_standing,
        "enrolled_class": enrolled_class,
        "major": major,
        "minor": minor,
    }


if __name__ == "__main__":
    student = add_student()
    print("Student added successfully:")
    for field, value in student.items():
        print(f"{field.replace('_', ' ').title()}: {value}")