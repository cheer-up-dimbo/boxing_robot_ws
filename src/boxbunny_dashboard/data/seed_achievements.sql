-- Seed data: BoxBunny achievement definitions
-- These rows populate the achievement_definitions table used by the
-- gamification engine to track and display unlocked achievements.

INSERT OR IGNORE INTO achievement_definitions (achievement_id, name, description, icon, category, xp_reward) VALUES
    ('first_blood',       'First Blood',        'Complete your very first training session.',                           'fist',       'milestone',  50),
    ('century',           'Century',             'Throw 100 punches in a single session.',                              'fire',       'power',      75),
    ('fury',              'Fury',                'Throw 500 punches in a single session.',                              'flame',      'power',     150),
    ('thousand_fists',    'Thousand Fists',      'Throw 1,000 punches in a single session.',                            'explosion',  'power',     300),
    ('speed_demon',       'Speed Demon',         'Achieve a Lightning-tier reaction time.',                             'bolt',       'speed',     200),
    ('weekly_warrior',    'Weekly Warrior',       'Maintain a 7-day training streak.',                                  'calendar',   'streak',    100),
    ('consistent',        'Consistency King',    'Maintain a 30-day training streak.',                                  'crown',      'streak',    500),
    ('iron_chin',         'Iron Chin',           'Complete 10 total training sessions.',                                'shield',     'milestone', 100),
    ('marathon',          'Marathon',            'Complete 50 total training sessions.',                                'medal',      'milestone', 250),
    ('centurion',         'Centurion',           'Complete 100 total training sessions.',                               'trophy',     'milestone', 500),
    ('well_rounded',      'Well Rounded',        'Train in at least 3 different drill modes.',                          'circle',     'variety',   150),
    ('perfect_round',     'Perfect Round',       'Achieve 100% accuracy in a completed session.',                      'star',       'skill',     300),
    ('early_bird',        'Early Bird',          'Start a training session before 7 AM.',                               'sunrise',    'fun',        50),
    ('night_owl',         'Night Owl',           'Start a training session after 10 PM.',                               'moon',       'fun',        50),
    ('comeback_kid',      'Comeback Kid',        'Resume training after a break of 7 or more days.',                   'arrow_up',   'milestone',  75);
