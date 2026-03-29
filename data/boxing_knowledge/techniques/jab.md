# The Jab

The jab is the most important punch in boxing. It is a straight punch thrown with the lead hand (left hand for orthodox, right hand for southpaw). The jab sets up every other punch, controls distance, and disrupts your opponent's rhythm.

## Proper Form

1. **Starting Position**: Begin in your fighting stance with hands up, chin tucked, and elbows close to the body.
2. **Extension**: Extend the lead hand straight forward from the chin. The fist rotates so the palm faces down at full extension.
3. **Shoulder Turn**: Rotate the lead shoulder forward slightly to add reach and protect the chin.
4. **Snap Back**: Retract the hand immediately along the same line. The jab is a snap punch -- speed of return matters as much as speed of delivery.
5. **Rear Hand**: Keep the rear hand glued to the chin throughout the entire motion.

## Key Mechanics

- **Weight Distribution**: Stays roughly 50/50 or shifts slightly forward. Do not lunge.
- **Elbow Path**: The elbow stays down and moves along a straight line. Flaring the elbow telegraphs the punch and reduces power.
- **Foot Position**: The lead foot may step forward slightly to add reach, but the back foot must follow to maintain stance width.
- **Breathing**: Exhale sharply through the nose or with a short "tss" on each jab.

## Common Mistakes

| Mistake | Why It Happens | Fix |
|---------|---------------|-----|
| Dropping the hand before throwing | Loading up for power | Practice jab from guard -- no wind-up |
| Flaring the elbow out | Trying to add power | Shadow box in front of a mirror, watch elbow path |
| Leaning forward | Reaching for distance | Step with the jab instead of leaning |
| Slow retraction | Focusing only on the hit | Count "one" on throw, "two" on retract -- both fast |
| Rear hand drops | Lack of discipline | Hold a tennis ball against chin with rear glove during drills |

## Jab Variations

### Power Jab
Step forward with the lead foot as you throw, adding body weight behind the punch. Useful for establishing range.

### Flicker Jab
A loose, fast, low-effort jab used to maintain distance and obstruct the opponent's vision. Thrown with a relaxed arm that snaps out and back.

### Body Jab
Bend the knees and dip the lead shoulder to throw the jab to the opponent's midsection. Effective for mixing levels of attack.

### Up Jab
Thrown with a slight upward angle, useful against opponents who shell up with a tight guard. Targets the chin from underneath.

### Double and Triple Jab
Multiple jabs in succession. Vary the speed and power of each -- throw the first light to measure, the second hard to score.

## Drills for Improving the Jab

1. **Mirror Work (3 rounds)**: Throw 50 jabs per round in front of a mirror. Focus on keeping a straight line and snapping back.
2. **Speed Jab on Bag (3 rounds)**: Throw only jabs at maximum speed for the full round. Count total jabs and try to beat your record.
3. **Jab and Move (3 rounds)**: Throw a jab, take a lateral step, throw another jab. Develop the ability to jab while moving.
4. **Partner Drill -- Catch and Counter**: Partner throws a jab, you parry and return your own jab immediately.
5. **Resistance Band Jab**: Attach a light resistance band behind you. Throw jabs against the resistance to build shoulder endurance.

## When to Use the Jab

- To measure distance before committing to power punches
- To keep an aggressive opponent at bay (range management)
- To set up the cross (1-2 combination)
- To disrupt an opponent's timing when they are about to attack
- To score points with volume in a sparring or competition round
- To create openings by moving the opponent's guard

## BoxBunny Detection Notes

The jab is detected by the CV model as a fast linear extension of the lead hand. It typically registers on the **centre** or **left** pad on the BoxBunny system. The IMU fusion window for jabs is tight because of the punch's speed -- the CV detection and pad impact should occur within 200ms.
