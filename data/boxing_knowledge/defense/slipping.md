# Slipping

Slipping is a defensive technique that involves moving the head laterally to avoid an incoming punch. Unlike blocking, slipping allows the punch to pass by without any contact, leaving both hands free for immediate counter-attacks. It is one of the most effective defensive skills in boxing.

## Basic Slip Technique

### Slipping to the Outside (vs Jab or Cross)

1. **Read the Punch**: Watch the opponent's shoulder and hand. The shoulder rolls forward before the fist arrives.
2. **Bend at the Knees and Waist**: Dip slightly and rotate the torso to move the head 4-6 inches to the outside of the incoming punch. "Outside" means away from the punching arm.
3. **Keep Eyes on Opponent**: Do not look at the floor. Your eyes stay on the opponent's chest or chin.
4. **Hands Stay Up**: The guard does not drop during the slip. Both hands remain at chin level.
5. **Return to Centre**: After the punch passes, straighten back to your stance. Do not linger in the slipped position.

### Slipping to the Inside (vs Jab or Cross)

1. **Same read and dip** as the outside slip.
2. **Rotate the torso inward**: Move the head to the inside of the incoming arm (between the opponent's arms).
3. **Higher Risk**: Slipping inside puts you between the opponent's arms, which is more dangerous but opens powerful counter opportunities (particularly the cross and lead hook).

## Mechanics of the Slip

- **Knee Bend**: The knees act as shock absorbers and provide the vertical component of the slip. Bending the knees 2-3 inches creates the necessary head movement.
- **Torso Rotation**: The torso rotates laterally, combining with the knee bend to move the head off the centre line.
- **Head Movement**: The head moves just enough to avoid the punch -- typically 4-6 inches. Larger slips waste energy and create recovery delay.
- **Weight Transfer**: Weight shifts to the side you are slipping toward. This loads the legs for a powerful counter.

## Timing

Timing is the most critical aspect of slipping:

- **Too Early**: The opponent can adjust the punch trajectory to follow your head.
- **Too Late**: The punch lands before you move.
- **Just Right**: The slip happens as the punch is fully committed but before it arrives. This is a narrow window that requires practice.

### Developing Timing
1. Start with slow partner drills. Have a partner throw jabs at 30% speed while you practice the slip.
2. Gradually increase speed as your reaction time improves.
3. Use a double-end bag -- it snaps back unpredictably and forces reactive slipping.
4. The BoxBunny reaction time drill helps calibrate your slip timing against machine-speed stimuli.

## Counter-Attacking After Slips

The slip is not complete until you counter. The slip loads your body for explosive counters.

### Outside Slip Counters
| After Slipping... | Counter With |
|-------------------|-------------|
| Outside a jab | Rear cross over the top |
| Outside a cross | Lead hook to the exposed head |
| Outside a jab | Lead body hook (opponent's ribs are open) |

### Inside Slip Counters
| After Slipping... | Counter With |
|-------------------|-------------|
| Inside a jab | Rear uppercut |
| Inside a cross | Lead uppercut or lead hook |
| Inside a jab | Rear cross (straight up the middle) |

## Common Slipping Mistakes

1. **Bending at the waist only**: The slip should involve the knees, not just a waist bend. Bending at the waist alone puts you off-balance and makes recovery slow.
2. **Over-slipping**: Moving the head too far offline. You end up out of position and unable to counter effectively.
3. **Dropping the hands**: The guard must stay up during the slip. If your hands drop, you are vulnerable to follow-up punches.
4. **Looking at the floor**: Keep your eyes on the opponent throughout the movement.
5. **Not countering**: A slip without a counter is a wasted defensive action. The opponent will simply throw again.
6. **Only slipping one direction**: Train both inside and outside slips equally on both sides.
7. **Pulling straight backward**: Pulling the head back is not a slip -- it is a lean, and it puts you off balance with no counter opportunity.

## Drills for Slipping

1. **Rope Slip Drill**: Tie a rope at head height between two posts. Walk along the rope, slipping under it by bending the knees and rotating the torso. Go forward and backward.
2. **Partner Jab Drill (3 rounds)**: Partner throws jabs at 50% speed. Slip every jab and counter with a cross. Focus on timing over speed.
3. **Double-End Bag**: The unpredictable rebound forces reactive head movement. Throw a jab, slip the rebound, throw another punch.
4. **Shadow Boxing with Slips**: Every 3-4 punches in a combination, add a slip. Build the habit of defensive movement between offensive sequences.
5. **Pendulum Drill**: Stand in stance and rock your head side to side in a pendulum motion, bending at the knees. Do 30 seconds on, 30 seconds off, for 3 rounds.
6. **Reaction Ball**: Bounce a reaction ball off a wall. Practice moving your head out of the way as it returns. Develops reflexive lateral head movement.

## BoxBunny Detection Notes

Slipping is detected by the BoxBunny system through the user tracking module, which measures lateral displacement and depth changes via the D435i depth camera. A slip is classified when the lateral displacement exceeds the `slip_lateral_threshold_px` (default 40 pixels) or the depth displacement exceeds `slip_depth_threshold_m` (default 0.15 metres) during a defense window. The system differentiates between slips and dodges based on the magnitude of displacement.
