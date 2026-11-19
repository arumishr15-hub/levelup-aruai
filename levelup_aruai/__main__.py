"""Play in the terminal:  python -m levelup_aruai [--topic loops] [--rounds 5]"""
import argparse

from .agents import Coordinator
from .templates import TOPICS


def main(argv=None, input_fn=input, print_fn=print):
    p = argparse.ArgumentParser(prog="levelup_aruai")
    p.add_argument("--topic", choices=TOPICS)
    p.add_argument("--rounds", type=int, default=5)
    p.add_argument("--seed", type=int)
    args = p.parse_args(argv)
    game = Coordinator(seed=args.seed)
    print_fn("🐍  LevelUp_AruAI  —  type a letter, 'h' for a hint, 'q' to quit\n")
    for _ in range(args.rounds):
        data = game.next_question(topic=args.topic)
        q, lesson = data["question"], data["lesson"]
        print_fn(f"📘 Teacher: {lesson['title']} — {lesson['explain']}")
        print_fn(f"\n[{q.topic} · level {q.level}] {q.prompt}\n")
        print_fn("\n".join("    " + line for line in q.code.splitlines()) + "\n")
        letters = "abcd"[: len(q.options)]
        for letter, opt in zip(letters, q.options):
            print_fn(f"  {letter}) {opt.replace(chr(10), ' ⏎ ')}")
        while True:
            pick = input_fn("> ").strip().lower()
            if pick == "q":
                print_fn(f"\nBye! XP {game.teacher.xp} · {game.teacher.rank}")
                return game
            if pick == "h":
                print_fn(f"💡 {game.hint()}")
                continue
            if pick in letters:
                break
        fb = game.answer(q.options[letters.index(pick)])
        print_fn(("✅ " if fb["correct"] else "❌ ") + fb["message"])
        print_fn("   Walkthrough:\n   " + "\n   ".join(fb["walkthrough"]))
        if fb["level_change"]:
            print_fn(f"⭐ Level {fb['level_change']}! Now level {fb['level']}")
        print_fn(f"   +{fb['xp_gained']} XP → {fb['xp']} ({fb['rank']})\n")
    print_fn(f"Done! XP {game.teacher.xp} · {game.teacher.rank}")
    return game


if __name__ == "__main__":
    main()
