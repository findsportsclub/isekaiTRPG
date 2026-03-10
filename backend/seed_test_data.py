from app.db.session import SessionLocal
from app.models.user import User
from app.models.world import World

db = SessionLocal()

user = User(
    email="test@example.com",
    username="testuser",
    password_hash="dummy_hash"
)
db.add(user)
db.commit()
db.refresh(user)

world = World(
    owner_user_id=user.user_id,
    world_name="黒霧の辺境",
    hero_name="アオ",
    seed=12345,
    era="DUNGEON_AGE",
    current_location="はじまりの村"
)
db.add(world)
db.commit()
db.refresh(world)

print("USER:", user.user_id, user.email, user.username)
print("WORLD:", world.world_id, world.world_name, world.hero_name)

db.close()
