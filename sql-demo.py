import sqlite3

database_url=":memory:"
connection = sqlite3.connect(database_url, autocommit=False)
connection.row_factory = sqlite3.Row
cursor=connection.cursor()

cursor.execute("CREATE TABLE user(id, name, passwrd)")
cursor.execute("CREATE TABLE post(id, user, content)")

connection.commit()

def hash_password(value:str) -> str:
    return value

cursor.executemany("INSERT INTO user VALUES (?, ?, ?)", [
    (0,"Allish", hash_password("1234")),
    (1,"Max", hash_password("1234")),
])

cursor.executemany("INSERT INTO post VALUES (:id, :user, :content)", [
    {"id":0, "user":0, "content":"djngkjn"}
])

connection.commit()


print("Users:")
for row in cursor.execute("SELECT id, name FROM user"):
    print(" ", row[0], row[1])


result = cursor.execute("SELECT post.id AS id, user.name AS author, post.content AS content FROM post " \
                        "JOIN user ON post.user = user.id")
posts = result.fetchall()

from pprint import pprint
pprint(posts)
for post in posts:
    print(" ", post["author"], ":", post["content"])

user_id = 0
result = cursor.execute("SELECT user.name FROM user WHERE user.id = ?", [user_id])
user = result.fetchone()
