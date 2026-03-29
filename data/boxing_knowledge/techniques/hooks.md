# Hooks: Left Hook and Right Hook

Hooks are semi-circular punches that travel along a horizontal arc to strike the side of the opponent's head or body. The hook is one of the most devastating punches in boxing when thrown correctly, because the target often cannot see it coming from the peripheral angle.

## Left Hook (Lead Hook for Orthodox)

### Proper Form

1. **Starting Position**: Fighting stance, hands up, elbows in.
2. **Pivot**: Rotate the lead foot, hip, and torso sharply to the right (for orthodox). The rotation generates the power.
3. **Arm Position**: The lead arm forms a roughly 90-degree angle at the elbow. The fist stays at chin height, palm facing down or toward you.
4. **Elbow Elevation**: The elbow rises to shoulder height during the punch. The forearm stays parallel to the ground.
5. **Contact**: Strike with the first two knuckles. The punch connects at the side of the target.
6. **Recovery**: Reverse the rotation to return to guard position.

### Key Points
- The arm angle stays fixed -- the power comes entirely from body rotation, not from swinging the arm.
- Keep the rear hand glued to the chin for protection.
- The lead foot pivots so the toes point roughly toward the target at the moment of impact.

## Right Hook (Rear Hook for Orthodox)

### Proper Form

1. **Starting Position**: Fighting stance, balanced weight.
2. **Pivot**: Drive the rear hip and rotate the torso to the left. The ball of the rear foot pivots inward.
3. **Arm Position**: The rear arm maintains a 90-degree bend. Fist travels horizontally at chin or body level.
4. **Shoulder Protection**: The rear shoulder comes forward to protect the chin during delivery.
5. **Recovery**: Reverse rotation back to stance.

### Key Points
- The right hook is slower than the left hook for orthodox fighters because it travels a longer distance.
- It is most effective when set up by a left hook or jab that turns the opponent's attention to the other side.
- Weight shifts from rear to front during the rotation.

## Common Mistakes

| Mistake | Why It Happens | Fix |
|---------|---------------|-----|
| Arm too straight (slapping) | Not bending elbow enough | Practice holding 90-degree angle against the bag |
| Arm too tight (no range) | Over-bending the elbow | Maintain fist at chin distance from your own face |
| Winding up / telegraphing | Pulling the arm back before throwing | Throw from guard -- no extra motion |
| Thumb up (pushing) | Incorrect fist orientation | Palm faces you or faces down, never sideways |
| No hip rotation | Arm punching | Drill rotation without punching first |
| Dropping the opposite hand | Loss of discipline | Partner taps you when guard drops |
| Hooking too wide | Trying to reach around the guard | Tighter arc, shorter distance to target |

## Hook Variations

### Shovel Hook
A hybrid between a hook and an uppercut. The fist travels at a 45-degree upward angle. Effective to the body, especially the liver (left shovel hook for orthodox vs southpaw).

### Check Hook
A defensive lead hook thrown while pivoting away from an advancing opponent. Used to counter aggressive fighters who charge forward.

### Long Hook
Thrown with a wider arm angle (around 120 degrees). Sacrifices some power for extra range. Useful at mid-range when the opponent is just out of close hook distance.

### Body Hook
Same mechanics but targeted at the ribs or liver. Bend the knees to lower your level rather than dropping the punch from high to low.

## Drills for Improving Hooks

1. **Heavy Bag Hooks (3 rounds)**: Stand close to the bag and throw only hooks. Focus on rotation, not arm swing. Feel the bag compress from your body weight.
2. **Mirror Rotation Drill**: Stand in front of a mirror without throwing punches. Practice the hip and torso rotation for both left and right hooks. Watch for clean, compact movement.
3. **Slip-Hook Combo**: Slip to the outside, immediately throw a lead hook. Develops the counter-hooking reflex.
4. **Double Hook Drill**: Throw left hook to body, left hook to head in quick succession. Trains level changes within the same punch type.
5. **Partner Catch Drill**: Partner holds a focus mitt at the side of their head. Throw hooks with emphasis on accuracy and controlled power.

## When to Use Hooks

- After the 1-2 combination (1-2-3 = jab-cross-hook)
- As a counter when the opponent drops their guard on one side
- To the body to attack the liver (left hook) or floating ribs
- After slipping a straight punch -- slip outside and counter with the hook
- To cut off a retreating opponent by hooking around their guard

## BoxBunny Detection Notes

Hooks are detected by the CV model through the characteristic lateral arc of the fist. The left hook registers on the **left** pad and the right hook on the **right** pad. Due to the rotational nature of hooks, the CV model may sometimes confuse them with uppercuts at close range -- the IMU pad location helps disambiguate via the fusion reclassification logic.
