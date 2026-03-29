# Blocking Techniques

Blocking is the most fundamental defensive skill in boxing. It involves using the hands, arms, and shoulders to absorb or deflect incoming punches. A good block minimizes damage while keeping you in position to counter immediately.

## High Guard Block

The high guard is the primary defense against head punches.

### Technique
1. **Hands Up**: Both fists press against the forehead or temples. Fingers point upward.
2. **Elbows In**: Elbows tuck tight against the ribs and float at chin level.
3. **Chin Down**: The chin is tucked behind the forearms.
4. **Absorb and Reset**: When a punch lands on the guard, brace slightly, then immediately return to an offensive-ready position.

### Blocking Specific Punches

| Incoming Punch | Block Technique |
|---------------|-----------------|
| Jab | Rear hand catches or parries; lead hand stays ready to counter |
| Cross | Lead hand catches at the temple; rotate torso slightly to absorb |
| Lead Hook | Tighten the guard on the lead side; press the glove to the temple |
| Rear Hook | Raise the rear forearm to ear level; absorb with the arm |
| Uppercut | Drop the elbows and press forearms together in front of the chin |

## Parrying

Parrying is an active deflection that redirects the incoming punch away from its target. It is more advanced than blocking because it requires timing and creates immediate counter opportunities.

### Jab Parry
1. Use the rear hand to tap the incoming jab downward and to the inside.
2. The parry is a small, sharp movement -- not a sweeping motion.
3. Immediately counter with your own jab or cross over the deflected arm.

### Cross Parry
1. Use the lead hand to deflect the cross to the outside.
2. Rotate the torso slightly to assist the deflection.
3. Counter with a lead hook or rear hand as the opponent is turned.

### Key Principles of Parrying
- **Minimal Movement**: The deflection should be 3-4 inches, just enough to make the punch miss.
- **Timing**: Parry at the last possible moment to maintain your own guard.
- **Counter-Ready**: The parry should flow seamlessly into your counter punch.
- **Open Hand or Glove Face**: Use the palm/glove face to redirect, not a slap.

## Body Guard Block

Protecting the body requires adjusting the guard to cover the midsection.

### Technique
1. **Elbow Drop**: Drop the elbow on the targeted side to cover the ribs. The forearm stays vertical.
2. **Torso Turn**: Rotate the torso slightly so the elbow absorbs the punch rather than the soft tissue.
3. **Brace the Core**: Tighten the abdominal muscles at the moment of impact.
4. **Do Not Reach Down**: Lower the elbow, not the entire guard. Dropping the hands to block the body exposes the head.

### Liver Shot Defense
The liver (right side of the body for the defender) is the most dangerous body target. To protect it:
- Keep the right elbow pinned to the right side of the ribcage.
- Rotate the right hip slightly backward to move the liver away from the punch.
- If you anticipate the body shot, bend the knees and shift weight slightly to the rear foot.

## Shoulder Roll (Advanced)

The shoulder roll uses the lead shoulder to deflect straight punches while keeping both hands in position to counter.

### Technique
1. **Lead Shoulder Up**: Raise the lead shoulder to chin height. The chin tucks behind it.
2. **Lean Slightly Back**: A small rearward lean (2-3 inches) creates the rolling surface.
3. **Roll on Contact**: As the punch arrives, rotate the lead shoulder forward and upward, deflecting the punch across the shoulder surface.
4. **Counter**: The rear hand fires over the top as the opponent's punch slides off the shoulder.

### Prerequisites
- Excellent timing and distance awareness
- Strong understanding of punch trajectories
- Not recommended until basic blocking is second nature

## Common Blocking Mistakes

1. **Closing the eyes**: You cannot counter what you cannot see. Keep eyes open through impact.
2. **Reaching for the block**: Move the guard to the incoming punch path, do not lunge your body.
3. **Holding the block too long**: Block and immediately reset to offense. Staying in a shell invites volume.
4. **One-sided blocking**: Train both sides equally. Most people neglect their weaker side.
5. **Tensing up constantly**: Stay relaxed between punches. Tense only at the moment of impact.
6. **Blocking too far from the head**: The closer your guard is to your head, the more stable and effective the block.

## Drills for Blocking

1. **Partner Punch and Block**: One partner throws specific punches at 50% power while the other blocks. Rotate after each round.
2. **Reaction Block Drill**: Partner throws random punches (head and body). Block each one and call out what it was.
3. **Block and Counter**: Block one punch, immediately throw a counter. Develops the defensive-to-offensive transition.
4. **Wall Drill**: Stand with your back near a wall. Practice blocking without retreating -- forces you to rely on hand defense.
5. **Tennis Ball Drop**: Partner drops a tennis ball. Catch it while maintaining guard position. Develops hand speed and guard awareness.

## BoxBunny Detection Notes

The CV model detects blocks through the characteristic guard-tightening posture -- both hands raised, elbows in, chin tucked. The block detection requires consecutive frames of the blocking pose (configurable via `block_consecutive_needed`). In defense drill mode, the system evaluates whether the user blocked the robot arm punch before contact, using both CV block detection and robot arm IMU data.
