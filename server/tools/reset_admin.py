from app.database import SessionLocal
from app.models import User
from app.security import hash_password, verify_password

USERNAME = "admin"
PASSWORD = "admin12345"


def main():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == USERNAME).first()

        if user is None:
            print(f"администратор '{USERNAME}' не найден. создаю...")
            user = User(
                username=USERNAME,
                password_hash=hash_password(PASSWORD),
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"администратор создан: {USERNAME}")
        else:
            print(f"администратор '{USERNAME}' найден (id={user.id}).")
            print(f"текущий хеш пароля: {user.password_hash[:30]}...")
            
            if verify_password(PASSWORD, user.password_hash):
                print("пароль уже правильный.")
            else:
                print("пароль не подходит. обновляю...")
                user.password_hash = hash_password(PASSWORD)
                db.commit()
                print(f"пароль обновлён: {PASSWORD}")

        print("\nтеперь можно войти как:")
        print(f"  логин: {USERNAME}")
        print(f"  пароль: {PASSWORD}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
