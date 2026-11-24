from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol, Literal

from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)

# https://gchq.github.io/CyberChef/
# The first part of the cookie is the stored information.
app.secret_key = b'secret-key-change' # We need this for sessions!
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 # 1 MB

# Handlers

@app.route("/")
def index_get():
  order = request.args.get("order", "desc")
  toggle_url = "?order=asc" if order == "desc" else "?"
  # class IndexPresenter
  user_service = get_user_service()
  post_service = get_post_service()
  #
  items = post_service.get_posts(order)
  user = user_service.get_user(session.get("user", None))
  return render_template("index.html",
    user=user,
    items=items,
    toggle_url=toggle_url)

@app.route("/create-post", methods=["GET"])
def post_create_get():
  return render_template("post-form.html", title="Create new post")

# TODO Update the old functionality.
#   We need to load user from the session["user"]

# @app.route("/create-post", methods=["POST"])
# def post_create_post():
#   content = request.form["content"]
#   #
#   user_service = get_user_service()
#   post_service = get_post_service()
#   #
#   user = user_service.get_user(session.get("user", None))
#   return redirect(url_for("index_get"))

# New endpoints ...

@app.route("/register", methods=["GET"])
def user_register_get():
  return render_template("register.html")

@app.route("/register", methods=["POST"])
def user_register_post():
  username = request.form["username"]
  password = request.form["password"]
  avatar = request.files["avatar"].read()
  #
  user_service = get_user_service()
  user = user_service.register_user(username, password)
  user_service.set_avatar(user.identifier, avatar)
  # Login user and redirect to main.
  session["user"] = user.identifier
  # return redirect(url_for("index_get"))
  return ""

@app.route("/login", methods=["GET"])
def user_login_get():
  return render_template("login.html")

@app.route("/login", methods=["POST"])
def user_login_post():
  username = request.form["username"]
  password = request.form["password"]
  #
  user_service = get_user_service()
  user = user_service.authenticate(username, password)
  if user is None:
    return render_template("login.html", username=username, message="Failed to login!")
  else:
    session["user"] = user.identifier
    return redirect(url_for("index_get"))

@app.route("/logout", methods=["POST"])
def user_logout():
  session["user"] = None
  return redirect(url_for("index_get"))

@app.route("/api/users/<user>/avatar", methods=["GET"])
def user_avatar_get(user:str):
  user_service = get_user_service()
  #
  avatar = user_service.get_avatar(user)
  if avatar == None:
    return "", 404
  # https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types/Common_types
  return avatar, 200, {"Content-Type": "image/jpeg"}

# Template

@app.template_filter("datetime")
def format_datetime(value: datetime):
  if not value:
    return ""
  return value.strftime("%d.%m.%Y %H:%M %H:%M")

# Data definition

@dataclass
class User:
  identifier: str
  name: str

@dataclass
class Post:
  identifier: str
  author_identifier: str
  created_at: datetime
  content: str

# Data layer

class UserDatabase(Protocol):

  def create_user(self, name: str, password: str) -> User:
    """Create and return new user."""
    raise NotImplementedError

  def get_user(self, identifier: str) -> User | None:
    """Return user with given identifier or None."""
    raise NotImplementedError

  def authenticate(self, name: str, password: str) -> User | None:
    """Authenticate and return user or None."""
    raise NotImplementedError

class PostDatabase(Protocol):

  def get_posts(self) -> list[Post]:
    """Return ordered list of posts."""
    raise NotImplementedError

  def get_post(self, identifier:str) -> Post | None:
    """Return post or none."""
    raise NotImplementedError

  def create_post(self, author: User, content: str) -> Post:
    """Create and return new post."""
    raise NotImplementedError

  def update_post(self, identifier:str, content: str) -> Post | None:
    """Update and return existing post."""
    raise NotImplementedError

# InMemory

class InMemoryUserDatabase:

  def __init__(self):
    self.users = [{
      "identifier": "user-0",
      "name": "Ailish",
      "password": "aaa",
    }]

  def create_user(self, name: str, password: str) -> User:
    """Create and return new user."""
    identifier = f"user-{len(self.users)}"
    self.users.append({
      "identifier": identifier,
      "name": name,
      "password": password,
    })
    return User(identifier, name)

  def get_user(self, identifier: str | None) -> User | None:
    """Return user with given identifier or None."""
    if identifier == None:
      return None
    for user in self.users:
      if user["identifier"] == identifier:
        return User(identifier, user["name"])
    return None

  def authenticate(self, name: str, password: str) -> User | None:
    """Authenticate and return user or None."""
    for user in self.users:
      if user["name"] == name and user["password"] == password:
        return User(user["identifier"], user["name"])
    return None

class InMemoryPostDatabase(Protocol):
  posts: list[Post]

  def __init__(self):
    self.posts = [Post("post-0", "user-0", datetime.now(timezone.utc), "Her highness.")]

  def get_posts(self) -> list[Post]:
    """Return ordered list of posts."""
    return self.posts

  def get_post(self, identifier:str) -> Post | None:
    """Return post or none."""
    for post in self.posts:
      if post.identifier == identifier:
        return post
    return None

  def create_post(self, author: User, content: str) -> Post:
    """Create and return new post."""
    post = Post(
      f"post-{len(self.posts)}",
      author.identifier,
      datetime.now(timezone.utc),
      content)
    self.posts.append(post)
    return post

  def update_post(self, identifier:str, content: str) -> Post:
    """Create and return new post."""
    for post in self.posts:
      if post.identifier == identifier:
        post.content = content
        return post
    return None

# Services

class UserService:

  def __init__(self, user_database: UserDatabase):
    self.user_database = user_database
    self.avatars = {}

  def register_user(self, name: str, password: str) -> User:
    return self.user_database.create_user(name, password)

  def get_user(self, identifier: str) -> User | None:
    return self.user_database.get_user(identifier)

  def authenticate(self, name: str, password: str) -> User | None:
    return self.user_database.authenticate(name, password)

  def set_avatar(self, identifier: str, avatar: typing.ByteString) -> None:
    self.avatars[identifier] = avatar

  def get_avatar(self, identifier: str) -> typing.ByteString | None:
    return self.avatars.get(identifier, None)

class PostService:

  def __init__(self, post_database: PostDatabase):
    self.post_database = post_database.get_posts()

  def get_posts(self, order: typing.Literal["desc", "asc"]) -> list[Post]:
    """Return list of all posts."""
    posts = self.post_database
    return sorted(
      posts,
      key=lambda item: item.created_at,
      reverse=(order == order))

  def create_post(self, author: User, content: str) -> Post:
    """Create and return new post."""
    return self.post_database.create_post(author, content)

  def update_post(identifier: str, author: User, content: str) -> Post | None:
    """Update and return existing post."""
    prev = self.post_database.get_post(identifier)
    # Make sure we edit what belongs to the author.
    if not prev.author_identifier == author.identifier:
      return None
    #
    return self.update_post(identifier, content)

# Services temporary

user_service = UserService(InMemoryUserDatabase())

def get_user_service() -> UserService:
  return user_service

post_service = PostService(InMemoryPostDatabase())

def get_post_service() -> PostService:
  return post_service

#
