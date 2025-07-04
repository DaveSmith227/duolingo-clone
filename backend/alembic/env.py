import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the project root to Python path so we can import our app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import our application modules
from app.core.config import get_settings
from app.core.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get database URL from our settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_dsn)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all model modules here to ensure they're registered with Base.metadata
# This is necessary for autogenerate to work properly
try:
    # Import all models so they're registered with Base.metadata
    from app.models.user import User, OAuthProvider
    from app.models.course import Language, Course, Section, Unit, Lesson, LessonPrerequisite
    from app.models.exercise import ExerciseType, Exercise, ExerciseOption, LessonExercise, AudioFile
    from app.models.progress import UserCourse, UserLessonProgress, UserExerciseInteraction
    from app.models.gamification import UserDailyXP, UserHeartsLog, Achievement, UserAchievement
    from app.models.audit import UserActivityLog, SystemAuditLog
except ImportError as e:
    # Models may not exist yet during initial setup
    print(f"Warning: Could not import models: {e}")
    pass

# Set target metadata for autogenerate support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
