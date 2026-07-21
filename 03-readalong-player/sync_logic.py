"""
sync_logic.py - the core lookup for scenario 3.

Given a playback position t, find which word should be highlighted right now in a
list of word timestamps sorted by start time.

Run this file directly to execute the five edge-case tests:

    python sync_logic.py

The player front end uses a JavaScript mirror of this function with identical logic;
see templates/player.html.
"""


def find_active(words: list, t: float, speaker_filter: str = None):
    """Return the index of the word to highlight, or None.

    The lookup is stateless: it derives the answer from t alone rather than from a
    running cursor. That is what keeps it correct when the user drags the scrubber
    backwards, jumps around, or seeks past the end.
    """
    if not words or t < words[0]["start"] or t > words[-1]["end"]:
        return None                          # out of range: before the start or after the end
    lo, hi, answer = 0, len(words) - 1, -1
    while lo <= hi:                          # binary search: halve the range each step
        mid = (lo + hi) // 2
        if words[mid]["start"] <= t:
            answer, lo = mid, mid + 1        # candidate; look right for a later start
        else:
            hi = mid - 1
    if answer < 0 or t > words[answer]["end"]:
        return None                          # t fell in the silence between two words
    if speaker_filter and words[answer].get("speaker") != speaker_filter:
        return None                          # speaker filter: one table, filtered after the fact
    return answer


if __name__ == "__main__":
    words = [
        {"text": "Hello", "start": 0.0, "end": 0.4, "speaker": "A"},
        {"text": "world", "start": 0.5, "end": 0.9, "speaker": "A"},
        # --- a 1.5 second pause (the speaker takes a breath) ---
        {"text": "this",  "start": 2.4, "end": 2.6, "speaker": "B"},
        {"text": "is",    "start": 2.7, "end": 2.8, "speaker": "B"},
        {"text": "sync",  "start": 2.9, "end": 3.5, "speaker": "B"},
    ]
    assert find_active(words, 0.2) == 0,    "1. normal hit"
    assert find_active(words, 1.5) is None, "2. silence between words: highlight nothing"
    assert find_active(words, -1)  is None, "3. before the start: out of range"
    assert find_active(words, 9.9) is None, "4. past the end: no IndexError"
    assert find_active(words, 2.5, speaker_filter="A") is None, "5. speaker filter excludes"
    assert find_active(words, 2.5, speaker_filter="B") == 2,    "5. speaker filter includes"
    print("5/5 edge-case tests passed. "
          "Click-to-seek is the reverse lookup: words[i]['start'], O(1).")
