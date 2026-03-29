-- BoxBunny Achievement Seed Data
-- Run against the per-user database to populate the achievement catalog.
-- The 'achievements' table tracks which ones a user has unlocked;
-- this reference table defines available achievements.

CREATE TABLE IF NOT EXISTS achievement_catalog (
    achievement_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    icon TEXT NOT NULL DEFAULT 'trophy',
    xp_reward INTEGER NOT NULL DEFAULT 0
);

INSERT OR IGNORE INTO achievement_catalog (achievement_id, name, description, category, icon, xp_reward) VALUES
    ('first_blood',       'First Blood',        'Complete your first training session',                 'milestone',  'fist',        50),
    ('century',           'Century',             'Throw 100 punches in a single session',               'punches',    'fire',       100),
    ('fury',              'Fury',                'Throw 500 punches in a single session',               'punches',    'flame',      250),
    ('thousand_fists',    'Thousand Fists',      'Throw 1,000 punches in a single session',             'punches',    'explosion',  500),
    ('iron_chin',         'Iron Chin',           'Complete 10 sparring sessions',                       'sparring',   'shield',     150),
    ('speed_demon',       'Speed Demon',         'Achieve Lightning tier reaction time',                'reaction',   'lightning',  200),
    ('curriculum_master', 'Curriculum Master',   'Complete all 50 combo drills',                        'drills',     'scroll',     500),
    ('marathon',          'Marathon',            'Complete 50 total training sessions',                 'milestone',  'road',       300),
    ('centurion',         'Centurion',           'Complete 100 total training sessions',                'milestone',  'crown',      500),
    ('consistent',        'Consistent',          'Maintain a 30-day training streak',                   'streak',     'calendar',   400),
    ('weekly_warrior',    'Weekly Warrior',       'Maintain a 7-day training streak',                    'streak',     'sword',      100),
    ('well_rounded',      'Well-Rounded',        'Complete at least one session of every training mode', 'diversity',  'circle',     200),
    ('perfect_round',     'Perfect Round',       'Achieve 100% accuracy in a completed session',        'accuracy',   'bullseye',   300),
    ('power_house',       'Power House',         'Record a peak force above 800 N in a power test',     'power',      'dumbbell',   250),
    ('endurance_king',    'Endurance King',      'Maintain 60+ punches per minute for 3 minutes',       'stamina',    'heart',      250),
    ('combo_breaker',     'Combo Breaker',       'Land 10 perfect combos in shadow sparring',           'combos',     'chain',      200),
    ('night_owl',         'Night Owl',           'Train after 10 PM',                                   'fun',        'moon',        50),
    ('early_bird',        'Early Bird',          'Train before 6 AM',                                   'fun',        'sun',         50),
    ('social_butterfly',  'Social Butterfly',    'Participate in 5 coaching sessions',                  'social',     'people',     150),
    ('defense_master',    'Defence Master',      'Successfully block 50 attacks in defence drill',       'defence',    'wall',       300);
