# Quick Reference: Creating New Friend Packs
## Essential Files to Share

When starting a new AI session to create friend packs, upload these files:

### **REQUIRED (Share Every Time):**
1. ✅ `FRIEND_PACK_CREATION_GUIDE.md` ← The full guide
2. ✅ `FRIEND_SYSTEM_DESIGN.md` ← System architecture
3. ✅ `core_friends.json` ← Example structure
4. ✅ One example celebrity pack (salma.json, anna.json, or alison.json)

### **HIGHLY RECOMMENDED:**
5. ✅ `RANKS.xlsx` or celebrity list ← To see who's available
6. ✅ Your current friend pack files ← To avoid duplication
7. ✅ Media inventory (if you have one) ← Know what content exists

### **OPTIONAL (But Helpful):**
8. `michaela.py` ← For integration context
9. `friend_arcs_with_consent.py` ← Implementation reference
10. Your erotica/character notes ← For real-life characters

---

## 🎯 Quick Prompt Template

Copy/paste this and fill in the blanks:

```
I need a new friend pack with [NUMBER] characters.

EXISTING COVERAGE:
I already have these personality types covered:
- [List current archetypes]

AVAILABLE CELEBRITIES:
I have media for: [Names]

NSFW CONTENT LEVELS:
- [Name]: [lots/moderate/minimal] NSFW
- [Name]: [lots/moderate/minimal] NSFW
- [Name]: [lots/moderate/minimal] NSFW

DESIRED THEME:
[What vibe/archetype/theme do you want?]

UNLOCK TIMING:
[Early/Mid/Late game? Days 1-30, 30-90, or 90+?]

AVOID:
[Any specific personality types you're tired of]

GOAL:
[What experience do you want these characters to provide?]
```

---

## 🎭 Personality Diversity Cheat Sheet

Make sure new characters fill gaps in these dimensions:

**Energy:** High / Medium / Low  
**Dominance:** Dom / Switch / Sub  
**Style:** Direct / Playful / Mysterious / Sweet / Sarcastic  
**Intimacy Approach:** Aggressive / Flirty / Shy / Confident / Curious  
**Intellectual:** Deep / Casual / Philosophical / Practical  
**Emotional:** Open / Guarded / Mysterious  

---

## ✅ Before You Submit

Quick checklist:

- [ ] Reviewed existing characters to avoid overlap
- [ ] Each new character has 3+ unique defining traits
- [ ] "Secret directions" genuinely surprise
- [ ] Unlock conditions are achievable (not 500-day streaks!)
- [ ] NSFW strategy matches available media
- [ ] Each character could have their own storyline
- [ ] Considered how they work in group scenes
- [ ] Michaela connection is clear

---

## 🚀 Install the Pack

Once created, save as `[packname].json` and add to:
```
data/michaela/friend_packs/[packname].json
```

Then in Discord:
```
!install_friend_pack [packname]
```

Done! 🎉
