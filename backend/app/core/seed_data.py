"""
Initial Data Seeding Script

Populates the database with initial data including languages, exercise types,
achievements, and other reference data for the Duolingo clone application.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import init_database, SessionLocal
from app.models.course import Language
from app.models.exercise import ExerciseType
from app.models.gamification import Achievement, AchievementType


def seed_languages(db: Session) -> List[Language]:
    """
    Seed the database with initial language data.
    
    Args:
        db: Database session
        
    Returns:
        List of created Language objects
    """
    languages_data = [
        {
            "code": "en",
            "name": "English",
            "native_name": "English",
            "flag_url": "/flags/en.svg",
            "is_active": True,
            "sort_order": 1
        },
        {
            "code": "es",
            "name": "Spanish",
            "native_name": "Español",
            "flag_url": "/flags/es.svg",
            "is_active": True,
            "sort_order": 2
        },
        {
            "code": "fr",
            "name": "French",
            "native_name": "Français",
            "flag_url": "/flags/fr.svg",
            "is_active": True,
            "sort_order": 3
        },
        {
            "code": "de",
            "name": "German",
            "native_name": "Deutsch",
            "flag_url": "/flags/de.svg",
            "is_active": True,
            "sort_order": 4
        },
        {
            "code": "it",
            "name": "Italian",
            "native_name": "Italiano",
            "flag_url": "/flags/it.svg",
            "is_active": True,
            "sort_order": 5
        },
        {
            "code": "pt",
            "name": "Portuguese",
            "native_name": "Português",
            "flag_url": "/flags/pt.svg",
            "is_active": True,
            "sort_order": 6
        },
        {
            "code": "ru",
            "name": "Russian",
            "native_name": "Русский",
            "flag_url": "/flags/ru.svg",
            "is_active": True,
            "sort_order": 7
        },
        {
            "code": "ja",
            "name": "Japanese",
            "native_name": "日本語",
            "flag_url": "/flags/ja.svg",
            "is_active": True,
            "sort_order": 8
        },
        {
            "code": "ko",
            "name": "Korean",
            "native_name": "한국어",
            "flag_url": "/flags/ko.svg",
            "is_active": True,
            "sort_order": 9
        },
        {
            "code": "zh",
            "name": "Chinese",
            "native_name": "中文",
            "flag_url": "/flags/zh.svg",
            "is_active": True,
            "sort_order": 10
        }
    ]
    
    created_languages = []
    
    for lang_data in languages_data:
        try:
            # Check if language already exists
            existing = db.query(Language).filter(Language.code == lang_data["code"]).first()
            if existing:
                print(f"Language {lang_data['code']} already exists, skipping...")
                created_languages.append(existing)
                continue
            
            language = Language(**lang_data)
            db.add(language)
            db.commit()
            db.refresh(language)
            created_languages.append(language)
            print(f"Created language: {language.name} ({language.code})")
            
        except IntegrityError as e:
            db.rollback()
            print(f"Error creating language {lang_data['code']}: {e}")
            continue
    
    return created_languages


def seed_exercise_types(db: Session) -> List[ExerciseType]:
    """
    Seed the database with initial exercise type data.
    
    Args:
        db: Database session
        
    Returns:
        List of created ExerciseType objects
    """
    exercise_types_data = [
        {
            "name": "translation",
            "display_name": "Translation",
            "description": "Translate text from one language to another",
            "instructions": "Read the text and provide an accurate translation",
            "icon": "translate",
            "is_active": True,
            "supports_audio": False,
            "supports_images": True,
            "requires_text_input": True,
            "requires_multiple_choice": False,
            "xp_reward": 10
        },
        {
            "name": "multiple_choice",
            "display_name": "Multiple Choice",
            "description": "Select the correct answer from multiple options",
            "instructions": "Choose the best answer from the options provided",
            "icon": "list",
            "is_active": True,
            "supports_audio": True,
            "supports_images": True,
            "requires_text_input": False,
            "requires_multiple_choice": True,
            "max_options": 4,
            "xp_reward": 8
        },
        {
            "name": "listening",
            "display_name": "Listening",
            "description": "Listen to audio and provide the correct answer",
            "instructions": "Listen carefully and type what you hear",
            "icon": "volume-up",
            "is_active": True,
            "supports_audio": True,
            "supports_images": False,
            "requires_text_input": True,
            "requires_multiple_choice": False,
            "xp_reward": 12
        },
        {
            "name": "speaking",
            "display_name": "Speaking",
            "description": "Speak the prompted text aloud",
            "instructions": "Read the text aloud clearly",
            "icon": "microphone",
            "is_active": True,
            "supports_audio": True,
            "supports_images": False,
            "requires_text_input": False,
            "requires_multiple_choice": False,
            "xp_reward": 15
        },
        {
            "name": "match_pairs",
            "display_name": "Match Pairs",
            "description": "Match words or phrases with their translations",
            "instructions": "Connect each word with its correct translation",
            "icon": "link",
            "is_active": True,
            "supports_audio": False,
            "supports_images": True,
            "requires_text_input": False,
            "requires_multiple_choice": False,
            "xp_reward": 10
        },
        {
            "name": "fill_blanks",
            "display_name": "Fill in the Blanks",
            "description": "Complete sentences by filling in missing words",
            "instructions": "Type the missing word to complete the sentence",
            "icon": "edit",
            "is_active": True,
            "supports_audio": True,
            "supports_images": False,
            "requires_text_input": True,
            "requires_multiple_choice": False,
            "xp_reward": 12
        },
        {
            "name": "sort_words",
            "display_name": "Sort Words",
            "description": "Arrange words to form correct sentences",
            "instructions": "Drag and drop words to create a correct sentence",
            "icon": "arrows-sort",
            "is_active": True,
            "supports_audio": False,
            "supports_images": False,
            "requires_text_input": False,
            "requires_multiple_choice": False,
            "xp_reward": 14
        }
    ]
    
    created_types = []
    
    for type_data in exercise_types_data:
        try:
            # Check if exercise type already exists
            existing = db.query(ExerciseType).filter(ExerciseType.name == type_data["name"]).first()
            if existing:
                print(f"Exercise type {type_data['name']} already exists, skipping...")
                created_types.append(existing)
                continue
            
            exercise_type = ExerciseType(**type_data)
            db.add(exercise_type)
            db.commit()
            db.refresh(exercise_type)
            created_types.append(exercise_type)
            print(f"Created exercise type: {exercise_type.display_name} ({exercise_type.name})")
            
        except IntegrityError as e:
            db.rollback()
            print(f"Error creating exercise type {type_data['name']}: {e}")
            continue
    
    return created_types


def seed_achievements(db: Session) -> List[Achievement]:
    """
    Seed the database with initial achievement data.
    
    Args:
        db: Database session
        
    Returns:
        List of created Achievement objects
    """
    achievements_data = [
        # Streak achievements
        {
            "name": "first_streak",
            "display_name": "Getting Started",
            "description": "Complete your first day of learning",
            "achievement_type": AchievementType.STREAK.value,
            "icon_url": "/achievements/first_streak.svg",
            "badge_color": "#4CAF50",
            "xp_reward": 50,
            "hearts_reward": 1,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 1,
            "requirements": '{"streak_days": 1}',
            "achievement_metadata": '{"category": "beginner", "difficulty": "easy"}'
        },
        {
            "name": "week_warrior",
            "display_name": "Week Warrior",
            "description": "Maintain a 7-day learning streak",
            "achievement_type": AchievementType.STREAK.value,
            "icon_url": "/achievements/week_warrior.svg",
            "badge_color": "#FF9800",
            "xp_reward": 200,
            "hearts_reward": 2,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 2,
            "requirements": '{"streak_days": 7}',
            "achievement_metadata": '{"category": "dedication", "difficulty": "medium"}'
        },
        {
            "name": "month_master",
            "display_name": "Month Master",
            "description": "Maintain a 30-day learning streak",
            "achievement_type": AchievementType.STREAK.value,
            "icon_url": "/achievements/month_master.svg",
            "badge_color": "#9C27B0",
            "xp_reward": 1000,
            "hearts_reward": 5,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 3,
            "requirements": '{"streak_days": 30}',
            "achievement_metadata": '{"category": "dedication", "difficulty": "hard"}'
        },
        
        # XP milestone achievements
        {
            "name": "xp_explorer",
            "display_name": "XP Explorer",
            "description": "Earn your first 100 XP",
            "achievement_type": AchievementType.XP_MILESTONE.value,
            "icon_url": "/achievements/xp_explorer.svg",
            "badge_color": "#2196F3",
            "xp_reward": 25,
            "hearts_reward": 1,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 10,
            "requirements": '{"total_xp": 100}',
            "achievement_metadata": '{"category": "progress", "difficulty": "easy"}'
        },
        {
            "name": "xp_collector",
            "display_name": "XP Collector",
            "description": "Earn 1,000 total XP",
            "achievement_type": AchievementType.XP_MILESTONE.value,
            "icon_url": "/achievements/xp_collector.svg",
            "badge_color": "#FF5722",
            "xp_reward": 100,
            "hearts_reward": 2,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 11,
            "requirements": '{"total_xp": 1000}',
            "achievement_metadata": '{"category": "progress", "difficulty": "medium"}'
        },
        {
            "name": "xp_legend",
            "display_name": "XP Legend",
            "description": "Earn 10,000 total XP",
            "achievement_type": AchievementType.XP_MILESTONE.value,
            "icon_url": "/achievements/xp_legend.svg",
            "badge_color": "#FFD700",
            "xp_reward": 500,
            "hearts_reward": 5,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 12,
            "requirements": '{"total_xp": 10000}',
            "achievement_metadata": '{"category": "progress", "difficulty": "hard"}'
        },
        
        # Lesson completion achievements
        {
            "name": "first_lesson",
            "display_name": "First Steps",
            "description": "Complete your first lesson",
            "achievement_type": AchievementType.LESSON_COMPLETION.value,
            "icon_url": "/achievements/first_lesson.svg",
            "badge_color": "#8BC34A",
            "xp_reward": 30,
            "hearts_reward": 1,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 20,
            "requirements": '{"lessons_completed": 1}',
            "achievement_metadata": '{"category": "milestone", "difficulty": "easy"}'
        },
        {
            "name": "lesson_enthusiast",
            "display_name": "Lesson Enthusiast",
            "description": "Complete 50 lessons",
            "achievement_type": AchievementType.LESSON_COMPLETION.value,
            "icon_url": "/achievements/lesson_enthusiast.svg",
            "badge_color": "#673AB7",
            "xp_reward": 250,
            "hearts_reward": 3,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 21,
            "requirements": '{"lessons_completed": 50}',
            "achievement_metadata": '{"category": "milestone", "difficulty": "medium"}'
        },
        
        # Perfect lesson achievements
        {
            "name": "perfectionist",
            "display_name": "Perfectionist",
            "description": "Complete a lesson with 100% accuracy",
            "achievement_type": AchievementType.PERFECT_LESSON.value,
            "icon_url": "/achievements/perfectionist.svg",
            "badge_color": "#E91E63",
            "xp_reward": 75,
            "hearts_reward": 1,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 30,
            "requirements": '{"perfect_lessons": 1, "accuracy": 100}',
            "achievement_metadata": '{"category": "skill", "difficulty": "medium"}'
        },
        
        # Speed challenge achievements
        {
            "name": "speed_demon",
            "display_name": "Speed Demon",
            "description": "Complete a lesson in under 2 minutes",
            "achievement_type": AchievementType.SPEED_CHALLENGE.value,
            "icon_url": "/achievements/speed_demon.svg",
            "badge_color": "#FF4444",
            "xp_reward": 100,
            "hearts_reward": 2,
            "is_active": True,
            "is_hidden": False,
            "sort_order": 40,
            "requirements": '{"max_time_seconds": 120}',
            "achievement_metadata": '{"category": "skill", "difficulty": "hard"}'
        }
    ]
    
    created_achievements = []
    
    for achievement_data in achievements_data:
        try:
            # Check if achievement already exists
            existing = db.query(Achievement).filter(Achievement.name == achievement_data["name"]).first()
            if existing:
                print(f"Achievement {achievement_data['name']} already exists, skipping...")
                created_achievements.append(existing)
                continue
            
            achievement = Achievement(**achievement_data)
            db.add(achievement)
            db.commit()
            db.refresh(achievement)
            created_achievements.append(achievement)
            print(f"Created achievement: {achievement.display_name} ({achievement.name})")
            
        except IntegrityError as e:
            db.rollback()
            print(f"Error creating achievement {achievement_data['name']}: {e}")
            continue
    
    return created_achievements


def seed_all_data(db: Session) -> Dict[str, List[Any]]:
    """
    Seed all initial data.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with lists of created objects by type
    """
    print("Starting database seeding...")
    
    # Seed languages
    print("\n--- Seeding Languages ---")
    languages = seed_languages(db)
    
    # Seed exercise types
    print("\n--- Seeding Exercise Types ---")
    exercise_types = seed_exercise_types(db)
    
    # Seed achievements
    print("\n--- Seeding Achievements ---")
    achievements = seed_achievements(db)
    
    print(f"\n--- Seeding Complete ---")
    print(f"Created {len(languages)} languages")
    print(f"Created {len(exercise_types)} exercise types")
    print(f"Created {len(achievements)} achievements")
    
    return {
        "languages": languages,
        "exercise_types": exercise_types,
        "achievements": achievements
    }


def main():
    """Main function to run the seeding script."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import get_settings
    
    # Create engine and session directly
    settings = get_settings()
    print(f"Connecting to database: {settings.database_dsn}")
    
    engine = create_engine(
        settings.database_dsn,
        connect_args={"check_same_thread": False} if settings.database_dsn.startswith("sqlite") else {}
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    try:
        seed_all_data(db)
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()