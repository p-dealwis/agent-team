#!/usr/bin/env python3
"""When a usage limit resets, and the one-shot cron that resumes just after it.

Usage: reset-time.py "<the limit message>" [margin-minutes, default 3]

Reads the reset time from a usage-limit message, for example
  "Claude usage limit reached. Your limit will reset at 3pm (Australia/Sydney)."
  "5-hour limit reached ∙ resets 3:30pm"
  "Claude AI usage limit reached|1759390200"           (epoch seconds)
  "Weekly limit reached ∙ resets Oct 3, 9am (Europe/London)"
A time without a date that has already passed means tomorrow. A named zone in parentheses is
used; otherwise the local zone. Prints, in local time (CronCreate's zone):
  RESET_AT=2026-10-02 15:00 AEST
  RESUME_AT=2026-10-02 15:03 AEST
  CRON=3 15 2 10 *
  WAIT_MINUTES=47
Exits 2 when the message has no reset time it can read.
"""
import re
import sys
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None

MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def fail(why):
    print(f"UNPARSED: {why}")
    sys.exit(2)


def main():
    if len(sys.argv) < 2:
        fail("no message given")
    msg = sys.argv[1]
    margin = timedelta(minutes=int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    local = datetime.now().astimezone()

    epoch = re.search(r"\|\s*(\d{10})\b", msg) or re.search(r"\b(1\d{9})\b", msg)
    if epoch:
        reset = datetime.fromtimestamp(int(epoch.group(1))).astimezone()
    else:
        zone = re.search(r"\(([A-Za-z_]+(?:/[A-Za-z_+-]+)+|UTC)\)", msg)
        tz = local.tzinfo
        if zone and ZoneInfo is not None:
            try:
                tz = ZoneInfo(zone.group(1))
            except Exception:
                fail(f"unknown time zone {zone.group(1)}")
        # The time after "reset" / "resets" (at), e.g. "3pm", "3:30 pm", "15:00".
        after = re.split(r"reset[s]?", msg, maxsplit=1, flags=re.I)
        text = after[1] if len(after) > 1 else msg
        t = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.sub(r"\b[A-Za-z]{3,9}\s+\d{1,2},", "", text), re.I)
        if not t or (t.group(2) is None and t.group(3) is None):
            fail("no reset time in the message")
        hour, minute, ampm = int(t.group(1)), int(t.group(2) or 0), (t.group(3) or "").lower()
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        if hour > 23 or minute > 59:
            fail("reset time out of range")
        now = datetime.now(tz)
        date = re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})\b", text)
        if date and date.group(1).lower() in MONTHS:
            month, day = MONTHS[date.group(1).lower()], int(date.group(2))
            reset = now.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            if reset < now - timedelta(days=180):
                reset = reset.replace(year=reset.year + 1)
        else:
            reset = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if reset < now - timedelta(minutes=1):
                reset += timedelta(days=1)
        reset = reset.astimezone(local.tzinfo)

    resume = (reset + margin).astimezone(local.tzinfo)
    fmt = "%Y-%m-%d %H:%M %Z"
    print(f"RESET_AT={reset.strftime(fmt)}")
    print(f"RESUME_AT={resume.strftime(fmt)}")
    print(f"CRON={resume.minute} {resume.hour} {resume.day} {resume.month} *")
    print(f"WAIT_MINUTES={max(0, int((resume - local).total_seconds() // 60))}")


if __name__ == "__main__":
    main()
